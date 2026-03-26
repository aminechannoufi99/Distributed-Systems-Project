from __future__ import annotations

import threading
import time
from queue import Empty, Queue
from typing import Dict, Optional, Tuple

import messages
from state import (
    AVAILABLE,
    BUSY,
    CRASHED,
    COMPLETED,
    PENDING,
    PROCESSING,
    REASSIGNED,
    Order,
    StateStore,
)


class Coordinator(threading.Thread):
    """Central coordinator for order assignment, timeouts, and GUI updates."""

    def __init__(
        self,
        state_store: StateStore,
        inbox: Queue,
        pizzaiolo_inboxes: Dict[int, Queue],
        gui_queue: Optional[Queue] = None,
        stop_event: Optional[threading.Event] = None,
        timeout_seconds: float = 10.0,
        recovery_seconds: float = 6.0,
    ) -> None:
        super().__init__(name="Coordinator", daemon=True)
        self.state_store = state_store
        self.inbox = inbox
        self.pizzaiolo_inboxes = pizzaiolo_inboxes
        self.gui_queue = gui_queue
        self.stop_event = stop_event or threading.Event()

        self.in_progress: Dict[str, Tuple[int, float]] = {}
        self.crashed_until: Dict[int, float] = {}
        self.timeout_seconds = timeout_seconds
        self.recovery_seconds = recovery_seconds
        self._last_gui_emit = 0.0

    def run(self) -> None:
        self._log("Coordinator started")
        self._emit_state(force=True)
        while not self.stop_event.is_set():
            try:
                msg = self.inbox.get(timeout=0.5)
            except Empty:
                msg = None

            if msg:
                if msg.get("type") == messages.SHUTDOWN:
                    break
                self._handle_message(msg)

            self._check_timeouts()
            self._try_assign()

        self._log("Coordinator stopped")

    def _handle_message(self, msg: dict) -> None:
        msg_type = msg.get("type")
        if msg_type == messages.NEW_ORDER:
            self._handle_new_order(msg)
        elif msg_type == messages.COMPLETE:
            self._handle_complete(msg)

    def _handle_new_order(self, msg: dict) -> None:
        order_id = msg["order_id"]
        pizza_type = msg["pizza_type"]
        now = msg.get("created_at", time.time())

        with self.state_store.lock:
            if order_id in self.state_store.orders:
                self._log(f"Duplicate order ignored: {order_id}")
                return

            order = Order(
                order_id=order_id,
                pizza_type=pizza_type,
                status=PENDING,
                created_at=now,
                updated_at=now,
            )
            self.state_store.orders[order_id] = order
            self.state_store.pending_queue.append(order_id)

        self._log(f"New order received: {order_id} ({pizza_type})")
        self._state_changed()

    def _handle_complete(self, msg: dict) -> None:
        order_id = msg["order_id"]
        pizzaiolo_id = msg["pizzaiolo_id"]
        completed_at = msg.get("completed_at", time.time())

        with self.state_store.lock:
            order = self.state_store.orders.get(order_id)
            if not order:
                self._log(f"Unknown order completed: {order_id}")
                return
            if order.status != PROCESSING or order.assigned_to != pizzaiolo_id:
                self._log(f"Late completion ignored for {order_id} from P{pizzaiolo_id}")
                return

            order.status = COMPLETED
            order.completed_at = completed_at
            order.updated_at = completed_at
            self.state_store.pizzaioli[pizzaiolo_id] = AVAILABLE
            self.in_progress.pop(order_id, None)

        self._log(f"Order completed: {order_id} by P{pizzaiolo_id}")
        self._state_changed(force_emit=True)

    def _try_assign(self) -> None:
        while True:
            with self.state_store.lock:
                available = sorted(
                    pid
                    for pid, status in self.state_store.pizzaioli.items()
                    if status == AVAILABLE
                )
                if not available or not self.state_store.pending_queue:
                    return

                order_id = self.state_store.pending_queue.popleft() # here we should implement the FCFS (removes the first (oldest) element  returns it)
                order = self.state_store.orders.get(order_id)
                if not order:
                    continue

                #preferred = [pid for pid in available if pid != order.last_failed_pizzaiolo]
                #pizzaiolo_id = (preferred or available)[0]
                pizzaiolo_id= available[0]
                started_at = time.time()
                order.status = PROCESSING
                order.assigned_to = pizzaiolo_id
                order.started_at = started_at
                order.updated_at = started_at
                order.attempts += 1

                self.state_store.pizzaioli[pizzaiolo_id] = BUSY
                self.in_progress[order_id] = (pizzaiolo_id, started_at)

            self.pizzaiolo_inboxes[pizzaiolo_id].put(
                messages.assign(order_id, order.pizza_type)
            )
            self.pizzaiolo_inboxes[pizzaiolo_id].put(messages.ack(order_id))
            self._log(f"Assigned {order_id} to P{pizzaiolo_id}")
            self._state_changed(force_emit=True)

    def _check_timeouts(self) -> None:
        now = time.time()
        timed_out: Dict[str, int] = {}
        recovered: Dict[int, float] = {}

        with self.state_store.lock:
            # Recover previously crashed workers when their timeout expires.
            for pizzaiolo_id, recover_at in list(self.crashed_until.items()):
                if now < recover_at:
                    continue
                if self.state_store.pizzaioli.get(pizzaiolo_id) == CRASHED:
                    self.state_store.pizzaioli[pizzaiolo_id] = AVAILABLE
                    recovered[pizzaiolo_id] = recover_at
                self.crashed_until.pop(pizzaiolo_id, None)

            # Detect active orders that exceeded the allowed timeout.
            for order_id, (pizzaiolo_id, start_time) in list(self.in_progress.items()):
                if now - start_time < self.timeout_seconds:
                    continue
                order = self.state_store.orders.get(order_id)
                if not order:
                    self.in_progress.pop(order_id, None)
                    continue

                self.state_store.pizzaioli[pizzaiolo_id] = CRASHED
                self.crashed_until[pizzaiolo_id] = now + self.recovery_seconds

                if order.status == PROCESSING and order.assigned_to == pizzaiolo_id:
                    order.status = REASSIGNED
                    order.assigned_to = None
                    order.started_at = None
                    order.updated_at = now
                    order.last_failed_pizzaiolo = pizzaiolo_id
                    self.state_store.pending_queue.appendleft(order_id)

                self.in_progress.pop(order_id, None)
                timed_out[order_id] = pizzaiolo_id

        for order_id, pizzaiolo_id in timed_out.items():
            self._log(f"Timeout -> P{pizzaiolo_id} crashed on {order_id}, reassigned.")
        for pizzaiolo_id in recovered.keys():
            self._log(f"P{pizzaiolo_id} recovered and is AVAILABLE again.")

        if timed_out or recovered:
            self._state_changed(force_emit=True)

    def _state_changed(self, force_emit: bool = False) -> None:
        self._emit_state(force=force_emit)

    def _emit_state(self, force: bool = False) -> None:
        if self.gui_queue is None:
            return
        now = time.time()
        if not force and now - self._last_gui_emit < 0.2:
            return

        snapshot = self.state_store.snapshot()
        self.gui_queue.put(messages.gui_state(snapshot))
        self._last_gui_emit = now

    def _log(self, message: str) -> None:
        if self.gui_queue is not None:
            self.gui_queue.put(messages.gui_log(message))

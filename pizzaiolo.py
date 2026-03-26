from __future__ import annotations

import random
import threading
import time
from queue import Empty, Queue
from typing import Dict, Optional, Tuple

import messages


class Pizzaiolo(threading.Thread):
    """Worker that simulates pizza preparation."""

    def __init__(
        self,
        pizzaiolo_id: int,
        inbox: Queue,
        coordinator_queue: Queue,
        stop_event: Optional[threading.Event] = None,
        prep_range: Tuple[int, int] = (5, 10),
        prep_ranges_by_type: Optional[Dict[str, Tuple[int, int]]] = None,
        crash_prob: float = 0.0,
        crash_delay_range: Tuple[float, float] = (0.5, 2.0),
    ) -> None:
        super().__init__(name=f"Pizzaiolo-{pizzaiolo_id}", daemon=True)
        self.pizzaiolo_id = pizzaiolo_id
        self.inbox = inbox
        self.coordinator_queue = coordinator_queue
        self.prep_range = prep_range
        self.prep_ranges_by_type = prep_ranges_by_type or {}
        self.stop_event = stop_event or threading.Event()
        self.crash_prob = crash_prob
        self.crash_delay_range = crash_delay_range
        self._crash_until = 0.0

    def run(self) -> None:
        while not self.stop_event.is_set():
            if self._crash_until > time.time():
                time.sleep(0.2)
                continue

            try:
                msg = self.inbox.get(timeout=0.5)
            except Empty:
                continue

            msg_type = msg.get("type")
            if msg_type == messages.SHUTDOWN:
                break
            if msg_type in {messages.ACK, None}:
                continue
            if msg_type != messages.ASSIGN:
                continue

            self._process_order(msg)

    def _process_order(self, msg: dict) -> None:
        order_id = msg["order_id"]
        pizza_type = msg.get("pizza_type")

        if self.crash_prob > 0.0 and random.random() < self.crash_prob:
            self._crash_until = time.time() + random.uniform(*self.crash_delay_range)
            return

        range_for_type = self.prep_ranges_by_type.get(pizza_type, self.prep_range)
        prep_time = random.uniform(*range_for_type)
        started_at = time.time()
        while time.time() - started_at < prep_time:
            if self.stop_event.is_set():
                return
            time.sleep(0.2)

        self._emit_complete(order_id)

    def _emit_complete(self, order_id: str) -> None:
        self.coordinator_queue.put(messages.complete(self.pizzaiolo_id, order_id))

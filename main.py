from __future__ import annotations

import itertools
import random
import threading
import time
from queue import Queue
from typing import Dict, List

import messages
from coordinator import Coordinator
from gui.dashboard import Dashboard
from pizzaiolo import Pizzaiolo
from state import StateStore
from supervisor import Supervisor

PIZZA_TYPES = [
    "Margherita",
    "Pepperoni",
    "Diavola",
    "Quattro Formaggi",
    "Funghi",
    "Veggie",
    "Prosciutto",
    "Capricciosa",
]

PIZZA_PREP_RANGES = {
    "Margherita": (5, 7),
    "Pepperoni": (6, 9),
    "Diavola": (7, 10),
    "Quattro Formaggi": (7, 10),
    "Funghi": (6, 8),
    "Veggie": (5, 8),
    "Prosciutto": (6, 9),
    "Capricciosa": (7, 10),
}

AUTO_GENERATE = False
ARRIVAL_MODE = "burst"
TOTAL_ORDERS = 8
CONTINUOUS_MAX_INTERVAL = 4.0

CRASH_PROB = 0.2
TIMEOUT_SECONDS = 10.0
RECOVERY_SECONDS = 6.0


def main() -> None:
    """Run the pizza delivery simulation with a monitoring GUI."""
    stop_event = threading.Event()
    coord_inbox: Queue = Queue()
    gui_queue: Queue = Queue()

    pizzaiolo_ids = list(range(4))
    pizzaiolo_inboxes: Dict[int, Queue] = {pid: Queue() for pid in pizzaiolo_ids}

    state_store = StateStore()
    state_store.initialize(pizzaiolo_ids)  # Central registry for global state.

    pizzaioli: List[Pizzaiolo] = []
    for pid in pizzaiolo_ids:
        worker = Pizzaiolo(
            pid,
            pizzaiolo_inboxes[pid],
            coord_inbox,
            stop_event=stop_event,
            prep_ranges_by_type=PIZZA_PREP_RANGES,
            crash_prob=CRASH_PROB,
        )
        worker.start()
        pizzaioli.append(worker)

    # Factory so the Supervisor can recreate the Coordinator if needed.
    def coordinator_factory() -> Coordinator:
        return Coordinator(
            state_store,
            coord_inbox,
            pizzaiolo_inboxes,
            gui_queue=gui_queue,
            stop_event=stop_event,
            timeout_seconds=TIMEOUT_SECONDS,
            recovery_seconds=RECOVERY_SECONDS,
        )

    supervisor = Supervisor(
        coordinator_queue=coord_inbox,
        coordinator_factory=coordinator_factory,
        stop_event=stop_event,
    )
    supervisor.start()

    order_counter = itertools.count()
    counter_lock = threading.Lock()

    def next_order_id() -> str:
        with counter_lock:
            return f"O{next(order_counter)}"

    def send_new_order() -> None:
        order_id = next_order_id()
        pizza_type = random.choice(PIZZA_TYPES)
        coord_inbox.put(messages.new_order(order_id, pizza_type))

    def start_order_generator() -> None:
        def runner() -> None:
            if ARRIVAL_MODE == "burst":
                for _ in range(TOTAL_ORDERS):
                    send_new_order()
            else:
                for _ in range(TOTAL_ORDERS):
                    send_new_order()
                    time.sleep(random.uniform(1.0, CONTINUOUS_MAX_INTERVAL))

        thread = threading.Thread(target=runner, name="OrderGenerator", daemon=True)
        thread.start()

    def shutdown() -> None:
        if stop_event.is_set():
            return
        stop_event.set()
        coord_inbox.put(messages.shutdown())
        for q in pizzaiolo_inboxes.values():
            q.put(messages.shutdown())

    if AUTO_GENERATE:
        start_order_generator()

    dashboard = Dashboard(
        event_queue=gui_queue,
        pizzaiolo_ids=pizzaiolo_ids,
        on_new_order=send_new_order,
        on_close=shutdown,
    )
    dashboard.run()

    shutdown()
    supervisor.join(timeout=2.0)
    for worker in pizzaioli:
        worker.join(timeout=2.0)


if __name__ == "__main__":
    main()

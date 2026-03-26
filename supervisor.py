from __future__ import annotations

import threading
import time
from queue import Queue
from typing import Callable, Optional

import messages


class Supervisor(threading.Thread):
    """Monitors the Coordinator and restarts it if it stops."""

    def __init__(
        self,
        coordinator_queue: Queue,
        coordinator_factory: Callable[[], threading.Thread],
        stop_event: threading.Event,
        check_interval: float = 1.0,
    ) -> None:
        super().__init__(name="Supervisor", daemon=True)
        self.coordinator_queue = coordinator_queue
        self.coordinator_factory = coordinator_factory
        self.stop_event = stop_event
        self.check_interval = check_interval
        self._coordinator: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def run(self) -> None:
        print("[Supervisor] Started")
        self._start_coordinator()
        while not self.stop_event.is_set():
            with self._lock:
                if self._coordinator is None or not self._coordinator.is_alive():
                    print("[Supervisor] Coordinator crashed -> respawn")
                    self._start_coordinator()
            time.sleep(self.check_interval)
        print("[Supervisor] Stopping")
        self._stop_coordinator()
        print("[Supervisor] Stopped gracefully")

    def _start_coordinator(self) -> None:
        self._coordinator = self.coordinator_factory()
        self._coordinator.start()

    def _stop_coordinator(self) -> None:
        if self._coordinator and self._coordinator.is_alive():
            self.coordinator_queue.put(messages.shutdown())
            self._coordinator.join(timeout=2.0)

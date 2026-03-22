from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any, Deque, Dict, List, Optional

# Pizzaioli statuses
AVAILABLE = "AVAILABLE"
BUSY = "BUSY"
CRASHED = "CRASHED"

# Order statuses
PENDING = "PENDING"
PROCESSING = "PROCESSING"
COMPLETED = "COMPLETED"


@dataclass
class Order:
    order_id: str
    pizza_type: str
    status: str
    created_at: float
    updated_at: float
    assigned_to: Optional[int] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    attempts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Order":
        return Order(**data)


class StateStore:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.pending_queue: Deque[str] = deque()
        self.orders: Dict[str, Order] = {}
        self.pizzaioli: Dict[int, str] = {}

    def initialize(self, pizzaiolo_ids: List[int]) -> None:
        with self.lock:
            if not self.pizzaioli:
                self.pizzaioli = {pid: AVAILABLE for pid in pizzaiolo_ids}

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "pending_queue": list(self.pending_queue),
                "orders": {oid: order.to_dict() for oid, order in self.orders.items()},
                "pizzaioli": dict(self.pizzaioli),
                "saved_at": time.time(),
            }

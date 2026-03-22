from __future__ import annotations

import time
from typing import Any, Dict, Optional

# Message types
ASSIGN = "ASSIGN"
COMPLETE = "COMPLETE"
ACK = "ACK"
NEW_ORDER = "NEW_ORDER"
SHUTDOWN = "SHUTDOWN"

# GUI event types
GUI_STATE = "GUI_STATE"
GUI_LOG = "GUI_LOG"


def now_ts() -> float:
    return time.time()


def assign(order_id: str, pizza_type: str, assigned_at: Optional[float] = None) -> Dict[str, Any]:
    return {
        "type": ASSIGN,
        "order_id": order_id,
        "pizza_type": pizza_type,
        "assigned_at": assigned_at if assigned_at is not None else now_ts(),
    }


def ack(order_id: str) -> Dict[str, Any]:
    return {"type": ACK, "order_id": order_id, "ts": now_ts()}


def complete(pizzaiolo_id: int, order_id: str, completed_at: Optional[float] = None) -> Dict[str, Any]:
    return {
        "type": COMPLETE,
        "pizzaiolo_id": pizzaiolo_id,
        "order_id": order_id,
        "completed_at": completed_at if completed_at is not None else now_ts(),
    }


def new_order(order_id: str, pizza_type: str, created_at: Optional[float] = None) -> Dict[str, Any]:
    return {
        "type": NEW_ORDER,
        "order_id": order_id,
        "pizza_type": pizza_type,
        "created_at": created_at if created_at is not None else now_ts(),
    }


def shutdown() -> Dict[str, Any]:
    return {"type": SHUTDOWN, "ts": now_ts()}


def gui_state(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": GUI_STATE, "snapshot": snapshot, "ts": now_ts()}


def gui_log(message: str) -> Dict[str, Any]:
    return {"type": GUI_LOG, "message": message, "ts": now_ts()}

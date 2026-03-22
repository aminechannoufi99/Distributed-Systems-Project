from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, Iterable

from state import AVAILABLE, BUSY, CRASHED


STATUS_COLORS = {
    AVAILABLE: "#2e7d32",
    BUSY: "#ef6c00",
    CRASHED: "#c62828",
}


class PizzaioliPanel(ttk.Frame):
    def __init__(self, master: tk.Widget, pizzaiolo_ids: Iterable[int]) -> None:
        super().__init__(master)
        title = ttk.Label(self, text="Pizzaioli", font=("Segoe UI", 12, "bold"))
        title.grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))

        self._rows: Dict[int, ttk.Label] = {}
        row = 1
        for pid in pizzaiolo_ids:
            label = ttk.Label(self, text=f"P{pid}: AVAILABLE")
            label.grid(row=row, column=0, sticky="w", padx=12, pady=2)
            self._rows[pid] = label
            row += 1

    def update_statuses(self, statuses: Dict[int, str]) -> None:
        for pid, status in statuses.items():
            label = self._rows.get(pid)
            if not label:
                continue
            color = STATUS_COLORS.get(status, "#424242")
            label.configure(text=f"P{pid}: {status}", foreground=color)


class OrdersPanel(ttk.Frame):
    def __init__(self, master: tk.Widget) -> None:
        super().__init__(master)
        title = ttk.Label(self, text="Orders", font=("Segoe UI", 12, "bold"))
        title.grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))

        columns = ("pizza", "status", "assigned", "attempts")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        self.tree.heading("pizza", text="Pizza")
        self.tree.heading("status", text="Status")
        self.tree.heading("assigned", text="Assigned")
        self.tree.heading("attempts", text="Attempts")
        self.tree.column("pizza", width=140)
        self.tree.column("status", width=120)
        self.tree.column("assigned", width=80, anchor="center")
        self.tree.column("attempts", width=80, anchor="center")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=4)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def update_orders(self, orders: Dict[str, dict]) -> None:
        existing = set(self.tree.get_children(""))
        incoming = set(orders.keys())

        for order_id, data in orders.items():
            assigned_to = data.get("assigned_to")
            assigned_text = f"P{assigned_to}" if assigned_to is not None else "-"
            values = (
                data.get("pizza_type", "-"),
                data.get("status", "-"),
                assigned_text,
                data.get("attempts", 0),
            )
            if order_id in existing:
                self.tree.item(order_id, values=values)
            else:
                self.tree.insert("", "end", iid=order_id, values=values)

        for iid in existing - incoming:
            self.tree.delete(iid)

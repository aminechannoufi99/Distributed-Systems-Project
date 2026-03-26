from __future__ import annotations

import queue
import time
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Iterable

import messages
from gui.panels import OrdersPanel, PizzaioliPanel


class Dashboard:
    """Tkinter dashboard for real-time monitoring."""

    def __init__(
        self,
        event_queue: "queue.Queue",
        pizzaiolo_ids: Iterable[int],
        on_new_order: Callable[[], None],
        on_close: Callable[[], None],
    ) -> None:
        self.event_queue = event_queue
        self.on_new_order = on_new_order
        self.on_close = on_close

        self.root = tk.Tk()
        self.root.title("Pizza Delivery - Monitoring")
        self.root.geometry("940x640")
        self.root.protocol("WM_DELETE_WINDOW", self._handle_close)

        self._setup_style()
        self._build_layout(list(pizzaiolo_ids))

    def run(self) -> None:
        self._poll_events()
        self.root.mainloop()

    def _setup_style(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

    def _build_layout(self, pizzaiolo_ids: Iterable[int]) -> None:
        header = ttk.Frame(self.root)
        header.pack(side="top", fill="x")

        title = ttk.Label(
            header, text="Pizza Delivery System", font=("Segoe UI", 16, "bold")
        )
        title.pack(side="left", padx=12, pady=10)

        controls = ttk.Frame(header)
        controls.pack(side="right", padx=12, pady=10)
        ttk.Button(controls, text="New Order", command=self.on_new_order).grid(
            row=0, column=0, padx=6
        )

        body = ttk.Frame(self.root)
        body.pack(side="top", fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="y")
        right = ttk.Frame(body)
        right.pack(side="right", fill="both", expand=True)

        self.pizzaioli_panel = PizzaioliPanel(left, pizzaiolo_ids)
        self.pizzaioli_panel.pack(side="top", fill="x")

        self.orders_panel = OrdersPanel(right)
        self.orders_panel.pack(side="top", fill="both", expand=True)

        log_frame = ttk.Frame(right)
        log_frame.pack(side="bottom", fill="both", expand=False, padx=8, pady=6)
        ttk.Label(log_frame, text="Coordinator Log", font=("Segoe UI", 11, "bold")).pack(
            side="top", anchor="w"
        )

        self.log_text = tk.Text(log_frame, height=8, wrap="word", state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True)

        log_scroll = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log_text.yview
        )
        log_scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=log_scroll.set)

    def _handle_close(self) -> None:
        self.on_close()
        self.root.destroy()

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.event_queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.root.after(200, self._poll_events)

    def _handle_event(self, event: Dict[str, object]) -> None:
        event_type = event.get("type")
        if event_type == messages.GUI_STATE:
            snapshot = event.get("snapshot", {})
            self._update_state(snapshot)
        elif event_type == messages.GUI_LOG:
            self._append_log(event.get("message", ""))

    def _update_state(self, snapshot: Dict[str, object]) -> None:
        pizzaioli = snapshot.get("pizzaioli", {})
        orders = snapshot.get("orders", {})
        self.pizzaioli_panel.update_statuses(pizzaioli)
        self.orders_panel.update_orders(orders)

    def _append_log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

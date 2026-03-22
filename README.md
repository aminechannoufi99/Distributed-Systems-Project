# Pizza Delivery Distributed System

Run the system with the GUI:

```bash
python main.py
```

Notes:
- The system uses only Python standard library threads and queues.
- By default, orders are manual (GUI button). To auto-generate, set `AUTO_GENERATE = True` in `main.py`.
- Each pizza type has its own preparation time range (see `main.py`).

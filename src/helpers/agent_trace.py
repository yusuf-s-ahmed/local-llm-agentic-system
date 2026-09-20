"""Per-run execution events, delivered synchronously to the UI queue."""

from contextvars import ContextVar
from datetime import datetime


trace_sink = ContextVar("trace_sink", default=None)


def emit_trace(*nodes, status="completed", detail=""):
    event = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "nodes": list(nodes),
        "status": status,
        "detail": detail,
    }
    sink = trace_sink.get()
    if sink:
        sink(event)


def traced_call(agent, operation, function, *args, **kwargs):
    emit_trace(agent, operation, status="running")
    try:
        result = function(*args, **kwargs)
    except Exception as error:
        emit_trace(agent, operation, status="error", detail=str(error))
        raise
    empty = (hasattr(result, "confidence") and result.confidence == 0) or (
        isinstance(result, str) and result.startswith(("ERROR:", "Unable to summarise"))
    ) or (isinstance(result, dict) and bool(result.get("error")))
    emit_trace(operation, agent, status="warning" if empty else "completed",
               detail=str(getattr(result, "reasoning", result)) if empty else "Result received")
    return result

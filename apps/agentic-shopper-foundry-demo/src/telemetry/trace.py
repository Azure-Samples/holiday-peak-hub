from __future__ import annotations

import json
import time
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional, TypeVar


@dataclass
class TraceEvent:
    ts_ms: int
    kind: str
    message: str
    data: Optional[Dict[str, Any]] = None


_current_trace: ContextVar[Optional[List[TraceEvent]]] = ContextVar("_current_trace", default=None)


def start_trace() -> None:
    _current_trace.set([])


def end_trace() -> List[Dict[str, Any]]:
    events = _current_trace.get() or []
    _current_trace.set(None)
    return [asdict(e) for e in events]


def add_event(kind: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
    trace = _current_trace.get()
    if trace is None:
        return
    trace.append(TraceEvent(ts_ms=int(time.time() * 1000), kind=kind, message=message, data=data))


T = TypeVar("T")


def trace_tool(tool_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for tool functions so the UI can show what got called."""

    def _decorator(fn: Callable[..., T]) -> Callable[..., T]:
        def _wrapped(*args: Any, **kwargs: Any) -> T:
            try:
                add_event("tool.call", f"{tool_name}()", {"args": list(args), "kwargs": kwargs})
                result = fn(*args, **kwargs)
                # Keep result small in traces
                preview = result
                if isinstance(result, str) and len(result) > 400:
                    preview = result[:400] + "…"
                add_event("tool.result", f"{tool_name}()", {"result": preview})
                return result
            except Exception as e:  # pragma: no cover
                add_event("tool.error", f"{tool_name}()", {"error": str(e)})
                raise

        _wrapped.__name__ = fn.__name__
        _wrapped.__doc__ = fn.__doc__
        return _wrapped

    return _decorator


def dump_trace_json() -> str:
    events = _current_trace.get() or []
    return json.dumps([asdict(e) for e in events], indent=2)

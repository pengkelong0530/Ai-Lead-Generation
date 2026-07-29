"""Progress callback for streaming status updates (流式反馈 / Streaming).

Provides real-time progress updates during pipeline execution.
Can be consumed by the Streamlit UI or CLI for live status display.

Usage:
    callback = ProgressCallback()
    agent = SupervisorAgent(callbacks=[callback])
    await agent.run_pipeline(...)

    # Or use as context manager
    with ProgressCallback() as cb:
        ...
        cb.on_step("Searching companies...")
"""

from datetime import datetime
from typing import Any, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage


class ProgressCallback(BaseCallbackHandler):
    """Callback handler that records pipeline progress events.

    Stores events in a list for later display. Can also push
    updates to an async queue for real-time streaming.
    """

    def __init__(self, event_queue: Optional[list[dict[str, Any]]] = None) -> None:
        super().__init__()
        self.events: list[dict[str, Any]] = event_queue or []
        self._current_step: str = ""

    # ── Custom step tracking ─────────────────────

    def on_step_start(self, step_name: str, detail: str = "") -> None:
        """Record the start of a pipeline step (Node 1-6)."""
        self._current_step = step_name
        self._add_event("step_start", {
            "step": step_name,
            "detail": detail,
        })

    def on_step_complete(self, step_name: str, result: str = "") -> None:
        """Record the completion of a pipeline step."""
        self._add_event("step_complete", {
            "step": step_name,
            "result": result[:500],
        })

    def on_step_error(self, step_name: str, error: str) -> None:
        """Record an error in a pipeline step."""
        self._add_event("step_error", {
            "step": step_name,
            "error": error,
        })

    def on_message(self, msg: str) -> None:
        """Record an informational message."""
        self._add_event("message", {"text": msg})

    # ── LangChain callback hooks ──────────────────

    def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        self._add_event("llm_start", {
            "step": self._current_step,
        })

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        self._add_event("llm_end", {
            "step": self._current_step,
        })

    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        tool_name = serialized.get("name", "unknown")
        self._add_event("tool_start", {
            "step": self._current_step,
            "tool": tool_name,
            "input": input_str[:200],
        })

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        self._add_event("tool_end", {
            "step": self._current_step,
        })

    def on_tool_error(
        self, error: BaseException, **kwargs: Any
    ) -> None:
        self._add_event("tool_error", {
            "step": self._current_step,
            "error": str(error)[:300],
        })

    def on_chain_start(
        self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any
    ) -> None:
        chain_name = serialized.get("name", "unknown")
        self._add_event("chain_start", {
            "step": self._current_step,
            "chain": chain_name,
        })

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        self._add_event("chain_end", {
            "step": self._current_step,
        })

    # ── Helpers ─────────────────────────────────

    def _add_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Add a timestamped event to the log."""
        self.events.append({
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_progress_report(self) -> str:
        """Generate a human-readable progress report from events."""
        lines = []
        for event in self.events:
            ts = event["timestamp"][11:19]  # HH:MM:SS
            data = event["data"]
            t = event["type"]

            if t == "step_start":
                detail = data.get("detail", "")
                lines.append(f"\n[{ts}] 🔄 {data['step']} {detail}")
            elif t == "step_complete":
                lines.append(f"[{ts}] ✅ {data['step']}")
            elif t == "step_error":
                lines.append(f"[{ts}] ❌ {data['step']}: {data['error']}")
            elif t == "message":
                lines.append(f"[{ts}] 💬 {data['text']}")
            elif t == "tool_start":
                lines.append(f"[{ts}]   🔧 {data['tool']}")
            elif t == "tool_error":
                lines.append(f"[{ts}]   ⚠️ Tool error: {data['error']}")

        return "\n".join(lines)

    def get_last_n_events(self, n: int = 5) -> list[dict[str, Any]]:
        """Get the last N events for live display."""
        return self.events[-n:]

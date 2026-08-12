from datetime import datetime

class ActivityLog:
    """Formats events into log text and holds the running buffer. No Qt here."""

    def __init__(self, max_lines: int = 500):
        self._lines: list[str] = []
        self._max_lines = max_lines

    def add(self, kind: str, payload) -> str:
        self._lines.append(self._format(kind, payload))
        self._lines = self._lines[-self._max_lines:]
        return self.text

    @property
    def text(self) -> str:
        return "\n".join(reversed(self._lines))

    def _format(self, kind: str, payload) -> str:
        ts = datetime.now().strftime("%H:%M:%S")
        match kind:
            case 'status':
                body = ", ".join(f"{k}={v}" for k, v in payload.items())
            case 'ok':
                body = "ok"
            case 'error' | 'line':
                body = payload
            case _:
                body = str(payload)
        return f"[{ts}] {body}"

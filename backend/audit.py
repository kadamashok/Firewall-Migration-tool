from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_DIR = Path("backend/audit")
AUDIT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG = AUDIT_DIR / "audit.log"


def write_audit(event: str, actor: str, payload: dict[str, Any] | None = None) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "actor": actor,
        "payload": payload or {},
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

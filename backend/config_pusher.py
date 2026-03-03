from __future__ import annotations

import os
from typing import Any

from config_extractor import get_adapter


def push_to_destination(vendor: str, push_fn: Any, transformed_config: dict, dry_run: bool) -> list[str]:
    logs: list[str] = []
    prefer_api = os.getenv("PREFER_API_PUSH", "true").lower() == "true"
    api_enabled = os.getenv("DEVICE_API_ENABLED", "false").lower() == "true"
    if prefer_api and not api_enabled:
        logs.append("API disabled on destination. Falling back to SSH CLI push.")

    adapter = get_adapter(vendor)
    if adapter:
        return logs + adapter.push_config(push_fn, transformed_config, dry_run)
    commands = transformed_config.get("commands", [])
    if dry_run:
        return logs + [f"DRY-RUN: would push {len(commands)} commands to destination"]
    push_fn(commands)
    return logs + [f"Pushed {len(commands)} commands to destination"]

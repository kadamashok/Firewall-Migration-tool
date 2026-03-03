from __future__ import annotations

from typing import Iterable

from models import DeviceInfo
from vendors import VENDOR_ADAPTERS

DETECT_COMMANDS = ["show version", "get system status", "show system info"]


def detect_device(run_command, commands: Iterable[str] = DETECT_COMMANDS) -> DeviceInfo:
    outputs: dict[str, str] = {}
    for cmd in commands:
        try:
            outputs[cmd] = run_command(cmd)
        except Exception:
            outputs[cmd] = ""

    for adapter in VENDOR_ADAPTERS:
        facts = adapter.detect(outputs)
        if facts:
            return DeviceInfo(
                vendor=facts.vendor,
                model=facts.model,
                os_version=facts.os_version,
                raw_output=facts.raw_output,
            )

    raw = "\n".join(outputs.values())
    low = raw.lower()
    if "sophos" in low:
        vendor = "Sophos"
    else:
        vendor = "Unknown"
    return DeviceInfo(vendor=vendor, model="Unknown", os_version="Unknown", raw_output=raw)

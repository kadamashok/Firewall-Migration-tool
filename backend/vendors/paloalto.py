from __future__ import annotations

from typing import Any

from .base import DeviceFacts, VendorAdapter


class PaloAltoAdapter(VendorAdapter):
    name = "paloalto"

    def detect(self, command_outputs: dict[str, str]) -> DeviceFacts | None:
        combined = "\n".join(command_outputs.values()).lower()
        if "palo alto" not in combined and "pan-os" not in combined:
            return None
        model = "Unknown"
        os_version = "Unknown"
        raw = "\n".join(command_outputs.values())
        for line in raw.splitlines():
            low = line.lower()
            if "model" in low and ":" in line:
                model = line.split(":", 1)[1].strip()
            if "sw-version" in low or "pan-os" in low:
                os_version = line.split(":")[-1].strip()
        return DeviceFacts(vendor="Palo Alto", model=model, os_version=os_version, raw_output=raw)

    def extract_config(self, run_command: Any) -> dict[str, Any]:
        return {
            "interfaces": run_command("show interface all"),
            "zones": run_command("show zone all"),
            "address_objects": run_command("show address all"),
            "service_objects": run_command("show service all"),
            "policies": run_command("show running security-policy"),
            "nat": run_command("show running nat-policy"),
            "vpn": run_command("show running vpn"),
            "static_routes": run_command("show routing route"),
        }

    def push_config(self, push_fn: Any, transformed_config: dict[str, Any], dry_run: bool) -> list[str]:
        commands = transformed_config.get("commands", [])
        if dry_run:
            return [f"DRY-RUN: would push {len(commands)} commands to Palo Alto"]
        if commands:
            push_fn(commands)
            push_fn(["commit"])
        return [f"Pushed {len(commands)} commands and committed on Palo Alto"]

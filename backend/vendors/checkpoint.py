from __future__ import annotations

from typing import Any

from .base import DeviceFacts, VendorAdapter


class CheckPointAdapter(VendorAdapter):
    name = "checkpoint"

    def detect(self, command_outputs: dict[str, str]) -> DeviceFacts | None:
        raw = "\n".join(command_outputs.values())
        low = raw.lower()
        if "checkpoint" not in low and "gaia" not in low:
            return None
        model = "Unknown"
        os_version = "Unknown"
        for line in raw.splitlines():
            l = line.lower()
            if "model" in l and ":" in line:
                model = line.split(":", 1)[1].strip()
            if "version" in l:
                os_version = line.strip()
        return DeviceFacts(vendor="CheckPoint", model=model, os_version=os_version, raw_output=raw)

    def extract_config(self, run_command: Any) -> dict[str, Any]:
        return {
            "interfaces": run_command("show interfaces all"),
            "zones": run_command("show configuration security-zone"),
            "address_objects": run_command("show configuration objects network"),
            "service_objects": run_command("show configuration objects services"),
            "policies": run_command("show configuration access-policy"),
            "nat": run_command("show configuration nat"),
            "vpn": run_command("show configuration vpn"),
            "static_routes": run_command("show route static"),
        }

    def push_config(self, push_fn: Any, transformed_config: dict[str, Any], dry_run: bool) -> list[str]:
        commands = transformed_config.get("commands", [])
        if dry_run:
            return [f"DRY-RUN: would push {len(commands)} commands to CheckPoint"]
        if commands:
            push_fn(commands)
            push_fn(["save config"])
        return [f"Pushed {len(commands)} commands and saved on CheckPoint"]

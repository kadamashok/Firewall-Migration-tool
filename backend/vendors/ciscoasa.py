from __future__ import annotations

from typing import Any

from .base import DeviceFacts, VendorAdapter


class CiscoAsaAdapter(VendorAdapter):
    name = "ciscoasa"

    def detect(self, command_outputs: dict[str, str]) -> DeviceFacts | None:
        raw = "\n".join(command_outputs.values())
        low = raw.lower()
        if "cisco adaptive security appliance" not in low and "asa version" not in low:
            return None
        model = "Unknown"
        os_version = "Unknown"
        for line in raw.splitlines():
            l = line.lower()
            if "hardware:" in l:
                model = line.split(":", 1)[-1].strip()
            if "asa version" in l:
                os_version = line.strip()
        return DeviceFacts(vendor="Cisco ASA", model=model, os_version=os_version, raw_output=raw)

    def extract_config(self, run_command: Any) -> dict[str, Any]:
        return {
            "interfaces": run_command("show interface ip brief"),
            "zones": run_command("show run access-group"),
            "address_objects": run_command("show run object network"),
            "service_objects": run_command("show run object service"),
            "policies": run_command("show run access-list"),
            "nat": run_command("show run nat"),
            "vpn": run_command("show run tunnel-group"),
            "static_routes": run_command("show route"),
        }

    def push_config(self, push_fn: Any, transformed_config: dict[str, Any], dry_run: bool) -> list[str]:
        commands = transformed_config.get("commands", [])
        if dry_run:
            return [f"DRY-RUN: would push {len(commands)} commands to Cisco ASA"]
        if commands:
            push_fn(["configure terminal", *commands, "write memory"])
        return [f"Pushed {len(commands)} commands and saved on Cisco ASA"]

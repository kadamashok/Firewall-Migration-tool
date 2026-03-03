from __future__ import annotations

from typing import Any

from .base import DeviceFacts, VendorAdapter


class FortinetAdapter(VendorAdapter):
    name = "fortinet"

    def detect(self, command_outputs: dict[str, str]) -> DeviceFacts | None:
        raw = "\n".join(command_outputs.values())
        low = raw.lower()
        if "fortinet" not in low and "fortios" not in low:
            return None
        model = "Unknown"
        os_version = "Unknown"
        for line in raw.splitlines():
            l = line.lower()
            if "version" in l and "fortios" in l:
                os_version = line.strip()
            if "model name" in l and ":" in line:
                model = line.split(":", 1)[1].strip()
        return DeviceFacts(vendor="Fortinet", model=model, os_version=os_version, raw_output=raw)

    def extract_config(self, run_command: Any) -> dict[str, Any]:
        return {
            "interfaces": run_command("show system interface"),
            "zones": run_command("show system zone"),
            "address_objects": run_command("show firewall address"),
            "service_objects": run_command("show firewall service custom"),
            "policies": run_command("show firewall policy"),
            "nat": run_command("show firewall ippool"),
            "vpn": run_command("show vpn ipsec phase1-interface"),
            "static_routes": run_command("show router static"),
        }

    def push_config(self, push_fn: Any, transformed_config: dict[str, Any], dry_run: bool) -> list[str]:
        commands = transformed_config.get("commands", [])
        if dry_run:
            return [f"DRY-RUN: would push {len(commands)} commands to Fortinet"]
        if commands:
            push_fn(["config global", *commands, "end"])
        return [f"Pushed {len(commands)} commands on Fortinet"]

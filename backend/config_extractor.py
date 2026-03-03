from __future__ import annotations

from typing import Any

from vendors import VENDOR_ADAPTERS


def get_adapter(vendor: str):
    for adapter in VENDOR_ADAPTERS:
        if adapter.name.lower() in vendor.lower().replace(" ", ""):
            return adapter
    return None


def extract_full_config(vendor: str, run_command: Any) -> dict[str, Any]:
    adapter = get_adapter(vendor)
    if adapter:
        return adapter.extract_config(run_command)
    return {
        "interfaces": run_command("show interfaces"),
        "zones": "",
        "address_objects": run_command("show run | include object"),
        "service_objects": run_command("show run | include service"),
        "policies": run_command("show run | include access-list"),
        "nat": run_command("show run | include nat"),
        "vpn": run_command("show run | include vpn"),
        "static_routes": run_command("show route"),
    }


def backup_destination(vendor: str, run_command: Any) -> dict[str, Any]:
    adapter = get_adapter(vendor)
    if adapter:
        return adapter.backup_config(run_command)
    return {"running_config": run_command("show running-config")}

from __future__ import annotations

from typing import Any

from models import DeviceInfo


def normalize_config(extracted: dict[str, Any]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for key, value in extracted.items():
        if isinstance(value, str):
            normalized[key] = [line.strip() for line in value.splitlines() if line.strip()]
        elif isinstance(value, list):
            normalized[key] = [str(v).strip() for v in value if str(v).strip()]
        else:
            normalized[key] = [str(value)]
    return normalized


def transform_config(source: DeviceInfo, destination: DeviceInfo, extracted: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_config(extracted)
    commands: list[str] = []

    for item in normalized.get("address_objects", [])[:200]:
        commands.append(f"! mapped-address {item}")
    for item in normalized.get("service_objects", [])[:200]:
        commands.append(f"! mapped-service {item}")
    for item in normalized.get("policies", [])[:500]:
        commands.append(f"! mapped-policy {item}")
    for item in normalized.get("nat", [])[:200]:
        commands.append(f"! mapped-nat {item}")
    for item in normalized.get("static_routes", [])[:100]:
        commands.append(f"! mapped-route {item}")

    metadata = {
        "source_vendor": source.vendor,
        "destination_vendor": destination.vendor,
        "source_os": source.os_version,
        "destination_os": destination.os_version,
    }
    return {"commands": commands, "metadata": metadata, "normalized": normalized}

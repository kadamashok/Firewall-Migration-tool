from __future__ import annotations

import re

from models import CompatibilityIssue, CompatibilityResult, DeviceInfo


def _major(version: str) -> int | None:
    m = re.search(r"(\d+)", version)
    if not m:
        return None
    return int(m.group(1))


def check_compatibility(source: DeviceInfo, destination: DeviceInfo) -> CompatibilityResult:
    issues: list[CompatibilityIssue] = []
    matrix = {
        "address_objects": "mapped",
        "service_objects": "mapped",
        "security_policies": "mapped",
        "nat_rules": "mapped",
        "vpn_config": "partial",
    }

    if source.vendor == "Unknown" or destination.vendor == "Unknown":
        issues.append(
            CompatibilityIssue(
                category="Detection",
                severity="high",
                message="Unable to identify one or both devices. Compatibility check is incomplete.",
            )
        )
        return CompatibilityResult(
            compatible=False,
            score=20,
            mode="unknown",
            issues=issues,
            conversion_matrix=matrix,
        )

    if source.vendor == destination.vendor:
        mode = "native"
        s_major = _major(source.os_version)
        d_major = _major(destination.os_version)
        score = 95
        if s_major and d_major and abs(s_major - d_major) > 2:
            issues.append(
                CompatibilityIssue(
                    category="Firmware",
                    severity="medium",
                    message=f"Major firmware gap detected: source {source.os_version} vs destination {destination.os_version}",
                )
            )
            score = 75
        if "Unknown" in (source.model, destination.model):
            issues.append(
                CompatibilityIssue(
                    category="Model",
                    severity="low",
                    message="Model detection incomplete; object limits cannot be fully validated.",
                )
            )
            score -= 10
        return CompatibilityResult(
            compatible=True,
            score=max(score, 0),
            mode=mode,
            issues=issues,
            conversion_matrix=matrix,
        )

    mode = "policy-conversion"
    issues.extend(
        [
            CompatibilityIssue(
                category="Cross-vendor",
                severity="medium",
                message=f"{source.vendor} to {destination.vendor} requires syntax and feature mapping.",
            ),
            CompatibilityIssue(
                category="VPN",
                severity="medium",
                message="VPN settings may need manual re-keying and crypto-suite validation.",
            ),
        ]
    )
    matrix["vpn_config"] = "manual-review"
    return CompatibilityResult(
        compatible=True,
        score=68,
        mode=mode,
        issues=issues,
        conversion_matrix=matrix,
    )

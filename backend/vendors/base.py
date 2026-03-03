from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DeviceFacts:
    vendor: str
    model: str
    os_version: str
    raw_output: str


class VendorAdapter:
    name: str = "generic"

    def detect(self, command_outputs: dict[str, str]) -> DeviceFacts | None:
        raise NotImplementedError

    def extract_config(self, run_command: Any) -> dict[str, Any]:
        raise NotImplementedError

    def backup_config(self, run_command: Any) -> dict[str, Any]:
        return self.extract_config(run_command)

    def push_config(self, push_fn: Any, transformed_config: dict[str, Any], dry_run: bool) -> list[str]:
        raise NotImplementedError

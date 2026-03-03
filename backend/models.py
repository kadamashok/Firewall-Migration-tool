from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, IPvAnyAddress


class FirewallEndpoint(BaseModel):
    ip: IPvAnyAddress
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    ssh_port: int = Field(default=22, ge=1, le=65535)


class EncryptedFirewallEndpoint(BaseModel):
    ip: str
    username: str
    encrypted_password: str
    ssh_port: int = 22


class ConnectivityResult(BaseModel):
    ok: bool
    error: str | None = None
    detail: str | None = None


class DeviceInfo(BaseModel):
    vendor: str
    model: str
    os_version: str
    raw_output: str | None = None


class CompatibilityIssue(BaseModel):
    category: str
    severity: str
    message: str


class CompatibilityResult(BaseModel):
    compatible: bool
    score: int = Field(ge=0, le=100)
    mode: str
    issues: list[CompatibilityIssue]
    conversion_matrix: dict[str, str]


class MigrationRequest(BaseModel):
    source: FirewallEndpoint
    destination: FirewallEndpoint
    dry_run: bool = True
    notify_email: str | None = None


class MigrationJobStatus(BaseModel):
    job_id: str
    status: str
    progress: int = Field(ge=0, le=100)
    logs: list[str]
    source_device: DeviceInfo | None = None
    destination_device: DeviceInfo | None = None
    compatibility: CompatibilityResult | None = None
    report_id: str | None = None
    updated_at: datetime
    result: dict[str, Any] | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

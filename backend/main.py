from __future__ import annotations

import smtplib
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from threading import Lock
from typing import Any, Annotated

from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from audit import write_audit
from compatibility_engine import check_compatibility
from config_extractor import backup_destination, extract_full_config
from config_pusher import push_to_destination
from device_detector import detect_device
from device_transport import (
    DeviceAuthenticationError,
    DeviceConnectionError,
    DeviceCredentials,
    SSHTransport,
    ping_tcp,
)
from models import (
    CompatibilityResult,
    ConnectivityResult,
    DeviceInfo,
    EncryptedFirewallEndpoint,
    FirewallEndpoint,
    LoginRequest,
    LoginResponse,
    MigrationJobStatus,
    MigrationRequest,
)
from report_generator import generate_json_report, generate_pdf_report
from security import (
    User,
    authenticate_user,
    create_access_token,
    decrypt_secret,
    encrypt_secret,
    get_current_user,
    require_role,
)
from transformer import transform_config

app = FastAPI(title="Firewall Migration Tool", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs: dict[str, MigrationJobStatus] = {}
job_lock = Lock()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def set_job(job_id: str, **kwargs: Any) -> None:
    with job_lock:
        current = jobs[job_id]
        merged = current.model_dump()
        merged.update(kwargs)
        merged["updated_at"] = utc_now()
        jobs[job_id] = MigrationJobStatus(**merged)


def add_log(job_id: str, message: str) -> None:
    with job_lock:
        current = jobs[job_id]
        logs = list(current.logs)
        logs.append(message)
        jobs[job_id] = current.model_copy(update={"logs": logs, "updated_at": utc_now()})


def encrypt_endpoint(endpoint: FirewallEndpoint) -> EncryptedFirewallEndpoint:
    return EncryptedFirewallEndpoint(
        ip=str(endpoint.ip),
        username=endpoint.username,
        encrypted_password=encrypt_secret(endpoint.password),
        ssh_port=endpoint.ssh_port,
    )


def to_creds(ep: EncryptedFirewallEndpoint) -> DeviceCredentials:
    return DeviceCredentials(
        ip=ep.ip,
        username=ep.username,
        password=decrypt_secret(ep.encrypted_password),
        ssh_port=ep.ssh_port,
    )


def check_connectivity(endpoint: FirewallEndpoint) -> ConnectivityResult:
    ip = str(endpoint.ip)
    if not ping_tcp(ip, endpoint.ssh_port):
        return ConnectivityResult(ok=False, error="Device unreachable", detail=f"{ip}:{endpoint.ssh_port} not reachable")
    try:
        with SSHTransport(DeviceCredentials(ip=ip, username=endpoint.username, password=endpoint.password, ssh_port=endpoint.ssh_port)):
            pass
        return ConnectivityResult(ok=True, detail="SSH connectivity successful")
    except DeviceAuthenticationError:
        return ConnectivityResult(ok=False, error="Authentication failed", detail="Invalid username or password")
    except DeviceConnectionError as exc:
        return ConnectivityResult(ok=False, error="Device unreachable", detail=str(exc))


def detect_endpoint(endpoint: FirewallEndpoint) -> DeviceInfo:
    with SSHTransport(DeviceCredentials(ip=str(endpoint.ip), username=endpoint.username, password=endpoint.password, ssh_port=endpoint.ssh_port)) as ssh:
        return detect_device(ssh.run_command)


def send_notification(email_to: str, subject: str, body: str) -> None:
    smtp_host = "localhost"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "firewall-migration@localhost"
    msg["To"] = email_to
    msg.set_content(body)
    with smtplib.SMTP(smtp_host, 25, timeout=8) as smtp:
        smtp.send_message(msg)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication failed")
    token = create_access_token({"sub": user.username, "role": user.role})
    return LoginResponse(access_token=token, role=user.role)


@app.post("/connectivity-test")
def connectivity_test(
    endpoint: FirewallEndpoint,
    user: Annotated[User, Depends(get_current_user)],
) -> ConnectivityResult:
    require_role(user, {"Admin", "Operator"})
    result = check_connectivity(endpoint)
    write_audit("connectivity_test", user.username, {"ip": str(endpoint.ip), "ok": result.ok})
    return result


@app.post("/detect-device")
def detect_device_endpoint(
    endpoint: FirewallEndpoint,
    user: Annotated[User, Depends(get_current_user)],
) -> DeviceInfo:
    require_role(user, {"Admin", "Operator"})
    try:
        info = detect_endpoint(endpoint)
    except DeviceAuthenticationError as exc:
        raise HTTPException(status_code=401, detail="Authentication failed") from exc
    except DeviceConnectionError as exc:
        raise HTTPException(status_code=400, detail=f"Device unreachable: {exc}") from exc
    write_audit("device_detected", user.username, {"ip": str(endpoint.ip), "vendor": info.vendor})
    return info


@app.post("/check-compatibility")
def compatibility_check(
    request: MigrationRequest,
    user: Annotated[User, Depends(get_current_user)],
) -> CompatibilityResult:
    require_role(user, {"Admin", "Operator"})
    src_info = detect_endpoint(request.source)
    dst_info = detect_endpoint(request.destination)
    result = check_compatibility(src_info, dst_info)
    write_audit(
        "compatibility_check",
        user.username,
        {"source_vendor": src_info.vendor, "destination_vendor": dst_info.vendor, "score": result.score},
    )
    return result


def run_migration_job(
    job_id: str,
    source: EncryptedFirewallEndpoint,
    destination: EncryptedFirewallEndpoint,
    dry_run: bool,
    actor: str,
    notify_email: str | None,
) -> None:
    try:
        set_job(job_id, status="running", progress=5)
        add_log(job_id, "Step 1: Testing source connectivity")
        src_fw = FirewallEndpoint(ip=source.ip, username=source.username, password=decrypt_secret(source.encrypted_password), ssh_port=source.ssh_port)
        dst_fw = FirewallEndpoint(ip=destination.ip, username=destination.username, password=decrypt_secret(destination.encrypted_password), ssh_port=destination.ssh_port)
        src_conn = check_connectivity(src_fw)
        if not src_conn.ok:
            raise RuntimeError(src_conn.error or "Source connectivity failed")
        add_log(job_id, "Step 1: Testing destination connectivity")
        dst_conn = check_connectivity(dst_fw)
        if not dst_conn.ok:
            raise RuntimeError(dst_conn.error or "Destination connectivity failed")

        set_job(job_id, progress=15)
        add_log(job_id, "Step 2: Detecting devices")
        with SSHTransport(to_creds(source)) as src_ssh:
            src_info = detect_device(src_ssh.run_command)
        with SSHTransport(to_creds(destination)) as dst_ssh:
            dst_info = detect_device(dst_ssh.run_command)
        set_job(job_id, source_device=src_info, destination_device=dst_info, progress=25)

        add_log(job_id, "Step 3: Running compatibility engine")
        compatibility = check_compatibility(src_info, dst_info)
        set_job(job_id, compatibility=compatibility, progress=35)
        if not compatibility.compatible:
            add_log(job_id, "Incompatible devices. Migration stopped.")
            report_id = str(uuid.uuid4())
            payload = {
                "status": "incompatible",
                "source": src_info.model_dump(),
                "destination": dst_info.model_dump(),
                "compatibility": compatibility.model_dump(),
                "issues": [i.model_dump() for i in compatibility.issues],
                "summary": "Compatibility check failed. See issue list.",
            }
            generate_json_report(report_id, payload)
            generate_pdf_report(report_id, payload)
            set_job(job_id, status="failed", progress=100, report_id=report_id, result=payload)
            return

        add_log(job_id, "Step 4: Extracting source configuration")
        with SSHTransport(to_creds(source)) as src_ssh:
            extracted = extract_full_config(src_info.vendor, src_ssh.run_command)
        set_job(job_id, progress=50)

        add_log(job_id, "Step 5: Transforming configuration")
        transformed = transform_config(src_info, dst_info, extracted)
        set_job(job_id, progress=65)

        add_log(job_id, "Step 6: Backing up destination configuration")
        with SSHTransport(to_creds(destination)) as dst_ssh:
            backup = backup_destination(dst_info.vendor, dst_ssh.run_command)
        set_job(job_id, progress=75)

        add_log(job_id, "Step 6: Pushing configuration")
        with SSHTransport(to_creds(destination)) as dst_ssh:
            push_logs = push_to_destination(dst_info.vendor, dst_ssh.push_commands, transformed, dry_run)
        for item in push_logs:
            add_log(job_id, item)
        set_job(job_id, progress=90)

        add_log(job_id, "Step 7: Post-migration validation")
        extracted_policy_count = len(transformed.get("normalized", {}).get("policies", []))
        with SSHTransport(to_creds(destination)) as dst_ssh:
            destination_routes = dst_ssh.run_command("show route")
        summary = (
            f"Migration {'dry-run ' if dry_run else ''}completed. "
            f"Mapped policy entries: {extracted_policy_count}. "
            f"Compatibility score: {compatibility.score}."
        )
        report_id = str(uuid.uuid4())
        payload = {
            "status": "success",
            "source": src_info.model_dump(),
            "destination": dst_info.model_dump(),
            "compatibility": compatibility.model_dump(),
            "dry_run": dry_run,
            "backup": backup,
            "summary": summary,
            "validation": {
                "mapped_policy_count": extracted_policy_count,
                "mapped_address_count": len(transformed.get("normalized", {}).get("address_objects", [])),
                "mapped_service_count": len(transformed.get("normalized", {}).get("service_objects", [])),
                "route_snapshot_lines": len([x for x in destination_routes.splitlines() if x.strip()]),
            },
        }
        generate_json_report(report_id, payload)
        generate_pdf_report(report_id, payload)
        set_job(job_id, status="completed", progress=100, report_id=report_id, result=payload)
        write_audit("migration_completed", actor, {"job_id": job_id, "report_id": report_id, "dry_run": dry_run})

        if notify_email:
            try:
                send_notification(notify_email, "Firewall Migration Completed", f"Job {job_id} completed.\nReport: {report_id}")
                add_log(job_id, f"Email notification sent to {notify_email}")
            except Exception as exc:
                add_log(job_id, f"Email notification failed: {exc}")
    except Exception as exc:
        set_job(job_id, status="failed", progress=100)
        add_log(job_id, f"Migration failed: {exc}")
        write_audit("migration_failed", actor, {"job_id": job_id, "error": str(exc)})


@app.post("/start-migration")
def start_migration(
    request: MigrationRequest,
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    require_role(user, {"Admin", "Operator"})
    job_id = str(uuid.uuid4())
    jobs[job_id] = MigrationJobStatus(
        job_id=job_id,
        status="queued",
        progress=0,
        logs=["Job queued"],
        updated_at=utc_now(),
    )
    enc_src = encrypt_endpoint(request.source)
    enc_dst = encrypt_endpoint(request.destination)
    background_tasks.add_task(
        run_migration_job,
        job_id,
        enc_src,
        enc_dst,
        request.dry_run,
        user.username,
        request.notify_email,
    )
    write_audit("migration_started", user.username, {"job_id": job_id, "dry_run": request.dry_run})
    return {"job_id": job_id}


@app.post("/dry-run")
def dry_run_migration(
    request: MigrationRequest,
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    require_role(user, {"Admin", "Operator"})
    request.dry_run = True
    return start_migration(request, background_tasks, user)


@app.get("/jobs/{job_id}", response_model=MigrationJobStatus)
def get_job(job_id: str, user: Annotated[User, Depends(get_current_user)]) -> MigrationJobStatus:
    require_role(user, {"Admin", "Operator"})
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/reports/{report_id}/json")
def download_json_report(report_id: str, user: Annotated[User, Depends(get_current_user)]):
    require_role(user, {"Admin", "Operator"})
    file_path = Path(f"backend/reports/{report_id}.json")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="JSON report not found")
    return FileResponse(str(file_path), media_type="application/json", filename=f"{report_id}.json")


@app.get("/reports/{report_id}/pdf")
def download_pdf_report(report_id: str, user: Annotated[User, Depends(get_current_user)]):
    require_role(user, {"Admin", "Operator"})
    file_path = Path(f"backend/reports/{report_id}.pdf")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF report not found")
    return FileResponse(str(file_path), media_type="application/pdf", filename=f"{report_id}.pdf")


@app.post("/rollback/{job_id}")
def rollback(job_id: str, user: Annotated[User, Depends(get_current_user)]) -> dict[str, str]:
    require_role(user, {"Admin"})
    job = jobs.get(job_id)
    if not job or not job.result:
        raise HTTPException(status_code=404, detail="No backup associated with this job")
    write_audit("rollback_requested", user.username, {"job_id": job_id})
    return {"status": "Rollback stub prepared. Implement vendor-specific restore using backup payload."}


@app.post("/bulk-migration")
def bulk_migration(
    requests: list[MigrationRequest],
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    require_role(user, {"Admin"})
    job_ids: list[str] = []
    for req in requests:
        response = start_migration(req, background_tasks, user)
        job_ids.append(response["job_id"])
    write_audit("bulk_migration_started", user.username, {"count": len(job_ids)})
    return {"job_ids": job_ids, "count": len(job_ids)}

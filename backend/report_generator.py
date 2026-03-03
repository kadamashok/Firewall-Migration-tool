from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

REPORT_DIR = Path("backend/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def generate_json_report(report_id: str, payload: dict[str, Any]) -> Path:
    path = REPORT_DIR / f"{report_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def generate_pdf_report(report_id: str, payload: dict[str, Any]) -> Path:
    path = REPORT_DIR / f"{report_id}.pdf"
    c = canvas.Canvas(str(path), pagesize=LETTER)
    width, height = LETTER
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Firewall Migration Summary")
    c.setFont("Helvetica", 10)
    y -= 25

    def line(text: str):
        nonlocal y
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)
        c.drawString(50, y, text[:130])
        y -= 14

    source = payload.get("source", {})
    destination = payload.get("destination", {})
    compatibility = payload.get("compatibility", {})
    issues = compatibility.get("issues", [])

    line(f"Source: {source.get('vendor')} / {source.get('model')} / {source.get('os_version')}")
    line(f"Destination: {destination.get('vendor')} / {destination.get('model')} / {destination.get('os_version')}")
    line(f"Compatibility Score: {compatibility.get('score', 'N/A')}")
    line(f"Status: {payload.get('status', 'Unknown')}")
    line("Issues Found:")
    for issue in issues:
        line(f"- [{issue.get('severity')}] {issue.get('category')}: {issue.get('message')}")
    line("Summary:")
    line(payload.get("summary", "No summary available"))
    c.save()
    return path

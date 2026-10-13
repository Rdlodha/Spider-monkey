"""Report generation service for ReconForge.

Generates comprehensive Markdown and PDF assessment reports.
Supports:
- Redaction of sensitive tokens, passwords, API keys, and hashes in evidence.
- Optional exclusion of FALSE_POSITIVE findings.
- Escaping text before inserting into Markdown/HTML.
- Direct PDF compilation using ReportLab.
"""

from __future__ import annotations

import io
import re
import html
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.base import Project, Target, Host, Service, Endpoint, Finding, FindingLink, Evidence, ChecklistProgress, ChecklistTemplateItem, ScopeEntry

# Regex patterns for token/password redaction
REDACTION_PATTERNS = [
    (re.compile(r'(?i)(password|passwd|pwd|secret|api_key|token|bearer)\s*[:=]\s*["\']?([^"\'\s&]+)["\']?'), r'\1=[REDACTED]'),
    (re.compile(r'(?i)bearer\s+[a-zA-Z0-9_\-\.]{15,}'), 'Bearer [REDACTED]'),
    (re.compile(r'ghp_[a-zA-Z0-9]{36}'), 'ghp_[REDACTED]'),
    (re.compile(r'eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}'), '[JWT-REDACTED]'),
]


def redact_sensitive(text: Optional[str]) -> str:
    """Mask credentials, tokens, and authorization headers in evidence or text."""
    if not text:
        return ""
    result = str(text)
    for pattern, replacement in REDACTION_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def escape_md(text: Optional[str]) -> str:
    """Sanitize and escape text before Markdown rendering."""
    if not text:
        return ""
    # Strip dangerous HTML tags
    clean = html.escape(str(text))
    return clean


def compile_project_report_data(
    db: Session,
    project_id: str,
    exclude_false_positives: bool = True,
    redact_evidence: bool = True,
) -> Dict[str, Any]:
    """Gather and structure all project assets, scope, findings, and methodology checklist."""
    project = db.get(Project, project_id)
    if not project:
        raise ValueError("Project not found")

    scopes = db.query(ScopeEntry).filter(ScopeEntry.project_id == project_id).all()
    targets = db.query(Target).filter(Target.project_id == project_id).all()
    hosts = db.query(Host).filter(Host.project_id == project_id).all()
    endpoints = db.query(Endpoint).filter(Endpoint.project_id == project_id).all()

    findings_query = db.query(Finding).filter(Finding.project_id == project_id)
    if exclude_false_positives:
        findings_query = findings_query.filter(Finding.status != "FALSE_POSITIVE")
    findings = findings_query.order_by(Finding.created_at.desc()).all()

    checklist_items = (
        db.query(ChecklistProgress, ChecklistTemplateItem)
        .join(ChecklistTemplateItem, ChecklistProgress.template_item_id == ChecklistTemplateItem.id)
        .join(Target, ChecklistProgress.target_id == Target.id)
        .filter(Target.project_id == project_id)
        .order_by(ChecklistTemplateItem.sort_order)
        .all()
    )

    # Calculate summary metrics
    sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for f in findings:
        sev = f.severity.upper() if f.severity else "INFO"
        sev_counts[sev] = sev_counts.get(sev, 0) + 1

    checklist_summary = {"TOTAL": len(checklist_items), "COMPLETED": 0, "IN_PROGRESS": 0, "NOT_STARTED": 0}
    for prog, item in checklist_items:
        st = prog.state
        if st in checklist_summary:
            checklist_summary[st] += 1

    processed_findings = []
    for f in findings:
        processed_ev = []
        for ev in f.evidence:
            ev_text = ev.text or ""
            if redact_evidence:
                ev_text = redact_sensitive(ev_text)
            processed_ev.append({
                "kind": ev.kind,
                "text": escape_md(ev_text),
                "original_filename": ev.original_filename,
                "created_at": ev.created_at.strftime("%Y-%m-%d %H:%M") if ev.created_at else "",
            })

        processed_findings.append({
            "id": f.id,
            "title": escape_md(f.title),
            "severity": f.severity,
            "status": f.status,
            "description": escape_md(f.description),
            "notes": escape_md(f.notes),
            "evidence": processed_ev,
        })

    return {
        "project": {
            "name": escape_md(project.name),
            "id": project.id,
            "created_at": project.created_at.strftime("%Y-%m-%d %H:%M") if project.created_at else "",
            "authorized_ack_at": project.authorized_ack_at.strftime("%Y-%m-%d %H:%M") if project.authorized_ack_at else "Not recorded",
        },
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "scopes": [{"type": s.type, "value": escape_md(s.value)} for s in scopes],
        "targets": [{"value": escape_md(t.value), "created_at": str(t.created_at)} for t in targets],
        "hosts": [
            {
                "ip": h.ip,
                "hostname": escape_md(h.hostname) or "—",
                "is_interesting": h.is_interesting,
                "services": [
                    {"port": s.port, "protocol": s.protocol, "state": s.state, "name": s.name or "unknown", "version": s.version or ""}
                    for s in h.services
                ],
            }
            for h in hosts
        ],
        "endpoints": [
            {"url": escape_md(e.url), "status_code": e.status_code, "is_interesting": e.is_interesting}
            for e in endpoints[:50]  # cap to top 50 in summary report
        ],
        "total_endpoints_count": len(endpoints),
        "findings": processed_findings,
        "sev_counts": sev_counts,
        "checklist_summary": checklist_summary,
        "checklist": [
            {
                "section": item.section,
                "title": item.title,
                "state": prog.state,
                "note": escape_md(prog.note) if prog.note else "",
            }
            for prog, item in checklist_items
        ],
    }


def generate_markdown_report(data: Dict[str, Any]) -> str:
    """Render a structured Markdown security assessment report."""
    md = []
    p = data["project"]
    md.append(f"# Security Reconnaissance Report: {p['name']}")
    md.append(f"**Generated:** {data['generated_at']}  ")
    md.append(f"**Authorization Acknowledged:** {p['authorized_ack_at']}  \n")
    md.append("---\n")

    md.append("## Executive Summary")
    sev = data["sev_counts"]
    md.append(f"- **Critical Severity Findings:** {sev['CRITICAL']}")
    md.append(f"- **High Severity Findings:** {sev['HIGH']}")
    md.append(f"- **Medium Severity Findings:** {sev['MEDIUM']}")
    md.append(f"- **Low Severity Findings:** {sev['LOW']}")
    md.append(f"- **Informational Items:** {sev['INFO']}")
    md.append(f"- **Live Hosts Identified:** {len(data['hosts'])}")
    md.append(f"- **Total Web Endpoints Enumerated:** {data['total_endpoints_count']}\n")

    md.append("## Assessment Scope")
    if not data["scopes"]:
        md.append("_No formal ScopeEntry entries defined for this project._\n")
    else:
        md.append("| Type | Allowed Target Rule |")
        md.append("| :--- | :--- |")
        for s in data["scopes"]:
            md.append(f"| {s['type']} | `{s['value']}` |")
        md.append("")

    md.append("## Methodology & Checklist Progress")
    chk = data["checklist_summary"]
    md.append(f"Total Tasks: {chk['TOTAL']} | Completed: {chk['COMPLETED']} | In Progress: {chk['IN_PROGRESS']} | Not Started: {chk['NOT_STARTED']}\n")
    if data["checklist"]:
        md.append("| Section | Task | State | Notes |")
        md.append("| :--- | :--- | :--- | :--- |")
        for c in data["checklist"]:
            md.append(f"| {c['section'] or 'General'} | {c['title']} | **{c['state']}** | {c['note'] or '—'} |")
        md.append("")

    md.append("## Attack Surface: Discovered Hosts & Services")
    if not data["hosts"]:
        md.append("_No active hosts recorded._\n")
    else:
        for h in data["hosts"]:
            interesting_tag = " ★ (Interesting)" if h["is_interesting"] else ""
            md.append(f"### Host: `{h['ip']}` ({h['hostname']}){interesting_tag}")
            if not h["services"]:
                md.append("No open ports recorded.\n")
            else:
                md.append("| Port | Protocol | State | Service | Version |")
                md.append("| :--- | :--- | :--- | :--- | :--- |")
                for s in h["services"]:
                    md.append(f"| {s['port']} | {s['protocol']} | {s['state']} | {s['name']} | {s['version']} |")
                md.append("")

    md.append("## Enumerated Endpoints (Sample)")
    if not data["endpoints"]:
        md.append("_No endpoints recorded._\n")
    else:
        md.append(f"Displaying {len(data['endpoints'])} of {data['total_endpoints_count']} total endpoints.\n")
        md.append("| Status | URL |")
        md.append("| :--- | :--- |")
        for ep in data["endpoints"]:
            code = ep["status_code"] or "—"
            md.append(f"| {code} | `{ep['url']}` |")
        md.append("")

    md.append("## Security Findings & Observations")
    if not data["findings"]:
        md.append("_No findings identified in this assessment._\n")
    else:
        for f in data["findings"]:
            md.append(f"### [{f['severity']}] {f['title']}")
            md.append(f"**Status:** {f['status']}  ")
            if f["description"]:
                md.append(f"\n**Description:**\n{f['description']}\n")
            if f["notes"]:
                md.append(f"\n**Analyst Notes:**\n{f['notes']}\n")

            if f["evidence"]:
                md.append("#### Evidence & Artifacts")
                for ev in f["evidence"]:
                    md.append(f"**Type:** `{ev['kind']}` ({ev['created_at']})")
                    if ev["text"]:
                        md.append(f"```text\n{ev['text']}\n```")
                md.append("")

    md.append("---\n*End of ReconForge Assessment Report.*")
    return "\n".join(md)


def generate_pdf_report(data: Dict[str, Any]) -> bytes:
    """Generate professional PDF report from project data using ReportLab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E293B'),
    )
    h2_style = ParagraphStyle(
        'DocHeading2',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155'),
    )
    code_style = ParagraphStyle(
        'DocCode',
        parent=styles['Code'],
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#0F172A'),
        backColor=colors.HexColor('#F1F5F9'),
    )

    story = []

    # Title & Header
    p = data["project"]
    story.append(Paragraph(f"ReconForge Security Report: {p['name']}", title_style))
    story.append(Paragraph(f"<b>Generated:</b> {data['generated_at']} &bull; <b>Auth Acknowledged:</b> {p['authorized_ack_at']}", body_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3B82F6'), spaceAfter=15))

    # Executive Summary Table
    story.append(Paragraph("Executive Summary & Finding Metrics", h2_style))
    sev = data["sev_counts"]
    metrics_data = [
        ["Critical", "High", "Medium", "Low", "Info", "Live Hosts", "Endpoints"],
        [str(sev['CRITICAL']), str(sev['HIGH']), str(sev['MEDIUM']), str(sev['LOW']), str(sev['INFO']), str(len(data['hosts'])), str(data['total_endpoints_count'])],
    ]
    t = Table(metrics_data, colWidths=[70, 70, 70, 70, 70, 85, 90])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F8FAFC')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    # Scope Summary
    story.append(Paragraph("Scope Definitions", h2_style))
    if data["scopes"]:
        scope_rows = [["Type", "Target Identifier"]]
        for s in data["scopes"]:
            scope_rows.append([s['type'], s['value']])
        st_table = Table(scope_rows, colWidths=[100, 425])
        st_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        story.append(st_table)
    else:
        story.append(Paragraph("<i>No project scope whitelist specified.</i>", body_style))
    story.append(Spacer(1, 15))

    # Findings
    story.append(Paragraph("Security Observations & Findings", h2_style))
    if data["findings"]:
        for f in data["findings"]:
            sev_color = "#DC2626" if f['severity'] in ["CRITICAL", "HIGH"] else "#D97706" if f['severity'] == "MEDIUM" else "#2563EB"
            f_header = f"<font color='{sev_color}'><b>[{f['severity']}]</b></font> <b>{f['title']}</b> (Status: {f['status']})"
            story.append(Paragraph(f_header, body_style))
            if f['description']:
                story.append(Paragraph(f"<b>Description:</b> {f['description']}", body_style))
            if f['notes']:
                story.append(Paragraph(f"<b>Notes:</b> {f['notes']}", body_style))

            if f["evidence"]:
                for ev in f["evidence"]:
                    if ev["text"]:
                        sample = ev["text"][:300] + ("..." if len(ev["text"]) > 300 else "")
                        story.append(Paragraph(f"<i>Evidence ({ev['kind']}):</i><br/>{sample}", code_style))
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("<i>No findings reported.</i>", body_style))

    doc.build(story)
    return buffer.getvalue()

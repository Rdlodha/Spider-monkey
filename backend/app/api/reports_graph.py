"""API endpoints for Reports, Attack Surface Graph, and Audit Log UI."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import Optional, List, Dict, Any

from app.api.projects import get_db
from app.models.base import Project, Target, Host, Service, Endpoint, Finding, FindingLink, AuditLog
from app.services.report_service import compile_project_report_data, generate_markdown_report, generate_pdf_report

router = APIRouter()


# ── Reports API ───────────────────────────────────────────────────────────────

@router.get("/reports/{project_id}/markdown", response_class=PlainTextResponse)
def get_markdown_report(
    project_id: str,
    exclude_false_positives: bool = Query(True),
    redact_evidence: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Generate and return structured Markdown report."""
    try:
        data = compile_project_report_data(
            db, project_id,
            exclude_false_positives=exclude_false_positives,
            redact_evidence=redact_evidence,
        )
        return generate_markdown_report(data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/reports/{project_id}/pdf")
def get_pdf_report(
    project_id: str,
    exclude_false_positives: bool = Query(True),
    redact_evidence: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Generate and stream PDF report."""
    try:
        data = compile_project_report_data(
            db, project_id,
            exclude_false_positives=exclude_false_positives,
            redact_evidence=redact_evidence,
        )
        pdf_bytes = generate_pdf_report(data)
        filename = f"reconforge_{data['project']['name'].lower().replace(' ', '_')}_report.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Attack Surface Graph API ──────────────────────────────────────────────────

@router.get("/graph/{project_id}")
def get_attack_surface_graph(project_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Generate nodes and edges for React Flow attack surface visualizer.

    Hierarchy: Target -> Host -> Port/Service -> Endpoint -> Finding
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    nodes = []
    edges = []

    # 1. Root Project Node
    nodes.append({
        "id": f"proj-{project.id}",
        "type": "project",
        "data": {"label": project.name, "type": "Project"},
        "position": {"x": 250, "y": 0},
    })

    targets = db.query(Target).filter(Target.project_id == project_id).all()
    hosts = db.query(Host).filter(Host.project_id == project_id).all()
    endpoints = db.query(Endpoint).filter(Endpoint.project_id == project_id).all()
    findings = db.query(Finding).filter(Finding.project_id == project_id).all()
    finding_links = db.query(FindingLink).join(Finding).filter(Finding.project_id == project_id).all()

    # Targets
    t_idx = 0
    for t in targets:
        t_id = f"target-{t.id}"
        nodes.append({
            "id": t_id,
            "type": "target",
            "data": {"label": t.value, "type": "Target", "id": t.id},
            "position": {"x": 100 + t_idx * 220, "y": 100},
        })
        edges.append({"id": f"e-proj-{t.id}", "source": f"proj-{project.id}", "target": t_id})
        t_idx += 1

    # Hosts & Services
    h_idx = 0
    for h in hosts:
        h_id = f"host-{h.id}"
        nodes.append({
            "id": h_id,
            "type": "host",
            "data": {"label": f"{h.ip}\n({h.hostname or 'no-host'})", "type": "Host", "is_interesting": h.is_interesting, "id": h.id},
            "position": {"x": 80 + h_idx * 200, "y": 220},
        })
        # Connect host to first target (or project)
        target_source = f"target-{targets[0].id}" if targets else f"proj-{project.id}"
        edges.append({"id": f"e-h-{h.id}", "source": target_source, "target": h_id})

        # Services under host
        s_idx = 0
        for s in h.services:
            s_id = f"srv-{s.id}"
            nodes.append({
                "id": s_id,
                "type": "service",
                "data": {"label": f"{s.port}/{s.protocol} ({s.name or 'srv'})", "type": "Service", "is_interesting": s.is_interesting, "id": s.id},
                "position": {"x": 60 + h_idx * 200 + s_idx * 70, "y": 340},
            })
            edges.append({"id": f"e-s-{s.id}", "source": h_id, "target": s_id})
            s_idx += 1
        h_idx += 1

    # Endpoints (sample top 30 to avoid overwhelming graph)
    ep_idx = 0
    for ep in endpoints[:30]:
        ep_id = f"ep-{ep.id}"
        nodes.append({
            "id": ep_id,
            "type": "endpoint",
            "data": {"label": ep.url[:35] + ("..." if len(ep.url) > 35 else ""), "type": "Endpoint", "url": ep.url, "code": ep.status_code, "id": ep.id},
            "position": {"x": 40 + ep_idx * 160, "y": 460},
        })
        # Connect to host if linked, else project
        src = f"host-{ep.host_id}" if ep.host_id else f"proj-{project.id}"
        edges.append({"id": f"e-ep-{ep.id}", "source": src, "target": ep_id})
        ep_idx += 1

    # Findings
    f_idx = 0
    for f in findings:
        f_id = f"find-{f.id}"
        nodes.append({
            "id": f_id,
            "type": "finding",
            "data": {"label": f"[{f.severity}] {f.title[:30]}", "type": "Finding", "severity": f.severity, "status": f.status, "id": f.id},
            "position": {"x": 50 + f_idx * 180, "y": 580},
        })
        # Link findings to associated entities or project
        linked_edges = 0
        for link in finding_links:
            if link.finding_id == f.id:
                target_node = f"{link.entity_type}-{link.entity_id}" if link.entity_type != "service" else f"srv-{link.entity_id}"
                edges.append({"id": f"e-f-{link.id}", "source": target_node, "target": f_id, "animated": True})
                linked_edges += 1
        if linked_edges == 0:
            edges.append({"id": f"e-f-proj-{f.id}", "source": f"proj-{project.id}", "target": f_id, "animated": True})
        f_idx += 1

    return {"nodes": nodes, "edges": edges}


# ── Audit Log API (Append-only) ───────────────────────────────────────────────

@router.get("/audit", response_model=List[Dict[str, Any]])
def get_audit_logs(
    action: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Retrieve system audit logs. Strictly append-only (no modify/delete endpoints)."""
    q = select(AuditLog).order_by(desc(AuditLog.ts)).limit(limit)
    if action:
        q = q.where(AuditLog.action == action)
    logs = db.scalars(q).all()
    return [
        {
            "id": l.id,
            "ts": l.ts.isoformat() if l.ts else None,
            "actor": l.actor,
            "action": l.action,
            "target": l.target,
            "tool": l.tool,
            "result": l.result,
        }
        for l in logs
    ]

"""Checklist API: list templates, get per-target progress, update item state."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.projects import get_db
from app.models.base import ChecklistTemplate, ChecklistProgress, Target
from app.schemas.findings import (
    ChecklistTemplateResponse,
    ChecklistProgressResponse,
    ChecklistProgressUpdate,
)
from app.services import checklist_service

router = APIRouter()


@router.get("/templates", response_model=list[ChecklistTemplateResponse])
def list_templates(db: Session = Depends(get_db)):
    return db.query(ChecklistTemplate).all()


@router.get("/templates/{template_id}", response_model=ChecklistTemplateResponse)
def get_template(template_id: str, db: Session = Depends(get_db)):
    tpl = db.query(ChecklistTemplate).filter_by(id=template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl


@router.get("/progress/{target_id}", response_model=list[ChecklistProgressResponse])
def get_progress(target_id: str, db: Session = Depends(get_db)):
    target = db.query(Target).filter_by(id=target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    rows = checklist_service.get_or_create_progress_for_target(db, target)
    result = []
    for row in rows:
        item = row.template_item
        result.append(
            ChecklistProgressResponse(
                id=row.id,
                target_id=row.target_id,
                template_item_id=row.template_item_id,
                state=row.state,
                note=row.note,
                updated_at=row.updated_at,
                item_section=item.section if item else None,
                item_title=item.title if item else "",
                item_sort_order=item.sort_order if item else 0,
            )
        )
    result.sort(key=lambda r: (r.item_section or "", r.item_sort_order))
    return result


@router.patch("/progress/{progress_id}", response_model=ChecklistProgressResponse)
def update_progress(
    progress_id: str,
    data: ChecklistProgressUpdate,
    db: Session = Depends(get_db),
):
    row = db.query(ChecklistProgress).filter_by(id=progress_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Progress record not found")
    valid_states = {"NOT_STARTED", "IN_PROGRESS", "COMPLETED", "NOT_APPLICABLE"}
    if data.state.upper() not in valid_states:
        raise HTTPException(status_code=400, detail=f"Invalid state. Must be one of: {valid_states}")
    updated = checklist_service.update_progress(db, row, data.state, data.note)
    item = updated.template_item
    return ChecklistProgressResponse(
        id=updated.id,
        target_id=updated.target_id,
        template_item_id=updated.template_item_id,
        state=updated.state,
        note=updated.note,
        updated_at=updated.updated_at,
        item_section=item.section if item else None,
        item_title=item.title if item else "",
        item_sort_order=item.sort_order if item else 0,
    )

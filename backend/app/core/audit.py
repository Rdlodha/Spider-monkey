from sqlalchemy.orm import Session
from app.models.base import AuditLog

def audit(db: Session, action: str, target: str = None, tool: str = None, result: str = None):
    log = AuditLog(action=action, target=target, tool=tool, result=result)
    db.add(log)
    db.commit()

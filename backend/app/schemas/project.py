from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

class TargetBase(BaseModel):
    value: str

class TargetCreate(TargetBase):
    pass

class TargetResponse(TargetBase):
    id: str
    project_id: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ProjectBase(BaseModel):
    name: str

class ProjectCreate(ProjectBase):
    authorized_ack: bool = Field(..., description="Must be true to authorize testing targets")

class ProjectResponse(ProjectBase):
    id: str
    authorized_ack_at: Optional[datetime]
    created_at: datetime
    targets: List[TargetResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

from fastapi import APIRouter
from .health import router as health_router
from .projects import router as projects_router
from .targets import router as targets_router
from .scans import router as scans_router
from .hosts import router as hosts_router
from .endpoints import router as endpoints_router
from .findings import router as findings_router
from .checklists import router as checklists_router
from .analytics import router as analytics_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(targets_router, prefix="/targets", tags=["targets"])
api_router.include_router(scans_router, prefix="/scans", tags=["scans"])
api_router.include_router(hosts_router, prefix="/hosts", tags=["hosts"])
api_router.include_router(endpoints_router, prefix="/endpoints", tags=["endpoints"])
api_router.include_router(findings_router, prefix="/findings", tags=["findings"])
api_router.include_router(checklists_router, prefix="/checklists", tags=["checklists"])
api_router.include_router(analytics_router, tags=["analytics"])

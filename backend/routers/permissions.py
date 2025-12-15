from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Optional

from backend.config import settings
from backend.services.permissions_service import (
    assign_dashboard,
    get_allowed_dashboards,
    get_full_permissions,
    get_permissions_map,
    is_admin as is_admin_email,
    remove_dashboard,
    get_maintenance_config,
    set_maintenance_mode
)
from shared.odoo_client import OdooClient

router = APIRouter(prefix="/api/v1/permissions", tags=["Permissions"])


class PermissionUpdateRequest(BaseModel):
    dashboard: str
    email: str
    admin_username: str
    admin_password: str


class MaintenanceRequest(BaseModel):
    enabled: bool
    message: Optional[str] = None
    admin_username: str
    admin_password: str


def _validate_admin(username: str, password: str) -> None:
    try:
        OdooClient(username=username, password=password)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    normalized = username.strip().lower()
    allowed = {entry.strip().lower() for entry in settings.PERMISSION_ADMINS}
    if normalized not in allowed:
        raise HTTPException(status_code=403, detail="Usuario no autorizado")


@router.get("/user")
def user_permissions(username: str = Query(..., description="Correo del usuario")) -> Dict:
    """Retorna la lista de dashboards restringidos y los permisos del usuario."""
    restricted = get_permissions_map()
    allowed = get_allowed_dashboards(username)
    return {
        "restricted": restricted,
        "allowed": allowed,
        "is_admin": is_admin_email(username)
    }


@router.get("/all")
def all_permissions(
    admin_username: str = Query(...),
    admin_password: str = Query(...)
) -> Dict:
    """Retorna el mapa completo de permisos (solo admins)."""
    _validate_admin(admin_username, admin_password)
    return get_full_permissions()


@router.post("/assign")
def assign_permission(payload: PermissionUpdateRequest) -> Dict:
    _validate_admin(payload.admin_username, payload.admin_password)
    dashboards = assign_dashboard(payload.dashboard, payload.email)
    return {"dashboards": dashboards}


@router.post("/remove")
def remove_permission(payload: PermissionUpdateRequest) -> Dict:
    _validate_admin(payload.admin_username, payload.admin_password)
    dashboards = remove_dashboard(payload.dashboard, payload.email)
    return {"dashboards": dashboards}


# ============ ENDPOINTS DE MANTENIMIENTO ============

@router.get("/maintenance/status")
def maintenance_status() -> Dict:
    """Obtiene el estado del banner de mantenimiento (público)."""
    return get_maintenance_config()


@router.post("/maintenance")
def update_maintenance(payload: MaintenanceRequest) -> Dict:
    """Actualiza el estado del modo de mantenimiento (solo admins)."""
    _validate_admin(payload.admin_username, payload.admin_password)
    result = set_maintenance_mode(payload.enabled, payload.message)
    return {"maintenance": result}


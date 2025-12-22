from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Optional, List

from backend.config import settings
from backend.services.permissions_service import (
    assign_dashboard,
    get_allowed_dashboards,
    get_full_permissions,
    get_permissions_map,
    is_admin as is_admin_email,
    remove_dashboard,
    get_maintenance_config,
    set_maintenance_mode,
    # Page-level permissions
    get_all_module_pages,
    get_module_pages,
    get_allowed_pages,
    get_page_permissions,
    assign_page,
    remove_page,
    clear_page_restriction
)
from shared.odoo_client import OdooClient

router = APIRouter(prefix="/api/v1/permissions", tags=["Permissions"])


class PermissionUpdateRequest(BaseModel):
    dashboard: str
    email: str
    admin_username: str
    admin_password: str


class PagePermissionRequest(BaseModel):
    module: str
    page: str
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


# ============ PERMISOS DE PÁGINAS/TABS ============

@router.get("/pages/structure")
def get_pages_structure() -> Dict:
    """Retorna la estructura de páginas de todos los módulos."""
    return {"modules": get_all_module_pages()}


@router.get("/pages/module/{module}")
def get_module_pages_endpoint(module: str) -> Dict:
    """Retorna las páginas disponibles para un módulo específico."""
    pages = get_module_pages(module)
    return {"module": module, "pages": pages}


@router.get("/pages/permissions")
def get_all_page_permissions(
    admin_username: str = Query(...),
    admin_password: str = Query(...)
) -> Dict:
    """Retorna todos los permisos de páginas (solo admins)."""
    _validate_admin(admin_username, admin_password)
    return {"pages": get_page_permissions()}


@router.get("/pages/user")
def get_user_page_permissions(
    username: str = Query(..., description="Correo del usuario"),
    module: str = Query(..., description="Módulo a consultar")
) -> Dict:
    """Retorna las páginas permitidas para un usuario en un módulo."""
    allowed = get_allowed_pages(username, module)
    return {
        "module": module,
        "allowed_pages": allowed,
        "is_admin": is_admin_email(username)
    }


@router.post("/pages/assign")
def assign_page_permission(payload: PagePermissionRequest) -> Dict:
    """Asigna acceso a una página específica para un usuario."""
    _validate_admin(payload.admin_username, payload.admin_password)
    pages = assign_page(payload.module, payload.page, payload.email)
    return {"pages": pages}


@router.post("/pages/remove")
def remove_page_permission(payload: PagePermissionRequest) -> Dict:
    """Quita acceso a una página específica para un usuario."""
    _validate_admin(payload.admin_username, payload.admin_password)
    pages = remove_page(payload.module, payload.page, payload.email)
    return {"pages": pages}


@router.post("/pages/clear")
def clear_page_permission(
    module: str = Query(...),
    page: str = Query(...),
    admin_username: str = Query(...),
    admin_password: str = Query(...)
) -> Dict:
    """Elimina la restricción de una página (la hace pública)."""
    _validate_admin(admin_username, admin_password)
    pages = clear_page_restriction(module, page)
    return {"pages": pages}



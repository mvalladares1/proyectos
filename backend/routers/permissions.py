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


# ============ ENDPOINTS DE ADMINISTRADORES ============

@router.get("/admins")
def get_admins_endpoint() -> Dict:
    """Obtiene la lista de administradores."""
    from backend.services.permissions_service import get_admins
    return {"admins": get_admins()}


@router.post("/admins/assign")
def assign_admin_endpoint(
    email: str = Query(..., description="Email del nuevo admin"),
    admin_username: str = Query(...),
    admin_password: str = Query(...)
) -> Dict:
    """Agrega un administrador."""
    from backend.services.permissions_service import assign_admin
    _validate_admin(admin_username, admin_password)
    admins = assign_admin(email)
    return {"admins": admins}


@router.post("/admins/remove")
def remove_admin_endpoint(
    email: str = Query(..., description="Email del admin a remover"),
    admin_username: str = Query(...),
    admin_password: str = Query(...)
) -> Dict:
    """Remueve un administrador."""
    from backend.services.permissions_service import remove_admin
    _validate_admin(admin_username, admin_password)
    admins = remove_admin(email)
    return {"admins": admins}


# ============ OVERRIDE DE ORIGEN ============

class OverrideOrigenRequest(BaseModel):
    picking_name: str
    origen: str
    admin_username: str
    admin_password: str


@router.get("/overrides/origen")
def get_overrides_origen() -> Dict:
    """Obtiene todos los overrides de origen (público para recepciones)."""
    from backend.services.permissions_service import get_override_origen_map
    return {"overrides": get_override_origen_map()}


@router.get("/overrides/origen/list")
def get_overrides_origen_list(
    admin_username: str = Query(...),
    admin_password: str = Query(...)
) -> Dict:
    """Obtiene lista detallada de overrides (solo admins)."""
    from backend.services.permissions_service import get_override_origen_list
    _validate_admin(admin_username, admin_password)
    return {"overrides": get_override_origen_list()}


@router.post("/overrides/origen/add")
def add_override_origen_endpoint(payload: OverrideOrigenRequest) -> Dict:
    """Agrega un override de origen."""
    from backend.services.permissions_service import add_override_origen
    _validate_admin(payload.admin_username, payload.admin_password)
    try:
        overrides = add_override_origen(payload.picking_name, payload.origen)
        return {"overrides": overrides}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/overrides/origen/remove")
def remove_override_origen_endpoint(
    picking_name: str = Query(...),
    admin_username: str = Query(...),
    admin_password: str = Query(...)
) -> Dict:
    """Elimina un override de origen."""
    from backend.services.permissions_service import remove_override_origen
    _validate_admin(admin_username, admin_password)
    overrides = remove_override_origen(picking_name)
    return {"overrides": overrides}


# ============ EXCLUSIONES DE VALORIZACIÓN ============

class ExclusionRequest(BaseModel):
    albaran: str
    motivo: Optional[str] = ""
    admin_username: str
    admin_password: str


@router.get("/exclusiones")
def get_exclusiones_endpoint() -> Dict:
    """Obtiene set de exclusiones (público para servicios)."""
    from backend.services.permissions_service import get_exclusiones_set
    return {"exclusiones": list(get_exclusiones_set())}


@router.get("/exclusiones/list")
def get_exclusiones_list_endpoint(
    admin_username: str = Query(...),
    admin_password: str = Query(...)
) -> Dict:
    """Obtiene lista detallada de exclusiones (solo admins)."""
    from backend.services.permissions_service import get_exclusiones_list
    _validate_admin(admin_username, admin_password)
    return {"exclusiones": get_exclusiones_list()}


@router.post("/exclusiones/add")
def add_exclusion_endpoint(payload: ExclusionRequest) -> Dict:
    """Agrega una exclusión."""
    from backend.services.permissions_service import add_exclusion
    _validate_admin(payload.admin_username, payload.admin_password)
    exclusiones = add_exclusion(payload.albaran, payload.motivo or "")
    return {"exclusiones": exclusiones}


@router.post("/exclusiones/remove")
def remove_exclusion_endpoint(
    albaran: str = Query(...),
    admin_username: str = Query(...),
    admin_password: str = Query(...)
) -> Dict:
    """Elimina una exclusión."""
    from backend.services.permissions_service import remove_exclusion
    _validate_admin(admin_username, admin_password)
    exclusiones = remove_exclusion(albaran)
    return {"exclusiones": exclusiones}

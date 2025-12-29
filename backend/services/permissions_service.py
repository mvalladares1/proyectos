"""Servicio de permisos para dashboards."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import settings
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PERMISSIONS_FILE = DATA_DIR / "permissions.json"

# Lista completa de dashboards disponibles en el sistema (slugs técnicos)
ALL_DASHBOARDS = [
    "recepciones",
    "produccion",
    "bandejas",
    "stock",
    "containers",
    "rendimiento",
    "finanzas",
    "compras",
    "automatizaciones",
    "permisos",
]

# Mapeo de slugs a nombres amigables para mostrar en el panel
DASHBOARD_NAMES = {
    "recepciones": "Recepciones",
    "produccion": "Producción",
    "bandejas": "Bandejas",
    "stock": "Stock",
    "containers": "Containers",
    "rendimiento": "Rendimiento",
    "finanzas": "Finanzas",
    "estado_resultado": "Finanzas",  # Alias para compatibilidad
    "compras": "Compras",
    "automatizaciones": "Automatizaciones",
    "permisos": "Permisos",
}

# ============ PÁGINAS/TABS DENTRO DE CADA MÓDULO ============
# Estructura: módulo -> lista de páginas con slug y nombre
# Los nombres DEBEN coincidir con los tabs reales de cada página
MODULE_PAGES: Dict[str, List[Dict[str, str]]] = {
    "recepciones": [
        {"slug": "kpis_calidad", "name": "KPIs y Calidad"},
        {"slug": "gestion_recepciones", "name": "Gestión de Recepciones"},
        {"slug": "curva_abastecimiento", "name": "Curva de Abastecimiento"},
        {"slug": "aprobaciones_mp", "name": "Aprobaciones MP"},
    ],
    "produccion": [
        {"slug": "reporteria_general", "name": "Reportería General"},
        {"slug": "detalle_of", "name": "Detalle de OF"},
    ],
    "bandejas": [
        {"slug": "dashboard", "name": "Dashboard"},
    ],
    "stock": [
        {"slug": "camaras", "name": "Cámaras"},
        {"slug": "pallets", "name": "Pallets"},
        {"slug": "trazabilidad", "name": "Trazabilidad"},
    ],
    "containers": [
        {"slug": "lista", "name": "Lista Containers"},
    ],
    "finanzas": [
        {"slug": "agrupado", "name": "Agrupado"},
        {"slug": "mensualizado", "name": "Mensualizado"},
        {"slug": "ytd", "name": "YTD (Acumulado)"},
        {"slug": "cg", "name": "CG"},
        {"slug": "detalle", "name": "Detalle"},
    ],
    "compras": [
        {"slug": "ordenes", "name": "Órdenes de Compra"},
        {"slug": "lineas_credito", "name": "Líneas de Crédito"},
    ],
    "rendimiento": [
        {"slug": "dashboard", "name": "Dashboard"},
    ],
    "automatizaciones": [
        {"slug": "crear_orden", "name": "Crear Orden"},
        {"slug": "monitor_ordenes", "name": "Monitor de Órdenes"},
    ],
    "permisos": [
        {"slug": "modulos", "name": "Módulos"},
        {"slug": "paginas", "name": "Páginas"},
        {"slug": "por_usuario", "name": "Por Usuario"},
        {"slug": "configuracion", "name": "Configuración"},
    ],
}

DEFAULT_PERMISSIONS: Dict[str, Any] = {
    "dashboards": {slug: [] for slug in ALL_DASHBOARDS},  # Todos públicos por defecto
    "pages": {},  # Permisos granulares por página: "modulo.pagina" -> [emails]
    "admins": ["mvalladares@riofuturo.cl"],
    "maintenance": {
        "enabled": False,
        "message": "El sistema está siendo ajustado en este momento."
    }
}


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_dashboard(slug: str) -> str:
    return slug.strip().lower()


def _ensure_file() -> None:
    if not PERMISSIONS_FILE.exists():
        _write_permissions(DEFAULT_PERMISSIONS)


def _read_permissions() -> Dict[str, Any]:
    _ensure_file()
    try:
        with PERMISSIONS_FILE.open("r", encoding="utf-8") as handler:
            data: Dict[str, Any] = json.load(handler)
    except json.JSONDecodeError:
        data = DEFAULT_PERMISSIONS.copy()
    data.setdefault("dashboards", {})
    data.setdefault("admins", [])
    return data


def _write_permissions(data: Dict[str, Any]) -> None:
    with PERMISSIONS_FILE.open("w", encoding="utf-8") as handler:
        json.dump(data, handler, ensure_ascii=False, indent=2)


def get_permissions_map() -> Dict[str, List[str]]:
    """Retorna el mapa de permisos, asegurando que todos los dashboards estén incluidos."""
    full_data = _read_permissions()
    dashboards = full_data["dashboards"]
    modified = False
    
    # Asegurar que todos los dashboards de ALL_DASHBOARDS estén presentes
    for slug in ALL_DASHBOARDS:
        if slug not in dashboards:
            dashboards[slug] = []
            modified = True
    
    # Limpiar entradas espurias (dashboards que no están en ALL_DASHBOARDS)
    stray_keys = [k for k in dashboards.keys() if k not in ALL_DASHBOARDS]
    for key in stray_keys:
        del dashboards[key]
        modified = True
    
    # Si hubo cambios, persistir
    if modified:
        full_data["dashboards"] = dashboards
        _write_permissions(full_data)
    
    return dashboards.copy()


def get_admins() -> List[str]:
    return _read_permissions().get("admins", [])


def is_admin(email: str) -> bool:
    normalized = _normalize_email(email)
    allowed = { _normalize_email(item) for item in settings.PERMISSION_ADMINS }
    allowed.update(_normalize_email(item) for item in get_admins())
    return normalized in allowed


def get_allowed_dashboards(email: str) -> List[str]:
    """
    Retorna los dashboards que el usuario puede ver.
    - Si un dashboard tiene lista vacía [] → es público (todos pueden ver)
    - Si tiene correos específicos → solo esos correos pueden ver
    - Admins pueden ver todo
    """
    normalized = _normalize_email(email)
    dashboards = get_permissions_map()
    
    # Admins pueden ver todo
    if is_admin(email):
        return list(dashboards.keys())
    
    allowed: List[str] = []
    for slug, emails in dashboards.items():
        # Lista vacía = público
        if not emails:
            allowed.append(slug)
        # Lista con correos = restringido
        elif normalized in {_normalize_email(addr) for addr in emails}:
            allowed.append(slug)
    return allowed


def assign_dashboard(slug: str, email: str) -> Dict[str, List[str]]:
    data = _read_permissions()
    slug_key = _normalize_dashboard(slug)
    dashboards = data.setdefault("dashboards", {})
    bucket = dashboards.setdefault(slug_key, [])
    normalized_email = _normalize_email(email)
    if normalized_email not in {_normalize_email(addr) for addr in bucket}:
        bucket.append(email.strip())
    _write_permissions(data)
    return dashboards.copy()


def remove_dashboard(slug: str, email: str) -> Dict[str, List[str]]:
    data = _read_permissions()
    slug_key = _normalize_dashboard(slug)
    dashboards = data.setdefault("dashboards", {})
    bucket = dashboards.get(slug_key, [])
    normalized_email = _normalize_email(email)
    dashboards[slug_key] = [addr for addr in bucket if _normalize_email(addr) != normalized_email]
    _write_permissions(data)
    return dashboards.copy()


def get_full_permissions() -> Dict[str, Any]:
    return _read_permissions()


def get_dashboard_name(slug: str) -> str:
    """Obtiene el nombre amigable de un dashboard."""
    return DASHBOARD_NAMES.get(_normalize_dashboard(slug), slug)


def get_all_dashboards() -> List[str]:
    """Retorna la lista de todos los dashboards disponibles."""
    return ALL_DASHBOARDS.copy()


# ============ PERMISOS A NIVEL DE PÁGINA/TAB ============

def get_module_pages(module: str) -> List[Dict[str, str]]:
    """Retorna las páginas disponibles para un módulo."""
    return MODULE_PAGES.get(_normalize_dashboard(module), [])


def get_all_module_pages() -> Dict[str, List[Dict[str, str]]]:
    """Retorna todas las páginas de todos los módulos."""
    return MODULE_PAGES.copy()


def get_page_permissions() -> Dict[str, List[str]]:
    """Retorna el mapa de permisos de páginas."""
    data = _read_permissions()
    return data.get("pages", {})


def get_allowed_pages(email: str, module: str) -> List[str]:
    """
    Retorna las páginas permitidas para un usuario dentro de un módulo.
    - Si la página no tiene restricción -> permitida
    - Si tiene lista de emails -> solo esos usuarios
    - Admins ven todo
    """
    normalized = _normalize_email(email)
    module_key = _normalize_dashboard(module)
    
    # Admins ven todo
    if is_admin(email):
        return [p["slug"] for p in MODULE_PAGES.get(module_key, [])]
    
    pages_perms = get_page_permissions()
    allowed: List[str] = []
    
    for page in MODULE_PAGES.get(module_key, []):
        page_key = f"{module_key}.{page['slug']}"
        emails_list = pages_perms.get(page_key, [])
        
        # Lista vacía = público
        if not emails_list:
            allowed.append(page["slug"])
        # Lista con correos = restringido
        elif normalized in {_normalize_email(addr) for addr in emails_list}:
            allowed.append(page["slug"])
    
    return allowed


def assign_page(module: str, page: str, email: str) -> Dict[str, List[str]]:
    """Asigna acceso a una página específica para un usuario."""
    data = _read_permissions()
    pages = data.setdefault("pages", {})
    page_key = f"{_normalize_dashboard(module)}.{page.strip().lower()}"
    bucket = pages.setdefault(page_key, [])
    normalized_email = _normalize_email(email)
    
    if normalized_email not in {_normalize_email(addr) for addr in bucket}:
        bucket.append(email.strip())
    
    _write_permissions(data)
    return pages.copy()


def remove_page(module: str, page: str, email: str) -> Dict[str, List[str]]:
    """Quita acceso a una página específica para un usuario."""
    data = _read_permissions()
    pages = data.setdefault("pages", {})
    page_key = f"{_normalize_dashboard(module)}.{page.strip().lower()}"
    bucket = pages.get(page_key, [])
    normalized_email = _normalize_email(email)
    
    pages[page_key] = [addr for addr in bucket if _normalize_email(addr) != normalized_email]
    _write_permissions(data)
    return pages.copy()


def clear_page_restriction(module: str, page: str) -> Dict[str, List[str]]:
    """Elimina la restricción de una página (la hace pública)."""
    data = _read_permissions()
    pages = data.setdefault("pages", {})
    page_key = f"{_normalize_dashboard(module)}.{page.strip().lower()}"
    
    if page_key in pages:
        del pages[page_key]
    
    _write_permissions(data)
    return pages.copy()


# ============ BANNER DE MANTENIMIENTO ============

def get_maintenance_config() -> Dict[str, Any]:
    """Obtiene la configuración del banner de mantenimiento."""
    data = _read_permissions()
    default_maintenance = {
        "enabled": False,
        "message": "El sistema está siendo ajustado en este momento."
    }
    return data.get("maintenance", default_maintenance)


def set_maintenance_mode(enabled: bool, message: Optional[str] = None) -> Dict[str, Any]:
    """Activa o desactiva el modo de mantenimiento."""
    data = _read_permissions()
    if "maintenance" not in data:
        data["maintenance"] = {
            "enabled": False,
            "message": "El sistema está siendo ajustado en este momento."
        }
    
    data["maintenance"]["enabled"] = enabled
    if message is not None:
        data["maintenance"]["message"] = message
    
    _write_permissions(data)
    return data["maintenance"]


def is_maintenance_mode() -> bool:
    """Verifica si el modo de mantenimiento está activo."""
    config = get_maintenance_config()
    return config.get("enabled", False)

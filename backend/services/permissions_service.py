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
    "pedidos_venta",
    "rendimiento",
    "relacion_comercial",
    "reconciliacion",
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
    "relacion_comercial": "Relación Comercial",
    "finanzas": "Finanzas",
    "estado_resultado": "Finanzas",  # Alias para compatibilidad
    "compras": "Compras",
    "automatizaciones": "Automatizaciones",
    "permisos": "Permisos",
}

# ============ PÁGINAS/TABS DENTRO DE CADA MÓDULO ============
# Estructura: módulo -> lista de páginas con slug y nombre
# Los nombres DEBEN coincidir con los tabs reales de cada página
# ACTUALIZADO: 2026-01-20
MODULE_PAGES: Dict[str, List[Dict[str, str]]] = {
    "recepciones": [
        {"slug": "kpis_calidad", "name": "KPIs y Calidad"},
        {"slug": "gestion_recepciones", "name": "Gestión de Recepciones"},
        {"slug": "pallets_recepcion", "name": "Pallets por Recepción"},
        {"slug": "curva_abastecimiento", "name": "Curva de Abastecimiento"},
        {"slug": "aprobaciones_mp", "name": "Aprobaciones MP"},
        {"slug": "aprobaciones_fletes", "name": "🚚 Aprobaciones Fletes"},
        {"slug": "proforma_fletes", "name": "📄 Proforma Consolidada"},
    ],
    "produccion": [
        {"slug": "reporteria_general", "name": "Reportería General"},
        {"slug": "detalle_of", "name": "Detalle de OF"},
        {"slug": "clasificacion", "name": "Clasificación"},
    ],
    "bandejas": [
        {"slug": "dashboard", "name": "Dashboard"},
    ],
    "stock": [
        {"slug": "movimientos", "name": "Movimientos"},
        {"slug": "camaras", "name": "Cámaras"},
        {"slug": "pallets", "name": "Pallets"},
        {"slug": "trazabilidad", "name": "Trazabilidad"},
    ],
    "containers": [
        {"slug": "lista", "name": "Lista Containers"},
    ],
    "pedidos_venta": [
        {"slug": "lista", "name": "Lista de Pedidos"},
    ],
    "finanzas": [
        {"slug": "eerr", "name": "Estado de Resultados"},
        {"slug": "cg", "name": "Cuentas (CG)"},
        {"slug": "flujo_caja", "name": "Flujo de Caja"},
    ],
    "compras": [
        {"slug": "ordenes", "name": "Órdenes de Compra"},
        {"slug": "lineas_credito", "name": "Líneas de Crédito"},
    ],
    "rendimiento": [
        {"slug": "trazabilidad_pallets", "name": "Trazabilidad por Pallets"},
        {"slug": "diagrama_sankey", "name": "Diagrama Sankey"},
    ],
    "relacion_comercial": [
        {"slug": "dashboard", "name": "Dashboard"},
    ],
    "reconciliacion": [
        {"slug": "reconciliacion", "name": "Reconciliación ODF"},
    ],
    "automatizaciones": [
        {"slug": "crear_orden", "name": "Crear Orden"},
        {"slug": "monitor_ordenes", "name": "Monitor de Órdenes"},
        {"slug": "movimientos", "name": "Movimientos"},
        {"slug": "monitor_mov", "name": "Monitor Mov."},
    ],
    "permisos": [
        {"slug": "modulos", "name": "Módulos"},
        {"slug": "paginas", "name": "Páginas"},
        {"slug": "usuarios", "name": "Usuarios"},
        {"slug": "override_origen", "name": "Override Origen"},
        {"slug": "configuracion", "name": "Configuración"},
    ],
}

DEFAULT_PERMISSIONS: Dict[str, Any] = {
    "dashboards": {slug: [] for slug in ALL_DASHBOARDS},  # Todos públicos por defecto
    "pages": {},  # Permisos granulares por página: "modulo.pagina" -> [emails]
    "admins": ["mvalladares@riofuturo.cl", "frios@riofuturo.cl"],
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


import time
from contextlib import contextmanager

LOCK_FILE = DATA_DIR / "permissions.lock"

class FileLock:
    def __init__(self, lock_file: Path, timeout: float = 10.0, delay: float = 0.1):
        self.lock_file = lock_file
        self.timeout = timeout
        self.delay = delay
    
    def acquire(self):
        start_time = time.time()
        while True:
            try:
                # Modos 'x' crea archivo exclusivo, falla si existe. Atomic en POSIX y Windows (Python 3)
                with open(self.lock_file, "x"):
                    return
            except FileExistsError:
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Could not acquire lock on {self.lock_file}")
                time.sleep(self.delay)

    def release(self):
        try:
            self.lock_file.unlink()
        except FileNotFoundError:
            pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

@contextmanager
def permission_transaction():
    """Transaction context for read-modify-write operations."""
    with FileLock(LOCK_FILE):
        data = _read_permissions()
        yield data
        _write_permissions(data)

def _read_permissions() -> Dict[str, Any]:
    _ensure_file()
    try:
        with PERMISSIONS_FILE.open("r", encoding="utf-8") as handler:
            data: Dict[str, Any] = json.load(handler)
    except json.JSONDecodeError:
        data = DEFAULT_PERMISSIONS.copy()
    
    # Ensure structure
    data.setdefault("dashboards", {})
    data.setdefault("pages", {})
    data.setdefault("admins", [])
    data.setdefault("maintenance", DEFAULT_PERMISSIONS["maintenance"])
    
    return data


def _write_permissions(data: Dict[str, Any]) -> None:
    # Atomic write pattern: write to temp file then rename
    temp_file = PERMISSIONS_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as handler:
        json.dump(data, handler, ensure_ascii=False, indent=2)
    temp_file.replace(PERMISSIONS_FILE)


def get_permissions_map() -> Dict[str, List[str]]:
    """Retorna el mapa de permisos, asegurando consistencia."""
    # Usamos lock para asegurar que la limpieza no colisione con otras escrituras
    with FileLock(LOCK_FILE):
        full_data = _read_permissions()
        dashboards = full_data["dashboards"]
        modified = False
        
        # Asegurar keys requeridas
        for slug in ALL_DASHBOARDS:
            if slug not in dashboards:
                dashboards[slug] = []
                modified = True
        
        # Limpiar keys viejas
        stray_keys = [k for k in dashboards.keys() if k not in ALL_DASHBOARDS]
        for key in stray_keys:
            del dashboards[key]
            modified = True
        
        if modified:
            full_data["dashboards"] = dashboards
            _write_permissions(full_data)
        
        return dashboards.copy()


def get_admins() -> List[str]:
    # Read is safe enough without lock if we accept slightly stale data, 
    # but strictly a shared lock would be better. For now simple read.
    return _read_permissions().get("admins", [])


def is_admin(email: str) -> bool:
    normalized = _normalize_email(email)
    allowed = { _normalize_email(item) for item in settings.PERMISSION_ADMINS }
    allowed.update(_normalize_email(item) for item in get_admins())
    return normalized in allowed


def get_allowed_dashboards(email: str) -> List[str]:
    normalized = _normalize_email(email)
    dashboards = get_permissions_map()
    
    if is_admin(email):
        return list(dashboards.keys())
    
    allowed: List[str] = []
    for slug, emails in dashboards.items():
        if not emails:
            allowed.append(slug)
        elif normalized in {_normalize_email(addr) for addr in emails}:
            allowed.append(slug)
    return allowed


def get_restricted_modules() -> Dict[str, List[str]]:
    dashboards = get_permissions_map()
    restricted: Dict[str, List[str]] = {}
    for slug, emails in dashboards.items():
        if emails:
            restricted[slug] = emails
    return restricted


def assign_dashboard(slug: str, email: str) -> Dict[str, List[str]]:
    with permission_transaction() as data:
        slug_key = _normalize_dashboard(slug)
        dashboards = data.setdefault("dashboards", {})
        bucket = dashboards.setdefault(slug_key, [])
        normalized_email = _normalize_email(email)
        if normalized_email not in {_normalize_email(addr) for addr in bucket}:
            bucket.append(email.strip())
        # Triggers _write_permissions on exit
    return data["dashboards"]


def remove_dashboard(slug: str, email: str) -> Dict[str, List[str]]:
    with permission_transaction() as data:
        slug_key = _normalize_dashboard(slug)
        dashboards = data.setdefault("dashboards", {})
        bucket = dashboards.get(slug_key, [])
        normalized_email = _normalize_email(email)
        dashboards[slug_key] = [addr for addr in bucket if _normalize_email(addr) != normalized_email]
    return data["dashboards"]


def get_full_permissions() -> Dict[str, Any]:
    return _read_permissions()


def get_dashboard_name(slug: str) -> str:
    return DASHBOARD_NAMES.get(_normalize_dashboard(slug), slug)


def get_all_dashboards() -> List[str]:
    return ALL_DASHBOARDS.copy()


# ============ PERMISOS A NIVEL DE PÁGINA/TAB ============

def get_module_pages(module: str) -> List[Dict[str, str]]:
    return MODULE_PAGES.get(_normalize_dashboard(module), [])


def get_all_module_pages() -> Dict[str, List[Dict[str, str]]]:
    return MODULE_PAGES.copy()


def get_page_permissions() -> Dict[str, List[str]]:
    data = _read_permissions()
    return data.get("pages", {})


def get_allowed_pages(email: str, module: str) -> List[str]:
    normalized = _normalize_email(email)
    module_key = _normalize_dashboard(module)
    
    if is_admin(email):
        return [p["slug"] for p in MODULE_PAGES.get(module_key, [])]
    
    # We read once here
    pages_perms = get_page_permissions()
    allowed: List[str] = []
    
    for page in MODULE_PAGES.get(module_key, []):
        page_key = f"{module_key}.{page['slug']}"
        emails_list = pages_perms.get(page_key, [])
        
        if not emails_list:
            allowed.append(page["slug"])
        elif normalized in {_normalize_email(addr) for addr in emails_list}:
            allowed.append(page["slug"])
    
    return allowed


def assign_page(module: str, page: str, email: str) -> Dict[str, List[str]]:
    with permission_transaction() as data:
        pages = data.setdefault("pages", {})
        page_key = f"{_normalize_dashboard(module)}.{page.strip().lower()}"
        bucket = pages.setdefault(page_key, [])
        normalized_email = _normalize_email(email)
        
        if normalized_email not in {_normalize_email(addr) for addr in bucket}:
            bucket.append(email.strip())
    return data["pages"]


def remove_page(module: str, page: str, email: str) -> Dict[str, List[str]]:
    with permission_transaction() as data:
        pages = data.setdefault("pages", {})
        page_key = f"{_normalize_dashboard(module)}.{page.strip().lower()}"
        bucket = pages.get(page_key, [])
        normalized_email = _normalize_email(email)
        
        pages[page_key] = [addr for addr in bucket if _normalize_email(addr) != normalized_email]
    return data["pages"]


def clear_page_restriction(module: str, page: str) -> Dict[str, List[str]]:
    with permission_transaction() as data:
        pages = data.setdefault("pages", {})
        page_key = f"{_normalize_dashboard(module)}.{page.strip().lower()}"
        if page_key in pages:
            del pages[page_key]
    return data["pages"]


# ============ ADMINISTRADORES ============

def assign_admin(email: str) -> List[str]:
    """Agrega un email a la lista de administradores."""
    with permission_transaction() as data:
        admins = data.setdefault("admins", [])
        normalized_email = _normalize_email(email)
        
        # Evitar duplicados
        if not any(_normalize_email(existing) == normalized_email for existing in admins):
            admins.append(email.strip())
    return data["admins"]


def remove_admin(email: str) -> List[str]:
    """Remueve un email de la lista de administradores."""
    with permission_transaction() as data:
        admins = data.setdefault("admins", [])
        normalized_email = _normalize_email(email)
        
        # Filtrar el email
        data["admins"] = [e for e in admins if _normalize_email(e) != normalized_email]
    return data["admins"]


# ============ BANNER DE MANTENIMIENTO ============

def get_maintenance_config() -> Dict[str, Any]:
    data = _read_permissions()
    # Ensure maintenance key exists inside _read_permissions, so just get it
    return data.get("maintenance", DEFAULT_PERMISSIONS["maintenance"])


def set_maintenance_mode(enabled: bool, message: Optional[str] = None) -> Dict[str, Any]:
    with permission_transaction() as data:
        if "maintenance" not in data:
            data["maintenance"] = DEFAULT_PERMISSIONS["maintenance"].copy()
        
        data["maintenance"]["enabled"] = enabled
        if message is not None:
            data["maintenance"]["message"] = message
    return data["maintenance"]


def is_maintenance_mode() -> bool:
    config = get_maintenance_config()
    return config.get("enabled", False)

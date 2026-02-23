"""Servicio de permisos para dashboards."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from threading import Lock

from backend.config import settings
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PERMISSIONS_FILE = DATA_DIR / "permissions.json"
PERMISSIONS_DB_FILE = DATA_DIR / "permissions.db"

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
        {"slug": "ajuste_proformas", "name": "💱 Ajuste Proformas"},
    ],
    "produccion": [
        {"slug": "reporteria_general", "name": "Reportería General"},
        {"slug": "detalle_of", "name": "Detalle de OF"},
        {"slug": "clasificacion", "name": "Clasificación"},
        {"slug": "automatizacion_of", "name": "Automatización OF"},
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


_DB_INIT_LOCK = Lock()
_DB_READY = False


def _read_permissions_file() -> Dict[str, Any]:
    if not PERMISSIONS_FILE.exists():
        return DEFAULT_PERMISSIONS.copy()
    try:
        with PERMISSIONS_FILE.open("r", encoding="utf-8") as handler:
            data: Dict[str, Any] = json.load(handler)
    except json.JSONDecodeError:
        data = DEFAULT_PERMISSIONS.copy()

    data.setdefault("dashboards", {})
    data.setdefault("pages", {})
    data.setdefault("admins", [])
    data.setdefault("maintenance", DEFAULT_PERMISSIONS["maintenance"].copy())
    return data


def _get_connection() -> sqlite3.Connection:
    return sqlite3.connect(PERMISSIONS_DB_FILE, timeout=15)


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS permission_dashboards (
            slug TEXT NOT NULL,
            email TEXT NOT NULL,
            PRIMARY KEY (slug, email)
        );

        CREATE TABLE IF NOT EXISTS permission_pages (
            module_slug TEXT NOT NULL,
            page_slug TEXT NOT NULL,
            email TEXT NOT NULL,
            PRIMARY KEY (module_slug, page_slug, email)
        );

        CREATE TABLE IF NOT EXISTS permission_admins (
            email TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS permission_maintenance (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            enabled INTEGER NOT NULL DEFAULT 0,
            message TEXT NOT NULL DEFAULT 'El sistema está siendo ajustado en este momento.'
        );
        
        -- Overrides de origen para recepciones
        CREATE TABLE IF NOT EXISTS override_origen (
            picking_name TEXT PRIMARY KEY,
            origen TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Exclusiones de valorización
        CREATE TABLE IF NOT EXISTS exclusiones_valorizacion (
            albaran TEXT PRIMARY KEY,
            motivo TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO permission_maintenance (id, enabled, message) VALUES (1, 0, ?)",
        (DEFAULT_PERMISSIONS["maintenance"]["message"],)
    )


def _is_db_empty(conn: sqlite3.Connection) -> bool:
    dashboards_count = conn.execute("SELECT COUNT(*) FROM permission_dashboards").fetchone()[0]
    pages_count = conn.execute("SELECT COUNT(*) FROM permission_pages").fetchone()[0]
    admins_count = conn.execute("SELECT COUNT(*) FROM permission_admins").fetchone()[0]
    return dashboards_count == 0 and pages_count == 0 and admins_count == 0


def _migrate_json_to_db(conn: sqlite3.Connection) -> None:
    source = _read_permissions_file()

    dashboards = source.get("dashboards", {})
    for slug, emails in dashboards.items():
        slug_key = _normalize_dashboard(slug)
        for email in emails or []:
            conn.execute(
                "INSERT OR IGNORE INTO permission_dashboards (slug, email) VALUES (?, ?)",
                (slug_key, _normalize_email(email))
            )

    pages = source.get("pages", {})
    for page_key, emails in pages.items():
        if "." not in page_key:
            continue
        module_slug, page_slug = page_key.split(".", 1)
        module_slug = _normalize_dashboard(module_slug)
        page_slug = page_slug.strip().lower()
        for email in emails or []:
            conn.execute(
                "INSERT OR IGNORE INTO permission_pages (module_slug, page_slug, email) VALUES (?, ?, ?)",
                (module_slug, page_slug, _normalize_email(email))
            )

    for admin_email in source.get("admins", []):
        conn.execute(
            "INSERT OR IGNORE INTO permission_admins (email) VALUES (?)",
            (_normalize_email(admin_email),)
        )

    maintenance = source.get("maintenance", DEFAULT_PERMISSIONS["maintenance"])
    conn.execute(
        "UPDATE permission_maintenance SET enabled = ?, message = ? WHERE id = 1",
        (
            1 if maintenance.get("enabled", False) else 0,
            maintenance.get("message", DEFAULT_PERMISSIONS["maintenance"]["message"]),
        )
    )


def _ensure_db() -> None:
    global _DB_READY
    if _DB_READY:
        return

    with _DB_INIT_LOCK:
        if _DB_READY:
            return

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with _get_connection() as conn:
            _init_schema(conn)
            if _is_db_empty(conn):
                _migrate_json_to_db(conn)
        _DB_READY = True


def _build_permissions_payload() -> Dict[str, Any]:
    _ensure_db()
    with _get_connection() as conn:
        dashboards: Dict[str, List[str]] = {slug: [] for slug in ALL_DASHBOARDS}
        for slug, email in conn.execute(
            "SELECT slug, email FROM permission_dashboards ORDER BY slug, email"
        ).fetchall():
            dashboards.setdefault(slug, []).append(email)

        pages: Dict[str, List[str]] = {}
        for module_slug, pages_data in MODULE_PAGES.items():
            for page in pages_data:
                pages[f"{module_slug}.{page['slug']}"] = []

        for module_slug, page_slug, email in conn.execute(
            "SELECT module_slug, page_slug, email FROM permission_pages ORDER BY module_slug, page_slug, email"
        ).fetchall():
            page_key = f"{module_slug}.{page_slug}"
            pages.setdefault(page_key, []).append(email)

        admins = [
            row[0]
            for row in conn.execute("SELECT email FROM permission_admins ORDER BY email").fetchall()
        ]

        maintenance_row = conn.execute(
            "SELECT enabled, message FROM permission_maintenance WHERE id = 1"
        ).fetchone()
        if maintenance_row:
            maintenance = {
                "enabled": bool(maintenance_row[0]),
                "message": maintenance_row[1],
            }
        else:
            maintenance = DEFAULT_PERMISSIONS["maintenance"].copy()

    return {
        "dashboards": dashboards,
        "pages": pages,
        "admins": admins,
        "maintenance": maintenance,
    }


def get_permissions_map() -> Dict[str, List[str]]:
    return _build_permissions_payload()["dashboards"]


def get_admins() -> List[str]:
    return _build_permissions_payload().get("admins", [])


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
    _ensure_db()
    with _get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO permission_dashboards (slug, email) VALUES (?, ?)",
            (_normalize_dashboard(slug), _normalize_email(email)),
        )
    return get_permissions_map()


def remove_dashboard(slug: str, email: str) -> Dict[str, List[str]]:
    _ensure_db()
    with _get_connection() as conn:
        conn.execute(
            "DELETE FROM permission_dashboards WHERE slug = ? AND email = ?",
            (_normalize_dashboard(slug), _normalize_email(email)),
        )
    return get_permissions_map()


def get_full_permissions() -> Dict[str, Any]:
    return _build_permissions_payload()


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
    return _build_permissions_payload().get("pages", {})


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
    _ensure_db()
    with _get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO permission_pages (module_slug, page_slug, email) VALUES (?, ?, ?)",
            (_normalize_dashboard(module), page.strip().lower(), _normalize_email(email)),
        )
    return get_page_permissions()


def remove_page(module: str, page: str, email: str) -> Dict[str, List[str]]:
    _ensure_db()
    with _get_connection() as conn:
        conn.execute(
            "DELETE FROM permission_pages WHERE module_slug = ? AND page_slug = ? AND email = ?",
            (_normalize_dashboard(module), page.strip().lower(), _normalize_email(email)),
        )
    return get_page_permissions()


def clear_page_restriction(module: str, page: str) -> Dict[str, List[str]]:
    _ensure_db()
    with _get_connection() as conn:
        conn.execute(
            "DELETE FROM permission_pages WHERE module_slug = ? AND page_slug = ?",
            (_normalize_dashboard(module), page.strip().lower()),
        )
    return get_page_permissions()


# ============ ADMINISTRADORES ============

def assign_admin(email: str) -> List[str]:
    """Agrega un email a la lista de administradores."""
    _ensure_db()
    with _get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO permission_admins (email) VALUES (?)",
            (_normalize_email(email),),
        )
    return get_admins()


def remove_admin(email: str) -> List[str]:
    """Remueve un email de la lista de administradores."""
    _ensure_db()
    with _get_connection() as conn:
        conn.execute(
            "DELETE FROM permission_admins WHERE email = ?",
            (_normalize_email(email),),
        )
    return get_admins()


# ============ BANNER DE MANTENIMIENTO ============

def get_maintenance_config() -> Dict[str, Any]:
    _ensure_db()
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT enabled, message FROM permission_maintenance WHERE id = 1"
        ).fetchone()
        if not row:
            return DEFAULT_PERMISSIONS["maintenance"].copy()
        return {"enabled": bool(row[0]), "message": row[1]}


def set_maintenance_mode(enabled: bool, message: Optional[str] = None) -> Dict[str, Any]:
    _ensure_db()
    with _get_connection() as conn:
        current = conn.execute(
            "SELECT message FROM permission_maintenance WHERE id = 1"
        ).fetchone()
        final_message = message if message is not None else (
            current[0] if current else DEFAULT_PERMISSIONS["maintenance"]["message"]
        )
        conn.execute(
            "UPDATE permission_maintenance SET enabled = ?, message = ? WHERE id = 1",
            (1 if enabled else 0, final_message),
        )
    return get_maintenance_config()


def is_maintenance_mode() -> bool:
    config = get_maintenance_config()
    return config.get("enabled", False)


# ============ OVERRIDE DE ORIGEN DE RECEPCIONES ============

def get_override_origen_map() -> Dict[str, str]:
    """Obtiene todos los overrides de origen como diccionario {picking: origen}."""
    _ensure_db()
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT picking_name, origen FROM override_origen ORDER BY picking_name"
        ).fetchall()
    return {row[0]: row[1] for row in rows}


def get_override_origen_list() -> List[Dict[str, str]]:
    """Obtiene lista de overrides con fecha de creación."""
    _ensure_db()
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT picking_name, origen, created_at FROM override_origen ORDER BY created_at DESC"
        ).fetchall()
    return [{"picking_name": r[0], "origen": r[1], "created_at": r[2]} for r in rows]


def add_override_origen(picking_name: str, origen: str) -> Dict[str, str]:
    """Agrega o actualiza un override de origen."""
    _ensure_db()
    picking = picking_name.strip().upper()
    orig = origen.strip().upper()
    if orig not in ("RFP", "VILKUN", "SAN JOSE"):
        raise ValueError(f"Origen inválido: {orig}. Debe ser RFP, VILKUN o SAN JOSE")
    
    with _get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO override_origen (picking_name, origen, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (picking, orig),
        )
    return get_override_origen_map()


def remove_override_origen(picking_name: str) -> Dict[str, str]:
    """Elimina un override de origen."""
    _ensure_db()
    with _get_connection() as conn:
        conn.execute(
            "DELETE FROM override_origen WHERE picking_name = ?",
            (picking_name.strip().upper(),),
        )
    return get_override_origen_map()


def bulk_add_override_origen(overrides: Dict[str, str]) -> Dict[str, str]:
    """Agrega múltiples overrides de una vez (para migración)."""
    _ensure_db()
    with _get_connection() as conn:
        for picking, origen in overrides.items():
            picking = picking.strip().upper()
            orig = origen.strip().upper()
            if orig in ("RFP", "VILKUN", "SAN JOSE"):
                conn.execute(
                    "INSERT OR IGNORE INTO override_origen (picking_name, origen) VALUES (?, ?)",
                    (picking, orig),
                )
    return get_override_origen_map()


# ============ EXCLUSIONES DE VALORIZACIÓN ============

def get_exclusiones_list() -> List[Dict[str, str]]:
    """Obtiene lista de exclusiones con motivo y fecha."""
    _ensure_db()
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT albaran, motivo, created_at FROM exclusiones_valorizacion ORDER BY created_at DESC"
        ).fetchall()
    return [{"albaran": r[0], "motivo": r[1] or "", "created_at": r[2]} for r in rows]


def get_exclusiones_set() -> set:
    """Obtiene set de albaranes excluidos (para búsqueda rápida)."""
    _ensure_db()
    with _get_connection() as conn:
        rows = conn.execute("SELECT albaran FROM exclusiones_valorizacion").fetchall()
    return {r[0] for r in rows}


def add_exclusion(albaran: str, motivo: str = "") -> List[Dict[str, str]]:
    """Agrega una exclusión."""
    _ensure_db()
    with _get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO exclusiones_valorizacion (albaran, motivo, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (albaran.strip(), motivo.strip()),
        )
    return get_exclusiones_list()


def remove_exclusion(albaran: str) -> List[Dict[str, str]]:
    """Elimina una exclusión."""
    _ensure_db()
    with _get_connection() as conn:
        conn.execute(
            "DELETE FROM exclusiones_valorizacion WHERE albaran = ?",
            (albaran.strip(),),
        )
    return get_exclusiones_list()


def bulk_add_exclusiones(albaranes: List[str], motivo: str = "Migración desde JSON") -> List[Dict[str, str]]:
    """Agrega múltiples exclusiones de una vez (para migración)."""
    _ensure_db()
    with _get_connection() as conn:
        for albaran in albaranes:
            conn.execute(
                "INSERT OR IGNORE INTO exclusiones_valorizacion (albaran, motivo) VALUES (?, ?)",
                (albaran.strip(), motivo),
            )
    return get_exclusiones_list()

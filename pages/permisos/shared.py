"""
Módulo compartido para Permisos.
Contiene CSS, constantes y funciones API comunes.
"""
import os
import httpx
import streamlit as st

# Determinar API_URL basado en ENV
ENV = os.getenv("ENV", "production")
if ENV == "development":
    API_URL = "http://127.0.0.1:8002"  # Puerto DEV
else:
    API_URL = "http://127.0.0.1:8000"  # Puerto PROD

# --------------------- Mapeo de nombres ---------------------

MODULE_NAMES = {
    "recepciones": "📥 Recepciones",
    "produccion": "🏭 Producción",
    "reconciliacion": "🔄 Reconciliación",
    "bandejas": "📊 Bandejas",
    "stock": "📦 Stock",
    "pedidos_venta": "🚢 Pedidos de Venta",
    "rendimiento": "🔍 Trazabilidad",
    "relacion_comercial": "🤝 Relación Comercial",
    "automatizaciones": "🦾 Automatizaciones",
    "finanzas": "💰 Finanzas",
    "compras": "🛒 Compras",
    "permisos": "⚙️ Permisos",
}

# --------------------- CSS Global ---------------------

CSS_GLOBAL = """
<style>
.permission-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
    border: 1px solid #3498db44;
    transition: all 0.3s ease;
}
.permission-card:hover {
    border-color: #3498db88;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
.module-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    border-bottom: 1px solid #ffffff11;
}
.module-row:last-child {
    border-bottom: none;
}
.badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}
.badge-public { background: #2ecc71; color: white; }
.badge-restricted { background: #e74c3c; color: white; }
</style>
"""


# --------------------- Funciones API ---------------------

@st.cache_data(ttl=30)
def fetch_full_permissions(username: str, password: str, version: int = 0):
    """Obtiene todos los permisos (módulos y páginas)."""
    try:
        resp = httpx.get(
            f"{API_URL}/api/v1/permissions/all",
            params={"admin_username": username, "admin_password": password},
            timeout=10.0
        )
        resp.raise_for_status()
        return resp.json()
    except:
        return {"dashboards": {}, "pages": {}, "admins": []}


@st.cache_data(ttl=60)
def fetch_module_structure():
    """Obtiene la estructura de módulos y páginas."""
    try:
        resp = httpx.get(f"{API_URL}/api/v1/permissions/pages/structure", timeout=10.0)
        resp.raise_for_status()
        return resp.json().get("modules", {})
    except:
        return {}


def update_module_permission(action: str, dashboard: str, email: str, username: str, password: str):
    """Asigna o revoca permiso a un módulo."""
    if not email:
        st.error("Email requerido")
        return False
    
    try:
        resp = httpx.post(
            f"{API_URL}/api/v1/permissions/{action}",
            json={
                "dashboard": dashboard,
                "email": email,
                "admin_username": username,
                "admin_password": password
            },
            timeout=10.0
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False


def update_page_permission(action: str, module: str, page: str, email: str, username: str, password: str):
    """Asigna o revoca permiso a una página."""
    if not email:
        st.error("Email requerido")
        return False
    
    try:
        resp = httpx.post(
            f"{API_URL}/api/v1/permissions/pages/{action}",
            json={
                "module": module,
                "page": page,
                "email": email,
                "admin_username": username,
                "admin_password": password
            },
            timeout=10.0
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False


def get_user_permissions(email: str):
    """Obtiene los permisos de un usuario específico."""
    try:
        resp = httpx.get(f"{API_URL}/api/v1/permissions/user", params={"username": email})
        if resp.status_code == 200:
            return resp.json()
        return None
    except:
        return None


def get_maintenance_config():
    """Obtiene la configuración de mantenimiento."""
    try:
        resp = httpx.get(f"{API_URL}/api/v1/permissions/maintenance/status")
        if resp.status_code == 200:
            return resp.json()
        return {"enabled": False, "message": ""}
    except:
        return {"enabled": False, "message": ""}


def save_maintenance_config(enabled: bool, message: str, username: str, password: str):
    """Guarda la configuración de mantenimiento."""
    try:
        httpx.post(f"{API_URL}/api/v1/permissions/maintenance", json={
            "enabled": enabled,
            "message": message,
            "admin_username": username,
            "admin_password": password
        })
        return True
    except:
        return False


# --------------------- Inicialización de Session State ---------------------

def init_session_state():
    """Inicializa variables de session_state para el módulo."""
    if "perms_version" not in st.session_state:
        st.session_state.perms_version = 0
    if "permisos_consultar_loading" not in st.session_state:
        st.session_state.permisos_consultar_loading = False
    if "permisos_config_loading" not in st.session_state:
        st.session_state.permisos_config_loading = False
    if "permisos_buscar_loading" not in st.session_state:
        st.session_state.permisos_buscar_loading = False
    if "permisos_excluir_loading" not in st.session_state:
        st.session_state.permisos_excluir_loading = False


def refresh_perms():
    """Incrementa la versión para refrescar permisos."""
    st.session_state.perms_version += 1
    st.cache_data.clear()

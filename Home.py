"""
Rio Futuro Dashboards - Página Principal
Sistema unificado de dashboards para gestión de datos Odoo
"""
import os

import httpx
import streamlit as st

from shared.auth import guardar_permisos_state


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


def fetch_permissions(username: str) -> dict | None:
    try:
        resp = httpx.get(
            f"{API_URL}/api/v1/permissions/user",
            params={"username": username},
            timeout=10.0
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError:
        return None


def ensure_permissions(username: str) -> None:
    if not username:
        guardar_permisos_state({}, [], False)
        return
    if 'restricted_dashboards' in st.session_state:
        return
    permisos = fetch_permissions(username)
    if permisos:
        guardar_permisos_state(
            permisos.get('restricted', {}),
            permisos.get('allowed', []),
            permisos.get('is_admin', False)
        )
    else:
        guardar_permisos_state({}, [], False)


def is_user_authenticated() -> bool:
    """Verifica si hay un usuario autenticado en session_state o query_params."""
    # Verificar session_state primero (más confiable)
    if st.session_state.get('authenticated') and st.session_state.get('username'):
        return True
    # Verificar query_params (persistencia entre recargas)
    token = st.query_params.get('token')
    if token and token != '':
        return True
    return False


# Definir páginas con iconos usando st.navigation
home_page = st.Page("Home_Content.py", title="Home", icon="🏠", default=True)

# Asegurar permisos están cargados antes de verificar autenticación
username = st.session_state.get('username', '')
if username and not st.session_state.get('restricted_dashboards'):
    ensure_permissions(username)

# Solo mostrar las demás páginas si el usuario está autenticado
if is_user_authenticated() and username:
    # Obtener información del usuario
    username = st.session_state.get('username', '')
    is_admin = st.session_state.get('is_admin', False)
    restricted_dashboards = st.session_state.get('restricted_dashboards', {})
    
    def tiene_acceso(dashboard_key: str) -> bool:
        """Verifica si el usuario tiene acceso a un dashboard."""
        if is_admin:
            return True
        # Si el dashboard no está en restricted o está vacío, es público
        if dashboard_key not in restricted_dashboards:
            return True
        usuarios_permitidos = restricted_dashboards.get(dashboard_key, [])
        if not usuarios_permitidos:  # Lista vacía = público
            return True
        return username in usuarios_permitidos
    
    # Definir todas las páginas posibles
    all_pages = {
        "Operaciones": [
            ("recepciones", st.Page("pages/1_Recepciones.py", title="Recepciones", icon="📥")),
            ("produccion", st.Page("pages/2_Produccion.py", title="Producción", icon="🏭")),
            ("reconciliacion", st.Page("pages/12_Reconciliacion_Produccion.py", title="Reconciliación", icon="🔄")),
            ("bandejas", st.Page("pages/3_Bandejas.py", title="Bandejas", icon="📊")),
            ("stock", st.Page("pages/4_Stock.py", title="Stock", icon="📦")),
            ("pedidos_venta", st.Page("pages/5_Pedidos_Venta.py", title="Pedidos de Venta", icon="🚢")),
            ("rendimiento", st.Page("pages/7_Rendimiento.py", title="Trazabilidad", icon="🔍")),
            ("relacion_comercial", st.Page("pages/11_Relacion_Comercial.py", title="Relación Comercial", icon="🤝")),
            ("automatizaciones", st.Page("pages/10_Automatizaciones.py", title="Automatizaciones", icon="🦾")),
        ],
        "Finanzas": [
            ("finanzas", st.Page("pages/6_Finanzas.py", title="Finanzas", icon="💰")),
            ("compras", st.Page("pages/8_Compras.py", title="Compras", icon="🛒")),
        ],
        "Administración": [
            ("permisos", st.Page("pages/9_Permisos.py", title="Permisos", icon="⚙️")),
        ],
    }
    
    # Filtrar páginas según permisos
    pages = {}
    for category, category_pages in all_pages.items():
        filtered_pages = [page for dashboard_key, page in category_pages if tiene_acceso(dashboard_key)]
        if filtered_pages:  # Solo agregar categoría si tiene páginas visibles
            pages[category] = filtered_pages
    
    # Navegación con páginas filtradas
    nav = st.navigation([home_page] + [p for group in pages.values() for p in group])
else:
    # Usuario no autenticado: solo mostrar Home (login)
    nav = st.navigation([home_page])

nav.run()


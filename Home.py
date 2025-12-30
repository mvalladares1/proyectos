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


# Definir páginas con iconos usando st.navigation
home_page = st.Page("Home_Content.py", title="Home", icon="🏠", default=True)

pages = {
    "Operaciones": [
        st.Page("pages/1_Recepciones.py", title="Recepciones", icon="📥"),
        st.Page("pages/2_Produccion.py", title="Producción", icon="🏭"),
        st.Page("pages/3_Bandejas.py", title="Bandejas", icon="📊"),
        st.Page("pages/4_Stock.py", title="Stock", icon="📦"),
        st.Page("pages/5_Containers.py", title="Containers", icon="🚢"),
        st.Page("pages/7_Rendimiento.py", title="Rendimiento", icon="📈"),
        st.Page("pages/11_Relacion_Comercial.py", title="Relación Comercial", icon="🤝"),
        st.Page("pages/10_Automatizaciones.py", title="Automatizaciones", icon="🤖"),
    ],
    "Finanzas": [
        st.Page("pages/6_Finanzas.py", title="Finanzas", icon="💰"),
        st.Page("pages/8_Compras.py", title="Compras", icon="🛒"),
    ],
    "Administración": [
        st.Page("pages/9_Permisos.py", title="Permisos", icon="⚙️"),
    ],
}

# Navegación
nav = st.navigation([home_page] + [p for group in pages.values() for p in group])
nav.run()

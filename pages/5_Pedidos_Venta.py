"""
Seguimiento de ventas y despachos: pedidos de venta y avance de producción por cliente.

Este archivo es el orquestador principal que importa y renderiza el contenido modular.
Ahora con dos tabs: Progreso de Ventas y Proyección de Ventas.
"""
import streamlit as st
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.auth import proteger_modulo, tiene_acceso_dashboard, get_credenciales, tiene_acceso_pagina

# Añadir pages al path para imports de containers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos
from containers import content, shared, tab_proyeccion, tab_calendario

# Configuración de la página
st.set_page_config(
    page_title="Pedidos de Venta",
    page_icon="🚢",
    layout="wide"
)

# Proteger la página
if not proteger_modulo("pedidos_venta"):
    st.stop()

if not tiene_acceso_dashboard("pedidos_venta"):
    st.error("No tienes permisos para ver este dashboard.")
    st.stop()

# Inicializar session state
shared.init_session_state()

# Título
st.title("🚢 Dashboard de Pedidos de Venta")
st.markdown("Seguimiento de producción y proyección por pedido de venta")

# Obtener credenciales
username, password = get_credenciales()

if not (username and password):
    st.error("No se encontraron credenciales válidas en la sesión.")
    st.stop()

# ============================================================================
# TABS PRINCIPALES
# ============================================================================

tab_progreso, tab_proyeccion_ui, tab_calendario_ui = st.tabs([
    "📦 Progreso de Ventas",
    "📊 Proyección de Ventas",
    "📅 Calendario"
])

# Tab 1: Progreso de Ventas (contenido existente)
with tab_progreso:
    content.render(username, password)

# Tab 2: Proyección de Ventas (nuevo)
with tab_proyeccion_ui:
    tab_proyeccion.render(username, password)

# Tab 3: Calendario (nuevo)
with tab_calendario_ui:
    tab_calendario.render(username, password)

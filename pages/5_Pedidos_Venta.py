"""
Seguimiento de ventas y despachos: pedidos de venta y avance de producción por cliente.

Este archivo es el orquestador principal que importa y renderiza el contenido modular.
"""
import streamlit as st
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.auth import proteger_modulo, tiene_acceso_dashboard, get_credenciales

# Añadir pages al path para imports de containers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos
from containers import content, shared

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
st.markdown("Seguimiento de producción por pedido de venta")

# Obtener credenciales
username, password = get_credenciales()

if not (username and password):
    st.error("No se encontraron credenciales válidas en la sesión.")
    st.stop()

# Renderizar contenido
content.render(username, password)

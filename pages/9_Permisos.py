"""
Panel de administración: gestiona qué usuarios pueden acceder a cada dashboard y página.

Este archivo es el orquestador principal que importa y renderiza el contenido modular.
"""
import streamlit as st
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.auth import es_admin, proteger_modulo, get_credenciales

# Añadir pages al path para imports de permisos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos
from permisos import shared
from permisos import content

# Configuración de página
st.set_page_config(
    page_title="Permisos",
    page_icon="⚙️",
    layout="wide"
)

# Verificar autenticación y permisos
if not proteger_modulo("permisos"):
    st.stop()

if not es_admin():
    st.error("Solo administradores pueden acceder a este panel.")
    st.stop()

# Obtener credenciales
username, password = get_credenciales()
if not username or not password:
    st.warning("Inicia sesión con credenciales válidas para administrar los permisos.")
    st.stop()

# Inicializar session state
shared.init_session_state()

# CSS Global
st.markdown(shared.CSS_GLOBAL, unsafe_allow_html=True)

# Renderizar contenido
content.render(username, password)

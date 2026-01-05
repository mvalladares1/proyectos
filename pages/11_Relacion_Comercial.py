"""
Dashboard de Relación Comercial - Rio Futuro
Muestra análisis de ventas por cliente, programa, manejo y especie.

Este archivo es el orquestador principal que importa y renderiza el contenido modular.
"""
import streamlit as st
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.auth import proteger_modulo, get_credenciales
from backend.services.comercial_service import ComercialService

# Añadir pages al path para imports de relacion_comercial
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos
from relacion_comercial import shared
from relacion_comercial import content

# Configuración de página
st.set_page_config(
    layout="wide", 
    page_title="Relación Comercial", 
    page_icon="📊",
    initial_sidebar_state="collapsed"
)

# Verificar autenticación
if not proteger_modulo("relacion_comercial"):
    st.stop()

# Obtener credenciales
username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales. Por favor inicie sesión nuevamente.")
    st.stop()

# Instanciar servicio
comercial_service = ComercialService(
    username=username, 
    password=password
)

# Inicializar session state
shared.init_session_state()

# CSS Global
st.markdown(shared.CSS_GLOBAL, unsafe_allow_html=True)

# Renderizar contenido
content.render(comercial_service, username, password)

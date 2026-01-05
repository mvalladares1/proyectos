"""
Recepción de bandejas desde procesos externos. Control de cantidades y trazabilidad por proveedor.

Este archivo es el orquestador principal que importa y renderiza el contenido modular.
"""
import streamlit as st
import sys
import os

# Añadir el directorio raíz al path para imports de shared/auth
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.auth import verificar_autenticacion, proteger_modulo, get_credenciales

# Añadir el directorio pages al path para imports de bandejas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos
from bandejas import shared
from bandejas import content

# Configuración de página
st.set_page_config(page_title="Bandejas", page_icon="📊", layout="wide")

# Autenticación central
if not proteger_modulo("bandejas"):
    st.stop()

# Obtener credenciales del usuario autenticado
username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales. Por favor inicie sesión nuevamente.")
    st.stop()

# Inicializar session state del módulo
shared.init_session_state()

# Título de la página
st.title("Recepción Bandejas Río Futuro Procesos")

# Renderizar contenido
content.render(username, password)

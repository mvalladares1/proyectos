"""
Rendimiento Productivo: Dashboard de trazabilidad.
Trazabilidad: Lote MP → MO → Lote PT

Este archivo es el orquestador principal que importa y renderiza el contenido modular.
"""
import streamlit as st
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.auth import proteger_modulo, get_credenciales

# Añadir pages al path para imports de rendimiento
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos
from rendimiento import content

# Configuración de página
st.set_page_config(page_title="Trazabilidad", page_icon="🔍", layout="wide")

# Autenticación
if not proteger_modulo("trazabilidad"):
    st.stop()

username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales. Por favor inicie sesión nuevamente.")
    st.stop()

# Título
st.title("🔍 Trazabilidad Productiva")
st.caption("Seguimiento de lotes: Materia Prima (MP) → Producto Terminado (PT)")

# Renderizar contenido
content.render(username, password)

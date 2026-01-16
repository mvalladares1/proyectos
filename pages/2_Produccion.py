"""
Órdenes de fabricación: seguimiento de producción, rendimientos y consumo de materias primas.

Este archivo es el orquestador principal que importa y renderiza los tabs modulares.
"""
import streamlit as st
import sys
import os

# Añadir el directorio raíz al path para imports de shared/auth
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.auth import proteger_modulo, get_credenciales, tiene_acceso_dashboard, tiene_acceso_pagina

# Añadir el directorio pages al path para imports de produccion
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos de tabs
from produccion import shared
from produccion import tab_reporteria
from produccion import tab_detalle
from produccion import tab_clasificacion

# Configuración de página
st.set_page_config(page_title="Producción", page_icon="🏭", layout="wide")

# Verificar autenticación
if not proteger_modulo("produccion"):
    st.stop()

if not tiene_acceso_dashboard("produccion"):
    st.error("No tienes permisos para ver este dashboard.")
    st.stop()

# Obtener credenciales
username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales válidas.")
    st.stop()

# Inicializar session state del módulo
shared.init_session_state()

# Título principal
st.title("🏭 Dashboard de Producción")
st.caption("Monitorea rendimientos productivos y detalle de órdenes de fabricación")

# === PRE-CALCULAR PERMISOS ===
_perm_reporteria = tiene_acceso_pagina("produccion", "reporteria_general")
_perm_detalle = tiene_acceso_pagina("produccion", "detalle_of")
_perm_clasificacion = tiene_acceso_pagina("produccion", "clasificacion")

# === CONSTRUIR TABS DINÁMICAMENTE SEGÚN PERMISOS ===
tabs_disponibles = []
tabs_nombres = []

if _perm_reporteria:
    tabs_nombres.append("📊 Reportería General")
    tabs_disponibles.append("reporteria")

if _perm_detalle:
    tabs_nombres.append("📋 Detalle de OF")
    tabs_disponibles.append("detalle")

if _perm_clasificacion:
    tabs_nombres.append("📦 Clasificación")
    tabs_disponibles.append("clasificacion")

if not tabs_disponibles:
    st.error("🚫 **Acceso Restringido** - No tienes permisos para acceder a ninguna sección de Producción.")
    st.info("💡 Contacta al administrador para solicitar acceso.")
    st.stop()

tabs_ui = st.tabs(tabs_nombres)
tab_index = 0

if "reporteria" in tabs_disponibles:
    with tabs_ui[tab_index]:
        tab_reporteria.render(username, password)
    tab_index += 1

if "detalle" in tabs_disponibles:
    with tabs_ui[tab_index]:
        tab_detalle.render(username, password)
    tab_index += 1

if "clasificacion" in tabs_disponibles:
    with tabs_ui[tab_index]:
        tab_clasificacion.render(username, password)
    tab_index += 1

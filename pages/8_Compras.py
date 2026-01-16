"""
Compras: Dashboard de Órdenes de Compra (PO) y Líneas de Crédito
Estados de aprobación, recepción y monitoreo de crédito.

Este archivo es el orquestador principal que importa y renderiza los tabs modulares.
"""
import streamlit as st
import sys
import os

# Añadir el directorio raíz al path para imports de shared/auth
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.auth import proteger_modulo, get_credenciales, tiene_acceso_pagina

# Añadir el directorio pages al path para imports de compras
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos de tabs
from compras import shared
from compras import tab_ordenes
from compras import tab_lineas_credito

# Configuración de página
st.set_page_config(page_title="Compras", page_icon="🛒", layout="wide")

# Autenticación central
if not proteger_modulo("compras"):
    st.stop()

# Obtener credenciales del usuario autenticado
username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales.")
    st.stop()

# Inicializar session state del módulo
shared.init_session_state()

# Título de la página
st.title("🛒 Compras y Líneas de Crédito")

# === PRE-CALCULAR PERMISOS ===
_perm_ordenes = tiene_acceso_pagina("compras", "ordenes")
_perm_lineas = tiene_acceso_pagina("compras", "lineas_credito")

# === CONSTRUIR TABS DINÁMICAMENTE SEGÚN PERMISOS ===
tabs_disponibles = []
tabs_nombres = []

if _perm_ordenes:
    tabs_nombres.append("📋 Órdenes de Compra")
    tabs_disponibles.append("ordenes")

if _perm_lineas:
    tabs_nombres.append("💳 Líneas de Crédito")
    tabs_disponibles.append("lineas")

if not tabs_disponibles:
    st.error("🚫 **Acceso Restringido** - No tienes permisos para acceder a ninguna sección de Compras.")
    st.info("💡 Contacta al administrador para solicitar acceso.")
    st.stop()

tabs_ui = st.tabs(tabs_nombres)
tab_index = 0

if "ordenes" in tabs_disponibles:
    with tabs_ui[tab_index]:
        tab_ordenes.render(username, password)
    tab_index += 1

if "lineas" in tabs_disponibles:
    with tabs_ui[tab_index]:
        tab_lineas_credito.render(username, password)
    tab_index += 1

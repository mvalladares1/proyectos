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

# CSS Global Forzado (Dark Mode)
# CSS Global Forzado (Dark Mode) - INLINED to avoid cache issues
st.markdown("""
<style>
    /* Force Dark Theme Main Colors */
    [data-testid="stAppViewContainer"] { 
        background-color: #0e1117 !important; 
        color: #ffffff !important;
    }
    [data-testid="stHeader"] { 
        background-color: rgba(14, 17, 23, 0.9) !important; 
    }
    [data-testid="stSidebar"] { 
        background-color: #262730 !important; 
        color: #ffffff !important;
    }
    
    /* Text Colors */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stCaption {
        color: #ffffff !important;
    }
    
    /* Standard Card Style */
    .info-card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    
    /* Inputs */
    .stTextInput input, .stSelectbox, .stDateInput input, .stNumberInput input {
        color: #ffffff !important; 
        background-color: #1a1c23 !important;
        border-color: #334155 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8 !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #3b82f6 !important;
        border-bottom-color: #3b82f6 !important;
    }
</style>
""", unsafe_allow_html=True)


# Título principal
st.title("🏭 Dashboard de Producción")
st.caption("Monitorea rendimientos productivos y detalle de órdenes de fabricación")

# === PRE-CALCULAR PERMISOS ===
_perm_reporteria = tiene_acceso_pagina("produccion", "reporteria_general")
_perm_detalle = tiene_acceso_pagina("produccion", "detalle_of")
_perm_clasificacion = tiene_acceso_pagina("produccion", "clasificacion")

# === TABS PRINCIPALES ===
tab_general, tab_detalle_ui, tab_clasificacion_ui = st.tabs([
    "📊 Reportería General", 
    "📋 Detalle de OF", 
    "📦 Clasificación"
])

# =====================================================
#           TAB 1: REPORTERÍA GENERAL
# =====================================================
with tab_general:
    if _perm_reporteria:
        tab_reporteria.render(username, password)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Reportería General'. Contacta al administrador.")

# =====================================================
#           TAB 2: DETALLE DE OF
# =====================================================
with tab_detalle_ui:
    if _perm_detalle:
        tab_detalle.render(username, password)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Detalle de OF'. Contacta al administrador.")

# =====================================================
#           TAB 3: CLASIFICACIÓN
# =====================================================
with tab_clasificacion_ui:
    if _perm_clasificacion:
        tab_clasificacion.render(username, password)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Clasificación'. Contacta al administrador.")



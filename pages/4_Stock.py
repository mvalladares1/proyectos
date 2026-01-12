"""
Inventario en cámaras de frío: ubicaciones, pallets, lotes y trazabilidad de producto terminado.

Este archivo es el orquestador principal que importa y renderiza los tabs modulares.
"""
import streamlit as st
import sys
import os
from datetime import datetime

# Añadir el directorio raíz al path para imports de shared/auth
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.auth import proteger_modulo, tiene_acceso_dashboard, get_credenciales, tiene_acceso_pagina

# Añadir el directorio pages al path para imports de stock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos de tabs
from stock import shared
from stock import tab_movimientos
from stock import tab_camaras
from stock import tab_pallets
from stock import tab_trazabilidad

# Configuración de página
st.set_page_config(page_title="Stock", page_icon="📦", layout="wide")

# Autenticación central
if not proteger_modulo("stock"):
    st.stop()

if not tiene_acceso_dashboard("stock"):
    st.error("No tienes permisos para ver este dashboard.")
    st.stop()

# Obtener credenciales del usuario autenticado
username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales válidas en la sesión.")
    st.stop()

# Inicializar session state del módulo
shared.init_session_state()

# Título de la página
st.title("📦 Stock y Cámaras")
st.markdown("Gestión de inventario, ubicaciones y trazabilidad de pallets")

# Filtros de fecha (globales)
st.markdown("### 📅 Filtros de Fecha")
col_fecha1, col_fecha2 = st.columns(2)
with col_fecha1:
    fecha_desde_stock = st.date_input(
        "Fecha desde",
        datetime(2025, 11, 24),
        format="DD/MM/YYYY",
        key="stock_fecha_desde"
    )
with col_fecha2:
    fecha_hasta_stock = st.date_input(
        "Fecha hasta", 
        datetime.now(),
        format="DD/MM/YYYY",
        key="stock_fecha_hasta"
    )

# Panel de configuración de capacidades
with st.expander("⚙️ Configurar Capacidades", expanded=False):
    st.markdown("Modifica la capacidad de pallets de cada ubicación:")
    
    # Inicializar capacidades en session_state si no existen
    if "capacidades_config" not in st.session_state:
        st.session_state.capacidades_config = shared.get_capacidades_default()
    
    cap_cols = st.columns(2)
    ubicaciones = list(st.session_state.capacidades_config.keys())
    
    for i, ubicacion in enumerate(ubicaciones):
        with cap_cols[i % 2]:
            nueva_cap = st.number_input(
                f"📦 {ubicacion}",
                min_value=0,
                max_value=2000,
                value=st.session_state.capacidades_config[ubicacion],
                step=10,
                key=f"cap_{ubicacion.replace('/', '_').replace(' ', '_').replace('°', '')}"
            )
            st.session_state.capacidades_config[ubicacion] = nueva_cap
    
    st.caption("💡 Los cambios se aplican automáticamente al recargar los datos.")

st.markdown("---")

# === BOTÓN DE CARGA ===
col_carga1, col_carga2 = st.columns([1, 4])
with col_carga1:
    btn_cargar_stock = st.button("🔍 Cargar Stock", type="primary", key="btn_cargar_stock", disabled=st.session_state.get('stock_loading', False))

if not btn_cargar_stock and not st.session_state.get('stock_data_loaded', False):
    st.info("📋 Haz clic en 'Cargar Stock' para consultar información de cámaras en el rango seleccionado")
    st.stop()

# === CARGA GLOBAL DE CÁMARAS ===
st.session_state.stock_loading = True
try:
    with st.spinner("Cargando datos de cámaras..."):
        camaras_data_all = shared.fetch_camaras(username, password, fecha_desde_stock, fecha_hasta_stock)
    st.session_state.stock_data_loaded = True
finally:
    st.session_state.stock_loading = False

# Determinar si mostrar todas o solo principales
if st.session_state.get("mostrar_todas_camaras", False):
    camaras_data = camaras_data_all
else:
    camaras_data = shared.filtrar_camaras_principales(camaras_data_all) if camaras_data_all else []

# === PRE-CALCULAR PERMISOS ===
_perm_movimientos = tiene_acceso_pagina("stock", "movimientos")
_perm_camaras = tiene_acceso_pagina("stock", "camaras")
_perm_pallets = tiene_acceso_pagina("stock", "pallets")
_perm_trazabilidad = tiene_acceso_pagina("stock", "trazabilidad")

# === TABS PRINCIPALES ===
tab_mov_ui, tab_cam_ui, tab_pal_ui, tab_tra_ui = st.tabs([
    "📲 Movimientos", 
    "🏢 Cámaras", 
    "📦 Pallets", 
    "🏷️ Trazabilidad"
])

# =====================================================
#           TAB 1: MOVIMIENTOS
# =====================================================
with tab_mov_ui:
    if _perm_movimientos:
        tab_movimientos.render(username, password, camaras_data_all)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Movimientos'. Contacta al administrador.")
        st.info("💡 Contacta al administrador para solicitar acceso a esta sección.")

# =====================================================
#           TAB 2: CÁMARAS
# =====================================================
with tab_cam_ui:
    if _perm_camaras:
        tab_camaras.render(username, password, camaras_data_all)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Cámaras'. Contacta al administrador.")
        st.info("💡 Contacta al administrador para solicitar acceso a esta sección.")

# =====================================================
#           TAB 3: PALLETS
# =====================================================
with tab_pal_ui:
    if _perm_pallets:
        tab_pallets.render(username, password, camaras_data)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Pallets'. Contacta al administrador.")
        st.info("💡 Contacta al administrador para solicitar acceso a esta sección.")

# =====================================================
#           TAB 4: TRAZABILIDAD
# =====================================================
with tab_tra_ui:
    if _perm_trazabilidad:
        tab_trazabilidad.render(username, password, camaras_data)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Trazabilidad'. Contacta al administrador.")
        st.info("💡 Contacta al administrador para solicitar acceso a esta sección.")

# Footer
st.divider()
st.caption("Rio Futuro - Sistema de Gestión de Stock y Cámaras")

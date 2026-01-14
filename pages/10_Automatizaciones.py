"""
Dashboard de Automatizaciones - Túneles Estáticos
Permite crear órdenes de fabricación y monitorear su estado.

Este archivo es el orquestador principal que importa y renderiza los tabs modulares.
"""
import streamlit as st
import sys
import os
from pathlib import Path

# Configuración de la página
st.set_page_config(
    page_title="Automatizaciones",
    page_icon="🦾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importar autenticación
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.auth import proteger_pagina, obtener_info_sesion, get_credenciales, tiene_acceso_pagina

# Añadir pages al path para imports de automatizaciones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos
from automatizaciones import shared
from automatizaciones import tab_crear
from automatizaciones import tab_monitor
from automatizaciones import tab_movimientos
from automatizaciones import tab_monitor_movimientos
# from automatizaciones import tab_revertir_consumo  # OCULTO TEMPORALMENTE

# Requerir autenticación
proteger_pagina()

# Obtener info de sesión y credenciales
session_info = obtener_info_sesion()
username, password = get_credenciales()

# Inicializar session state
shared.init_session_state()

# CSS Global
st.markdown(shared.CSS_GLOBAL, unsafe_allow_html=True)

# Título
st.title("🦾 Automatizaciones")
st.markdown("**Túneles Estáticos** - Creación automatizada de órdenes de fabricación")

# === MOSTRAR RESULTADO PERSISTENTE DE ÚLTIMA ORDEN ===
if 'last_order_result' in st.session_state and st.session_state.last_order_result:
    result = st.session_state.last_order_result
    
    with st.container():
        if result.get('success'):
            st.success(f"✅ {result.get('mensaje')}")
            
            col_info1, col_info2 = st.columns(2)
            col_info1.info(f"📋 Orden: **{result.get('mo_name')}**")
            col_info2.info(f"📊 Total: **{result.get('total_kg', 0):,.2f} Kg** en **{result.get('pallets_count')}** pallets")
            
            if result.get('componentes_count') or result.get('subproductos_count'):
                col_a, col_b = st.columns(2)
                if result.get('componentes_count'):
                    col_a.metric("🔵 Componentes", result['componentes_count'])
                if result.get('subproductos_count'):
                    col_b.metric("🟢 Subproductos", result['subproductos_count'])
            
            for adv in result.get('advertencias', []):
                st.warning(f"⚠️ {adv}")
            
            # Mostrar validaciones con colores diferenciados
            for warning in result.get('validation_warnings', []):
                tipo = warning.get('tipo', 'desconocido')
                if tipo == 'pallet_duplicado':
                    st.warning(f"🟡 ADVERTENCIA: {warning.get('pallet')} ya está en orden {warning.get('orden_existente')} (se agregó de todas formas)")
                else:
                    st.warning(f"🟡 ADVERTENCIA: {warning.get('detalle', 'Sin detalle')}")
            
            for error in result.get('validation_errors', []):
                tipo = error.get('tipo', 'desconocido')
                if tipo == 'sin_stock':
                    st.error(f"🔴 ERROR: {error.get('pallet')} sin stock disponible - Agregado como PENDIENTE")
                elif tipo == 'pallet_no_existe':
                    st.error(f"🔴 ERROR: {error.get('detalle', 'Sin detalle')}")
                else:
                    st.error(f"🔴 ERROR: {error.get('detalle', 'Sin detalle')}")
            
            if result.get('has_pending'):
                st.info(f"🟠 {result.get('pending_count', 0)} pallets pendientes de recepción")
        
        if st.button("✖️ Cerrar mensaje", key="close_order_result"):
            del st.session_state.last_order_result
            st.rerun()
    
    st.divider()

# === PRE-CALCULAR PERMISOS ===
_perm_crear = tiene_acceso_pagina("automatizaciones", "crear_orden")
_perm_monitor = tiene_acceso_pagina("automatizaciones", "monitor_ordenes")
_perm_movimientos = tiene_acceso_pagina("automatizaciones", "movimientos")

# Cargar túneles (para ambos tabs)
tuneles = shared.get_tuneles(username, password)

# Obtener API URL
API_URL = shared.API_URL

# === TABS PRINCIPALES ===
tab1, tab2, tab3, tab4 = st.tabs(["📦 Crear Orden", "📊 Monitor de Órdenes", "📦 Movimientos", "📊 Monitor Mov."])
# tab5 = "🔄 Revertir Consumo" OCULTO TEMPORALMENTE

# =====================================================
#           TAB 1: CREAR ORDEN
# =====================================================
with tab1:
    if _perm_crear:
        tab_crear.render(username, password)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Crear Orden'. Contacta al administrador.")

# =====================================================
#           TAB 2: MONITOR DE ÓRDENES
# =====================================================
with tab2:
    if _perm_monitor:
        tab_monitor.render(username, password, tuneles)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Monitor de Órdenes'. Contacta al administrador.")

# =====================================================
#           TAB 3: MOVIMIENTOS DE PALLETS
# =====================================================
with tab3:
    if _perm_movimientos:
        tab_movimientos.render(username, password)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Movimientos'. Contacta al administrador.")

# =====================================================
#           TAB 4: MONITOR DE MOVIMIENTOS
# =====================================================
with tab4:
    if _perm_movimientos:
        tab_monitor_movimientos.render(username, password)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Monitor Movimientos'. Contacta al administrador.")

# =====================================================
#           TAB 5: REVERTIR CONSUMO DE ODF (OCULTO)
# =====================================================
# with tab5:
#     if _perm_crear:  # Mismo permiso que crear orden
#         tab_revertir_consumo.render(username, password)
#     else:
#         st.error("🚫 **Acceso Restringido** - No tienes permisos para usar 'Revertir Consumo'. Contacta al administrador.")

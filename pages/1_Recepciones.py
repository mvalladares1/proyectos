"""
Recepciones de Materia Prima: KPIs de Kg, costos, % IQF/Block y análisis de calidad por productor.

Este archivo es el orquestador principal que importa y renderiza los tabs modulares.
"""
import streamlit as st
import sys
import os

# Añadir el directorio raíz al path para imports de shared/auth
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.auth import proteger_modulo, get_credenciales, tiene_acceso_pagina

# Añadir el directorio pages al path para imports de recepciones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos de tabs
from recepciones import shared
from recepciones import tab_kpis
from recepciones import tab_gestion
from recepciones import tab_curva
from recepciones import tab_aprobaciones

# Configuración de página
st.set_page_config(page_title="Recepciones", page_icon="📥", layout="wide")

# Autenticación central
if not proteger_modulo("recepciones"):
    st.stop()

# Obtener credenciales del usuario autenticado
username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales. Por favor inicie sesión nuevamente.")
    st.stop()

# Inicializar session state del módulo
shared.init_session_state()

# Título de la página
st.title("📥 Recepciones de Materia Prima (MP)")
st.caption("Monitorea la fruta recepcionada en planta, con KPIs de calidad asociados")

# Botón de emergencia para limpiar caché (en caso de errores intermitentes)
with st.expander("⚙️ Herramientas de Depuración", expanded=False):
    st.caption("Si experimentas errores 500 intermitentes, usa este botón para limpiar todos los cachés")
    if st.button("🔄 Limpiar Todos los Cachés", type="secondary"):
        with st.spinner("Limpiando cachés..."):
            success, msg = shared.clear_all_caches()
            if success:
                st.success(msg)
                st.info("Por favor, recarga la página para aplicar los cambios")
            else:
                st.warning(msg)

# === PRE-CALCULAR PERMISOS ===
_perm_kpis = tiene_acceso_pagina("recepciones", "kpis_calidad")
_perm_gestion = tiene_acceso_pagina("recepciones", "gestion_recepciones")
_perm_curva = tiene_acceso_pagina("recepciones", "curva_abastecimiento")
_perm_aprobaciones = tiene_acceso_pagina("recepciones", "aprobaciones_mp")

# === TABS PRINCIPALES ===
tab_kpis_ui, tab_gestion_ui, tab_curva_ui, tab_aprobaciones_ui = st.tabs([
    "📊 KPIs y Calidad", 
    "📋 Gestión de Recepciones", 
    "📈 Curva de Abastecimiento", 
    "📥 Aprobaciones MP"
])

# =====================================================
#           TAB 1: KPIs Y CALIDAD
# =====================================================
with tab_kpis_ui:
    if _perm_kpis:
        @st.fragment
        def _frag_kpis():
            tab_kpis.render(username, password)
        _frag_kpis()
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'KPIs y Calidad'. Contacta al administrador.")
        st.info("💡 Contacta al administrador para solicitar acceso a esta sección.")

# =====================================================
#           TAB 2: GESTIÓN DE RECEPCIONES
# =====================================================
with tab_gestion_ui:
    if _perm_gestion:
        @st.fragment
        def _frag_gestion():
            tab_gestion.render(username, password)
        _frag_gestion()
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Gestión de Recepciones'. Contacta al administrador.")
        st.info("💡 Contacta al administrador para solicitar acceso a esta sección.")

# =====================================================
#           TAB 3: CURVA DE ABASTECIMIENTO
# =====================================================
with tab_curva_ui:
    if _perm_curva:
        @st.fragment
        def _frag_curva():
            tab_curva.render(username, password)
        _frag_curva()
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Curva de Abastecimiento'. Contacta al administrador.")
        st.info("💡 Contacta al administrador para solicitar acceso a esta sección.")

# =====================================================
#           TAB 4: APROBACIONES MP
# =====================================================
with tab_aprobaciones_ui:
    if _perm_aprobaciones:
        tab_aprobaciones.render(username, password)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Aprobaciones MP'. Contacta al administrador.")
        st.info("💡 Contacta al administrador para solicitar acceso a esta sección.")

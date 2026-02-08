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
from recepciones import tab_pallets
from recepciones import tab_aprobaciones_fletes
from recepciones import tab_proforma_consolidada
from recepciones import tab_ajuste_proformas
from recepciones import tab_kg_linea

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

# === PRE-CALCULAR PERMISOS ===
_perm_kpis = tiene_acceso_pagina("recepciones", "kpis_calidad")
_perm_gestion = tiene_acceso_pagina("recepciones", "gestion_recepciones")
_perm_curva = tiene_acceso_pagina("recepciones", "curva_abastecimiento")
_perm_aprobaciones = tiene_acceso_pagina("recepciones", "aprobaciones_mp")
_perm_pallets = tiene_acceso_pagina("recepciones", "pallets_recepcion") # Permiso nuevo o reusado
_perm_aprobaciones_fletes = tiene_acceso_pagina("recepciones", "aprobaciones_fletes")  # Nuevo permiso
_perm_proforma_fletes = tiene_acceso_pagina("recepciones", "proforma_fletes")  # Proforma consolidada
_perm_ajuste_proformas = tiene_acceso_pagina("recepciones", "ajuste_proformas")  # Ajuste USD → CLP
_perm_kg_linea = tiene_acceso_pagina("recepciones", "kg_linea")  # KG por Línea

# === CONSTRUIR TABS DINÁMICAMENTE SEGÚN PERMISOS ===
tabs_disponibles = []
tabs_nombres = []

if _perm_kpis:
    tabs_nombres.append("📊 KPIs y Calidad")
    tabs_disponibles.append("kpis")

if _perm_gestion:
    tabs_nombres.append("📋 Gestión de Recepciones")
    tabs_disponibles.append("gestion")

if _perm_gestion or _perm_pallets:
    tabs_nombres.append("📦 Pallets por Recepción")
    tabs_disponibles.append("pallets")

if _perm_curva:
    tabs_nombres.append("📈 Curva de Abastecimiento")
    tabs_disponibles.append("curva")

if _perm_aprobaciones:
    tabs_nombres.append("📥 Aprobaciones MP")
    tabs_disponibles.append("aprobaciones")

if _perm_aprobaciones_fletes:
    tabs_nombres.append("🚚 Aprobaciones Fletes")
    tabs_disponibles.append("aprobaciones_fletes")

if _perm_proforma_fletes:
    tabs_nombres.append("📄 Proforma Consolidada")
    tabs_disponibles.append("proforma_fletes")

if _perm_ajuste_proformas:
    tabs_nombres.append("💱 Ajuste Proformas")
    tabs_disponibles.append("ajuste_proformas")

if _perm_kg_linea or _perm_gestion:
    tabs_nombres.append("⚡ KG por Línea")
    tabs_disponibles.append("kg_linea")

# Si no tiene acceso a ningún tab, mostrar mensaje
if not tabs_disponibles:
    st.error("🚫 **Acceso Restringido** - No tienes permisos para acceder a ninguna sección de Recepciones.")
    st.info("💡 Contacta al administrador para solicitar acceso.")
    st.stop()

# Crear tabs dinámicamente
tabs_ui = st.tabs(tabs_nombres)

# Mapear tabs a funciones de renderizado
tab_index = 0

if "kpis" in tabs_disponibles:
    with tabs_ui[tab_index]:
        @st.fragment
        def _frag_kpis():
            tab_kpis.render(username, password)
        _frag_kpis()
    tab_index += 1

if "gestion" in tabs_disponibles:
    with tabs_ui[tab_index]:
        @st.fragment
        def _frag_gestion():
            tab_gestion.render(username, password)
        _frag_gestion()
    tab_index += 1

if "pallets" in tabs_disponibles:
    with tabs_ui[tab_index]:
        @st.fragment
        def _frag_pallets():
            tab_pallets.render(username, password)
        _frag_pallets()
    tab_index += 1

if "curva" in tabs_disponibles:
    with tabs_ui[tab_index]:
        @st.fragment
        def _frag_curva():
            tab_curva.render(username, password)
        _frag_curva()
    tab_index += 1

if "aprobaciones" in tabs_disponibles:
    with tabs_ui[tab_index]:
        tab_aprobaciones.render(username, password)
    tab_index += 1

if "aprobaciones_fletes" in tabs_disponibles:
    with tabs_ui[tab_index]:
        @st.fragment
        def _frag_aprobaciones_fletes():
            tab_aprobaciones_fletes.render_tab(username, password)
        _frag_aprobaciones_fletes()
    tab_index += 1

if "proforma_fletes" in tabs_disponibles:
    with tabs_ui[tab_index]:
        @st.fragment
        def _frag_proforma_fletes():
            tab_proforma_consolidada.render(username, password)
        _frag_proforma_fletes()
    tab_index += 1

if "ajuste_proformas" in tabs_disponibles:
    with tabs_ui[tab_index]:
        @st.fragment
        def _frag_ajuste_proformas():
            tab_ajuste_proformas.render(username, password)
        _frag_ajuste_proformas()
    tab_index += 1

if "kg_linea" in tabs_disponibles:
    with tabs_ui[tab_index]:
        @st.fragment
        def _frag_kg_linea():
            tab_kg_linea.render(username, password)
        _frag_kg_linea()
    tab_index += 1

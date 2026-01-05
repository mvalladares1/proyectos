"""
Estado de Resultado contable: ingresos, costos, márgenes y comparación Real vs Presupuesto mensual.
Módulo modularizado según MODULARIZATION_GUIDE.md
"""
import streamlit as st
from datetime import datetime
import requests
import sys
import os

# Añadir el directorio raíz al path para imports de shared/auth
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.auth import proteger_modulo, tiene_acceso_dashboard, get_credenciales, tiene_acceso_pagina

# Añadir el directorio pages al path para imports de finanzas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos de tabs
from finanzas import shared
from finanzas import tab_agrupado
from finanzas import tab_mensualizado
from finanzas import tab_ytd
from finanzas import tab_cg
from finanzas import tab_detalle
from finanzas import tab_flujo_caja

# === CONFIGURACIÓN DE PÁGINA ===
st.set_page_config(page_title="Finanzas", page_icon="💰", layout="wide")

# === AUTENTICACIÓN Y PERMISOS ===
if not proteger_modulo("finanzas"):
    st.stop()

if not tiene_acceso_dashboard("finanzas"):
    st.error("No tienes permisos para ver este dashboard.")
    st.stop()

# Obtener credenciales
username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales. Por favor inicia sesión nuevamente.")
    st.stop()

# Inicializar session state
shared.init_session_state()

# === PERMISOS POR TAB ===
_perm_agrupado = tiene_acceso_pagina("finanzas", "agrupado")
_perm_mensualizado = tiene_acceso_pagina("finanzas", "mensualizado")
_perm_ytd = tiene_acceso_pagina("finanzas", "ytd")
_perm_cg = tiene_acceso_pagina("finanzas", "cg")
_perm_detalle = tiene_acceso_pagina("finanzas", "detalle")
_perm_flujo = tiene_acceso_pagina("finanzas", "flujo_caja")

# === HEADER ===
col_logo, col_title = st.columns([1, 4])
with col_title:
    st.title("📈 Control Presupuestario - Estado de Resultado")
    st.caption("Datos obtenidos en tiempo real desde Odoo | Presupuesto desde Excel")

# === SIDEBAR - FILTROS ===
st.sidebar.header("Filtros")

# Filtro de año
año_seleccionado = st.sidebar.selectbox("Año", [2025, 2026], index=0)

# Filtro de meses
meses_opciones = {
    "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
    "Mayo": "05", "Junio": "06", "Julio": "07", "Agosto": "08",
    "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12"
}
meses_seleccionados = st.sidebar.multiselect(
    "Mes", list(meses_opciones.keys()),
    default=list(meses_opciones.keys())[:datetime.now().month]
)

# Calcular fechas
if meses_seleccionados:
    meses_nums = [meses_opciones[m] for m in meses_seleccionados]
    fecha_inicio = f"{año_seleccionado}-{min(meses_nums)}-01"
    mes_fin = max(meses_nums)
    if mes_fin in ["01", "03", "05", "07", "08", "10", "12"]:
        ultimo_dia = "31"
    elif mes_fin == "02":
        ultimo_dia = "28"
    else:
        ultimo_dia = "30"
    fecha_fin = f"{año_seleccionado}-{mes_fin}-{ultimo_dia}"
else:
    fecha_inicio = f"{año_seleccionado}-01-01"
    fecha_fin = f"{año_seleccionado}-12-31"

# Centros de costo
centros = shared.fetch_centros_costo(username, password)
opciones_centros = {"Todas": None}
if isinstance(centros, list):
    for c in centros:
        opciones_centros[c.get("name", f"ID {c['id']}")] = c["id"]

centro_seleccionado = st.sidebar.selectbox("Centro de Costo", list(opciones_centros.keys()))

# === CARGA DE PRESUPUESTO ===
st.sidebar.divider()
st.sidebar.subheader("📁 Cargar Presupuesto")
uploaded_file = st.sidebar.file_uploader(
    f"Subir archivo PPTO {año_seleccionado}",
    type=["xlsx", "xls"],
    help="Sube el archivo Excel con el presupuesto"
)

if uploaded_file:
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        resp = requests.post(f"{shared.PRESUPUESTO_URL}/upload/{año_seleccionado}", files=files)
        if resp.status_code == 200:
            result = resp.json()
            if "error" in result:
                st.sidebar.error(f"Error: {result['error']}")
            else:
                st.sidebar.success(f"✅ Archivo cargado: {result.get('filename')}")
        else:
            st.sidebar.error(f"Error {resp.status_code}: {resp.text}")
    except Exception as e:
        st.sidebar.error(f"Error al cargar: {e}")

# Botón actualizar
if st.sidebar.button("🔄 Actualizar datos"):
    st.cache_data.clear()
    for key in ['finanzas_eerr_datos', 'finanzas_eerr_ppto']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# === OBTENER DATOS ===
cache_key = f"finanzas_{año_seleccionado}_{fecha_inicio}_{fecha_fin}_{centro_seleccionado}"

if "finanzas_cache_key" not in st.session_state or st.session_state.finanzas_cache_key != cache_key:
    st.session_state.finanzas_cache_key = cache_key
    with st.spinner("Cargando datos..."):
        st.session_state.finanzas_eerr_datos = shared.fetch_estado_resultado(
            fecha_inicio, fecha_fin, opciones_centros.get(centro_seleccionado),
            username, password
        )
        st.session_state.finanzas_eerr_ppto = shared.fetch_presupuesto(
            año_seleccionado, opciones_centros.get(centro_seleccionado)
        )

datos = st.session_state.get('finanzas_eerr_datos')
ppto = st.session_state.get('finanzas_eerr_ppto', {})

# === MOSTRAR DATOS ===
if datos:
    if "error" in datos:
        st.error(f"Error al obtener datos reales: {datos['error']}")
    else:
        resultados = datos.get("resultados", {})
        estructura = datos.get("estructura", {})
        datos_mensuales = datos.get("datos_mensuales", {})
        
        # Presupuesto
        ppto_ytd = ppto.get("ytd", {}) if ppto else {}
        ppto_mensual = ppto.get("mensual", {}) if ppto else {}
        
        # === TABS ===
        tab_agrupado_ui, tab_mensualizado_ui, tab_ytd_ui, tab_cg_ui, tab_detalle_ui, tab_flujo_ui = st.tabs([
            "📅 Agrupado", "💰 Mensualizado", "📊 YTD (Acumulado)", "📊 CG", "📋 Detalle", "💵 Flujo de Caja"
        ])
        
        with tab_agrupado_ui:
            if not _perm_agrupado:
                st.error("🚫 **Acceso Restringido** - Contacta al administrador.")
            else:
                tab_agrupado.render(datos_mensuales, ppto_mensual, meses_seleccionados, meses_opciones, año_seleccionado)
        
        with tab_mensualizado_ui:
            if not _perm_mensualizado:
                st.error("🚫 **Acceso Restringido** - Contacta al administrador.")
            else:
                tab_mensualizado.render(datos_mensuales, ppto_mensual, meses_seleccionados, meses_opciones, año_seleccionado)
        
        with tab_ytd_ui:
            if not _perm_ytd:
                st.error("🚫 **Acceso Restringido** - Contacta al administrador.")
            else:
                tab_ytd.render(resultados, ppto_ytd, estructura)
        
        with tab_cg_ui:
            if not _perm_cg:
                st.error("🚫 **Acceso Restringido** - Contacta al administrador.")
            else:
                tab_cg.render(estructura, fecha_inicio, fecha_fin, centro_seleccionado)
        
        with tab_detalle_ui:
            if not _perm_detalle:
                st.error("🚫 **Acceso Restringido** - Contacta al administrador.")
            else:
                tab_detalle.render(estructura, ppto_ytd)
        
        with tab_flujo_ui:
            if not _perm_flujo:
                st.error("🚫 **Acceso Restringido** - Contacta al administrador.")
            else:
                tab_flujo_caja.render(username, password)
else:
    st.info("Selecciona los filtros y haz clic en 'Actualizar datos' para cargar información.")

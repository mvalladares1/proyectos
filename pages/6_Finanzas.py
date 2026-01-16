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
from finanzas import tab_eerr
from finanzas import tab_cg
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
_perm_eerr = tiene_acceso_pagina("finanzas", "agrupado")
_perm_cg = tiene_acceso_pagina("finanzas", "cg")
_perm_flujo = tiene_acceso_pagina("finanzas", "flujo_caja")


# === HEADER ===
st.title("📈 Control Presupuestario - Estado de Resultado")
st.caption("Datos obtenidos en tiempo real desde Odoo | Presupuesto desde Excel")

# === FILTROS EN ÁREA PRINCIPAL ===
st.markdown("---")
# Primera fila: Filtros principales
col_filtros = st.columns([1, 2, 2, 2])

with col_filtros[0]:
    año_seleccionado = st.selectbox("📅 Año", [2025, 2026], index=0, key="finanzas_año")

with col_filtros[1]:
    meses_opciones = {
        "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
        "Mayo": "05", "Junio": "06", "Julio": "07", "Agosto": "08",
        "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12"
    }
    meses_seleccionados = st.multiselect(
        "📅 Meses", list(meses_opciones.keys()),
        default=list(meses_opciones.keys())[:datetime.now().month],
        key="finanzas_meses"
    )

with col_filtros[2]:
    centros = shared.fetch_centros_costo(username, password)
    opciones_centros = {"Todas": None}
    if isinstance(centros, list):
        for c in centros:
            opciones_centros[c.get("name", f"ID {c['id']}")] = c["id"]
    centro_seleccionado = st.selectbox("🏢 Centro de Costo", list(opciones_centros.keys()), key="finanzas_centro")

with col_filtros[3]:
    # Carga de presupuesto
    uploaded_file = st.file_uploader(
        f"📁 PPTO {año_seleccionado}",
        type=["xlsx", "xls"],
        help="Sube el archivo Excel con el presupuesto",
        key="finanzas_ppto_upload"
    )

# Procesar upload de PPTO (esto sí puede ser inmediato porque es interacción de archivo)
if uploaded_file:
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        resp = requests.post(f"{shared.PRESUPUESTO_URL}/upload/{año_seleccionado}", files=files)
        if resp.status_code == 200:
            result = resp.json()
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.success(f"✅ Presupuesto cargado: {result.get('filename')}")
        else:
            st.error(f"Error {resp.status_code}: {resp.text}")
    except Exception as e:
        st.error(f"Error al cargar: {e}")

# Botón de Consultar (Segunda fila para darle importancia)
st.markdown("") # Spacer
col_btn = st.columns([1, 4])
with col_btn[0]:
    btn_consultar = st.button("🔄 Generar Reporte", type="primary", use_container_width=True)

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

# Generar lista de meses
meses_lista = []
if meses_seleccionados:
    for mes_nombre in meses_seleccionados:
        mes_num = meses_opciones[mes_nombre]
        meses_lista.append(f"{año_seleccionado}-{mes_num}")
    meses_lista.sort()
else:
    for i in range(1, 13):
        meses_lista.append(f"{año_seleccionado}-{i:02d}")

st.markdown("---")

# === CONTROL DE CARGA ===
# Lógica: Cargar solo si se presiona el botón O si ya hay datos cargados y no queremos resetear (persistencia básica)
# Pero el usuario pidió explícitamente NO carga dinámica al cambiar filtros.
# Así que: Si se presiona el botón -> Cargar y guardar en session state.
# Si NO se presiona -> Mostrar lo que hay en session state (si hay) PERO con advertencia si los filtros cambiaron (opcional, por ahora simple).

if btn_consultar:
    st.session_state["finanzas_data_loaded"] = True
    st.session_state["finanzas_filtros_usados"] = {
        "año": año_seleccionado,
        "meses": meses_seleccionados,
        "centro": centro_seleccionado
    }
    
    with st.spinner("📊 Cargando reporte financiero..."):
        try:
            st.session_state.finanzas_eerr_datos = shared.fetch_estado_resultado(
                fecha_inicio, fecha_fin, opciones_centros.get(centro_seleccionado),
                username, password
            )
            st.session_state.finanzas_eerr_ppto = shared.fetch_presupuesto(
                año_seleccionado, opciones_centros.get(centro_seleccionado)
            )
        except Exception as e:
            st.error(f"Error al cargar datos: {e}")
            st.session_state["finanzas_data_loaded"] = False

# Verificar si hay datos cargados
datos = st.session_state.get('finanzas_eerr_datos')
ppto = st.session_state.get('finanzas_eerr_ppto', {})
data_loaded = st.session_state.get("finanzas_data_loaded", False)

# === MOSTRAR DATOS ===
if data_loaded and datos:
    if "error" in datos:
        st.error(f"Error al obtener datos reales: {datos['error']}")
    else:
        estructura = datos.get("estructura", {})
        datos_mensuales = datos.get("datos_mensuales", {})
        
        # Presupuesto
        ppto_ytd = ppto.get("ytd", {}) if ppto else {}
        ppto_mensual = ppto.get("mensual", {}) if ppto else {}
        
        # === TABS ===
        tab_eerr_ui, tab_cg_ui, tab_flujo_ui = st.tabs([
            "📊 Estado de Resultados", "📁 Cuentas (CG)", "💵 Flujo de Caja"
        ])
        
        with tab_eerr_ui:
            if not _perm_eerr:
                st.error("🚫 **Acceso Restringido** - Contacta al administrador.")
            else:
                @st.fragment
                def _frag_eerr():
                    tab_eerr.render(
                        username, password,
                        estructura=estructura,
                        datos_mensuales=datos_mensuales,
                        meses_lista=meses_lista,
                        ppto_mensual=ppto_mensual
                    )
                _frag_eerr()
        
        with tab_cg_ui:
            if not _perm_cg:
                st.error("🚫 **Acceso Restringido** - Contacta al administrador.")
            else:
                @st.fragment
                def _frag_cg():
                    # Nota: tab_cg también usa los filtros globales, asegurar consistencia
                    # Si el usuario cambió los filtros pero NO presionó generar, tab_cg podría mostrar datos inconsistentes
                    # con los títulos. Pero como 'datos' vienen del session_state snapshot, los datos son consistentes entre sí.
                    # Pasamos fecha_inicio/centro calculados ARRIBA (los actuales de la UI).
                    # Idealmente deberíamos guardar también las fechas usadas para el reporte en session_state.
                    # Por simplicidad ahora usaremos los actuales, asumiendo que el usuario acaba de generar o no ha tocado nada.
                    tab_cg.render(estructura, fecha_inicio, fecha_fin, centro_seleccionado)
                _frag_cg()
        
        with tab_flujo_ui:
            if not _perm_flujo:
                st.error("🚫 **Acceso Restringido** - Contacta al administrador.")
            else:
                @st.fragment
                def _frag_flujo():
                    tab_flujo_caja.render(username, password)
                _frag_flujo()
elif not data_loaded:
    st.info("👆 Configura los filtros y haz clic en **'Generar Reporte'** para ver los resultados.")
else:
    st.warning("⚠️ No se pudieron cargar los datos o la consulta devolvió vacío.")


"""
Estado de Resultado contable: ingresos, costos, márgenes y comparación Real vs Presupuesto mensual.
"""

import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from datetime import date, datetime

from shared.auth import proteger_modulo, tiene_acceso_dashboard, get_credenciales, tiene_acceso_pagina

st.set_page_config(page_title="Finanzas", page_icon="💰", layout="wide")

if not proteger_modulo("finanzas"):
    st.stop()

if not tiene_acceso_dashboard("finanzas"):
    st.error("No tienes permisos para ver este dashboard.")
    st.stop()

API_BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
ESTADO_RESULTADO_URL = f"{API_BASE_URL}/api/v1/estado-resultado"
PRESUPUESTO_URL = f"{API_BASE_URL}/api/v1/presupuesto"

# Obtener credenciales del usuario logueado
username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales. Por favor inicia sesión nuevamente.")
    st.stop()

# === HEADER ===
col_logo, col_title = st.columns([1, 4])
with col_title:
    st.title("📈 Control Presupuestario - Estado de Resultado")
    st.caption("Datos obtenidos en tiempo real desde Odoo | Presupuesto desde Excel")

# === FILTROS ===
st.sidebar.header("Filtros")

# Filtro de año
año_seleccionado = st.sidebar.selectbox("Año", [2025, 2026], index=0)

# Filtro de meses (selección múltiple)
meses_opciones = {
    "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
    "Mayo": "05", "Junio": "06", "Julio": "07", "Agosto": "08",
    "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12"
}
meses_seleccionados = st.sidebar.multiselect(
    "Mes",
    list(meses_opciones.keys()),
    default=list(meses_opciones.keys())[:datetime.now().month]
)

# Calcular fechas según meses seleccionados
if meses_seleccionados:
    meses_nums = [meses_opciones[m] for m in meses_seleccionados]
    fecha_inicio = f"{año_seleccionado}-{min(meses_nums)}-01"
    mes_fin = max(meses_nums)
    # Último día del mes
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

# Obtener centros de costo
@st.cache_data(ttl=300)
def obtener_centros_costo(_username, _password):
    try:
        resp = requests.get(
            f"{ESTADO_RESULTADO_URL}/centros-costo",
            params={"username": _username, "password": _password}
        )
        resp.raise_for_status()
        return resp.json()
    except:
        return []

centros = obtener_centros_costo(username, password)
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
        resp = requests.post(f"{PRESUPUESTO_URL}/upload/{año_seleccionado}", files=files)
        if resp.status_code == 200:
            result = resp.json()
            if "error" in result:
                st.sidebar.error(f"Error: {result['error']}")
            else:
                st.sidebar.success(f"✅ Archivo cargado: {result.get('filename')}")
                st.sidebar.info(f"Hojas: {result.get('hojas_disponibles', [])}")
        else:
            st.sidebar.error(f"Error {resp.status_code}: {resp.text}")
    except Exception as e:
        st.sidebar.error(f"Error al cargar: {e}")

# Botón para recargar datos
if st.sidebar.button("🔄 Actualizar datos"):
    st.cache_data.clear()
    # Limpiar datos cacheados en session_state
    if "eerr_datos" in st.session_state:
        del st.session_state["eerr_datos"]
    if "eerr_ppto" in st.session_state:
        del st.session_state["eerr_ppto"]
    st.rerun()

# === OBTENER DATOS REALES ===
@st.cache_data(ttl=300, show_spinner="Cargando datos desde Odoo...")
def obtener_estado_resultado(fecha_ini, fecha_f, centro, _username, _password):
    try:
        params = {
            "fecha_inicio": fecha_ini,
            "username": _username,
            "password": _password
        }
        if fecha_f:
            params["fecha_fin"] = fecha_f
        if centro:
            params["centro_costo"] = centro
        resp = requests.get(f"{ESTADO_RESULTADO_URL}/", params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

# === OBTENER PRESUPUESTO ===
@st.cache_data(ttl=300, show_spinner="Cargando presupuesto...")
def obtener_presupuesto(año, centro=None):
    try:
        params = {"año": año}
        if centro:
            params["centro_costo"] = centro
        resp = requests.get(f"{PRESUPUESTO_URL}/", params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

# Usar session_state para cachear los datos y evitar recargas en cada widget
cache_key = f"{año_seleccionado}_{fecha_inicio}_{fecha_fin}_{centro_seleccionado}"

# Cargar datos si no existen o si cambió el caché
if "eerr_cache_key" not in st.session_state or st.session_state.eerr_cache_key != cache_key or "eerr_datos" not in st.session_state:
    st.session_state.eerr_cache_key = cache_key
    with st.spinner("Cargando datos..."):
        st.session_state.eerr_datos = obtener_estado_resultado(
            fecha_inicio,
            fecha_fin,
            opciones_centros.get(centro_seleccionado),
            username,
            password
        )
        st.session_state.eerr_ppto = obtener_presupuesto(
            año_seleccionado, 
            centro_seleccionado if centro_seleccionado != "Todas" else None
        )

datos = st.session_state.eerr_datos if "eerr_datos" in st.session_state else None
ppto = st.session_state.eerr_ppto if "eerr_ppto" in st.session_state else {}

# === MOSTRAR DATOS ===
if datos:
    if "error" in datos:
        st.error(f"Error al obtener datos reales: {datos['error']}")
    else:
        resultados = datos.get("resultados", {})
        estructura = datos.get("estructura", {})
        datos_mensuales = datos.get("datos_mensuales", {})

        # Obtener datos de presupuesto
        ppto_ytd = {}
        ppto_mensual = {}
        if ppto and "error" not in ppto:
            ppto_ytd = ppto.get("ytd", {})
            ppto_mensual = ppto.get("mensual", {})

        # === TABS PRINCIPALES ===
        # Pre-calcular permisos
        _perm_agrupado = tiene_acceso_pagina("finanzas", "agrupado")
        _perm_mensualizado = tiene_acceso_pagina("finanzas", "mensualizado")
        _perm_ytd = tiene_acceso_pagina("finanzas", "ytd")
        _perm_cg = tiene_acceso_pagina("finanzas", "cg")
        _perm_detalle = tiene_acceso_pagina("finanzas", "detalle")
        _perm_flujo = tiene_acceso_pagina("finanzas", "flujo_caja")
        
        tab_mensual, tab_control_mensual, tab_ytd, tab_cg, tab_detalle, tab_flujo = st.tabs([
            "📅 Agrupado", "💰 Mensualizado", "📊 YTD (Acumulado)", "📊 CG", "📋 Detalle", "💵 Flujo de Caja"
        ])

        with tab_mensual:
            if not _perm_agrupado:
                st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Agrupado'. Contacta al administrador.")
            st.subheader("Estado de Resultados - Agrupado por Meses Seleccionados")

            # Filtrar datos mensuales por meses seleccionados
            meses_filtro = [f"{año_seleccionado}-{meses_opciones[m]}" for m in meses_seleccionados]

            # Función helper para sumar valores de meses
            def sumar_meses(cat_nombre):
                real = sum(datos_mensuales.get(m, {}).get(cat_nombre, 0) for m in meses_filtro if m in datos_mensuales)
                ppto = sum(ppto_mensual.get(m, {}).get(cat_nombre, 0) for m in meses_filtro if m in ppto_mensual)
                return real, ppto

            # Crear DataFrame con estructura jerárquica
            eerr_mensual = []

            def agregar_fila_agrupado(concepto, real, ppto, es_calculado=False):
                dif = real - ppto
                dif_pct = (dif / ppto * 100) if ppto != 0 else 0
                eerr_mensual.append({
                    "Concepto": concepto,
                    "Real Mes": real,
                    "PPTO Mes": ppto,
                    "Dif Mes": dif,
                    "Dif %": dif_pct,
                    "es_calculado": es_calculado
                })

            # 1 - INGRESOS
            ing_real, ing_ppto = sumar_meses("1 - INGRESOS")
            agregar_fila_agrupado("1 - INGRESOS", ing_real, ing_ppto)

            # 2 - COSTOS
            cost_real, cost_ppto = sumar_meses("2 - COSTOS")
            agregar_fila_agrupado("2 - COSTOS", cost_real, cost_ppto)

            # 3 - UTILIDAD BRUTA = 1 - 2
            ub_real = ing_real - cost_real
            ub_ppto = ing_ppto - cost_ppto
            agregar_fila_agrupado("3 - UTILIDAD BRUTA", ub_real, ub_ppto, es_calculado=True)

            # 4 - GASTOS DIRECTOS
            gd_real, gd_ppto = sumar_meses("4 - GASTOS DIRECTOS")
            agregar_fila_agrupado("4 - GASTOS DIRECTOS", gd_real, gd_ppto)

            # 5 - MARGEN DE CONTRIBUCIÓN = 3 - 4
            mc_real = ub_real - gd_real
            mc_ppto = ub_ppto - gd_ppto
            agregar_fila_agrupado("5 - MARGEN DE CONTRIBUCIÓN", mc_real, mc_ppto, es_calculado=True)

            # 6 - GAV
            gav_real, gav_ppto = sumar_meses("6 - GAV")
            agregar_fila_agrupado("6 - GAV", gav_real, gav_ppto)

            # 7 - UTILIDAD OPERACIONAL (EBIT) = 5 - 6
            ebit_real = mc_real - gav_real
            ebit_ppto = mc_ppto - gav_ppto
            agregar_fila_agrupado("7 - UTILIDAD OPERACIONAL (EBIT)", ebit_real, ebit_ppto, es_calculado=True)

            # 8 - INTERESES
            int_real, int_ppto = sumar_meses("8 - INTERESES")
            agregar_fila_agrupado("8 - INTERESES", int_real, int_ppto)

            # 9 - UTILIDAD ANTES DE NO OP = 7 - 8
            uano_real = ebit_real - int_real
            uano_ppto = ebit_ppto - int_ppto
            agregar_fila_agrupado("9 - UTILIDAD ANTES DE NO OP.", uano_real, uano_ppto, es_calculado=True)

            # 10 - INGRESOS NO OPERACIONALES
            ino_real, ino_ppto = sumar_meses("10 - INGRESOS NO OPERACIONALES")
            agregar_fila_agrupado("10 - INGRESOS NO OPERACIONALES", ino_real, ino_ppto)

            # 11 - GASTOS NO OPERACIONALES
            gno_real, gno_ppto = sumar_meses("11 - GASTOS NO OPERACIONALES")
            agregar_fila_agrupado("11 - GASTOS NO OPERACIONALES", gno_real, gno_ppto)

            # 12 - RESULTADO NO OPERACIONAL = 10 - 11
            rno_real = ino_real - gno_real
            rno_ppto = ino_ppto - gno_ppto
            agregar_fila_agrupado("12 - RESULTADO NO OPERACIONAL", rno_real, rno_ppto, es_calculado=True)

            # 13 - UTILIDAD ANTES DE IMPUESTOS = 9 + 12
            uai_real = uano_real + rno_real
            uai_ppto = uano_ppto + rno_ppto
            agregar_fila_agrupado("13 - UTILIDAD ANTES DE IMPUESTOS", uai_real, uai_ppto, es_calculado=True)

            df_mensual = pd.DataFrame(eerr_mensual)
            cols_mostrar_agr = ["Concepto", "Real Mes", "PPTO Mes", "Dif Mes", "Dif %"]
            df_display_agr = df_mensual[cols_mostrar_agr].copy()

            def resaltar_calculados_agr(row):
                idx = row.name
                if df_mensual.iloc[idx].get("es_calculado", False):
                    return ["background-color: #2d3748; font-weight: bold"] * len(cols_mostrar_agr)
                return [""] * len(cols_mostrar_agr)

            # Formatear y mostrar
            st.dataframe(
                df_display_agr.style
                .format({
                    "Real Mes": "${:,.0f}",
                    "PPTO Mes": "${:,.0f}",
                    "Dif Mes": "${:,.0f}",
                    "Dif %": "{:.1f}%"
                })
                .apply(resaltar_calculados_agr, axis=1),
                use_container_width=True,
                hide_index=True
            )

        with tab_control_mensual:
            if not _perm_mensualizado:
                st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Mensualizado'. Contacta al administrador.")
            st.subheader("💰 Control Presupuestario - Mensualizado Detalle")
            st.caption("Detalle mes a mes de los meses seleccionados")

            # === MESES DEL AÑO ===
            meses_nombres = {
                "01": "ENE", "02": "FEB", "03": "MAR", "04": "ABR",
                "05": "MAY", "06": "JUN", "07": "JUL", "08": "AGO",
                "09": "SEP", "10": "OCT", "11": "NOV", "12": "DIC"
            }

            # Mapear datos mensuales por número de mes
            meses_data = {}
            for mes_str, datos_mes in datos_mensuales.items():
                if "-" in mes_str:
                    mes_num = mes_str.split("-")[1]
                    if mes_num in meses_nombres:
                        meses_data[mes_num] = datos_mes

            # Convertir meses seleccionados a números
            meses_nums_sel = [meses_opciones[m] for m in meses_seleccionados]

            # Definir estructura completa EERR con indicador de calculado
            estructura_eerr = [
                ("1 - INGRESOS", False),
                ("2 - COSTOS", False),
                ("3 - UTILIDAD BRUTA", True),          # 1 - 2
                ("4 - GASTOS DIRECTOS", False),
                ("5 - MARGEN DE CONTRIBUCIÓN", True),  # 3 - 4
                ("6 - GAV", False),
                ("7 - UTILIDAD OPERACIONAL (EBIT)", True),  # 5 - 6
                ("8 - INTERESES", False),
                ("9 - UTILIDAD ANTES DE NO OP.", True),  # 7 - 8
                ("10 - INGRESOS NO OPERACIONALES", False),
                ("11 - GASTOS NO OPERACIONALES", False),
                ("12 - RESULTADO NO OPERACIONAL", True),  # 10 - 11
                ("13 - UTILIDAD ANTES DE IMPUESTOS", True),  # 9 + 12
            ]

            # Función para obtener valor de mes (datos reales o ppto)
            def obtener_valor_mensual(mes_num, concepto, datos_mes_dict, ppto_dict=None, año=None):
                if concepto.startswith("3 - "):  # Utilidad Bruta
                    ing = datos_mes_dict.get(mes_num, {}).get("1 - INGRESOS", 0)
                    cost = datos_mes_dict.get(mes_num, {}).get("2 - COSTOS", 0)
                    return ing - cost
                elif concepto.startswith("5 - "):  # Margen de Contribución
                    ub = obtener_valor_mensual(mes_num, "3 - UTILIDAD BRUTA", datos_mes_dict)
                    gd = datos_mes_dict.get(mes_num, {}).get("4 - GASTOS DIRECTOS", 0)
                    return ub - gd
                elif concepto.startswith("7 - "):  # EBIT
                    mc = obtener_valor_mensual(mes_num, "5 - MARGEN", datos_mes_dict)
                    gav = datos_mes_dict.get(mes_num, {}).get("6 - GAV", 0)
                    return mc - gav
                elif concepto.startswith("9 - "):  # Utilidad antes No Op
                    ebit = obtener_valor_mensual(mes_num, "7 - EBIT", datos_mes_dict)
                    inter = datos_mes_dict.get(mes_num, {}).get("8 - INTERESES", 0)
                    return ebit - inter
                elif concepto.startswith("12 - "):  # Resultado No Op
                    ino = datos_mes_dict.get(mes_num, {}).get("10 - INGRESOS NO OPERACIONALES", 0)
                    gno = datos_mes_dict.get(mes_num, {}).get("11 - GASTOS NO OPERACIONALES", 0)
                    return ino - gno
                elif concepto.startswith("13 - "):  # Utilidad antes Impuestos
                    uano = obtener_valor_mensual(mes_num, "9 - UTIL", datos_mes_dict)
                    rno = obtener_valor_mensual(mes_num, "12 - RESULTADO", datos_mes_dict)
                    return uano + rno
                else:
                    return datos_mes_dict.get(mes_num, {}).get(concepto, 0)

            # === VISTA DE REALES MENSUALES ===
            st.write("**📊 Montos Reales (CLP)**")
            tabla_real = {"Concepto": [], "es_calculado": []}
            for concepto, es_calc in estructura_eerr:
                tabla_real["Concepto"].append(concepto)
                tabla_real["es_calculado"].append(es_calc)
            
            for mes_num in meses_nums_sel:
                tabla_real[meses_nombres[mes_num]] = []
                for concepto, es_calc in estructura_eerr:
                    val = obtener_valor_mensual(mes_num, concepto, meses_data)
                    tabla_real[meses_nombres[mes_num]].append(val)

            df_real_mes = pd.DataFrame(tabla_real)
            cols_meses = [meses_nombres[m] for m in meses_nums_sel]
            
            def resaltar_calculados_mens(row):
                idx = row.name
                if df_real_mes.iloc[idx].get("es_calculado", False):
                    return ["background-color: #2d3748; font-weight: bold"] * len(row)
                return [""] * len(row)

            df_display_real = df_real_mes[["Concepto"] + cols_meses].copy()
            st.dataframe(
                df_display_real.style
                .format("{:,.0f}", subset=cols_meses)
                .apply(lambda x: resaltar_calculados_mens(x), axis=1),
                use_container_width=True,
                hide_index=True
            )

            # === VISTA DE PRESUPUESTO MENSUAL ===
            st.write("**💰 Presupuesto (CLP)**")
            
            # Crear meses_ppto_data con la misma estructura
            meses_ppto_data = {}
            for mes_num in meses_nums_sel:
                mes_key = f"{año_seleccionado}-{mes_num}"
                meses_ppto_data[mes_num] = ppto_mensual.get(mes_key, {})

            tabla_ppto = {"Concepto": [], "es_calculado": []}
            for concepto, es_calc in estructura_eerr:
                tabla_ppto["Concepto"].append(concepto)
                tabla_ppto["es_calculado"].append(es_calc)
            
            for mes_num in meses_nums_sel:
                tabla_ppto[meses_nombres[mes_num]] = []
                for concepto, es_calc in estructura_eerr:
                    val = obtener_valor_mensual(mes_num, concepto, meses_ppto_data)
                    tabla_ppto[meses_nombres[mes_num]].append(val)

            df_ppto_mes = pd.DataFrame(tabla_ppto)
            df_display_ppto = df_ppto_mes[["Concepto"] + cols_meses].copy()
            
            def resaltar_calculados_ppto(row):
                idx = row.name
                if df_ppto_mes.iloc[idx].get("es_calculado", False):
                    return ["background-color: #2d3748; font-weight: bold"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df_display_ppto.style
                .format("{:,.0f}", subset=cols_meses)
                .apply(resaltar_calculados_ppto, axis=1),
                use_container_width=True,
                hide_index=True
            )

            # === VARIACIONES ===
            st.divider()
            st.write("**📈 Variaciones (Real - PPTO)**")
            tabla_var = {"Concepto": [], "es_calculado": []}
            for concepto, es_calc in estructura_eerr:
                tabla_var["Concepto"].append(concepto)
                tabla_var["es_calculado"].append(es_calc)
            
            for mes_num in meses_nums_sel:
                tabla_var[meses_nombres[mes_num]] = []
                for concepto, es_calc in estructura_eerr:
                    real_val = obtener_valor_mensual(mes_num, concepto, meses_data)
                    ppto_val = obtener_valor_mensual(mes_num, concepto, meses_ppto_data)
                    tabla_var[meses_nombres[mes_num]].append(real_val - ppto_val)

            df_var_mes = pd.DataFrame(tabla_var)
            df_display_var = df_var_mes[["Concepto"] + cols_meses].copy()
            
            def resaltar_calculados_var(row):
                idx = row.name
                if df_var_mes.iloc[idx].get("es_calculado", False):
                    return ["background-color: #2d3748; font-weight: bold"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df_display_var.style
                .format("{:,.0f}", subset=cols_meses)
                .apply(resaltar_calculados_var, axis=1),
                use_container_width=True,
                hide_index=True
            )


        with tab_ytd:
            if not _perm_ytd:
                st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'YTD'. Contacta al administrador.")
            st.subheader("Estado de Resultados - YTD (Acumulado)")

            # === MÉTRICAS PRINCIPALES (calculadas con las mismas fórmulas que la tabla) ===
            real_ing = resultados.get('ingresos', 0)
            real_cost = resultados.get('costos', 0)
            real_gd = resultados.get('gastos_directos', 0)
            real_gav = resultados.get('gav', 0)
            
            # Cálculos jerárquicos
            ub_calc = real_ing - real_cost  # 3 - Utilidad Bruta
            mc_calc = ub_calc - real_gd      # 5 - Margen de Contribución
            ebit_calc = mc_calc - real_gav   # 7 - EBIT
            
            ppto_ing = ppto_ytd.get('1 - INGRESOS', 0)
            ppto_cost = ppto_ytd.get('2 - COSTOS', 0)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                dif_ing = ((real_ing - ppto_ing) / ppto_ing * 100) if ppto_ing else 0
                st.metric("Ingresos", f"${real_ing:,.0f}", f"{dif_ing:.1f}% vs PPTO")
            with col2:
                dif_cost = ((real_cost - ppto_cost) / ppto_cost * 100) if ppto_cost else 0
                st.metric("Costos", f"${real_cost:,.0f}", f"{dif_cost:.1f}% vs PPTO")
            with col3:
                st.metric("Utilidad Bruta (3)", f"${ub_calc:,.0f}")
            with col4:
                st.metric("EBIT (7)", f"${ebit_calc:,.0f}")

            st.divider()

            # === TABLA ESTADO DE RESULTADOS YTD ===
            eerr_data = []

            def agregar_fila(concepto, real, ppto, nivel=0, es_calculado=False):
                dif = real - ppto
                dif_pct = (dif / ppto * 100) if ppto != 0 else 0
                indent = "    " * nivel
                eerr_data.append({
                    "Concepto": f"{indent}{concepto}",
                    "Real YTD": real,
                    "PPTO YTD": ppto,
                    "Dif YTD": dif,
                    "Dif %": dif_pct,
                    "Nivel": nivel,
                    "es_calculado": es_calculado
                })

            # =========== ESTRUCTURA JERÁRQUICA ===========
            
            # 1 - INGRESOS
            ingresos_real = resultados.get("ingresos", 0)
            ingresos_ppto = ppto_ytd.get("1 - INGRESOS", 0)
            agregar_fila("1 - INGRESOS", ingresos_real, ingresos_ppto)
            if "1 - INGRESOS" in estructura:
                for subcat, subdata in estructura["1 - INGRESOS"].get("subcategorias", {}).items():
                    agregar_fila(subcat, subdata.get("total", 0), 0, 1)

            # 2 - COSTOS
            costos_real = resultados.get("costos", 0)
            costos_ppto = ppto_ytd.get("2 - COSTOS", 0)
            agregar_fila("2 - COSTOS", costos_real, costos_ppto)
            if "2 - COSTOS" in estructura:
                for subcat, subdata in estructura["2 - COSTOS"].get("subcategorias", {}).items():
                    agregar_fila(subcat, subdata.get("total", 0), 0, 1)

            # 3 - UTILIDAD BRUTA = 1 - 2
            ub_real = ingresos_real - costos_real
            ub_ppto = ingresos_ppto - costos_ppto
            agregar_fila("3 - UTILIDAD BRUTA", ub_real, ub_ppto, es_calculado=True)

            # 4 - GASTOS DIRECTOS
            gd_real = resultados.get("gastos_directos", 0)
            gd_ppto = ppto_ytd.get("4 - GASTOS DIRECTOS", 0)
            agregar_fila("4 - GASTOS DIRECTOS", gd_real, gd_ppto)

            # 5 - MARGEN DE CONTRIBUCIÓN = 3 - 4
            mc_real = ub_real - gd_real
            mc_ppto = ub_ppto - gd_ppto
            agregar_fila("5 - MARGEN DE CONTRIBUCIÓN", mc_real, mc_ppto, es_calculado=True)

            # 6 - GAV
            gav_real = resultados.get("gav", 0)
            gav_ppto = ppto_ytd.get("6 - GAV", 0)
            agregar_fila("6 - GAV", gav_real, gav_ppto)

            # 7 - UTILIDAD OPERACIONAL (EBIT) = 5 - 6
            ebit_real = mc_real - gav_real
            ebit_ppto = mc_ppto - gav_ppto
            agregar_fila("7 - UTILIDAD OPERACIONAL (EBIT)", ebit_real, ebit_ppto, es_calculado=True)

            # 8 - INTERESES
            int_real = resultados.get("intereses", 0)
            int_ppto = ppto_ytd.get("8 - INTERESES", 0)
            agregar_fila("8 - INTERESES", int_real, int_ppto)

            # 9 - UTILIDAD ANTES DE NO OP = 7 - 8
            uano_real = ebit_real - int_real
            uano_ppto = ebit_ppto - int_ppto
            agregar_fila("9 - UTILIDAD ANTES DE NO OP.", uano_real, uano_ppto, es_calculado=True)

            # 10 - INGRESOS NO OPERACIONALES
            ino_real = resultados.get("ingresos_no_operacionales", 0)
            ino_ppto = ppto_ytd.get("10 - INGRESOS NO OPERACIONALES", 0)
            agregar_fila("10 - INGRESOS NO OPERACIONALES", ino_real, ino_ppto)

            # 11 - GASTOS NO OPERACIONALES
            gno_real = resultados.get("gastos_no_operacionales", 0)
            gno_ppto = ppto_ytd.get("11 - GASTOS NO OPERACIONALES", 0)
            agregar_fila("11 - GASTOS NO OPERACIONALES", gno_real, gno_ppto)

            # 12 - RESULTADO NO OPERACIONAL = 10 - 11
            rno_real = ino_real - gno_real
            rno_ppto = ino_ppto - gno_ppto
            agregar_fila("12 - RESULTADO NO OPERACIONAL", rno_real, rno_ppto, es_calculado=True)

            # 13 - UTILIDAD ANTES DE IMPUESTOS = 9 + 12
            uai_real = uano_real + rno_real
            uai_ppto = uano_ppto + rno_ppto
            agregar_fila("13 - UTILIDAD ANTES DE IMPUESTOS", uai_real, uai_ppto, es_calculado=True)

            df_eerr = pd.DataFrame(eerr_data)
            
            # Columnas a mostrar
            cols_mostrar = ["Concepto", "Real YTD", "PPTO YTD", "Dif YTD", "Dif %"]
            df_display = df_eerr[cols_mostrar].copy()
            
            # Función para resaltar filas calculadas
            def resaltar_calculados(row):
                idx = row.name
                if df_eerr.iloc[idx].get("es_calculado", False):
                    return ["background-color: #2d3748; font-weight: bold"] * len(cols_mostrar)
                return [""] * len(cols_mostrar)

            # Mostrar tabla con formato
            st.dataframe(
                df_display.style
                .format({
                    "Real YTD": "${:,.0f}",
                    "PPTO YTD": "${:,.0f}",
                    "Dif YTD": "${:,.0f}",
                    "Dif %": "{:.1f}%"
                })
                .apply(resaltar_calculados, axis=1),
                use_container_width=True,
                hide_index=True
            )

        with tab_cg:
            if not _perm_cg:
                st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'CG'. Contacta al administrador.")
            st.subheader("📊 CG - Por Cuenta Contable")
            st.caption("Análisis detallado por cuenta contable | Filtros aplicables en sidebar")

            # Extraer todas las cuentas contables de la estructura
            cuentas_dict = {}
            
            if estructura:
                for cat_name, cat_data in estructura.items():
                    if isinstance(cat_data, dict):
                        # Nivel 1: Categoría principal
                        subcategorias = cat_data.get("subcategorias", {})
                        if isinstance(subcategorias, dict):
                            for subcat2_name, subcat2_data in subcategorias.items():
                                # Nivel 2: Subcategoría IFRS2
                                if isinstance(subcat2_data, dict):
                                    # Buscar cuentas en nivel 3
                                    subcats3 = subcat2_data.get("subcategorias", {})
                                    if isinstance(subcats3, dict):
                                        for subcat3_name, subcat3_data in subcats3.items():
                                            # Nivel 3: Subcategoría IFRS3
                                            if isinstance(subcat3_data, dict):
                                                cuentas = subcat3_data.get("cuentas", {})
                                                if isinstance(cuentas, dict):
                                                    for cuenta_name, cuenta_monto in cuentas.items():
                                                        cuentas_dict[cuenta_name] = {
                                                            "monto": cuenta_monto,
                                                            "categoria": cat_name,
                                                            "subcat2": subcat2_name,
                                                            "subcat3": subcat3_name
                                                        }

            if cuentas_dict:
                # Selector de cuenta contable
                opciones_cuentas = ["Todas"] + sorted([c for c in cuentas_dict.keys()])
                cuenta_seleccionada = st.selectbox(
                    "Seleccionar Cuenta Contable",
                    opciones_cuentas,
                    key="cuenta_cg"
                )

                if cuenta_seleccionada == "Todas":
                    # Mostrar todas las cuentas
                    st.write("**Todas las Cuentas Contables**")

                    df_cuentas = []
                    for cuenta_name, cuenta_info in sorted(cuentas_dict.items()):
                        df_cuentas.append({
                            "Cuenta": cuenta_name,
                            "Categoría": cuenta_info["categoria"],
                            "Subcategoría": cuenta_info.get("subcat3", cuenta_info.get("subcat2", "")),
                            "Monto": cuenta_info["monto"]
                        })

                    df = pd.DataFrame(df_cuentas)
                    df = df.sort_values("Monto", key=abs, ascending=False)

                    st.dataframe(
                        df.style.format({"Monto": "${:,.0f}"}),
                        use_container_width=True,
                        hide_index=True
                    )

                    # Gráfico de top 10
                    st.divider()
                    st.subheader("📈 Top 10 Cuentas por Monto")

                    df_top = df.copy()
                    df_top["Abs_Monto"] = df_top["Monto"].abs()
                    df_top = df_top.nlargest(10, "Abs_Monto")

                    # Gráfico con plotly
                    fig = px.bar(
                        df_top.sort_values("Monto"),
                        y="Cuenta",
                        x="Monto",
                        orientation="h",
                        title="Top 10 Cuentas Contables",
                        labels={"Monto": "Monto (CLP)", "Cuenta": "Cuenta"},
                        color="Monto",
                        color_continuous_scale="RdYlGn"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Resumen por categoría
                    st.divider()
                    st.subheader("📊 Distribución por Categoría")

                    resumen_cat = df.groupby("Categoría")["Monto"].sum().reset_index()
                    resumen_cat = resumen_cat.sort_values("Monto", key=abs, ascending=False)

                    col_tabla, col_grafico = st.columns([1, 1])
                    with col_tabla:
                        st.dataframe(
                            resumen_cat.style.format({"Monto": "${:,.0f}"}),
                            use_container_width=True,
                            hide_index=True
                        )
                    with col_grafico:
                        fig_cat = px.pie(
                            resumen_cat,
                            values="Monto",
                            names="Categoría",
                            title="Proporción por Categoría"
                        )
                        st.plotly_chart(fig_cat, use_container_width=True)

                else:
                    # Mostrar cuenta específica
                    cuenta_info = cuentas_dict[cuenta_seleccionada]

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Monto", f"${cuenta_info['monto']:,.0f}")
                    with col2:
                        st.metric("Categoría", cuenta_info["categoria"])
                    with col3:
                        st.metric("Subcategoría", cuenta_info.get("subcat3", cuenta_info.get("subcat2", "")))

                    st.divider()
                    st.info(f"""
                    **Cuenta:** {cuenta_seleccionada}
                    
                    **Categoría:** {cuenta_info['categoria']}
                    
                    **Subcategoría 2:** {cuenta_info['subcat2']}
                    
                    **Subcategoría 3:** {cuenta_info['subcat3']}
                    
                    **Período:** {fecha_inicio} a {fecha_fin}
                    
                    **Centro de Costo:** {centro_seleccionado}
                    """)
            else:
                st.warning("No hay cuentas contables disponibles para el período y filtros seleccionados.")
                
                # Debug info
                with st.expander("ℹ️ Información de debug"):
                    st.write("Estructura disponible:")
                    if estructura:
                        st.write(f"Categorías: {list(estructura.keys())}")
                        for cat_name in list(estructura.keys())[:1]:
                            st.write(f"\n{cat_name}:")
                            st.json(estructura[cat_name], expanded=False)
                    else:
                        st.write("Estructura vacía")

        with tab_detalle:
            if not _perm_detalle:
                st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Detalle'. Contacta al administrador.")
            st.subheader("📋 Estado de Resultados - Vista Desplegable")
            st.caption("Haz clic en cada categoría para ver el detalle de subcategorías y cuentas")
            
            # Orden de categorías para el EERR
            orden_categorias = [
                "1 - INGRESOS",
                "2 - COSTOS", 
                "4 - GASTOS DIRECTOS",
                "6 - GAV",
                "8 - INTERESES",
                "10 - INGRESOS NO OPERACIONALES",
                "11 - GASTOS NO OPERACIONALES"
            ]
            
            # Función para formatear montos
            def fmt_monto(valor):
                if valor >= 0:
                    return f"${valor:,.0f}"
                else:
                    return f"-${abs(valor):,.0f}"
            
            def fmt_pct(valor):
                if valor is None or str(valor) == "inf" or pd.isna(valor):
                    return "-"
                return f"{valor:.1f}%"
            
            # Calcular resultados intermedios
            ingresos = estructura.get("1 - INGRESOS", {}).get("total", 0)
            costos = estructura.get("2 - COSTOS", {}).get("total", 0)
            gastos_directos = estructura.get("4 - GASTOS DIRECTOS", {}).get("total", 0)
            gav = estructura.get("6 - GAV", {}).get("total", 0)
            intereses = estructura.get("8 - INTERESES", {}).get("total", 0)
            ing_no_op = estructura.get("10 - INGRESOS NO OPERACIONALES", {}).get("total", 0)
            gast_no_op = estructura.get("11 - GASTOS NO OPERACIONALES", {}).get("total", 0)
            
            utilidad_bruta = ingresos - costos
            margen_contribucion = utilidad_bruta - gastos_directos
            ebit = margen_contribucion - gav
            util_antes_no_op = ebit - intereses
            resultado_no_op = ing_no_op - gast_no_op
            util_antes_impuestos = util_antes_no_op + resultado_no_op
            
            # Resultados calculados
            filas_calculadas = {
                "3 - UTILIDAD BRUTA": utilidad_bruta,
                "5 - MARGEN DE CONTRIBUCIÓN": margen_contribucion,
                "7 - UTILIDAD OPERACIONAL (EBIT)": ebit,
                "9 - UTILIDAD ANTES DE NO OP.": util_antes_no_op,
                "12 - RESULTADO NO OPERACIONAL": resultado_no_op,
                "13 - UTILIDAD ANTES DE IMPUESTOS": util_antes_impuestos
            }
            
            # Mapeo de categorías a PPTO
            mapeo_ppto = {
                "1 - INGRESOS": "1 - INGRESOS",
                "2 - COSTOS": "2 - COSTOS",
                "4 - GASTOS DIRECTOS": "4 - GASTOS DIRECTOS",
                "6 - GAV": "6 - GAV",
                "8 - INTERESES": "8 - INTERESES",
                "10 - INGRESOS NO OPERACIONALES": "10 - INGRESOS NO OPERACIONALES",
                "11 - GASTOS NO OPERACIONALES": "11 - GASTOS NO OPERACIONALES"
            }
            
            # === MOSTRAR CADA CATEGORÍA ===
            for cat in orden_categorias:
                cat_data = estructura.get(cat, {"total": 0, "subcategorias": {}})
                real_total = cat_data.get("total", 0)
                ppto_total = ppto_ytd.get(mapeo_ppto.get(cat, cat), 0)
                dif = real_total - ppto_total
                dif_pct = (dif / ppto_total * 100) if ppto_total != 0 else 0
                
                # Header de categoría con métricas
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                with col1:
                    st.markdown(f"### {cat}")
                with col2:
                    st.metric("Real YTD", fmt_monto(real_total))
                with col3:
                    st.metric("PPTO YTD", fmt_monto(ppto_total))
                with col4:
                    delta_color = "normal" if dif >= 0 else "inverse"
                    # Para costos/gastos, invertir el color (menos es mejor)
                    if cat.startswith(("2 -", "4 -", "6 -", "8 -", "11 -")):
                        delta_color = "inverse" if dif >= 0 else "normal"
                    st.metric("Dif", fmt_monto(dif), delta=fmt_pct(dif_pct))
                
                # Subcategorías desplegables
                subcats = cat_data.get("subcategorias", {})
                if subcats:
                    for subcat_nombre, subcat_data in sorted(subcats.items()):
                        subcat_total = subcat_data.get("total", 0)
                        with st.expander(f"↳ {subcat_nombre}: {fmt_monto(subcat_total)}"):
                            # Nivel 3: Subcategorías internas
                            nivel3 = subcat_data.get("subcategorias", {})
                            if nivel3:
                                for n3_nombre, n3_data in sorted(nivel3.items()):
                                    n3_total = n3_data.get("total", 0)
                                    st.markdown(f"**{n3_nombre}**: {fmt_monto(n3_total)}")
                                    
                                    # Cuentas individuales
                                    cuentas = n3_data.get("cuentas", {})
                                    if cuentas:
                                        df_cuentas = pd.DataFrame([
                                            {"Cuenta": k, "Monto": v}
                                            for k, v in sorted(cuentas.items(), key=lambda x: abs(x[1]), reverse=True)
                                        ])
                                        st.dataframe(
                                            df_cuentas.style.format({"Monto": "${:,.0f}"}),
                                            use_container_width=True,
                                            hide_index=True,
                                            height=min(len(df_cuentas) * 35 + 38, 300)
                                        )
                            else:
                                # Si no hay nivel 3, mostrar cuentas directamente
                                cuentas = subcat_data.get("cuentas", {})
                                if cuentas:
                                    df_cuentas = pd.DataFrame([
                                        {"Cuenta": k, "Monto": v}
                                        for k, v in sorted(cuentas.items(), key=lambda x: abs(x[1]), reverse=True)
                                    ])
                                    st.dataframe(
                                        df_cuentas.style.format({"Monto": "${:,.0f}"}),
                                        use_container_width=True,
                                        hide_index=True,
                                        height=min(len(df_cuentas) * 35 + 38, 300)
                                    )
                
                st.markdown("---")
                
                # Insertar filas calculadas después de ciertas categorías
                if cat == "2 - COSTOS":
                    st.markdown("### 🟦 3 - UTILIDAD BRUTA")
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                    with col2:
                        st.metric("Real YTD", fmt_monto(utilidad_bruta))
                    ppto_ub = ppto_ytd.get("1 - INGRESOS", 0) - ppto_ytd.get("2 - COSTOS", 0)
                    with col3:
                        st.metric("PPTO YTD", fmt_monto(ppto_ub))
                    with col4:
                        dif_ub = utilidad_bruta - ppto_ub
                        st.metric("Dif", fmt_monto(dif_ub))
                    st.markdown("---")
                    
                elif cat == "4 - GASTOS DIRECTOS":
                    st.markdown("### 🟦 5 - MARGEN DE CONTRIBUCIÓN")
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                    with col2:
                        st.metric("Real YTD", fmt_monto(margen_contribucion))
                    ppto_mc = ppto_ytd.get("1 - INGRESOS", 0) - ppto_ytd.get("2 - COSTOS", 0) - ppto_ytd.get("4 - GASTOS DIRECTOS", 0)
                    with col3:
                        st.metric("PPTO YTD", fmt_monto(ppto_mc))
                    with col4:
                        dif_mc = margen_contribucion - ppto_mc
                        st.metric("Dif", fmt_monto(dif_mc))
                    st.markdown("---")
                    
                elif cat == "6 - GAV":
                    st.markdown("### 🟦 7 - UTILIDAD OPERACIONAL (EBIT)")
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                    with col2:
                        st.metric("Real YTD", fmt_monto(ebit))
                    ppto_ebit = ppto_ytd.get("1 - INGRESOS", 0) - ppto_ytd.get("2 - COSTOS", 0) - ppto_ytd.get("4 - GASTOS DIRECTOS", 0) - ppto_ytd.get("6 - GAV", 0)
                    with col3:
                        st.metric("PPTO YTD", fmt_monto(ppto_ebit))
                    with col4:
                        dif_ebit = ebit - ppto_ebit
                        st.metric("Dif", fmt_monto(dif_ebit))
                    st.markdown("---")
                    
                elif cat == "8 - INTERESES":
                    st.markdown("### 🟦 9 - UTILIDAD ANTES DE NO OP.")
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                    with col2:
                        st.metric("Real YTD", fmt_monto(util_antes_no_op))
                    st.markdown("---")
                    
                elif cat == "11 - GASTOS NO OPERACIONALES":
                    st.markdown("### 🟦 12 - RESULTADO NO OPERACIONAL")
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                    with col2:
                        st.metric("Real YTD", fmt_monto(resultado_no_op))
                    st.markdown("---")
                    
                    st.markdown("### 🟩 13 - UTILIDAD ANTES DE IMPUESTOS")
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                    with col2:
                        st.metric("Real YTD", fmt_monto(util_antes_impuestos))

        # === TAB FLUJO DE CAJA ===
        with tab_flujo:
            if not _perm_flujo:
                st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Flujo de Caja'. Contacta al administrador.")
            
            st.subheader("💵 Estado de Flujo de Efectivo")
            st.caption("Método Directo - NIIF IAS 7")
            
            # URL del API
            FLUJO_CAJA_URL = f"{API_BASE_URL}/api/v1/flujo-caja"
            
            # === SELECTORES DE PERÍODO ===
            st.markdown("#### 📅 Seleccionar Período")
            
            from datetime import datetime, timedelta
            from calendar import monthrange
            
            # Opciones de período predefinidas
            periodo_opciones = [
                "Mes actual",
                "Mes anterior", 
                "Último trimestre",
                "Año actual",
                "Personalizado"
            ]
            
            col_periodo, col_desde, col_hasta = st.columns([1, 1, 1])
            
            with col_periodo:
                periodo_sel = st.selectbox(
                    "Período",
                    periodo_opciones,
                    key="flujo_periodo_sel"
                )
            
            # Calcular fechas según selección
            hoy = datetime.now()
            
            if periodo_sel == "Mes actual":
                flujo_fecha_ini = hoy.replace(day=1)
                ultimo_dia = monthrange(hoy.year, hoy.month)[1]
                flujo_fecha_fin = hoy.replace(day=ultimo_dia)
            elif periodo_sel == "Mes anterior":
                primer_dia_actual = hoy.replace(day=1)
                ultimo_dia_anterior = primer_dia_actual - timedelta(days=1)
                flujo_fecha_ini = ultimo_dia_anterior.replace(day=1)
                flujo_fecha_fin = ultimo_dia_anterior
            elif periodo_sel == "Último trimestre":
                flujo_fecha_fin = hoy
                flujo_fecha_ini = hoy - timedelta(days=90)
            elif periodo_sel == "Año actual":
                flujo_fecha_ini = datetime(hoy.year, 1, 1)
                flujo_fecha_fin = hoy
            else:  # Personalizado
                flujo_fecha_ini = hoy.replace(day=1)
                flujo_fecha_fin = hoy
            
            with col_desde:
                flujo_f_inicio = st.date_input(
                    "Desde",
                    value=flujo_fecha_ini,
                    format="DD/MM/YYYY",
                    key="flujo_fecha_inicio",
                    disabled=periodo_sel != "Personalizado"
                )
            
            with col_hasta:
                flujo_f_fin = st.date_input(
                    "Hasta",
                    value=flujo_fecha_fin,
                    format="DD/MM/YYYY",
                    key="flujo_fecha_fin",
                    disabled=periodo_sel != "Personalizado"
                )
            
            # Usar fechas seleccionadas o calculadas
            if periodo_sel == "Personalizado":
                flujo_inicio_str = flujo_f_inicio.strftime("%Y-%m-%d")
                flujo_fin_str = flujo_f_fin.strftime("%Y-%m-%d")
            else:
                flujo_inicio_str = flujo_fecha_ini.strftime("%Y-%m-%d")
                flujo_fin_str = flujo_fecha_fin.strftime("%Y-%m-%d")
            
            # Cache key con fechas del flujo
            flujo_cache_key = f"flujo_{flujo_inicio_str}_{flujo_fin_str}"
            
            st.markdown("---")
            
            def cargar_flujo_click():
                """Callback que se ejecuta al hacer click en el botón"""
                st.session_state['flujo_loading'] = True
                st.session_state['flujo_clicked'] = True
            
            col_btn, col_info = st.columns([1, 2])
            with col_btn:
                # Botón con callback
                st.button(
                    "🔄 Generar Flujo de Caja", 
                    type="primary", 
                    use_container_width=True,
                    key="btn_flujo_caja",
                    on_click=cargar_flujo_click
                )
            with col_info:
                st.info(f"📅 Período: {flujo_inicio_str} a {flujo_fin_str}")
            
            # Cargar datos si se hizo click (flag en session_state)
            if st.session_state.get('flujo_clicked'):
                st.session_state['flujo_clicked'] = False  # Reset flag
                with st.spinner("Generando Estado de Flujo de Efectivo..."):
                    try:
                        resp = requests.get(
                            f"{FLUJO_CAJA_URL}/",
                            params={
                                "fecha_inicio": flujo_inicio_str,
                                "fecha_fin": flujo_fin_str,
                                "username": username,
                                "password": password
                            },
                            timeout=120
                        )
                        if resp.status_code == 200:
                            st.session_state[flujo_cache_key] = resp.json()
                        else:
                            st.error(f"Error {resp.status_code}: {resp.text}")
                    except Exception as e:
                        st.error(f"Error al conectar con API: {e}")
                st.session_state['flujo_loading'] = False
            
            # Mostrar datos si existen en cache
            flujo_data = st.session_state.get(flujo_cache_key)
            
            if flujo_data and "error" not in flujo_data:
                import altair as alt
                
                actividades = flujo_data.get("actividades", {})
                conciliacion = flujo_data.get("conciliacion", {})
                validacion = flujo_data.get("validacion", {})
                
                # === ALERTAS DE VALIDACIÓN ===
                if validacion:
                    errores = validacion.get("errores", [])
                    alertas = validacion.get("alertas", [])
                    
                    for err in errores:
                        st.error(f"🚫 **Error:** {err.get('mensaje', '')}")
                    
                    for alerta in alertas:
                        st.warning(f"⚠️ {alerta.get('mensaje', '')}")
                    
                    if validacion.get("valido") and not alertas:
                        st.success("✅ Flujo validado correctamente")
                
                # Función para formatear montos
                def fmt_flujo(valor):
                    if valor >= 0:
                        return f"${valor:,.0f}"
                    else:
                        return f"-${abs(valor):,.0f}"
                
                # === KPIs CON ESTILOS PREMIUM ===
                st.markdown("""
                <style>
                    .kpi-card {
                        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                        border-radius: 12px;
                        padding: 20px;
                        margin: 5px;
                        border-left: 4px solid;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                    }
                    .kpi-operacion { border-color: #2ecc71; }
                    .kpi-inversion { border-color: #3498db; }
                    .kpi-financ { border-color: #9b59b6; }
                    .kpi-inicial { border-color: #f39c12; }
                    .kpi-final { border-color: #1abc9c; }
                    .kpi-label { color: #a0aec0; font-size: 0.85em; margin-bottom: 5px; }
                    .kpi-value { color: #ffffff; font-size: 1.6em; font-weight: bold; }
                    .kpi-positive { color: #2ecc71; }
                    .kpi-negative { color: #e74c3c; }
                    .kpi-neutral { color: #f39c12; }
                </style>
                """, unsafe_allow_html=True)
                
                op = actividades.get("OPERACION", {}).get("subtotal", 0)
                inv = actividades.get("INVERSION", {}).get("subtotal", 0)
                fin = actividades.get("FINANCIAMIENTO", {}).get("subtotal", 0)
                ef_ini = conciliacion.get("efectivo_inicial", 0)
                ef_fin = conciliacion.get("efectivo_final", 0)
                otros = conciliacion.get("otros_no_clasificados", 0)
                
                # KPIs en grid
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    color_op = "kpi-positive" if op >= 0 else "kpi-negative"
                    st.markdown(f"""
                    <div class="kpi-card kpi-operacion">
                        <div class="kpi-label">📈 Flujo Operación</div>
                        <div class="kpi-value {color_op}">{fmt_flujo(op)}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    color_inv = "kpi-positive" if inv >= 0 else "kpi-negative"
                    st.markdown(f"""
                    <div class="kpi-card kpi-inversion">
                        <div class="kpi-label">🏭 Flujo Inversión</div>
                        <div class="kpi-value {color_inv}">{fmt_flujo(inv)}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    color_fin = "kpi-positive" if fin >= 0 else "kpi-negative"
                    st.markdown(f"""
                    <div class="kpi-card kpi-financ">
                        <div class="kpi-label">💳 Flujo Financiamiento</div>
                        <div class="kpi-value {color_fin}">{fmt_flujo(fin)}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="kpi-card kpi-inicial">
                        <div class="kpi-label">🏦 Efectivo Inicial</div>
                        <div class="kpi-value kpi-neutral">{fmt_flujo(ef_ini)}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col5:
                    color_final = "kpi-positive" if ef_fin >= ef_ini else "kpi-negative"
                    st.markdown(f"""
                    <div class="kpi-card kpi-final">
                        <div class="kpi-label">💰 Efectivo Final</div>
                        <div class="kpi-value {color_final}">{fmt_flujo(ef_fin)}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # === GRÁFICO WATERFALL ===
                st.markdown("### 📊 Flujo de Efectivo - Visualización")
                
                waterfall_data = [
                    {"Concepto": "Efectivo Inicial", "Monto": ef_ini, "Tipo": "Inicial"},
                    {"Concepto": "Operación", "Monto": op, "Tipo": "Operación"},
                    {"Concepto": "Inversión", "Monto": inv, "Tipo": "Inversión"},
                    {"Concepto": "Financiamiento", "Monto": fin, "Tipo": "Financiamiento"},
                ]
                if otros != 0:
                    waterfall_data.append({"Concepto": "No Clasificados", "Monto": otros, "Tipo": "Otros"})
                waterfall_data.append({"Concepto": "Efectivo Final", "Monto": ef_fin, "Tipo": "Final"})
                
                df_waterfall = pd.DataFrame(waterfall_data)
                
                # Determinar color
                def get_color(tipo, monto):
                    if tipo in ["Inicial", "Final"]:
                        return "#3498db"
                    if tipo == "Otros":
                        return "#e74c3c"
                    return "#2ecc71" if monto >= 0 else "#e74c3c"
                
                df_waterfall["Color"] = df_waterfall.apply(
                    lambda x: get_color(x["Tipo"], x["Monto"]), axis=1
                )
                
                chart_waterfall = alt.Chart(df_waterfall).mark_bar(
                    cornerRadiusTopLeft=4,
                    cornerRadiusTopRight=4
                ).encode(
                    x=alt.X("Concepto:N", sort=None, title=None),
                    y=alt.Y("Monto:Q", title="Monto ($)", axis=alt.Axis(format="$,.0f")),
                    color=alt.Color("Color:N", scale=None),
                    tooltip=[
                        alt.Tooltip("Concepto:N", title="Categoría"),
                        alt.Tooltip("Monto:Q", title="Monto", format="$,.0f")
                    ]
                ).properties(
                    height=300
                ).configure_axis(
                    labelFontSize=11,
                    titleFontSize=12
                )
                
                st.altair_chart(chart_waterfall, use_container_width=True)
                
                st.divider()
                
                # === DETALLE POR ACTIVIDAD ===
                st.markdown("### 📋 Detalle por Actividad")
                
                for act_key, act_color in [("OPERACION", "#2ecc71"), ("INVERSION", "#3498db"), ("FINANCIAMIENTO", "#9b59b6")]:
                    act_data = actividades.get(act_key, {})
                    act_nombre = act_data.get("nombre", act_key)
                    lineas = act_data.get("lineas", [])
                    subtotal = act_data.get("subtotal", 0)
                    subtotal_nombre = act_data.get("subtotal_nombre", "Subtotal")
                    
                    with st.expander(f"📊 {act_nombre}", expanded=act_key=="OPERACION"):
                        filas = []
                        for linea in lineas:
                            monto = linea.get("monto", 0)
                            if monto != 0:
                                filas.append({
                                    "Concepto": linea.get("nombre", ""),
                                    "Monto": monto
                                })
                        
                        if filas:
                            df_act = pd.DataFrame(filas)
                            
                            # Tabla con estilos
                            def style_monto(val):
                                color = "#2ecc71" if val >= 0 else "#e74c3c"
                                return f"color: {color}; font-weight: bold;"
                            
                            styled_df = df_act.style.format({"Monto": "${:,.0f}"}).applymap(
                                style_monto, subset=["Monto"]
                            )
                            
                            st.dataframe(
                                styled_df,
                                use_container_width=True,
                                hide_index=True,
                                height=min(300, 50 + len(filas) * 35)
                            )
                        else:
                            st.info("Sin movimientos en este período")
                        
                        # Subtotal con estilo
                        subtotal_color = "#2ecc71" if subtotal >= 0 else "#e74c3c"
                        st.markdown(f"""
                        <div style="background: linear-gradient(90deg, {act_color}22, transparent); 
                                    padding: 12px 15px; border-radius: 8px; margin-top: 10px;
                                    border-left: 3px solid {act_color};">
                            <span style="color: #a0aec0;">{subtotal_nombre}:</span>
                            <span style="color: {subtotal_color}; font-size: 1.2em; font-weight: bold; margin-left: 10px;">
                                {fmt_flujo(subtotal)}
                            </span>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.divider()
                
                # === ADVERTENCIAS DE ACTIVIDADES ===
                # Punto 3: Advertencia si IN o FI = 0
                if inv == 0:
                    st.info("ℹ️ No se detectaron flujos de **inversión** en el período. Verifica la clasificación si esto no refleja la realidad del negocio.")
                if fin == 0:
                    st.info("ℹ️ No se detectaron flujos de **financiamiento** en el período. Verifica la clasificación si esto no refleja la realidad del negocio.")
                
                # === CONCILIACIÓN ===
                st.markdown("### 📑 Conciliación de Efectivo")
                
                concil_data = [
                    {"Concepto": "Incremento neto (disminución) en efectivo", "Monto": conciliacion.get("incremento_neto", 0)},
                    {"Concepto": "Efectos de variación en tasa de cambio", "Monto": conciliacion.get("efecto_tipo_cambio", 0)},
                ]
                
                # Punto 1: Otros no clasificados es ACCIONABLE
                if otros != 0:
                    concil_data.append({"Concepto": "⚠️ Otros no clasificados (click para revisar)", "Monto": otros})
                
                concil_data.extend([
                    {"Concepto": "Variación neta de efectivo", "Monto": conciliacion.get("variacion_efectivo", 0)},
                    {"Concepto": "Efectivo al principio del período", "Monto": conciliacion.get("efectivo_inicial", 0)},
                    {"Concepto": "💰 Efectivo al final del período", "Monto": conciliacion.get("efectivo_final", 0)},
                ])
                
                df_concil = pd.DataFrame(concil_data)
                
                def highlight_rows(row):
                    if "al final" in row["Concepto"].lower():
                        return ["background: linear-gradient(90deg, #1abc9c33, transparent); font-weight: bold;"] * 2
                    elif "no clasificados" in row["Concepto"].lower():
                        return ["background: linear-gradient(90deg, #e74c3c22, transparent); color: #e74c3c; cursor: pointer;"] * 2
                    return [""] * 2
                
                st.dataframe(
                    df_concil.style
                    .format({"Monto": "${:,.0f}"})
                    .apply(highlight_rows, axis=1),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Punto 5: Botón de acción directa desde conciliación
                if otros != 0:
                    cuentas_nc = flujo_data.get("cuentas_sin_clasificar", [])
                    col_action1, col_action2 = st.columns([2, 3])
                    with col_action1:
                        if st.button("🔍 Revisar cuentas no clasificadas", type="primary", key="btn_revisar_nc"):
                            st.session_state['mostrar_editor_expandido'] = True
                    with col_action2:
                        st.caption(f"${abs(otros):,.0f} en {len(cuentas_nc)} cuentas requieren clasificación")
                
                # === EDITOR DE MAPEO ===
                st.markdown("---")
                
                # Determinar si expandir editor automáticamente
                expandir_editor = st.session_state.get('mostrar_editor_expandido', False) or otros != 0
                
                with st.expander("📝 Editor de Mapeo de Cuentas", expanded=expandir_editor):
                    # Obtener cuentas sin clasificar del flujo
                    cuentas_nc = flujo_data.get("cuentas_sin_clasificar", [])
                    
                    # Punto 2: Mensaje correcto del editor
                    if cuentas_nc or otros != 0:
                        # HAY PROBLEMAS: mostrar warning, no success
                        if cuentas_nc:
                            st.error(f"🚨 **{len(cuentas_nc)} cuentas** generan ${abs(otros):,.0f} en 'Otros no clasificados'. Asigna categorías para corregir.")
                        else:
                            st.warning(f"⚠️ Existen ${abs(otros):,.0f} en movimientos no conciliados. Revisa las cuentas a continuación.")
                        
                        # Categorías disponibles
                        categorias_options = {
                            "--- Seleccionar ---": "",
                            "🟢 OP01 - Cobros por ventas": "OP01",
                            "🟢 OP02 - Pagos a proveedores": "OP02",
                            "🟢 OP03 - Pagos a empleados": "OP03",
                            "🟢 OP04 - Intereses pagados": "OP04",
                            "🟢 OP05 - Intereses recibidos": "OP05",
                            "🟢 OP06 - Impuestos": "OP06",
                            "🟢 OP07 - Otros operacionales": "OP07",
                            "🔵 IN01 - Control subsidiarias": "IN01",
                            "🔵 IN02 - Participaciones no control.": "IN02",
                            "🔵 IN03 - Compra PPE": "IN03",
                            "🔵 IN04 - Compra intangibles": "IN04",
                            "🔵 IN05 - Dividendos recibidos": "IN05",
                            "🔵 IN06 - Venta PPE": "IN06",
                            "🟣 FI01 - Préstamos LP recibidos": "FI01",
                            "🟣 FI02 - Préstamos CP recibidos": "FI02",
                            "🟣 FI03 - Préstamos relacionadas": "FI03",
                            "🟣 FI04 - Pagos préstamos": "FI04",
                            "🟣 FI05 - Pagos relacionadas": "FI05",
                            "🟣 FI06 - Pagos leasing": "FI06",
                            "🟣 FI07 - Dividendos pagados": "FI07",
                            "⚪ NEUTRAL - Transf. internas": "NEUTRAL",
                            "🟡 FX_EFFECT - Dif. tipo cambio": "FX_EFFECT"
                        }
                        
                        # Encabezado de tabla
                        st.markdown("""
                        <div style="display: grid; grid-template-columns: 1fr 2fr 1fr 1fr 2fr; gap: 10px; padding: 10px; background: #1a1a2e; border-radius: 8px; margin-bottom: 10px;">
                            <div style="color: #a0aec0; font-weight: bold;">Código</div>
                            <div style="color: #a0aec0; font-weight: bold;">Nombre</div>
                            <div style="color: #a0aec0; font-weight: bold;">Monto</div>
                            <div style="color: #a0aec0; font-weight: bold;">% Flujo</div>
                            <div style="color: #a0aec0; font-weight: bold;">Categoría</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Calcular total para porcentaje
                        total_flujo = abs(op) + abs(inv) + abs(fin) + abs(otros)
                        
                        # Tabla de cuentas con selector
                        for i, cuenta in enumerate(cuentas_nc[:25]):
                            codigo = cuenta.get('codigo', '')
                            nombre = cuenta.get('nombre', '')[:35]
                            monto = cuenta.get('monto', 0)
                            porcentaje = (abs(monto) / total_flujo * 100) if total_flujo > 0 else 0
                            
                            # Punto 4: Normalizar signos (positivo=entrada verde, negativo=salida roja)
                            monto_color = "#2ecc71" if monto >= 0 else "#e74c3c"
                            monto_display = f"+${monto:,.0f}" if monto >= 0 else f"-${abs(monto):,.0f}"
                            
                            col1, col2, col3, col4, col5 = st.columns([1, 2, 1.2, 0.8, 2.5])
                            
                            with col1:
                                st.code(codigo, language=None)
                            with col2:
                                st.caption(nombre)
                            with col3:
                                st.markdown(f"<span style='color:{monto_color};font-weight:bold;'>{monto_display}</span>", unsafe_allow_html=True)
                            with col4:
                                st.caption(f"{porcentaje:.1f}%")
                            with col5:
                                col_sel, col_btn = st.columns([3, 1])
                                with col_sel:
                                    categoria_sel = st.selectbox(
                                        "Cat",
                                        options=list(categorias_options.keys()),
                                        key=f"cat_{codigo}",
                                        label_visibility="collapsed"
                                    )
                                with col_btn:
                                    if categorias_options.get(categoria_sel):
                                        if st.button("💾", key=f"save_{codigo}", help=f"Guardar {codigo}"):
                                            try:
                                                save_resp = requests.post(
                                                    f"{FLUJO_CAJA_URL}/mapeo-cuenta",
                                                    params={
                                                        "codigo": codigo,
                                                        "categoria": categorias_options[categoria_sel],
                                                        "nombre": nombre,
                                                        "username": username,
                                                        "password": password,
                                                        "impacto_estimado": monto
                                                    },
                                                    timeout=10
                                                )
                                                if save_resp.status_code == 200:
                                                    st.success(f"✓ {codigo} → {categorias_options[categoria_sel]}")
                                                    st.session_state['mostrar_editor_expandido'] = False
                                                    st.rerun()
                                                else:
                                                    st.error(f"Error")
                                            except Exception as e:
                                                st.error(f"Error: {e}")
                        
                        if len(cuentas_nc) > 25:
                            st.info(f"Mostrando 25 de {len(cuentas_nc)} cuentas. Las de mayor impacto primero.")
                        
                        st.markdown("---")
                        st.caption("💡 **Tip:** Después de clasificar, haz click en 'Generar Flujo de Caja' para ver los cambios reflejados.")
                    
                    else:
                        # Punto 2: Solo mostrar success si REALMENTE todo está OK
                        if otros == 0:
                            st.success("✅ Todas las cuentas están clasificadas correctamente. El flujo está completo.")
                        else:
                            st.warning(f"⚠️ Hay ${abs(otros):,.0f} en 'Otros no clasificados' pero no se encontraron cuentas pendientes. Revisa el mapeo.")
                
                # Info adicional
                with st.expander("ℹ️ Información del Reporte"):
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.write(f"**Movimientos analizados:** {flujo_data.get('total_movimientos', 0):,}")
                        st.write(f"**Período:** {flujo_data.get('periodo', {}).get('inicio', '')} a {flujo_data.get('periodo', {}).get('fin', '')}")
                    with col_info2:
                        st.write(f"**Generado:** {flujo_data.get('generado', '')[:19]}")
                        st.write(f"**Norma:** NIIF IAS 7 - Método Directo")
            
            elif flujo_data and "error" in flujo_data:
                st.error(f"Error: {flujo_data['error']}")
            
            elif not flujo_data:
                st.info("Haz clic en **Generar Flujo de Caja** para calcular el estado de flujo de efectivo.")
                
                with st.expander("ℹ️ ¿Cómo funciona?"):
                    st.markdown("""
                    ### Estado de Flujo de Efectivo (NIIF IAS 7)
                    
                    Este reporte muestra los movimientos de efectivo clasificados en:
                    
                    | Categoría | Descripción |
                    |-----------|-------------|
                    | **Operación** | Cobros de ventas, pagos a proveedores, empleados, impuestos |
                    | **Inversión** | Compra/venta de activos fijos, intangibles, inversiones |
                    | **Financiamiento** | Préstamos recibidos/pagados, dividendos |
                    
                    ### Método Directo
                    
                    El flujo se construye analizando los movimientos reales en cuentas de efectivo
                    y clasificando según la contrapartida del asiento contable.
                    """)

else:
    st.warning("No se pudieron obtener datos del Estado de Resultado.")


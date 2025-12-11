"""
Estado de Resultado contable: ingresos, costos, márgenes y comparación Real vs Presupuesto mensual.
"""

import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from datetime import date, datetime

from shared.auth import proteger_pagina, tiene_acceso_dashboard, get_credenciales

st.set_page_config(page_title="Estado de Resultado", page_icon="📈", layout="wide")

if not proteger_pagina():
    st.stop()

if not tiene_acceso_dashboard("estado_resultado"):
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
        tab_mensual, tab_control_mensual, tab_ytd, tab_cg, tab_detalle = st.tabs(["📅 Agrupado", "💰 Mensualizado", "📊 YTD (Acumulado)", "📊 CG", "📋 Detalle"])

        with tab_mensual:
            st.subheader("Estado de Resultados - Agrupado por Meses Seleccionados")

            # Filtrar datos mensuales por meses seleccionados
            meses_filtro = [f"{año_seleccionado}-{meses_opciones[m]}" for m in meses_seleccionados]

            # Crear DataFrame comparativo mensual
            eerr_mensual = []
            categorias = [
                ("1 - INGRESOS", "ingresos"),
                ("2 - COSTOS", "costos"),
                ("4 - GASTOS DIRECTOS", "gastos_directos"),
                ("6 - GAV", "gav"),
                ("8 - INTERESES", "intereses"),
                ("10 - INGRESOS NO OPERACIONALES", "ingresos_no_operacionales"),
                ("11 - GASTOS NO OPERACIONALES", "gastos_no_operacionales"),
            ]

            for cat_nombre, cat_key in categorias:
                real_mes = sum(datos_mensuales.get(m, {}).get(cat_nombre, 0) for m in meses_filtro if m in datos_mensuales)
                ppto_mes = sum(ppto_mensual.get(m, {}).get(cat_nombre, 0) for m in meses_filtro if m in ppto_mensual)
                dif_mes = real_mes - ppto_mes
                dif_pct = (dif_mes / ppto_mes * 100) if ppto_mes != 0 else 0

                eerr_mensual.append({
                    "Concepto": cat_nombre,
                    "Real Mes": real_mes,
                    "PPTO Mes": ppto_mes,
                    "Dif Mes": dif_mes,
                    "Dif %": dif_pct
                })

            df_mensual = pd.DataFrame(eerr_mensual)

            # Formatear y mostrar
            st.dataframe(
                df_mensual.style.format({
                    "Real Mes": "${:,.0f}",
                    "PPTO Mes": "${:,.0f}",
                    "Dif Mes": "${:,.0f}",
                    "Dif %": "{:.1f}%"
                }),
                use_container_width=True,
                hide_index=True
            )

        with tab_control_mensual:
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

            # Definir categorías principales del EERR
            categorias_eerr = [
                ("1 - INGRESOS", "Ingresos de operación"),
                ("2 - COSTOS", "Costos de venta y operación"),
                ("4 - GASTOS DIRECTOS", "Gastos directos"),
                ("6 - GAV", "Gastos de administración y venta"),
                ("8 - INTERESES", "Gastos financieros"),
                ("10 - INGRESOS NO OPERACIONALES", "Ingresos no operacionales"),
                ("11 - GASTOS NO OPERACIONALES", "Gastos no operacionales"),
            ]

            # Convertir meses seleccionados a números
            meses_nums_sel = [meses_opciones[m] for m in meses_seleccionados]
            meses_nombres_sel = [meses_nombres[m] for m in meses_nums_sel]

            # === VISTA DE REALES MENSUALES ===
            st.write("**📊 Montos Reales (CLP)**")
            tabla_real = {"Concepto": []}
            for cat_name, cat_desc in categorias_eerr:
                tabla_real["Concepto"].append(cat_name)
            
            for mes_num in meses_nums_sel:
                tabla_real[meses_nombres[mes_num]] = []
                for cat_name, cat_desc in categorias_eerr:
                    real_mes = meses_data.get(mes_num, {}).get(cat_name, 0)
                    tabla_real[meses_nombres[mes_num]].append(real_mes)

            df_real_mes = pd.DataFrame(tabla_real)
            st.dataframe(
                df_real_mes.style.format("{:,.0f}", subset=[col for col in df_real_mes.columns if col != "Concepto"]),
                use_container_width=True,
                hide_index=True
            )

            # === VISTA DE PRESUPUESTO MENSUAL ===
            st.write("**💰 Presupuesto (CLP)**")
            tabla_ppto = {"Concepto": []}
            for cat_name, cat_desc in categorias_eerr:
                tabla_ppto["Concepto"].append(cat_name)
            
            for mes_num in meses_nums_sel:
                tabla_ppto[meses_nombres[mes_num]] = []
                mes_key = f"{año_seleccionado}-{mes_num}"
                for cat_name, cat_desc in categorias_eerr:
                    ppto_mes = ppto_mensual.get(mes_key, {}).get(cat_name, 0)
                    tabla_ppto[meses_nombres[mes_num]].append(ppto_mes)

            df_ppto_mes = pd.DataFrame(tabla_ppto)
            st.dataframe(
                df_ppto_mes.style.format("{:,.0f}", subset=[col for col in df_ppto_mes.columns if col != "Concepto"]),
                use_container_width=True,
                hide_index=True
            )

            # === VARIACIONES ===
            st.divider()
            st.write("**📈 Variaciones (Real - PPTO)**")
            tabla_var = {"Concepto": []}
            for cat_name, cat_desc in categorias_eerr:
                tabla_var["Concepto"].append(cat_name)
            
            for mes_num in meses_nums_sel:
                tabla_var[meses_nombres[mes_num]] = []
                mes_key = f"{año_seleccionado}-{mes_num}"
                for cat_name, cat_desc in categorias_eerr:
                    real_mes = meses_data.get(mes_num, {}).get(cat_name, 0)
                    ppto_mes = ppto_mensual.get(mes_key, {}).get(cat_name, 0)
                    tabla_var[meses_nombres[mes_num]].append(real_mes - ppto_mes)

            df_var_mes = pd.DataFrame(tabla_var)
            st.dataframe(
                df_var_mes.style.format("{:,.0f}", subset=[col for col in df_var_mes.columns if col != "Concepto"]),
                use_container_width=True,
                hide_index=True
            )



        with tab_ytd:
            st.subheader("Estado de Resultados - YTD (Acumulado)")

            # === MÉTRICAS PRINCIPALES ===
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                real_ing = resultados.get('ingresos', 0)
                ppto_ing = ppto_ytd.get('1 - INGRESOS', 0)
                dif_ing = ((real_ing - ppto_ing) / ppto_ing * 100) if ppto_ing else 0
                st.metric("Ingresos", f"${real_ing:,.0f}", f"{dif_ing:.1f}% vs PPTO")
            with col2:
                real_cost = resultados.get('costos', 0)
                ppto_cost = ppto_ytd.get('2 - COSTOS', 0)
                dif_cost = ((real_cost - ppto_cost) / ppto_cost * 100) if ppto_cost else 0
                st.metric("Costos", f"${real_cost:,.0f}", f"{dif_cost:.1f}% vs PPTO")
            with col3:
                st.metric("Utilidad Bruta", f"${resultados.get('utilidad_bruta', 0):,.0f}")
            with col4:
                st.metric("Utilidad Operacional", f"${resultados.get('utilidad_operacional', 0):,.0f}")

            st.divider()

            # === TABLA ESTADO DE RESULTADOS YTD ===
            eerr_data = []

            def agregar_fila(concepto, real, ppto, nivel=0):
                dif = real - ppto
                dif_pct = (dif / ppto * 100) if ppto != 0 else 0
                indent = "    " * nivel
                eerr_data.append({
                    "Concepto": f"{indent}{concepto}",
                    "Real YTD": real,
                    "PPTO YTD": ppto,
                    "Dif YTD": dif,
                    "Dif %": dif_pct,
                    "Nivel": nivel
                })

            # Estructura completa
            agregar_fila("1 - INGRESOS", resultados.get("ingresos", 0), ppto_ytd.get("1 - INGRESOS", 0))
            if "1 - INGRESOS" in estructura:
                for subcat, subdata in estructura["1 - INGRESOS"].get("subcategorias", {}).items():
                    agregar_fila(subcat, subdata.get("total", 0), 0, 1)

            agregar_fila("2 - COSTOS", resultados.get("costos", 0), ppto_ytd.get("2 - COSTOS", 0))
            if "2 - COSTOS" in estructura:
                for subcat, subdata in estructura["2 - COSTOS"].get("subcategorias", {}).items():
                    agregar_fila(subcat, subdata.get("total", 0), 0, 1)

            # Utilidad Bruta
            ub_real = resultados.get("utilidad_bruta", 0)
            ub_ppto = ppto_ytd.get("1 - INGRESOS", 0) - ppto_ytd.get("2 - COSTOS", 0)
            agregar_fila("UTILIDAD BRUTA", ub_real, ub_ppto)

            agregar_fila("4 - GASTOS DIRECTOS", resultados.get("gastos_directos", 0), ppto_ytd.get("4 - GASTOS DIRECTOS", 0))
            agregar_fila("6 - GAV", resultados.get("gav", 0), ppto_ytd.get("6 - GAV", 0))

            # Utilidad Operacional
            uo_ppto = ub_ppto - ppto_ytd.get("4 - GASTOS DIRECTOS", 0) - ppto_ytd.get("6 - GAV", 0)
            agregar_fila("UTILIDAD OPERACIONAL", resultados.get("utilidad_operacional", 0), uo_ppto)

            agregar_fila("8 - INTERESES", resultados.get("intereses", 0), ppto_ytd.get("8 - INTERESES", 0))
            agregar_fila("10 - INGRESOS NO OPERACIONALES", resultados.get("ingresos_no_operacionales", 0), ppto_ytd.get("10 - INGRESOS NO OPERACIONALES", 0))
            agregar_fila("11 - GASTOS NO OPERACIONALES", resultados.get("gastos_no_operacionales", 0), ppto_ytd.get("11 - GASTOS NO OPERACIONALES", 0))

            # Resultado No Operacional
            rno_ppto = ppto_ytd.get("10 - INGRESOS NO OPERACIONALES", 0) - ppto_ytd.get("11 - GASTOS NO OPERACIONALES", 0) - ppto_ytd.get("8 - INTERESES", 0)
            agregar_fila("RESULTADO NO OPERACIONAL", resultados.get("resultado_no_operacional", 0), rno_ppto)

            # Utilidad antes de impuestos
            uai_ppto = uo_ppto + rno_ppto
            agregar_fila("UTILIDAD ANTES DE IMPUESTOS", resultados.get("utilidad_antes_impuestos", 0), uai_ppto)

            df_eerr = pd.DataFrame(eerr_data)

            # Mostrar tabla con formato
            st.dataframe(
                df_eerr[["Concepto", "Real YTD", "PPTO YTD", "Dif YTD", "Dif %"]].style.format({
                    "Real YTD": "${:,.0f}",
                    "PPTO YTD": "${:,.0f}",
                    "Dif YTD": "${:,.0f}",
                    "Dif %": "{:.1f}%"
                }),
                use_container_width=True,
                hide_index=True
            )

        with tab_cg:
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
            st.subheader("Detalle por Categoría")

            # Selector de categoría
            categoria_sel = st.selectbox(
                "Seleccionar categoría",
                list(estructura.keys())
            )

            if categoria_sel and categoria_sel in estructura:
                cat_data = estructura[categoria_sel]
                st.metric(f"Total {categoria_sel}", f"${cat_data.get('total', 0):,.0f}")

                # Mostrar subcategorías
                for subcat, subdata in cat_data.get("subcategorias", {}).items():
                    with st.expander(f"{subcat}: ${subdata.get('total', 0):,.0f}"):
                        # Mostrar cuentas individuales
                        cuentas_df = pd.DataFrame([
                            {"Cuenta": k, "Monto": v}
                            for k, v in subdata.get("cuentas", {}).items()
                        ])
                        if not cuentas_df.empty:
                            st.dataframe(
                                cuentas_df.style.format({"Monto": "${:,.0f}"}),
                                use_container_width=True,
                                hide_index=True
                            )

        st.divider()

        # === EVOLUCIÓN MENSUAL ===
        if datos_mensuales:
            st.subheader("📈 Evolución Mensual")

            # Convertir a DataFrame
            df_evol = pd.DataFrame(datos_mensuales).T
            df_evol.index.name = "Mes"
            df_evol = df_evol.reset_index()

            # Gráfico de líneas
            col_graf1, col_graf2 = st.columns(2)
            with col_graf1:
                st.line_chart(df_evol.set_index("Mes")[["1 - INGRESOS", "2 - COSTOS"]])
            with col_graf2:
                st.line_chart(df_evol.set_index("Mes")[["6 - GAV", "4 - GASTOS DIRECTOS"]])

        # === INFO ADICIONAL ===
        with st.expander("ℹ️ Información del reporte"):
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.write(f"**Total movimientos procesados:** {datos.get('total_movimientos', 0):,}")
                st.write(f"**Período:** {fecha_inicio} a {fecha_fin}")
            with col_info2:
                st.write(f"**Centro de costo:** {centro_seleccionado}")
                st.write(f"**Año presupuesto:** {año_seleccionado}")
                if ppto and "error" not in ppto:
                    st.write(f"**Registros PPTO:** {ppto.get('total_registros', 'N/A')}")

else:
    st.warning("No se pudieron obtener datos del Estado de Resultado.")

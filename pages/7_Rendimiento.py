"""
Rendimiento Productivo: Dashboard de análisis de eficiencia por lote de fruta.
Trazabilidad: Lote MP → MO → Lote PT
Versión 2: Con PT detalle, salas, ranking, alertas y Excel
"""
import streamlit as st
import pandas as pd
import requests
import altair as alt
from datetime import datetime, timedelta
import sys
import os
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.auth import proteger_pagina, get_credenciales


# --- Funciones de formateo chileno ---
def fmt_numero(valor, decimales=0):
    """Formatea número con punto como miles y coma como decimal"""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "0"
    try:
        if decimales > 0:
            formatted = f"{valor:,.{decimales}f}"
        else:
            formatted = f"{valor:,.0f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except:
        return str(valor)


def fmt_porcentaje(valor, decimales=1):
    """Formatea porcentaje"""
    return f"{fmt_numero(valor, decimales)}%"


def get_alert_color(rendimiento):
    """Retorna color según rendimiento"""
    if rendimiento >= 95:
        return "🟢"
    elif rendimiento >= 90:
        return "🟡"
    else:
        return "🔴"


# Configuración de página
st.set_page_config(page_title="Rendimiento", page_icon="📊", layout="wide")

# Autenticación
if not proteger_pagina():
    st.stop()

username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales. Por favor inicie sesión nuevamente.")
    st.stop()

st.title("📊 Rendimiento Productivo")
st.caption("Análisis de eficiencia por lote de materia prima (MP) → Producto Terminado (PT)")

# API URL
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# --- Estado de sesión ---
if 'rend_data' not in st.session_state:
    st.session_state.rend_data = None
if 'rend_lotes' not in st.session_state:
    st.session_state.rend_lotes = None
if 'rend_proveedores' not in st.session_state:
    st.session_state.rend_proveedores = None
if 'rend_mos' not in st.session_state:
    st.session_state.rend_mos = None
if 'rend_ranking' not in st.session_state:
    st.session_state.rend_ranking = None
if 'rend_salas' not in st.session_state:
    st.session_state.rend_salas = None
if 'rend_pt_detalle' not in st.session_state:
    st.session_state.rend_pt_detalle = None
if 'rend_consolidado' not in st.session_state:
    st.session_state.rend_consolidado = None

# --- Filtros ---
st.sidebar.header("📅 Filtros de Período")
col1, col2 = st.sidebar.columns(2)
with col1:
    fecha_inicio = st.date_input(
        "Desde",
        datetime.now() - timedelta(days=30),
        format="DD/MM/YYYY"
    )
with col2:
    fecha_fin = st.date_input(
        "Hasta",
        datetime.now(),
        format="DD/MM/YYYY"
    )

if st.sidebar.button("🔄 Consultar Rendimiento", type="primary", use_container_width=True):
    params = {
        "username": username,
        "password": password,
        "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
        "fecha_fin": fecha_fin.strftime("%Y-%m-%d")
    }
    
    with st.spinner("Cargando datos de rendimiento..."):
        try:
            # Obtener overview
            resp_overview = requests.get(f"{API_URL}/api/v1/rendimiento/overview", params=params, timeout=120)
            if resp_overview.status_code == 200:
                st.session_state.rend_data = resp_overview.json()
            
            # Obtener lotes
            resp_lotes = requests.get(f"{API_URL}/api/v1/rendimiento/lotes", params=params, timeout=120)
            if resp_lotes.status_code == 200:
                st.session_state.rend_lotes = resp_lotes.json()
            
            # Obtener proveedores
            resp_prov = requests.get(f"{API_URL}/api/v1/rendimiento/proveedores", params=params, timeout=120)
            if resp_prov.status_code == 200:
                st.session_state.rend_proveedores = resp_prov.json()
            
            # Obtener MOs
            resp_mos = requests.get(f"{API_URL}/api/v1/rendimiento/mos", params=params, timeout=120)
            if resp_mos.status_code == 200:
                st.session_state.rend_mos = resp_mos.json()
            
            # Obtener ranking
            resp_ranking = requests.get(f"{API_URL}/api/v1/rendimiento/ranking", params=params, timeout=120)
            if resp_ranking.status_code == 200:
                st.session_state.rend_ranking = resp_ranking.json()
            
            # Obtener salas
            resp_salas = requests.get(f"{API_URL}/api/v1/rendimiento/salas", params=params, timeout=120)
            if resp_salas.status_code == 200:
                st.session_state.rend_salas = resp_salas.json()
            
            # Obtener detalle PT
            resp_pt = requests.get(f"{API_URL}/api/v1/rendimiento/pt-detalle", params=params, timeout=120)
            if resp_pt.status_code == 200:
                st.session_state.rend_pt_detalle = resp_pt.json()
            
            # Obtener consolidado por fruta
            resp_cons = requests.get(f"{API_URL}/api/v1/rendimiento/consolidado", params=params, timeout=120)
            if resp_cons.status_code == 200:
                st.session_state.rend_consolidado = resp_cons.json()
                
        except requests.exceptions.ConnectionError:
            st.error("No se puede conectar al servidor API.")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# --- Mostrar datos ---
data = st.session_state.rend_data

if data:
    # === SECCIÓN 1: KPIs Overview ===
    st.subheader("📈 KPIs Consolidados")
    
    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        st.metric("Total Kg MP", fmt_numero(data['total_kg_mp'], 0))
    with kpi_cols[1]:
        st.metric("Total Kg PT", fmt_numero(data['total_kg_pt'], 0))
    with kpi_cols[2]:
        rend = data['rendimiento_promedio']
        alert = get_alert_color(rend)
        st.metric(f"Rendimiento {alert}", fmt_porcentaje(rend), delta=f"{rend-85:.1f}% vs 85%")
    with kpi_cols[3]:
        st.metric("Merma Total", fmt_numero(data['merma_total_kg'], 0) + " Kg")
    with kpi_cols[4]:
        st.metric("Kg/HH", fmt_numero(data['kg_por_hh'], 1))
    
    kpi_cols2 = st.columns(4)
    with kpi_cols2[0]:
        st.metric("MOs Procesadas", data['mos_procesadas'])
    with kpi_cols2[1]:
        st.metric("Lotes Únicos", data['lotes_unicos'])
    with kpi_cols2[2]:
        st.metric("Total HH", fmt_numero(data['total_hh'], 1))
    with kpi_cols2[3]:
        st.metric("Merma %", fmt_porcentaje(data['merma_pct']))
    
    st.markdown("---")
    
    # === TABS para diferentes vistas ===
    tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🍓 Consolidado", "🧺 Por Lote", "🏭 Por Proveedor", "⚙️ Por MO", 
        "🏠 Por Sala", "📊 Gráficos", "🔍 Trazabilidad"
    ])
    
    # --- TAB 0: CONSOLIDADO POR FRUTA/MANEJO/PRODUCTO ---
    with tab0:
        st.subheader("🍓 Vista Ejecutiva: Consolidado por Fruta")
        consolidado = st.session_state.rend_consolidado
        
        if consolidado:
            resumen = consolidado.get('resumen', {})
            
            # KPIs globales
            kpi_cols = st.columns(4)
            with kpi_cols[0]:
                alert = get_alert_color(resumen.get('rendimiento_global', 0))
                st.metric(f"Rendimiento Global {alert}", fmt_porcentaje(resumen.get('rendimiento_global', 0)))
            with kpi_cols[1]:
                st.metric("Total Kg PT", fmt_numero(resumen.get('total_kg_pt', 0)))
            with kpi_cols[2]:
                st.metric("Total Kg MP", fmt_numero(resumen.get('total_kg_mp', 0)))
            with kpi_cols[3]:
                st.metric("Merma Global", fmt_numero(resumen.get('merma_global', 0)) + " Kg")
            
            st.markdown("---")
            
            # Sub-tabs para los 3 niveles
            sub1, sub2, sub3 = st.tabs(["🍎 Por Tipo Fruta", "🏷️ Fruta + Manejo", "📦 Por Producto"])
            
            # === Por Tipo Fruta ===
            with sub1:
                st.markdown("### Rendimiento por Tipo de Fruta")
                por_fruta = consolidado.get('por_fruta', [])
                
                if por_fruta:
                    for fruta in por_fruta:
                        alert = get_alert_color(fruta['rendimiento'])
                        with st.expander(f"{alert} **{fruta['tipo_fruta']}** | {fmt_numero(fruta['kg_pt'])} Kg PT | Rend: {fmt_porcentaje(fruta['rendimiento'])}"):
                            cols = st.columns(4)
                            with cols[0]:
                                st.metric("Rendimiento", fmt_porcentaje(fruta['rendimiento']))
                            with cols[1]:
                                st.metric("Kg/HH", fmt_numero(fruta.get('kg_por_hh', 0), 1))
                            with cols[2]:
                                st.metric("Kg/Hora", fmt_numero(fruta.get('kg_por_hora', 0), 1))
                            with cols[3]:
                                st.metric("Merma", fmt_numero(fruta['merma']) + " Kg")
                            
                            cols2 = st.columns(4)
                            with cols2[0]:
                                st.markdown(f"**Kg MP:** {fmt_numero(fruta['kg_mp'])}")
                            with cols2[1]:
                                st.markdown(f"**Kg PT:** {fmt_numero(fruta['kg_pt'])}")
                            with cols2[2]:
                                st.markdown(f"**Lotes:** {fruta['num_lotes']}")
                            with cols2[3]:
                                st.markdown(f"**Proveedores:** {fruta.get('num_proveedores', 'N/A')}")
                    
                    # Gráfico resumen
                    df_fruta = pd.DataFrame(por_fruta)
                    chart = alt.Chart(df_fruta).mark_bar().encode(
                        x=alt.X('tipo_fruta:N', sort='-y', title='Tipo Fruta'),
                        y=alt.Y('rendimiento:Q', title='Rendimiento %'),
                        color=alt.condition(
                            alt.datum.rendimiento >= 90,
                            alt.value('#28a745'),
                            alt.value('#dc3545')
                        ),
                        tooltip=['tipo_fruta', 'kg_pt', 'rendimiento', 'num_lotes']
                    ).properties(height=300)
                    st.altair_chart(chart, use_container_width=True)
            
            # === Por Fruta + Manejo ===
            with sub2:
                st.markdown("### Rendimiento por Fruta + Manejo")
                por_fm = consolidado.get('por_fruta_manejo', [])
                
                if por_fm:
                    # Filtro por fruta
                    frutas = sorted(set(d['tipo_fruta'] for d in por_fm))
                    fruta_sel = st.selectbox("Filtrar por Fruta", ["Todos"] + frutas)
                    
                    df_fm = pd.DataFrame(por_fm)
                    if fruta_sel != "Todos":
                        df_fm = df_fm[df_fm['tipo_fruta'] == fruta_sel]
                    
                    # Tabla
                    df_fm['estado'] = df_fm['rendimiento'].apply(get_alert_color)
                    df_display = df_fm[['estado', 'tipo_fruta', 'manejo', 'kg_mp', 'kg_pt', 'rendimiento', 'merma', 'num_lotes']].copy()
                    df_display.columns = ['', 'Fruta', 'Manejo', 'Kg MP', 'Kg PT', 'Rend %', 'Merma', 'Lotes']
                    df_display['Kg MP'] = df_display['Kg MP'].apply(lambda x: fmt_numero(x, 0))
                    df_display['Kg PT'] = df_display['Kg PT'].apply(lambda x: fmt_numero(x, 0))
                    df_display['Rend %'] = df_display['Rend %'].apply(lambda x: fmt_porcentaje(x))
                    df_display['Merma'] = df_display['Merma'].apply(lambda x: fmt_numero(x, 0))
                    
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # === Por Producto ===
            with sub3:
                st.markdown("### Rendimiento por Producto MP")
                por_prod = consolidado.get('por_producto', [])
                
                if por_prod:
                    # Filtros
                    cols = st.columns(2)
                    with cols[0]:
                        frutas = sorted(set(d['tipo_fruta'] for d in por_prod))
                        fruta_prod = st.selectbox("Filtrar Fruta", ["Todos"] + frutas, key="prod_fruta")
                    with cols[1]:
                        manejos = sorted(set(d['manejo'] for d in por_prod))
                        manejo_prod = st.selectbox("Filtrar Manejo", ["Todos"] + manejos, key="prod_manejo")
                    
                    df_prod = pd.DataFrame(por_prod)
                    if fruta_prod != "Todos":
                        df_prod = df_prod[df_prod['tipo_fruta'] == fruta_prod]
                    if manejo_prod != "Todos":
                        df_prod = df_prod[df_prod['manejo'] == manejo_prod]
                    
                    # Tabla
                    df_prod['estado'] = df_prod['rendimiento'].apply(get_alert_color)
                    df_display = df_prod[['estado', 'producto', 'tipo_fruta', 'manejo', 'kg_mp', 'kg_pt', 'rendimiento', 'merma']].copy()
                    df_display.columns = ['', 'Producto', 'Fruta', 'Manejo', 'Kg MP', 'Kg PT', 'Rend %', 'Merma']
                    df_display['Kg MP'] = df_display['Kg MP'].apply(lambda x: fmt_numero(x, 0))
                    df_display['Kg PT'] = df_display['Kg PT'].apply(lambda x: fmt_numero(x, 0))
                    df_display['Rend %'] = df_display['Rend %'].apply(lambda x: fmt_porcentaje(x))
                    df_display['Merma'] = df_display['Merma'].apply(lambda x: fmt_numero(x, 0))
                    
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("Carga los datos para ver el consolidado por fruta.")
    
    # --- TAB 1: Por Lote con Alertas y PT Detalle ---
    with tab1:
        st.subheader("Rendimiento por Lote de MP")
        lotes = st.session_state.rend_lotes
        pt_detalle = st.session_state.rend_pt_detalle or {}
        
        if lotes:
            df_lotes = pd.DataFrame(lotes)
            
            # === FILTROS ===
            st.markdown("**Filtrar por:**")
            filter_cols = st.columns(4)
            
            with filter_cols[0]:
                proveedores_unicos = sorted(df_lotes['proveedor'].unique().tolist())
                prov_filtro = st.multiselect("Proveedor", proveedores_unicos)
            
            with filter_cols[1]:
                if 'tipo_fruta' in df_lotes.columns:
                    frutas_unicas = sorted(df_lotes['tipo_fruta'].unique().tolist())
                    fruta_filtro = st.multiselect("Tipo Fruta", frutas_unicas)
                else:
                    fruta_filtro = []
            
            with filter_cols[2]:
                if 'manejo' in df_lotes.columns:
                    manejos_unicos = sorted(df_lotes['manejo'].unique().tolist())
                    manejo_filtro = st.multiselect("Manejo", manejos_unicos)
                else:
                    manejo_filtro = []
            
            with filter_cols[3]:
                # Filtro de alerta
                alerta_filtro = st.selectbox("Alertas", ["Todos", "🔴 Crítico (<90%)", "🟡 Atención (<95%)"])
            
            # Aplicar filtros
            df_filtered = df_lotes.copy()
            if prov_filtro:
                df_filtered = df_filtered[df_filtered['proveedor'].isin(prov_filtro)]
            if fruta_filtro:
                df_filtered = df_filtered[df_filtered['tipo_fruta'].isin(fruta_filtro)]
            if manejo_filtro:
                df_filtered = df_filtered[df_filtered['manejo'].isin(manejo_filtro)]
            if alerta_filtro == "🔴 Crítico (<90%)":
                df_filtered = df_filtered[df_filtered['rendimiento'] < 90]
            elif alerta_filtro == "🟡 Atención (<95%)":
                df_filtered = df_filtered[df_filtered['rendimiento'] < 95]
            
            # Agregar columna de alerta
            df_filtered['estado'] = df_filtered['rendimiento'].apply(get_alert_color)
            
            st.caption(f"Mostrando {len(df_filtered)} de {len(df_lotes)} lotes")
            
            # Mostrar lotes con expander para PT detalle
            for _, row in df_filtered.iterrows():
                lot_id = row.get('lot_id')
                lot_name = row.get('lot_name', 'N/A')
                rend = row.get('rendimiento', 0)
                alert = get_alert_color(rend)
                
                with st.expander(f"{alert} **{lot_name}** | {row.get('product_name', '')[:50]} | Rend: {fmt_porcentaje(rend)} | MP: {fmt_numero(row.get('kg_consumidos', 0))} Kg"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**Proveedor:** {row.get('proveedor', 'N/A')}")
                        st.markdown(f"**OC:** {row.get('orden_compra', 'N/A')}")
                        st.markdown(f"**Fecha Recepción:** {row.get('fecha_recepcion', 'N/A')}")
                    with col2:
                        st.markdown(f"**Kg MP:** {fmt_numero(row.get('kg_consumidos', 0))}")
                        st.markdown(f"**Kg PT:** {fmt_numero(row.get('kg_producidos', 0))}")
                        st.markdown(f"**Merma:** {fmt_numero(row.get('merma', 0))} Kg ({fmt_porcentaje(row.get('merma_pct', 0))})")
                    with col3:
                        st.markdown(f"**Tipo Fruta:** {row.get('tipo_fruta', 'N/A')}")
                        st.markdown(f"**Manejo:** {row.get('manejo', 'N/A')}")
                        st.markdown(f"**MOs:** {row.get('num_mos', 0)}")
                    
                    # Mostrar detalle PT
                    if str(lot_id) in pt_detalle:
                        st.markdown("---")
                        st.markdown("**📦 Productos de Salida (PT):**")
                        pt_list = pt_detalle[str(lot_id)]
                        if pt_list:
                            df_pt = pd.DataFrame(pt_list)
                            df_pt['kg'] = df_pt['kg'].apply(lambda x: fmt_numero(x, 2))
                            st.dataframe(df_pt[['product_name', 'lot_name', 'kg']], use_container_width=True, hide_index=True)
            
            # Excel export
            st.markdown("---")
            try:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_lotes.to_excel(writer, sheet_name='Lotes', index=False)
                st.download_button(
                    "📥 Descargar Excel",
                    buffer.getvalue(),
                    "rendimiento_lotes.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except:
                csv = df_lotes.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Descargar CSV", csv, "rendimiento_lotes.csv", "text/csv")
    
    # --- TAB 2: Por Proveedor con Ranking ---
    with tab2:
        st.subheader("Rendimiento por Proveedor")
        ranking = st.session_state.rend_ranking
        proveedores = st.session_state.rend_proveedores
        
        if ranking:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🏆 Top 5 Mejores")
                for i, p in enumerate(ranking.get('top', [])[:5]):
                    alert = get_alert_color(p['rendimiento'])
                    st.markdown(f"**{i+1}. {alert} {p['proveedor'][:40]}** - {fmt_porcentaje(p['rendimiento'])} ({fmt_numero(p['kg_consumidos'])} Kg)")
            
            with col2:
                st.markdown("### ⚠️ Bottom 5 - Atención")
                for i, p in enumerate(ranking.get('bottom', [])[:5]):
                    alert = get_alert_color(p['rendimiento'])
                    st.markdown(f"**{i+1}. {alert} {p['proveedor'][:40]}** - {fmt_porcentaje(p['rendimiento'])} ({fmt_numero(p['kg_consumidos'])} Kg)")
            
            st.markdown("---")
            st.metric("Rendimiento Promedio Proveedores", fmt_porcentaje(ranking.get('promedio_rendimiento', 0)))
        
        if proveedores:
            df_prov = pd.DataFrame(proveedores)
            
            # Tabla con alertas
            df_prov['estado'] = df_prov['rendimiento'].apply(get_alert_color)
            df_prov_display = df_prov[['estado', 'proveedor', 'kg_consumidos', 'kg_producidos', 'rendimiento', 'merma', 'lotes']].copy()
            df_prov_display.columns = ['', 'Proveedor', 'Kg MP', 'Kg PT', 'Rend %', 'Merma Kg', 'Lotes']
            
            df_prov_display['Kg MP'] = df_prov_display['Kg MP'].apply(lambda x: fmt_numero(x, 0))
            df_prov_display['Kg PT'] = df_prov_display['Kg PT'].apply(lambda x: fmt_numero(x, 0))
            df_prov_display['Rend %'] = df_prov_display['Rend %'].apply(lambda x: fmt_porcentaje(x))
            df_prov_display['Merma Kg'] = df_prov_display['Merma Kg'].apply(lambda x: fmt_numero(x, 0))
            
            st.dataframe(df_prov_display, use_container_width=True, hide_index=True)
            
            # Gráfico de barras
            chart_prov = alt.Chart(df_prov).mark_bar().encode(
                x=alt.X('proveedor:N', sort='-y', title='Proveedor', axis=alt.Axis(labelAngle=-45, labelLimit=200)),
                y=alt.Y('rendimiento:Q', title='Rendimiento %'),
                color=alt.condition(
                    alt.datum.rendimiento >= 90,
                    alt.value('#28a745'),
                    alt.value('#dc3545')
                ),
                tooltip=['proveedor', 'rendimiento', 'kg_consumidos']
            ).properties(width=700, height=400)
            
            st.altair_chart(chart_prov, use_container_width=True)
    
    # --- TAB 3: Por MO con Sala ---
    with tab3:
        st.subheader("Rendimiento por Orden de Fabricación")
        mos = st.session_state.rend_mos
        
        if mos:
            df_mos = pd.DataFrame(mos)
            
            # Filtro por sala
            if 'sala' in df_mos.columns:
                salas_unicas = sorted([s for s in df_mos['sala'].unique() if s])
                sala_filtro = st.multiselect("Filtrar por Sala", salas_unicas)
                if sala_filtro:
                    df_mos = df_mos[df_mos['sala'].isin(sala_filtro)]
            
            # Agregar alertas
            df_mos['estado'] = df_mos['rendimiento'].apply(get_alert_color)
            
            df_mos_display = df_mos[['estado', 'mo_name', 'sala', 'kg_mp', 'kg_pt', 'rendimiento', 'merma', 'duracion_horas', 'dotacion', 'fecha']].copy()
            df_mos_display.columns = ['', 'MO', 'Sala', 'Kg MP', 'Kg PT', 'Rend %', 'Merma Kg', 'Horas', 'Dotación', 'Fecha']
            
            df_mos_display['Kg MP'] = df_mos_display['Kg MP'].apply(lambda x: fmt_numero(x, 0))
            df_mos_display['Kg PT'] = df_mos_display['Kg PT'].apply(lambda x: fmt_numero(x, 0))
            df_mos_display['Rend %'] = df_mos_display['Rend %'].apply(lambda x: fmt_porcentaje(x))
            df_mos_display['Merma Kg'] = df_mos_display['Merma Kg'].apply(lambda x: fmt_numero(x, 0))
            
            st.dataframe(df_mos_display, use_container_width=True, hide_index=True)
            
            # Estadísticas
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                df_mos_orig = pd.DataFrame(mos)
                st.metric("Duración Promedio", f"{df_mos_orig['duracion_horas'].mean():.1f} h")
            with col_stat2:
                st.metric("Dotación Promedio", f"{df_mos_orig['dotacion'].mean():.1f}")
            with col_stat3:
                st.metric("Rendimiento Mín/Máx", f"{df_mos_orig['rendimiento'].min():.1f}% / {df_mos_orig['rendimiento'].max():.1f}%")
    
    # --- TAB 4: Por Sala (Productividad) ---
    with tab4:
        st.subheader("🏠 Productividad por Sala de Proceso")
        salas = st.session_state.rend_salas
        
        if salas:
            df_salas = pd.DataFrame(salas)
            
            # KPIs por sala
            for _, sala in df_salas.iterrows():
                alert = get_alert_color(sala['rendimiento'])
                with st.expander(f"{alert} **{sala['sala']}** | {fmt_numero(sala['kg_pt'])} Kg PT | {sala['num_mos']} MOs"):
                    cols = st.columns(4)
                    with cols[0]:
                        st.metric("Rendimiento", fmt_porcentaje(sala['rendimiento']))
                    with cols[1]:
                        st.metric("Kg/Hora", fmt_numero(sala['kg_por_hora'], 1))
                    with cols[2]:
                        st.metric("Kg/HH", fmt_numero(sala['kg_por_hh'], 1))
                    with cols[3]:
                        st.metric("Kg/Operario", fmt_numero(sala['kg_por_operario'], 1))
                    
                    cols2 = st.columns(4)
                    with cols2[0]:
                        st.markdown(f"**Kg MP:** {fmt_numero(sala['kg_mp'])}")
                    with cols2[1]:
                        st.markdown(f"**Kg PT:** {fmt_numero(sala['kg_pt'])}")
                    with cols2[2]:
                        st.markdown(f"**HH Total:** {fmt_numero(sala['hh_total'], 1)}")
                    with cols2[3]:
                        st.markdown(f"**Dotación Prom:** {sala['dotacion_promedio']:.1f}")
            
            # Gráfico comparativo
            st.markdown("---")
            st.markdown("### Comparativa de Productividad")
            
            chart_salas = alt.Chart(df_salas).mark_bar().encode(
                x=alt.X('sala:N', sort='-y', title='Sala'),
                y=alt.Y('kg_por_hora:Q', title='Kg/Hora'),
                color=alt.Color('rendimiento:Q', scale=alt.Scale(scheme='redyellowgreen'), title='Rend %'),
                tooltip=['sala', 'kg_por_hora', 'kg_por_hh', 'rendimiento', 'num_mos']
            ).properties(width=700, height=300)
            
            st.altair_chart(chart_salas, use_container_width=True)
    
    # --- TAB 5: Gráficos ---
    with tab5:
        st.subheader("Análisis Gráfico")
        
        lotes = st.session_state.rend_lotes
        if lotes:
            df_lotes = pd.DataFrame(lotes)
            
            # Distribución de rendimiento con líneas de alerta
            st.markdown("### Distribución de Rendimiento por Lote")
            hist_rend = alt.Chart(df_lotes).mark_bar().encode(
                x=alt.X('rendimiento:Q', bin=alt.Bin(maxbins=20), title='Rendimiento %'),
                y=alt.Y('count()', title='Cantidad de Lotes')
            ).properties(width=700, height=300)
            
            rule_90 = alt.Chart(pd.DataFrame({'x': [90]})).mark_rule(color='red', strokeDash=[5,5]).encode(x='x:Q')
            rule_95 = alt.Chart(pd.DataFrame({'x': [95]})).mark_rule(color='orange', strokeDash=[5,5]).encode(x='x:Q')
            
            st.altair_chart(hist_rend + rule_90 + rule_95, use_container_width=True)
            st.caption("🔴 Línea roja: 90% | 🟡 Línea naranja: 95%")
            
            # Rendimiento vs Volumen
            st.markdown("### Rendimiento vs Volumen")
            scatter = alt.Chart(df_lotes).mark_circle(size=60).encode(
                x=alt.X('kg_consumidos:Q', title='Kg Consumidos'),
                y=alt.Y('rendimiento:Q', title='Rendimiento %'),
                color=alt.Color('proveedor:N', legend=alt.Legend(title='Proveedor')),
                tooltip=['lot_name', 'proveedor', 'kg_consumidos', 'rendimiento']
            ).properties(width=700, height=400).interactive()
            
            st.altair_chart(scatter, use_container_width=True)
        
        mos = st.session_state.rend_mos
        if mos:
            df_mos = pd.DataFrame(mos)
            
            st.markdown("### Rendimiento por Fecha")
            line_rend = alt.Chart(df_mos).mark_line(point=True).encode(
                x=alt.X('fecha:T', title='Fecha'),
                y=alt.Y('rendimiento:Q', title='Rendimiento %', scale=alt.Scale(domain=[0, 120])),
                tooltip=['mo_name', 'fecha', 'rendimiento', 'kg_mp']
            ).properties(width=700, height=300)
            
            st.altair_chart(line_rend, use_container_width=True)
        
        # === NUEVO: Gráfico de evolución de rendimiento por tipo de fruta ===
        lotes = st.session_state.rend_lotes
        if lotes:
            df_lotes = pd.DataFrame(lotes)
            
            if 'tipo_fruta' in df_lotes.columns and 'fecha_recepcion' in df_lotes.columns:
                st.markdown("---")
                st.markdown("### 📈 Evolución del Rendimiento por Tipo de Fruta")
                st.caption("Rendimiento promedio ponderado por volumen, agrupado por día y tipo de fruta")
                
                # Preparar datos: agrupar por fecha y tipo de fruta
                df_tiempo = df_lotes.copy()
                df_tiempo['fecha'] = pd.to_datetime(df_tiempo['fecha_recepcion']).dt.date
                
                # Calcular rendimiento ponderado por día y fruta
                rendimiento_diario = df_tiempo.groupby(['fecha', 'tipo_fruta']).apply(
                    lambda x: pd.Series({
                        'rendimiento': (x['rendimiento'] * x['kg_consumidos']).sum() / x['kg_consumidos'].sum() if x['kg_consumidos'].sum() > 0 else 0,
                        'kg_total': x['kg_consumidos'].sum(),
                        'num_lotes': len(x)
                    })
                ).reset_index()
                
                # Colores personalizados para cada fruta
                colores_fruta = {
                    'Arándano': '#4C78A8',
                    'Frambuesa': '#F58518', 
                    'Frutilla': '#E45756',
                    'Mora': '#72B7B2',
                    'Cereza': '#54A24B',
                    'Kiwi': '#EECA3B',
                    'Uva': '#B279A2',
                    'Manzana': '#FF9DA6',
                    'Pera': '#9D755D'
                }
                
                # Crear lista de frutas y colores
                frutas_disponibles = rendimiento_diario['tipo_fruta'].unique().tolist()
                color_domain = frutas_disponibles
                color_range = [colores_fruta.get(f, '#999999') for f in frutas_disponibles]
                
                # Gráfico de líneas
                line_fruta = alt.Chart(rendimiento_diario).mark_line(point=True, strokeWidth=2).encode(
                    x=alt.X('fecha:T', title='Fecha'),
                    y=alt.Y('rendimiento:Q', title='Rendimiento %', scale=alt.Scale(domain=[50, 110])),
                    color=alt.Color('tipo_fruta:N', 
                                   scale=alt.Scale(domain=color_domain, range=color_range),
                                   legend=alt.Legend(title='Tipo de Fruta')),
                    strokeDash=alt.StrokeDash('tipo_fruta:N'),
                    tooltip=[
                        alt.Tooltip('fecha:T', title='Fecha'),
                        alt.Tooltip('tipo_fruta:N', title='Fruta'),
                        alt.Tooltip('rendimiento:Q', title='Rendimiento %', format='.1f'),
                        alt.Tooltip('kg_total:Q', title='Kg Total', format=',.0f'),
                        alt.Tooltip('num_lotes:Q', title='Lotes')
                    ]
                ).properties(height=400)
                
                # Líneas de referencia
                rule_90 = alt.Chart(pd.DataFrame({'y': [90]})).mark_rule(color='red', strokeDash=[5,5], strokeWidth=1).encode(y='y:Q')
                rule_95 = alt.Chart(pd.DataFrame({'y': [95]})).mark_rule(color='orange', strokeDash=[5,5], strokeWidth=1).encode(y='y:Q')
                
                st.altair_chart(line_fruta + rule_90 + rule_95, use_container_width=True)
                st.caption("🔴 Línea roja: 90% (Crítico) | 🟡 Línea naranja: 95% (Atención)")
                
                # Tabla resumen por fruta
                st.markdown("#### Resumen por Tipo de Fruta (Período seleccionado)")
                resumen_fruta = df_lotes.groupby('tipo_fruta').agg({
                    'kg_consumidos': 'sum',
                    'kg_producidos': 'sum',
                    'rendimiento': 'mean'
                }).reset_index()
                resumen_fruta['rendimiento_ponderado'] = (
                    df_lotes.groupby('tipo_fruta').apply(
                        lambda x: (x['rendimiento'] * x['kg_consumidos']).sum() / x['kg_consumidos'].sum() if x['kg_consumidos'].sum() > 0 else 0
                    ).values
                )
                resumen_fruta.columns = ['Tipo Fruta', 'Kg MP', 'Kg PT', 'Rend. Simple %', 'Rend. Ponderado %']
                resumen_fruta['Kg MP'] = resumen_fruta['Kg MP'].apply(lambda x: fmt_numero(x, 0))
                resumen_fruta['Kg PT'] = resumen_fruta['Kg PT'].apply(lambda x: fmt_numero(x, 0))
                resumen_fruta['Rend. Simple %'] = resumen_fruta['Rend. Simple %'].apply(lambda x: fmt_porcentaje(x))
                resumen_fruta['Rend. Ponderado %'] = resumen_fruta['Rend. Ponderado %'].apply(lambda x: fmt_porcentaje(x))
                st.dataframe(resumen_fruta, use_container_width=True, hide_index=True)
    
    # --- TAB 6: Trazabilidad Inversa ---
    with tab6:
        st.subheader("🔍 Trazabilidad Inversa: PT → MP")
        st.markdown("Ingresa un lote de Producto Terminado para encontrar los lotes de Materia Prima originales.")
        
        lote_pt_input = st.text_input("Número de Lote PT", placeholder="Ej: 0000304776")
        
        if st.button("Buscar Origen", type="primary"):
            if lote_pt_input:
                with st.spinner("Buscando trazabilidad..."):
                    try:
                        params = {"username": username, "password": password}
                        resp = requests.get(
                            f"{API_URL}/api/v1/rendimiento/trazabilidad-inversa/{lote_pt_input}",
                            params=params,
                            timeout=60
                        )
                        if resp.status_code == 200:
                            traz = resp.json()
                            
                            if traz.get('error'):
                                st.warning(traz['error'])
                            else:
                                st.success(f"✅ Lote encontrado: **{traz['lote_pt']}**")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**Producto PT:** {traz.get('producto_pt', 'N/A')}")
                                    st.markdown(f"**Fecha Creación:** {traz.get('fecha_creacion', 'N/A')}")
                                with col2:
                                    if traz.get('mo'):
                                        st.markdown(f"**MO:** {traz['mo'].get('name', 'N/A')}")
                                        st.markdown(f"**Fecha MO:** {traz['mo'].get('fecha', 'N/A')}")
                                
                                st.markdown("---")
                                st.markdown("### 📦 Lotes MP Originales")
                                
                                lotes_mp = traz.get('lotes_mp', [])
                                if lotes_mp:
                                    df_mp = pd.DataFrame(lotes_mp)
                                    df_mp['kg'] = df_mp['kg'].apply(lambda x: fmt_numero(x, 2))
                                    st.dataframe(df_mp[['lot_name', 'product_name', 'kg', 'proveedor', 'fecha_recepcion']], 
                                               use_container_width=True, hide_index=True)
                                    st.metric("Total Kg MP", fmt_numero(traz.get('total_kg_mp', 0), 2))
                                else:
                                    st.info("No se encontraron lotes MP asociados")
                        else:
                            st.error(f"Error: {resp.status_code}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Ingresa un número de lote")

else:
    st.info("👈 Selecciona un rango de fechas y haz clic en **Consultar Rendimiento** para ver los datos.")
    
    with st.expander("ℹ️ ¿Cómo funciona este dashboard?"):
        st.markdown("""
        ### Flujo de Trazabilidad
        
        ```
        📥 Recepción → 🧺 Lote MP → ⚙️ MO (Proceso) → 📦 Lote PT
        ```
        
        ### Métricas Clave
        
        | Métrica | Descripción |
        |---------|-------------|
        | **Rendimiento %** | Kg PT / Kg MP × 100 (ponderado por volumen) |
        | **Merma** | Kg MP - Kg PT |
        | **Kg/HH** | Productividad: Kg PT / Horas Hombre |
        | **Kg/Hora** | Velocidad: Kg PT / Horas de proceso |
        | **Kg/Operario** | Eficiencia: Kg PT / Dotación promedio |
        
        ### Alertas de Rendimiento
        
        - 🟢 **≥ 95%** - Excelente
        - 🟡 **90-95%** - Atención
        - 🔴 **< 90%** - Crítico
        
        ### Nuevas Funcionalidades
        
        - 📦 **Detalle PT por Lote**: Ver qué productos salieron de cada lote MP
        - 🏠 **Productividad por Sala**: Comparar eficiencia entre salas
        - 🏆 **Ranking Proveedores**: Top 5 y Bottom 5
        - 🔍 **Trazabilidad Inversa**: De PT a MP original
        """)

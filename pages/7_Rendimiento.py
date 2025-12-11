"""
Rendimiento Productivo: Dashboard de análisis de eficiencia por lote de fruta.
Trazabilidad: Lote MP → MO → Lote PT
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


def fmt_dinero(valor, decimales=0):
    """Formatea valor monetario con símbolo $"""
    return f"${fmt_numero(valor, decimales)}"


def fmt_porcentaje(valor, decimales=1):
    """Formatea porcentaje"""
    return f"{fmt_numero(valor, decimales)}%"


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
            else:
                st.error(f"Error overview: {resp_overview.status_code}")
                st.session_state.rend_data = None
            
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
                
        except requests.exceptions.ConnectionError:
            st.error("No se puede conectar al servidor API. Verificar que el backend esté corriendo.")
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
        delta_color = "normal" if rend >= 85 else "inverse"
        st.metric("Rendimiento Prom.", fmt_porcentaje(rend), delta=f"{rend-85:.1f}% vs 85%")
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
    tab1, tab2, tab3, tab4 = st.tabs(["🧺 Por Lote", "🏭 Por Proveedor", "⚙️ Por MO", "📊 Gráficos"])
    
    # --- TAB 1: Por Lote ---
    with tab1:
        st.subheader("Rendimiento por Lote de MP")
        lotes = st.session_state.rend_lotes
        
        if lotes:
            df_lotes = pd.DataFrame(lotes)
            
            # === FILTROS ===
            st.markdown("**Filtrar por:**")
            filter_cols = st.columns(3)
            
            with filter_cols[0]:
                # Filtro por proveedor
                proveedores_unicos = sorted(df_lotes['proveedor'].unique().tolist())
                prov_filtro = st.multiselect("Proveedor", proveedores_unicos)
            
            with filter_cols[1]:
                # Filtro por tipo de fruta
                if 'tipo_fruta' in df_lotes.columns:
                    frutas_unicas = sorted(df_lotes['tipo_fruta'].unique().tolist())
                    fruta_filtro = st.multiselect("Tipo Fruta", frutas_unicas)
                else:
                    fruta_filtro = []
            
            with filter_cols[2]:
                # Filtro por manejo
                if 'manejo' in df_lotes.columns:
                    manejos_unicos = sorted(df_lotes['manejo'].unique().tolist())
                    manejo_filtro = st.multiselect("Manejo", manejos_unicos)
                else:
                    manejo_filtro = []
            
            # Aplicar filtros
            df_filtered = df_lotes.copy()
            if prov_filtro:
                df_filtered = df_filtered[df_filtered['proveedor'].isin(prov_filtro)]
            if fruta_filtro:
                df_filtered = df_filtered[df_filtered['tipo_fruta'].isin(fruta_filtro)]
            if manejo_filtro:
                df_filtered = df_filtered[df_filtered['manejo'].isin(manejo_filtro)]
            
            # Mostrar métricas del filtro
            if prov_filtro or fruta_filtro or manejo_filtro:
                st.caption(f"Mostrando {len(df_filtered)} de {len(df_lotes)} lotes")
            
            # Preparar columnas para mostrar
            display_cols = ['lot_name', 'product_name', 'tipo_fruta', 'manejo', 'proveedor', 
                           'orden_compra', 'fecha_recepcion', 'kg_consumidos', 'kg_producidos', 
                           'rendimiento', 'merma', 'num_mos']
            
            # Filtrar solo columnas que existen
            available_cols = [c for c in display_cols if c in df_filtered.columns]
            df_display = df_filtered[available_cols].copy()
            
            # Renombrar columnas
            col_names = {
                'lot_name': 'Lote', 'product_name': 'Producto', 
                'tipo_fruta': 'Fruta', 'manejo': 'Manejo',
                'proveedor': 'Proveedor', 'orden_compra': 'OC',
                'fecha_recepcion': 'Fecha Recep.', 'kg_consumidos': 'Kg MP',
                'kg_producidos': 'Kg PT', 'rendimiento': 'Rend %',
                'merma': 'Merma Kg', 'num_mos': 'MOs'
            }
            df_display = df_display.rename(columns=col_names)
            
            # Formatear números
            if 'Kg MP' in df_display.columns:
                df_display['Kg MP'] = df_display['Kg MP'].apply(lambda x: fmt_numero(x, 0))
            if 'Kg PT' in df_display.columns:
                df_display['Kg PT'] = df_display['Kg PT'].apply(lambda x: fmt_numero(x, 0))
            if 'Rend %' in df_display.columns:
                df_display['Rend %'] = df_display['Rend %'].apply(lambda x: fmt_porcentaje(x))
            if 'Merma Kg' in df_display.columns:
                df_display['Merma Kg'] = df_display['Merma Kg'].apply(lambda x: fmt_numero(x, 0))
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Descargar
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar CSV", csv, "rendimiento_lotes.csv", "text/csv")
        else:
            st.info("Sin datos de lotes. Haz clic en 'Consultar Rendimiento'.")
    
    # --- TAB 2: Por Proveedor ---
    with tab2:
        st.subheader("Rendimiento por Proveedor")
        proveedores = st.session_state.rend_proveedores
        
        if proveedores:
            df_prov = pd.DataFrame(proveedores)
            
            # Mostrar tabla
            df_prov_display = df_prov[['proveedor', 'kg_consumidos', 'kg_producidos', 'rendimiento', 'merma', 'lotes']].copy()
            df_prov_display.columns = ['Proveedor', 'Kg Consumidos', 'Kg Producidos', 'Rendimiento %', 'Merma Kg', 'Lotes']
            
            df_prov_display['Kg Consumidos'] = df_prov_display['Kg Consumidos'].apply(lambda x: fmt_numero(x, 0))
            df_prov_display['Kg Producidos'] = df_prov_display['Kg Producidos'].apply(lambda x: fmt_numero(x, 0))
            df_prov_display['Rendimiento %'] = df_prov_display['Rendimiento %'].apply(lambda x: fmt_porcentaje(x))
            df_prov_display['Merma Kg'] = df_prov_display['Merma Kg'].apply(lambda x: fmt_numero(x, 0))
            
            st.dataframe(df_prov_display, use_container_width=True, hide_index=True)
            
            # Gráfico de barras
            chart_prov = alt.Chart(df_prov).mark_bar().encode(
                x=alt.X('proveedor:N', sort='-y', title='Proveedor', axis=alt.Axis(labelAngle=-45, labelLimit=200)),
                y=alt.Y('rendimiento:Q', title='Rendimiento %'),
                color=alt.condition(
                    alt.datum.rendimiento >= 85,
                    alt.value('#28a745'),
                    alt.value('#dc3545')
                ),
                tooltip=['proveedor', 'rendimiento', 'kg_consumidos', 'kg_producidos']
            ).properties(width=700, height=400, title='Rendimiento por Proveedor')
            
            st.altair_chart(chart_prov, use_container_width=True)
        else:
            st.info("Sin datos de proveedores.")
    
    # --- TAB 3: Por MO ---
    with tab3:
        st.subheader("Rendimiento por Orden de Fabricación")
        mos = st.session_state.rend_mos
        
        if mos:
            df_mos = pd.DataFrame(mos)
            
            df_mos_display = df_mos[['mo_name', 'kg_mp', 'kg_pt', 'rendimiento', 'merma', 'duracion_horas', 'dotacion', 'fecha']].copy()
            df_mos_display.columns = ['MO', 'Kg MP', 'Kg PT', 'Rend %', 'Merma Kg', 'Duración (h)', 'Dotación', 'Fecha']
            
            df_mos_display['Kg MP'] = df_mos_display['Kg MP'].apply(lambda x: fmt_numero(x, 0))
            df_mos_display['Kg PT'] = df_mos_display['Kg PT'].apply(lambda x: fmt_numero(x, 0))
            df_mos_display['Rend %'] = df_mos_display['Rend %'].apply(lambda x: fmt_porcentaje(x))
            df_mos_display['Merma Kg'] = df_mos_display['Merma Kg'].apply(lambda x: fmt_numero(x, 0))
            
            st.dataframe(df_mos_display, use_container_width=True, hide_index=True)
            
            # Estadísticas
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("Duración Promedio", f"{df_mos['duracion_horas'].mean():.1f} h")
            with col_stat2:
                st.metric("Dotación Promedio", f"{df_mos['dotacion'].mean():.1f}")
            with col_stat3:
                st.metric("Rendimiento Mín/Máx", f"{df_mos['rendimiento'].min():.1f}% / {df_mos['rendimiento'].max():.1f}%")
        else:
            st.info("Sin datos de MOs.")
    
    # --- TAB 4: Gráficos ---
    with tab4:
        st.subheader("Análisis Gráfico")
        
        lotes = st.session_state.rend_lotes
        if lotes:
            df_lotes = pd.DataFrame(lotes)
            
            # Distribución de rendimiento
            st.markdown("### Distribución de Rendimiento por Lote")
            hist_rend = alt.Chart(df_lotes).mark_bar().encode(
                x=alt.X('rendimiento:Q', bin=alt.Bin(maxbins=20), title='Rendimiento %'),
                y=alt.Y('count()', title='Cantidad de Lotes')
            ).properties(width=700, height=300)
            
            # Línea de referencia en 85%
            rule = alt.Chart(pd.DataFrame({'x': [85]})).mark_rule(color='red', strokeDash=[5,5]).encode(x='x:Q')
            
            st.altair_chart(hist_rend + rule, use_container_width=True)
            
            # Rendimiento vs Kg consumidos
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
            
            # Rendimiento por fecha
            st.markdown("### Rendimiento por Fecha")
            line_rend = alt.Chart(df_mos).mark_line(point=True).encode(
                x=alt.X('fecha:T', title='Fecha'),
                y=alt.Y('rendimiento:Q', title='Rendimiento %', scale=alt.Scale(domain=[0, 120])),
                tooltip=['mo_name', 'fecha', 'rendimiento', 'kg_mp']
            ).properties(width=700, height=300)
            
            st.altair_chart(line_rend, use_container_width=True)

else:
    st.info("👈 Selecciona un rango de fechas y haz clic en **Consultar Rendimiento** para ver los datos.")
    
    # Mostrar información de uso
    with st.expander("ℹ️ ¿Cómo funciona este dashboard?"):
        st.markdown("""
        ### Flujo de Trazabilidad
        
        ```
        📥 Recepción → 🧺 Lote MP → ⚙️ MO (Proceso) → 📦 Lote PT
        ```
        
        ### Métricas Clave
        
        | Métrica | Descripción |
        |---------|-------------|
        | **Rendimiento %** | Kg PT / Kg MP consumidos × 100 |
        | **Merma** | Kg MP - Kg PT |
        | **Kg/HH** | Productividad: Kg PT / Horas Hombre |
        
        ### Filtros
        
        - **Por Lote**: Análisis granular de cada lote de fruta
        - **Por Proveedor**: Comparación de rendimiento entre proveedores
        - **Por MO**: Detalle de cada orden de fabricación
        
        ### Productos Incluidos
        
        Solo se analizan productos de **fruta**: Arándano, Frambuesa, Frutilla, Mora, Cereza, Grosella.
        """)

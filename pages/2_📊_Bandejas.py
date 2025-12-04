"""
Dashboard de Bandejas - Control de recepción y despacho
Migrado y adaptado del dashboard original
"""
import streamlit as st
import pandas as pd
import altair as alt
import httpx
import os
from datetime import datetime

# Importar utilidades compartidas
import sys
sys.path.insert(0, str(__file__).replace('pages/2_📊_Bandejas.py', ''))

from shared.auth import proteger_pagina, tiene_acceso_dashboard, get_credenciales
from shared.constants import MESES, COLORES

# Configuración de página
st.set_page_config(
    page_title="Bandejas - Rio Futuro",
    page_icon="📊",
    layout="wide"
)

# Verificar autenticación
if not proteger_pagina():
    st.stop()

if not tiene_acceso_dashboard("bandejas"):
    st.error("No tienes permisos para ver este dashboard.")
    st.stop()

# Header
st.title("📊 Recepción Bandejas Río Futuro Procesos")
st.markdown("---")

# Obtener credenciales
username, password = get_credenciales()
api_url = os.getenv("API_URL", "http://127.0.0.1:8000")


@st.cache_data(ttl=300)
def cargar_movimientos_entrada(user: str, pwd: str):
    """Carga movimientos de entrada desde el API"""
    try:
        response = httpx.get(
            f"{api_url}/api/v1/bandejas/movimientos-entrada",
            params={"username": user, "password": pwd},
            timeout=60.0
        )
        if response.status_code == 200:
            data = response.json().get('data', [])
            return pd.DataFrame(data) if data else pd.DataFrame()
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar movimientos de entrada: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def cargar_movimientos_salida(user: str, pwd: str):
    """Carga movimientos de salida desde el API"""
    try:
        response = httpx.get(
            f"{api_url}/api/v1/bandejas/movimientos-salida",
            params={"username": user, "password": pwd},
            timeout=60.0
        )
        if response.status_code == 200:
            data = response.json().get('data', [])
            return pd.DataFrame(data) if data else pd.DataFrame()
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar movimientos de salida: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def cargar_stock(user: str, pwd: str):
    """Carga stock de bandejas desde el API"""
    try:
        response = httpx.get(
            f"{api_url}/api/v1/bandejas/stock",
            params={"username": user, "password": pwd},
            timeout=30.0
        )
        if response.status_code == 200:
            data = response.json().get('data', [])
            return pd.DataFrame(data) if data else pd.DataFrame()
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar stock: {e}")
        return pd.DataFrame()


# Cargar datos
with st.spinner("Cargando datos de Odoo..."):
    df_in = cargar_movimientos_entrada(username, password)
    df_out = cargar_movimientos_salida(username, password)
    df_stock = cargar_stock(username, password)

if not df_in.empty or not df_out.empty:
    st.success("✅ Datos cargados correctamente.")
    
    # Convertir fechas
    if not df_in.empty and 'date_order' in df_in.columns:
        df_in['date_order'] = pd.to_datetime(df_in['date_order'])
    if not df_out.empty and 'date' in df_out.columns:
        df_out['date'] = pd.to_datetime(df_out['date'])
    
    # Determinar rango de años para filtros
    dates = pd.Series(dtype='datetime64[ns]')
    if not df_in.empty and 'date_order' in df_in.columns:
        dates = pd.concat([dates, df_in['date_order']])
    if not df_out.empty and 'date' in df_out.columns:
        dates = pd.concat([dates, df_out['date']])
    
    if not dates.empty:
        data_min_year = int(dates.dt.year.min())
        data_max_year = int(dates.dt.year.max())
        current_year = datetime.now().year
        max_year = max(data_max_year, current_year, 2026)
        years = ['Todos'] + list(range(data_min_year, max_year + 1))
    else:
        years = ['Todos', 2025]
    
    # Filtros
    with st.expander("📅 Filtros de Fecha", expanded=True):
        filter_type = st.radio("Tipo de Filtro", ["Por Mes/Año", "Por Temporada"], horizontal=True)
        
        selected_year = 'Todos'
        selected_month = None
        selected_season = None
        
        if filter_type == "Por Mes/Año":
            col1, col2 = st.columns(2)
            with col1:
                selected_year = st.selectbox("Año", years, index=0)
            with col2:
                month_options = ['Todos'] + list(MESES.values())
                selected_month_name = st.selectbox("Mes", month_options, index=0)
                if selected_month_name != 'Todos':
                    selected_month = [k for k, v in MESES.items() if v == selected_month_name][0]
        else:
            # Temporadas
            season_options = []
            for y in range(2024, max_year + 1):
                season_options.append(f"Temporada {str(y)[-2:]}-{str(y+1)[-2:]}")
            
            today = datetime.now()
            current_season_year = today.year if today.month >= 11 else today.year - 1
            current_season = f"Temporada {str(current_season_year)[-2:]}-{str(current_season_year+1)[-2:]}"
            default_idx = season_options.index(current_season) if current_season in season_options else len(season_options)-1
            
            selected_season = st.selectbox("Temporada", season_options, index=default_idx)
    
    # Aplicar filtros a los datos
    df_in_filtered = df_in.copy() if not df_in.empty else pd.DataFrame()
    df_out_filtered = df_out.copy() if not df_out.empty else pd.DataFrame()
    
    if filter_type == "Por Mes/Año":
        if selected_year != 'Todos' and not df_in_filtered.empty:
            df_in_filtered = df_in_filtered[df_in_filtered['date_order'].dt.year == selected_year]
        if selected_month and not df_in_filtered.empty:
            df_in_filtered = df_in_filtered[df_in_filtered['date_order'].dt.month == selected_month]
        
        if selected_year != 'Todos' and not df_out_filtered.empty:
            df_out_filtered = df_out_filtered[df_out_filtered['date'].dt.year == selected_year]
        if selected_month and not df_out_filtered.empty:
            df_out_filtered = df_out_filtered[df_out_filtered['date'].dt.month == selected_month]
    else:
        # Filtro por temporada
        if selected_season:
            parts = selected_season.replace("Temporada ", "").split("-")
            start_year = 2000 + int(parts[0])
            end_year = start_year + 1
            start_date = pd.Timestamp(f"{start_year}-11-01")
            end_date = pd.Timestamp(f"{end_year}-10-31")
            
            if not df_in_filtered.empty:
                df_in_filtered = df_in_filtered[
                    (df_in_filtered['date_order'] >= start_date) & 
                    (df_in_filtered['date_order'] <= end_date)
                ]
            if not df_out_filtered.empty:
                df_out_filtered = df_out_filtered[
                    (df_out_filtered['date'] >= start_date) & 
                    (df_out_filtered['date'] <= end_date)
                ]
    
    # Agrupar datos
    df_in_grouped = pd.DataFrame(columns=['partner_name', 'Recepcionadas'])
    df_out_grouped = pd.DataFrame(columns=['partner_name', 'Despachadas'])
    
    if not df_in_filtered.empty and 'qty_received' in df_in_filtered.columns:
        df_in_grouped = df_in_filtered.groupby('partner_name')['qty_received'].sum().reset_index()
        df_in_grouped.columns = ['partner_name', 'Recepcionadas']
    
    if not df_out_filtered.empty and 'qty_sent' in df_out_filtered.columns:
        df_out_done = df_out_filtered[df_out_filtered['state'] == 'done']
        if not df_out_done.empty:
            df_out_grouped = df_out_done.groupby('partner_name')['qty_sent'].sum().reset_index()
            df_out_grouped.columns = ['partner_name', 'Despachadas']
    
    # Merge
    df_merged = pd.merge(df_in_grouped, df_out_grouped, on='partner_name', how='outer').fillna(0)
    df_merged = df_merged.rename(columns={'partner_name': 'Productor'})
    df_merged['Bandejas en Productor'] = df_merged['Despachadas'] - df_merged['Recepcionadas']
    
    # Stock de bandejas
    if not df_stock.empty:
        st.markdown("---")
        st.subheader("🗃️ Gestión Bandejas - Stock Actual")
        
        # Calcular totales por tipo
        total_limpia = df_stock[df_stock['tipo'] == 'Limpia']['qty_available'].sum() if 'tipo' in df_stock.columns else 0
        total_sucia = df_stock[df_stock['tipo'] == 'Sucia']['qty_available'].sum() if 'tipo' in df_stock.columns else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Bandejas Limpias", f"{total_limpia:,.0f}".replace(",", "."))
        with col2:
            st.metric("Bandejas Sucias", f"{total_sucia:,.0f}".replace(",", "."))
        with col3:
            st.metric("Total Stock", f"{total_limpia + total_sucia:,.0f}".replace(",", "."))
        
        # Tabla de stock
        if 'display_name' in df_stock.columns:
            st.dataframe(
                df_stock[['display_name', 'default_code', 'qty_available', 'tipo']].rename(columns={
                    'display_name': 'Producto',
                    'default_code': 'Código',
                    'qty_available': 'Cantidad',
                    'tipo': 'Tipo'
                }),
                use_container_width=True,
                hide_index=True
            )
    
    # Tabla de productores
    st.markdown("---")
    st.subheader("👥 Detalle por Productor")
    
    # Filtro por productor
    with st.expander("🔍 Filtrar por Productor", expanded=False):
        all_producers = sorted(df_merged['Productor'].unique())
        selected_producers = st.multiselect("Seleccionar Productores", all_producers)
    
    df_display = df_merged.copy()
    if selected_producers:
        df_display = df_display[df_display['Productor'].isin(selected_producers)]
    
    # Calcular totales
    total_in = df_display['Recepcionadas'].sum()
    total_out = df_display['Despachadas'].sum()
    total_diff = total_out - total_in
    
    # Agregar fila de totales
    total_row = pd.DataFrame([{
        'Productor': 'TOTAL',
        'Recepcionadas': total_in,
        'Despachadas': total_out,
        'Bandejas en Productor': total_diff
    }])
    df_display = pd.concat([df_display, total_row], ignore_index=True)
    
    # Formatear números
    for col in ['Recepcionadas', 'Despachadas', 'Bandejas en Productor']:
        df_display[col] = df_display[col].apply(lambda x: f"{int(x):,}".replace(",", "."))

    # Mostrar tabla con estilo igual al dashboard original (fila TOTAL en amarillo)
    def highlight_total(row):
        if row['Productor'] == 'TOTAL':
            return ['background-color: #ffff00; color: black; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    styled_df = df_display.style.apply(highlight_total, axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Sección de Stock por Producto con tabla y gráfico
    st.markdown("---")
    st.markdown("##### Stock por Producto (Sucia vs Limpia)")

    if not df_stock.empty and 'default_code' in df_stock.columns and 'display_name' in df_stock.columns:
        # Clasificar tipo
        def classify_stock(row):
            code = str(row.get('default_code', '')).strip().upper()
            if code.endswith('L'):
                return 'Limpia'
            else:
                return 'Sucia'
        df_stock['Tipo'] = df_stock.apply(classify_stock, axis=1)
        df_stock['BaseCode'] = df_stock['default_code'].apply(lambda x: str(x).strip().upper().rstrip('L'))
        # Agrupar por BaseCode y Tipo
        df_grouped = df_stock.groupby(['BaseCode', 'Tipo'])['qty_available'].sum().unstack(fill_value=0)
        if 'Sucia' not in df_grouped.columns:
            df_grouped['Sucia'] = 0
        if 'Limpia' not in df_grouped.columns:
            df_grouped['Limpia'] = 0
        df_grouped = df_grouped.reset_index()
        # Obtener nombre
        name_map = df_stock.sort_values('Tipo', ascending=False).drop_duplicates('BaseCode')[['BaseCode', 'display_name']]
        df_gestion = pd.merge(df_grouped, name_map, on='BaseCode', how='left')
        def clean_name(name):
            name = str(name)
            name = name.replace("(copia)", "").replace("- Sucia", "").replace("Limpia", "").strip()
            return name
        df_gestion['display_name'] = df_gestion['display_name'].apply(clean_name)
        df_gestion = df_gestion.rename(columns={
            'BaseCode': 'Código',
            'display_name': 'Nombre',
            'Sucia': 'Bandejas Sucias',
            'Limpia': 'Bandejas Limpias'
        })
        # Proyectados (si existe df_out_projected)
        df_gestion['Proyectados'] = 0
        # Calcular Diferencia
        df_gestion['Diferencia'] = df_gestion['Proyectados'] - df_gestion['Bandejas Limpias']
        
        # Guardar copia para el gráfico (antes de agregar totales y formatear)
        df_gestion_chart = df_gestion.copy()
        df_gestion_chart = df_gestion_chart.melt(id_vars=['Nombre'], value_vars=['Bandejas Sucias', 'Bandejas Limpias', 'Proyectados'], var_name='Tipo', value_name='Cantidad')
        df_gestion_chart['Tipo'] = df_gestion_chart['Tipo'].replace({'Bandejas Sucias': 'Sucia', 'Bandejas Limpias': 'Limpia', 'Proyectados': 'Proyectada'})
        
        # Agregar fila de totales
        total_sucias = df_gestion['Bandejas Sucias'].sum()
        total_limpias = df_gestion['Bandejas Limpias'].sum()
        total_proyectados = df_gestion['Proyectados'].sum()
        total_diferencia = df_gestion['Diferencia'].sum()
        
        total_row_gestion = pd.DataFrame([{
            'Nombre': 'TOTAL',
            'Bandejas Sucias': total_sucias,
            'Bandejas Limpias': total_limpias,
            'Proyectados': total_proyectados,
            'Diferencia': total_diferencia
        }])
        df_gestion = pd.concat([df_gestion, total_row_gestion], ignore_index=True)
        
        # Formatear números
        for col in ['Bandejas Sucias', 'Bandejas Limpias', 'Proyectados', 'Diferencia']:
            df_gestion[col] = df_gestion[col].apply(lambda x: f"{x:,.0f}".replace(",", "."))
        
        # Estilo para resaltar fila TOTAL en amarillo
        def highlight_total_gestion(row):
            if row['Nombre'] == 'TOTAL':
                return ['background-color: #ffc107; color: black; font-weight: bold'] * len(row)
            return [''] * len(row)
        
        # Mostrar tabla de gestión con totales
        st.dataframe(
            df_gestion[['Nombre', 'Bandejas Sucias', 'Bandejas Limpias', 'Proyectados', 'Diferencia']].style.apply(highlight_total_gestion, axis=1),
            hide_index=True,
            use_container_width=True
        )
        
        # Colores iguales al dashboard original
        domain = ['Sucia', 'Limpia', 'Proyectada']
        range_ = ['#dc3545', '#28a745', '#ff7f0e']  # Rojo, Verde, Naranja
        
        # Gráfico de barras
        bars = alt.Chart(df_gestion_chart).mark_bar().encode(
            x=alt.X('Nombre:N', axis=alt.Axis(labelAngle=-45), title=None),
            y=alt.Y('Cantidad:Q', title='Cantidad'),
            color=alt.Color('Tipo:N', scale=alt.Scale(domain=domain, range=range_), legend=alt.Legend(title='Tipo de Bandeja')),
            xOffset='Tipo:N',
            tooltip=['Nombre', 'Tipo', 'Cantidad']
        )
        
        # Etiquetas de valores sobre las barras
        text = alt.Chart(df_gestion_chart).mark_text(
            align='center',
            baseline='bottom',
            dy=-5,
            fontSize=10
        ).encode(
            x=alt.X('Nombre:N', axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('Cantidad:Q'),
            xOffset='Tipo:N',
            text=alt.Text('Cantidad:Q', format=',.0f'),
            color=alt.value('white')
        )
        
        chart = (bars + text).properties(
            height=400,
            title="Detalle de Stock por Producto"
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("No se encontraron datos de bandejas para el gráfico.")

# Botón de actualizar
if st.button("🔄 Actualizar Datos"):
    st.cache_data.clear()
    st.rerun()

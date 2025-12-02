"""
Dashboard de Producción - Órdenes de fabricación y KPIs
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import httpx
import os
from datetime import datetime, timedelta

# Importar utilidades compartidas
import sys
sys.path.insert(0, str(__file__).replace('pages/1_📦_Produccion.py', ''))

from shared.auth import proteger_pagina, get_credenciales

# Configuración de página
st.set_page_config(
    page_title="Producción - Rio Futuro",
    page_icon="📦",
    layout="wide"
)

# Verificar autenticación
if not proteger_pagina():
    st.stop()

# Header
st.title("📦 Dashboard de Producción")
st.markdown("---")

# Obtener credenciales
username, password = get_credenciales()
api_url = os.getenv("API_URL", "http://127.0.0.1:8000")


@st.cache_data(ttl=300)
def cargar_ordenes(user: str, pwd: str):
    """Carga órdenes de fabricación desde el API"""
    try:
        response = httpx.get(
            f"{api_url}/api/v1/produccion/ordenes",
            params={"username": user, "password": pwd},
            timeout=30.0
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error al cargar órdenes: {e}")
        return []


@st.cache_data(ttl=300)
def cargar_kpis(user: str, pwd: str):
    """Carga KPIs de producción desde el API"""
    try:
        response = httpx.get(
            f"{api_url}/api/v1/produccion/kpis",
            params={"username": user, "password": pwd},
            timeout=30.0
        )
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        st.error(f"Error al cargar KPIs: {e}")
        return {}


# Cargar datos
with st.spinner("Cargando datos de producción..."):
    ordenes = cargar_ordenes(username, password)
    kpis = cargar_kpis(username, password)

if kpis:
    # KPIs en tarjetas
    st.subheader("📊 Indicadores Clave")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="Total Órdenes",
            value=kpis.get('total_ordenes', 0),
            delta=None
        )
    
    with col2:
        st.metric(
            label="En Progreso",
            value=kpis.get('ordenes_progress', 0),
            delta=None
        )
    
    with col3:
        st.metric(
            label="Confirmadas",
            value=kpis.get('ordenes_confirmed', 0),
            delta=None
        )
    
    with col4:
        st.metric(
            label="Completadas",
            value=kpis.get('ordenes_done', 0),
            delta=None
        )
    
    with col5:
        st.metric(
            label="Por Cerrar",
            value=kpis.get('ordenes_to_close', 0),
            delta=None
        )

st.markdown("---")

if ordenes:
    df = pd.DataFrame(ordenes)
    
    # Filtros
    with st.expander("🔍 Filtros", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            estados = ['Todos'] + list(df['state'].unique()) if 'state' in df.columns else ['Todos']
            estado_filtro = st.selectbox("Estado", estados)
        
        with col2:
            if 'product_name' in df.columns:
                productos = ['Todos'] + sorted(df['product_name'].dropna().unique().tolist())
                producto_filtro = st.selectbox("Producto", productos)
            else:
                producto_filtro = 'Todos'
    
    # Aplicar filtros
    df_filtrado = df.copy()
    if estado_filtro != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['state'] == estado_filtro]
    if producto_filtro != 'Todos' and 'product_name' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['product_name'] == producto_filtro]
    
    # Gráficos
    st.subheader("📈 Análisis Visual")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de estados
        if 'state' in df_filtrado.columns:
            estado_counts = df_filtrado['state'].value_counts().reset_index()
            estado_counts.columns = ['Estado', 'Cantidad']
            
            fig_estado = px.pie(
                estado_counts,
                values='Cantidad',
                names='Estado',
                title='Distribución por Estado',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig_estado, use_container_width=True)
    
    with col2:
        # Gráfico de productos top
        if 'product_name' in df_filtrado.columns:
            top_productos = df_filtrado['product_name'].value_counts().head(10).reset_index()
            top_productos.columns = ['Producto', 'Cantidad']
            
            fig_productos = px.bar(
                top_productos,
                x='Cantidad',
                y='Producto',
                orientation='h',
                title='Top 10 Productos',
                color='Cantidad',
                color_continuous_scale='Blues'
            )
            fig_productos.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_productos, use_container_width=True)
    
    # Tabla de datos
    st.subheader("📋 Detalle de Órdenes")
    
    # Seleccionar columnas a mostrar
    columnas_mostrar = ['name', 'product_name', 'product_qty', 'qty_produced', 'state', 'date_start']
    columnas_disponibles = [c for c in columnas_mostrar if c in df_filtrado.columns]
    
    st.dataframe(
        df_filtrado[columnas_disponibles],
        use_container_width=True,
        hide_index=True
    )
    
    # Exportar
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar CSV",
        data=csv,
        file_name=f"produccion_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

else:
    st.info("No hay órdenes de fabricación para mostrar.")

# Botón de actualizar
if st.button("🔄 Actualizar Datos"):
    st.cache_data.clear()
    st.rerun()

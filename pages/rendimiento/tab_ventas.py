"""
Tab de Análisis de Ventas de Productos Terminados (PTT/Retail)
Análisis aislado de facturas de clientes
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def render(username: str, password: str):
    """Renderiza el tab de análisis de ventas."""
    
    st.subheader("💰 Análisis de Ventas - Productos Terminados")
    st.markdown("Análisis de facturas de clientes (PTT/Retail/Subproductos).")
    
    # Filtros de fecha
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fecha_desde = st.date_input("Desde", value=datetime(2025, 11, 1), format="DD/MM/YYYY", key="ventas_desde")
    
    with col2:
        fecha_hasta = st.date_input("Hasta", value=datetime(2026, 1, 31), format="DD/MM/YYYY", key="ventas_hasta")
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        cargar_datos = st.button("🔄 Actualizar Datos", type="primary", use_container_width=True, key="ventas_cargar")
    
    if not cargar_datos and 'ventas_data' not in st.session_state:
        st.info("ℹ️ Presiona 'Actualizar Datos' para cargar la información")
        return
    
    if cargar_datos or 'ventas_data' not in st.session_state:
        with st.spinner("🔎 Cargando datos de ventas..."):
            from .shared_analisis import get_ventas_data
            st.session_state.ventas_data = get_ventas_data(
                username, password,
                fecha_desde.strftime('%Y-%m-%d'),
                fecha_hasta.strftime('%Y-%m-%d')
            )
    
    data = st.session_state.ventas_data
    
    if data.get('error'):
        st.error(f"❌ {data['error']}")
        return
    
    st.info(f"📅 Período analizado: **{data.get('fecha_desde', '')}** a **{data.get('fecha_hasta', '')}**")
    
    # Métricas principales
    st.markdown("### 📊 Resumen General")
    resumen = data.get('resumen', {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Vendido", f"{resumen.get('kg', 0):,.0f} kg")
    with col2:
        st.metric("Ingresos Totales", f"${resumen.get('monto', 0):,.0f} CLP")
    with col3:
        st.metric("Precio Promedio", f"${resumen.get('precio_promedio', 0):,.2f}/kg")
    
    # Distribución por categoría
    st.markdown("### 📦 Distribución por Categoría")
    por_categoria = data.get('por_categoria', [])
    
    if por_categoria:
        df_cat = pd.DataFrame(por_categoria)
        
        fig_cat = px.pie(df_cat, values='monto', names='categoria', title='Ventas por Categoría (PTT/Retail/Subproducto)', hole=0.4)
        st.plotly_chart(fig_cat, use_container_width=True)
        
        df_cat['%'] = df_cat['porcentaje'].apply(lambda x: f"{x:.1f}%")
        df_cat['Monto'] = df_cat['monto'].apply(lambda x: f"${x:,.0f}")
        st.dataframe(df_cat[['categoria', 'kg', 'Monto', '%']], use_container_width=True, hide_index=True)
    
    # Top clientes
    st.markdown("### 👥 Top Clientes")
    top_clientes = data.get('top_clientes', [])
    
    if top_clientes:
        df_cli = pd.DataFrame(top_clientes[:10])
        
        fig_cli = px.bar(df_cli, x='monto', y='cliente', orientation='h', title='Top 10 Clientes por Ingresos', text='monto')
        fig_cli.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_cli, use_container_width=True)
        
        df_cli['Monto'] = df_cli['monto'].apply(lambda x: f"${x:,.0f}")
        df_cli['Precio/kg'] = df_cli['precio_promedio'].apply(lambda x: f"${x:,.2f}")
        st.dataframe(df_cli[['cliente', 'pais', 'kg', 'Monto', 'Precio/kg']], use_container_width=True, hide_index=True)
    
    # Tendencia
    st.markdown("### 📈 Tendencia de Precios")
    tendencia = data.get('tendencia_precios', [])
    
    if tendencia:
        df_tend = pd.DataFrame(tendencia)
        
        fig_tend = go.Figure()
        fig_tend.add_trace(go.Scatter(x=df_tend['mes'], y=df_tend['precio_promedio'], mode='lines+markers', name='Precio Promedio', line=dict(color='#2ca02c', width=3), marker=dict(size=8)))
        fig_tend.update_layout(title='Evolución del Precio Promedio de Venta', xaxis_title='Mes', yaxis_title='Precio CLP/kg', hovermode='x unified')
        st.plotly_chart(fig_tend, use_container_width=True)
    
    # Detalle
    st.markdown("### 📋 Detalle de Facturas")
    detalle = data.get('detalle', [])
    
    if detalle:
        df_det = pd.DataFrame(detalle)
        
        col1, col2 = st.columns(2)
        with col1:
            cat_filter = st.multiselect("Filtrar por Categoría", sorted(df_det['categoria'].unique()), key="ventas_cat_filter")
        with col2:
            cli_filter = st.multiselect("Filtrar por Cliente", sorted(df_det['cliente'].unique()), key="ventas_cli_filter")
        
        df_filtrado = df_det.copy()
        if cat_filter:
            df_filtrado = df_filtrado[df_filtrado['categoria'].isin(cat_filter)]
        if cli_filter:
            df_filtrado = df_filtrado[df_filtrado['cliente'].isin(cli_filter)]
        
        df_filtrado['Monto'] = df_filtrado['monto'].apply(lambda x: f"${x:,.0f}")
        st.dataframe(df_filtrado[['fecha', 'cliente', 'producto', 'categoria', 'kg', 'Monto']], use_container_width=True, hide_index=True)
        st.caption(f"Mostrando {len(df_filtrado):,} de {len(df_det):,} líneas")

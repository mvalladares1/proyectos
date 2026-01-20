"""
Tab de Análisis de Producción y Rendimientos
Calcula rendimiento PSP → PTT usando órdenes de fabricación
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
    """Renderiza el tab de análisis de producción."""
    
    st.subheader("🏭 Análisis de Producción y Rendimientos")
    st.markdown("Análisis de órdenes de fabricación: rendimiento PSP → PTT y merma de proceso.")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fecha_desde = st.date_input("Desde", value=datetime(2025, 11, 1), format="DD/MM/YYYY", key="prod_desde")
    
    with col2:
        fecha_hasta = st.date_input("Hasta", value=datetime(2026, 1, 31), format="DD/MM/YYYY", key="prod_hasta")
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        cargar_datos = st.button("🔄 Actualizar Datos", type="primary", use_container_width=True, key="prod_cargar")
    
    if not cargar_datos and 'produccion_data' not in st.session_state:
        st.info("ℹ️ Presiona 'Actualizar Datos' para cargar la información")
        return
    
    if cargar_datos or 'produccion_data' not in st.session_state:
        with st.spinner("🔎 Cargando datos de producción..."):
            from .shared_analisis import get_produccion_data
            st.session_state.produccion_data = get_produccion_data(
                username, password,
                fecha_desde.strftime('%Y-%m-%d'),
                fecha_hasta.strftime('%Y-%m-%d')
            )
    
    data = st.session_state.produccion_data
    
    if data.get('error'):
        st.error(f"❌ {data['error']}")
        return
    
    st.info(f"📅 Período analizado: **{data.get('fecha_desde', '')}** a **{data.get('fecha_hasta', '')}**")
    
    # Resumen
    st.markdown("### 📊 Resumen General")
    resumen = data.get('resumen', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("MP Consumida", f"{resumen.get('kg_consumido', 0):,.0f} kg", help="Materia prima consumida")
    
    with col2:
        st.metric("PT Producido", f"{resumen.get('kg_producido', 0):,.0f} kg", help="Producto terminado obtenido")
    
    with col3:
        rend_pct = resumen.get('rendimiento_pct', 0)
        st.metric("Rendimiento", f"{rend_pct:.1f}%", help="% de aprovechamiento (PT/MP)")
    
    with col4:
        merma_pct = resumen.get('merma_pct', 0)
        st.metric("Merma Proceso", f"{merma_pct:.1f}%", delta=f"-{resumen.get('merma_kg', 0):,.0f} kg", delta_color="inverse", help="Pérdida en proceso")
    
    st.caption(f"📦 Total de órdenes procesadas: **{resumen.get('ordenes_total', 0):,}**")
    
    # Rendimientos por tipo
    st.markdown("### 🍓 Rendimientos por Tipo de Fruta")
    
    rendimientos = data.get('rendimientos_por_tipo', [])
    
    if rendimientos:
        df_rend = pd.DataFrame(rendimientos)
        
        # Gráfico de barras
        fig_rend = go.Figure()
        
        fig_rend.add_trace(go.Bar(
            name='Consumo MP',
            x=df_rend['tipo_fruta'],
            y=df_rend['kg_consumido'],
            marker_color='#ff7f0e'
        ))
        
        fig_rend.add_trace(go.Bar(
            name='Producción PT',
            x=df_rend['tipo_fruta'],
            y=df_rend['kg_producido'],
            marker_color='#2ca02c'
        ))
        
        fig_rend.update_layout(
            title='Consumo MP vs Producción PT por Tipo de Fruta',
            xaxis_title='Tipo de Fruta',
            yaxis_title='Kilogramos',
            barmode='group',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_rend, use_container_width=True)
        
        # Tabla de rendimientos
        st.markdown("#### Detalle de Rendimientos")
        
        df_rend['Consumo'] = df_rend['kg_consumido'].apply(lambda x: f"{x:,.0f} kg")
        df_rend['Producido'] = df_rend['kg_producido'].apply(lambda x: f"{x:,.0f} kg")
        df_rend['Rend.'] = df_rend['rendimiento_pct'].apply(lambda x: f"{x:.1f}%")
        df_rend['Merma'] = df_rend['merma_pct'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(
            df_rend[['tipo_fruta', 'Consumo', 'Producido', 'Rend.', 'Merma']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No hay datos de rendimientos")
    
    # Detalle de órdenes
    st.markdown("### 📋 Detalle de Órdenes de Producción")
    
    ordenes = data.get('detalle_ordenes', [])
    
    if ordenes:
        df_ord = pd.DataFrame(ordenes)
        
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            tipo_filter = st.multiselect("Filtrar por Tipo de Fruta", sorted(df_ord['tipo_fruta'].unique()), key="prod_tipo_filter")
        
        with col2:
            estado_filter = st.multiselect("Filtrar por Estado", sorted(df_ord['estado'].unique()), key="prod_estado_filter")
        
        df_filtrado = df_ord.copy()
        if tipo_filter:
            df_filtrado = df_filtrado[df_filtrado['tipo_fruta'].isin(tipo_filter)]
        if estado_filter:
            df_filtrado = df_filtrado[df_filtrado['estado'].isin(estado_filter)]
        
        # Formatear
        df_filtrado['Consumo'] = df_filtrado['kg_consumido'].apply(lambda x: f"{x:,.1f}")
        df_filtrado['Producido'] = df_filtrado['kg_producido'].apply(lambda x: f"{x:,.1f}")
        df_filtrado['Rend.'] = df_filtrado['rendimiento_pct'].apply(lambda x: f"{x:.1f}%")
        df_filtrado['Merma'] = df_filtrado['merma_pct'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(
            df_filtrado[['fecha', 'orden', 'tipo_fruta', 'estado', 'Consumo', 'Producido', 'Rend.', 'Merma']],
            use_container_width=True,
            hide_index=True
        )
        
        st.caption(f"Mostrando {len(df_filtrado):,} de {len(df_ord):,} órdenes")
        
        # Estadísticas
        if len(df_filtrado) > 0:
            st.markdown("#### Estadísticas del Filtro")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Órdenes", len(df_filtrado))
            with col2:
                rend_prom = df_ord['rendimiento_pct'].mean() if len(df_filtrado) > 0 else 0
                st.metric("Rendimiento Promedio", f"{rend_prom:.1f}%")
            with col3:
                merma_prom = df_ord['merma_pct'].mean() if len(df_filtrado) > 0 else 0
                st.metric("Merma Promedio", f"{merma_prom:.1f}%")
    else:
        st.warning("No hay órdenes de producción en el período")

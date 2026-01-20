"""
Tab de Análisis de Compras de Materia Prima (MP/PSP)
Análisis aislado de facturas de proveedores
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
    """Renderiza el tab de análisis de compras."""
    
    st.subheader("📦 Análisis de Compras - Materia Prima")
    st.markdown("Análisis de facturas de proveedores (PSP/MP). **Solo productos clasificados.**")
    
    # Filtros de fecha
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fecha_desde = st.date_input(
            "Desde",
            value=datetime(2025, 11, 1),
            format="DD/MM/YYYY"
        )
    
    with col2:
        fecha_hasta = st.date_input(
            "Hasta",
            value=datetime(2026, 1, 31),
            format="DD/MM/YYYY"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        cargar_datos = st.button("🔄 Actualizar Datos", type="primary", use_container_width=True)
    
    # Solo cargar datos cuando se presiona el botón
    if not cargar_datos and 'compras_data' not in st.session_state:
        st.info("ℹ️ Presiona 'Actualizar Datos' para cargar la información")
        return
    
    # Obtener datos
    if cargar_datos or 'compras_data' not in st.session_state:
        with st.spinner("🔎 Cargando datos de compras..."):
            from .shared_analisis import get_compras_data
            st.session_state.compras_data = get_compras_data(
                username, password,
                fecha_desde.strftime('%Y-%m-%d'),
                fecha_hasta.strftime('%Y-%m-%d')
            )
    
    data = st.session_state.compras_data
    
    if data.get('error'):
        st.error(f"❌ {data['error']}")
        return
    
    # Mostrar período
    st.info(f"📅 Período analizado: **{data.get('fecha_desde', '')}** a **{data.get('fecha_hasta', '')}**")
    
    # ============================================================================
    # MÉTRICAS PRINCIPALES
    # ============================================================================
    st.markdown("### 📊 Resumen General")
    
    resumen = data.get('resumen', {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Comprado",
            f"{resumen.get('kg', 0):,.0f} kg",
            help="Kilogramos totales de materia prima comprada"
        )
    
    with col2:
        st.metric(
            "Inversión Total",
            f"${resumen.get('monto', 0):,.0f} CLP",
            help="Monto total gastado en compras"
        )
    
    with col3:
        st.metric(
            "Precio Promedio",
            f"${resumen.get('precio_promedio', 0):,.2f}/kg",
            help="Precio promedio ponderado de compra"
        )
    
    # ============================================================================
    # DISTRIBUCIÓN POR TIPO DE FRUTA
    # ============================================================================
    st.markdown("### 🍓 Distribución por Tipo de Fruta")
    
    por_tipo = data.get('por_tipo', [])
    
    if por_tipo:
        df_tipo = pd.DataFrame(por_tipo)
        
        # Gráfico de torta por monto
        fig_pie = px.pie(
            df_tipo,
            values='monto',
            names='tipo_fruta',
            title='Distribución de Compras por Tipo de Fruta (CLP)',
            hole=0.4
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # Tabla detallada
        st.markdown("#### Detalle por Tipo y Manejo")
        
        # Formatear tabla
        df_tipo['Monto CLP'] = df_tipo['monto'].apply(lambda x: f"${x:,.0f}")
        df_tipo['Kg'] = df_tipo['kg'].apply(lambda x: f"{x:,.0f}")
        df_tipo['Precio/kg'] = df_tipo['precio_promedio'].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(
            df_tipo[['tipo_fruta', 'manejo', 'Kg', 'Monto CLP', 'Precio/kg']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No hay datos de compras por tipo de fruta")
    
    # ============================================================================
    # TOP PROVEEDORES
    # ============================================================================
    st.markdown("### 👥 Top Proveedores")
    
    top_proveedores = data.get('top_proveedores', [])
    
    if top_proveedores:
        df_prov = pd.DataFrame(top_proveedores[:10])  # Top 10
        
        # Gráfico de barras
        fig_prov = px.bar(
            df_prov,
            x='monto',
            y='proveedor',
            orientation='h',
            title='Top 10 Proveedores por Monto',
            labels={'monto': 'Monto CLP', 'proveedor': 'Proveedor'},
            text='monto'
        )
        fig_prov.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_prov, use_container_width=True)
        
        # Tabla
        df_prov['Monto CLP'] = df_prov['monto'].apply(lambda x: f"${x:,.0f}")
        df_prov['Kg'] = df_prov['kg'].apply(lambda x: f"{x:,.0f}")
        df_prov['Precio/kg'] = df_prov['precio_promedio'].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(
            df_prov[['proveedor', 'Kg', 'Monto CLP', 'Precio/kg']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No hay datos de proveedores")
    
    # ============================================================================
    # TENDENCIA DE PRECIOS
    # ============================================================================
    st.markdown("### 📈 Tendencia de Precios")
    
    tendencia = data.get('tendencia_precios', [])
    
    if tendencia:
        df_tend = pd.DataFrame(tendencia)
        
        # Gráfico de línea
        fig_tend = go.Figure()
        
        fig_tend.add_trace(go.Scatter(
            x=df_tend['mes'],
            y=df_tend['precio_promedio'],
            mode='lines+markers',
            name='Precio Promedio',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=8)
        ))
        
        fig_tend.update_layout(
            title='Evolución del Precio Promedio de Compra',
            xaxis_title='Mes',
            yaxis_title='Precio CLP/kg',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_tend, use_container_width=True)
        
        # Tabla
        df_tend['Monto CLP'] = df_tend['monto'].apply(lambda x: f"${x:,.0f}")
        df_tend['Kg'] = df_tend['kg'].apply(lambda x: f"{x:,.0f}")
        df_tend['Precio/kg'] = df_tend['precio_promedio'].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(
            df_tend[['mes', 'Kg', 'Monto CLP', 'Precio/kg']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No hay datos de tendencia")
    
    # ============================================================================
    # DETALLE DE LÍNEAS
    # ============================================================================
    st.markdown("### 📋 Detalle de Facturas")
    
    detalle = data.get('detalle', [])
    
    if detalle:
        df_det = pd.DataFrame(detalle)
        
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            tipo_filter = st.multiselect(
                "Filtrar por Tipo de Fruta",
                options=sorted(df_det['tipo_fruta'].unique()),
                default=None
            )
        
        with col2:
            prov_filter = st.multiselect(
                "Filtrar por Proveedor",
                options=sorted(df_det['proveedor'].unique()),
                default=None
            )
        
        # Aplicar filtros
        df_filtrado = df_det.copy()
        if tipo_filter:
            df_filtrado = df_filtrado[df_filtrado['tipo_fruta'].isin(tipo_filter)]
        if prov_filter:
            df_filtrado = df_filtrado[df_filtrado['proveedor'].isin(prov_filter)]
        
        # Formatear
        df_filtrado['Monto CLP'] = df_filtrado['monto'].apply(lambda x: f"${x:,.0f}")
        df_filtrado['Precio/kg'] = df_filtrado['precio_kg'].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(
            df_filtrado[['fecha', 'proveedor', 'producto', 'tipo_fruta', 'manejo', 'kg', 'Monto CLP', 'Precio/kg']],
            use_container_width=True,
            hide_index=True
        )
        
        st.caption(f"Mostrando {len(df_filtrado):,} de {len(df_det):,} líneas")
    else:
        st.warning("No hay detalle de facturas")

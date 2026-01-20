"""
Tab Unificado de Análisis Completo
Integra: Compras, Ventas, Producción e Inventario en un solo tab
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
    """Renderiza el tab unificado de análisis completo."""
    
    st.title("📊 Análisis Integral de Operaciones")
    
    # Descripción del objetivo del tab
    st.markdown("""
    <div style="background-color: #f0f8ff; padding: 20px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-bottom: 20px;">
        <h4 style="color: #1f77b4; margin-top: 0;">🎯 Objetivo del Módulo</h4>
        <p style="margin-bottom: 10px;">
            Este módulo proporciona un <strong>análisis integral de las operaciones</strong> de Rio Futuro, 
            integrando métricas críticas de toda la cadena de valor en un solo panel de control.
        </p>
        <p style="margin-bottom: 10px;"><strong>¿Qué resuelve?</strong></p>
        <ul style="margin-bottom: 10px;">
            <li><strong>Compras MP/PSP:</strong> Identifica productos con mejor precio, volumen y tendencias de compra</li>
            <li><strong>Ventas PTT:</strong> Analiza productos más rentables, clientes top y márgenes reales</li>
            <li><strong>Producción:</strong> Calcula rendimientos PSP→PTT por tipo de fruta, detecta pérdidas y eficiencia</li>
            <li><strong>Inventario:</strong> Monitorea rotación, valorización y alertas de sobre/sub stock</li>
        </ul>
        <p style="margin-bottom: 0;">
            <strong>💡 Valor:</strong> Elimina la necesidad de analizar reportes separados. 
            Toda la información clave en un solo lugar para tomar decisiones rápidas y fundamentadas.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # ============================================================================
    # FILTROS GLOBALES (compartidos por todos los análisis)
    # ============================================================================
    st.markdown("### 🗓️ Selección de Período")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fecha_desde = st.date_input(
            "Desde",
            value=datetime(2025, 11, 1),
            format="DD/MM/YYYY",
            key="analisis_fecha_desde"
        )
    
    with col2:
        fecha_hasta = st.date_input(
            "Hasta",
            value=datetime(2026, 1, 31),
            format="DD/MM/YYYY",
            key="analisis_fecha_hasta"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        cargar_datos = st.button("🔄 Cargar Todos los Datos", type="primary", use_container_width=True)
    
    # ============================================================================
    # CARGAR DATOS (solo cuando se presiona el botón)
    # ============================================================================
    if not cargar_datos and 'analisis_completo_loaded' not in st.session_state:
        st.info("ℹ️ Presiona 'Cargar Todos los Datos' para iniciar el análisis")
        return
    
    if cargar_datos:
        fecha_desde_str = fecha_desde.strftime('%Y-%m-%d')
        fecha_hasta_str = fecha_hasta.strftime('%Y-%m-%d')
        
        with st.spinner("🔎 Cargando datos de todos los módulos..."):
            from .shared_analisis import (
                get_compras_data, 
                get_ventas_data, 
                get_produccion_data, 
                get_inventario_rotacion_data
            )
            
            # Cargar los 4 análisis en paralelo conceptualmente
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 1. Compras
            status_text.text("📦 Cargando compras...")
            progress_bar.progress(25)
            st.session_state.datos_compras = get_compras_data(username, password, fecha_desde_str, fecha_hasta_str)
            
            # 2. Ventas
            status_text.text("💰 Cargando ventas...")
            progress_bar.progress(50)
            st.session_state.datos_ventas = get_ventas_data(username, password, fecha_desde_str, fecha_hasta_str)
            
            # 3. Producción
            status_text.text("🏭 Cargando producción...")
            progress_bar.progress(75)
            st.session_state.datos_produccion = get_produccion_data(username, password, fecha_desde_str, fecha_hasta_str)
            
            # 4. Inventario
            status_text.text("📊 Cargando inventario...")
            progress_bar.progress(100)
            st.session_state.datos_inventario = get_inventario_rotacion_data(username, password, fecha_desde_str, fecha_hasta_str)
            
            st.session_state.analisis_completo_loaded = True
            st.session_state.periodo_desde = fecha_desde_str
            st.session_state.periodo_hasta = fecha_hasta_str
            
            progress_bar.empty()
            status_text.empty()
            
            st.success("✅ Datos cargados correctamente")
    
    # ============================================================================
    # TABS INTERNOS (4 análisis)
    # ============================================================================
    st.markdown("---")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📦 Compras MP",
        "💰 Ventas PT", 
        "🏭 Producción",
        "📊 Inventario"
    ])
    
    # ============================================================================
    # TAB 1: COMPRAS
    # ============================================================================
    with tab1:
        _render_compras(st.session_state.get('datos_compras', {}))
    
    # ============================================================================
    # TAB 2: VENTAS
    # ============================================================================
    with tab2:
        _render_ventas(st.session_state.get('datos_ventas', {}))
    
    # ============================================================================
    # TAB 3: PRODUCCIÓN
    # ============================================================================
    with tab3:
        _render_produccion(st.session_state.get('datos_produccion', {}))
    
    # ============================================================================
    # TAB 4: INVENTARIO
    # ============================================================================
    with tab4:
        _render_inventario(st.session_state.get('datos_inventario', {}))


# ==============================================================================
# FUNCIONES MODULARES PARA CADA ANÁLISIS
# ==============================================================================

def _render_compras(data):
    """Renderiza análisis de compras."""
    if data.get('error'):
        st.error(f"❌ {data['error']}")
        return
    
    if not data:
        st.info("No hay datos cargados")
        return
    
    st.info(f"📅 Período: **{data.get('fecha_desde', '')}** a **{data.get('fecha_hasta', '')}**")
    
    # Métricas
    st.markdown("#### 📊 Resumen")
    resumen = data.get('resumen', {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Comprado", f"{resumen.get('kg', 0):,.0f} kg")
    with col2:
        st.metric("Inversión", f"${resumen.get('monto', 0):,.0f}")
    with col3:
        st.metric("Precio Promedio", f"${resumen.get('precio_promedio', 0):,.2f}/kg")
    
    # Distribución por tipo
    st.markdown("#### 🍓 Por Tipo de Fruta")
    por_tipo = data.get('por_tipo', [])
    
    if por_tipo:
        df_tipo = pd.DataFrame(por_tipo)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            fig_pie = px.pie(df_tipo, values='monto', names='tipo_fruta', title='Distribución por Tipo', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            df_tipo['Monto'] = df_tipo['monto'].apply(lambda x: f"${x:,.0f}")
            df_tipo['Kg'] = df_tipo['kg'].apply(lambda x: f"{x:,.0f}")
            df_tipo['$/kg'] = df_tipo['precio_promedio'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(df_tipo[['tipo_fruta', 'manejo', 'Kg', 'Monto', '$/kg']], use_container_width=True, hide_index=True)
    
    # Top proveedores
    st.markdown("#### 👥 Top Proveedores")
    top_prov = data.get('top_proveedores', [])
    
    if top_prov:
        df_prov = pd.DataFrame(top_prov[:5])
        fig_prov = px.bar(df_prov, x='monto', y='proveedor', orientation='h', text='monto')
        fig_prov.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_prov, use_container_width=True)
    
    # Tendencia
    st.markdown("#### 📈 Tendencia de Precios")
    tendencia = data.get('tendencia_precios', [])
    
    if tendencia:
        df_tend = pd.DataFrame(tendencia)
        fig_tend = go.Figure()
        fig_tend.add_trace(go.Scatter(x=df_tend['mes'], y=df_tend['precio_promedio'], mode='lines+markers', line=dict(width=3)))
        fig_tend.update_layout(xaxis_title='Mes', yaxis_title='Precio CLP/kg', hovermode='x unified')
        st.plotly_chart(fig_tend, use_container_width=True)


def _render_ventas(data):
    """Renderiza análisis de ventas."""
    if data.get('error'):
        st.error(f"❌ {data['error']}")
        return
    
    if not data:
        st.info("No hay datos cargados")
        return
    
    st.info(f"📅 Período: **{data.get('fecha_desde', '')}** a **{data.get('fecha_hasta', '')}**")
    
    # Métricas
    st.markdown("#### 📊 Resumen")
    resumen = data.get('resumen', {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Vendido", f"{resumen.get('kg', 0):,.0f} kg")
    with col2:
        st.metric("Ingresos", f"${resumen.get('monto', 0):,.0f}")
    with col3:
        st.metric("Precio Promedio", f"${resumen.get('precio_promedio', 0):,.2f}/kg")
    
    # Por categoría
    st.markdown("#### 📦 Por Categoría")
    por_cat = data.get('por_categoria', [])
    
    if por_cat:
        df_cat = pd.DataFrame(por_cat)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            fig_cat = px.pie(df_cat, values='monto', names='categoria', title='Ventas por Categoría', hole=0.4)
            st.plotly_chart(fig_cat, use_container_width=True)
        
        with col2:
            df_cat['%'] = df_cat['porcentaje'].apply(lambda x: f"{x:.1f}%")
            df_cat['Monto'] = df_cat['monto'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(df_cat[['categoria', 'kg', 'Monto', '%']], use_container_width=True, hide_index=True)
    
    # Top clientes
    st.markdown("#### 👥 Top Clientes")
    top_cli = data.get('top_clientes', [])
    
    if top_cli:
        df_cli = pd.DataFrame(top_cli[:5])
        fig_cli = px.bar(df_cli, x='monto', y='cliente', orientation='h', text='monto')
        fig_cli.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_cli, use_container_width=True)
    
    # Tendencia
    st.markdown("#### 📈 Tendencia de Precios")
    tendencia = data.get('tendencia_precios', [])
    
    if tendencia:
        df_tend = pd.DataFrame(tendencia)
        fig_tend = go.Figure()
        fig_tend.add_trace(go.Scatter(x=df_tend['mes'], y=df_tend['precio_promedio'], mode='lines+markers', line=dict(width=3, color='#2ca02c')))
        fig_tend.update_layout(xaxis_title='Mes', yaxis_title='Precio CLP/kg', hovermode='x unified')
        st.plotly_chart(fig_tend, use_container_width=True)


def _render_produccion(data):
    """Renderiza análisis de producción."""
    if data.get('error'):
        st.error(f"❌ {data['error']}")
        return
    
    if not data:
        st.info("No hay datos cargados")
        return
    
    st.info(f"📅 Período: **{data.get('fecha_desde', '')}** a **{data.get('fecha_hasta', '')}**")
    
    # Métricas
    st.markdown("#### 📊 Resumen")
    resumen = data.get('resumen', {})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("MP Consumida", f"{resumen.get('kg_consumido', 0):,.0f} kg")
    with col2:
        st.metric("PT Producido", f"{resumen.get('kg_producido', 0):,.0f} kg")
    with col3:
        st.metric("Rendimiento", f"{resumen.get('rendimiento_pct', 0):.1f}%")
    with col4:
        st.metric("Merma", f"{resumen.get('merma_pct', 0):.1f}%", delta=f"-{resumen.get('merma_kg', 0):,.0f} kg", delta_color="inverse")
    
    st.caption(f"📦 Órdenes: {resumen.get('ordenes_total', 0):,}")
    
    # Rendimientos por tipo
    st.markdown("#### 🍓 Rendimientos por Tipo")
    rendimientos = data.get('rendimientos_por_tipo', [])
    
    if rendimientos:
        df_rend = pd.DataFrame(rendimientos)
        
        fig_rend = go.Figure()
        fig_rend.add_trace(go.Bar(name='Consumo MP', x=df_rend['tipo_fruta'], y=df_rend['kg_consumido'], marker_color='#ff7f0e'))
        fig_rend.add_trace(go.Bar(name='Producción PT', x=df_rend['tipo_fruta'], y=df_rend['kg_producido'], marker_color='#2ca02c'))
        fig_rend.update_layout(barmode='group', xaxis_title='Tipo', yaxis_title='Kg', hovermode='x unified')
        st.plotly_chart(fig_rend, use_container_width=True)
        
        df_rend['Rend.'] = df_rend['rendimiento_pct'].apply(lambda x: f"{x:.1f}%")
        df_rend['Merma'] = df_rend['merma_pct'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(df_rend[['tipo_fruta', 'kg_consumido', 'kg_producido', 'Rend.', 'Merma']], use_container_width=True, hide_index=True)
    
    # Detalle órdenes (solo últimas 10)
    ordenes = data.get('detalle_ordenes', [])
    if ordenes:
        st.markdown("#### 📋 Últimas Órdenes")
        df_ord = pd.DataFrame(ordenes[:10])
        df_ord['Rend.'] = df_ord['rendimiento_pct'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(df_ord[['fecha', 'orden', 'tipo_fruta', 'kg_consumido', 'kg_producido', 'Rend.']], use_container_width=True, hide_index=True)


def _render_inventario(data):
    """Renderiza análisis de inventario."""
    if data.get('error'):
        st.error(f"❌ {data['error']}")
        return
    
    if not data:
        st.info("No hay datos cargados")
        return
    
    st.info(f"📅 Período: **{data.get('fecha_desde', '')}** a **{data.get('fecha_hasta', '')}** ({data.get('dias_periodo', 0)} días)")
    
    # Métricas
    st.markdown("#### 📊 Resumen")
    resumen = data.get('resumen', {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Stock Total", f"{resumen.get('stock_total_kg', 0):,.0f} kg")
    with col2:
        st.metric("Valorización", f"${resumen.get('valor_total', 0):,.0f}")
    with col3:
        st.metric("Productos", f"{resumen.get('productos_con_stock', 0):,}")
    
    # Por ubicación
    st.markdown("#### 📍 Por Ubicación")
    por_ubic = data.get('por_ubicacion', [])
    
    if por_ubic:
        df_ubic = pd.DataFrame(por_ubic[:5])
        
        fig_ubic = px.pie(df_ubic, values='kg', names='ubicacion', title='Stock por Ubicación', hole=0.4)
        st.plotly_chart(fig_ubic, use_container_width=True)
    
    # Top productos
    st.markdown("#### 📦 Top 10 Productos (por valor)")
    por_prod = data.get('por_producto', [])
    
    if por_prod:
        df_prod = pd.DataFrame(por_prod[:10])
        df_prod['Valor'] = df_prod['valor_stock'].apply(lambda x: f"${x:,.0f}")
        df_prod['Días'] = df_prod['dias_inventario'].apply(lambda x: f"{x:.0f}" if x < 999 else "999+")
        st.dataframe(df_prod[['producto', 'tipo_fruta', 'stock_kg', 'Valor', 'rotacion', 'Días']], use_container_width=True, hide_index=True)
    
    # Alertas
    st.markdown("#### ⚠️ Alertas de Inventario")
    alertas = data.get('alertas', [])
    
    if alertas:
        for alerta in alertas[:5]:
            tipo = alerta.get('tipo', '')
            if tipo == 'stock_lento':
                st.warning(f"🐌 **{alerta.get('producto', '')}**: {alerta.get('mensaje', '')}")
            elif tipo == 'sin_movimiento':
                st.error(f"❌ **{alerta.get('producto', '')}**: {alerta.get('mensaje', '')}")
    else:
        st.success("✅ No hay alertas de inventario")

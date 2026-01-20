"""
Tab de Stock Teórico Anual
Análisis multi-anual de compras, ventas y merma proyectada por tipo de fruta y manejo
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
    """Renderiza el análisis de stock teórico anual."""
    
    st.title("📊 Stock Teórico Anual")
    
    # ============================================================================
    # FILTROS DE AÑOS Y CONFIGURACIÓN
    # ============================================================================
    st.markdown("### 🗓️ Configuración de Análisis")
    
    st.info("ℹ️ **Temporadas**: Cada temporada va del 1 de noviembre al 31 de octubre del año siguiente. Ejemplo: Temporada 2024 = Nov 2023 a Oct 2024")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Selector de años múltiples
        anios_disponibles = [2023, 2024, 2025, 2026]
        anios_seleccionados = st.multiselect(
            "Temporadas a Analizar",
            options=anios_disponibles,
            default=[2024, 2025, 2026],
            key="stock_teorico_anios"
        )
    
    with col2:
        # Fecha de corte (mes-día)
        mes_corte = st.selectbox(
            "Mes de Corte",
            options=list(range(1, 13)),
            index=9,  # Octubre (index 9 = mes 10)
            format_func=lambda x: datetime(2000, x, 1).strftime("%B"),
            key="stock_teorico_mes"
        )
        
        dia_corte = st.number_input(
            "Día de Corte",
            min_value=1,
            max_value=31,
            value=31,
            key="stock_teorico_dia"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        cargar_datos = st.button("🔄 Cargar Análisis", type="primary", use_container_width=True)
    
    # ============================================================================
    # VALIDAR Y CARGAR DATOS
    # ============================================================================
    if not anios_seleccionados:
        st.warning("⚠️ Selecciona al menos una temporada para analizar")
        return
    
    if not cargar_datos and 'stock_teorico_loaded' not in st.session_state:
        st.info("ℹ️ Presiona 'Cargar Análisis' para iniciar el cálculo de stock teórico por temporada")
        return
    
    if cargar_datos:
        fecha_corte_str = f"{mes_corte:02d}-{dia_corte:02d}"
        
        with st.spinner("🔎 Analizando compras, ventas y calculando merma histórica..."):
            from .shared_analisis import get_stock_teorico_anual
            
            # Cargar análisis multi-anual
            st.session_state.datos_stock_teorico = get_stock_teorico_anual(
                username, 
                password, 
                anios_seleccionados,
                fecha_corte_str
            )
            
            st.session_state.stock_teorico_loaded = True
            st.session_state.stock_teorico_corte = fecha_corte_str
            
            st.success(f"✅ Análisis completado para {len(anios_seleccionados)} años")
    
    # ============================================================================
    # MOSTRAR RESULTADOS
    # ============================================================================
    data = st.session_state.get('datos_stock_teorico', {})
    
    if data.get('error'):
        st.error(f"❌ {data['error']}")
        return
    
    if not data:
        return
    
    st.markdown("---")
    
    # Información del análisis
    st.info(f"""
    📅 **Análisis de {len(data.get('anios_analizados', []))} temporadas** | 
    📍 Corte: {data.get('fecha_corte', '')} (Fin de temporada) | 
    📉 Merma Histórica: **{data.get('merma_historica_pct', 0):.2f}%**
    """)
    
    # ============================================================================
    # RESUMEN GENERAL CONSOLIDADO
    # ============================================================================
    st.markdown("### 📊 Resumen General (Todas las Temporadas)")
    
    resumen = data.get('resumen_general', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Compras", 
            f"{resumen.get('total_compras_kg', 0):,.0f} kg",
            delta=f"${resumen.get('total_compras_monto', 0):,.0f}"
        )
        st.caption(f"Precio: ${resumen.get('precio_promedio_compra_global', 0):,.2f}/kg")
    
    with col2:
        st.metric(
            "Total Ventas", 
            f"{resumen.get('total_ventas_kg', 0):,.0f} kg",
            delta=f"${resumen.get('total_ventas_monto', 0):,.0f}"
        )
        st.caption(f"Precio: ${resumen.get('precio_promedio_venta_global', 0):,.2f}/kg")
    
    with col3:
        st.metric(
            "Total Merma", 
            f"{resumen.get('total_merma_kg', 0):,.0f} kg",
            delta=f"{resumen.get('pct_merma_historico', 0):.2f}%",
            delta_color="inverse"
        )
    
    with col4:
        st.metric(
            "Stock Teórico Total", 
            f"${resumen.get('total_stock_teorico_valor', 0):,.0f}",
            delta="Valorización"
        )
    
    # ============================================================================
    # TABS POR AÑO
    # ============================================================================
    st.markdown("---")
    st.markdown("### 📅 Análisis Detallado por Temporada")
    
    por_anio = data.get('por_anio', {})
    
    if not por_anio:
        st.warning("No hay datos por temporada")
        return
    
    # Crear tabs dinámicamente según los años analizados
    anios_ordenados = sorted(por_anio.keys())
    tabs = st.tabs([f"📆 Temporada {anio}" for anio in anios_ordenados])
    
    for idx, anio in enumerate(anios_ordenados):
        with tabs[idx]:
            _render_anio_detalle(anio, por_anio[anio])
    
    # ============================================================================
    # COMPARATIVA MULTI-ANUAL
    # ============================================================================
    st.markdown("---")
    st.markdown("### 📈 Comparativa Multi-Anual")
    
    _render_comparativa_multianual(por_anio)


# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def _render_anio_detalle(anio: int, data: dict):
    """Renderiza el detalle de una temporada específica."""
    
    st.markdown(f"#### 📅 Temporada {anio}")
    temporada_str = data.get('temporada', f'{int(anio)-1}-11-01 a {int(anio)}-10-31')
    st.caption(f"Período: {temporada_str}")
    st.caption(f"Datos: {data.get('fecha_desde', '')} hasta {data.get('fecha_hasta', '')}")
    
    datos = data.get('datos', [])
    
    if not datos:
        st.warning(f"No hay datos para la temporada {anio}")
        return
    
    # Convertir a DataFrame
    df = pd.DataFrame(datos)
    
    # Calcular totales del año
    total_compras_kg = df['compras_kg'].sum()
    total_compras_monto = df['compras_monto'].sum()
    total_ventas_kg = df['ventas_kg'].sum()
    total_ventas_monto = df['ventas_monto'].sum()
    total_merma_kg = df['merma_kg'].sum()
    total_stock_valor = df['stock_teorico_valor'].sum()
    
    # Métricas del año
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Compras", f"{total_compras_kg:,.0f} kg")
        st.caption(f"Monto: ${total_compras_monto:,.0f}")
        st.caption(f"Precio: ${total_compras_monto/total_compras_kg:,.2f}/kg" if total_compras_kg > 0 else "N/A")
    
    with col2:
        st.metric("Ventas", f"{total_ventas_kg:,.0f} kg")
        st.caption(f"Monto: ${total_ventas_monto:,.0f}")
        st.caption(f"Precio: ${total_ventas_monto/total_ventas_kg:,.2f}/kg" if total_ventas_kg > 0 else "N/A")
    
    with col3:
        merma_pct = (total_merma_kg / total_compras_kg * 100) if total_compras_kg > 0 else 0
        st.metric("Merma", f"{total_merma_kg:,.0f} kg", delta=f"{merma_pct:.2f}%", delta_color="inverse")
        st.caption(f"Stock teórico: ${total_stock_valor:,.0f}")
    
    # Tabla detallada por tipo y manejo
    st.markdown("##### 📊 Por Tipo de Fruta y Manejo")
    
    # Formatear DataFrame para visualización
    df_display = df.copy()
    df_display['Compras (kg)'] = df_display['compras_kg'].apply(lambda x: f"{x:,.0f}")
    df_display['Compras ($)'] = df_display['compras_monto'].apply(lambda x: f"${x:,.0f}")
    df_display['$/kg Compra'] = df_display['precio_promedio_compra'].apply(lambda x: f"${x:,.2f}")
    df_display['Ventas (kg)'] = df_display['ventas_kg'].apply(lambda x: f"{x:,.0f}")
    df_display['Ventas ($)'] = df_display['ventas_monto'].apply(lambda x: f"${x:,.0f}")
    df_display['$/kg Venta'] = df_display['precio_promedio_venta'].apply(lambda x: f"${x:,.2f}")
    df_display['Merma (kg)'] = df_display['merma_kg'].apply(lambda x: f"{x:,.0f}")
    df_display['Merma (%)'] = df_display['merma_pct'].apply(lambda x: f"{x:.2f}%")
    df_display['Stock Teórico ($)'] = df_display['stock_teorico_valor'].apply(lambda x: f"${x:,.0f}")
    
    st.dataframe(
        df_display[[
            'tipo_fruta', 'manejo', 
            'Compras (kg)', 'Compras ($)', '$/kg Compra',
            'Ventas (kg)', 'Ventas ($)', '$/kg Venta',
            'Merma (kg)', 'Merma (%)', 
            'Stock Teórico ($)'
        ]],
        use_container_width=True,
        hide_index=True
    )
    
    # Fila de totales
    st.markdown("##### 📊 Totales")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Compras", f"{total_compras_kg:,.0f} kg", delta=f"${total_compras_monto:,.0f}")
    
    with col2:
        st.metric("Ventas", f"{total_ventas_kg:,.0f} kg", delta=f"${total_ventas_monto:,.0f}")
    
    with col3:
        st.metric("Merma", f"{total_merma_kg:,.0f} kg", delta=f"{merma_pct:.2f}%", delta_color="inverse")
    
    with col4:
        st.metric("Stock Teórico", f"${total_stock_valor:,.0f}")
    
    with col5:
        precio_compra_prom = total_compras_monto/total_compras_kg if total_compras_kg > 0 else 0
        precio_venta_prom = total_ventas_monto/total_ventas_kg if total_ventas_kg > 0 else 0
        st.metric("$/kg Compra", f"${precio_compra_prom:,.2f}")
        st.caption(f"$/kg Venta: ${precio_venta_prom:,.2f}")
    
    # Gráfico de distribución de compras por tipo
    st.markdown("##### 🍓 Distribución de Compras por Tipo de Fruta")
    
    fig_pie = px.pie(
        df, 
        values='compras_kg', 
        names='tipo_fruta', 
        title=f'Compras Temporada {anio} por Tipo de Fruta',
        hole=0.4
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # Gráfico de barras: Compras vs Ventas vs Merma
    st.markdown("##### 📊 Comparación Compras vs Ventas vs Merma")
    
    fig_bar = go.Figure()
    
    fig_bar.add_trace(go.Bar(
        name='Compras',
        x=df['tipo_fruta'] + ' - ' + df['manejo'],
        y=df['compras_kg'],
        marker_color='#1f77b4'
    ))
    
    fig_bar.add_trace(go.Bar(
        name='Ventas',
        x=df['tipo_fruta'] + ' - ' + df['manejo'],
        y=df['ventas_kg'],
        marker_color='#2ca02c'
    ))
    
    fig_bar.add_trace(go.Bar(
        name='Merma',
        x=df['tipo_fruta'] + ' - ' + df['manejo'],
        y=df['merma_kg'],
        marker_color='#d62728'
    ))
    
    fig_bar.update_layout(
        barmode='group',
        xaxis_title='Tipo - Manejo',
        yaxis_title='Kilogramos',
        hovermode='x unified',
        xaxis_tickangle=-45
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)


def _render_comparativa_multianual(por_anio: dict):
    """Renderiza gráficos comparativos entre temporadas."""
    
    # Consolidar datos de todas las temporadas
    datos_comparativa = []
    
    for anio, data in por_anio.items():
        for item in data.get('datos', []):
            datos_comparativa.append({
                'anio': anio,
                'tipo_fruta': item['tipo_fruta'],
                'manejo': item['manejo'],
                'compras_kg': item['compras_kg'],
                'ventas_kg': item['ventas_kg'],
                'merma_kg': item['merma_kg'],
                'merma_pct': item['merma_pct'],
                'precio_compra': item['precio_promedio_compra'],
                'precio_venta': item['precio_promedio_venta']
            })
    
    if not datos_comparativa:
        st.warning("No hay datos para comparar")
        return
    
    df_comp = pd.DataFrame(datos_comparativa)
    
    # Totales por año
    df_totales_anio = df_comp.groupby('anio').agg({
        'compras_kg': 'sum',
        'ventas_kg': 'sum',
        'merma_kg': 'sum'
    }).reset_index()
    
    # Gráfico de líneas: Evolución de compras/ventas por temporada
    st.markdown("#### 📈 Evolución de Compras y Ventas por Temporada")
    
    fig_evol = go.Figure()
    
    fig_evol.add_trace(go.Scatter(
        x=df_totales_anio['anio'],
        y=df_totales_anio['compras_kg'],
        mode='lines+markers',
        name='Compras',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=10)
    ))
    
    fig_evol.add_trace(go.Scatter(
        x=df_totales_anio['anio'],
        y=df_totales_anio['ventas_kg'],
        mode='lines+markers',
        name='Ventas',
        line=dict(color='#2ca02c', width=3),
        marker=dict(size=10)
    ))
    
    fig_evol.add_trace(go.Scatter(
        x=df_totales_anio['anio'],
        y=df_totales_anio['merma_kg'],
        mode='lines+markers',
        name='Merma',
        line=dict(color='#d62728', width=3),
        marker=dict(size=10)
    ))
    
    fig_evol.update_layout(
        xaxis_title='Temporada',
        yaxis_title='Kilogramos',
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_evol, use_container_width=True)
    
    # Tabla de totales por año
    st.markdown("#### 📊 Tabla Comparativa por Temporada")
    
    df_totales_display = df_totales_anio.copy()
    df_totales_display['Compras (kg)'] = df_totales_display['compras_kg'].apply(lambda x: f"{x:,.0f}")
    df_totales_display['Ventas (kg)'] = df_totales_display['ventas_kg'].apply(lambda x: f"{x:,.0f}")
    df_totales_display['Merma (kg)'] = df_totales_display['merma_kg'].apply(lambda x: f"{x:,.0f}")
    df_totales_display['Merma (%)'] = (df_totales_display['merma_kg'] / df_totales_display['compras_kg'] * 100).apply(lambda x: f"{x:.2f}%")
    
    st.dataframe(
        df_totales_display[['anio', 'Compras (kg)', 'Ventas (kg)', 'Merma (kg)', 'Merma (%)']],
        use_container_width=True,
        hide_index=True
    )
    
    # Evolución de precios promedio por tipo de fruta
    st.markdown("#### 💰 Evolución de Precios Promedio por Tipo de Fruta")
    
    # Agrupar por año y tipo de fruta
    df_precios = df_comp.groupby(['anio', 'tipo_fruta']).agg({
        'precio_compra': 'mean',
        'precio_venta': 'mean'
    }).reset_index()
    
    # Crear selector de tipo de fruta
    tipos_disponibles = sorted(df_precios['tipo_fruta'].unique())
    
    if tipos_disponibles:
        tipo_seleccionado = st.selectbox(
            "Seleccionar Tipo de Fruta",
            options=tipos_disponibles,
            key="comparativa_tipo_fruta"
        )
        
        df_tipo_filtrado = df_precios[df_precios['tipo_fruta'] == tipo_seleccionado]
        
        fig_precios = go.Figure()
        
        fig_precios.add_trace(go.Scatter(
            x=df_tipo_filtrado['anio'],
            y=df_tipo_filtrado['precio_compra'],
            mode='lines+markers',
            name='Precio Compra',
            line=dict(color='#ff7f0e', width=3),
            marker=dict(size=10)
        ))
        
        fig_precios.add_trace(go.Scatter(
            x=df_tipo_filtrado['anio'],
            y=df_tipo_filtrado['precio_venta'],
            mode='lines+markers',
            name='Precio Venta',
            line=dict(color='#2ca02c', width=3),
            marker=dict(size=10)
        ))
        
        fig_precios.update_layout(
            title=f'Evolución de Precios: {tipo_seleccionado}',
            xaxis_title='Temporada',
            yaxis_title='Precio ($/kg)',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_precios, use_container_width=True)


# ==============================================================================
# FUNCIONES LEGACY (mantener compatibilidad si se referencian desde otro lado)
# ==============================================================================

# ==============================================================================
# FUNCIONES LEGACY (mantener compatibilidad si se referencian desde otro lado)
# ==============================================================================

def _render_compras(data):
    """Función legacy - mantener por compatibilidad."""
    pass

def _render_ventas(data):
    """Función legacy - mantener por compatibilidad."""
    pass

def _render_produccion(data):
    """Función legacy - mantener por compatibilidad."""
    pass

def _render_inventario(data):
    """Función legacy - mantener por compatibilidad."""
    pass

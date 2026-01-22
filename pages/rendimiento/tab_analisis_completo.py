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
    # FILTROS DE FECHAS
    # ============================================================================
    st.markdown("### 🗓️ Configuración de Análisis")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        fecha_desde = st.date_input(
            "Fecha Desde",
            value=datetime(2023, 11, 1),
            key="stock_teorico_fecha_desde"
        )
    
    with col2:
        fecha_hasta = st.date_input(
            "Fecha Hasta",
            value=datetime.now(),
            key="stock_teorico_fecha_hasta"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        cargar_datos = st.button("🔄 Cargar Análisis", type="primary", use_container_width=True)
    
    # ============================================================================
    # VALIDAR Y CARGAR DATOS
    # ============================================================================
    if fecha_desde >= fecha_hasta:
        st.warning("⚠️ La fecha desde debe ser menor que la fecha hasta")
        return
    
    if not cargar_datos and 'stock_teorico_loaded' not in st.session_state:
        st.info("ℹ️ Presiona 'Cargar Análisis' para iniciar el cálculo de stock teórico")
        return
    
    if cargar_datos:
        fecha_desde_str = fecha_desde.strftime("%Y-%m-%d")
        fecha_hasta_str = fecha_hasta.strftime("%Y-%m-%d")
        
        with st.spinner("🔎 Analizando compras, ventas y calculando merma histórica..."):
            from .shared_analisis import get_stock_teorico_rango
            
            # Guardar credenciales en session_state para funciones auxiliares
            st.session_state.username = username
            st.session_state.password = password
            
            # Cargar análisis por rango
            st.session_state.datos_stock_teorico = get_stock_teorico_rango(
                username, 
                password, 
                fecha_desde_str,
                fecha_hasta_str
            )
            
            st.session_state.stock_teorico_loaded = True
            st.session_state.st_fecha_desde_cargada = fecha_desde_str
            st.session_state.st_fecha_hasta_cargada = fecha_hasta_str
            
            st.success(f"✅ Análisis completado")
    
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
    fecha_desde_display = data.get('fecha_desde', '')
    fecha_hasta_display = data.get('fecha_hasta', '')
    st.info(f"""
    📅 **Período**: {fecha_desde_display} → {fecha_hasta_display} | 
    📉 Merma Histórica: **{data.get('merma_historica_pct', 0):.2f}%**
    """)
    
    # ============================================================================
    # DETALLE POR TIPO Y MANEJO (incluye resumen integrado)
    # ============================================================================
    
    datos = data.get('datos', [])
    
    if not datos:
        st.warning("No hay datos para el período seleccionado")
        return
    
    _render_detalle_datos(datos, data.get('resumen', {}))


# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================
def _render_detalle_datos(datos: list, resumen: dict):
    """Renderiza el detalle de datos por tipo y manejo."""
    
    df = pd.DataFrame(datos)
    
    # ============================================================================
    # CALCULAR COLUMNAS DE RENTABILIDAD
    # ============================================================================
    df['margen_bruto_kg'] = df['precio_promedio_venta'] - df['precio_promedio_compra']
    df['margen_bruto_pct'] = ((df['precio_promedio_venta'] / df['precio_promedio_compra'] - 1) * 100).fillna(0)
    df['costo_merma'] = df['merma_kg'] * df['precio_promedio_compra']
    df['utilidad_neta'] = df['ventas_monto'] - df['compras_monto']
    df['rentabilidad_real'] = df['ventas_monto'] - df['compras_monto'] - df['costo_merma']
    df['roi_pct'] = ((df['utilidad_neta'] / df['compras_monto']) * 100).fillna(0)
    
    # ============================================================================
    # RESUMEN GENERAL (ÚNICO)
    # ============================================================================
    st.markdown("### 📊 Resumen General")
    
    total_compras_kg = df['compras_kg'].sum()
    total_compras_monto = df['compras_monto'].sum()
    total_ventas_kg = df['ventas_kg'].sum()
    total_ventas_monto = df['ventas_monto'].sum()
    total_merma_kg = df['merma_kg'].sum()
    total_stock_valor = df['stock_teorico_valor'].sum()
    merma_pct = (total_merma_kg / total_compras_kg * 100) if total_compras_kg > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📦 Compras")
        st.metric("", f"{total_compras_kg:,.0f} kg", delta=f"${total_compras_monto:,.0f}", delta_color="off")
        st.caption(f"Precio: ${total_compras_monto/total_compras_kg:,.2f}/kg" if total_compras_kg > 0 else "N/A")
    
    with col2:
        st.markdown("#### 💰 Ventas")
        st.metric("", f"{total_ventas_kg:,.0f} kg", delta=f"${total_ventas_monto:,.0f}", delta_color="off")
        st.caption(f"Precio: ${total_ventas_monto/total_ventas_kg:,.2f}/kg" if total_ventas_kg > 0 else "N/A")
    
    with col3:
        st.markdown("#### 📉 Merma")
        st.metric("", f"{total_merma_kg:,.0f} kg", delta=f"{merma_pct:.2f}%", delta_color="inverse")
        st.caption(f"Stock teórico: ${total_stock_valor:,.0f}")
    
    # ============================================================================
    # TABLA DETALLADA CON RENTABILIDAD
    # ============================================================================
    st.markdown("---")
    st.markdown("### 📋 Detalle por Tipo de Fruta y Manejo")
    
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
    df_display['Margen $/kg'] = df_display['margen_bruto_kg'].apply(lambda x: f"${x:,.2f}")
    df_display['Margen %'] = df_display['margen_bruto_pct'].apply(lambda x: f"{x:.1f}%")
    df_display['ROI %'] = df_display['roi_pct'].apply(lambda x: f"{x:.1f}%")
    df_display['Stock Teórico ($)'] = df_display['stock_teorico_valor'].apply(lambda x: f"${x:,.0f}")
    
    # Agregar fila de totales
    precio_compra_prom = total_compras_monto/total_compras_kg if total_compras_kg > 0 else 0
    precio_venta_prom = total_ventas_monto/total_ventas_kg if total_ventas_kg > 0 else 0
    margen_bruto_total = precio_venta_prom - precio_compra_prom
    margen_pct_total = ((precio_venta_prom / precio_compra_prom - 1) * 100) if precio_compra_prom > 0 else 0
    roi_total = (((total_ventas_monto - total_compras_monto) / total_compras_monto) * 100) if total_compras_monto > 0 else 0
    
    totales_row = pd.DataFrame([{
        'tipo_fruta': '📊 Totales',
        'manejo': '',
        'Compras (kg)': f"{total_compras_kg:,.0f}",
        'Compras ($)': f"${total_compras_monto:,.0f}",
        '$/kg Compra': f"${precio_compra_prom:,.2f}",
        'Ventas (kg)': f"{total_ventas_kg:,.0f}",
        'Ventas ($)': f"${total_ventas_monto:,.0f}",
        '$/kg Venta': f"${precio_venta_prom:,.2f}",
        'Merma (kg)': f"{total_merma_kg:,.0f}",
        'Merma (%)': f"{merma_pct:.2f}%",
        'Margen $/kg': f"${margen_bruto_total:,.2f}",
        'Margen %': f"{margen_pct_total:.1f}%",
        'ROI %': f"{roi_total:.1f}%",
        'Stock Teórico ($)': f"${total_stock_valor:,.0f}"
    }])
    
    df_display_con_totales = pd.concat([df_display[[
        'tipo_fruta', 'manejo', 
        'Compras (kg)', 'Compras ($)', '$/kg Compra',
        'Ventas (kg)', 'Ventas ($)', '$/kg Venta',
        'Merma (kg)', 'Merma (%)', 
        'Margen $/kg', 'Margen %', 'ROI %',
        'Stock Teórico ($)'
    ]], totales_row], ignore_index=True)
    
    st.dataframe(
        df_display_con_totales,
        use_container_width=True,
        hide_index=True,
        height=600
    )
    
    # ============================================================================
    # GRÁFICOS DE ANÁLISIS
    # ============================================================================
    st.markdown("---")
    st.markdown("### 📊 Distribución de Compras por Tipo de Fruta")
    
    # Agrupar por tipo de fruta
    df_por_tipo = df.groupby('tipo_fruta').agg({
        'compras_kg': 'sum',
        'compras_monto': 'sum',
        'ventas_kg': 'sum',
        'ventas_monto': 'sum'
    }).reset_index()
    
    # Ordenar por compras (mayor a menor)
    df_por_tipo = df_por_tipo.sort_values('compras_kg', ascending=False)
    
    # Crear DataFrame largo para mejor visualización
    df_tipo_melt = df_por_tipo.melt(
        id_vars=['tipo_fruta'], 
        value_vars=['compras_kg', 'ventas_kg'],
        var_name='Tipo',
        value_name='Kilogramos'
    )
    
    # Renombrar para leyenda más clara
    df_tipo_melt['Tipo'] = df_tipo_melt['Tipo'].replace({
        'compras_kg': 'Compras',
        'ventas_kg': 'Ventas'
    })
    
    fig_tipo = px.bar(
        df_tipo_melt,
        x='tipo_fruta',
        y='Kilogramos',
        color='Tipo',
        title='Compras vs Ventas por Tipo de Fruta (kg)',
        labels={'tipo_fruta': 'Tipo de Fruta', 'Kilogramos': 'Kilogramos (kg)'},
        barmode='group',
        color_discrete_map={'Compras': '#2ecc71', 'Ventas': '#e74c3c'}
    )
    
    fig_tipo.update_layout(
        xaxis_title="Tipo de Fruta",
        yaxis_title="Kilogramos (kg)",
        legend_title="",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_tipo, use_container_width=True)
    
    st.markdown("### 🌱 Distribución por Tipo de Manejo")
    
    df_por_manejo = df.groupby('manejo').agg({
        'compras_kg': 'sum',
        'compras_monto': 'sum',
        'ventas_kg': 'sum',
        'ventas_monto': 'sum'
    }).reset_index()
    
    # Ordenar por compras
    df_por_manejo = df_por_manejo.sort_values('compras_kg', ascending=False)
    
    fig_manejo = px.pie(
        df_por_manejo,
        values='compras_kg',
        names='manejo',
        title='Distribución de Compras por Tipo de Manejo (kg)',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    
    fig_manejo.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>%{value:,.0f} kg<br>%{percent}<extra></extra>'
    )
    
    st.plotly_chart(fig_manejo, use_container_width=True)
    
    # ============================================================================
    # ANÁLISIS TEMPORAL MES A MES
    # ============================================================================
    st.markdown("---")
    st.markdown("### 📈 Análisis Temporal Mes a Mes")
    
    with st.spinner("Calculando tendencias mensuales..."):
        from .shared_analisis import get_analisis_mensual
        
        fecha_desde_str = st.session_state.get('st_fecha_desde_cargada', '')
        fecha_hasta_str = st.session_state.get('st_fecha_hasta_cargada', '')
        
        if fecha_desde_str and fecha_hasta_str:
            datos_mensuales = get_analisis_mensual(
                st.session_state.get('username', ''),
                st.session_state.get('password', ''),
                fecha_desde_str,
                fecha_hasta_str
            )
            
            if datos_mensuales and not datos_mensuales.get('error'):
                df_mensual = pd.DataFrame(datos_mensuales)
                
                # Gráfico de línea: Merma % por mes
                fig_merma_mensual = go.Figure()
                
                fig_merma_mensual.add_trace(go.Scatter(
                    x=df_mensual['mes'],
                    y=df_mensual['merma_pct'],
                    mode='lines+markers',
                    name='Merma %',
                    line=dict(color='#e74c3c', width=3),
                    marker=dict(size=8)
                ))
                
                fig_merma_mensual.update_layout(
                    title='Evolución de Merma Mensual (%)',
                    xaxis_title='Mes',
                    yaxis_title='Merma (%)',
                    hovermode='x unified',
                    yaxis=dict(ticksuffix='%')
                )
                
                st.plotly_chart(fig_merma_mensual, use_container_width=True)
                
                # Gráfico de línea: Kg comprados vs vendidos por mes
                fig_kg_mensual = go.Figure()
                
                fig_kg_mensual.add_trace(go.Scatter(
                    x=df_mensual['mes'],
                    y=df_mensual['compras_kg'],
                    mode='lines+markers',
                    name='Compras (kg)',
                    line=dict(color='#2ecc71', width=3),
                    marker=dict(size=8)
                ))
                
                fig_kg_mensual.add_trace(go.Scatter(
                    x=df_mensual['mes'],
                    y=df_mensual['ventas_kg'],
                    mode='lines+markers',
                    name='Ventas (kg)',
                    line=dict(color='#3498db', width=3),
                    marker=dict(size=8)
                ))
                
                fig_kg_mensual.update_layout(
                    title='Evolución Mensual: Compras vs Ventas (kg)',
                    xaxis_title='Mes',
                    yaxis_title='Kilogramos (kg)',
                    hovermode='x unified',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )
                
                st.plotly_chart(fig_kg_mensual, use_container_width=True)
                
                # Insight: Tendencia
                if len(df_mensual) >= 3:
                    merma_inicial = df_mensual.iloc[0]['merma_pct']
                    merma_final = df_mensual.iloc[-1]['merma_pct']
                    cambio_merma = merma_final - merma_inicial
                    
                    if cambio_merma < -2:
                        st.success(f"✅ **Tendencia positiva**: La merma ha mejorado en {abs(cambio_merma):.1f} puntos porcentuales")
                    elif cambio_merma > 2:
                        st.warning(f"⚠️ **Tendencia negativa**: La merma ha aumentado en {cambio_merma:.1f} puntos porcentuales")
                    else:
                        st.info("ℹ️ **Tendencia estable**: La merma se mantiene relativamente constante")
    
    # ============================================================================
    # COMPARATIVA AÑO VS AÑO
    # ============================================================================
    st.markdown("---")
    st.markdown("### 🔄 Comparativa Año vs Año")
    
    col_anio1, col_anio2, col_comparar = st.columns([2, 2, 1])
    
    with col_anio1:
        anio_base = st.selectbox(
            "Año Base",
            options=[2024, 2025, 2026],
            index=0,
            key="comparativa_anio_base"
        )
    
    with col_anio2:
        anio_comparar = st.selectbox(
            "Año a Comparar",
            options=[2024, 2025, 2026],
            index=1,
            key="comparativa_anio_comparar"
        )
    
    with col_comparar:
        st.markdown("<br>", unsafe_allow_html=True)
        ejecutar_comparativa = st.button("📊 Comparar", type="primary", use_container_width=True)
    
    if ejecutar_comparativa:
        if anio_base == anio_comparar:
            st.warning("⚠️ Selecciona dos años diferentes para comparar")
        else:
            with st.spinner(f"Comparando temporada {anio_base} vs {anio_comparar}..."):
                from .shared_analisis import get_comparativa_anual
                
                comparativa = get_comparativa_anual(
                    st.session_state.get('username', ''),
                    st.session_state.get('password', ''),
                    anio_base,
                    anio_comparar
                )
                
                if comparativa and not comparativa.get('error'):
                    df_comp = pd.DataFrame(comparativa)
                    
                    # Ordenar por delta de merma (mayor empeoramiento primero)
                    df_comp = df_comp.sort_values('delta_merma_pct', ascending=False)
                    
                    st.markdown(f"#### Comparativa: Temporada {anio_base} vs {anio_comparar}")
                    
                    # Formatear tabla
                    df_comp_display = df_comp.copy()
                    df_comp_display['Tipo Fruta'] = df_comp_display['tipo_fruta']
                    df_comp_display['Manejo'] = df_comp_display['manejo']
                    df_comp_display[f'Compras {anio_base} (kg)'] = df_comp_display[f'compras_kg_{anio_base}'].apply(lambda x: f"{x:,.0f}")
                    df_comp_display[f'Compras {anio_comparar} (kg)'] = df_comp_display[f'compras_kg_{anio_comparar}'].apply(lambda x: f"{x:,.0f}")
                    df_comp_display['Δ Compras (kg)'] = df_comp_display['delta_compras_kg'].apply(lambda x: f"{x:+,.0f}")
                    df_comp_display['Δ Compras (%)'] = df_comp_display['delta_compras_pct'].apply(lambda x: f"{x:+.1f}%")
                    df_comp_display[f'Ventas {anio_base} (kg)'] = df_comp_display[f'ventas_kg_{anio_base}'].apply(lambda x: f"{x:,.0f}")
                    df_comp_display[f'Ventas {anio_comparar} (kg)'] = df_comp_display[f'ventas_kg_{anio_comparar}'].apply(lambda x: f"{x:,.0f}")
                    df_comp_display['Δ Ventas (kg)'] = df_comp_display['delta_ventas_kg'].apply(lambda x: f"{x:+,.0f}")
                    df_comp_display['Δ Ventas (%)'] = df_comp_display['delta_ventas_pct'].apply(lambda x: f"{x:+.1f}%")
                    df_comp_display[f'Merma {anio_base} (%)'] = df_comp_display[f'merma_pct_{anio_base}'].apply(lambda x: f"{x:.2f}%")
                    df_comp_display[f'Merma {anio_comparar} (%)'] = df_comp_display[f'merma_pct_{anio_comparar}'].apply(lambda x: f"{x:.2f}%")
                    df_comp_display['Δ Merma (pp)'] = df_comp_display['delta_merma_pct'].apply(lambda x: f"{x:+.2f}")
                    
                    st.dataframe(
                        df_comp_display[[
                            'Tipo Fruta', 'Manejo',
                            f'Compras {anio_base} (kg)', f'Compras {anio_comparar} (kg)', 'Δ Compras (kg)', 'Δ Compras (%)',
                            f'Ventas {anio_base} (kg)', f'Ventas {anio_comparar} (kg)', 'Δ Ventas (kg)', 'Δ Ventas (%)',
                            f'Merma {anio_base} (%)', f'Merma {anio_comparar} (%)', 'Δ Merma (pp)'
                        ]],
                        use_container_width=True,
                        hide_index=True,
                        height=600
                    )
                    
                    # Gráfico de deltas de merma
                    fig_delta_merma = px.bar(
                        df_comp.head(10),
                        x='tipo_fruta',
                        y='delta_merma_pct',
                        color='delta_merma_pct',
                        color_continuous_scale=['green', 'yellow', 'red'],
                        title=f'Top 10: Cambio en Merma (puntos porcentuales) - {anio_base} vs {anio_comparar}',
                        labels={'tipo_fruta': 'Tipo de Fruta', 'delta_merma_pct': 'Cambio en Merma (pp)'},
                        text='delta_merma_pct'
                    )
                    
                    fig_delta_merma.update_traces(texttemplate='%{text:+.1f}pp', textposition='outside')
                    fig_delta_merma.update_layout(showlegend=False)
                    
                    st.plotly_chart(fig_delta_merma, use_container_width=True)
                    
                    # Insights
                    mejoras = df_comp[df_comp['delta_merma_pct'] < -2]
                    empeoramientos = df_comp[df_comp['delta_merma_pct'] > 2]
                    
                    col_m1, col_m2 = st.columns(2)
                    
                    with col_m1:
                        if len(mejoras) > 0:
                            st.success(f"✅ **{len(mejoras)} productos mejoraron** (merma reducida >2pp)")
                            for _, row in mejoras.head(3).iterrows():
                                st.caption(f"• {row['tipo_fruta']} {row['manejo']}: {row['delta_merma_pct']:+.1f}pp")
                        else:
                            st.info("ℹ️ No hay productos con mejora significativa de merma")
                    
                    with col_m2:
                        if len(empeoramientos) > 0:
                            st.warning(f"⚠️ **{len(empeoramientos)} productos empeoraron** (merma aumentó >2pp)")
                            for _, row in empeoramientos.head(3).iterrows():
                                st.caption(f"• {row['tipo_fruta']} {row['manejo']}: {row['delta_merma_pct']:+.1f}pp")
                        else:
                            st.success("✅ No hay productos con empeoramiento significativo de merma")
                
                else:
                    st.error(f"Error al obtener comparativa: {comparativa.get('error', 'Desconocido')}")


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
        hide_index=True,
        height=600
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
        hide_index=True,
        height=400
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

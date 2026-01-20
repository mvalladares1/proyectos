"""
Tab de Trazabilidad de Inventario: Compras, Ventas y Merma
Análisis de facturas de clientes y proveedores por categoría de producto
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
    """Renderiza el tab de trazabilidad de inventario."""
    
    st.subheader("📊 Trazabilidad de Inventario: Compras, Ventas y Merma")
    st.markdown("Análisis de facturas por tipo de fruta y categoría de manejo. **Solo productos clasificados.**")
    
    # Filtros de fecha
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fecha_desde = st.date_input(
            "Desde",
            value=datetime(2026, 1, 1),
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
    if not cargar_datos and 'inventario_data' not in st.session_state:
        st.info("ℹ️ Presiona 'Actualizar Datos' para cargar la información")
        return
    
    # Obtener datos
    if cargar_datos or 'inventario_data' not in st.session_state:
        with st.spinner("🔎 Cargando datos de facturas..."):
            from .shared import get_inventario_data
            st.session_state.inventario_data = get_inventario_data(
                username, password, 
                fecha_desde.strftime('%Y-%m-%d'),
                fecha_hasta.strftime('%Y-%m-%d')
            )
    
    data = st.session_state.inventario_data
    
    if data.get('error'):
        st.error(f"❌ {data['error']}")
        return
    
    # Mostrar período
    st.info(f"📅 Período analizado: **{data.get('fecha_desde', '')}** a **{data.get('fecha_hasta', '')}**")
    
    # Mostrar métricas principales
    st.markdown("### 📈 Resumen General")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Comprado",
            f"{data['total_comprado_kg']:,.0f} kg",
            f"${data['total_comprado_monto']:,.0f}",
            help="Suma de todas las facturas de proveedor"
        )
        st.caption(f"Precio promedio: **${data.get('total_comprado_precio_promedio', 0):,.2f}/kg**")
    
    with col2:
        st.metric(
            "Total Vendido",
            f"{data['total_vendido_kg']:,.0f} kg",
            f"${data['total_vendido_monto']:,.0f}",
            help="Suma de todas las facturas de cliente"
        )
        st.caption(f"Precio promedio: **${data.get('total_vendido_precio_promedio', 0):,.2f}/kg**")
    
    with col3:
        diferencia_kg = data['total_comprado_kg'] - data['total_vendido_kg']
        
        # Si la diferencia es positiva = tenemos inventario
        # Si es negativa = vendimos más de lo que compramos (hay inventario inicial)
        if diferencia_kg > 0:
            st.metric(
                "Inventario Final Teórico",
                f"{diferencia_kg:,.0f} kg",
                help="Stock que debería quedar (Comprado - Vendido)"
            )
            pct_sobre_compra = (diferencia_kg / data['total_comprado_kg'] * 100) if data['total_comprado_kg'] > 0 else 0
            st.caption(f"**{pct_sobre_compra:.1f}%** del total comprado")
        else:
            st.metric(
                "Inventario Inicial Usado",
                f"{abs(diferencia_kg):,.0f} kg",
                help="Vendimos más de lo comprado en el período (usamos inventario anterior)"
            )
            pct_sobre_venta = (abs(diferencia_kg) / data['total_vendido_kg'] * 100) if data['total_vendido_kg'] > 0 else 0
            st.caption(f"**{pct_sobre_venta:.1f}%** de lo vendido vino de inventario previo")
    
    with col4:
        # Calcular margen bruto (diferencia entre venta y compra en dinero)
        margen_monto = data['total_vendido_monto'] - data['total_comprado_monto']
        margen_pct = (margen_monto / data['total_vendido_monto'] * 100) if data['total_vendido_monto'] > 0 else 0
        
        st.metric(
            "Margen Bruto",
            f"${margen_monto:,.0f}",
            f"{margen_pct:.1f}%",
            help="Diferencia entre ingresos por venta y costo de compra"
        )
    
    # Mostrar tabla detallada
    st.markdown("### 📋 Detalle por Tipo de Fruta y Manejo")
    
    if data['detalle']:
        df = pd.DataFrame(data['detalle'])
        
        # Formatear columnas para display
        df_display = df.copy()
        df_display['Tipo Fruta'] = df['tipo_fruta']
        df_display['Manejo'] = df['manejo']
        df_display['Comprado (kg)'] = df['comprado_kg'].apply(lambda x: f"{x:,.2f}")
        df_display['Comprado ($)'] = df['comprado_monto'].apply(lambda x: f"${x:,.0f}")
        df_display['$/kg Compra'] = df['comprado_precio_promedio'].apply(lambda x: f"${x:,.2f}")
        df_display['Vendido (kg)'] = df['vendido_kg'].apply(lambda x: f"{x:,.2f}")
        df_display['Vendido ($)'] = df['vendido_monto'].apply(lambda x: f"${x:,.0f}")
        df_display['$/kg Venta'] = df['vendido_precio_promedio'].apply(lambda x: f"${x:,.2f}")
        df_display['Merma (kg)'] = df['merma_kg'].apply(lambda x: f"{x:,.2f}")
        df_display['% Merma'] = df['merma_pct'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(
            df_display[['Tipo Fruta', 'Manejo', 'Comprado (kg)', 'Comprado ($)', '$/kg Compra', 
                        'Vendido (kg)', 'Vendido ($)', '$/kg Venta', 'Merma (kg)', '% Merma']],
            use_container_width=True,
            hide_index=True
        )
        
        # Gráfico de barras
        st.markdown("### 📊 Visualización")
        
        tab_viz1, tab_viz2, tab_viz3 = st.tabs(["Por Tipo de Fruta", "Por Manejo", "Comparativo"])
        
        with tab_viz1:
            # Agrupar por tipo de fruta
            df_fruta = df.groupby('tipo_fruta').agg({
                'comprado_kg': 'sum',
                'vendido_kg': 'sum',
                'merma_kg': 'sum'
            }).reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Comprado',
                x=df_fruta['tipo_fruta'],
                y=df_fruta['comprado_kg'],
                marker_color='#4CAF50'
            ))
            fig.add_trace(go.Bar(
                name='Vendido',
                x=df_fruta['tipo_fruta'],
                y=df_fruta['vendido_kg'],
                marker_color='#2196F3'
            ))
            fig.add_trace(go.Bar(
                name='Merma',
                x=df_fruta['tipo_fruta'],
                y=df_fruta['merma_kg'],
                marker_color='#FF9800'
            ))
            
            fig.update_layout(
                title="Compras, Ventas y Merma por Tipo de Fruta (kg)",
                xaxis_title="Tipo de Fruta",
                yaxis_title="Kilogramos",
                barmode='group',
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab_viz2:
            # Agrupar por manejo
            df_manejo = df.groupby('manejo').agg({
                'comprado_kg': 'sum',
                'vendido_kg': 'sum',
                'merma_kg': 'sum'
            }).reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Comprado',
                x=df_manejo['manejo'],
                y=df_manejo['comprado_kg'],
                marker_color='#4CAF50'
            ))
            fig.add_trace(go.Bar(
                name='Vendido',
                x=df_manejo['manejo'],
                y=df_manejo['vendido_kg'],
                marker_color='#2196F3'
            ))
            fig.add_trace(go.Bar(
                name='Merma',
                x=df_manejo['manejo'],
                y=df_manejo['merma_kg'],
                marker_color='#FF9800'
            ))
            
            fig.update_layout(
                title="Compras, Ventas y Merma por Categoría de Manejo (kg)",
                xaxis_title="Categoría de Manejo",
                yaxis_title="Kilogramos",
                barmode='group',
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab_viz3:
            # Sunburst: Tipo Fruta > Manejo > Movimiento
            df_sunburst = []
            for _, row in df.iterrows():
                # Compras
                df_sunburst.append({
                    'tipo_fruta': row['tipo_fruta'],
                    'manejo': row['manejo'],
                    'movimiento': 'Comprado',
                    'valor': row['comprado_kg']
                })
                # Ventas
                df_sunburst.append({
                    'tipo_fruta': row['tipo_fruta'],
                    'manejo': row['manejo'],
                    'movimiento': 'Vendido',
                    'valor': row['vendido_kg']
                })
            
            df_sun = pd.DataFrame(df_sunburst)
            
            fig = px.sunburst(
                df_sun,
                path=['movimiento', 'tipo_fruta', 'manejo'],
                values='valor',
                title="Distribución de Compras y Ventas (kg)",
                height=600
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("ℹ️ No se encontraron datos para el periodo seleccionado")

"""
Tab de Análisis de Inventario y Rotación
Último módulo del sistema de análisis completo
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
    """Renderiza el tab de análisis de inventario."""
    
    st.subheader("📊 Análisis de Inventario y Rotación")
    st.markdown("Análisis de stock actual, rotación y alertas de inventario.")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fecha_desde = st.date_input("Desde", value=datetime(2025, 11, 1), format="DD/MM/YYYY", key="inv_desde")
    
    with col2:
        fecha_hasta = st.date_input("Hasta", value=datetime(2026, 1, 31), format="DD/MM/YYYY", key="inv_hasta")
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        cargar_datos = st.button("🔄 Actualizar Datos", type="primary", use_container_width=True, key="inv_cargar")
    
    if not cargar_datos and 'inventario_data' not in st.session_state:
        st.info("ℹ️ Presiona 'Actualizar Datos' para cargar la información")
        return
    
    if cargar_datos or 'inventario_data' not in st.session_state:
        with st.spinner("🔎 Cargando datos de inventario..."):
            from .shared_analisis import get_inventario_rotacion_data
            st.session_state.inventario_data = get_inventario_rotacion_data(
                username, password,
                fecha_desde.strftime('%Y-%m-%d'),
                fecha_hasta.strftime('%Y-%m-%d')
            )
    
    data = st.session_state.inventario_data
    
    if data.get('error'):
        st.error(f"❌ {data['error']}")
        return
    
    st.info(f"📅 Período: **{data.get('fecha_desde', '')}** a **{data.get('fecha_hasta', '')}** ({data.get('dias_periodo', 0)} días)")
    
    # Resumen
    st.markdown("### 📊 Resumen de Inventario")
    resumen = data.get('resumen', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Stock Total", f"{resumen.get('stock_total_kg', 0):,.0f} kg")
    
    with col2:
        st.metric("Valorización", f"${resumen.get('valor_total', 0):,.0f}")
    
    with col3:
        st.metric("Productos", f"{resumen.get('productos_con_stock', 0):,}")
    
    with col4:
        st.metric("Ubicaciones", f"{resumen.get('ubicaciones', 0):,}")
    
    # Stock por ubicación
    st.markdown("### 📍 Stock por Ubicación")
    por_ubic = data.get('por_ubicacion', [])
    
    if por_ubic:
        df_ubic = pd.DataFrame(por_ubic)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            fig_ubic = px.pie(
                df_ubic.head(10),
                values='kg',
                names='ubicacion',
                title='Distribución de Stock por Ubicación',
                hole=0.4
            )
            st.plotly_chart(fig_ubic, use_container_width=True)
        
        with col2:
            df_ubic['%'] = df_ubic['porcentaje'].apply(lambda x: f"{x:.1f}%")
            df_ubic['Valor'] = df_ubic['valor'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(
                df_ubic[['ubicacion', 'kg', 'Valor', '%']].head(10),
                use_container_width=True,
                hide_index=True
            )
    
    # Top productos con rotación
    st.markdown("### 📦 Top Productos (por valor de stock)")
    por_prod = data.get('por_producto', [])
    
    if por_prod:
        df_prod = pd.DataFrame(por_prod)
        
        # Gráfico de barras
        fig_prod = px.bar(
            df_prod.head(10),
            x='valor_stock',
            y='producto',
            orientation='h',
            title='Top 10 Productos por Valor de Stock',
            labels={'valor_stock': 'Valor CLP', 'producto': 'Producto'},
            text='valor_stock'
        )
        fig_prod.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_prod, use_container_width=True)
        
        # Tabla con rotación
        st.markdown("#### Detalle con Rotación")
        
        df_prod['Stock'] = df_prod['stock_kg'].apply(lambda x: f"{x:,.0f} kg")
        df_prod['Valor'] = df_prod['valor_stock'].apply(lambda x: f"${x:,.0f}")
        df_prod['Salidas'] = df_prod['salidas_periodo'].apply(lambda x: f"{x:,.0f} kg")
        df_prod['Días Inv.'] = df_prod['dias_inventario'].apply(lambda x: f"{int(x)}" if x < 999 else "999+")
        
        # Colorear por rotación
        def color_rotacion(val):
            try:
                dias = int(val)
                if dias > 90:
                    return 'background-color: #ffcccc'  # Rojo claro
                elif dias > 60:
                    return 'background-color: #ffffcc'  # Amarillo
                else:
                    return 'background-color: #ccffcc'  # Verde claro
            except:
                return ''
        
        st.dataframe(
            df_prod[['producto', 'tipo_fruta', 'categoria', 'Stock', 'Valor', 'Salidas', 'rotacion', 'Días Inv.']].head(20),
            use_container_width=True,
            hide_index=True
        )
        
        st.caption("""
        **Interpretación:**
        - 🟢 **< 60 días**: Rotación buena
        - 🟡 **60-90 días**: Rotación normal
        - 🔴 **> 90 días**: Rotación lenta
        - **999+**: Sin salidas en período
        """)
    
    # Alertas
    st.markdown("### ⚠️ Alertas de Inventario")
    alertas = data.get('alertas', [])
    
    if alertas:
        # Contar tipos de alertas
        count_lento = len([a for a in alertas if a.get('tipo') == 'stock_lento'])
        count_sin_mov = len([a for a in alertas if a.get('tipo') == 'sin_movimiento'])
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("🐌 Stock Lento", count_lento, help="Productos con más de 90 días de stock")
        
        with col2:
            st.metric("❌ Sin Movimiento", count_sin_mov, help="Productos sin salidas en período")
        
        # Mostrar alertas
        st.markdown("#### Detalle de Alertas")
        
        tab1, tab2 = st.tabs(["🐌 Stock Lento", "❌ Sin Movimiento"])
        
        with tab1:
            alertas_lento = [a for a in alertas if a.get('tipo') == 'stock_lento']
            if alertas_lento:
                for alerta in alertas_lento[:10]:
                    st.warning(f"**{alerta.get('producto', '')}**: {alerta.get('mensaje', '')}")
            else:
                st.success("✅ No hay productos con rotación lenta")
        
        with tab2:
            alertas_sin_mov = [a for a in alertas if a.get('tipo') == 'sin_movimiento']
            if alertas_sin_mov:
                for alerta in alertas_sin_mov[:10]:
                    st.error(f"**{alerta.get('producto', '')}**: {alerta.get('mensaje', '')}")
            else:
                st.success("✅ Todos los productos tienen movimiento")
    else:
        st.success("✅ No hay alertas de inventario")
    
    # Análisis de rotación por categoría
    st.markdown("### 📊 Análisis de Rotación por Categoría")
    
    if por_prod:
        df_cat = pd.DataFrame(por_prod)
        
        # Agrupar por categoría
        cat_group = df_cat.groupby('categoria').agg({
            'stock_kg': 'sum',
            'valor_stock': 'sum',
            'rotacion': 'mean',
            'dias_inventario': 'mean'
        }).reset_index()
        
        cat_group = cat_group.sort_values('valor_stock', ascending=False)
        
        # Gráfico de rotación por categoría
        fig_cat = go.Figure()
        
        fig_cat.add_trace(go.Bar(
            name='Días de Inventario',
            x=cat_group['categoria'],
            y=cat_group['dias_inventario'],
            marker_color='#ff7f0e'
        ))
        
        fig_cat.update_layout(
            title='Días de Inventario Promedio por Categoría',
            xaxis_title='Categoría',
            yaxis_title='Días',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_cat, use_container_width=True)
        
        # Tabla
        cat_group['Stock'] = cat_group['stock_kg'].apply(lambda x: f"{x:,.0f} kg")
        cat_group['Valor'] = cat_group['valor_stock'].apply(lambda x: f"${x:,.0f}")
        cat_group['Rotación'] = cat_group['rotacion'].apply(lambda x: f"{x:.2f}")
        cat_group['Días'] = cat_group['dias_inventario'].apply(lambda x: f"{int(x)}" if x < 999 else "999+")
        
        st.dataframe(
            cat_group[['categoria', 'Stock', 'Valor', 'Rotación', 'Días']],
            use_container_width=True,
            hide_index=True
        )

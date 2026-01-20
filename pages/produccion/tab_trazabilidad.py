"""
Tab de Trazabilidad: Análisis de compras, ventas y merma por tipo de fruta y manejo
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

def render(username: str, password: str):
    """
    Renderiza el tab de trazabilidad con análisis de:
    - Compras por categoría de manejo y tipo de fruta
    - Ventas por categoría de manejo y tipo de fruta
    - Cálculo de merma
    - Inventario teórico a fin de año
    """
    
    st.subheader("📊 Trazabilidad de Inventario")
    st.caption("Análisis de compras, ventas y merma por tipo de fruta y categoría de manejo")
    
    # Filtros principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        año_seleccionado = st.selectbox(
            "Año",
            options=[2024, 2025, 2026],
            index=1  # 2025 por defecto
        )
    
    with col2:
        # Obtener tipos de fruta desde Odoo
        tipos_fruta = ["Todos", "Arándano", "Frambuesa", "Frutilla", "Mix", "Mora"]
        tipo_seleccionado = st.selectbox(
            "Tipo de Fruta",
            options=tipos_fruta
        )
    
    with col3:
        # Categorías de manejo
        manejos = ["Todos", "Convencional", "Orgánico"]
        manejo_seleccionado = st.selectbox(
            "Categoría de Manejo",
            options=manejos
        )
    
    # Fecha de corte para análisis de merma
    st.info("💡 **Análisis de Merma**: Se calculará sumando compras y ventas hasta fin de octubre para estimar merma anual")
    
    fecha_corte = st.date_input(
        "Fecha de corte para análisis",
        value=datetime(año_seleccionado, 10, 31),
        min_value=datetime(año_seleccionado, 1, 1),
        max_value=datetime(año_seleccionado, 12, 31)
    )
    
    if st.button("🔍 Analizar", type="primary"):
        with st.spinner("Consultando datos de Odoo..."):
            # Aquí irá la lógica de consulta
            st.info("Funcionalidad en desarrollo - Conectando con backend service")
            
            # Placeholder de datos de ejemplo
            st.success("✅ Datos cargados correctamente")
            
            # Tabs para diferentes vistas
            tab1, tab2, tab3, tab4 = st.tabs([
                "📈 Resumen General",
                "🛒 Compras",
                "💰 Ventas",
                "⚠️ Merma e Inventario"
            ])
            
            with tab1:
                render_resumen_general()
            
            with tab2:
                render_compras()
            
            with tab3:
                render_ventas()
            
            with tab4:
                render_merma_inventario()


def render_resumen_general():
    """Resumen general con KPIs principales"""
    st.subheader("📊 Resumen General")
    
    # KPIs en columnas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Comprado",
            "1,234,567 kg",
            "+15% vs año anterior"
        )
    
    with col2:
        st.metric(
            "Total Vendido",
            "1,100,000 kg",
            "+12% vs año anterior"
        )
    
    with col3:
        st.metric(
            "Merma Estimada",
            "134,567 kg",
            "10.9% del total"
        )
    
    with col4:
        st.metric(
            "Inventario Teórico",
            "234,567 kg",
            "A fin de octubre"
        )
    
    st.divider()
    
    # Gráfico de evolución mensual
    st.subheader("Evolución Mensual")
    
    # Datos de ejemplo
    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    compras = [100000, 120000, 150000, 180000, 200000, 220000, 180000, 160000, 140000, 120000, 100000, 80000]
    ventas = [80000, 100000, 130000, 160000, 180000, 200000, 170000, 150000, 130000, 110000, 90000, 70000]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=meses, y=compras, mode='lines+markers', name='Compras', line=dict(color='#2E86AB')))
    fig.add_trace(go.Scatter(x=meses, y=ventas, mode='lines+markers', name='Ventas', line=dict(color='#A23B72')))
    
    fig.update_layout(
        title="Compras vs Ventas Mensual",
        xaxis_title="Mes",
        yaxis_title="Cantidad (kg)",
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_compras():
    """Vista detallada de compras"""
    st.subheader("🛒 Análisis de Compras")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico por tipo de fruta
        st.subheader("Por Tipo de Fruta")
        data_tipos = {
            'Tipo': ['Arándano', 'Frambuesa', 'Frutilla', 'Mix', 'Mora'],
            'Cantidad': [500000, 300000, 200000, 150000, 84567]
        }
        df_tipos = pd.DataFrame(data_tipos)
        
        fig = px.pie(df_tipos, values='Cantidad', names='Tipo', title='Distribución por Tipo de Fruta')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Gráfico por manejo
        st.subheader("Por Categoría de Manejo")
        data_manejo = {
            'Manejo': ['Convencional', 'Orgánico'],
            'Cantidad': [800000, 434567]
        }
        df_manejo = pd.DataFrame(data_manejo)
        
        fig = px.pie(df_manejo, values='Cantidad', names='Manejo', title='Distribución por Manejo')
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Tabla detallada
    st.subheader("Detalle de Compras")
    
    data_detalle = {
        'Tipo Fruta': ['Arándano', 'Arándano', 'Frambuesa', 'Frambuesa', 'Frutilla'],
        'Manejo': ['Convencional', 'Orgánico', 'Convencional', 'Orgánico', 'Convencional'],
        'Cantidad (kg)': [300000, 200000, 180000, 120000, 200000],
        'Valor Total': [1500000, 1200000, 900000, 720000, 800000],
        'Precio Promedio': [5.0, 6.0, 5.0, 6.0, 4.0]
    }
    df_detalle = pd.DataFrame(data_detalle)
    
    st.dataframe(
        df_detalle,
        use_container_width=True,
        hide_index=True
    )


def render_ventas():
    """Vista detallada de ventas"""
    st.subheader("💰 Análisis de Ventas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico por tipo de fruta
        st.subheader("Por Tipo de Fruta")
        data_tipos = {
            'Tipo': ['Arándano', 'Frambuesa', 'Frutilla', 'Mix', 'Mora'],
            'Cantidad': [450000, 270000, 180000, 130000, 70000]
        }
        df_tipos = pd.DataFrame(data_tipos)
        
        fig = px.pie(df_tipos, values='Cantidad', names='Tipo', title='Distribución por Tipo de Fruta')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Gráfico por manejo
        st.subheader("Por Categoría de Manejo")
        data_manejo = {
            'Manejo': ['Convencional', 'Orgánico'],
            'Cantidad': [720000, 380000]
        }
        df_manejo = pd.DataFrame(data_manejo)
        
        fig = px.pie(df_manejo, values='Cantidad', names='Manejo', title='Distribución por Manejo')
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Tabla detallada
    st.subheader("Detalle de Ventas")
    
    data_detalle = {
        'Tipo Fruta': ['Arándano', 'Arándano', 'Frambuesa', 'Frambuesa', 'Frutilla'],
        'Manejo': ['Convencional', 'Orgánico', 'Convencional', 'Orgánico', 'Convencional'],
        'Cantidad (kg)': [270000, 180000, 162000, 108000, 180000],
        'Valor Total': [2700000, 2160000, 1620000, 1296000, 1440000],
        'Precio Promedio': [10.0, 12.0, 10.0, 12.0, 8.0]
    }
    df_detalle = pd.DataFrame(data_detalle)
    
    st.dataframe(
        df_detalle,
        use_container_width=True,
        hide_index=True
    )


def render_merma_inventario():
    """Análisis de merma e inventario teórico"""
    st.subheader("⚠️ Análisis de Merma e Inventario Teórico")
    
    st.info("""
    **Metodología:**
    - Se suman todas las compras hasta la fecha de corte (fin de octubre)
    - Se suman todas las ventas hasta la fecha de corte
    - Merma = Compras - Ventas - Inventario Real (si disponible)
    - Inventario Teórico = Compras - Ventas (sin considerar merma histórica)
    """)
    
    # Tabla de análisis
    st.subheader("Análisis por Tipo de Fruta y Manejo")
    
    data_analisis = {
        'Tipo Fruta': ['Arándano', 'Arándano', 'Frambuesa', 'Frambuesa', 'Frutilla'],
        'Manejo': ['Conv.', 'Org.', 'Conv.', 'Org.', 'Conv.'],
        'Compras (kg)': [300000, 200000, 180000, 120000, 200000],
        'Ventas (kg)': [270000, 180000, 162000, 108000, 180000],
        'Inventario Teórico (kg)': [30000, 20000, 18000, 12000, 20000],
        'Merma Estimada (kg)': [3000, 2000, 1800, 1200, 2000],
        '% Merma': ['10.0%', '10.0%', '10.0%', '10.0%', '10.0%']
    }
    df_analisis = pd.DataFrame(data_analisis)
    
    st.dataframe(
        df_analisis,
        use_container_width=True,
        hide_index=True
    )
    
    st.divider()
    
    # Gráfico de merma
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Distribución de Merma")
        fig = px.bar(
            df_analisis,
            x='Tipo Fruta',
            y='Merma Estimada (kg)',
            color='Manejo',
            title='Merma por Tipo de Fruta y Manejo',
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Inventario Teórico")
        fig = px.bar(
            df_analisis,
            x='Tipo Fruta',
            y='Inventario Teórico (kg)',
            color='Manejo',
            title='Inventario Teórico a Fin de Octubre',
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Exportar resultados
    st.divider()
    st.subheader("📥 Exportar Resultados")
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📊 Descargar Excel",
            data="",  # Aquí iría el Excel generado
            file_name=f"trazabilidad_inventario_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            disabled=True  # Por ahora deshabilitado
        )
    
    with col2:
        st.download_button(
            "📄 Descargar CSV",
            data=df_analisis.to_csv(index=False),
            file_name=f"trazabilidad_inventario_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

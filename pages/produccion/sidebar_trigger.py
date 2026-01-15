"""
Sidebar para Trigger SO Asociada.
Contiene filtros y configuración.
"""
import streamlit as st
from datetime import datetime, timedelta


def render():
    """Renderiza el sidebar con filtros."""
    st.sidebar.header("⚙️ Configuración")
    
    # Rango de fechas
    st.sidebar.subheader("📅 Rango de Fechas")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        fecha_inicio = st.date_input(
            "Desde",
            value=datetime.now().date() - timedelta(days=7),
            help="Fecha inicio de búsqueda",
            key="trigger_fecha_inicio"
        )
    
    with col2:
        fecha_fin = st.date_input(
            "Hasta",
            value=datetime.now().date(),
            help="Fecha fin de búsqueda",
            key="trigger_fecha_fin"
        )
    
    st.sidebar.divider()
    
    # Configuración de ejecución
    st.sidebar.subheader("⚡ Configuración")
    
    wait_seconds = st.sidebar.slider(
        "Espera entre operaciones",
        min_value=1.0,
        max_value=5.0,
        value=2.0,
        step=0.5,
        help="Segundos entre borrar y reescribir PO Cliente",
        key="trigger_wait_seconds"
    )
    
    limit = st.sidebar.number_input(
        "Límite de ODFs",
        min_value=1,
        max_value=200,
        value=50,
        help="Máximo de ODFs a procesar",
        key="trigger_limit"
    )
    
    st.sidebar.divider()
    
    # Botón de búsqueda
    buscar = st.sidebar.button(
        "🔍 Buscar ODFs Pendientes",
        type="primary",
        use_container_width=True,
        key="trigger_buscar_btn"
    )
    
    return {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'wait_seconds': wait_seconds,
        'limit': limit,
        'buscar': buscar
    }

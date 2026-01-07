"""
Contenido principal del dashboard de Trazabilidad.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from .shared import fmt_numero, get_trazabilidad_inversa, get_sankey_data


def render(username: str, password: str):
    """Renderiza el contenido principal del dashboard."""
    
    # Sidebar - Filtros de fecha para Sankey
    st.sidebar.header("📅 Período para Diagrama")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        fecha_inicio = st.date_input(
            "Desde",
            datetime.now() - timedelta(days=30),
            format="DD/MM/YYYY"
        )
    with col2:
        fecha_fin = st.date_input(
            "Hasta",
            datetime.now(),
            format="DD/MM/YYYY"
        )
    
    # Tabs
    tab1, tab2 = st.tabs(["📦 Trazabilidad por Pallets", "🔗 Diagrama Sankey"])
    
    with tab1:
        _render_trazabilidad(username, password)
    
    with tab2:
        _render_sankey(username, password, fecha_inicio, fecha_fin)


def _render_trazabilidad(username: str, password: str):
    """Renderiza el tab de trazabilidad inversa por pallets."""
    st.subheader("📦 Trazabilidad Completa: Pallet → Productor")
    st.markdown("Rastrea uno o varios pallets desde el producto terminado hasta el productor original.")
    
    # Sección de búsqueda
    st.markdown("### 🔍 Buscar Pallets")
    
    # Opciones de entrada
    modo = st.radio(
        "Modo de entrada:",
        ["📝 Ingresar uno por uno", "📋 Pegar lista (separada por comas o líneas)"],
        horizontal=True
    )
    
    pallets = []
    
    if modo == "📝 Ingresar uno por uno":
        col1, col2 = st.columns([3, 1])
        with col1:
            pallet_input = st.text_input(
                "Nombre del Pallet",
                placeholder="Ej: PALLET-RF-2024-0156",
                key="pallet_single"
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Agregar", use_container_width=True):
                if pallet_input and pallet_input not in st.session_state.get('pallets_list', []):
                    if 'pallets_list' not in st.session_state:
                        st.session_state.pallets_list = []
                    st.session_state.pallets_list.append(pallet_input.strip())
                    st.rerun()
        
        # Mostrar pallets agregados
        if 'pallets_list' in st.session_state and st.session_state.pallets_list:
            st.markdown("**Pallets agregados:**")
            cols = st.columns([4, 1])
            for idx, p in enumerate(st.session_state.pallets_list):
                with cols[0]:
                    st.write(f"{idx + 1}. {p}")
                with cols[1]:
                    if st.button(f"🗑️", key=f"del_{idx}"):
                        st.session_state.pallets_list.remove(p)
                        st.rerun()
            pallets = st.session_state.pallets_list
    else:
        pallets_text = st.text_area(
            "Lista de Pallets",
            placeholder="PALLET-001\nPALLET-002, PALLET-003\nPALLET-004",
            height=150,
            help="Separa los pallets por comas o líneas nuevas"
        )
        if pallets_text:
            # Separar por comas o líneas
            import re
            pallets = [p.strip() for p in re.split(r'[,\n]+', pallets_text) if p.strip()]
            st.info(f"🔢 {len(pallets)} pallet(s) detectado(s)")
    
    # Botón de búsqueda
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔍 Rastrear Trazabilidad", type="primary", use_container_width=True):
            if not pallets:
                st.warning("⚠️ Ingresa al menos un pallet")
                return
            
            with st.spinner(f"🔎 Rastreando {len(pallets)} pallet(s)..."):
                from .shared import get_trazabilidad_pallets
                resultado = get_trazabilidad_pallets(username, password, pallets)
                
                if resultado.get('error'):
                    st.error(f"❌ {resultado['error']}")
                    return
                
                # Guardar en session state
                st.session_state.trazabilidad_resultado = resultado
                st.rerun()
    
    # Botón para limpiar
    if 'pallets_list' in st.session_state and st.session_state.pallets_list:
        with col3:
            if st.button("🧹 Limpiar", use_container_width=True):
                st.session_state.pallets_list = []
                st.rerun()
    
    # Mostrar resultados
    if 'trazabilidad_resultado' in st.session_state:
        resultado = st.session_state.trazabilidad_resultado
        
        st.markdown("---")
        st.markdown(f"## 📊 Resultados ({resultado['pallets_rastreados']} pallet(s))")
        
        # Mostrar cada pallet
        for pallet_data in resultado['pallets']:
            _render_pallet_trazabilidad(pallet_data)


def _render_pallet_trazabilidad(pallet_data: dict):
    """Renderiza la trazabilidad de un pallet individual."""
    
    pallet_name = pallet_data.get('pallet', 'N/A')
    
    # Verificar si hay error
    if pallet_data.get('error'):
        with st.expander(f"❌ {pallet_name}", expanded=False):
            st.error(f"Error: {pallet_data['error']}")
        return
    
    # Pallet exitoso
    resumen = pallet_data.get('resumen', {})
    cadena = pallet_data.get('cadena', [])
    
    # Título del pallet
    with st.expander(f"✅ {pallet_name} - {pallet_data.get('producto_pt', 'N/A')}", expanded=True):
        
        # KPIs del pallet
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Kg PT", fmt_numero(pallet_data.get('kg_pt', 0), 2))
        with col2:
            st.metric("Kg MP Total", fmt_numero(resumen.get('kg_mp_total', 0), 2))
        with col3:
            rendimiento = resumen.get('rendimiento_total', 0)
            st.metric("Rendimiento", f"{rendimiento}%")
        with col4:
            merma = resumen.get('merma_kg', 0)
            st.metric("Merma", f"{fmt_numero(merma, 2)} kg")
        
        st.markdown("---")
        
        # Información del lote PT
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**📦 Lote PT:** {pallet_data.get('lote_pt', 'N/A')}")
        with col2:
            st.markdown(f"**🏭 Total Procesos:** {resumen.get('total_procesos', 0)}")
        
        # Productores origen
        if resumen.get('productores'):
            st.markdown("**👨‍🌾 Productores Origen:**")
            for prod in resumen['productores']:
                st.markdown(f"- {prod}")
        
        st.markdown("---")
        st.markdown("### 🔗 Cadena de Trazabilidad")
        
        # Organizar cadena por niveles
        niveles = {}
        for registro in cadena:
            nivel = registro.get('nivel', 0)
            if nivel not in niveles:
                niveles[nivel] = []
            niveles[nivel].append(registro)
        
        # Mostrar por niveles (de 0 a N)
        for nivel in sorted(niveles.keys()):
            registros = niveles[nivel]
            
            for registro in registros:
                tipo = registro.get('tipo', '')
                
                if tipo == 'PROCESO':
                    _render_proceso(registro, nivel)
                elif tipo == 'MATERIA_PRIMA':
                    _render_materia_prima(registro, nivel)


def _render_proceso(registro: dict, nivel: int):
    """Renderiza un registro de proceso."""
    indent = "  " * nivel
    
    # Cabecera del proceso
    sala = registro.get('sala', 'N/A')
    mo_name = registro.get('mo_name', 'N/A')
    fecha = registro.get('fecha_mo', 'N/A')
    
    st.markdown(f"{indent}**🏭 PROCESO - Nivel {nivel}**")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"{indent}- **Sala:** {sala}")
        st.markdown(f"{indent}- **MO:** {mo_name}")
        st.markdown(f"{indent}- **Lote:** {registro.get('lot_name', 'N/A')}")
    with col2:
        st.markdown(f"{indent}- **Fecha:** {fecha}")
        kg_consumido = registro.get('total_kg_consumido', 0)
        st.markdown(f"{indent}- **Total consumido:** {fmt_numero(kg_consumido, 2)} kg")
    
    # Consumos del proceso
    consumos = registro.get('consumos', [])
    if consumos:
        st.markdown(f"{indent}  **📥 Consumió:**")
        for c in consumos:
            st.markdown(
                f"{indent}    - {c['lot_name']}: {fmt_numero(c['qty_done'], 2)} kg ({c['product_name'][:60]}...)"
            )
    
    st.markdown("")  # Espacio


def _render_materia_prima(registro: dict, nivel: int):
    """Renderiza un registro de materia prima."""
    indent = "  " * nivel
    
    st.markdown(f"{indent}**🌾 MATERIA PRIMA - Nivel {nivel} (ORIGEN)**")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"{indent}- **Lote MP:** {registro.get('lot_name', 'N/A')}")
        st.markdown(f"{indent}- **Producto:** {registro.get('product_name', 'N/A')[:60]}")
        st.markdown(f"{indent}- **👨‍🌾 Productor:** {registro.get('productor', 'N/A')}")
    with col2:
        st.markdown(f"{indent}- **Fecha recepción:** {registro.get('fecha_recepcion', 'N/A')}")
    
    st.markdown("")  # Espacio



def _render_sankey(username: str, password: str, fecha_inicio, fecha_fin):
    """Renderiza el tab del diagrama Sankey."""
    st.subheader("🔗 Diagrama Sankey: Container → Fabricación → Pallets")
    st.caption("Visualización del flujo de containers, fabricaciones y pallets")
    
    if st.button("🔄 Generar Diagrama", type="primary"):
        with st.spinner("Generando diagrama Sankey..."):
            sankey_data = get_sankey_data(
                username, password,
                fecha_inicio.strftime("%Y-%m-%d"),
                fecha_fin.strftime("%Y-%m-%d")
            )
            
            if not sankey_data:
                st.error("Error al obtener datos del servidor")
                return
            
            if not sankey_data.get('nodes') or not sankey_data.get('links'):
                st.warning("No hay datos suficientes para generar el diagrama en el período seleccionado.")
                return
            
            # Crear figura Sankey
            fig = go.Figure(data=[go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=[n["label"] for n in sankey_data["nodes"]],
                    color=[n["color"] for n in sankey_data["nodes"]],
                    customdata=[n.get("detail", "") for n in sankey_data["nodes"]],
                    hovertemplate="%{label}<br>%{customdata}<extra></extra>"
                ),
                link=dict(
                    source=[l["source"] for l in sankey_data["links"]],
                    target=[l["target"] for l in sankey_data["links"]],
                    value=[l["value"] for l in sankey_data["links"]]
                )
            )])
            
            fig.update_layout(
                title="Flujo: Container → Fabricación → Pallets",
                height=700,
                font=dict(size=10)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Estadísticas
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Containers", len([n for n in sankey_data["nodes"] if n["color"] == "#3498db"]))
            with col2:
                st.metric("Fabricaciones", len([n for n in sankey_data["nodes"] if n["color"] == "#e74c3c"]))
            with col3:
                total_pallets = len([n for n in sankey_data["nodes"] if n["color"] in ["#f39c12", "#2ecc71"]])
                st.metric("Pallets", total_pallets)
            
            # Leyenda
            st.markdown("##### Leyenda:")
            st.markdown("🔵 Containers | 🔴 Fabricaciones | 🟠 Pallets IN | 🟢 Pallets OUT")
    else:
        st.info("👆 Selecciona las fechas en el sidebar y haz clic en **Generar Diagrama**")

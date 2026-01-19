"""
Contenido principal del dashboard de Trazabilidad.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared.auth import tiene_acceso_pagina

from .shared import (
    fmt_numero,
    get_trazabilidad_inversa,
    get_sankey_data,
    get_reactflow_data,
    get_traceability_raw,
    get_container_partners,
    get_sankey_producers
)

# Importar componente Timeline Flow
try:
    from components.timeline_flow import render_timeline_flow, render_simple_flow
    from components.timeline_flow.component import FLOW_AVAILABLE
    TIMELINE_FLOW_AVAILABLE = FLOW_AVAILABLE
except ImportError:
    TIMELINE_FLOW_AVAILABLE = False
    render_timeline_flow = None
    render_simple_flow = None

# Importar componente vis.js Network
try:
    from components.visjs_network import (
        render_visjs_network,
        render_visjs_timeline,
        render_combined_view,
        PYVIS_AVAILABLE,
    )
    VISJS_AVAILABLE = PYVIS_AVAILABLE
except ImportError:
    VISJS_AVAILABLE = False
    render_visjs_network = None
    render_visjs_timeline = None
    render_combined_view = None


def render(username: str, password: str):
    """Renderiza el contenido principal del dashboard."""
    
    # Pre-calcular permisos
    _perm_trazabilidad = tiene_acceso_pagina("rendimiento", "trazabilidad_pallets")
    _perm_sankey = tiene_acceso_pagina("rendimiento", "diagrama_sankey")
    
    # Tabs
    tab1, tab2 = st.tabs(["📦 Trazabilidad por Pallets", "🔗 Diagrama Sankey"])
    
    with tab1:
        if _perm_trazabilidad:
            _render_trazabilidad(username, password)
        else:
            st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Trazabilidad por Pallets'. Contacta al administrador.")
    
    with tab2:
        if _perm_sankey:
            _render_sankey(username, password)
        else:
            st.error("🚫 **Acceso Restringido** - No tienes permisos para ver 'Diagrama Sankey'. Contacta al administrador.")


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



def _render_sankey(username: str, password: str):
    """Renderiza el tab del diagrama de trazabilidad."""
    st.subheader("🔗 Diagrama de Trazabilidad")
    
    # Selector de tipo de diagrama
    st.markdown("### 📊 Tipo de Visualización")
    
    diagram_types = ["📈 Sankey (Plotly)", "� Tabla de Conexiones"]
    
    # Agregar opciones dinámicamente según disponibilidad
    if VISJS_AVAILABLE:
        diagram_types.insert(2 if TIMELINE_FLOW_AVAILABLE else 1, "🕸️ vis.js Network")
    
    diagram_type = st.radio(
        "Selecciona el tipo de diagrama:",
        diagram_types,
        horizontal=True,
        key="diagram_type_selector"
    )
    
    st.markdown("---")
    st.markdown("### 📅 Período para Diagrama")
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input(
            "Desde",
            datetime(2025, 12, 1),
            format="DD/MM/YYYY",
            key="sankey_fecha_inicio",
        )
    with col2:
        fecha_fin = st.date_input(
            "Hasta",
            datetime.now(),
            format="DD/MM/YYYY",
            key="sankey_fecha_fin",
        )

    # Filtro de productor (deshabilitado temporalmente)
    # TODO: Implementar filtro por productor buscando pallet por pallet
    st.caption("🔒 Filtro de productor disponible próximamente")
    
    # Inicializar session_state para datos de diagrama
    if "diagram_data" not in st.session_state:
        st.session_state.diagram_data = None
    if "diagram_data_type" not in st.session_state:
        st.session_state.diagram_data_type = None
    
    if st.button("🔄 Generar Diagrama", type="primary"):
        spinner_msg = "Obteniendo datos de trazabilidad..."
        
        with st.spinner(spinner_msg):
            fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
            fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")
            
            # Obtener datos según el tipo de diagrama
            if diagram_type == "📈 Sankey (Plotly)":
                data = get_sankey_data(username, password, fecha_inicio_str, fecha_fin_str)
                if not data or not data.get('nodes'):
                    st.warning("No hay datos suficientes para generar el diagrama en el período seleccionado.")
                    st.session_state.diagram_data = None
                    return
                st.session_state.diagram_data = data
                st.session_state.diagram_data_type = "sankey"
            
            elif diagram_type == "🕸️ vis.js Network" and VISJS_AVAILABLE:
                # Obtener datos crudos y transformar a vis.js
                raw_data = get_traceability_raw(username, password, fecha_inicio_str, fecha_fin_str)
                if not raw_data or not raw_data.get('pallets'):
                    st.warning("No hay datos suficientes para generar el diagrama en el período seleccionado.")
                    st.session_state.diagram_data = None
                    return
                # Transformar a formato vis.js
                from backend.services.traceability import transform_to_visjs
                data = transform_to_visjs(raw_data)
                st.session_state.diagram_data = data
                st.session_state.diagram_data_type = "visjs"
                
            elif diagram_type == "📋 Tabla de Conexiones":
                data = get_traceability_raw(username, password, fecha_inicio_str, fecha_fin_str)
                if not data or not data.get('pallets'):
                    st.warning("No hay datos suficientes para mostrar en el período seleccionado.")
                    st.session_state.diagram_data = None
                    return
                st.session_state.diagram_data = data
                st.session_state.diagram_data_type = "table"
    
    # Renderizar el diagrama si hay datos en session_state
    if st.session_state.diagram_data:
        data = st.session_state.diagram_data
        data_type = st.session_state.diagram_data_type
        
        if data_type == "sankey":
            _render_sankey_plotly(data)
            _render_sankey_stats(data)
        elif data_type == "reactflow" and TIMELINE_FLOW_AVAILABLE:
            _render_reactflow_diagram(data)
        elif data_type == "visjs" and VISJS_AVAILABLE:
            _render_visjs_diagram(data)
        elif data_type == "table":
            _render_connections_table(data)
    else:
        st.info("👆 Ajusta filtros y haz clic en **Generar Diagrama**")


def _render_sankey_plotly(sankey_data: dict):
    """Renderiza el diagrama Sankey con Plotly (layout automático)."""
    # Crear figura Sankey con layout automático de Plotly
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=[n["label"] for n in sankey_data["nodes"]],
            color=[n["color"] for n in sankey_data["nodes"]],
            customdata=[str(n.get("detail", "")) for n in sankey_data["nodes"]],
            hovertemplate="%{label}<br>%{customdata}<extra></extra>"
        ),
        link=dict(
            source=[l["source"] for l in sankey_data["links"]],
            target=[l["target"] for l in sankey_data["links"]],
            value=[l["value"] for l in sankey_data["links"]],
            color=[l.get("color", "rgba(200,200,200,0.35)") for l in sankey_data["links"]],
        )
    )])
    
    fig.update_layout(
        title="Trazabilidad Completa de Paquetes",
        height=800,
        font=dict(size=10)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def _render_visjs_diagram(visjs_data: dict):
    """Renderiza el diagrama con vis.js Network usando pyvis."""
    if not VISJS_AVAILABLE:
        st.error("❌ pyvis no está instalado. Ejecuta: pip install pyvis")
        return
    
    # Opción para mostrar timeline
    show_timeline = st.checkbox("📅 Mostrar Línea de Tiempo", value=True)
    
    if show_timeline and visjs_data.get("timeline_data"):
        # Vista combinada: timeline arriba, red abajo
        render_combined_view(
            visjs_data,
            network_height="500px",
            timeline_height="750px"
        )
    else:
        # Solo red
        render_visjs_network(visjs_data, height="700px")


def _render_connections_table(traceability_data: dict):
    """Renderiza una tabla de conexiones desde datos crudos de trazabilidad."""
    st.markdown("### 📋 Tabla de Conexiones")
    
    pallets = traceability_data.get("pallets", {})
    processes = traceability_data.get("processes", {})
    suppliers = traceability_data.get("suppliers", {})
    customers = traceability_data.get("customers", {})
    links = traceability_data.get("links", [])
    
    # Mostrar estadísticas
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🏭 Proveedores", len(suppliers))
    with col2:
        pallets_in = len([p for p in pallets.values() if p.get("direction") == "IN"])
        st.metric("🟠 Pallets IN", pallets_in)
    with col3:
        procs = len([p for p in processes.values() if not p.get("is_reception")])
        st.metric("🔴 Procesos", procs)
    with col4:
        pallets_out = len([p for p in pallets.values() if p.get("direction") == "OUT"])
        st.metric("🟢 Pallets OUT", pallets_out)
    with col5:
        st.metric("🔵 Clientes", len(customers))
    
    st.markdown("---")
    
    # Crear tabla de conexiones
    connections = []
    for link in links:
        source_type, source_id, target_type, target_id, qty = link
        
        # Resolver nombres
        source_name = "?"
        target_name = "?"
        
        if source_type == "RECV":
            source_name = f"📥 {source_id}"
        elif source_type == "PALLET":
            pinfo = pallets.get(source_id, {})
            source_name = f"📦 {pinfo.get('name', source_id)}"
        elif source_type == "PROCESS":
            source_name = f"🔴 {source_id}"
        
        if target_type == "PALLET":
            pinfo = pallets.get(target_id, {})
            target_name = f"📦 {pinfo.get('name', target_id)}"
        elif target_type == "PROCESS":
            target_name = f"🔴 {target_id}"
        elif target_type == "CUSTOMER":
            cname = customers.get(target_id, "Cliente")
            target_name = f"🔵 {cname}"
        
        connections.append({
            "Origen": source_name,
            "Tipo": source_type,
            "Destino": target_name,
            "Tipo Destino": target_type,
            "Cantidad (kg)": f"{qty:,.0f}",
        })
    
    if connections:
        df = pd.DataFrame(connections)
        st.dataframe(df, use_container_width=True, hide_index=True, height=500)
    else:
        st.info("No hay conexiones para mostrar")


def _render_reactflow_diagram(reactflow_data: dict):
    """Renderiza el diagrama con React Flow usando streamlit-flow-component."""
    if not TIMELINE_FLOW_AVAILABLE:
        st.error("❌ streamlit-flow-component no está disponible")
        return
    
    # Importar aquí para evitar errores si no está instalado
    try:
        from streamlit_flow import streamlit_flow
        from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
        from streamlit_flow.state import StreamlitFlowState
        from streamlit_flow.layouts import LayeredLayout, TreeLayout, RadialLayout
    except ImportError:
        st.error("❌ Error al importar streamlit-flow-component")
        return
    
    nodes_data = reactflow_data.get("nodes", [])
    edges_data = reactflow_data.get("edges", [])
    timeline_dates = reactflow_data.get("timeline_dates", [])
    stats = reactflow_data.get("stats", {})
    
    if not nodes_data:
        st.warning("No hay nodos para mostrar")
        return
    
    # Mostrar estadísticas
    st.markdown("### 📊 Resumen")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🏭 Proveedores", stats.get("suppliers", 0))
    with col2:
        st.metric("🟠 Pallets IN", stats.get("pallets_in", 0))
    with col3:
        st.metric("🔴 Procesos", stats.get("processes", 0))
    with col4:
        st.metric("🟢 Pallets OUT", stats.get("pallets_out", 0))
    with col5:
        st.metric("🔵 Clientes", stats.get("customers", 0))
    
    # Mostrar línea de tiempo si hay fechas
    if timeline_dates:
        with st.expander(f"📅 Línea de Tiempo ({len(timeline_dates)} fechas)", expanded=False):
            st.write(", ".join(timeline_dates[:20]))
    
    st.markdown("---")
    
    # Usar session_state para mantener el estado del flow
    flow_state_key = "reactflow_state"
    
    # Solo crear nodos/edges si no existen en session_state o si los datos cambiaron
    if flow_state_key not in st.session_state or st.session_state.get("reactflow_data_hash") != hash(str(nodes_data)):
        nodes = []
        for node in nodes_data:
            nodes.append(StreamlitFlowNode(
                id=node["id"],
                pos=(node["position"]["x"], node["position"]["y"]),
                data=node["data"],
                node_type=node.get("type", "default"),
                source_position=node.get("source_position", "right"),
                target_position=node.get("target_position", "left"),
                style=node.get("style", {})
            ))
        
        edges = []
        for edge in edges_data:
            edges.append(StreamlitFlowEdge(
                id=edge["id"],
                source=edge["source"],
                target=edge["target"],
                label=edge.get("label", ""),
                animated=edge.get("animated", False),
                edge_type=edge.get("edge_type", "smoothstep"),
                style=edge.get("style", {}),
                label_style=edge.get("label_style", {})
            ))
        
        st.session_state[flow_state_key] = StreamlitFlowState(nodes=nodes, edges=edges)
        st.session_state["reactflow_data_hash"] = hash(str(nodes_data))
    
    # Layout fijo (Layered horizontal)
    layout = LayeredLayout(direction="right", node_node_spacing=50, node_layer_spacing=200)
    
    # Renderizar con estado persistente
    updated_state = streamlit_flow(
        key="traceability_flow",
        state=st.session_state[flow_state_key],
        layout=layout,
        fit_view=True,
        height=700,
        show_minimap=True,
        show_controls=True,
        hide_watermark=True,
        allow_new_edges=False,
        pan_on_drag=True,
        allow_zoom=True,
        min_zoom=0.1,
        get_node_on_click=True,
    )
    
    # Actualizar estado si cambió
    if updated_state:
        st.session_state[flow_state_key] = updated_state
        if updated_state.selected_id:
            st.info(f"📍 Nodo seleccionado: **{updated_state.selected_id}**")


def _render_sankey_stats(sankey_data: dict):
    """Renderiza las estadísticas del diagrama."""
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🏭 Proveedores", len([n for n in sankey_data["nodes"] if n["color"] == "#9b59b6"]))
    with col2:
        st.metric("📥 Recepciones", len([n for n in sankey_data["nodes"] if n["color"] == "#1abc9c"]))
    with col3:
        st.metric("🔴 Procesos", len([n for n in sankey_data["nodes"] if n["color"] == "#e74c3c"]))
    with col4:
        st.metric("🟢 Pallets OUT", len([n for n in sankey_data["nodes"] if n["color"] == "#2ecc71"]))
    with col5:
        st.metric("🔵 Clientes", len([n for n in sankey_data["nodes"] if n["color"] == "#3498db"]))
    
    # Leyenda
    st.markdown("##### Leyenda de Nodos:")
    st.markdown("""
    - 🏭 **Proveedor** (morado): Origen de la mercadería
    - 📥 **Recepción** (turquesa): Entrada desde proveedor
    - 🔴 **Proceso** (rojo): Operación/transformación
    - 🟠 **Pallet IN** (naranja): Pallet que entra
    - 🟢 **Pallet OUT** (verde): Pallet que sale
    - 🔵 **Cliente** (azul): Destino de venta
    """)
    st.markdown("##### Conexiones:")
    st.markdown("""
    - 🟣 **Continuidad** (morado): Pallet OUT → mismo Pallet IN en otro proceso
    """)

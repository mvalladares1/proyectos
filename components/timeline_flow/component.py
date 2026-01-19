"""
Timeline Flow Component para Streamlit.
Usa streamlit-flow-component para renderizar React Flow.
"""
import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime

# Importar streamlit-flow-component
try:
    from streamlit_flow import streamlit_flow
    from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
    from streamlit_flow.state import StreamlitFlowState
    from streamlit_flow.layouts import TreeLayout, LayeredLayout, RadialLayout
    FLOW_AVAILABLE = True
except ImportError:
    FLOW_AVAILABLE = False


def render_timeline_flow(
    sankey_data: Dict,
    height: int = 800,
    key: str = "timeline_flow"
) -> None:
    """
    Renderiza un diagrama de flujo con línea de tiempo usando React Flow.
    
    Args:
        sankey_data: Datos del endpoint /sankey con nodes y links
        height: Altura del componente en píxeles
        key: Key único para el componente
    """
    if not FLOW_AVAILABLE:
        st.error("❌ La librería streamlit-flow-component no está instalada. Ejecuta: `pip install streamlit-flow-component`")
        return
    
    if not sankey_data or not sankey_data.get("nodes"):
        st.warning("No hay datos para mostrar")
        return
    
    # Convertir datos de Sankey a formato streamlit-flow
    nodes, edges, timeline_dates = _convert_to_streamlit_flow(sankey_data)
    
    if not nodes:
        st.warning("No se pudieron generar nodos para el diagrama")
        return
    
    # Mostrar línea de tiempo arriba
    if timeline_dates:
        _render_timeline_header(timeline_dates)
    
    # Crear estado del flow
    state = StreamlitFlowState(nodes=nodes, edges=edges)
    
    # Selector de layout
    col1, col2 = st.columns([1, 4])
    with col1:
        layout_option = st.selectbox(
            "Layout:",
            ["Layered (Horizontal)", "Tree", "Radial"],
            key=f"{key}_layout"
        )
    
    # Configurar layout
    if layout_option == "Layered (Horizontal)":
        layout = LayeredLayout(direction="right", node_node_spacing=50, layer_spacing=200)
    elif layout_option == "Tree":
        layout = TreeLayout(direction="right")
    else:
        layout = RadialLayout()
    
    # Renderizar el flow
    st.markdown("---")
    
    updated_state = streamlit_flow(
        key=key,
        state=state,
        layout=layout,
        fit_view=True,
        height=height,
        enable_node_menu=True,
        enable_edge_menu=True,
        enable_pane_menu=False,
        hide_watermark=True,
        allow_new_edges=False,
        animate_new_edges=True,
        min_zoom=0.1,
        max_zoom=2.0,
    )
    
    # Mostrar info si se selecciona un nodo
    if updated_state and updated_state.selected_id:
        selected_id = updated_state.selected_id
        # Buscar el nodo seleccionado
        for node in nodes:
            if node.id == selected_id:
                st.info(f"📍 Seleccionado: **{node.data.get('content', selected_id)}**")
                break


def _convert_to_streamlit_flow(sankey_data: Dict) -> tuple:
    """
    Convierte datos de Sankey a formato streamlit-flow.
    
    Returns:
        (nodes, edges, timeline_dates)
    """
    nodes = []
    edges = []
    timeline_dates = set()
    
    sankey_nodes = sankey_data.get("nodes", [])
    sankey_links = sankey_data.get("links", [])
    
    # Extraer fechas de los nodos para la línea de tiempo
    for node in sankey_nodes:
        detail = node.get("detail", {})
        if isinstance(detail, dict):
            date_str = detail.get("date") or detail.get("fecha")
            if date_str:
                try:
                    if "T" in str(date_str):
                        date_str = str(date_str).split("T")[0]
                    timeline_dates.add(date_str)
                except:
                    pass
    
    # Ordenar fechas
    sorted_dates = sorted(list(timeline_dates))
    
    # Crear nodos StreamlitFlow
    for i, node in enumerate(sankey_nodes):
        label = node.get("label", f"Nodo {i}")
        color = node.get("color", "#666")
        detail = node.get("detail", {})
        node_type = node.get("type", "default")
        
        # Determinar tipo de nodo para React Flow
        rf_node_type = "default"
        if node_type in ["SUPPLIER", "supplier"]:
            rf_node_type = "input"
        elif node_type in ["CUSTOMER", "customer"]:
            rf_node_type = "output"
        
        # Determinar posiciones source/target según el tipo
        source_pos = "right"
        target_pos = "left"
        
        # Crear contenido del nodo con markdown
        content = f"**{label}**"
        if isinstance(detail, dict):
            extra_info = []
            if detail.get("date"):
                extra_info.append(f"📅 {detail['date'][:10]}")
            if detail.get("qty"):
                extra_info.append(f"📦 {detail['qty']:.0f} kg")
            if extra_info:
                content += "\n\n" + " | ".join(extra_info)
        
        # Calcular posición inicial basada en x del sankey
        x_pos = node.get("x", 0.5) * 1000
        y_pos = (node.get("y", 0.5) * 600) if node.get("y") else i * 80
        
        flow_node = StreamlitFlowNode(
            id=str(i),
            pos=(x_pos, y_pos),
            data={"content": content},
            node_type=rf_node_type,
            source_position=source_pos,
            target_position=target_pos,
            style={
                "backgroundColor": color,
                "color": "#fff" if color not in ["#f39c12", "#2ecc71", "#f1c40f"] else "#000",
                "border": f"2px solid {color}",
                "borderRadius": "8px",
                "padding": "10px",
                "fontSize": "12px",
                "minWidth": "150px",
            }
        )
        nodes.append(flow_node)
    
    # Crear edges StreamlitFlow
    for j, link in enumerate(sankey_links):
        source = link.get("source")
        target = link.get("target")
        value = link.get("value", 1)
        color = link.get("color", "rgba(150,150,150,0.5)")
        
        if source is not None and target is not None:
            # Extraer color sólido del rgba
            solid_color = _extract_solid_color(color)
            
            # Label para el edge
            edge_label = f"{value:.0f} kg" if value > 10 else ""
            
            flow_edge = StreamlitFlowEdge(
                id=f"e{j}",
                source=str(source),
                target=str(target),
                label=edge_label,
                animated=False,
                edge_type="smoothstep",
                style={
                    "stroke": solid_color,
                    "strokeWidth": max(1, min(4, value / 200)),
                },
                label_style={
                    "fontSize": "10px",
                    "fill": "#666",
                }
            )
            edges.append(flow_edge)
    
    return nodes, edges, sorted_dates


def _extract_solid_color(rgba_color: str) -> str:
    """Extrae color sólido de un rgba."""
    if rgba_color.startswith("rgba("):
        parts = rgba_color.replace("rgba(", "").replace(")", "").split(",")
        if len(parts) >= 3:
            r, g, b = parts[:3]
            return f"rgb({r.strip()},{g.strip()},{b.strip()})"
    return rgba_color if rgba_color.startswith("#") or rgba_color.startswith("rgb") else "#999"


def _render_timeline_header(dates: List[str]) -> None:
    """Renderiza la cabecera con la línea de tiempo."""
    if not dates:
        return
    
    st.markdown("### 📅 Línea de Tiempo")
    
    # Crear columnas para las fechas
    cols = st.columns(len(dates))
    for i, date in enumerate(dates):
        with cols[i]:
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                st.markdown(f"**{dt.strftime('%d/%m/%Y')}**")
            except:
                st.markdown(f"**{date}**")


def render_simple_flow(sankey_data: Dict, height: int = 600) -> None:
    """
    Versión simplificada usando tabla para visualizar el flujo.
    Alternativa cuando streamlit-flow no está disponible.
    """
    if not sankey_data or not sankey_data.get("nodes"):
        st.warning("No hay datos para mostrar")
        return
    
    nodes = sankey_data.get("nodes", [])
    links = sankey_data.get("links", [])
    
    # Agrupar nodos por tipo
    suppliers = [n for n in nodes if n.get("type") == "SUPPLIER"]
    processes = [n for n in nodes if n.get("type") == "PROCESS"]
    pallets_in = [n for n in nodes if n.get("type") == "PALLET_IN"]
    pallets_out = [n for n in nodes if n.get("type") == "PALLET_OUT"]
    customers = [n for n in nodes if n.get("type") == "CUSTOMER"]
    
    # Mostrar estadísticas
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🏭 Proveedores", len(suppliers))
    with col2:
        st.metric("🟠 Pallets IN", len(pallets_in))
    with col3:
        st.metric("🔴 Procesos", len(processes))
    with col4:
        st.metric("🟢 Pallets OUT", len(pallets_out))
    with col5:
        st.metric("🔵 Clientes", len(customers))
    
    # Mostrar flujo en texto
    st.markdown("### 📋 Conexiones del Flujo")
    
    # Crear dataframe con conexiones
    connections = []
    for link in links:
        src_idx = link.get("source")
        tgt_idx = link.get("target")
        value = link.get("value", 0)
        
        if src_idx is not None and tgt_idx is not None and src_idx < len(nodes) and tgt_idx < len(nodes):
            src_node = nodes[src_idx]
            tgt_node = nodes[tgt_idx]
            
            connections.append({
                "Origen": src_node.get("label", "?"),
                "Tipo Origen": src_node.get("type", "?"),
                "Destino": tgt_node.get("label", "?"),
                "Tipo Destino": tgt_node.get("type", "?"),
                "Cantidad (kg)": f"{value:,.0f}"
            })
    
    if connections:
        import pandas as pd
        df = pd.DataFrame(connections)
        st.dataframe(df, use_container_width=True, height=height)

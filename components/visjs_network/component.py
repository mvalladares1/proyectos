"""
Componente de visualización de red usando pyvis (vis.js).
Genera HTML interactivo con vis.js Network.
"""
import streamlit as st
import streamlit.components.v1 as components
from typing import Dict, Optional
import json

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False


def render_visjs_network(
    data: Dict,
    height: str = "700px",
    show_physics_button: bool = True,
    notebook: bool = False,
) -> None:
    """
    Renderiza una red de trazabilidad usando pyvis/vis.js.
    
    Args:
        data: Dict con nodes, edges del visjs_transformer
        height: Altura del contenedor
        show_physics_button: Mostrar botón de toggle física
        notebook: Si está en notebook Jupyter
    """
    if not PYVIS_AVAILABLE:
        st.error("⚠️ pyvis no está instalado. Ejecuta: `pip install pyvis`")
        return
    
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    stats = data.get("stats", {})
    
    if not nodes:
        st.warning("No hay datos para visualizar")
        return
    
    # Mostrar estadísticas
    st.markdown("### 📊 Estadísticas de la red")
    cols = st.columns(6)
    stats_display = [
        ("🏭 Proveedores", stats.get("suppliers", 0)),
        ("📦 Pallets In", stats.get("pallets_in", 0)),
        ("🔄 Procesos", stats.get("processes", 0)),
        ("📤 Pallets Out", stats.get("pallets_out", 0)),
        ("👤 Clientes", stats.get("customers", 0)),
        ("🔗 Conexiones", stats.get("total_edges", 0)),
    ]
    for col, (label, value) in zip(cols, stats_display):
        col.metric(label, value)
    
    # Crear la red
    net = Network(
        height=height,
        width="100%",
        bgcolor="#ffffff",
        font_color="#333333",
        directed=True,
        notebook=notebook,
        cdn_resources="in_line",  # Para que funcione en Streamlit
    )
    
    # Configurar layout jerárquico
    net.set_options("""
    {
        "layout": {
            "hierarchical": {
                "enabled": true,
                "direction": "LR",
                "sortMethod": "directed",
                "levelSeparation": 250,
                "nodeSpacing": 80,
                "treeSpacing": 150,
                "blockShifting": true,
                "edgeMinimization": true
            }
        },
        "physics": {
            "enabled": false
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "zoomView": true,
            "dragView": true,
            "dragNodes": true,
            "navigationButtons": true,
            "keyboard": {
                "enabled": true,
                "bindToWindow": false
            }
        },
        "nodes": {
            "font": {"size": 11, "face": "Arial"},
            "borderWidth": 2,
            "shadow": true
        },
        "edges": {
            "smooth": {
                "type": "cubicBezier",
                "forceDirection": "horizontal",
                "roundness": 0.4
            },
            "arrows": {"to": {"enabled": true, "scaleFactor": 0.5}},
            "color": {"inherit": false}
        }
    }
    """)
    
    # Agregar nodos
    for node in nodes:
        net.add_node(
            node["id"],
            label=node.get("label", node["id"]),
            title=node.get("title", ""),
            level=node.get("level", 0),
            color=node.get("color", {"background": "#97c2fc"}),
            shape=node.get("shape", "box"),
            font=node.get("font", {"color": "#fff"}),
            borderWidth=node.get("borderWidth", 2),
            shadow=node.get("shadow", True),
            margin=node.get("margin", 10),
        )
    
    # Agregar edges
    for edge in edges:
        net.add_edge(
            edge["from"],
            edge["to"],
            value=edge.get("value", 1),
            width=edge.get("width", 1),
            label=edge.get("label", ""),
            title=f"{edge.get('value', 0):.0f} kg",
            arrows=edge.get("arrows", "to"),
            color=edge.get("color", {"color": "#888"}),
            font={"size": 9, "align": "middle"},
        )
    
    # Generar HTML
    html = net.generate_html()
    
    # Modificar HTML para mejor integración con Streamlit
    html = html.replace(
        '<body>',
        '<body style="margin: 0; padding: 0; overflow: hidden;">'
    )
    
    # Mostrar controles
    st.markdown("### 🕸️ Red de Trazabilidad")
    st.caption("🖱️ Arrastra nodos | 🔍 Scroll para zoom | 📍 Hover para detalles")
    
    # Renderizar
    components.html(html, height=int(height.replace("px", "")) + 50, scrolling=False)


def render_visjs_timeline(
    data: Dict,
    height: str = "300px",
) -> None:
    """
    Renderiza una línea de tiempo usando vis-timeline.
    
    Args:
        data: Dict con timeline_data del visjs_transformer
        height: Altura del contenedor
    """
    timeline_data = data.get("timeline_data", [])
    
    if not timeline_data:
        st.info("No hay datos de fechas para mostrar en la línea de tiempo")
        return
    
    # Agrupar por tipo
    groups = [
        {"id": "reception", "content": "📥 Recepciones", "style": "background-color: #1abc9c; color: white;"},
        {"id": "pallet_in", "content": "📦 Pallets IN", "style": "background-color: #f39c12; color: white;"},
        {"id": "process", "content": "🔄 Procesos", "style": "background-color: #e74c3c; color: white;"},
        {"id": "pallet_out", "content": "📤 Pallets OUT", "style": "background-color: #2ecc71; color: white;"},
    ]
    
    # Generar HTML de timeline
    timeline_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/vis-timeline@latest/standalone/umd/vis-timeline-graph2d.min.js"></script>
        <link href="https://unpkg.com/vis-timeline@latest/styles/vis-timeline-graph2d.min.css" rel="stylesheet" type="text/css" />
        <style>
            body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
            #timeline {{ width: 100%; height: {height}; }}
            .vis-item {{ 
                border-radius: 4px; 
                font-size: 11px;
                cursor: pointer;
            }}
            .vis-item.vis-selected {{
                border-width: 3px;
            }}
        </style>
    </head>
    <body>
        <div id="timeline"></div>
        <script>
            var groups = new vis.DataSet({json.dumps(groups)});
            var items = new vis.DataSet({json.dumps(timeline_data)});
            
            var options = {{
                showCurrentTime: false,
                zoomable: true,
                moveable: true,
                stack: true,
                orientation: 'top',
                margin: {{ item: 5 }},
                tooltip: {{
                    followMouse: true,
                    overflowMethod: 'cap'
                }}
            }};
            
            var container = document.getElementById('timeline');
            var timeline = new vis.Timeline(container, items, groups, options);
            
            // Fit all items
            timeline.fit();
            
            // Click handler
            timeline.on('select', function(properties) {{
                if (properties.items.length > 0) {{
                    console.log('Selected:', properties.items[0]);
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    st.markdown("### 📅 Línea de Tiempo")
    st.caption("🔍 Scroll para zoom | ← → Arrastra para navegar")
    
    components.html(timeline_html, height=int(height.replace("px", "")) + 50, scrolling=False)


def render_combined_view(
    data: Dict,
    network_height: str = "600px",
    timeline_height: str = "250px",
) -> None:
    """
    Renderiza red + timeline combinados.
    """
    # Timeline arriba
    render_visjs_timeline(data, height=timeline_height)
    
    st.divider()
    
    # Red abajo
    render_visjs_network(data, height=network_height)

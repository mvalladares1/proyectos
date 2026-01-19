"""
Componente de visualización de red usando vis.js directamente.
Genera HTML interactivo con vis.js Network y Timeline.
"""
import streamlit as st
import streamlit.components.v1 as components
from typing import Dict
import json

# vis.js se carga desde CDN, no necesitamos pyvis
PYVIS_AVAILABLE = True  # Mantenemos por compatibilidad


def render_visjs_network(
    data: Dict,
    height: str = "700px",
) -> None:
    """
    Renderiza una red de trazabilidad usando vis.js Network.
    
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
    
    # Generar HTML directamente con vis.js para control total del layout
    nodes_json = json.dumps(nodes)
    # Preparar nodos base
    nodes_base = []
    for n in nodes:
        node_id = n["id"]
        node_type = n.get("nodeType", "PROCESS")
        if not node_type:
            # Inferir tipo del ID
            if node_id.startswith("SUPP:"):
                node_type = "SUPPLIER"
            elif node_id.startswith("PKG:"):
                color = n.get("color", "")
                node_type = "PALLET_OUT" if "#2ecc71" in color else "PALLET_IN"
            elif node_id.startswith("PROC:"):
                node_type = "PROCESS"
            elif node_id.startswith("CUST:"):
                node_type = "CUSTOMER"
        
        nodes_base.append({
            "id": node_id,
            "label": n.get("label", node_id),
            "title": n.get("title", "").replace("\n", "<br>"),
            "nodeType": node_type,
            "group": node_type.lower() if node_type else "process",
        })
    
    edges_base = [{
        "from": e["from"],
        "to": e["to"],
        "value": e.get("value", 1),
        "width": max(1, min(6, e.get("value", 1) / 300)),
        "title": f"<b>{e.get('value', 0):,.0f} kg</b>",
    } for e in edges]
    
    # ============ LAYOUT 1: COLUMNAS FIJAS ============
    X_COLUMNS = {"SUPPLIER": 0, "PALLET_IN": 200, "PROCESS": 400, "PALLET_OUT": 600, "CUSTOMER": 800}
    type_counts = {}
    nodes_columns = []
    
    for n in nodes_base:
        node_type = n["nodeType"]
        type_counts[node_type] = type_counts.get(node_type, 0) + 1
        x = X_COLUMNS.get(node_type, 400)
        y = type_counts[node_type] * 60
        nodes_columns.append({**n, "x": x, "y": y, "fixed": True})
    
    # ============ LAYOUT 2: RADIAL ============
    import math
    type_angles = {"SUPPLIER": -120, "PALLET_IN": -60, "PROCESS": 0, "PALLET_OUT": 60, "CUSTOMER": 120}
    type_radius = {"SUPPLIER": 350, "PALLET_IN": 250, "PROCESS": 100, "PALLET_OUT": 250, "CUSTOMER": 350}
    type_counts_radial = {}
    nodes_radial = []
    
    for n in nodes_base:
        node_type = n["nodeType"]
        type_counts_radial[node_type] = type_counts_radial.get(node_type, 0) + 1
        base_angle = type_angles.get(node_type, 0)
        radius = type_radius.get(node_type, 200)
        # Distribuir nodos del mismo tipo en un arco
        count = type_counts_radial[node_type]
        angle_offset = (count - 1) * 15 - 30  # Spread de 15 grados
        angle = math.radians(base_angle + angle_offset)
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        nodes_radial.append({**n, "x": x, "y": y, "fixed": True})
    
    # ============ LAYOUT 3: FÍSICA (ORIGINAL) ============
    nodes_physics = [{**n} for n in nodes_base]  # Sin posiciones fijas
    
    # Generar JSON
    import json
    nodes_columns_json = json.dumps(nodes_columns)
    nodes_radial_json = json.dumps(nodes_radial)
    nodes_physics_json = json.dumps(nodes_physics)
    edges_json = json.dumps(edges_base)
    
    network_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.6/dist/vis-network.min.js"></script>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            html, body {{ height: 100%; overflow: auto; }}
            body {{ background: #0d1117; font-family: Arial, sans-serif; padding: 10px; }}
            
            .container {{ display: flex; flex-direction: column; gap: 15px; }}
            .network-card {{
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                overflow: hidden;
            }}
            .network-header {{
                background: #21262d;
                padding: 10px 15px;
                border-bottom: 1px solid #30363d;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .network-title {{
                color: #f0f6fc;
                font-size: 14px;
                font-weight: 600;
            }}
            .network-desc {{
                color: #8b949e;
                font-size: 11px;
            }}
            .network-canvas {{
                height: 350px;
                width: 100%;
            }}
            
            /* Legend */
            .legend {{
                position: fixed;
                top: 10px;
                right: 10px;
                background: rgba(22, 27, 34, 0.95);
                padding: 12px;
                border-radius: 8px;
                border: 1px solid #30363d;
                font-size: 11px;
                color: #c9d1d9;
                z-index: 1000;
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                margin: 5px 0;
            }}
            .legend-shape {{
                width: 12px;
                height: 12px;
                margin-right: 8px;
                border-radius: 2px;
            }}
            .legend-dot {{ border-radius: 50%; }}
        </style>
    </head>
    <body>
        <div class="legend">
            <div style="font-weight: bold; margin-bottom: 8px; color: #f0f6fc;">🗺️ Leyenda</div>
            <div class="legend-item"><div class="legend-shape" style="background: #9b59b6; clip-path: polygon(50% 0%, 0% 100%, 100% 100%);"></div>Proveedor</div>
            <div class="legend-item"><div class="legend-shape legend-dot" style="background: #f39c12;"></div>Pallet IN</div>
            <div class="legend-item"><div class="legend-shape" style="background: #e74c3c;"></div>Proceso</div>
            <div class="legend-item"><div class="legend-shape legend-dot" style="background: #2ecc71;"></div>Pallet OUT</div>
            <div class="legend-item"><div class="legend-shape" style="background: #3498db;"></div>Cliente</div>
        </div>
        
        <div class="container">
            <!-- Layout 1: Columnas -->
            <div class="network-card">
                <div class="network-header">
                    <div>
                        <div class="network-title">📊 Layout 1: Columnas Fijas</div>
                        <div class="network-desc">Flujo izquierda → derecha. Cada tipo en su columna. Posiciones fijas.</div>
                    </div>
                </div>
                <div id="network1" class="network-canvas"></div>
            </div>
            
            <!-- Layout 2: Radial -->
            <div class="network-card">
                <div class="network-header">
                    <div>
                        <div class="network-title">🔄 Layout 2: Radial</div>
                        <div class="network-desc">Procesos al centro. Proveedores izquierda, Clientes derecha.</div>
                    </div>
                </div>
                <div id="network2" class="network-canvas"></div>
            </div>
            
            <!-- Layout 3: Física -->
            <div class="network-card">
                <div class="network-header">
                    <div>
                        <div class="network-title">🌐 Layout 3: Física (Original)</div>
                        <div class="network-desc">Nodos se organizan por conexiones. Arrastrable. Orgánico.</div>
                    </div>
                </div>
                <div id="network3" class="network-canvas"></div>
            </div>
        </div>
        
        <script>
            var groupOptions = {{
                supplier: {{
                    shape: 'triangle',
                    color: {{ background: '#9b59b6', border: '#8e44ad', highlight: {{ background: '#a569bd' }}, hover: {{ background: '#a569bd' }} }},
                    size: 20
                }},
                pallet_in: {{
                    shape: 'dot',
                    color: {{ background: '#f39c12', border: '#d68910', highlight: {{ background: '#f5b041' }}, hover: {{ background: '#f5b041' }} }},
                    size: 15
                }},
                process: {{
                    shape: 'square',
                    color: {{ background: '#e74c3c', border: '#c0392b', highlight: {{ background: '#ec7063' }}, hover: {{ background: '#ec7063' }} }},
                    size: 16
                }},
                pallet_out: {{
                    shape: 'dot',
                    color: {{ background: '#2ecc71', border: '#27ae60', highlight: {{ background: '#58d68d' }}, hover: {{ background: '#58d68d' }} }},
                    size: 15
                }},
                customer: {{
                    shape: 'square',
                    color: {{ background: '#3498db', border: '#2980b9', highlight: {{ background: '#5dade2' }}, hover: {{ background: '#5dade2' }} }},
                    size: 18
                }}
            }};
            
            var edgeOptions = {{
                color: {{ color: 'rgba(139, 148, 158, 0.4)', highlight: '#58a6ff', hover: '#58a6ff' }},
                smooth: {{ enabled: true, type: 'curvedCW', roundness: 0.15 }},
                arrows: {{ to: {{ enabled: true, scaleFactor: 0.4 }} }},
                hoverWidth: 1.5
            }};
            
            var nodeOptions = {{
                font: {{ size: 9, color: '#c9d1d9', face: 'Arial' }},
                borderWidth: 2
            }};
            
            var interactionOptions = {{
                hover: true,
                tooltipDelay: 50,
                zoomView: true,
                dragView: true,
                navigationButtons: false
            }};
            
            // ========== NETWORK 1: COLUMNAS ==========
            var network1 = new vis.Network(
                document.getElementById('network1'),
                {{
                    nodes: new vis.DataSet({nodes_columns_json}),
                    edges: new vis.DataSet({edges_json})
                }},
                {{
                    layout: {{ improvedLayout: false }},
                    physics: {{ enabled: false }},
                    interaction: {{ ...interactionOptions, dragNodes: false }},
                    nodes: nodeOptions,
                    edges: edgeOptions,
                    groups: groupOptions
                }}
            );
            network1.fit({{ animation: false }});
            
            // ========== NETWORK 2: RADIAL ==========
            var network2 = new vis.Network(
                document.getElementById('network2'),
                {{
                    nodes: new vis.DataSet({nodes_radial_json}),
                    edges: new vis.DataSet({edges_json})
                }},
                {{
                    layout: {{ improvedLayout: false }},
                    physics: {{ enabled: false }},
                    interaction: {{ ...interactionOptions, dragNodes: false }},
                    nodes: nodeOptions,
                    edges: edgeOptions,
                    groups: groupOptions
                }}
            );
            network2.fit({{ animation: false }});
            
            // ========== NETWORK 3: FÍSICA ==========
            var network3 = new vis.Network(
                document.getElementById('network3'),
                {{
                    nodes: new vis.DataSet({nodes_physics_json}),
                    edges: new vis.DataSet({edges_json})
                }},
                {{
                    physics: {{
                        forceAtlas2Based: {{
                            gravitationalConstant: -40,
                            centralGravity: 0.01,
                            springLength: 120,
                            springConstant: 0.08,
                            damping: 0.4,
                            avoidOverlap: 0.5
                        }},
                        solver: 'forceAtlas2Based',
                        stabilization: {{ iterations: 200 }}
                    }},
                    interaction: {{ ...interactionOptions, dragNodes: true }},
                    nodes: nodeOptions,
                    edges: edgeOptions,
                    groups: groupOptions
                }}
            );
            network3.once('stabilizationIterationsDone', function() {{
                network3.fit({{ animation: {{ duration: 300 }} }});
            }});
        </script>
    </body>
    </html>
    """
    
    # Mostrar controles
    st.markdown("### 🕸️ Red de Trazabilidad")
    st.caption("🖱️ Arrastra para navegar | 🔍 Scroll para zoom | 📍 Hover para detalles")
    
    # Renderizar
    components.html(network_html, height=int(height.replace("px", "")) + 50, scrolling=False)


def render_visjs_timeline(
    data: Dict,
    height: str = "450px",
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
    
    # Todos los grupos con estilos (sin recepciones - van directo de proveedor a pallet)
    groups = [
        {"id": "supplier", "content": "🏭 Proveedores", "style": "background-color: #9b59b6; color: white;"},
        {"id": "pallet_in", "content": "📦 Pallets IN", "style": "background-color: #f39c12; color: white;"},
        {"id": "process", "content": "🔄 Procesos", "style": "background-color: #e74c3c; color: white;"},
        {"id": "pallet_out", "content": "📤 Pallets OUT", "style": "background-color: #2ecc71; color: white;"},
        {"id": "customer", "content": "🔵 Clientes", "style": "background-color: #3498db; color: white;"},
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
            #timeline-container {{ 
                width: 100%; 
                height: {height}; 
                position: relative;
                background: #1e1e1e;
            }}
            #timeline {{ width: 100%; height: 100%; }}
            .vis-item {{ 
                border-radius: 4px; 
                font-size: 11px;
                cursor: pointer;
            }}
            .vis-item.vis-selected {{
                border-width: 3px;
            }}
            /* Estilos para rangos (procesos) */
            .vis-item.vis-range {{
                border-radius: 6px;
            }}
            .timeline-process {{
                background-color: #e74c3c !important;
                border-color: #c0392b !important;
            }}
            .timeline-supplier {{
                background-color: #9b59b6 !important;
                border-color: #8e44ad !important;
            }}
            .timeline-reception {{
                background-color: #1abc9c !important;
                border-color: #16a085 !important;
            }}
            .timeline-pallet-in {{
                background-color: #f39c12 !important;
                border-color: #d68910 !important;
            }}
            .timeline-pallet-out {{
                background-color: #2ecc71 !important;
                border-color: #27ae60 !important;
            }}
            .timeline-customer {{
                background-color: #3498db !important;
                border-color: #2980b9 !important;
            }}
            /* Botón fullscreen */
            #fullscreen-btn {{
                position: absolute;
                top: 10px;
                right: 10px;
                z-index: 1000;
                padding: 8px 12px;
                background: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                display: flex;
                align-items: center;
                gap: 5px;
            }}
            #fullscreen-btn:hover {{
                background: #2980b9;
            }}
            /* Estilos en fullscreen */
            #timeline-container:fullscreen {{
                padding: 20px;
                height: 100vh !important;
            }}
            #timeline-container:fullscreen #timeline {{
                height: calc(100vh - 40px) !important;
            }}
            #timeline-container:-webkit-full-screen {{
                padding: 20px;
                height: 100vh !important;
            }}
            #timeline-container:-webkit-full-screen #timeline {{
                height: calc(100vh - 40px) !important;
            }}
        </style>
    </head>
    <body>
        <div id="timeline-container">
            <button id="fullscreen-btn" onclick="toggleFullscreen()">
                <span id="fs-icon">⛶</span> <span id="fs-text">Pantalla completa</span>
            </button>
            <div id="timeline"></div>
        </div>
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
                verticalScroll: true,
                horizontalScroll: true,
                zoomKey: 'ctrlKey',
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
            
            // Fullscreen toggle
            function toggleFullscreen() {{
                var elem = document.getElementById('timeline-container');
                var btn = document.getElementById('fullscreen-btn');
                var icon = document.getElementById('fs-icon');
                var text = document.getElementById('fs-text');
                
                if (!document.fullscreenElement && !document.webkitFullscreenElement) {{
                    if (elem.requestFullscreen) {{
                        elem.requestFullscreen();
                    }} else if (elem.webkitRequestFullscreen) {{
                        elem.webkitRequestFullscreen();
                    }}
                    icon.textContent = '✕';
                    text.textContent = 'Salir';
                }} else {{
                    if (document.exitFullscreen) {{
                        document.exitFullscreen();
                    }} else if (document.webkitExitFullscreen) {{
                        document.webkitExitFullscreen();
                    }}
                    icon.textContent = '⛶';
                    text.textContent = 'Pantalla completa';
                }}
            }}
            
            // Escuchar cambios de fullscreen para actualizar botón
            document.addEventListener('fullscreenchange', function() {{
                var icon = document.getElementById('fs-icon');
                var text = document.getElementById('fs-text');
                if (!document.fullscreenElement) {{
                    icon.textContent = '⛶';
                    text.textContent = 'Pantalla completa';
                    timeline.redraw();
                }} else {{
                    setTimeout(function() {{ timeline.redraw(); timeline.fit(); }}, 100);
                }}
            }});
            
            // Hacer la función global
            window.toggleFullscreen = toggleFullscreen;
        </script>
    </body>
    </html>
    """
    
    st.markdown("### 📅 Línea de Tiempo")
    st.caption("🔍 Ctrl+Scroll = zoom | ← → Arrastra | ↑↓ Scroll vertical | ⛶ Pantalla completa")
    
    components.html(timeline_html, height=int(height.replace("px", "")) + 50, scrolling=True)


def render_combined_view(
    data: Dict,
    network_height: str = "500px",
    timeline_height: str = "450px",
) -> None:
    """
    Renderiza red + timeline combinados.
    """
    # Timeline arriba
    render_visjs_timeline(data, height=timeline_height)
    
    st.divider()
    
    # Red abajo
    render_visjs_network(data, height=network_height)

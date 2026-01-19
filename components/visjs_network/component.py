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
    # Preparar nodos con grupos
    nodes_with_groups = []
    for n in nodes:
        # Determinar grupo basado en el ID del nodo
        node_id = n["id"]
        if node_id.startswith("SUPP:"):
            group = "supplier"
        elif node_id.startswith("PKG:"):
            # Determinar si es IN o OUT basado en el color
            color = n.get("color", "")
            group = "pallet_out" if "#2ecc71" in color else "pallet_in"
        elif node_id.startswith("PROC:"):
            group = "process"
        elif node_id.startswith("CUST:"):
            group = "customer"
        else:
            group = "other"
        
        node_data = {
            "id": node_id,
            "label": n.get("label", node_id),
            "title": n.get("title", ""),
            "group": group,
            "value": 1  # Para scaling
        }
        nodes_with_groups.append(node_data)
    
    nodes_json = json.dumps(nodes_with_groups)
    edges_json = json.dumps([{
        "from": e["from"],
        "to": e["to"],
        "value": e.get("value", 1),
        "width": max(1, min(8, e.get("value", 1) / 200)),
        "title": f"{e.get('value', 0):,.0f} kg",
    } for e in edges])
    
    network_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.6/dist/vis-network.min.js"></script>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            html, body {{ height: 100%; overflow: hidden; }}
            body {{ background: #1a1a2e; }}
            #network {{ width: 100vw; height: 100vh; }}
            #legend {{
                position: absolute;
                top: 10px;
                left: 10px;
                background: rgba(0,0,0,0.7);
                padding: 10px;
                border-radius: 8px;
                font-family: Arial, sans-serif;
                font-size: 11px;
                color: white;
                z-index: 1000;
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                margin: 5px 0;
            }}
            .legend-dot {{
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }}
            .legend-square {{
                width: 12px;
                height: 12px;
                margin-right: 8px;
            }}
            .legend-triangle {{
                width: 0;
                height: 0;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-bottom: 12px solid;
                margin-right: 8px;
            }}
        </style>
    </head>
    <body>
        <div id="legend">
            <div style="font-weight: bold; margin-bottom: 8px;">🗺️ Leyenda</div>
            <div class="legend-item"><div class="legend-triangle" style="border-bottom-color: #9b59b6;"></div>Proveedor</div>
            <div class="legend-item"><div class="legend-dot" style="background: #f39c12;"></div>Pallet Entrada</div>
            <div class="legend-item"><div class="legend-square" style="background: #e74c3c;"></div>Proceso</div>
            <div class="legend-item"><div class="legend-dot" style="background: #2ecc71;"></div>Pallet Salida</div>
            <div class="legend-item"><div class="legend-square" style="background: #3498db;"></div>Cliente</div>
        </div>
        <div id="network"></div>
        <script>
            var nodes = new vis.DataSet({nodes_json});
            var edges = new vis.DataSet({edges_json});
            
            var container = document.getElementById('network');
            var data = {{ nodes: nodes, edges: edges }};
            
            var options = {{
                nodes: {{
                    scaling: {{
                        min: 16,
                        max: 32
                    }},
                    font: {{
                        size: 11,
                        color: '#ffffff',
                        face: 'Arial'
                    }},
                    borderWidth: 2
                }},
                edges: {{
                    color: {{
                        color: 'rgba(150, 150, 150, 0.6)',
                        highlight: '#ffffff',
                        hover: '#ffffff'
                    }},
                    smooth: {{
                        enabled: true,
                        type: 'continuous',
                        roundness: 0.5
                    }},
                    arrows: {{
                        to: {{ enabled: true, scaleFactor: 0.5 }}
                    }}
                }},
                physics: {{
                    forceAtlas2Based: {{
                        gravitationalConstant: -50,
                        centralGravity: 0.01,
                        springLength: 150,
                        springConstant: 0.08,
                        damping: 0.4,
                        avoidOverlap: 0.5
                    }},
                    maxVelocity: 50,
                    solver: 'forceAtlas2Based',
                    timestep: 0.35,
                    stabilization: {{
                        enabled: true,
                        iterations: 300,
                        updateInterval: 25
                    }}
                }},
                interaction: {{
                    hover: true,
                    tooltipDelay: 100,
                    zoomView: true,
                    dragView: true,
                    dragNodes: true,
                    navigationButtons: true,
                    keyboard: {{ enabled: true, bindToWindow: false }}
                }},
                groups: {{
                    supplier: {{
                        shape: 'triangle',
                        color: {{
                            background: '#9b59b6',
                            border: '#8e44ad',
                            highlight: {{ background: '#a569bd', border: '#9b59b6' }},
                            hover: {{ background: '#a569bd', border: '#9b59b6' }}
                        }},
                        size: 25
                    }},
                    pallet_in: {{
                        shape: 'dot',
                        color: {{
                            background: '#f39c12',
                            border: '#d68910',
                            highlight: {{ background: '#f5b041', border: '#f39c12' }},
                            hover: {{ background: '#f5b041', border: '#f39c12' }}
                        }},
                        size: 18
                    }},
                    process: {{
                        shape: 'square',
                        color: {{
                            background: '#e74c3c',
                            border: '#c0392b',
                            highlight: {{ background: '#ec7063', border: '#e74c3c' }},
                            hover: {{ background: '#ec7063', border: '#e74c3c' }}
                        }},
                        size: 20
                    }},
                    pallet_out: {{
                        shape: 'dot',
                        color: {{
                            background: '#2ecc71',
                            border: '#27ae60',
                            highlight: {{ background: '#58d68d', border: '#2ecc71' }},
                            hover: {{ background: '#58d68d', border: '#2ecc71' }}
                        }},
                        size: 18
                    }},
                    customer: {{
                        shape: 'square',
                        color: {{
                            background: '#3498db',
                            border: '#2980b9',
                            highlight: {{ background: '#5dade2', border: '#3498db' }},
                            hover: {{ background: '#5dade2', border: '#3498db' }}
                        }},
                        size: 22
                    }},
                    other: {{
                        shape: 'dot',
                        color: '#666666',
                        size: 15
                    }}
                }}
            }};
            
            var network = new vis.Network(container, data, options);
            
            // Fit después de estabilizar
            network.once('stabilizationIterationsDone', function() {{
                network.fit({{
                    animation: {{
                        duration: 500,
                        easingFunction: 'easeInOutQuad'
                    }}
                }});
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

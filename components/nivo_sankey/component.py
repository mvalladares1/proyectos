"""
Renderizador de Sankey usando Nivo (React).
"""
import streamlit as st
import streamlit.components.v1 as components
import json
from typing import Dict

NIVO_AVAILABLE = True


def render_nivo_sankey(data: Dict, height: int = 800):
    """
    Renderiza un diagrama Sankey usando Nivo en orientación vertical.
    
    Args:
        data: Diccionario con 'nodes' y 'links' en formato Plotly
        height: Altura del diagrama en pixels
    """
    if not data or not data.get("nodes"):
        st.warning("No hay datos para renderizar")
        return
    
    # Transformar datos de formato Plotly a formato Nivo
    nivo_data = _transform_to_nivo_format(data)
    
    # Generar HTML con React + Nivo
    html_content = _generate_nivo_html(nivo_data, height)
    
    # Renderizar
    components.html(html_content, height=height + 50, scrolling=True)


def _transform_to_nivo_format(plotly_data: Dict) -> Dict:
    """
    Transforma datos de formato Plotly Sankey a formato Nivo.
    
    Plotly usa:
    - nodes: [{label, color, detail, ...}]
    - links: [{source: int, target: int, value, color}]
    
    Nivo usa:
    - nodes: [{id: str, nodeColor?: str}]
    - links: [{source: str, target: str, value: number, color?: str}]
    """
    nodes_plotly = plotly_data.get("nodes", [])
    links_plotly = plotly_data.get("links", [])
    
    # Crear nodos con IDs únicos
    nivo_nodes = []
    node_id_map = {}  # índice -> id
    
    for idx, node in enumerate(nodes_plotly):
        node_id = f"node_{idx}"
        node_id_map[idx] = node_id
        
        # Extraer información del detalle
        detail = node.get("detail", {})
        node_type = detail.get("type", "UNKNOWN")
        
        nivo_node = {
            "id": node_id,
            "nodeColor": node.get("color", "#cccccc"),
        }
        
        # Agregar metadata para tooltips
        if node_type == "SUPPLIER":
            nivo_node["label"] = f"🏭 {detail.get('name', 'Proveedor')}"
            nivo_node["metadata"] = {
                "type": "Proveedor",
                "name": detail.get("name", ""),
                "date": detail.get("date", ""),
                "date_done": detail.get("date_done", "")
            }
        elif node_type == "RECEPTION":
            nivo_node["label"] = f"📥 {detail.get('ref', 'Recepción')}"
            nivo_node["metadata"] = {
                "type": "Recepción",
                "ref": detail.get("ref", ""),
                "date": detail.get("date", ""),
                "supplier": detail.get("supplier", "")
            }
        elif node_type == "PALLET_IN":
            nivo_node["label"] = f"🟠 {detail.get('id', 'Pallet')}"
            nivo_node["metadata"] = {
                "type": "Pallet IN",
                "id": detail.get("id", ""),
                "qty": detail.get("qty", 0),
                "products": detail.get("products", ""),
                "date": detail.get("date", ""),
                "lots": detail.get("lots", "")
            }
        elif node_type == "PALLET_OUT":
            nivo_node["label"] = f"🟢 {detail.get('id', 'Pallet')}"
            nivo_node["metadata"] = {
                "type": "Pallet OUT",
                "id": detail.get("id", ""),
                "qty": detail.get("qty", 0),
                "products": detail.get("products", ""),
                "date": detail.get("date", ""),
                "lots": detail.get("lots", "")
            }
        elif node_type == "PROCESS":
            nivo_node["label"] = f"🔴 {detail.get('ref', 'Proceso')}"
            nivo_node["metadata"] = {
                "type": "Proceso",
                "ref": detail.get("ref", ""),
                "date": detail.get("date", ""),
                "mrp_start": detail.get("mrp_start", ""),
                "mrp_end": detail.get("mrp_end", ""),
                "product": detail.get("product", "")
            }
        elif node_type == "CUSTOMER":
            nivo_node["label"] = f"🔵 {detail.get('name', 'Cliente')}"
            nivo_node["metadata"] = {
                "type": "Cliente",
                "name": detail.get("name", ""),
                "date": detail.get("date", "")
            }
        else:
            nivo_node["label"] = node.get("label", f"Nodo {idx}")
            nivo_node["metadata"] = {"type": "Unknown"}
        
        nivo_nodes.append(nivo_node)
    
    # Crear links usando IDs de string
    nivo_links = []
    for link in links_plotly:
        source_idx = link.get("source")
        target_idx = link.get("target")
        value = link.get("value", 0)
        color = link.get("color", "rgba(200,200,200,0.4)")
        
        if source_idx in node_id_map and target_idx in node_id_map:
            nivo_links.append({
                "source": node_id_map[source_idx],
                "target": node_id_map[target_idx],
                "value": value,
                "color": color
            })
    
    return {
        "nodes": nivo_nodes,
        "links": nivo_links
    }


def _generate_nivo_html(data: Dict, height: int) -> str:
    """
    Genera el HTML completo con React + Nivo Sankey.
    """
    data_json = json.dumps(data, ensure_ascii=False)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
        <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
        <script src="https://unpkg.com/@nivo/core@0.87.0/dist/nivo-core.umd.js"></script>
        <script src="https://unpkg.com/@nivo/sankey@0.87.0/dist/nivo-sankey.umd.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background-color: transparent;
            }}
            #root {{
                width: 100%;
                height: {height}px;
            }}
            .tooltip {{
                background: white;
                padding: 12px;
                border-radius: 4px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                font-size: 12px;
                line-height: 1.6;
                max-width: 300px;
            }}
            .tooltip-title {{
                font-weight: 600;
                margin-bottom: 8px;
                font-size: 14px;
                color: #333;
            }}
            .tooltip-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 4px;
            }}
            .tooltip-label {{
                color: #666;
                margin-right: 12px;
            }}
            .tooltip-value {{
                color: #000;
                font-weight: 500;
            }}
        </style>
    </head>
    <body>
        <div id="root"></div>
        <script>
            const {{ ResponsiveSankey }} = window.nivo.Sankey;
            const {{ createElement }} = window.React;
            const {{ createRoot }} = window.ReactDOM;
            
            const data = {data_json};
            
            // Custom tooltip
            const CustomTooltip = ({{ node }}) => {{
                const metadata = node.nodeColor ? node : null;
                if (!metadata) return null;
                
                const meta = data.nodes.find(n => n.id === node.id)?.metadata || {{}};
                
                return createElement('div', {{ className: 'tooltip' }}, [
                    createElement('div', {{ className: 'tooltip-title', key: 'title' }}, 
                        data.nodes.find(n => n.id === node.id)?.label || node.id
                    ),
                    meta.type && createElement('div', {{ className: 'tooltip-row', key: 'type' }}, [
                        createElement('span', {{ className: 'tooltip-label' }}, 'Tipo:'),
                        createElement('span', {{ className: 'tooltip-value' }}, meta.type)
                    ]),
                    meta.date && createElement('div', {{ className: 'tooltip-row', key: 'date' }}, [
                        createElement('span', {{ className: 'tooltip-label' }}, 'Fecha:'),
                        createElement('span', {{ className: 'tooltip-value' }}, meta.date)
                    ]),
                    meta.date_done && createElement('div', {{ className: 'tooltip-row', key: 'date_done' }}, [
                        createElement('span', {{ className: 'tooltip-label' }}, 'Fecha realización:'),
                        createElement('span', {{ className: 'tooltip-value' }}, meta.date_done)
                    ]),
                    meta.qty && createElement('div', {{ className: 'tooltip-row', key: 'qty' }}, [
                        createElement('span', {{ className: 'tooltip-label' }}, 'Cantidad:'),
                        createElement('span', {{ className: 'tooltip-value' }}, meta.qty.toFixed(2) + ' kg')
                    ]),
                    meta.products && createElement('div', {{ className: 'tooltip-row', key: 'products' }}, [
                        createElement('span', {{ className: 'tooltip-label' }}, 'Productos:'),
                        createElement('span', {{ className: 'tooltip-value' }}, meta.products)
                    ]),
                    meta.lots && createElement('div', {{ className: 'tooltip-row', key: 'lots' }}, [
                        createElement('span', {{ className: 'tooltip-label' }}, 'Lotes:'),
                        createElement('span', {{ className: 'tooltip-value' }}, meta.lots)
                    ]),
                    meta.mrp_start && createElement('div', {{ className: 'tooltip-row', key: 'mrp_start' }}, [
                        createElement('span', {{ className: 'tooltip-label' }}, 'Inicio MRP:'),
                        createElement('span', {{ className: 'tooltip-value' }}, meta.mrp_start)
                    ]),
                    meta.mrp_end && createElement('div', {{ className: 'tooltip-row', key: 'mrp_end' }}, [
                        createElement('span', {{ className: 'tooltip-label' }}, 'Fin MRP:'),
                        createElement('span', {{ className: 'tooltip-value' }}, meta.mrp_end)
                    ]),
                    meta.product && createElement('div', {{ className: 'tooltip-row', key: 'product' }}, [
                        createElement('span', {{ className: 'tooltip-label' }}, 'Producto:'),
                        createElement('span', {{ className: 'tooltip-value' }}, meta.product)
                    ]),
                    meta.supplier && createElement('div', {{ className: 'tooltip-row', key: 'supplier' }}, [
                        createElement('span', {{ className: 'tooltip-label' }}, 'Proveedor:'),
                        createElement('span', {{ className: 'tooltip-value' }}, meta.supplier)
                    ])
                ].filter(Boolean));
            }};
            
            // Custom label
            const CustomLabel = ({{ node }}) => {{
                const nodeData = data.nodes.find(n => n.id === node.id);
                const label = nodeData?.label || node.id;
                
                // Truncar si es muy largo
                const displayLabel = label.length > 20 ? label.substring(0, 18) + '...' : label;
                
                return createElement('text', {{
                    x: node.x,
                    y: node.y,
                    textAnchor: 'middle',
                    dominantBaseline: 'central',
                    style: {{
                        fontSize: '11px',
                        fontWeight: 500,
                        fill: '#333',
                        pointerEvents: 'none'
                    }}
                }}, displayLabel);
            }};
            
            const SankeyChart = () => {{
                return createElement(ResponsiveSankey, {{
                    data: data,
                    layout: 'vertical',  // VERTICAL orientation
                    align: 'justify',
                    colors: {{ scheme: 'category10' }},
                    nodeColor: node => {{
                        const nodeData = data.nodes.find(n => n.id === node.id);
                        return nodeData?.nodeColor || '#cccccc';
                    }},
                    nodeOpacity: 1,
                    nodeHoverOpacity: 1,
                    nodeThickness: 18,
                    nodeSpacing: 24,
                    nodeBorderWidth: 0,
                    nodeBorderRadius: 3,
                    linkOpacity: 0.5,
                    linkHoverOpacity: 0.8,
                    linkContract: 0,
                    linkBlendMode: 'multiply',
                    linkColor: link => {{
                        const linkData = data.links.find(l => 
                            l.source === link.source.id && l.target === link.target.id
                        );
                        return linkData?.color || 'rgba(200,200,200,0.4)';
                    }},
                    enableLinkGradient: true,
                    label: CustomLabel,
                    labelPosition: 'inside',
                    labelOrientation: 'horizontal',
                    labelPadding: 16,
                    labelTextColor: '#333333',
                    nodeTooltip: CustomTooltip,
                    animate: true,
                    motionConfig: 'gentle',
                    margin: {{ top: 20, right: 160, bottom: 20, left: 160 }}
                }});
            }};
            
            const container = document.getElementById('root');
            const root = createRoot(container);
            root.render(createElement(SankeyChart));
        </script>
    </body>
    </html>
    """
    
    return html

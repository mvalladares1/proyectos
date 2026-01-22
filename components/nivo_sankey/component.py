"""
Renderizador de Sankey usando D3.js (orientación vertical).
D3 tiene excelente soporte de CDN y funciona sin necesidad de build.
"""
import streamlit as st
import streamlit.components.v1 as components
import json
from typing import Dict

NIVO_AVAILABLE = True  # Mantenemos el nombre por compatibilidad


def render_nivo_sankey(data: Dict, height: int = 800):
    """
    Renderiza un diagrama Sankey usando D3.js en orientación vertical.
    
    Args:
        data: Diccionario con 'nodes' y 'links' en formato Plotly
        height: Altura del diagrama en pixels
    """
    if not data or not data.get("nodes"):
        st.warning("No hay datos para renderizar")
        return
    
    # Transformar datos de formato Plotly a formato D3
    d3_data = _transform_to_d3_format(data)
    
    # Generar HTML con D3
    html_content = _generate_d3_sankey_html(d3_data, height)
    
    # Renderizar
    components.html(html_content, height=height + 50, scrolling=True)


def _transform_to_d3_format(plotly_data: Dict) -> Dict:
    """
    Transforma datos de formato Plotly Sankey a formato D3-sankey.
    """
    nodes_plotly = plotly_data.get("nodes", [])
    links_plotly = plotly_data.get("links", [])
    
    # Crear nodos (filtrar recepciones y remapear índices)
    d3_nodes = []
    original_to_new_idx = {}  # Mapeo de índice original -> nuevo índice
    
    for idx, node in enumerate(nodes_plotly):
        detail = node.get("detail", {})
        node_type = detail.get("type", "UNKNOWN")
        
        # SALTAR nodos de RECEPCIÓN
        if node_type == "RECEPTION":
            continue
        
        # Guardar mapeo de índices
        new_idx = len(d3_nodes)
        original_to_new_idx[idx] = new_idx
        
        d3_node = {
            "id": new_idx,
            "color": node.get("color", "#cccccc"),
            "date": detail.get("date", detail.get("mrp_start", "9999-99-99")),  # Fecha para ordenar
        }
        
        # Agregar metadata para tooltips
        if node_type == "SUPPLIER":
            d3_node["name"] = f"🏭 {detail.get('name', 'Proveedor')}"
            d3_node["tooltip"] = f"<strong>Proveedor</strong><br/>{detail.get('name', '')}"
            if detail.get("date"):
                d3_node["tooltip"] += f"<br/>Fecha: {detail.get('date')}"
        elif node_type == "PALLET_IN":
            # Usar el NOMBRE del pallet de los datos del backend
            pallet_name = nodes_plotly[idx].get("label", "").replace("🟠 ", "")
            d3_node["name"] = f"🟠 {pallet_name}"
            d3_node["tooltip"] = f"<strong>Pallet IN</strong><br/>Nombre: {pallet_name}"
            if detail.get("qty"):
                d3_node["tooltip"] += f"<br/>Cantidad: {detail.get('qty'):.0f} kg"
            if detail.get("date"):
                d3_node["tooltip"] += f"<br/>Fecha: {detail.get('date')}"
            if detail.get("products"):
                d3_node["tooltip"] += f"<br/>Productos: {detail.get('products')}"
        elif node_type == "PALLET_OUT":
            # Usar el NOMBRE del pallet de los datos del backend
            pallet_name = nodes_plotly[idx].get("label", "").replace("🟢 ", "")
            d3_node["name"] = f"🟢 {pallet_name}"
            d3_node["tooltip"] = f"<strong>Pallet OUT</strong><br/>Nombre: {pallet_name}"
            if detail.get("qty"):
                d3_node["tooltip"] += f"<br/>Cantidad: {detail.get('qty'):.0f} kg"
            if detail.get("date"):
                d3_node["tooltip"] += f"<br/>Fecha: {detail.get('date')}"
            if detail.get("products"):
                d3_node["tooltip"] += f"<br/>Productos: {detail.get('products')}"
        elif node_type == "PROCESS":
            d3_node["name"] = f"🔴 {detail.get('ref', 'Proceso')}"
            d3_node["tooltip"] = f"<strong>Proceso</strong><br/>{detail.get('ref', '')}"
            if detail.get("date"):
                d3_node["tooltip"] += f"<br/>Fecha: {detail.get('date')}"
            if detail.get("mrp_start"):
                d3_node["tooltip"] += f"<br/>Inicio MRP: {detail.get('mrp_start')}"
            if detail.get("mrp_end"):
                d3_node["tooltip"] += f"<br/>Fin MRP: {detail.get('mrp_end')}"
            if detail.get("product"):
                d3_node["tooltip"] += f"<br/>Producto: {detail.get('product')}"
        elif node_type == "CUSTOMER":
            d3_node["name"] = f"🔵 {detail.get('name', 'Cliente')}"
            d3_node["tooltip"] = f"<strong>Cliente</strong><br/>{detail.get('name', '')}"
            if detail.get("date"):
                d3_node["tooltip"] += f"<br/>Fecha: {detail.get('date')}"
        else:
            d3_node["name"] = node.get("label", f"Nodo {idx}")
            d3_node["tooltip"] = d3_node["name"]
        
        d3_nodes.append(d3_node)
    
    # Crear links (D3 usa índices numéricos) - remapear índices
    d3_links = []
    for link in links_plotly:
        source_idx = link.get("source")
        target_idx = link.get("target")
        value = link.get("value", 1)
        
        # Verificar que ambos índices existen en el mapeo (no fueron filtrados)
        if source_idx in original_to_new_idx and target_idx in original_to_new_idx:
            d3_links.append({
                "source": original_to_new_idx[source_idx],
                "target": original_to_new_idx[target_idx],
                "value": max(value, 1)  # D3 necesita value > 0
            })
    
    return {
        "nodes": d3_nodes,
        "links": d3_links
    }


def _generate_d3_sankey_html(data: Dict, height: int) -> str:
    """
    Genera el HTML completo con D3.js Sankey en orientación VERTICAL.
    """
    data_json = json.dumps(data, ensure_ascii=False)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <script src="https://unpkg.com/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 10px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background-color: #fafafa;
            }}
            #chart {{
                width: 100%;
                height: {height}px;
            }}
            .node rect {{
                cursor: pointer;
                stroke-width: 0.5px;
            }}
            .node text {{
                font-size: 9px;
                fill: #333;
                pointer-events: none;
            }}
            .link {{
                fill-opacity: 0.4;
            }}
            .link:hover {{
                fill-opacity: 0.7;
            }}
            .tooltip {{
                position: absolute;
                background: white;
                padding: 10px 14px;
                border-radius: 6px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.15);
                font-size: 12px;
                line-height: 1.5;
                pointer-events: none;
                z-index: 1000;
                max-width: 280px;
            }}
        </style>
    </head>
    <body>
        <div id="chart"></div>
        <div id="tooltip" class="tooltip" style="display: none;"></div>
        
        <script>
            const data = {data_json};
            
            const container = document.getElementById('chart');
            const width = container.clientWidth || 1200;
            const height = {height};
            
            // Márgenes para etiquetas y eje temporal
            const margin = {{ top: 30, right: 20, bottom: 70, left: 20 }};
            const innerWidth = width - margin.left - margin.right;
            const innerHeight = height - margin.top - margin.bottom;
            
            // Crear SVG
            const svg = d3.select('#chart')
                .append('svg')
                .attr('width', width)
                .attr('height', height);
            
            const g = svg.append('g')
                .attr('transform', `translate(${{margin.left}},${{margin.top}})`);
            
            // Tooltip
            const tooltip = d3.select('#tooltip');
            
            // Configurar Sankey - usamos configuración horizontal y luego rotamos
            const sankey = d3.sankey()
                .nodeId(d => d.id)
                .nodeWidth(15)
                .nodePadding(12)
                .nodeAlign(d3.sankeyJustify)
                .nodeSort((a, b) => {{
                    // Ordenar nodos por fecha (eje X = línea de tiempo)
                    const dateA = a.date || '9999-99-99';
                    const dateB = b.date || '9999-99-99';
                    return dateA.localeCompare(dateB);
                }})
                .extent([[0, 0], [innerHeight, innerWidth]]);  // Intercambiado para vertical
            
            // Clonar datos
            const graph = sankey({{
                nodes: data.nodes.map(d => ({{...d}})),
                links: data.links.map(d => ({{...d}}))
            }});
            
            // Rotar coordenadas para orientación vertical
            // x -> y, y -> x
            graph.nodes.forEach(node => {{
                const x0 = node.x0, x1 = node.x1, y0 = node.y0, y1 = node.y1;
                node.x0 = y0;
                node.x1 = y1;
                node.y0 = x0;
                node.y1 = x1;
            }});
            
            // Función para dibujar links verticales
            function verticalLink(d) {{
                const x0 = d.source.x0 + (d.source.x1 - d.source.x0) / 2;
                const x1 = d.target.x0 + (d.target.x1 - d.target.x0) / 2;
                const y0 = d.source.y1;
                const y1 = d.target.y0;
                const curvature = 0.5;
                const yi = d3.interpolateNumber(y0, y1);
                const y2 = yi(curvature);
                const y3 = yi(1 - curvature);
                const halfWidth = Math.max(1, d.width / 2);
                
                return `M${{x0 - halfWidth}},${{y0}}
                        C${{x0 - halfWidth}},${{y2}} ${{x1 - halfWidth}},${{y3}} ${{x1 - halfWidth}},${{y1}}
                        L${{x1 + halfWidth}},${{y1}}
                        C${{x1 + halfWidth}},${{y3}} ${{x0 + halfWidth}},${{y2}} ${{x0 + halfWidth}},${{y0}}
                        Z`;
            }}
            
            // Dibujar links
            const link = g.append('g')
                .attr('class', 'links')
                .selectAll('path')
                .data(graph.links)
                .join('path')
                .attr('class', 'link')
                .attr('d', verticalLink)
                .attr('fill', d => d.source.color || '#aaa')
                .attr('stroke', 'none')
                .on('mouseover', function(event, d) {{
                    d3.select(this).attr('fill-opacity', 0.7);
                    tooltip
                        .style('display', 'block')
                        .html(`<strong>${{d.source.name}} → ${{d.target.name}}</strong><br/>Cantidad: ${{d.value.toLocaleString()}} kg`)
                        .style('left', (event.pageX + 10) + 'px')
                        .style('top', (event.pageY - 10) + 'px');
                }})
                .on('mousemove', function(event) {{
                    tooltip
                        .style('left', (event.pageX + 10) + 'px')
                        .style('top', (event.pageY - 10) + 'px');
                }})
                .on('mouseout', function() {{
                    d3.select(this).attr('fill-opacity', 0.4);
                    tooltip.style('display', 'none');
                }});
            
            // Dibujar nodos
            const node = g.append('g')
                .attr('class', 'nodes')
                .selectAll('g')
                .data(graph.nodes)
                .join('g')
                .attr('class', 'node');
            
            node.append('rect')
                .attr('x', d => d.x0)
                .attr('y', d => d.y0)
                .attr('width', d => Math.max(1, d.x1 - d.x0))
                .attr('height', d => Math.max(1, d.y1 - d.y0))
                .attr('fill', d => d.color || '#69b3a2')
                .attr('stroke', '#333')
                .attr('stroke-width', 0.5)
                .attr('rx', 2)
                .attr('ry', 2)
                .on('mouseover', function(event, d) {{
                    d3.select(this).attr('opacity', 0.8);
                    tooltip
                        .style('display', 'block')
                        .html(d.tooltip || d.name)
                        .style('left', (event.pageX + 10) + 'px')
                        .style('top', (event.pageY - 10) + 'px');
                }})
                .on('mousemove', function(event) {{
                    tooltip
                        .style('left', (event.pageX + 10) + 'px')
                        .style('top', (event.pageY - 10) + 'px');
                }})
                .on('mouseout', function() {{
                    d3.select(this).attr('opacity', 1);
                    tooltip.style('display', 'none');
                }});
            
            // Etiquetas de nodos (arriba de cada nodo) - ROTADAS VERTICALMENTE
            node.append('text')
                .attr('x', d => (d.x0 + d.x1) / 2)
                .attr('y', d => d.y0 - 10)
                .attr('text-anchor', 'middle')
                .attr('transform', d => {{
                    const x = (d.x0 + d.x1) / 2;
                    const y = d.y0 - 10;
                    return `rotate(-45, ${{x}}, ${{y}})`;
                }})
                .attr('font-size', '10px')
                .attr('fill', '#333')
                .attr('font-weight', '500')
                .text(d => {{
                    const name = d.name || '';
                    return name.length > 25 ? name.substring(0, 23) + '...' : name;
                }});
            
            // Crear eje temporal debajo del diagrama
            // Extraer fechas válidas de los nodos
            const validDates = graph.nodes
                .map(d => d.date)
                .filter(date => date && date !== '9999-99-99')
                .map(date => new Date(date));
            
            if (validDates.length > 0) {{
                const minDate = d3.min(validDates);
                const maxDate = d3.max(validDates);
                
                // Escala temporal
                const timeScale = d3.scaleTime()
                    .domain([minDate, maxDate])
                    .range([0, innerWidth]);
                
                // Crear eje temporal
                const timeAxis = d3.axisBottom(timeScale)
                    .ticks(d3.timeMonth, 1)
                    .tickFormat(d3.timeFormat('%b %Y'));
                
                // Agregar grupo para el eje
                const axisGroup = g.append('g')
                    .attr('class', 'time-axis')
                    .attr('transform', `translate(0, ${{innerHeight + 20}})`)
                    .call(timeAxis);
                
                // Estilizar el eje
                axisGroup.selectAll('text')
                    .attr('font-size', '11px')
                    .attr('fill', '#666')
                    .style('text-anchor', 'middle');
                
                axisGroup.selectAll('line')
                    .attr('stroke', '#999');
                
                axisGroup.select('.domain')
                    .attr('stroke', '#999');
                    
                // Etiqueta del eje
                g.append('text')
                    .attr('x', innerWidth / 2)
                    .attr('y', innerHeight + 55)
                    .attr('text-anchor', 'middle')
                    .attr('font-size', '12px')
                    .attr('font-weight', 'bold')
                    .attr('fill', '#333')
                    .text('📅 Línea de Tiempo');
            }}
        </script>
    </body>
    </html>
    """
    
    return html

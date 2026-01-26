"""
Renderizador de Sankey usando D3.js (orientación vertical).
D3 tiene excelente soporte de CDN y funciona sin necesidad de build.
"""
import streamlit as st
import streamlit.components.v1 as components
import json
from typing import Dict

NIVO_AVAILABLE = True  # Mantenemos el nombre por compatibilidad


def render_nivo_sankey(data: dict, height: int = 800, highlight_package: str = None):
    """
    Renderiza un diagrama Sankey usando D3.js en orientación vertical.
    
    Args:
        data: Diccionario con 'nodes' y 'links' en formato Plotly Sankey
        height: Altura del diagrama en píxeles
        highlight_package: ID del paquete a resaltar (opcional)
    """
    if not data or not data.get("nodes"):
        st.warning("No hay datos para renderizar")
        return
    
    # Transformar datos de formato Plotly a formato D3
    d3_data = _transform_to_d3_format(data, highlight_package)
    
    # Generar HTML con D3
    html_content = _generate_d3_sankey_html(d3_data, height)
    
    # Renderizar
    components.html(html_content, height=height + 50, scrolling=True)


def _transform_to_d3_format(plotly_data: dict, highlight_package: str = None) -> dict:
    """
    Transforma datos de formato Plotly Sankey a formato D3-sankey.
    
    Args:
        plotly_data: Datos en formato Plotly
        highlight_package: Nombre del paquete a resaltar (sin emojis)
        show_receptions: Si True, incluye nodos de recepción en el diagrama
    """
    nodes_plotly = plotly_data.get("nodes", [])
    links_plotly = plotly_data.get("links", [])
    
    # Crear nodos (filtrar recepciones según parámetro y remapear índices)
    d3_nodes = []
    original_to_new_idx = {}  # Mapeo de índice original -> nuevo índice
    
    for idx, node in enumerate(nodes_plotly):
        detail = node.get("detail", {})
        node_type = detail.get("type", "UNKNOWN")
        
        # Guardar mapeo de índices
        new_idx = len(d3_nodes)
        original_to_new_idx[idx] = new_idx
        
        d3_node = {
            "id": new_idx,
            "color": node.get("color", "#cccccc"),
            "date": detail.get("date", detail.get("mrp_start", "9999-99-99")),  # Fecha para ordenar
            "node_type": node_type,  # Agregar tipo de nodo para rotación condicional
        }
        
        # Agregar metadata para tooltips
        if node_type == "SUPPLIER":
            d3_node["name"] = f"🏭 {detail.get('name', 'Proveedor')}"
            tooltip_parts = [f"<strong>Proveedor</strong><br/>{detail.get('name', '')}"]
            if detail.get("albaran"):
                tooltip_parts.append(f"Albarán: {detail.get('albaran')}")
            if detail.get("guia_despacho"):
                tooltip_parts.append(f"Guía: {detail.get('guia_despacho')}")
            if detail.get("origen"):
                tooltip_parts.append(f"Origen: {detail.get('origen')}")
            if detail.get("transportista"):
                tooltip_parts.append(f"Transportista: {detail.get('transportista')}")
            if detail.get("date"):
                tooltip_parts.append(f"Fecha: {detail.get('date')}")
            d3_node["tooltip"] = "<br/>".join(tooltip_parts)
        elif node_type == "RECEPTION":
            d3_node["name"] = f"📥"
            tooltip_parts = [f"<strong>Recepción</strong><br/>{detail.get('name', '')}"]
            if detail.get("albaran"):
                tooltip_parts.append(f"Albarán: {detail.get('albaran')}")
            if detail.get("guia_despacho"):
                tooltip_parts.append(f"Guía: {detail.get('guia_despacho')}")
            if detail.get("origen"):
                tooltip_parts.append(f"Origen: {detail.get('origen')}")
            if detail.get("transportista"):
                tooltip_parts.append(f"Transportista: {detail.get('transportista')}")
            if detail.get("date"):
                tooltip_parts.append(f"Fecha: {detail.get('date')}")
            d3_node["tooltip"] = "<br/>".join(tooltip_parts)
        elif node_type == "PALLET_IN":
            # Usar el NOMBRE del pallet de los datos del backend
            pallet_name = nodes_plotly[idx].get("label", "").replace("🟠 ", "")
            d3_node["name"] = pallet_name
            
            # Marcar si es el paquete buscado
            is_highlighted = False
            if highlight_package:
                # Comparar sin case-sensitive y sin espacios extra
                if pallet_name.strip().lower() == highlight_package.strip().lower():
                    is_highlighted = True
                    d3_node["color"] = "#FFD700"  # Dorado brillante
                    d3_node["highlight"] = True
            
            d3_node["tooltip"] = f"<strong>Pallet IN</strong><br/>Nombre: {pallet_name}"
            if is_highlighted:
                d3_node["tooltip"] = f"<strong>⭐</strong><br/>Nombre: {pallet_name}"
            if detail.get("qty"):
                d3_node["tooltip"] += f"<br/>Cantidad: {detail.get('qty'):.0f} kg"
            if detail.get("date"):
                d3_node["tooltip"] += f"<br/>Fecha: {detail.get('date')}"
            if detail.get("products"):
                d3_node["tooltip"] += f"<br/>Productos: {detail.get('products')}"
        elif node_type == "PALLET_OUT":
            # Usar el NOMBRE del pallet de los datos del backend
            pallet_name = nodes_plotly[idx].get("label", "").replace("🟢 ", "")
            d3_node["name"] = pallet_name
            
            # Marcar si es el paquete buscado
            is_highlighted = False
            if highlight_package:
                # Comparar sin case-sensitive y sin espacios extra
                if pallet_name.strip().lower() == highlight_package.strip().lower():
                    is_highlighted = True
                    d3_node["color"] = "#FFD700"  # Dorado brillante
                    d3_node["highlight"] = True
            
            d3_node["tooltip"] = f"<strong>Pallet OUT</strong><br/>Nombre: {pallet_name}"
            if is_highlighted:
                d3_node["tooltip"] = f"<strong>⭐</strong><br/>Nombre: {pallet_name}"
            if detail.get("qty"):
                d3_node["tooltip"] += f"<br/>Cantidad: {detail.get('qty'):.0f} kg"
            if detail.get("date"):
                d3_node["tooltip"] += f"<br/>Fecha: {detail.get('date')}"
            if detail.get("products"):
                d3_node["tooltip"] += f"<br/>Productos: {detail.get('products')}"
        elif node_type == "PROCESS":
            d3_node["name"] = detail.get('ref', 'Proceso')
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
            d3_node["name"] = detail.get('name', 'Cliente')
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
    Genera el HTML con D3 Sankey donde los nodos se posicionan en X según su fecha.
    Usa d3-sankey para el layout vertical y grosor de links, pero posición X temporal.
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
                overflow: visible;
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
                fill-opacity: 0.35;
            }}
            .link:hover {{
                fill-opacity: 0.6;
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
                max-width: 300px;
            }}
            .zoom-controls {{
                position: absolute;
                top: 10px;
                right: 20px;
                display: flex;
                gap: 5px;
                z-index: 100;
            }}
            .zoom-btn {{
                width: 32px;
                height: 32px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: white;
                cursor: pointer;
                font-size: 18px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .zoom-btn:hover {{
                background: #f0f0f0;
            }}
            .time-axis text {{
                font-size: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="zoom-controls">
            <button class="zoom-btn" id="zoom-in" title="Acercar">+</button>
            <button class="zoom-btn" id="zoom-out" title="Alejar">−</button>
            <button class="zoom-btn" id="zoom-reset" title="Restablecer">⟲</button>
        </div>
        <div id="chart"></div>
        <div id="tooltip" class="tooltip" style="display: none;"></div>
        
        <script>
            const data = {data_json};
            
            const container = document.getElementById('chart');
            const width = container.clientWidth || 1400;
            const height = {height};
            
            const margin = {{ top: 70, right: 120, bottom: 40, left: 120 }};
            const innerWidth = width - margin.left - margin.right;
            const innerHeight = height - margin.top - margin.bottom;
            
            const tooltip = d3.select('#tooltip');
            
            // ============================================================
            // PASO 1: Crear escala temporal en eje X
            // ============================================================
            const validDates = data.nodes
                .map(d => d.date)
                .filter(date => date && date !== '9999-99-99')
                .map(date => new Date(date + 'T12:00:00'));
            
            if (validDates.length === 0) {{
                document.getElementById('chart').innerHTML = '<p style="padding:20px;">No hay fechas válidas para mostrar</p>';
                throw new Error('No valid dates');
            }}
            
            const minDate = d3.min(validDates);
            const maxDate = d3.max(validDates);
            
            const dayPadding = 1;
            const paddedMinDate = d3.timeDay.offset(minDate, -dayPadding);
            const paddedMaxDate = d3.timeDay.offset(maxDate, dayPadding);
            
            const timeScale = d3.scaleTime()
                .domain([paddedMinDate, paddedMaxDate])
                .range([0, innerWidth]);
            
            // ============================================================
            // PASO 2: Configurar Sankey para calcular layout vertical
            // ============================================================
            const nodeWidth = 18;
            
            const sankey = d3.sankey()
                .nodeId(d => d.id)
                .nodeWidth(nodeWidth)
                .nodePadding(15)
                .nodeAlign(d3.sankeyLeft)
                .nodeSort((a, b) => {{
                    // Ordenar por fecha primero, luego por tipo
                    const dateA = a.date || '9999-99-99';
                    const dateB = b.date || '9999-99-99';
                    if (dateA !== dateB) return dateA.localeCompare(dateB);
                    const typeOrder = {{'SUPPLIER': 0, 'PALLET_IN': 1, 'PROCESS': 2, 'PALLET_OUT': 3, 'CUSTOMER': 4}};
                    return (typeOrder[a.node_type] || 99) - (typeOrder[b.node_type] || 99);
                }})
                .extent([[0, 0], [innerWidth, innerHeight]]);
            
            // Clonar datos para sankey
            const graph = sankey({{
                nodes: data.nodes.map(d => ({{...d}})),
                links: data.links.map(d => ({{...d}}))
            }});
            
            // ============================================================
            // PASO 3: Sobreescribir posición X según fecha real
            // ============================================================
            graph.nodes.forEach(node => {{
                const dateStr = node.date || '9999-99-99';
                let x;
                if (dateStr === '9999-99-99') {{
                    x = innerWidth - 20;
                }} else {{
                    x = timeScale(new Date(dateStr + 'T12:00:00'));
                }}
                // Mantener altura calculada por sankey, pero mover X
                const originalWidth = node.x1 - node.x0;
                node.x0 = x - originalWidth / 2;
                node.x1 = x + originalWidth / 2;
            }});
            
            // ============================================================
            // PASO 4: Crear SVG
            // ============================================================
            const svg = d3.select('#chart')
                .append('svg')
                .attr('width', width)
                .attr('height', height);
            
            const g = svg.append('g')
                .attr('transform', `translate(${{margin.left}},${{margin.top}})`);
            
            const contentGroup = g.append('g').attr('class', 'content');
            
            // ============================================================
            // PASO 5: Eje temporal arriba
            // ============================================================
            const timeAxisGroup = g.append('g')
                .attr('class', 'time-axis')
                .attr('transform', `translate(0, -25)`);
            
            const timeGridGroup = contentGroup.append('g').attr('class', 'time-grid');
            
            function updateTimeline(transform) {{
                const newTimeScale = transform.rescaleX(timeScale);
                
                const daysDiff = (paddedMaxDate - paddedMinDate) / (1000 * 60 * 60 * 24);
                const effectiveRange = daysDiff / transform.k;
                
                let tickInterval, tickFormat;
                if (effectiveRange <= 7) {{
                    tickInterval = d3.timeDay;
                    tickFormat = d3.timeFormat('%d %b %Y');
                }} else if (effectiveRange <= 30) {{
                    tickInterval = d3.timeDay.every(2);
                    tickFormat = d3.timeFormat('%d %b');
                }} else if (effectiveRange <= 90) {{
                    tickInterval = d3.timeWeek;
                    tickFormat = d3.timeFormat('%d %b');
                }} else {{
                    tickInterval = d3.timeMonth;
                    tickFormat = d3.timeFormat('%b %Y');
                }}
                
                const timeAxis = d3.axisTop(newTimeScale)
                    .ticks(tickInterval)
                    .tickFormat(tickFormat);
                
                timeAxisGroup.call(timeAxis);
                timeAxisGroup.selectAll('text').attr('font-size', '10px').attr('fill', '#555');
                timeAxisGroup.selectAll('line').attr('stroke', '#bbb');
                timeAxisGroup.select('.domain').attr('stroke', '#bbb');
                
                const tickValues = newTimeScale.ticks(tickInterval);
                timeGridGroup.selectAll('line')
                    .data(tickValues)
                    .join('line')
                    .attr('x1', d => newTimeScale(d))
                    .attr('x2', d => newTimeScale(d))
                    .attr('y1', 0)
                    .attr('y2', innerHeight)
                    .attr('stroke', '#e8e8e8')
                    .attr('stroke-dasharray', '4,4');
            }}
            
            // ============================================================
            // PASO 6: Dibujar links con curvas Sankey horizontales
            // ============================================================
            function sankeyLinkHorizontal(d) {{
                const x0 = d.source.x1;
                const x1 = d.target.x0;
                const y0 = d.y0;
                const y1 = d.y1;
                const xi = d3.interpolateNumber(x0, x1);
                const x2 = xi(0.5);
                const x3 = xi(0.5);
                
                return `M${{x0}},${{y0}}
                        C${{x2}},${{y0}} ${{x3}},${{y1}} ${{x1}},${{y1}}`;
            }}
            
            const linkGroup = contentGroup.append('g').attr('class', 'links');
            
            linkGroup.selectAll('path')
                .data(graph.links)
                .join('path')
                .attr('class', 'link')
                .attr('d', d3.sankeyLinkHorizontal())
                .attr('stroke', d => d.source.color || '#aaa')
                .attr('stroke-width', d => Math.max(1, d.width))
                .attr('fill', 'none')
                .attr('stroke-opacity', 0.4)
                .on('mouseover', function(event, d) {{
                    d3.select(this).attr('stroke-opacity', 0.7);
                    tooltip
                        .style('display', 'block')
                        .html(`<strong>${{d.source.name}}</strong><br/>↓<br/><strong>${{d.target.name}}</strong><br/><br/>Cantidad: ${{d.value.toLocaleString()}} kg`)
                        .style('left', (event.pageX + 15) + 'px')
                        .style('top', (event.pageY - 15) + 'px');
                }})
                .on('mousemove', function(event) {{
                    tooltip
                        .style('left', (event.pageX + 15) + 'px')
                        .style('top', (event.pageY - 15) + 'px');
                }})
                .on('mouseout', function() {{
                    d3.select(this).attr('stroke-opacity', 0.4);
                    tooltip.style('display', 'none');
                }});
            
            // ============================================================
            // PASO 7: Dibujar nodos
            // ============================================================
            const nodeGroup = contentGroup.append('g').attr('class', 'nodes');
            
            const node = nodeGroup.selectAll('g')
                .data(graph.nodes)
                .join('g')
                .attr('class', 'node');
            
            node.append('rect')
                .attr('x', d => d.x0)
                .attr('y', d => d.y0)
                .attr('width', d => Math.max(4, d.x1 - d.x0))
                .attr('height', d => Math.max(4, d.y1 - d.y0))
                .attr('fill', d => d.color || '#69b3a2')
                .attr('stroke', d => d.highlight ? '#FF6B00' : '#444')
                .attr('stroke-width', d => d.highlight ? 3 : 0.5)
                .attr('rx', 2)
                .style('filter', d => d.highlight ? 'drop-shadow(0 0 8px #FFD700)' : 'none')
                .on('mouseover', function(event, d) {{
                    d3.select(this).attr('opacity', 0.8);
                    tooltip
                        .style('display', 'block')
                        .html(d.tooltip || d.name)
                        .style('left', (event.pageX + 15) + 'px')
                        .style('top', (event.pageY - 15) + 'px');
                }})
                .on('mousemove', function(event) {{
                    tooltip
                        .style('left', (event.pageX + 15) + 'px')
                        .style('top', (event.pageY - 15) + 'px');
                }})
                .on('mouseout', function() {{
                    d3.select(this).attr('opacity', 1);
                    tooltip.style('display', 'none');
                }});
            
            // Etiquetas
            node.append('text')
                .attr('x', d => d.x0 < innerWidth / 2 ? d.x1 + 6 : d.x0 - 6)
                .attr('y', d => (d.y0 + d.y1) / 2)
                .attr('dy', '0.35em')
                .attr('text-anchor', d => d.x0 < innerWidth / 2 ? 'start' : 'end')
                .attr('font-size', '9px')
                .attr('fill', '#333')
                .attr('font-weight', d => d.highlight ? 'bold' : '500')
                .text(d => {{
                    const name = d.name || '';
                    return name.length > 25 ? name.substring(0, 23) + '...' : name;
                }});
            
            // ============================================================
            // PASO 8: Zoom
            // ============================================================
            const zoom = d3.zoom()
                .scaleExtent([0.3, 4])
                .on('zoom', (event) => {{
                    contentGroup.attr('transform', event.transform);
                    updateTimeline(event.transform);
                }});
            
            svg.call(zoom);
            updateTimeline(d3.zoomIdentity);
            
            d3.select('#zoom-in').on('click', () => svg.transition().duration(300).call(zoom.scaleBy, 1.4));
            d3.select('#zoom-out').on('click', () => svg.transition().duration(300).call(zoom.scaleBy, 0.7));
            d3.select('#zoom-reset').on('click', () => svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity));
            
            // Título
            g.append('text')
                .attr('x', innerWidth / 2)
                .attr('y', -50)
                .attr('text-anchor', 'middle')
                .attr('font-size', '12px')
                .attr('font-weight', 'bold')
                .attr('fill', '#444')
                .text('📅 Línea de Tiempo');
        </script>
    </body>
    </html>
    """
    
    return html

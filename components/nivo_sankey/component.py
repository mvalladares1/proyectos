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
        
        # Extraer información de calidad de origen
        origin_quality = node.get("origin_quality", "")
        origin_process = node.get("origin_process", "")
        selection_reason = node.get("selection_reason", "")
        
        d3_node = {
            "id": new_idx,
            "color": node.get("color", "#cccccc"),
            "date": detail.get("date", detail.get("mrp_start", "9999-99-99")),  # Fecha para ordenar
            "node_type": node_type,  # Agregar tipo de nodo para rotación condicional
            "originQuality": origin_quality,
            "originProcess": origin_process,
            "selectionReason": selection_reason,
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
        <div class="filters" style="position: absolute; top: 10px; left: 10px; z-index: 100; background: rgba(255, 255, 255, 0.95); padding: 15px; border-radius: 8px; border: 1px solid #ddd;">
            <div style="font-weight: bold; margin-bottom: 10px; font-size: 14px; color: #333;">🔍 Filtros de Calidad</div>
            <label style="display: block; margin-bottom: 5px; cursor: pointer; user-select: none;">
                <input type="checkbox" id="filter-claro" checked onchange="applyOriginFilters()"> ✅ Origen Claro
            </label>
            <label style="display: block; margin-bottom: 5px; cursor: pointer; user-select: none;">
                <input type="checkbox" id="filter-ambiguo" checked onchange="applyOriginFilters()"> ⚠️ Origen Ambiguo
            </label>
            <label style="display: block; margin-bottom: 5px; cursor: pointer; user-select: none;">
                <input type="checkbox" id="filter-desconocido" checked onchange="applyOriginFilters()"> ❓ Origen Desconocido
            </label>
            <label style="display: block; margin-bottom: 5px; cursor: pointer; user-select: none;">
                <input type="checkbox" id="filter-sin-origen" checked onchange="applyOriginFilters()"> 🔴 Sin Origen
            </label>
            <label style="display: block; margin-bottom: 5px; cursor: pointer; user-select: none;">
                <input type="checkbox" id="filter-no-analizado" checked onchange="applyOriginFilters()"> ⚪ Sin Analizar
            </label>
        </div>
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
                .nodeAlign(d3.sankeyLeft)  // Alinear a la izquierda para respetar el orden temporal
                .nodeSort((a, b) => {{
                    const dateA = a.date || '9999-99-99';
                    const dateB = b.date || '9999-99-99';
                    return dateA.localeCompare(dateB);
                }})
                .extent([[0, 0], [innerHeight, innerWidth]]);  // Intercambiado para vertical
            
            // Debug: verificar datos
            console.log('Sankey data:', data);
            console.log('Nodes:', data.nodes.length, 'Links:', data.links.length);
            
            // Validar que hay nodos y links
            if (!data.nodes || data.nodes.length === 0) {{
                document.body.innerHTML = '<div style="padding: 20px; color: red;">Error: No hay nodos para renderizar</div>';
                throw new Error('No nodes to render');
            }}
            
            if (!data.links || data.links.length === 0) {{
                document.body.innerHTML = '<div style="padding: 20px; color: orange;">Advertencia: No hay links para renderizar</div>';
            }}
            
            // Detectar y eliminar ciclos usando algoritmo de Tarjan
            function detectAndBreakCycles(nodes, links) {{
                console.log('Iniciando detección de ciclos...');
                
                // Construir mapa de índices de nodos
                const nodeIndexMap = new Map();
                nodes.forEach((n, i) => nodeIndexMap.set(n.id, i));
                
                // Construir grafo de adyacencia con índices
                const adjacency = Array(nodes.length).fill(null).map(() => []);
                const linksByEdge = new Map();  // key: 'source->target', value: link
                
                links.forEach(link => {{
                    const sourceIdx = nodeIndexMap.get(link.source);
                    const targetIdx = nodeIndexMap.get(link.target);
                    
                    if (sourceIdx !== undefined && targetIdx !== undefined) {{
                        adjacency[sourceIdx].push(targetIdx);
                        linksByEdge.set(`${{sourceIdx}}->${{targetIdx}}`, link);
                    }}
                }});
                
                // DFS para detectar ciclos
                const WHITE = 0, GRAY = 1, BLACK = 2;
                const colors = Array(nodes.length).fill(WHITE);
                const cyclicEdges = new Set();
                
                function dfs(u) {{
                    colors[u] = GRAY;
                    
                    for (const v of adjacency[u]) {{
                        if (colors[v] === GRAY) {{
                            // Encontrado back edge (ciclo)
                            const edgeKey = `${{u}}->${{v}}`;
                            cyclicEdges.add(edgeKey);
                            console.log(`Ciclo detectado: ${{nodes[u].id}} -> ${{nodes[v].id}}`);
                        }} else if (colors[v] === WHITE) {{
                            dfs(v);
                        }}
                    }}
                    
                    colors[u] = BLACK;
                }}
                
                // Ejecutar DFS desde cada nodo no visitado
                for (let i = 0; i < nodes.length; i++) {{
                    if (colors[i] === WHITE) {{
                        dfs(i);
                    }}
                }}
                
                // Filtrar links que causan ciclos
                const cleanLinks = links.filter(link => {{
                    const sourceIdx = nodeIndexMap.get(link.source);
                    const targetIdx = nodeIndexMap.get(link.target);
                    const edgeKey = `${{sourceIdx}}->${{targetIdx}}`;
                    return !cyclicEdges.has(edgeKey);
                }});
                
                const removedCount = links.length - cleanLinks.length;
                if (removedCount > 0) {{
                    console.warn(`Removidos ${{removedCount}} links cíclicos`);
                }}
                
                return cleanLinks;
            }}
            
            // Clonar datos y limpiar ciclos
            let graph;
            try {{
                const clonedNodes = data.nodes.map(d => ({{...d}}));
                const clonedLinks = data.links.map(d => ({{...d}}));
                
                // Limpiar ciclos
                const cleanLinks = detectAndBreakCycles(clonedNodes, clonedLinks);
                
                console.log(`Procesando: ${{clonedNodes.length}} nodos, ${{cleanLinks.length}} links (removidos ${{clonedLinks.length - cleanLinks.length}} ciclos)`);
                
                graph = sankey({{
                    nodes: clonedNodes,
                    links: cleanLinks
                }});
                console.log('Sankey graph computed successfully');
            }} catch (error) {{
                console.error('Error computing sankey:', error);
                document.body.innerHTML = '<div style="padding: 20px; color: red;">Error al computar Sankey: ' + error.message + '<br/><br/>Esto puede deberse a ciclos en los datos. Revisa la consola para más detalles.</div>';
                throw error;
            }}
            
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
                .attr('stroke', d => d.highlight ? '#FF6B00' : '#333')
                .attr('stroke-width', d => d.highlight ? 4 : 0.5)
                .attr('rx', 2)
                .attr('ry', 2)
                .style('filter', d => d.highlight ? 'drop-shadow(0 0 10px #FFD700)' : 'none')
                .on('mouseover', function(event, d) {{
                    d3.select(this).attr('opacity', 0.8);
                    
                    // Construir tooltip con información de calidad de origen
                    let tooltipHtml = d.tooltip || d.name;
                    
                    if (d.originQuality) {{
                        // Agregar separador
                        tooltipHtml += '<hr style="margin: 5px 0; border: none; border-top: 1px solid #ddd;">';
                        
                        // Emoji según calidad
                        let emoji = '';
                        if (d.originQuality.includes('CLARO')) emoji = '✅';
                        else if (d.originQuality.includes('AMBIGUO')) emoji = '⚠️';
                        else if (d.originQuality.includes('DESCONOCIDO')) emoji = '❓';
                        else if (d.originQuality.includes('SIN_ORIGEN')) emoji = '🔴';
                        else if (d.originQuality === 'NO_ANALIZADO') emoji = '⚪';
                        
                        tooltipHtml += `<div style="margin-top: 5px;"><strong>${{emoji}} Calidad:</strong> ${{d.originQuality}}</div>`;
                        
                        if (d.originProcess) {{
                            tooltipHtml += `<div><strong>Proceso:</strong> ${{d.originProcess}}</div>`;
                        }}
                        
                        if (d.selectionReason) {{
                            tooltipHtml += `<div><strong>Razón:</strong> ${{d.selectionReason}}</div>`;
                        }}
                    }}
                    
                    tooltip
                        .style('display', 'block')
                        .html(tooltipHtml)
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
            
            // Etiquetas de nodos (arriba de cada nodo)
            node.append('text')
                .attr('x', d => (d.x0 + d.x1) / 2)
                .attr('y', d => d.y0 - 10)
                .attr('text-anchor', 'middle')
                .attr('transform', d => {{
                    const x = (d.x0 + d.x1) / 2;
                    const y = d.y0 - 10;
                    // Solo rotar pallets y procesos, NO proveedores ni clientes
                    const shouldRotate = d.node_type === 'PALLET_IN' || 
                                        d.node_type === 'PALLET_OUT' || 
                                        d.node_type === 'PROCESS';
                    if (shouldRotate) {{
                        return `rotate(-35, ${{x}}, ${{y}})`;
                    }}
                    return '';
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
            
            let timeScale, minDate, maxDate, timeAxisGroup, timeGridGroup, timeLabel;
            
            if (validDates.length > 0) {{
                minDate = d3.min(validDates);
                maxDate = d3.max(validDates);
                
                // Escala temporal
                timeScale = d3.scaleTime()
                    .domain([minDate, maxDate])
                    .range([0, innerWidth]);
                
                // Grupos para timeline (se actualizarán con zoom)
                timeGridGroup = g.append('g').attr('class', 'time-grid');
                timeAxisGroup = g.append('g')
                    .attr('class', 'time-axis')
                    .attr('transform', `translate(0, ${{innerHeight + 20}})`);
                
                // Etiqueta del eje
                timeLabel = g.append('text')
                    .attr('x', innerWidth / 2)
                    .attr('y', innerHeight + 55)
                    .attr('text-anchor', 'middle')
                    .attr('font-size', '12px')
                    .attr('font-weight', 'bold')
                    .attr('fill', '#333')
                    .text('📅 Línea de Tiempo');
            }}
            
            // Función para actualizar timeline según zoom
            function updateTimeline(zoomLevel) {{
                if (!timeScale) return;
                
                // Calcular rango en días
                const daysDiff = (maxDate - minDate) / (1000 * 60 * 60 * 24);
                
                // Determinar intervalo según zoom y rango de datos
                let tickInterval, tickFormat;
                const effectiveRange = daysDiff / zoomLevel;
                
                if (effectiveRange <= 3) {{
                    // Vista muy cercana: por día con hora
                    tickInterval = d3.timeDay;
                    tickFormat = d3.timeFormat('%d %b');
                }} else if (effectiveRange <= 14) {{
                    // Cercano: por día
                    tickInterval = d3.timeDay;
                    tickFormat = d3.timeFormat('%d %b');
                }} else if (effectiveRange <= 60) {{
                    // Medio: por semana
                    tickInterval = d3.timeWeek;
                    tickFormat = d3.timeFormat('%d %b');
                }} else if (effectiveRange <= 180) {{
                    // Alejado: por mes
                    tickInterval = d3.timeMonth;
                    tickFormat = d3.timeFormat('%b %Y');
                }} else {{
                    // Muy alejado: por mes
                    tickInterval = d3.timeMonth;
                    tickFormat = d3.timeFormat('%b %Y');
                }}
                
                // Actualizar eje
                const timeAxis = d3.axisBottom(timeScale)
                    .ticks(tickInterval, 1)
                    .tickFormat(tickFormat);
                
                timeAxisGroup.call(timeAxis);
                
                // Estilizar el eje
                timeAxisGroup.selectAll('text')
                    .attr('font-size', '11px')
                    .attr('fill', '#666')
                    .style('text-anchor', 'middle');
                
                timeAxisGroup.selectAll('line')
                    .attr('stroke', '#999');
                
                timeAxisGroup.select('.domain')
                    .attr('stroke', '#999');
                
                // Actualizar grid
                const tickValues = timeScale.ticks(tickInterval, 1);
                timeGridGroup.selectAll('line')
                    .data(tickValues)
                    .join('line')
                    .attr('x1', d => timeScale(d))
                    .attr('x2', d => timeScale(d))
                    .attr('y1', 0)
                    .attr('y2', innerHeight)
                    .attr('stroke', '#333')
                    .attr('stroke-width', 1)
                    .attr('opacity', 0.15)
                    .attr('stroke-dasharray', '4,4');
            }}
            
            // Inicializar timeline
            updateTimeline(1);
            applyOriginFilters();
            
            // Aplicar filtros de calidad de origen
            function applyOriginFilters() {{
                // Leer estado actual de los checkboxes
                const showClaro = document.getElementById('filter-claro').checked;
                const showAmbiguo = document.getElementById('filter-ambiguo').checked;
                const showDesconocido = document.getElementById('filter-desconocido').checked;
                const showSinOrigen = document.getElementById('filter-sin-origen').checked;
                const showNoAnalizado = document.getElementById('filter-no-analizado').checked;
                
                // Crear mapa de filtros
                const filters = {{
                    'ORIGEN_CLARO': showClaro,
                    'ORIGEN_CLARO_RECOVERED': showClaro,
                    'ORIGEN_AMBIGUO': showAmbiguo,
                    'ORIGEN_AMBIGUO_RECOVERED': showAmbiguo,
                    'ORIGEN_DESCONOCIDO': showDesconocido,
                    'ORIGEN_DESCONOCIDO_RECOVERED': showDesconocido,
                    'SIN_ORIGEN': showSinOrigen,
                    'NO_ANALIZADO': showNoAnalizado,
                    '': true  // Siempre mostrar nodos sin clasificación
                }};
                
                // Filtrar nodos
                node.style('opacity', d => {{
                    // Si el nodo no tiene originQuality, siempre mostrarlo
                    if (!d.originQuality || d.originQuality === '') return 1;
                    // Aplicar filtro según el estado del checkbox
                    return filters[d.originQuality] ? 1 : 0.1;
                }});
                
                // Filtrar links según visibilidad de nodos origen/destino
                link.style('fill-opacity', function(d) {{
                    const sourceVisible = !d.source.originQuality || 
                                        d.source.originQuality === '' || 
                                        filters[d.source.originQuality];
                    const targetVisible = !d.target.originQuality || 
                                        d.target.originQuality === '' || 
                                        filters[d.target.originQuality];
                    
                    return (sourceVisible && targetVisible) ? 0.4 : 0.05;
                }});
            }}
            
            // Configurar zoom DESPUÉS de dibujar todo
            let currentZoomLevel = 1;
            const zoom = d3.zoom()
                .scaleExtent([0.5, 10])
                .on('zoom', (event) => {{
                    currentZoomLevel = event.transform.k;
                    g.attr('transform', `translate(${{margin.left + event.transform.x}},${{margin.top + event.transform.y}}) scale(${{event.transform.k}})`);
                    updateTimeline(event.transform.k);
                }});
            
            svg.call(zoom);
            
            // Botones de zoom
            d3.select('#zoom-in').on('click', () => {{
                svg.transition().duration(300).call(zoom.scaleBy, 1.5);
            }});
            d3.select('#zoom-out').on('click', () => {{
                svg.transition().duration(300).call(zoom.scaleBy, 0.67);
            }});
            d3.select('#zoom-reset').on('click', () => {{
                svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
            }});
        </script>
    </body>
    </html>
    """
    
    return html

"""
Flow Timeline Component - Diagrama de flujo con eje temporal usando D3.js.

Características:
- Eje X: Fechas (timeline cronológico)
- Eje Y: Niveles del flujo (Proveedor → Pallet IN → Proceso → Pallet OUT → Cliente)
- Curvas estilo Sankey (Bézier)
- Múltiples nodos por fecha distribuidos verticalmente
- Timeline sincronizado con zoom
"""
import streamlit as st
import streamlit.components.v1 as components
from typing import Dict, List
import json
from datetime import datetime


# Niveles Y para cada tipo de nodo
NODE_LEVELS = {
    "SUPPLIER": 0,
    "RECEPTION": 1,
    "PALLET_IN": 2,
    "PROCESS": 3,
    "PALLET_OUT": 4,
    "CUSTOMER": 5,
}

LEVEL_NAMES = ["Proveedores", "Recepciones", "Pallets IN", "Procesos", "Pallets OUT", "Clientes"]

# Colores por tipo
NODE_COLORS = {
    "SUPPLIER": "#9b59b6",
    "RECEPTION": "#1abc9c",
    "PALLET_IN": "#f39c12", 
    "PROCESS": "#e74c3c",
    "PALLET_OUT": "#2ecc71",
    "CUSTOMER": "#3498db",
}


def _prepare_flow_data(data: Dict) -> Dict:
    """
    Prepara los datos para el Flow Timeline.
    Agrupa nodos por fecha y nivel, calcula posiciones.
    """
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    
    # Crear mapa de nodos por ID
    nodes_by_id = {n.get("id", ""): n for n in nodes}
    
    # Extraer fechas válidas y rango
    dates_set = set()
    for n in nodes:
        date_str = n.get("date", "")
        if date_str:
            try:
                datetime.strptime(date_str[:10], "%Y-%m-%d")
                dates_set.add(date_str[:10])
            except:
                pass
    
    if not dates_set:
        return {"nodes": [], "edges": [], "dateRange": None}
    
    dates_sorted = sorted(dates_set)
    min_date = dates_sorted[0]
    max_date = dates_sorted[-1]
    
    # Construir grafo de conexiones para heredar fechas
    node_connections = {}  # node_id -> [connected_node_ids]
    for e in edges:
        src = e.get("from", "")
        tgt = e.get("to", "")
        if src and tgt:
            if src not in node_connections:
                node_connections[src] = []
            if tgt not in node_connections:
                node_connections[tgt] = []
            node_connections[src].append(tgt)
            node_connections[tgt].append(src)
    
    # Procesar nodos
    processed_nodes = []
    for n in nodes:
        node_id = n.get("id", "")
        node_type = n.get("nodeType", "PROCESS")
        
        # Inferir tipo del ID si no está
        if not node_type:
            if node_id.startswith("SUPP:"):
                node_type = "SUPPLIER"
            elif node_id.startswith("RECV:"):
                node_type = "RECEPTION"
            elif node_id.startswith("PKG:"):
                color = n.get("color", {})
                bg = color.get("background", "") if isinstance(color, dict) else ""
                node_type = "PALLET_OUT" if "#2ecc71" in bg else "PALLET_IN"
            elif node_id.startswith("PROC:"):
                node_type = "PROCESS"
            elif node_id.startswith("CUST:"):
                node_type = "CUSTOMER"
            else:
                node_type = "PROCESS"
        
        date_str = n.get("date", "")[:10] if n.get("date") else ""
        
        # Si no tiene fecha, heredar de nodos conectados
        if not date_str and node_id in node_connections:
            for connected_id in node_connections[node_id]:
                connected_node = nodes_by_id.get(connected_id, {})
                connected_date = connected_node.get("date", "")[:10] if connected_node.get("date") else ""
                if connected_date:
                    date_str = connected_date
                    break
        
        # Si aún no tiene fecha, usar la fecha mínima del rango
        if not date_str:
            date_str = min_date
        
        # Extraer información de calidad de origen si es pallet
        origin_quality = None
        origin_process = None
        selection_reason = None
        if node_type in ["PALLET_IN", "PALLET_OUT"]:
            origin_quality = n.get("origin_quality", "")
            origin_process = n.get("origin_process", "")
            selection_reason = n.get("selection_reason", "")
        
        processed_nodes.append({
            "id": node_id,
            "label": n.get("label", node_id),
            "title": n.get("title", "").replace("\n", "<br>") if n.get("title") else "",
            "nodeType": node_type,
            "level": NODE_LEVELS.get(node_type, 2),
            "date": date_str,
            "color": NODE_COLORS.get(node_type, "#888"),
            "value": n.get("value", 1),
            "originQuality": origin_quality,
            "originProcess": origin_process,
            "selectionReason": selection_reason,
        })
    
    # Procesar edges
    processed_edges = []
    for e in edges:
        processed_edges.append({
            "source": e.get("from", ""),
            "target": e.get("to", ""),
            "value": e.get("value", 1),
        })
    
    return {
        "nodes": processed_nodes,
        "edges": processed_edges,
        "dateRange": {"min": min_date, "max": max_date},
        "dates": dates_sorted,
    }


def render_flow_timeline(
    data: Dict,
    height: int = 800,
) -> None:
    """
    Renderiza un diagrama de flujo con timeline usando D3.js.
    
    Args:
        data: Dict con nodes, edges del visjs_transformer
        height: Altura total del componente
    """
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    stats = data.get("stats", {})
    
    if not nodes:
        st.warning("No hay datos para visualizar")
        return
    
    # Mostrar estadísticas
    st.markdown("### 📊 Estadísticas")
    cols = st.columns(7)
    stats_display = [
        ("🏭 Proveedores", stats.get("suppliers", 0)),
        ("📥 Recepciones", stats.get("receptions", 0)),
        ("📦 Pallets In", stats.get("pallets_in", 0)),
        ("🔄 Procesos", stats.get("processes", 0)),
        ("📤 Pallets Out", stats.get("pallets_out", 0)),
        ("👤 Clientes", stats.get("customers", 0)),
        ("🔗 Conexiones", stats.get("total_edges", 0)),
    ]
    for col, (label, value) in zip(cols, stats_display):
        col.metric(label, value)
    
    # Los filtros se manejan ahora en JavaScript para evitar recargas de página
    
    # Preparar datos
    flow_data = _prepare_flow_data(data)
    
    if not flow_data.get("dateRange"):
        st.warning("No hay fechas válidas para crear el timeline")
        return
    
    nodes_json = json.dumps(flow_data["nodes"])
    edges_json = json.dumps(flow_data["edges"])
    dates_json = json.dumps(flow_data["dates"])
    date_range_json = json.dumps(flow_data["dateRange"])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            html, body {{ 
                height: 100%; 
                overflow: hidden;
                background: #0d1117;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            
            #container {{
                width: 100%;
                height: 100%;
                display: flex;
                flex-direction: column;
            }}
            
            #diagram {{
                flex: 1;
                overflow: hidden;
            }}
            
            #timeline {{
                height: 50px;
                background: #161b22;
                border-top: 1px solid #30363d;
            }}
            
            .node {{
                cursor: pointer;
            }}
            
            .node:hover {{
                filter: brightness(1.2);
            }}
            
            .node-label {{
                font-size: 9px;
                fill: #c9d1d9;
                pointer-events: none;
                text-anchor: middle;
            }}
            
            .link {{
                fill: none;
                stroke-opacity: 0.4;
            }}
            
            .link:hover {{
                stroke-opacity: 0.8;
            }}
            
            .level-label {{
                font-size: 11px;
                fill: #8b949e;
                font-weight: 500;
            }}
            
            .level-band {{
                fill: rgba(255, 255, 255, 0.02);
            }}
            
            .level-band:nth-child(odd) {{
                fill: rgba(255, 255, 255, 0.04);
            }}
            
            .timeline-axis text {{
                fill: #8b949e;
                font-size: 10px;
            }}
            
            .timeline-axis line,
            .timeline-axis path {{
                stroke: #30363d;
            }}
            
            .tooltip {{
                position: absolute;
                background: rgba(22, 27, 34, 0.95);
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11px;
                color: #c9d1d9;
                pointer-events: none;
                z-index: 1000;
                max-width: 300px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            }}
            
            .tooltip-title {{
                font-weight: 600;
                color: #f0f6fc;
                margin-bottom: 4px;
            }}
            
            /* Legend */
            .legend {{
                position: absolute;
                top: 10px;
                right: 10px;
                background: rgba(22, 27, 34, 0.95);
                padding: 10px 14px;
                border-radius: 8px;
                border: 1px solid #30363d;
                font-size: 11px;
                color: #c9d1d9;
            }}
            
            .legend-title {{
                font-weight: 600;
                color: #f0f6fc;
                margin-bottom: 8px;
            }}
            
            .legend-item {{
                display: flex;
                align-items: center;
                margin: 4px 0;
            }}
            
            .legend-color {{
                width: 12px;
                height: 12px;
                border-radius: 3px;
                margin-right: 8px;
            }}
            
            /* Zoom controls */
            .controls {{
                position: absolute;
                top: 10px;
                left: 10px;
                display: flex;
                gap: 4px;
            }}
            
            .control-btn {{
                width: 28px;
                height: 28px;
                background: rgba(22, 27, 34, 0.95);
                border: 1px solid #30363d;
                border-radius: 4px;
                color: #c9d1d9;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
            }}
            
            .control-btn:hover {{
                background: #30363d;
            }}
        </style>
    </head>
    <body>
        <div id="container">
            <div id="diagram"></div>
            <div id="timeline"></div>
        </div>
        
        <script>
            // Definir stub de la función inmediatamente para que esté disponible
            window.applyOriginFilters = function() {{
                console.log('Filter stub called - waiting for full implementation');
            }};
        </script>
        
        <div class="filters" style="position: absolute; top: 10px; right: 10px; z-index: 100; background: rgba(13, 17, 23, 0.95); padding: 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);">
            <div style="color: #fff; font-weight: bold; margin-bottom: 10px; font-size: 14px;">🔍 Filtros de Calidad</div>
            <label style="display: block; color: #fff; margin-bottom: 5px; cursor: pointer; user-select: none;">
                <input type="checkbox" id="filter-claro" checked onchange="window.applyOriginFilters()"> ✅ Origen Claro
            </label>
            <label style="display: block; color: #fff; margin-bottom: 5px; cursor: pointer; user-select: none;">
                <input type="checkbox" id="filter-ambiguo" checked onchange="window.applyOriginFilters()"> ⚠️ Origen Ambiguo
            </label>
            <label style="display: block; color: #fff; margin-bottom: 5px; cursor: pointer; user-select: none;">
                <input type="checkbox" id="filter-desconocido" checked onchange="window.applyOriginFilters()"> ❓ Origen Desconocido
            </label>
            <label style="display: block; color: #fff; margin-bottom: 5px; cursor: pointer; user-select: none;">
                <input type="checkbox" id="filter-sin-origen" checked onchange="window.applyOriginFilters()"> 🔴 Sin Origen
            </label>
            <label style="display: block; color: #fff; margin-bottom: 5px; cursor: pointer; user-select: none;">
                <input type="checkbox" id="filter-no-analizado" checked onchange="window.applyOriginFilters()"> ⚪ Sin Analizar
            </label>
        </div>
        
        <div class="legend">
            <div class="legend-title">🗺️ Leyenda</div>
            <div class="legend-item"><div class="legend-color" style="background: #9b59b6;"></div>Proveedor</div>
            <div class="legend-item"><div class="legend-color" style="background: #f39c12;"></div>Pallet IN</div>
            <div class="legend-item"><div class="legend-color" style="background: #e74c3c;"></div>Proceso</div>
            <div class="legend-item"><div class="legend-color" style="background: #2ecc71;"></div>Pallet OUT</div>
            <div class="legend-item"><div class="legend-color" style="background: #3498db;"></div>Cliente</div>
        </div>
        
        <div class="controls">
            <button class="control-btn" onclick="zoomIn()" title="Zoom In">+</button>
            <button class="control-btn" onclick="zoomOut()" title="Zoom Out">−</button>
            <button class="control-btn" onclick="resetZoom()" title="Reset">⟲</button>
            <button class="control-btn" onclick="toggleFullscreen()" title="Pantalla completa">⛶</button>
        </div>
        
        <div class="tooltip" id="tooltip" style="display: none;"></div>
        
        <script>
            const nodesData = {nodes_json};
            const edgesData = {edges_json};
            const datesData = {dates_json};
            const dateRange = {date_range_json};
            
            const levelNames = ['Proveedores', 'Recepciones', 'Pallets IN', 'Procesos', 'Pallets OUT', 'Clientes'];
            const levelCount = 6;
            
            // Función para trazar un paquete (click en PALLET_IN con origen)
            function tracePackage(pkgName) {{
                if (!pkgName) return;
                // Limpiar emojis del inicio del label
                const cleaned = pkgName.replace(/^[^A-Za-z0-9]+\\s*/, '').trim();
                if (!cleaned) return;
                console.log('Tracing package:', cleaned);
                const url = new URL(window.parent.location.href);
                url.searchParams.set('trace_pkg', cleaned);
                window.parent.location.href = url.toString();
            }}
            
            // Dimensiones - serán actualizadas en resize
            const margin = {{ top: 30, right: 20, bottom: 10, left: 100 }};
            let containerEl, width, height, xScale, yBandHeight, svg, g, zoom, currentTransform, timelineSvg, timelineG;
            let parseDate, nodeMap;
            let isLargeDataset = false;
            let zoomRafPending = false;
            let lastZoomEvent = null;
            
            function initDiagram() {{
                containerEl = document.getElementById('diagram');
                width = containerEl.clientWidth - margin.left - margin.right;
                height = containerEl.clientHeight - margin.top - margin.bottom;
                
                // Escalas
                parseDate = d3.timeParse("%Y-%m-%d");
                const minDate = parseDate(dateRange.min);
                const maxDate = parseDate(dateRange.max);
                
                // Añadir padding temporal
                const timePadding = (maxDate - minDate) * 0.05 || 86400000; // 5% o 1 día
                xScale = d3.scaleTime()
                    .domain([new Date(minDate - timePadding), new Date(maxDate.getTime() + timePadding)])
                    .range([0, width]);
                
                yBandHeight = height / levelCount;
                
                // Limpiar SVG anterior si existe
                d3.select('#diagram').selectAll('*').remove();
                
                // SVG principal
                svg = d3.select('#diagram')
                    .append('svg')
                    .attr('width', containerEl.clientWidth)
                    .attr('height', containerEl.clientHeight);
                
                // Grupo con zoom
                g = svg.append('g')
                    .attr('transform', `translate(${{margin.left}},${{margin.top}})`);
                
                // Zoom behavior - filtrar para no capturar clicks en nodos
                zoom = d3.zoom()
                    .scaleExtent([0.5, 10])
                    .filter(event => {{
                        // No aplicar zoom si el click es en un nodo
                        if (event.type === 'mousedown' || event.type === 'click') {{
                            const target = event.target;
                            if (target.closest && target.closest('.node')) {{
                                return false;
                            }}
                        }}
                        return !event.button;
                    }})
                    .on('zoom', zoomed);
                
                svg.call(zoom);
                
                currentTransform = d3.zoomIdentity;
                
                // Crear timeline
                d3.select('#timeline').selectAll('*').remove();
                timelineSvg = d3.select('#timeline')
                    .append('svg')
                    .attr('width', containerEl.clientWidth)
                    .attr('height', 50);
                
                timelineG = timelineSvg.append('g')
                    .attr('transform', `translate(${{margin.left}}, 10)`);
            }}
            
            function zoomed(event) {{
                lastZoomEvent = event;
                if (zoomRafPending) return;
                zoomRafPending = true;
                requestAnimationFrame(() => {{
                    zoomRafPending = false;
                    if (!lastZoomEvent) return;

                    currentTransform = lastZoomEvent.transform;

                    // Actualizar escala X con zoom
                    const newXScale = currentTransform.rescaleX(xScale);

                    // Actualizar posiciones de nodos
                    g.selectAll('.node')
                        .attr('transform', d => {{
                            const x = newXScale(d.parsedDate || xScale.domain()[0]);
                            return `translate(${{x}},${{d.y}})`;
                        }});

                    // Actualizar links
                    g.selectAll('.link')
                        .attr('d', d => generateLink(d, newXScale));

                    // Actualizar timeline
                    updateTimeline(newXScale);
                }});
            }}
            
            // Función para generar links curvos tipo Sankey
            function generateLink(edge, scale) {{
                const source = nodeMap[edge.source];
                const target = nodeMap[edge.target];
                if (!source || !target) return '';
                
                const x0 = scale(source.parsedDate || xScale.domain()[0]);
                const y0 = source.y;
                const x1 = scale(target.parsedDate || xScale.domain()[1]);
                const y1 = target.y;
                
                // Curva Bézier vertical (de arriba a abajo)
                const midY = (y0 + y1) / 2;
                
                return `M${{x0}},${{y0}} C${{x0}},${{midY}} ${{x1}},${{midY}} ${{x1}},${{y1}}`;
            }}
            
            function renderDiagram() {{
                // Bandas de niveles
                for (let i = 0; i < levelCount; i++) {{
                    g.append('rect')
                        .attr('class', 'level-band')
                        .attr('x', -margin.left)
                        .attr('y', i * yBandHeight)
                        .attr('width', width + margin.left + margin.right)
                        .attr('height', yBandHeight)
                        .attr('fill', i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'rgba(255,255,255,0.04)');
                    
                    // Labels de niveles
                    g.append('text')
                        .attr('class', 'level-label')
                        .attr('x', -10)
                        .attr('y', i * yBandHeight + yBandHeight / 2)
                        .attr('text-anchor', 'end')
                        .attr('dominant-baseline', 'middle')
                        .text(levelNames[i]);
                }}
                
                // Procesar nodos - calcular posiciones Y dentro de cada banda
                const nodesByDateAndLevel = {{}};
            nodesData.forEach(node => {{
                node.parsedDate = node.date ? parseDate(node.date) : null;
                const key = `${{node.date || 'nodate'}}_${{node.level}}`;
                if (!nodesByDateAndLevel[key]) nodesByDateAndLevel[key] = [];
                nodesByDateAndLevel[key].push(node);
            }});
            
            // Asignar posiciones Y
            Object.values(nodesByDateAndLevel).forEach(nodes => {{
                const level = nodes[0].level;
                const bandTop = level * yBandHeight;
                const bandHeight = yBandHeight;
                const nodeSpacing = Math.min(30, (bandHeight - 20) / (nodes.length + 1));
                
                nodes.forEach((node, i) => {{
                    node.y = bandTop + 15 + (i + 1) * nodeSpacing;
                }});
            }});
            
            // Crear mapa de nodos por ID
            nodeMap = {{}};
            nodesData.forEach(n => nodeMap[n.id] = n);
            
            // Dibujar links
            const links = g.append('g')
                .attr('class', 'links')
                .selectAll('.link')
                .data(edgesData)
                .enter()
                .append('path')
                .attr('class', 'link')
                .attr('d', d => generateLink(d, xScale))
                .attr('stroke', d => {{
                    const source = nodeMap[d.source];
                    return source ? source.color : '#888';
                }})
                .attr('stroke-width', d => Math.max(1, Math.min(8, Math.sqrt(d.value / 100))))
                .on('mouseover', function(event, d) {{
                    d3.select(this).attr('stroke-opacity', 0.8);
                    showTooltip(event, `<b>${{d.value.toLocaleString()}} kg</b>`);
                }})
                .on('mouseout', function() {{
                    d3.select(this).attr('stroke-opacity', 0.4);
                    hideTooltip();
                }});
            
            // Dibujar nodos
            const nodeRadius = 8;
            const nodes = g.append('g')
                .attr('class', 'nodes')
                .selectAll('.node')
                .data(nodesData)
                .enter()
                .append('g')
                .attr('class', 'node')
                .attr('transform', d => {{
                    const x = xScale(d.parsedDate || xScale.domain()[0]);
                    return `translate(${{x}},${{d.y}})`;
                }})
                .style('cursor', d => {{
                    // PALLET_IN son clickeables para trazar hacia atrás
                    if (d.nodeType === 'PALLET_IN') {{
                        return 'pointer';
                    }}
                    return 'default';
                }})
                .on('click', function(event, d) {{
                    // Click en PALLET_IN para trazar su origen
                    if (d.nodeType === 'PALLET_IN') {{
                        console.log('Click on PALLET_IN:', d);
                        tracePackage(d.label);
                    }}
                }})
                .on('mouseover', function(event, d) {{
                    let tooltipHtml = `<div class="tooltip-title">${{d.label}}</div>${{d.title || ''}}`;
                    
                    // Agregar información de calidad de origen si existe
                    if (d.originQuality) {{
                        tooltipHtml += `<hr style="margin: 5px 0; border: none; border-top: 1px solid rgba(255,255,255,0.2);">`;
                        
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
                        
                        // Indicar si es clickeable para trazar
                        if (d.nodeType === 'PALLET_IN' && !d.originQuality.includes('SIN_ORIGEN') && d.originQuality !== 'NO_ANALIZADO') {{
                            tooltipHtml += `<div style="margin-top: 8px; padding: 4px 8px; background: rgba(52,152,219,0.3); border-radius: 4px; font-size: 11px;">👆 Click para trazar origen</div>`;
                        }}
                    }}
                    
                    showTooltip(event, tooltipHtml);
                }})
                .on('mouseout', hideTooltip);
            
            // Formas de nodos según tipo
            nodes.each(function(d) {{
                const node = d3.select(this);
                let shape;
                
                if (d.nodeType === 'SUPPLIER') {{
                    // Triángulo para proveedores
                    shape = node.append('path')
                        .attr('d', d3.symbol().type(d3.symbolTriangle).size(200))
                        .attr('fill', d.color);
                }} else if (d.nodeType === 'PROCESS') {{
                    // Cuadrado para procesos
                    shape = node.append('rect')
                        .attr('x', -8)
                        .attr('y', -8)
                        .attr('width', 16)
                        .attr('height', 16)
                        .attr('rx', 2)
                        .attr('fill', d.color);
                }} else if (d.nodeType === 'CUSTOMER') {{
                    // Cuadrado redondeado para clientes
                    shape = node.append('rect')
                        .attr('x', -9)
                        .attr('y', -9)
                        .attr('width', 18)
                        .attr('height', 18)
                        .attr('rx', 4)
                        .attr('fill', d.color);
                }} else {{
                    // Círculo para pallets
                    shape = node.append('circle')
                        .attr('r', nodeRadius)
                        .attr('fill', d.color);
                }}
                
                // Click handler directo en la forma para PALLET_IN
                if (d.nodeType === 'PALLET_IN') {{
                    shape.style('cursor', 'pointer')
                        .on('click', function(event) {{
                            event.stopPropagation();
                            console.log('Direct click on PALLET_IN shape:', d.label);
                            tracePackage(d.label);
                        }});
                }}
            }});
            
            // Labels de nodos (omitir en datasets grandes para mejorar rendimiento)
            isLargeDataset = nodesData.length > 2000;
            if (!isLargeDataset) {{
                nodes.append('text')
                    .attr('class', 'node-label')
                    .attr('y', 20)
                    .text(d => d.label.length > 15 ? d.label.slice(0, 12) + '...' : d.label);
            }}
            
            // Actualizar timeline
            updateTimeline(xScale);
            }}
            
            // Función para actualizar timeline
            function updateTimeline(scale) {{
                timelineG.selectAll('*').remove();
                
                // Calcular zoom level para adaptar el timeline
                const zoomLevel = currentTransform ? currentTransform.k : 1;
                const domain = scale.domain();
                const rangeDays = (domain[1] - domain[0]) / (1000 * 60 * 60 * 24);
                
                // Decidir el intervalo según el zoom y rango de días visibles
                let tickInterval, tickFormat;
                if (rangeDays / zoomLevel > 60) {{
                    // Vista amplia: mostrar meses
                    tickInterval = d3.timeMonth.every(1);
                    tickFormat = d3.timeFormat('%b %Y');
                }} else if (rangeDays / zoomLevel > 14) {{
                    // Vista media: mostrar semanas
                    tickInterval = d3.timeWeek.every(1);
                    tickFormat = d3.timeFormat('%d %b');
                }} else {{
                    // Vista cercana: mostrar días
                    tickInterval = d3.timeDay.every(1);
                    tickFormat = d3.timeFormat('%d %b');
                }}
                
                const axis = d3.axisBottom(scale)
                    .ticks(tickInterval)
                    .tickFormat(tickFormat);
                
                // Dibujar líneas verticales de referencia en el diagrama principal
                const tickValues = scale.ticks(tickInterval);
                g.selectAll('.date-line').remove();
                g.selectAll('.date-line')
                    .data(tickValues)
                    .enter()
                    .append('line')
                    .attr('class', 'date-line')
                    .attr('x1', d => scale(d))
                    .attr('y1', 0)
                    .attr('x2', d => scale(d))
                    .attr('y2', height)
                    .attr('stroke', 'rgba(255,255,255,0.05)')
                    .attr('stroke-width', 1);
                
                // Eje del timeline
                const axisGroup = timelineG.append('g')
                    .attr('class', 'timeline-axis')
                    .call(axis);
                
                // Rotar etiquetas para evitar solapamiento
                axisGroup.selectAll('text')
                    .attr('transform', 'rotate(-45)')
                    .style('text-anchor', 'end')
                    .attr('dx', '-0.8em')
                    .attr('dy', '0.15em');
            }}
            
            // Inicializar diagrama
            initDiagram();
            renderDiagram();
            updateTimeline(xScale);
            
            // Función local para aplicar filtros (tiene acceso a g y nodeMap por closure)
            function applyOriginFilters() {{
                console.log('✓ Aplicando filtros de origen...');
                
                const claroBox = document.getElementById('filter-claro');
                const ambiguoBox = document.getElementById('filter-ambiguo');
                const desconocidoBox = document.getElementById('filter-desconocido');
                const sinOrigenBox = document.getElementById('filter-sin-origen');
                const noAnalizadoBox = document.getElementById('filter-no-analizado');
                
                if (!claroBox) {{ console.error('✗ Checkboxes no encontrados'); return; }}
                
                const showClaro = claroBox.checked;
                const showAmbiguo = ambiguoBox.checked;
                const showDesconocido = desconocidoBox.checked;
                const showSinOrigen = sinOrigenBox.checked;
                const showNoAnalizado = noAnalizadoBox.checked;
                
                console.log('✓ Estados:', {{ showClaro, showAmbiguo, showDesconocido, showSinOrigen, showNoAnalizado }});
                
                const filters = {{
                    'ORIGEN_CLARO': showClaro,
                    'ORIGEN_CLARO_RECOVERED': showClaro,
                    'ORIGEN_AMBIGUO': showAmbiguo,
                    'ORIGEN_AMBIGUO_RECOVERED': showAmbiguo,
                    'ORIGEN_DESCONOCIDO': showDesconocido,
                    'ORIGEN_DESCONOCIDO_RECOVERED': showDesconocido,
                    'SIN_ORIGEN': showSinOrigen,
                    'NO_ANALIZADO': showNoAnalizado,
                    '': true
                }};
                
                if (!g) {{ console.error('✗ Variable g no disponible'); return; }}
                
                const nodes = g.selectAll('.node');
                const links = g.selectAll('.link');
                
                console.log(`✓ Filtrando ${{nodes.size()}} nodos y ${{links.size()}} links`);
                
                let visibleCount = 0;
                let hiddenCount = 0;
                let sampleLog = 0;
                
                nodes.each(function(d) {{
                    const hasQuality = d.originQuality && d.originQuality !== '';
                    const isVisible = !hasQuality || filters[d.originQuality];
                    
                    if (hasQuality && sampleLog < 5) {{
                        console.log(`Nodo ${{d.id}}: quality=${{d.originQuality}}, visible=${{isVisible}}`);
                        sampleLog++;
                    }}
                    
                    d3.select(this)
                        .style('display', isVisible ? null : 'none')
                        .style('pointer-events', isVisible ? 'all' : 'none')
                        .style('opacity', isVisible ? 1 : 0);
                    
                    if (isVisible) visibleCount++;
                    else hiddenCount++;
                }});
                
                links.each(function(d) {{
                    const sourceNode = nodeMap[d.source];
                    const targetNode = nodeMap[d.target];
                    if (!sourceNode || !targetNode) {{
                        d3.select(this).style('display', null).style('opacity', 0.4);
                        return;
                    }}
                    
                    const sourceVisible = !sourceNode.originQuality || sourceNode.originQuality === '' || filters[sourceNode.originQuality];
                    const targetVisible = !targetNode.originQuality || targetNode.originQuality === '' || filters[targetNode.originQuality];
                    const showLink = sourceVisible && targetVisible;
                    
                    d3.select(this)
                        .style('display', showLink ? null : 'none')
                        .style('opacity', showLink ? 0.4 : 0);
                }});
                
                console.log(`✓ Filtros aplicados - ${{visibleCount}} visibles, ${{hiddenCount}} ocultos`);
            }}
            
            // Adjuntar event listeners DESPUÉS del render
            setTimeout(() => {{
                console.log('✓ Adjuntando event listeners a checkboxes...');
                const checkboxes = ['filter-claro', 'filter-ambiguo', 'filter-desconocido', 'filter-sin-origen', 'filter-no-analizado'];
                checkboxes.forEach(id => {{
                    const checkbox = document.getElementById(id);
                    if (checkbox) {{
                        checkbox.addEventListener('change', function() {{
                            console.log(`✓ Checkbox ${{id}} changed to ${{this.checked}}`);
                            applyOriginFilters();
                        }});
                        console.log(`✓ Listener adjuntado a ${{id}}`);
                    }} else {{
                        console.error(`✗ No se encontró checkbox ${{id}}`);
                    }}
                }});
                
                // Aplicar filtros inicialmente
                applyOriginFilters();
            }}, 100);
            
            // Tooltip functions
            function showTooltip(event, html) {{
                const tooltip = document.getElementById('tooltip');
                tooltip.innerHTML = html;
                tooltip.style.display = 'block';
                tooltip.style.left = (event.pageX + 10) + 'px';
                tooltip.style.top = (event.pageY - 10) + 'px';
            }}
            
            function hideTooltip() {{
                document.getElementById('tooltip').style.display = 'none';
            }}
            
            // Zoom controls
            window.zoomIn = function() {{
                svg.transition().call(zoom.scaleBy, 1.3);
            }};
            
            window.zoomOut = function() {{
                svg.transition().call(zoom.scaleBy, 0.7);
            }};
            
            window.resetZoom = function() {{
                svg.transition().call(zoom.transform, d3.zoomIdentity);
            }};
            
            // Fullscreen toggle
            window.toggleFullscreen = function() {{
                const container = document.getElementById('container');
                if (!document.fullscreenElement) {{
                    container.requestFullscreen().catch(err => {{
                        console.error('Error al entrar en pantalla completa:', err);
                    }});
                }} else {{
                    document.exitFullscreen();
                }}
            }};
            
            // Listener para redimensionar al entrar/salir de fullscreen
            document.addEventListener('fullscreenchange', function() {{
                setTimeout(function() {{
                    initDiagram();
                    renderDiagram();
                }}, 100);
            }});
        </script>
    </body>
    </html>
    """
    
    st.markdown("### 📊 Flow Timeline")
    st.caption("🖱️ Arrastra para navegar | 🔍 Scroll para zoom | ⬆️ Proveedor → Cliente ⬇️ | ⬅️ Antiguo → Nuevo ➡️")
    
    components.html(html, height=height, scrolling=False)

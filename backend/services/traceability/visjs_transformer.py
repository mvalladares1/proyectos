"""
Transformador de datos de trazabilidad a formato vis.js Network.
Usa pyvis para generar visualizaciones interactivas de red.
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime


# Colores para los tipos de nodos
NODE_COLORS = {
    "SUPPLIER": {"background": "#9b59b6", "border": "#8e44ad", "highlight": {"background": "#a569bd", "border": "#9b59b6"}},
    "RECEPTION": {"background": "#1abc9c", "border": "#16a085", "highlight": {"background": "#48c9b0", "border": "#1abc9c"}},
    "PALLET_IN": {"background": "#f39c12", "border": "#d68910", "highlight": {"background": "#f5b041", "border": "#f39c12"}},
    "PALLET_OUT": {"background": "#2ecc71", "border": "#27ae60", "highlight": {"background": "#58d68d", "border": "#2ecc71"}},
    "PROCESS": {"background": "#e74c3c", "border": "#c0392b", "highlight": {"background": "#ec7063", "border": "#e74c3c"}},
    "CUSTOMER": {"background": "#3498db", "border": "#2980b9", "highlight": {"background": "#5dade2", "border": "#3498db"}},
}

# Colores para grupos del timeline (CSS)
TIMELINE_GROUP_STYLES = {
    "supplier": "background-color: #9b59b6; color: white;",
    "reception": "background-color: #1abc9c; color: white;",
    "pallet_in": "background-color: #f39c12; color: white;",
    "process": "background-color: #e74c3c; color: white;",
    "pallet_out": "background-color: #2ecc71; color: white;",
    "customer": "background-color: #3498db; color: white;",
}

# Iconos por tipo
NODE_ICONS = {
    "SUPPLIER": "🏭",
    "RECEPTION": "📥",
    "PALLET_IN": "🟠",
    "PALLET_OUT": "🟢",
    "PROCESS": "🔴",
    "CUSTOMER": "🔵",
}

# Niveles para layout jerárquico (izquierda a derecha)
NODE_LEVELS = {
    "SUPPLIER": 0,
    "RECEPTION": 1,
    "PALLET_IN": 2,
    "PROCESS": 3,
    "PALLET_OUT": 4,
    "CUSTOMER": 5,
}


def transform_to_visjs(traceability_data: Dict) -> Dict:
    """
    Transforma datos de trazabilidad a formato vis.js Network.
    
    Args:
        traceability_data: Datos del TraceabilityService
        
    Returns:
        Dict con:
        - nodes: Lista de nodos para vis.js
        - edges: Lista de edges para vis.js
        - timeline_data: Datos para timeline (si se usa)
        - timeline_groups: Grupos para el timeline
        - stats: Estadísticas
    """
    pallets = traceability_data.get("pallets", {})
    processes = traceability_data.get("processes", {})
    suppliers = traceability_data.get("suppliers", {})
    customers = traceability_data.get("customers", {})
    links_raw = traceability_data.get("links", [])
    
    nodes = []
    edges = []
    node_ids = set()
    timeline_data = []
    
    # Track de fechas de proveedores (usamos la fecha de primera recepción)
    supplier_first_dates = {}
    
    # Agregar nodos de proveedores (fechas se asignan después)
    for sid, sdata in suppliers.items():
        # sdata puede ser string (nombre) o dict con más info
        sname = sdata if isinstance(sdata, str) else sdata.get("name", str(sid))
        node_id = f"SUPP:{sid}"
        if node_id not in node_ids:
            nodes.append(_create_node(
                node_id,
                f"{NODE_ICONS['SUPPLIER']} {sname}",
                "SUPPLIER",
                title=f"Proveedor: {sname}"
            ))
            node_ids.add(node_id)
    
    # Agregar nodos de recepciones y trackear fechas de proveedores
    for ref, pinfo in processes.items():
        if pinfo.get("is_reception"):
            node_id = f"RECV:{ref}"
            if node_id not in node_ids:
                date = pinfo.get("date", "")[:10] if pinfo.get("date") else ""
                nodes.append(_create_node(
                    node_id,
                    f"{NODE_ICONS['RECEPTION']} {ref}",
                    "RECEPTION",
                    title=f"Recepción: {ref}\nFecha: {date}"
                ))
                node_ids.add(node_id)
                
                # Timeline: Recepción como punto
                if date:
                    timeline_data.append({
                        "id": node_id,
                        "content": ref,
                        "start": date,
                        "type": "point",
                        "group": "reception",
                        "className": "timeline-reception"
                    })
                    
                    # Trackear primera recepción por proveedor
                    supplier_id = pinfo.get("supplier_id")
                    if supplier_id:
                        if supplier_id not in supplier_first_dates or date < supplier_first_dates[supplier_id]:
                            supplier_first_dates[supplier_id] = date
    
    # Timeline: Agregar proveedores con su primera fecha de recepción
    for sid, first_date in supplier_first_dates.items():
        sdata = suppliers.get(sid, {})
        sname = sdata if isinstance(sdata, str) else sdata.get("name", str(sid))
        timeline_data.append({
            "id": f"SUPP:{sid}",
            "content": f"🏭 {sname}",
            "start": first_date,
            "type": "point",
            "group": "supplier",
            "className": "timeline-supplier"
        })
    
    # Agregar nodos de pallets
    for pid, pinfo in pallets.items():
        direction = pinfo.get("direction", "IN")
        node_type = f"PALLET_{direction}"
        node_id = f"PKG:{pid}"
        
        if node_id not in node_ids:
            name = pinfo.get("name", str(pid))
            qty = pinfo.get("qty", 0)
            products = list(pinfo.get("products", {}).keys())
            prods_str = ", ".join(products[:2])
            
            # Usar create_date si existe, sino first_date
            create_date = pinfo.get("create_date", "")
            date = create_date[:10] if create_date else (pinfo.get("first_date", "")[:10] if pinfo.get("first_date") else "")
            
            title = f"Pallet: {name}\nCantidad: {qty:.0f} kg\nProductos: {prods_str}"
            if date:
                title += f"\nFecha creación: {date}"
            
            nodes.append(_create_node(
                node_id,
                f"{NODE_ICONS[node_type]} {name}",
                node_type,
                title=title,
                value=qty  # Tamaño proporcional a cantidad
            ))
            node_ids.add(node_id)
            
            # Timeline: Pallet como punto
            if date:
                timeline_data.append({
                    "id": node_id,
                    "content": name,
                    "start": date,
                    "type": "point",
                    "group": "pallet_in" if direction == "IN" else "pallet_out",
                    "className": f"timeline-pallet-{direction.lower()}"
                })
    
    # Agregar nodos de procesos
    for ref, pinfo in processes.items():
        if not pinfo.get("is_reception"):
            node_id = f"PROC:{ref}"
            if node_id not in node_ids:
                # Usar fechas MRP si existen
                mrp_start = pinfo.get("mrp_start", "")
                mrp_end = pinfo.get("mrp_end", "")
                date = pinfo.get("date", "")[:10] if pinfo.get("date") else ""
                
                # Para el título del nodo
                title_date = mrp_start[:16] if mrp_start else date
                title = f"Proceso: {ref}"
                if mrp_start:
                    title += f"\nInicio: {mrp_start[:16]}"
                if mrp_end:
                    title += f"\nTérmino: {mrp_end[:16]}"
                elif date:
                    title += f"\nFecha: {date}"
                
                nodes.append(_create_node(
                    node_id,
                    f"{NODE_ICONS['PROCESS']} {ref}",
                    "PROCESS",
                    title=title
                ))
                node_ids.add(node_id)
                
                # Timeline: Proceso como RANGO si tiene inicio y término
                if mrp_start and mrp_end:
                    timeline_data.append({
                        "id": node_id,
                        "content": ref,
                        "start": mrp_start,
                        "end": mrp_end,
                        "type": "range",
                        "group": "process",
                        "className": "timeline-process"
                    })
                elif mrp_start or date:
                    # Solo punto si no hay rango completo
                    timeline_data.append({
                        "id": node_id,
                        "content": ref,
                        "start": mrp_start if mrp_start else date,
                        "type": "point",
                        "group": "process",
                        "className": "timeline-process"
                    })
    
    # Agregar nodos de clientes
    for cid, cdata in customers.items():
        node_id = f"CUST:{cid}"
        # cdata puede ser string o dict
        cname = cdata if isinstance(cdata, str) else cdata.get("name", str(cid))
        scheduled_date = "" if isinstance(cdata, str) else cdata.get("scheduled_date", "")
        
        if node_id not in node_ids:
            title = f"Cliente: {cname}"
            if scheduled_date:
                title += f"\nFecha programada: {scheduled_date[:10]}"
            
            nodes.append(_create_node(
                node_id,
                f"{NODE_ICONS['CUSTOMER']} {cname}",
                "CUSTOMER",
                title=title
            ))
            node_ids.add(node_id)
            
            # Timeline: Cliente como punto con fecha programada
            if scheduled_date:
                timeline_data.append({
                    "id": node_id,
                    "content": f"🔵 {cname}",
                    "start": scheduled_date[:10],
                    "type": "point",
                    "group": "customer",
                    "className": "timeline-customer"
                })
            node_ids.add(node_id)
    
    # Agregar edges
    edge_aggregated = {}
    
    for link_tuple in links_raw:
        source_type, source_id, target_type, target_id, qty = link_tuple
        
        source_nid = None
        target_nid = None
        
        # Determinar nodo fuente
        if source_type == "RECV":
            pinfo = processes.get(source_id, {})
            supplier_id = pinfo.get("supplier_id")
            if supplier_id and f"SUPP:{supplier_id}" in node_ids:
                source_nid = f"SUPP:{supplier_id}"
            elif f"RECV:{source_id}" in node_ids:
                source_nid = f"RECV:{source_id}"
        elif source_type == "PALLET":
            source_nid = f"PKG:{source_id}"
        elif source_type == "PROCESS":
            source_nid = f"PROC:{source_id}"
        
        # Determinar nodo destino
        if target_type == "PALLET":
            target_nid = f"PKG:{target_id}"
        elif target_type == "PROCESS":
            target_nid = f"PROC:{target_id}"
        elif target_type == "CUSTOMER":
            target_nid = f"CUST:{target_id}"
        
        if source_nid and target_nid and source_nid in node_ids and target_nid in node_ids:
            key = (source_nid, target_nid)
            if key not in edge_aggregated:
                edge_aggregated[key] = 0
            edge_aggregated[key] += qty
    
    # Crear edges finales
    for (source, target), qty in edge_aggregated.items():
        edge_width = max(1, min(10, qty / 100))
        label = f"{qty:.0f} kg" if qty > 10 else ""
        
        edges.append({
            "from": source,
            "to": target,
            "value": qty,
            "width": edge_width,
            "label": label,
            "arrows": "to",
            "smooth": {"type": "cubicBezier", "roundness": 0.5},
            "color": {"color": "#888", "highlight": "#333"},
            "font": {"size": 10, "align": "middle"}
        })
    
    # Estadísticas
    stats = {
        "suppliers": len(suppliers),
        "pallets_in": len([p for p in pallets.values() if p.get("direction") == "IN"]),
        "pallets_out": len([p for p in pallets.values() if p.get("direction") == "OUT"]),
        "processes": len([p for p in processes.values() if not p.get("is_reception")]),
        "customers": len(customers),
        "total_edges": len(edges),
    }
    
    return {
        "nodes": nodes,
        "edges": edges,
        "timeline_data": timeline_data,
        "stats": stats
    }


def _create_node(
    node_id: str,
    label: str,
    node_type: str,
    title: str = "",
    value: float = None
) -> Dict:
    """Crea un nodo en formato vis.js."""
    colors = NODE_COLORS.get(node_type, NODE_COLORS["PROCESS"])
    level = NODE_LEVELS.get(node_type, 3)
    
    node = {
        "id": node_id,
        "label": label,
        "title": title,  # Tooltip
        "level": level,
        "color": colors,
        "shape": "box",
        "font": {"color": "#fff", "size": 12},
        "borderWidth": 2,
        "shadow": True,
        "margin": 10,
    }
    
    # Tamaño proporcional si se especifica valor
    if value and value > 0:
        node["value"] = value
        node["scaling"] = {"min": 20, "max": 50}
    
    return node


def get_pyvis_options() -> Dict:
    """Retorna opciones de configuración para pyvis/vis.js."""
    return {
        "layout": {
            "hierarchical": {
                "enabled": True,
                "direction": "LR",  # Left to Right
                "sortMethod": "directed",
                "levelSeparation": 250,
                "nodeSpacing": 100,
                "treeSpacing": 200,
                "blockShifting": True,
                "edgeMinimization": True,
                "parentCentralization": True,
            }
        },
        "physics": {
            "enabled": False,  # Desactivar física para layout jerárquico
            "hierarchicalRepulsion": {
                "centralGravity": 0.0,
                "springLength": 200,
                "springConstant": 0.01,
                "nodeDistance": 150,
            }
        },
        "interaction": {
            "hover": True,
            "tooltipDelay": 100,
            "zoomView": True,
            "dragView": True,
            "dragNodes": True,
            "navigationButtons": True,
            "keyboard": {
                "enabled": True,
                "bindToWindow": False,
            }
        },
        "nodes": {
            "font": {"size": 12},
            "borderWidth": 2,
            "shadow": True,
        },
        "edges": {
            "smooth": {
                "type": "cubicBezier",
                "forceDirection": "horizontal",
                "roundness": 0.5
            },
            "arrows": {"to": {"enabled": True, "scaleFactor": 0.5}},
        }
    }

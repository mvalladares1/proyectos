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

# Niveles para layout jerárquico (izquierda a derecha) - Simplificado como Sankey
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
    
    # Mapear recepciones a proveedores para conexiones directas
    reception_to_supplier = {}
    reception_dates = {}  # ref -> fecha
    
    for ref, pinfo in processes.items():
        if pinfo.get("is_reception"):
            supplier_id = pinfo.get("supplier_id")
            if supplier_id:
                reception_to_supplier[ref] = supplier_id
            
            # Buscar cualquier fecha disponible: scheduled_date > date_done > date
            date = ""
            if pinfo.get("scheduled_date"):
                date = pinfo.get("scheduled_date", "")[:10]
            elif pinfo.get("date_done"):
                date = pinfo.get("date_done", "")[:10]
            elif pinfo.get("date"):
                date = pinfo.get("date", "")[:10]
            
            if date:
                reception_dates[ref] = date
                if supplier_id:
                    if supplier_id not in supplier_first_dates or date < supplier_first_dates[supplier_id]:
                        supplier_first_dates[supplier_id] = date
    
    # Debug: imprimir lo que encontramos
    print(f"[VisJS] Suppliers: {len(suppliers)}, Recepciones encontradas: {len(reception_dates)}")
    print(f"[VisJS] supplier_first_dates: {supplier_first_dates}")
    
    # Agregar nodos de proveedores con información detallada
    for sid, sdata in suppliers.items():
        if isinstance(sdata, dict):
            sname = sdata.get("name", str(sid))
            scheduled_date = sdata.get("scheduled_date", "")
            date_done = sdata.get("date_done", "")
        else:
            sname = sdata
            scheduled_date = ""
            date_done = ""
        
        node_id = f"SUPP:{sid}"
        if node_id not in node_ids:
            # Acortar nombre si es muy largo
            short_name = sname[:30] + "..." if len(sname) > 30 else sname
            first_date = supplier_first_dates.get(sid, scheduled_date[:10] if scheduled_date else "")
            
            # Título con información detallada
            title = f"Proveedor: {sname}"
            if first_date:
                title += f"\nPrimera recepción: {first_date}"
            
            nodes.append(_create_node(
                node_id,
                short_name,
                "SUPPLIER",
                title=title,
                date=first_date
            ))
            node_ids.add(node_id)
            
            # Timeline: Proveedor
            if first_date:
                timeline_data.append({
                    "id": node_id,
                    "content": f"🏭 {short_name}",
                    "start": first_date,
                    "type": "point",
                    "group": "supplier",
                    "className": "timeline-supplier"
                })
    
    # Agregar nodos de recepción (como en Sankey)
    for ref, pinfo in processes.items():
        if pinfo.get("is_reception"):
            node_id = f"RECV:{ref}"
            if node_id not in node_ids:
                supplier_id = pinfo.get("supplier_id")
                supplier_name = ""
                if supplier_id:
                    sdata = suppliers.get(supplier_id, {})
                    if isinstance(sdata, dict):
                        supplier_name = sdata.get("name", "")
                        if not supplier_name:
                            print(f"[VisJS] Recepción {ref}: supplier_id={supplier_id}, sdata={sdata}")
                    else:
                        supplier_name = sdata if sdata else ""
                
                # Información detallada de la recepción
                scheduled_date = pinfo.get("scheduled_date", "")[:10] if pinfo.get("scheduled_date") else ""
                date_done = pinfo.get("date_done", "")[:10] if pinfo.get("date_done") else ""
                albaran = pinfo.get("albaran", "")
                guia_despacho = pinfo.get("guia_despacho", "")
                origen = pinfo.get("origen", "")
                transportista = pinfo.get("transportista", "")
                
                # Usar la fecha que ya calculamos, o cualquier disponible
                node_date = reception_dates.get(ref, "") or scheduled_date or date_done or (pinfo.get("date", "")[:10] if pinfo.get("date") else "")
                
                # Construir título detallado
                title = f"Recepción: {ref}"
                if supplier_name:
                    title += f"\nProveedor: {supplier_name}"
                if albaran and albaran != ref:
                    title += f"\nAlbarán: {albaran}"
                if guia_despacho:
                    title += f"\nGuía despacho: {guia_despacho}"
                if origen:
                    title += f"\nOrigen: {origen}"
                if transportista:
                    title += f"\nTransportista: {transportista}"
                if scheduled_date:
                    title += f"\nFecha programada: {scheduled_date}"
                if date_done:
                    title += f"\nFecha realizada: {date_done}"
                
                nodes.append(_create_node(
                    node_id,
                    ref,
                    "RECEPTION",
                    title=title,
                    date=node_date
                ))
                node_ids.add(node_id)
                
                # Timeline: Recepción
                if node_date:
                    timeline_data.append({
                        "id": node_id,
                        "content": f"📥 {ref}",
                        "start": node_date,
                        "type": "point",
                        "group": "reception",
                        "className": "timeline-reception"
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
            origin_quality = pinfo.get("origin_quality", "")
            origin_process = pinfo.get("origin_process", "")
            selection_reason = pinfo.get("selection_reason", "")
            
            # Usar pack_date si existe, sino first_date (igual que sankey_transformer)
            pallet_date = pinfo.get("pack_date") or pinfo.get("first_date", "")
            date = pallet_date[:10] if pallet_date else ""
            
            title = f"Pallet: {name}\nCantidad: {qty:.0f} kg\nProductos: {prods_str}"
            if date:
                title += f"\nFecha pack: {date}"
            
            nodes.append(_create_node(
                node_id,
                name,
                node_type,
                title=title,
                value=qty,
                date=date,
                origin_quality=origin_quality,
                origin_process=origin_process,
                selection_reason=selection_reason
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
    
    # Agregar nodos de procesos (solo los que NO son recepciones)
    for ref, pinfo in processes.items():
        if not pinfo.get("is_reception"):
            node_id = f"PROC:{ref}"
            if node_id not in node_ids:
                # Usar fechas MRP si existen
                mrp_start = pinfo.get("mrp_start", "")
                mrp_end = pinfo.get("mrp_end", "")
                date = pinfo.get("date", "")[:10] if pinfo.get("date") else ""
                
                title = f"Proceso: {ref}"
                if mrp_start:
                    title += f"\nInicio: {mrp_start[:16]}"
                if mrp_end:
                    title += f"\nTérmino: {mrp_end[:16]}"
                elif date:
                    title += f"\nFecha: {date}"
                
                # Usar fecha de inicio como fecha principal
                node_date = mrp_start[:10] if mrp_start else date
                nodes.append(_create_node(
                    node_id,
                    ref,
                    "PROCESS",
                    title=title,
                    date=node_date
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
            short_name = cname[:25] + "..." if len(cname) > 25 else cname
            title = f"Cliente: {cname}"
            if scheduled_date:
                title += f"\nFecha programada: {scheduled_date[:10]}"
            
            nodes.append(_create_node(
                node_id,
                short_name,
                "CUSTOMER",
                title=title,
                date=scheduled_date[:10] if scheduled_date else ""
            ))
            node_ids.add(node_id)
            
            # Timeline: Cliente como punto con fecha programada
            if scheduled_date:
                timeline_data.append({
                    "id": node_id,
                    "content": f"🔵 {short_name}",
                    "start": scheduled_date[:10],
                    "type": "point",
                    "group": "customer",
                    "className": "timeline-customer"
                })
    
    # Agregar edges - Ahora con nodos de recepción
    edge_aggregated = {}
    
    for link_tuple in links_raw:
        source_type, source_id, target_type, target_id, qty = link_tuple
        
        source_nid = None
        target_nid = None
        
        # Determinar nodo fuente
        if source_type == "RECV":
            # Ahora tenemos nodos de recepción, usar RECV
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
    
    # Agregar links de proveedor → recepción
    for ref, pinfo in processes.items():
        if pinfo.get("is_reception"):
            supplier_id = pinfo.get("supplier_id")
            if supplier_id:
                source_nid = f"SUPP:{supplier_id}"
                target_nid = f"RECV:{ref}"
                if source_nid in node_ids and target_nid in node_ids:
                    key = (source_nid, target_nid)
                    if key not in edge_aggregated:
                        edge_aggregated[key] = 1  # Link simple para conexión
    
    # Crear edges finales con colores heredados del nodo fuente
    # Mapear prefijo de nodo a color
    edge_colors = {
        "SUPP:": "rgba(155, 89, 182, 0.6)",   # Morado (proveedores)
        "RECV:": "rgba(26, 188, 156, 0.6)",   # Turquesa (recepciones)
        "PKG:": "rgba(243, 156, 18, 0.6)",     # Naranja (pallets - por defecto IN)
        "PROC:": "rgba(231, 76, 60, 0.6)",    # Rojo (procesos)
        "CUST:": "rgba(52, 152, 219, 0.6)",   # Azul (clientes)
    }
    
    for (source, target), qty in edge_aggregated.items():
        # Determinar color basado en el nodo fuente
        edge_color = "rgba(150, 150, 150, 0.5)"
        for prefix, color in edge_colors.items():
            if source.startswith(prefix):
                edge_color = color
                break
        
        # Si va hacia pallet OUT, usar verde
        if target.startswith("PKG:"):
            pallet_id = int(target.split(":")[1])
            if pallet_id in pallets and pallets[pallet_id].get("direction") == "OUT":
                edge_color = "rgba(46, 204, 113, 0.6)"  # Verde
        
        edges.append({
            "from": source,
            "to": target,
            "value": qty,
            "color": edge_color,
        })
    
    # Estadísticas
    receptions_count = len([p for p in processes.values() if p.get("is_reception")])
    stats = {
        "suppliers": len(suppliers),
        "receptions": receptions_count,
        "pallets_in": len([p for p in pallets.values() if p.get("direction") == "IN"]),
        "pallets_out": len([p for p in pallets.values() if p.get("direction") == "OUT"]),
        "processes": len([p for p in processes.values() if not p.get("is_reception")]),
        "customers": len(customers),
        "total_edges": len(edges),
    }
    
    # Debug: contar nodos por tipo
    nodes_by_type = {}
    for n in nodes:
        ntype = n.get("nodeType", "UNKNOWN")
        nodes_by_type[ntype] = nodes_by_type.get(ntype, 0) + 1
    print(f"[VisJS] Nodos creados por tipo: {nodes_by_type}")
    print(f"[VisJS] Total edges: {len(edges)}")
    
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
    value: float = None,
    date: str = "",
    origin_quality: str = "",
    origin_process: str = "",
    selection_reason: str = ""
) -> Dict:
    """Crea un nodo en formato vis.js con nivel jerárquico explícito."""
    colors = NODE_COLORS.get(node_type, NODE_COLORS["PROCESS"])
    level = NODE_LEVELS.get(node_type, 2)
    
    node = {
        "id": node_id,
        "label": label,
        "title": title,
        "level": level,
        "color": colors["background"],
        "date": date,  # Fecha para posicionamiento en timeline
        "nodeType": node_type,  # Tipo para agrupación visual
        "origin_quality": origin_quality,
        "origin_process": origin_process,
        "selection_reason": selection_reason,
    }
    
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

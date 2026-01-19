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
    
    # Agregar nodos de proveedores
    for sid, sname in suppliers.items():
        node_id = f"SUPP:{sid}"
        if node_id not in node_ids:
            nodes.append(_create_node(
                node_id,
                f"{NODE_ICONS['SUPPLIER']} {sname}",
                "SUPPLIER",
                title=f"Proveedor: {sname}"
            ))
            node_ids.add(node_id)
    
    # Agregar nodos de recepciones
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
                
                # Timeline data
                if date:
                    timeline_data.append({
                        "id": node_id,
                        "content": ref,
                        "start": date,
                        "type": "point",
                        "group": "reception"
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
            date = pinfo.get("first_date", "")[:10] if pinfo.get("first_date") else ""
            
            title = f"Pallet: {name}\nCantidad: {qty:.0f} kg\nProductos: {prods_str}"
            if date:
                title += f"\nFecha: {date}"
            
            nodes.append(_create_node(
                node_id,
                f"{NODE_ICONS[node_type]} {name}",
                node_type,
                title=title,
                value=qty  # Tamaño proporcional a cantidad
            ))
            node_ids.add(node_id)
            
            # Timeline data
            if date:
                timeline_data.append({
                    "id": node_id,
                    "content": name,
                    "start": date,
                    "type": "point",
                    "group": "pallet_in" if direction == "IN" else "pallet_out"
                })
    
    # Agregar nodos de procesos
    for ref, pinfo in processes.items():
        if not pinfo.get("is_reception"):
            node_id = f"PROC:{ref}"
            if node_id not in node_ids:
                date = pinfo.get("date", "")[:10] if pinfo.get("date") else ""
                nodes.append(_create_node(
                    node_id,
                    f"{NODE_ICONS['PROCESS']} {ref}",
                    "PROCESS",
                    title=f"Proceso: {ref}\nFecha: {date}"
                ))
                node_ids.add(node_id)
                
                # Timeline data
                if date:
                    timeline_data.append({
                        "id": node_id,
                        "content": ref,
                        "start": date,
                        "type": "point",
                        "group": "process"
                    })
    
    # Agregar nodos de clientes
    for cid, cname in customers.items():
        node_id = f"CUST:{cid}"
        if node_id not in node_ids:
            nodes.append(_create_node(
                node_id,
                f"{NODE_ICONS['CUSTOMER']} {cname}",
                "CUSTOMER",
                title=f"Cliente: {cname}"
            ))
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

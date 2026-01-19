"""
Transformador de datos de trazabilidad a formato React Flow.
Para usar con streamlit-flow-component.
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime


# Colores para los tipos de nodos
NODE_COLORS = {
    "SUPPLIER": "#9b59b6",    # Morado
    "RECEPTION": "#1abc9c",   # Turquesa
    "PALLET_IN": "#f39c12",   # Naranja
    "PALLET_OUT": "#2ecc71",  # Verde
    "PROCESS": "#e74c3c",     # Rojo
    "CUSTOMER": "#3498db",    # Azul
}


def transform_to_reactflow(traceability_data: Dict) -> Dict:
    """
    Transforma datos de trazabilidad a formato React Flow.
    
    Args:
        traceability_data: Datos del TraceabilityService
        
    Returns:
        Dict con:
        - nodes: Lista de nodos en formato StreamlitFlowNode
        - edges: Lista de edges en formato StreamlitFlowEdge
        - timeline_dates: Lista de fechas ordenadas para la línea de tiempo
        - stats: Estadísticas de los datos
    """
    pallets = traceability_data.get("pallets", {})
    processes = traceability_data.get("processes", {})
    suppliers = traceability_data.get("suppliers", {})
    customers = traceability_data.get("customers", {})
    links_raw = traceability_data.get("links", [])
    
    nodes = []
    edges = []
    node_index = {}
    timeline_dates = set()
    
    # Extraer fechas para timeline
    for pinfo in pallets.values():
        date = pinfo.get("first_date", "")
        if date:
            timeline_dates.add(date[:10])  # Solo fecha, sin hora
    for pinfo in processes.values():
        date = pinfo.get("date", "")
        if date:
            timeline_dates.add(date[:10])
    
    sorted_dates = sorted(list(timeline_dates))
    date_to_x = {d: (i + 1) * 200 for i, d in enumerate(sorted_dates)}
    
    def add_node(
        nid: str,
        label: str,
        node_type: str,
        date: str = "",
        extra_data: Dict = None
    ) -> str:
        """Agrega un nodo y retorna su ID."""
        if nid in node_index:
            return nid
        
        color = NODE_COLORS.get(node_type, "#666")
        
        # Calcular posición X basada en fecha
        x_pos = 100
        if date and date[:10] in date_to_x:
            x_pos = date_to_x[date[:10]]
        elif node_type == "SUPPLIER":
            x_pos = 50
        elif node_type == "CUSTOMER":
            x_pos = max(date_to_x.values(), default=800) + 150
        
        # Calcular posición Y (distribuir verticalmente)
        type_count = sum(1 for n in nodes if n.get("node_type") == node_type)
        y_pos = 100 + (type_count * 100)
        
        # Crear contenido para el nodo
        content_parts = [f"**{label}**"]
        if extra_data:
            if extra_data.get("qty"):
                content_parts.append(f"📦 {extra_data['qty']:.0f} kg")
            if extra_data.get("date"):
                content_parts.append(f"📅 {extra_data['date'][:10]}")
            if extra_data.get("products"):
                content_parts.append(f"🏷️ {extra_data['products'][:50]}")
        
        # Determinar tipo de nodo para React Flow
        rf_type = "default"
        source_pos = "right"
        target_pos = "left"
        
        if node_type == "SUPPLIER":
            rf_type = "input"
            source_pos = "right"
        elif node_type == "CUSTOMER":
            rf_type = "output"
            target_pos = "left"
        
        node = {
            "id": nid,
            "node_type": node_type,
            "position": {"x": x_pos, "y": y_pos},
            "data": {
                "content": "\n\n".join(content_parts),
                "label": label,
            },
            "type": rf_type,
            "source_position": source_pos,
            "target_position": target_pos,
            "style": {
                "backgroundColor": color,
                "color": "#fff" if color not in ["#f39c12", "#2ecc71", "#f1c40f"] else "#000",
                "border": f"2px solid {color}",
                "borderRadius": "8px",
                "padding": "10px",
                "fontSize": "11px",
                "minWidth": "140px",
            }
        }
        
        nodes.append(node)
        node_index[nid] = len(nodes) - 1
        return nid
    
    # Agregar nodos de proveedores
    for sid, sname in suppliers.items():
        add_node(
            f"SUPP:{sid}",
            f"🏭 {sname}",
            "SUPPLIER",
            extra_data={"id": sid}
        )
    
    # Agregar nodos de recepciones
    for ref, pinfo in processes.items():
        if pinfo.get("is_reception"):
            add_node(
                f"RECV:{ref}",
                f"📥 {ref}",
                "RECEPTION",
                date=pinfo.get("date", ""),
                extra_data={"ref": ref}
            )
    
    # Agregar nodos de pallets
    for pid, pinfo in pallets.items():
        direction = pinfo.get("direction", "IN")
        node_type = f"PALLET_{direction}"
        icon = "🟢" if direction == "OUT" else "🟠"
        
        prods_str = ", ".join([f"{p}: {q:.0f}kg" for p, q in list(pinfo.get("products", {}).items())[:2]])
        
        add_node(
            f"PKG:{pid}",
            f"{icon} {pinfo.get('name', str(pid))}",
            node_type,
            date=pinfo.get("first_date", ""),
            extra_data={
                "qty": pinfo.get("qty", 0),
                "products": prods_str,
                "date": pinfo.get("first_date", "")
            }
        )
    
    # Agregar nodos de procesos
    for ref, pinfo in processes.items():
        if not pinfo.get("is_reception"):
            add_node(
                f"PROC:{ref}",
                f"🔴 {ref}",
                "PROCESS",
                date=pinfo.get("date", ""),
                extra_data={"date": pinfo.get("date", "")}
            )
    
    # Agregar nodos de clientes
    for cid, cname in customers.items():
        add_node(
            f"CUST:{cid}",
            f"🔵 {cname}",
            "CUSTOMER",
            extra_data={"id": cid}
        )
    
    # Agregar edges
    edge_aggregated = {}  # (source, target) -> qty
    
    for link_tuple in links_raw:
        source_type, source_id, target_type, target_id, qty = link_tuple
        
        source_nid = None
        target_nid = None
        
        # Determinar nodo fuente
        if source_type == "RECV":
            pinfo = processes.get(source_id, {})
            supplier_id = pinfo.get("supplier_id")
            if supplier_id and f"SUPP:{supplier_id}" in node_index:
                source_nid = f"SUPP:{supplier_id}"
            elif f"RECV:{source_id}" in node_index:
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
        
        if source_nid and target_nid and source_nid in node_index and target_nid in node_index:
            key = (source_nid, target_nid)
            if key not in edge_aggregated:
                edge_aggregated[key] = 0
            edge_aggregated[key] += qty
    
    # Crear edges finales
    for i, ((source, target), qty) in enumerate(edge_aggregated.items()):
        # Determinar color basado en el tipo de conexión
        color = "#999"
        if source.startswith("SUPP:") or source.startswith("RECV:"):
            color = "#9b59b6"  # Morado
        elif source.startswith("PROC:"):
            color = "#2ecc71"  # Verde
        elif target.startswith("CUST:"):
            color = "#3498db"  # Azul
        
        edge = {
            "id": f"e{i}",
            "source": source,
            "target": target,
            "label": f"{qty:.0f} kg" if qty > 10 else "",
            "animated": False,
            "edge_type": "smoothstep",
            "style": {
                "stroke": color,
                "strokeWidth": max(1, min(4, qty / 200)),
            },
            "label_style": {
                "fontSize": "10px",
                "fill": "#666",
            }
        }
        edges.append(edge)
    
    # Recalcular posiciones Y para evitar superposición
    _adjust_vertical_positions(nodes)
    
    # Estadísticas
    stats = {
        "suppliers": len(suppliers),
        "pallets_in": len([p for p in pallets.values() if p.get("direction") == "IN"]),
        "pallets_out": len([p for p in pallets.values() if p.get("direction") == "OUT"]),
        "processes": len([p for p in processes.values() if not p.get("is_reception")]),
        "customers": len(customers),
        "total_connections": len(edges),
    }
    
    return {
        "nodes": nodes,
        "edges": edges,
        "timeline_dates": sorted_dates,
        "stats": stats
    }


def _adjust_vertical_positions(nodes: List[Dict]):
    """Ajusta posiciones verticales para evitar superposición."""
    # Agrupar nodos por posición X similar
    x_groups = {}
    for node in nodes:
        x = node["position"]["x"]
        # Agrupar en rangos de 50px
        x_key = round(x / 50) * 50
        if x_key not in x_groups:
            x_groups[x_key] = []
        x_groups[x_key].append(node)
    
    # Distribuir verticalmente dentro de cada grupo
    for x_key, group in x_groups.items():
        for i, node in enumerate(group):
            node["position"]["y"] = 80 + (i * 120)


def convert_for_streamlit_flow(reactflow_data: Dict) -> Tuple[List, List]:
    """
    Convierte los datos a objetos StreamlitFlowNode y StreamlitFlowEdge.
    
    Uso:
        from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
        nodes_data, edges_data = convert_for_streamlit_flow(reactflow_data)
        nodes = [StreamlitFlowNode(**n) for n in nodes_data]
        edges = [StreamlitFlowEdge(**e) for e in edges_data]
    """
    nodes_data = []
    edges_data = []
    
    for node in reactflow_data.get("nodes", []):
        node_data = {
            "id": node["id"],
            "pos": (node["position"]["x"], node["position"]["y"]),
            "data": node["data"],
            "node_type": node.get("type", "default"),
            "source_position": node.get("source_position", "right"),
            "target_position": node.get("target_position", "left"),
            "style": node.get("style", {}),
        }
        nodes_data.append(node_data)
    
    for edge in reactflow_data.get("edges", []):
        edge_data = {
            "id": edge["id"],
            "source": edge["source"],
            "target": edge["target"],
            "label": edge.get("label", ""),
            "animated": edge.get("animated", False),
            "edge_type": edge.get("edge_type", "smoothstep"),
            "style": edge.get("style", {}),
            "label_style": edge.get("label_style", {}),
        }
        edges_data.append(edge_data)
    
    return nodes_data, edges_data

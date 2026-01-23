"""
Transformador de datos de trazabilidad a formato Sankey (Plotly).
"""
from typing import Dict, List, Tuple


def transform_to_sankey(traceability_data: Dict) -> Dict:
    """
    Transforma datos de trazabilidad a formato Sankey para Plotly.
    
    Args:
        traceability_data: Datos del TraceabilityService
        
    Returns:
        Dict con:
        - nodes: [{label, color, detail, x, y, type}]
        - links: [{source, target, value, color}]
    """
    pallets = traceability_data.get("pallets", {})
    processes = traceability_data.get("processes", {})
    suppliers = traceability_data.get("suppliers", {})
    customers = traceability_data.get("customers", {})
    links_raw = traceability_data.get("links", [])
    
    # Construir nodos
    nodes = []
    node_index = {}
    
    def add_node(nid: str, label: str, color: str, detail: Dict, node_type: str) -> int:
        """Agrega un nodo si no existe y retorna su índice."""
        if nid not in node_index:
            node_index[nid] = len(nodes)
            nodes.append({
                "label": label,
                "color": color,
                "detail": detail,
                "type": node_type,
                "x": None,
                "y": None
            })
        return node_index[nid]
    
    # Agregar nodos de proveedores
    for sid, sinfo in suppliers.items():
        # Suppliers ahora son diccionarios con name y date_done
        if isinstance(sinfo, dict):
            sname = sinfo.get("name", "Proveedor")
            scheduled_date = sinfo.get("scheduled_date", "")
            date_done = sinfo.get("date_done", "")
        else:
            # Compatibilidad con formato antiguo (string)
            sname = sinfo
            scheduled_date = ""
            date_done = ""
        
        add_node(
            f"SUPP:{sid}",
            f"🏭 {sname}",
            "#9b59b6",  # Morado
            {
                "type": "SUPPLIER",
                "id": sid,
                "name": sname,
                "date": scheduled_date,  # Usar scheduled_date para proveedores
                "date_done": date_done
            },
            "SUPPLIER"
        )
    
    # Agregar nodos de pallets
    for pid, pinfo in pallets.items():
        prods_str = ", ".join([f"{p}: {q:.0f}kg" for p, q in pinfo.get("products", {}).items()])
        direction = pinfo.get("direction", "IN")
        
        # Color según dirección
        if direction == "OUT":
            color = "#2ecc71"  # Verde (salida)
            icon = "🟢"
        else:
            color = "#f39c12"  # Naranja (entrada)
            icon = "🟠"
        
        # Usar pack_date si existe, si no usar first_date
        pallet_date = pinfo.get("pack_date") or pinfo.get("first_date", "")
        
        add_node(
            f"PKG:{pid}",
            f"{icon} {pinfo.get('name', str(pid))}",
            color,
            {
                "type": f"PALLET_{direction}",
                "id": pid,
                "qty": pinfo.get("qty", 0),
                "products": prods_str,
                "date": pallet_date,
                "lots": ", ".join(pinfo.get("lot_names", []))
            },
            f"PALLET_{direction}"
        )
    
    # Agregar nodos de procesos (solo los que no son recepciones)
    for ref, pinfo in processes.items():
        if not pinfo.get("is_reception"):
            # Incluir fechas de MRP y producto
            mrp_start = pinfo.get("mrp_start", "")
            mrp_end = pinfo.get("mrp_end", "")
            product_name = pinfo.get("product_name", "")
            
            add_node(
                f"PROC:{ref}",
                f"🔴 {ref}",
                "#e74c3c",  # Rojo
                {
                    "type": "PROCESS",
                    "ref": ref,
                    "date": pinfo.get("date", ""),
                    "mrp_start": mrp_start,
                    "mrp_end": mrp_end,
                    "product": product_name
                },
                "PROCESS"
            )
    
    # Agregar nodos de clientes
    for cid, cinfo in customers.items():
        # Customers ahora son diccionarios con name y date_done
        if isinstance(cinfo, dict):
            cname = cinfo.get("name", "Cliente")
            date_done = cinfo.get("date_done", "")
        else:
            # Compatibilidad con formato antiguo (string)
            cname = cinfo
            date_done = ""
        
        add_node(
            f"CUST:{cid}",
            f"🔵 {cname}",
            "#3498db",  # Azul
            {
                "type": "CUSTOMER",
                "id": cid,
                "name": cname,
                "date": date_done
            },
            "CUSTOMER"
        )
    
    # Agregar nodos de recepción (turquesa)
    for ref, pinfo in processes.items():
        if pinfo.get("is_reception"):
            supplier_id = pinfo.get("supplier_id")
            supplier_name = suppliers.get(supplier_id, {}).get("name", "Proveedor") if isinstance(suppliers.get(supplier_id), dict) else suppliers.get(supplier_id, "Proveedor")
            scheduled_date = pinfo.get("scheduled_date", "")
            date_done = pinfo.get("date_done", "")
            albaran = pinfo.get("albaran", "")
            guia_despacho = pinfo.get("guia_despacho", "")
            origen = pinfo.get("origen", "")
            transportista = pinfo.get("transportista", "")
            
            add_node(
                f"RECV:{ref}",
                f"📥 {ref}",
                "#9b59b6",  # Morado
                {
                    "type": "RECEPTION",
                    "ref": ref,
                    "date": scheduled_date,  # Usar scheduled_date para recepciones
                    "date_done": date_done,
                    "supplier": supplier_name,
                    "albaran": albaran,
                    "guia_despacho": guia_despacho,
                    "origen": origen,
                    "transportista": transportista
                },
                "RECEPTION"
            )
    
    # Construir links
    links = []
    link_aggregated = {}  # (source_nid, target_nid) -> qty
    
    for link_tuple in links_raw:
        source_type, source_id, target_type, target_id, qty = link_tuple
        
        source_nid = None
        target_nid = None
        color = "rgba(200, 200, 200, 0.5)"
        
        # Determinar nodo fuente
        if source_type == "RECV":
            # Buscar si hay proveedor asociado
            pinfo = processes.get(source_id, {})
            supplier_id = pinfo.get("supplier_id")
            if supplier_id:
                source_nid = f"SUPP:{supplier_id}"
                color = "rgba(155, 89, 182, 0.5)"  # Morado
            else:
                source_nid = f"RECV:{source_id}"
                color = "rgba(26, 188, 156, 0.5)"  # Turquesa
        elif source_type == "PALLET":
            source_nid = f"PKG:{source_id}"
            color = "rgba(243, 156, 18, 0.5)"  # Naranja
        elif source_type == "PROCESS":
            source_nid = f"PROC:{source_id}"
            color = "rgba(46, 204, 113, 0.5)"  # Verde
        
        # Determinar nodo destino
        if target_type == "PALLET":
            target_nid = f"PKG:{target_id}"
        elif target_type == "PROCESS":
            target_nid = f"PROC:{target_id}"
        elif target_type == "CUSTOMER":
            target_nid = f"CUST:{target_id}"
            color = "rgba(52, 152, 219, 0.5)"  # Azul
        
        # Agregar link si ambos nodos existen
        if source_nid and target_nid and source_nid in node_index and target_nid in node_index:
            key = (source_nid, target_nid)
            if key not in link_aggregated:
                link_aggregated[key] = {"qty": 0, "color": color}
            link_aggregated[key]["qty"] += qty
    
    # Crear links finales
    for (source_nid, target_nid), info in link_aggregated.items():
        links.append({
            "source": node_index[source_nid],
            "target": node_index[target_nid],
            "value": info["qty"] or 1,
            "color": info["color"]
        })
    
    # Calcular posiciones
    _calculate_positions(nodes, links, node_index, processes)
    
    return {"nodes": nodes, "links": links}


def _calculate_positions(
    nodes: List[Dict],
    links: List[Dict],
    node_index: Dict[str, int],
    processes: Dict
):
    """Calcula posiciones X,Y para los nodos."""
    
    def set_pos(nid: str, x: float, y: float):
        if nid in node_index:
            nodes[node_index[nid]]["x"] = x
            nodes[node_index[nid]]["y"] = y
    
    # Clasificar nodos por tipo
    supp_nodes = [nid for nid in node_index if nid.startswith("SUPP:")]
    recv_nodes = [nid for nid in node_index if nid.startswith("RECV:")]
    cust_nodes = [nid for nid in node_index if nid.startswith("CUST:")]
    proc_nodes = [nid for nid in node_index if nid.startswith("PROC:")]
    pkg_nodes = [nid for nid in node_index if nid.startswith("PKG:")]
    
    # Proveedores: x=0.02
    for i, nid in enumerate(supp_nodes):
        y = (i + 1) / (len(supp_nodes) + 1)
        set_pos(nid, 0.02, y)
    
    # Recepciones: x=0.12
    for i, nid in enumerate(recv_nodes):
        y = (i + 1) / (len(recv_nodes) + 1)
        set_pos(nid, 0.12, y)
    
    # Clientes: x=0.98
    for i, nid in enumerate(cust_nodes):
        y = (i + 1) / (len(cust_nodes) + 1)
        set_pos(nid, 0.98, y)
    
    # Procesos ordenados por fecha: x entre 0.35 y 0.65
    proc_sorted = sorted(
        proc_nodes,
        key=lambda n: processes.get(n.replace("PROC:", ""), {}).get("date", "")
    )
    for i, nid in enumerate(proc_sorted):
        if len(proc_sorted) > 1:
            x = 0.35 + (0.3 * i / (len(proc_sorted) - 1))
        else:
            x = 0.5
        y = (i + 1) / (len(proc_sorted) + 1)
        set_pos(nid, x, y)
    
    # Pallets: posicionar según conexiones y tipo
    for nid in pkg_nodes:
        idx = node_index[nid]
        node_type = nodes[idx].get("type", "")
        
        # Encontrar nodos conectados
        connected_x = []
        connected_y = []
        is_from_process = False
        is_to_process = False
        is_from_supplier = False
        is_to_customer = False
        
        for link in links:
            if link["source"] == idx:
                target_idx = link["target"]
                target_nid = [k for k, v in node_index.items() if v == target_idx]
                if target_nid:
                    target_nid = target_nid[0]
                    if target_nid.startswith("PROC:"):
                        is_to_process = True
                    elif target_nid.startswith("CUST:"):
                        is_to_customer = True
                if nodes[target_idx]["x"]:
                    connected_x.append(nodes[target_idx]["x"])
                    connected_y.append(nodes[target_idx]["y"])
            
            if link["target"] == idx:
                source_idx = link["source"]
                source_nid = [k for k, v in node_index.items() if v == source_idx]
                if source_nid:
                    source_nid = source_nid[0]
                    if source_nid.startswith("PROC:"):
                        is_from_process = True
                    elif source_nid.startswith("SUPP:") or source_nid.startswith("RECV:"):
                        is_from_supplier = True
                if nodes[source_idx]["x"]:
                    connected_x.append(nodes[source_idx]["x"])
                    connected_y.append(nodes[source_idx]["y"])
        
        if connected_x:
            avg_x = sum(connected_x) / len(connected_x)
            avg_y = sum(connected_y) / len(connected_y)
            
            # Ajustar posición según flujo
            if is_from_supplier and is_to_process:
                # Pallet de recepción que va a proceso
                x = 0.22
            elif is_from_process and is_to_customer:
                # Pallet que sale de proceso hacia cliente
                x = 0.85
            elif is_from_process and is_to_process:
                # Pallet intermedio entre procesos
                x = avg_x
            elif is_to_process:
                # Entra a proceso
                x = avg_x - 0.1
            elif is_from_process:
                # Sale de proceso
                x = avg_x + 0.1
            else:
                x = avg_x
            
            set_pos(nid, max(0.05, min(0.95, x)), avg_y)
        else:
            # Sin conexiones conocidas
            set_pos(nid, 0.2, 0.5)

"""
Servicio para gestión de Ventas/Containers y su seguimiento de producción
OPTIMIZADO: Parte desde fabricaciones con PO asociada para evitar consultas lentas

REFACTORIZADO: Constantes, helpers y Sankey extraídos a módulos separados.
"""
from typing import List, Dict, Optional
from shared.odoo_client import OdooClient
from backend.utils import clean_record, get_name_from_relation, get_state_display

from .constants import get_state_display as local_get_state_display
from .helpers import (
    build_pallet_products, 
    build_container_detail, 
    build_fabrication_detail,
    build_pallet_detail
)


class ContainersService:
    """Servicio para operaciones de Ventas (Containers) y seguimiento de fabricación"""

    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)

    def get_containers(self, 
                       start_date: Optional[str] = None, 
                       end_date: Optional[str] = None,
                       partner_id: Optional[int] = None,
                       state: Optional[str] = None) -> List[Dict]:
        """
        Obtiene lista de ventas/containers con su avance de producción.
        OPTIMIZADO: Busca desde fabricaciones que tienen x_studio_po_asociada_1
        """
        # PASO 1: Buscar TODAS las fabricaciones que tienen una PO asociada
        prod_domain = [("x_studio_po_asociada_1", "!=", False)]
        if start_date:
            prod_domain.append(("date_planned_start", ">=", start_date))
        if end_date:
            prod_domain.append(("date_planned_start", "<=", end_date))
        
        prod_fields = [
            "name", "product_id", "product_qty", "qty_produced",
            "state", "date_planned_start", "date_start", "date_finished",
            "user_id", "x_studio_po_asociada_1", "x_studio_po_cliente_1",
            "x_studio_kg_totales_po", "x_studio_kg_consumidos_po",
            "x_studio_kg_disponibles_po", "x_studio_sala_de_proceso",
            "x_studio_clientes"
        ]
        fallback_prod_fields = [
            "name", "product_id", "product_qty", "qty_produced",
            "state", "date_planned_start", "date_start", "date_finished",
            "user_id", "x_studio_po_asociada_1", "x_studio_po_cliente_1",
            "x_studio_kg_totales_po", "x_studio_kg_consumidos_po",
            "x_studio_kg_disponibles_po", "x_studio_sala_de_proceso"
        ]
        
        try:
            prod_ids = self.odoo.search(
                "mrp.production",
                prod_domain,
                limit=1000,
                order="date_planned_start desc"
            )
            
            if not prod_ids:
                return []
            
            try:
                prods_raw = self.odoo.read("mrp.production", prod_ids, prod_fields)
            except Exception as e:
                print(f"Error fetching productions with extra fields: {e}")
                prods_raw = self.odoo.read("mrp.production", prod_ids, fallback_prod_fields)
        except Exception as e:
            print(f"Error fetching productions: {e}")
            return []
        
        # PASO 2: Agrupar fabricaciones por sale.order (PO asociada)
        sales_map = {}  # sale_id -> {info, productions: []}
        sale_ids_to_fetch = set()
        
        for p in prods_raw:
            po_asociada = p.get("x_studio_po_asociada_1")
            if not po_asociada:
                continue
            
            sale_id = po_asociada[0] if isinstance(po_asociada, (list, tuple)) else po_asociada
            sale_ids_to_fetch.add(sale_id)
            
            if sale_id not in sales_map:
                sales_map[sale_id] = {
                    "productions": [],
                    "kg_producidos_total": 0
                }
            
            qty_produced = p.get("qty_produced", 0) or 0
            
            # Obtener nombres
            product = p.get("product_id")
            product_name = product[1] if isinstance(product, (list, tuple)) else "N/A"
            
            user = p.get("user_id")
            user_name = user[1] if isinstance(user, (list, tuple)) else "N/A"
            
            sala = p.get("x_studio_sala_de_proceso")
            sala_name = sala[1] if isinstance(sala, (list, tuple)) else "N/A"

            cliente = p.get("x_studio_clientes")
            cliente_name = cliente[1] if isinstance(cliente, (list, tuple)) else "N/A"
            
            sales_map[sale_id]["productions"].append({
                "id": p["id"],
                "name": p.get("name", ""),
                "product_name": product_name,
                "product_qty": p.get("product_qty", 0) or 0,
                "qty_produced": qty_produced,
                "kg_producidos": qty_produced,
                "state": p.get("state", ""),
                "state_display": local_get_state_display(p.get("state", "")),
                "date_planned_start": p.get("date_planned_start", ""),
                "date_start": p.get("date_start", ""),
                "date_finished": p.get("date_finished", ""),
                "user_name": user_name,
                "po_cliente": p.get("x_studio_po_cliente_1", ""),
                "kg_totales_po": p.get("x_studio_kg_totales_po", 0),
                "kg_consumidos_po": p.get("x_studio_kg_consumidos_po", 0),
                "kg_disponibles_po": p.get("x_studio_kg_disponibles_po", 0),
                "sala_proceso": sala_name,
                "cliente": cliente_name
            })
            
            sales_map[sale_id]["kg_producidos_total"] += qty_produced
        
        if not sale_ids_to_fetch:
            return []
        
        # PASO 3: Obtener datos de las ventas (sale.order) en UNA sola llamada
        sale_fields = [
            "name", "partner_id", "date_order", "commitment_date",
            "state", "amount_total", "currency_id", "origin",
            "user_id", "order_line", "client_id", "validity_date"
        ]
        fallback_sale_fields = [
            "name", "partner_id", "date_order", "commitment_date",
            "state", "amount_total", "currency_id", "origin",
            "user_id", "order_line"
        ]
        
        sale_domain = [("id", "in", list(sale_ids_to_fetch))]
        if partner_id:
            sale_domain.append(("partner_id", "=", partner_id))
        if state:
            sale_domain.append(("state", "=", state))
        
        try:
            filtered_sale_ids = self.odoo.search("sale.order", sale_domain)
            
            if not filtered_sale_ids:
                return []
            
            try:
                sales_raw = self.odoo.read("sale.order", filtered_sale_ids, sale_fields)
            except Exception as e:
                print(f"Error fetching sales with extra fields: {e}")
                sales_raw = self.odoo.read("sale.order", filtered_sale_ids, fallback_sale_fields)
        except Exception as e:
            print(f"Error fetching sales: {e}")
            return []
        
        # PASO 4: Obtener líneas de venta en UNA sola llamada
        all_line_ids = []
        for s in sales_raw:
            all_line_ids.extend(s.get("order_line", []))
        
        lines_map = {}  # sale_id -> [lines]
        if all_line_ids:
            try:
                lines_raw = self.odoo.read(
                    "sale.order.line",
                    all_line_ids,
                    ["order_id", "product_id", "name", "product_uom_qty", 
                     "product_uom", "price_unit", "price_subtotal", 
                     "qty_delivered", "qty_invoiced"]
                )
                for l in lines_raw:
                    order_id = l.get("order_id")
                    if order_id:
                        oid = order_id[0] if isinstance(order_id, (list, tuple)) else order_id
                        if oid not in lines_map:
                            lines_map[oid] = []
                        lines_map[oid].append(clean_record(l))
            except Exception as e:
                print(f"Error fetching lines: {e}")
        
        # PASO 5: Construir resultado final
        containers = []
        
        for sale in sales_raw:
            sale_id = sale["id"]
            
            # Obtener partner name ANTES de clean_record
            partner = sale.get("partner_id")
            partner_name = partner[1] if partner and isinstance(partner, (list, tuple)) and len(partner) > 1 else "N/A"
            
            sale_clean = clean_record(sale)
            
            # Líneas de este pedido
            lines_data = lines_map.get(sale_id, [])
            
            # KG totales del pedido (suma de líneas)
            kg_total = sum([l.get("product_uom_qty", 0) or 0 for l in lines_data])
            
            # Producciones y KG producidos
            sale_info = sales_map.get(sale_id, {"productions": [], "kg_producidos_total": 0})
            productions = sale_info["productions"]
            kg_producidos = sale_info["kg_producidos_total"]
            
            kg_disponibles = kg_total - kg_producidos
            avance_pct = (kg_producidos / kg_total * 100) if kg_total > 0 else 0
            
            # Producto principal
            producto_principal = "N/A"
            if lines_data:
                prod = lines_data[0].get("product_id")
                if isinstance(prod, dict):
                    producto_principal = prod.get("name", "N/A")
            
            client_name = get_name_from_relation(sale_clean.get("client_id"))
            if client_name == "N/A":
                client_name = partner_name

            containers.append({
                "id": sale_id,
                "name": sale_clean.get("name", ""),
                "partner_id": sale_clean.get("partner_id", {}),
                "partner_name": partner_name,
                "client_id": sale_clean.get("client_id", {}),
                "client_name": client_name,
                "date_order": sale_clean.get("date_order", ""),
                "commitment_date": sale_clean.get("commitment_date", ""),
                "validity_date": sale_clean.get("validity_date", ""),
                "state": sale_clean.get("state", ""),
                "origin": sale_clean.get("origin", ""),
                "currency_id": sale_clean.get("currency_id", {}),
                "amount_total": sale_clean.get("amount_total", 0),
                "user_id": sale_clean.get("user_id", {}),
                "producto_principal": producto_principal,
                "kg_total": kg_total,
                "kg_producidos": kg_producidos,
                "kg_disponibles": kg_disponibles,
                "avance_pct": round(avance_pct, 2),
                "num_fabricaciones": len(productions),
                "lines": lines_data,
                "productions": productions
            })
        
        return containers

    def get_container_detail(self, sale_id: int) -> Dict:
        """
        Obtiene el detalle completo de un container/venta específico.
        OPTIMIZADO: Usa consultas paralelas para producciones y venta.
        """
        prod_domain = [("x_studio_po_asociada_1", "=", sale_id)]
        
        prod_fields = [
            "name", "product_id", "product_qty", "qty_produced",
            "state", "date_planned_start", "date_start", "date_finished",
            "user_id", "x_studio_po_cliente_1", "x_studio_kg_totales_po",
            "x_studio_kg_consumidos_po", "x_studio_kg_disponibles_po",
            "x_studio_sala_de_proceso"
        ]
        
        sale_fields = [
            "name", "partner_id", "date_order", "commitment_date",
            "state", "amount_total", "currency_id", "origin", "order_line"
        ]
        
        # OPTIMIZADO: Ejecutar búsqueda de producciones y lectura de venta en paralelo
        try:
            results = self.odoo.parallel_search_read([
                {
                    "model": "mrp.production",
                    "domain": prod_domain,
                    "fields": prod_fields
                },
                {
                    "model": "sale.order",
                    "domain": [("id", "=", sale_id)],
                    "fields": sale_fields
                }
            ])
            prods_raw = results[0]
            sales_raw = results[1]
        except Exception as e:
            print(f"Error parallel query: {e}")
            # Fallback a consultas secuenciales
            try:
                prod_ids = self.odoo.search("mrp.production", prod_domain)
                prods_raw = self.odoo.read("mrp.production", prod_ids, prod_fields) if prod_ids else []
                sales_raw = self.odoo.read("sale.order", [sale_id], sale_fields)
            except Exception as e2:
                print(f"Error fallback: {e2}")
                return {}
        
        if not sales_raw:
            return {}
        sale = sales_raw[0]
        
        productions = []
        kg_producidos = 0
        
        for p in prods_raw:
            qty = p.get("qty_produced", 0) or 0
            kg_producidos += qty
            
            product = p.get("product_id")
            product_name = product[1] if isinstance(product, (list, tuple)) else "N/A"
            
            user = p.get("user_id")
            user_name = user[1] if isinstance(user, (list, tuple)) else "N/A"
            
            sala = p.get("x_studio_sala_de_proceso")
            sala_name = sala[1] if isinstance(sala, (list, tuple)) else "N/A"
            
            productions.append({
                "id": p["id"],
                "name": p.get("name", ""),
                "product_name": product_name,
                "product_qty": p.get("product_qty", 0) or 0,
                "qty_produced": qty,
                "kg_producidos": qty,
                "state": p.get("state", ""),
                "state_display": get_state_display(p.get("state", "")),
                "date_planned_start": p.get("date_planned_start", ""),
                "date_start": p.get("date_start", ""),
                "date_finished": p.get("date_finished", ""),
                "user_name": user_name,
                "sala_proceso": sala_name
            })
        
        sale_clean = clean_record(sale)
        
        partner = sale.get("partner_id")
        partner_name = partner[1] if isinstance(partner, (list, tuple)) else "N/A"
        
        # Líneas
        line_ids = sale.get("order_line", [])
        lines_data = []
        kg_total = 0
        
        if line_ids:
            try:
                lines_raw = self.odoo.read(
                    "sale.order.line",
                    line_ids,
                    ["product_id", "name", "product_uom_qty", "product_uom",
                     "price_unit", "price_subtotal", "qty_delivered"]
                )
                lines_data = [clean_record(l) for l in lines_raw]
                kg_total = sum([l.get("product_uom_qty", 0) or 0 for l in lines_data])
            except Exception as e:
                print(f"Error lines: {e}")
        
        avance_pct = (kg_producidos / kg_total * 100) if kg_total > 0 else 0
        
        producto_principal = "N/A"
        if lines_data:
            prod = lines_data[0].get("product_id")
            if isinstance(prod, dict):
                producto_principal = prod.get("name", "N/A")
        
        return {
            "id": sale_id,
            "name": sale_clean.get("name", ""),
            "partner_name": partner_name,
            "date_order": sale_clean.get("date_order", ""),
            "commitment_date": sale_clean.get("commitment_date", ""),
            "state": sale_clean.get("state", ""),
            "origin": sale_clean.get("origin", ""),
            "amount_total": sale_clean.get("amount_total", 0),
            "producto_principal": producto_principal,
            "kg_total": kg_total,
            "kg_producidos": kg_producidos,
            "kg_disponibles": kg_total - kg_producidos,
            "avance_pct": round(avance_pct, 2),
            "num_fabricaciones": len(productions),
            "lines": lines_data,
            "productions": productions
        }

    def get_partners_with_orders(self) -> List[Dict]:
        """Obtiene lista de clientes que tienen pedidos con fabricaciones"""
        try:
            prod_domain = [("x_studio_po_asociada_1", "!=", False)]
            prods = self.odoo.search_read(
                "mrp.production",
                prod_domain,
                ["x_studio_po_asociada_1"],
                limit=500
            )
            
            sale_ids = list(set([
                p["x_studio_po_asociada_1"][0] 
                for p in prods 
                if p.get("x_studio_po_asociada_1")
            ]))
            
            if not sale_ids:
                return []
            
            sales = self.odoo.read("sale.order", sale_ids, ["partner_id"])
            
            partner_ids = list(set([
                s["partner_id"][0] 
                for s in sales 
                if s.get("partner_id")
            ]))
            
            if not partner_ids:
                return []
            
            partners = self.odoo.read("res.partner", partner_ids, ["id", "name"])
            
            return sorted([{"id": p["id"], "name": p["name"]} for p in partners], key=lambda x: x["name"])
            
        except Exception as e:
            print(f"Error fetching partners: {e}")
            return []

    def get_containers_summary(self) -> Dict:
        """Obtiene resumen global de containers para KPIs"""
        containers = self.get_containers()
        
        total_containers = len(containers)
        total_kg = sum([c.get("kg_total", 0) for c in containers])
        total_producidos = sum([c.get("kg_producidos", 0) for c in containers])
        avance_global = (total_producidos / total_kg * 100) if total_kg > 0 else 0
        
        containers_activos = len([c for c in containers if c.get("state") in ["draft", "sent", "sale"]])
        containers_completados = len([c for c in containers if c.get("avance_pct", 0) >= 100])
        
        return {
            "total_containers": total_containers,
            "containers_activos": containers_activos,
            "containers_completados": containers_completados,
            "total_kg": total_kg,
            "total_producidos": total_producidos,
            "kg_pendientes": total_kg - total_producidos,
            "avance_global_pct": round(avance_global, 2)
        }
    
    def get_sankey_data(self, start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       limit: int = 50) -> Dict:
        """
        Genera datos para diagrama Sankey de trazabilidad.
        Flujo: Container → Fabricación → Pallets Consumidos
               Fabricación → Pallets de Salida
        
        Returns:
            {
                "nodes": [{"label": "...", "color": "..."}],
                "links": [{"source": idx, "target": idx, "value": kg}]
            }
        """
        # Layout buscado (como la imagen):
        # IN (izq) -> Proceso/Fabricación (centro) -> OUT (der)
        # - OUT con container: se agrupan por container (cliente)
        # - OUT sin container: quedan en amarillo cerca del proceso

        containers = self.get_containers(start_date, end_date)[:limit]

        # Producciones en containers (mantiene el orden actual)
        production_to_container: Dict[int, Dict] = {}
        productions_order: List[Dict] = []
        for container in containers:
            for fab in container.get("productions", []) or []:
                production_to_container[fab["id"]] = container
                productions_order.append(fab)

        # Producciones sin container (x_studio_po_asociada_1 vacío)
        orphan_productions: List[Dict] = []
        orphan_domain = [("x_studio_po_asociada_1", "=", False), ("state", "not in", ["cancel"])]
        if start_date:
            orphan_domain.append(("date_planned_start", ">=", start_date))
        if end_date:
            orphan_domain.append(("date_planned_start", "<=", end_date))

        orphan_fields = [
            "name", "product_id", "product_qty", "qty_produced",
            "state", "date_planned_start", "date_start", "date_finished",
            "user_id", "x_studio_sala_de_proceso", "x_studio_clientes"
        ]

        try:
            orphan_ids = self.odoo.search(
                "mrp.production",
                orphan_domain,
                limit=200,
                order="date_planned_start desc"
            )
            if orphan_ids:
                orphans_raw = self.odoo.read("mrp.production", orphan_ids, orphan_fields)
                for p in orphans_raw:
                    product = p.get("product_id")
                    product_name = product[1] if isinstance(product, (list, tuple)) else "N/A"

                    user = p.get("user_id")
                    user_name = user[1] if isinstance(user, (list, tuple)) else "N/A"

                    sala = p.get("x_studio_sala_de_proceso")
                    sala_name = sala[1] if isinstance(sala, (list, tuple)) else "N/A"

                    cliente = p.get("x_studio_clientes")
                    cliente_name = cliente[1] if isinstance(cliente, (list, tuple)) else "N/A"

                    qty_produced = p.get("qty_produced", 0) or 0

                    orphan_productions.append({
                        "id": p["id"],
                        "name": p.get("name", ""),
                        "product_name": product_name,
                        "product_qty": p.get("product_qty", 0) or 0,
                        "qty_produced": qty_produced,
                        "kg_producidos": qty_produced,
                        "state": p.get("state", ""),
                        "state_display": local_get_state_display(p.get("state", "")),
                        "date_planned_start": p.get("date_planned_start", ""),
                        "date_start": p.get("date_start", ""),
                        "date_finished": p.get("date_finished", ""),
                        "user_name": user_name,
                        "sala_proceso": sala_name,
                        "cliente": cliente_name,
                    })
        except Exception as e:
            print(f"Error fetching orphan productions for sankey: {e}")

        productions_order.extend(orphan_productions)

        extra_prod_ids = [p["id"] for p in orphan_productions]
        sankey_context = self._get_sankey_context(containers, extra_production_ids=extra_prod_ids)
        productions_by_id = sankey_context.get("productions", {})
        pallets_by_production = sankey_context.get("pallets", {})

        nodes: List[Dict] = []
        links: List[Dict] = []
        node_index: Dict[str, int] = {}
        node_meta: Dict[str, Dict] = {}

        container_out_nodes: Dict[int, List[str]] = {}

        def _ensure_node(node_id: str, label: str, color: str, detail: Dict, meta: Dict) -> int:
            if node_id not in node_index:
                node_index[node_id] = len(nodes)
                nodes.append({
                    "label": label,
                    "detail": detail,
                    "color": color,
                    "x": None,
                    "y": None,
                })
                node_meta[node_id] = meta
            return node_index[node_id]

        # Nodos/links por fabricación
        for fab in productions_order:
            prod_id = fab["id"]
            container = production_to_container.get(prod_id)
            container_id = container.get("id") if container else None

            f_id = f"F:{prod_id}"
            f_idx = _ensure_node(
                f_id,
                fab.get("name", ""),
                "#e74c3c",
                build_fabrication_detail(fab, productions_by_id.get(prod_id, {})),
                {"type": "fab", "container_id": container_id}
            )

            pallets_data = pallets_by_production.get(prod_id, {"consumidos": [], "salida": []})

            # IN
            for pallet_in in pallets_data.get("consumidos", []) or []:
                p_in_id = f"PIN:{pallet_in.get('name', '')}"
                p_in_idx = _ensure_node(
                    p_in_id,
                    f"IN: {pallet_in.get('name', '')}",
                    "#f39c12",
                    build_pallet_detail(pallet_in),
                    {"type": "in"}
                )
                links.append({
                    "source": p_in_idx,
                    "target": f_idx,
                    "value": pallet_in.get("qty", 1) or 1
                })

            # OUT
            for pallet_out in pallets_data.get("salida", []) or []:
                pallet_out_key = pallet_out.get("id") or pallet_out.get("name")
                if container_id:
                    out_id = f"POUT:C{container_id}:P{pallet_out_key}"
                    out_color = "#2ecc71"
                    out_meta = {"type": "out_container", "container_id": container_id}
                else:
                    out_id = f"POUT:NONE:P{pallet_out_key}"
                    out_color = "#f1c40f"  # amarillo sin container
                    out_meta = {"type": "out_orphan"}

                out_idx = _ensure_node(
                    out_id,
                    f"OUT: {pallet_out.get('name', '')}",
                    out_color,
                    build_pallet_detail(pallet_out),
                    out_meta
                )
                links.append({
                    "source": f_idx,
                    "target": out_idx,
                    "value": pallet_out.get("qty", 1) or 1
                })

                # Agrupar OUT en container (OUT -> Container)
                if container_id:
                    c_id = f"C:{container_id}"
                    c_idx = _ensure_node(
                        c_id,
                        container.get("name", ""),
                        "#3498db",
                        build_container_detail(container),
                        {"type": "container", "container_id": container_id}
                    )
                    links.append({
                        "source": out_idx,
                        "target": c_idx,
                        "value": pallet_out.get("qty", 1) or 1
                    })
                    container_out_nodes.setdefault(container_id, []).append(out_id)

        # Coordenadas para un layout tipo imagen
        def _set_xy(node_id: str, x: float, y: float) -> None:
            idx = node_index.get(node_id)
            if idx is None:
                return
            nodes[idx]["x"] = float(x)
            nodes[idx]["y"] = float(y)

        def _spread_y(node_ids: List[str], y0: float = 0.02, y1: float = 0.98) -> Dict[str, float]:
            if not node_ids:
                return {}
            n = len(node_ids)
            if n == 1:
                return {node_ids[0]: (y0 + y1) / 2}
            step = (y1 - y0) / (n - 1)
            return {nid: y0 + i * step for i, nid in enumerate(node_ids)}

        in_ids = [nid for nid, meta in node_meta.items() if meta.get("type") == "in"]
        fab_ids = [nid for nid, meta in node_meta.items() if meta.get("type") == "fab"]
        orphan_out_ids = [nid for nid, meta in node_meta.items() if meta.get("type") == "out_orphan"]

        for nid, y in _spread_y(in_ids, 0.05, 0.95).items():
            _set_xy(nid, 0.02, y)
        for nid, y in _spread_y(fab_ids, 0.05, 0.95).items():
            _set_xy(nid, 0.45, y)
        for nid, y in _spread_y(orphan_out_ids, 0.78, 0.95).items():
            _set_xy(nid, 0.68, y)

        container_ids_in_order = [c.get("id") for c in containers]
        active_container_ids = [cid for cid in container_ids_in_order if container_out_nodes.get(cid)]
        total_slots = sum(max(1, len(container_out_nodes.get(cid, []))) for cid in active_container_ids)
        if total_slots > 0:
            slot_cursor = 0
            for cid in active_container_ids:
                out_node_ids = container_out_nodes.get(cid, [])
                block_slots = max(1, len(out_node_ids))

                center_slot = slot_cursor + (block_slots / 2)
                center_y = 0.02 + 0.96 * (center_slot / total_slots)
                _set_xy(f"C:{cid}", 0.98, center_y)

                for j, out_nid in enumerate(out_node_ids):
                    y = 0.02 + 0.96 * ((slot_cursor + (j + 0.5)) / total_slots)
                    _set_xy(out_nid, 0.86, y)

                slot_cursor += block_slots

        return {"nodes": nodes, "links": links}
    
    def _get_sankey_context(self, containers: List[Dict], extra_production_ids: Optional[List[int]] = None) -> Dict:
        """Obtiene contexto de producciones y pallets para Sankey."""
        production_ids = []
        for container in containers:
            for fab in container.get("productions", []) or []:
                if fab.get("id"):
                    production_ids.append(fab.get("id"))

        if extra_production_ids:
            production_ids.extend([pid for pid in extra_production_ids if pid])

        if not production_ids:
            return {"productions": {}, "pallets": {}}

        prod_data = self.odoo.read(
            "mrp.production",
            list(set(production_ids)),
            ["id", "move_raw_ids", "move_finished_ids"]
        )

        prod_moves_map = {}
        raw_move_ids = []
        finished_move_ids = []
        for prod in prod_data:
            raw_ids = prod.get("move_raw_ids", []) or []
            finished_ids = prod.get("move_finished_ids", []) or []
            prod_moves_map[prod["id"]] = {
                "raw_ids": raw_ids,
                "finished_ids": finished_ids
            }
            raw_move_ids.extend(raw_ids)
            finished_move_ids.extend(finished_ids)

        move_ids = list(set(raw_move_ids + finished_move_ids))
        moves_by_id = {}
        if move_ids:
            move_fields = [
                "id",
                "product_id",
                "quantity_done",
                "product_uom_qty",
                "x_studio_float_field_hZJh1"
            ]
            fallback_move_fields = [
                "id",
                "product_id",
                "quantity_done",
                "product_uom_qty"
            ]
            try:
                moves_raw = self.odoo.read("stock.move", move_ids, move_fields)
            except Exception as e:
                print(f"Error fetching moves with extra fields: {e}")
                moves_raw = self.odoo.read("stock.move", move_ids, fallback_move_fields)
            moves_by_id = {move["id"]: move for move in moves_raw}

        production_details = {}
        move_to_production = {}
        for prod_id, move_ids_by_type in prod_moves_map.items():
            for move_id in move_ids_by_type.get("raw_ids", []):
                move_to_production[move_id] = prod_id
            for move_id in move_ids_by_type.get("finished_ids", []):
                move_to_production[move_id] = prod_id

            moves = []
            subproducts = []
            x_studio_total = 0
            sub_total_qty = 0
            sub_total_done = 0

            for move_id in move_ids_by_type.get("raw_ids", []) + move_ids_by_type.get("finished_ids", []):
                move = moves_by_id.get(move_id)
                if not move:
                    continue
                product_name = get_name_from_relation(move.get("product_id"))
                quantity_done = move.get("quantity_done", 0) or 0
                x_studio_value = move.get("x_studio_float_field_hZJh1", 0) or 0
                moves.append({
                    "product": product_name,
                    "quantity_done": quantity_done,
                    "x_studio_float_field_hZJh1": x_studio_value
                })
                x_studio_total += x_studio_value

                if move_id in move_ids_by_type.get("finished_ids", []):
                    product_uom_qty = move.get("product_uom_qty", 0) or 0
                    subproducts.append({
                        "product": product_name,
                        "product_uom_qty": product_uom_qty,
                        "quantity_done": quantity_done
                    })
                    sub_total_qty += product_uom_qty
                    sub_total_done += quantity_done

            production_details[prod_id] = {
                "moves": moves,
                "subproducts": subproducts,
                "x_studio_total": x_studio_total,
                "subproducts_totals": {
                    "product_uom_qty": sub_total_qty,
                    "quantity_done": sub_total_done
                }
            }

        pallets_by_production = {
            prod_id: {"consumidos": [], "salida": []} for prod_id in prod_moves_map.keys()
        }
        package_ids = set()
        pallets_by_key = {}
        excluded = ["caja", "bolsa", "insumo", "envase", "pallet", "etiqueta"]

        if raw_move_ids:
            lines_in = self.odoo.search_read(
                "stock.move.line",
                [["move_id", "in", raw_move_ids]],
                ["package_id", "qty_done", "product_id", "move_id"]
            )
            for line in lines_in:
                move_id = line.get("move_id")
                prod_id = move_to_production.get(move_id[0] if isinstance(move_id, (list, tuple)) else move_id)
                pkg = line.get("package_id")
                qty = line.get("qty_done", 0) or 0
                if not pkg or qty <= 0 or not prod_id:
                    continue
                prod_name = get_name_from_relation(line.get("product_id")).lower()
                if any(ex in prod_name for ex in excluded):
                    continue
                pkg_id = pkg[0] if isinstance(pkg, (list, tuple)) else pkg
                package_ids.add(pkg_id)
                key = (prod_id, pkg_id, "consumidos")
                pallets_by_key.setdefault(key, {"qty": 0})
                pallets_by_key[key]["qty"] += qty

        if finished_move_ids:
            lines_out = self.odoo.search_read(
                "stock.move.line",
                [["move_id", "in", finished_move_ids]],
                ["result_package_id", "qty_done", "product_id", "move_id"]
            )
            for line in lines_out:
                move_id = line.get("move_id")
                prod_id = move_to_production.get(move_id[0] if isinstance(move_id, (list, tuple)) else move_id)
                pkg = line.get("result_package_id")
                qty = line.get("qty_done", 0) or 0
                if not pkg or qty <= 0 or not prod_id:
                    continue
                prod_name = get_name_from_relation(line.get("product_id")).lower()
                if "proceso retail" in prod_name or "merma" in prod_name:
                    continue
                pkg_id = pkg[0] if isinstance(pkg, (list, tuple)) else pkg
                package_ids.add(pkg_id)
                key = (prod_id, pkg_id, "salida")
                pallets_by_key.setdefault(key, {"qty": 0})
                pallets_by_key[key]["qty"] += qty

        package_info = {}
        if package_ids:
            package_fields = ["id", "name", "pack_date"]
            fallback_package_fields = ["id", "name"]
            try:
                packages = self.odoo.read(
                    "stock.quant.package",
                    list(package_ids),
                    package_fields
                )
            except Exception as e:
                print(f"Error fetching packages with extra fields: {e}")
                packages = self.odoo.read(
                    "stock.quant.package",
                    list(package_ids),
                    fallback_package_fields
                )
            package_info = {pkg["id"]: pkg for pkg in packages}

        quants_by_package = {}
        if package_ids:
            quant_fields = ["package_id", "name", "lot_id", "quantity", "product_id"]
            fallback_quant_fields = ["package_id", "lot_id", "quantity", "product_id"]
            try:
                quants = self.odoo.search_read(
                    "stock.quant",
                    [["package_id", "in", list(package_ids)]],
                    quant_fields
                )
            except Exception as e:
                print(f"Error fetching quants with extra fields: {e}")
                quants = self.odoo.search_read(
                    "stock.quant",
                    [["package_id", "in", list(package_ids)]],
                    fallback_quant_fields
                )
            for quant in quants:
                pkg = quant.get("package_id")
                pkg_id = pkg[0] if isinstance(pkg, (list, tuple)) else pkg
                quants_by_package.setdefault(pkg_id, []).append(quant)

        for (prod_id, pkg_id, tipo), data in pallets_by_key.items():
            pkg_info = package_info.get(pkg_id, {})
            pallet = {
                "id": pkg_id,
                "name": pkg_info.get("name", str(pkg_id)),
                "pack_date": pkg_info.get("pack_date", ""),
                "qty": data.get("qty", 0),
                "products": build_pallet_products(quants_by_package.get(pkg_id, []))
            }
            pallets_by_production[prod_id][tipo].append(pallet)

        return {
            "productions": production_details,
            "pallets": pallets_by_production
        }

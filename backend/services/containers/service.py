"""
Servicio para gestión de Pedidos de Venta y su seguimiento de producción
OPTIMIZADO: Parte desde fabricaciones con PO asociada para evitar consultas lentas

REFACTORIZADO: Constantes, helpers y Sankey extraídos a módulos separados.
"""
from typing import List, Dict, Optional
from shared.odoo_client import OdooClient
from backend.utils import clean_record, get_name_from_relation, get_state_display
from backend.services.currency_service import CurrencyService

from .constants import get_state_display as local_get_state_display
from .helpers import (
    build_pallet_products, 
    build_container_detail, 
    build_fabrication_detail,
    build_pallet_detail
)


class ContainersService:
    """Servicio para operaciones de Pedidos de Venta y seguimiento de fabricación"""

    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
    
    def _convert_to_clp(self, amount: float, currency_id: any) -> float:
        """
        Convierte el monto a CLP si está en USD.
        
        Args:
            amount: Monto a convertir
            currency_id: Puede ser tuple (id, name) o dict con 'name'
            
        Returns:
            float: Monto en CLP
        """
        if not amount:
            return 0.0
        
        # Obtener nombre de la moneda
        currency_name = ""
        if isinstance(currency_id, (list, tuple)) and len(currency_id) > 1:
            currency_name = currency_id[1]
        elif isinstance(currency_id, dict):
            currency_name = currency_id.get("name", "")
        
        # Si es USD, convertir a CLP
        if currency_name and "USD" in currency_name.upper():
            return CurrencyService.convert_usd_to_clp(amount)
        
        # Si es CLP o cualquier otra, retornar el monto original
        return amount

    def get_containers(self, 
                       start_date: Optional[str] = None, 
                       end_date: Optional[str] = None,
                       partner_id: Optional[int] = None,
                       state: Optional[str] = None) -> List[Dict]:
        """
        Obtiene lista de pedidos de venta con su avance de producción.
        OPTIMIZADO: Busca desde fabricaciones que tienen x_studio_po_asociada
        """
        # PASO 1: Buscar TODAS las fabricaciones que tienen una PO asociada
        prod_domain = [("x_studio_po_asociada", "!=", False)]
        if start_date:
            prod_domain.append(("date_planned_start", ">=", start_date))
        if end_date:
            prod_domain.append(("date_planned_start", "<=", end_date))
        
        prod_fields = [
            "name", "product_id", "product_qty", "qty_produced",
            "state", "date_planned_start", "date_start", "date_finished",
            "user_id", "x_studio_po_asociada", "x_studio_po_cliente_1",
            "x_studio_kg_totales_po", "x_studio_kg_consumidos_po",
            "x_studio_kg_disponibles_po", "x_studio_sala_de_proceso",
            "x_studio_clientes"
        ]
        fallback_prod_fields = [
            "name", "product_id", "product_qty", "qty_produced",
            "state", "date_planned_start", "date_start", "date_finished",
            "user_id", "x_studio_po_asociada", "x_studio_po_cliente_1",
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
            
            print(f"[CONTAINERS] Domain: {prod_domain}")
            print(f"[CONTAINERS] Found {len(prod_ids)} productions with PO asociada")
            
            if not prod_ids:
                print("[CONTAINERS] No productions found, returning empty list")
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
        sales_map = {}  # sale_name -> {info, productions: []}
        sale_names_to_fetch = set()
        
        for p in prods_raw:
            po_asociada = p.get("x_studio_po_asociada")
            if not po_asociada:
                continue
            
            # x_studio_po_asociada contiene el NAME del sale.order (ej: "S00830"), no el ID
            sale_name = po_asociada.strip() if isinstance(po_asociada, str) else str(po_asociada)
            if not sale_name:
                continue
                
            sale_names_to_fetch.add(sale_name)
            
            if sale_name not in sales_map:
                sales_map[sale_name] = {
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
            
            sales_map[sale_name]["productions"].append({
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
            
            sales_map[sale_name]["kg_producidos_total"] += qty_produced
        
        if not sale_names_to_fetch:
            return []
        
        # PASO 3: Obtener datos de las ventas (sale.order) en UNA sola llamada
        sale_fields = [
            "name", "partner_id", "date_order", "commitment_date",
            "state", "amount_total", "currency_id", "origin",
            "user_id", "order_line", "validity_date"
        ]
        fallback_sale_fields = [
            "name", "partner_id", "date_order", "commitment_date",
            "state", "amount_total", "currency_id", "origin",
            "user_id", "order_line"
        ]
        
        sale_domain = [("name", "in", list(sale_names_to_fetch))]
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
            sale_name = sale.get("name", "")
            
            # Obtener partner name ANTES de clean_record
            partner = sale.get("partner_id")
            partner_name = partner[1] if partner and isinstance(partner, (list, tuple)) and len(partner) > 1 else "N/A"
            
            sale_clean = clean_record(sale)
            
            # Líneas de este pedido
            lines_data = lines_map.get(sale_id, [])
            
            # KG totales del pedido (suma de líneas)
            kg_total = sum([l.get("product_uom_qty", 0) or 0 for l in lines_data])
            
            # KG por producto (agrupado)
            kg_por_producto = {}
            for line in lines_data:
                prod = line.get("product_id", {})
                prod_name = prod.get("name", "N/A") if isinstance(prod, dict) else "N/A"
                kg = line.get("product_uom_qty", 0) or 0
                if prod_name in kg_por_producto:
                    kg_por_producto[prod_name] += kg
                else:
                    kg_por_producto[prod_name] = kg
            
            # Producciones y KG producidos - BUSCAR POR NAME no por ID
            sale_info = sales_map.get(sale_name, {"productions": [], "kg_producidos_total": 0})
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
            
            # partner_id es el cliente en sale.order
            client_name = partner_name
            
            # Convertir monto a CLP si es necesario
            currency_id = sale_clean.get("currency_id", {})
            amount_original = sale_clean.get("amount_total", 0)
            amount_clp = self._convert_to_clp(amount_original, currency_id)

            containers.append({
                "id": sale_id,
                "name": sale_clean.get("name", ""),
                "partner_id": sale_clean.get("partner_id", {}),
                "partner_name": partner_name,
                "client_name": client_name,
                "date_order": sale_clean.get("date_order", ""),
                "commitment_date": sale_clean.get("commitment_date", ""),
                "validity_date": sale_clean.get("validity_date", ""),
                "state": sale_clean.get("state", ""),
                "origin": sale_clean.get("origin", ""),
                "currency_id": currency_id,
                "amount_total": amount_clp,  # Monto convertido a CLP
                "amount_original": amount_original,  # Monto original
                "user_id": sale_clean.get("user_id", {}),
                "producto_principal": producto_principal,
                "kg_total": kg_total,
                "kg_producidos": kg_producidos,
                "kg_disponibles": kg_disponibles,
                "kg_por_producto": kg_por_producto,
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
        # Primero buscar el sale.order por ID para obtener su nombre
        try:
            sale_data = self.odoo.read("sale.order", [sale_id], ["name"])
            if not sale_data:
                return {}
            sale_name = sale_data[0].get("name", "")
        except Exception as e:
            print(f"Error getting sale.order name: {e}")
            return {}
        
        prod_domain = [("x_studio_po_asociada", "=", sale_name)]
        
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
        
        # Convertir monto a CLP si es necesario
        currency_id = sale_clean.get("currency_id", {})
        amount_original = sale_clean.get("amount_total", 0)
        amount_clp = self._convert_to_clp(amount_original, currency_id)
        
        return {
            "id": sale_id,
            "name": sale_clean.get("name", ""),
            "partner_name": partner_name,
            "date_order": sale_clean.get("date_order", ""),
            "commitment_date": sale_clean.get("commitment_date", ""),
            "state": sale_clean.get("state", ""),
            "origin": sale_clean.get("origin", ""),
            "currency_id": currency_id,
            "amount_total": amount_clp,  # Monto convertido a CLP
            "amount_original": amount_original,  # Monto original
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
            prod_domain = [("x_studio_po_asociada", "!=", False)]
            prod_ids = self.odoo.search("mrp.production", prod_domain, limit=500)
            
            if not prod_ids:
                return []
            
            prods = self.odoo.read("mrp.production", prod_ids, ["x_studio_po_asociada"])
            
            # x_studio_po_asociada contiene nombres (strings), no IDs
            sale_names = list(set([
                p["x_studio_po_asociada"].strip()
                for p in prods 
                if p.get("x_studio_po_asociada") and isinstance(p.get("x_studio_po_asociada"), str) and p.get("x_studio_po_asociada").strip()
            ]))
            
            if not sale_names:
                return []
            
            # Buscar sale.order por nombre
            sale_ids = self.odoo.search("sale.order", [("name", "in", sale_names)])
            
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
        """Obtiene resumen global de pedidos de venta para KPIs"""
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
                       end_date: Optional[str] = None) -> Dict:
        """
        Genera datos para diagrama Sankey de trazabilidad completa.
        
        Construye un GRAFO de relaciones entre paquetes:
        1. Por registro: package_id → result_package_id (mismo registro)
        2. Por continuidad: result_package de A = package de B (pallet atraviesa procesos)
        3. Por lote: registros con mismo lot_id están relacionados
        
        Identifica ventas: movimientos hacia Partner/Vendors (ID 4)
        """
        print(f"Generando Sankey data con trazabilidad completa...")
        
        PARTNER_VENDORS_LOCATION_ID = 4
        
        # Paso 1: Buscar TODOS los movimientos con paquetes
        domain = [
            "|",
            ("package_id", "!=", False),
            ("result_package_id", "!=", False),
            ("qty_done", ">", 0),
            ("state", "=", "done"),
        ]
        if start_date:
            domain.append(("date", ">=", start_date))
        if end_date:
            domain.append(("date", "<=", end_date))

        fields = [
            "id", "reference", "package_id", "result_package_id",
            "lot_id", "qty_done", "product_id", "location_id", 
            "location_dest_id", "date", "picking_id"
        ]
        
        try:
            move_lines = self.odoo.search_read(
                "stock.move.line",
                domain,
                fields,
                limit=10000,
                order="date asc"
            )
        except Exception as e:
            print(f"Error fetching move lines: {e}")
            return {"nodes": [], "links": []}
        
        if not move_lines:
            print("No se encontraron movimientos")
            return {"nodes": [], "links": []}
        
        print(f"Encontrados {len(move_lines)} movimientos")
        
        # Paso 2: Construir estructuras de datos
        # Mapas para resolver nombres
        all_packages = {}  # pkg_id -> {name, qty_total, products}
        all_lots = {}      # lot_id -> {name, packages: set()}
        
        # Grafo de relaciones
        # edges: (from_pkg, to_pkg, reference, lot_id, qty)
        edges = []
        
        # Paquetes que van a ventas
        sale_packages = {}  # pkg_id -> {customer_id, customer_name, picking_id}
        sale_picking_ids = set()
        
        for ml in move_lines:
            pkg_rel = ml.get("package_id")
            result_rel = ml.get("result_package_id")
            lot_rel = ml.get("lot_id")
            ref = ml.get("reference") or "Sin Ref"
            qty = ml.get("qty_done", 0) or 0
            
            loc_dest = ml.get("location_dest_id")
            loc_dest_id = loc_dest[0] if isinstance(loc_dest, (list, tuple)) else loc_dest
            
            prod_rel = ml.get("product_id")
            prod_name = prod_rel[1] if isinstance(prod_rel, (list, tuple)) and len(prod_rel) > 1 else "N/A"
            
            # Extraer IDs y nombres
            pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
            pkg_name = pkg_rel[1] if isinstance(pkg_rel, (list, tuple)) and len(pkg_rel) > 1 else None
            
            result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
            result_name = result_rel[1] if isinstance(result_rel, (list, tuple)) and len(result_rel) > 1 else None
            
            lot_id = lot_rel[0] if isinstance(lot_rel, (list, tuple)) else lot_rel
            lot_name = lot_rel[1] if isinstance(lot_rel, (list, tuple)) and len(lot_rel) > 1 else None
            
            # Registrar paquetes
            if pkg_id:
                if pkg_id not in all_packages:
                    all_packages[pkg_id] = {"name": pkg_name or str(pkg_id), "qty": 0, "products": {}}
                all_packages[pkg_id]["qty"] += qty
                if prod_name not in all_packages[pkg_id]["products"]:
                    all_packages[pkg_id]["products"][prod_name] = 0
                all_packages[pkg_id]["products"][prod_name] += qty
            
            if result_id:
                if result_id not in all_packages:
                    all_packages[result_id] = {"name": result_name or str(result_id), "qty": 0, "products": {}}
                all_packages[result_id]["qty"] += qty
                if prod_name not in all_packages[result_id]["products"]:
                    all_packages[result_id]["products"][prod_name] = 0
                all_packages[result_id]["products"][prod_name] += qty
            
            # Registrar lote y sus paquetes
            if lot_id:
                if lot_id not in all_lots:
                    all_lots[lot_id] = {"name": lot_name or str(lot_id), "packages": set()}
                if pkg_id:
                    all_lots[lot_id]["packages"].add(pkg_id)
                if result_id:
                    all_lots[lot_id]["packages"].add(result_id)
            
            # Crear arista directa: package -> result (si ambos existen)
            if pkg_id and result_id:
                edges.append({
                    "from": pkg_id,
                    "to": result_id,
                    "reference": ref,
                    "lot_id": lot_id,
                    "qty": qty
                })
            
            # Detectar ventas (destino Partner/Vendors)
            if loc_dest_id == PARTNER_VENDORS_LOCATION_ID:
                target_pkg = result_id or pkg_id
                if target_pkg:
                    picking_rel = ml.get("picking_id")
                    picking_id = picking_rel[0] if isinstance(picking_rel, (list, tuple)) else picking_rel
                    sale_packages[target_pkg] = {"picking_id": picking_id}
                    if picking_id:
                        sale_picking_ids.add(picking_id)
        
        print(f"Paquetes: {len(all_packages)}, Lotes: {len(all_lots)}, Aristas directas: {len(edges)}, Ventas: {len(sale_packages)}")
        
        # Paso 3: Resolver clientes de ventas
        if sale_picking_ids:
            try:
                pickings = self.odoo.read(
                    "stock.picking",
                    list(sale_picking_ids),
                    ["id", "partner_id", "origin"]
                )
                pickings_by_id = {p["id"]: p for p in pickings}
                
                for pkg_id, sale_data in sale_packages.items():
                    picking = pickings_by_id.get(sale_data.get("picking_id"), {})
                    partner_rel = picking.get("partner_id")
                    if partner_rel:
                        sale_packages[pkg_id]["customer_id"] = partner_rel[0] if isinstance(partner_rel, (list, tuple)) else partner_rel
                        sale_packages[pkg_id]["customer_name"] = partner_rel[1] if isinstance(partner_rel, (list, tuple)) and len(partner_rel) > 1 else "Cliente"
                    sale_packages[pkg_id]["origin"] = picking.get("origin", "")
            except Exception as e:
                print(f"Error fetching picking partners: {e}")
        
        # Paso 4: Construir grafo de conectividad
        # Crear aristas adicionales por continuidad de pallet
        # Si result_package de un registro = package de otro, ya están conectados por edges
        # Pero necesitamos encontrar cadenas transitivas
        
        # Grafo: pkg_id -> set of (to_pkg, reference)
        graph_out = {}  # pkg -> [(to_pkg, ref, qty)]
        graph_in = {}   # pkg -> [(from_pkg, ref, qty)]
        
        for edge in edges:
            from_pkg = edge["from"]
            to_pkg = edge["to"]
            ref = edge["reference"]
            qty = edge["qty"]
            
            if from_pkg not in graph_out:
                graph_out[from_pkg] = []
            graph_out[from_pkg].append((to_pkg, ref, qty))
            
            if to_pkg not in graph_in:
                graph_in[to_pkg] = []
            graph_in[to_pkg].append((from_pkg, ref, qty))
        
        # Paso 5: Clasificar paquetes
        # ORIGEN: aparece en graph_out pero no en graph_in (nunca fue creado, es entrada inicial)
        # DESTINO: aparece en graph_in pero no en graph_out (no genera nada más)
        # INTERMEDIO: aparece en ambos
        
        all_pkg_ids = set(all_packages.keys())
        pkg_origins = set()  # Paquetes que son origen (no fueron creados por ningún proceso)
        pkg_destinations = set()  # Paquetes que son destino final
        pkg_intermediates = set()  # Paquetes intermedios
        
        for pkg_id in all_pkg_ids:
            has_input = pkg_id in graph_in  # Alguien lo creó
            has_output = pkg_id in graph_out  # Él crea algo
            
            if has_output and not has_input:
                pkg_origins.add(pkg_id)
            elif has_input and not has_output:
                pkg_destinations.add(pkg_id)
            elif has_input and has_output:
                pkg_intermediates.add(pkg_id)
        
        print(f"Clasificación: {len(pkg_origins)} orígenes, {len(pkg_intermediates)} intermedios, {len(pkg_destinations)} destinos")
        
        # Paso 6: Construir nodos y links para Sankey
        nodes = []
        links = []
        node_index = {}
        
        def _get_node_idx(node_id: str, label: str, color: str, detail: dict) -> int:
            if node_id not in node_index:
                node_index[node_id] = len(nodes)
                nodes.append({
                    "label": label,
                    "color": color,
                    "detail": detail,
                    "x": None,
                    "y": None
                })
            return node_index[node_id]
        
        # Limitar cantidad para visualización (tomar cadenas más largas)
        # Encontrar paquetes origen que tienen cadenas largas
        def _chain_length(pkg_id: int, visited: set = None) -> int:
            if visited is None:
                visited = set()
            if pkg_id in visited:
                return 0
            visited.add(pkg_id)
            max_depth = 0
            for to_pkg, _, _ in graph_out.get(pkg_id, []):
                depth = _chain_length(to_pkg, visited.copy())
                max_depth = max(max_depth, depth)
            return 1 + max_depth
        
        # Calcular profundidad de cada origen
        origin_depths = [(pkg, _chain_length(pkg)) for pkg in pkg_origins]
        origin_depths.sort(key=lambda x: x[1], reverse=True)
        
        # Tomar los orígenes con cadenas más interesantes (depth > 1)
        selected_origins = [pkg for pkg, depth in origin_depths if depth > 1][:30]
        
        if not selected_origins:
            # Si no hay cadenas largas, tomar algunos orígenes cualquiera
            selected_origins = list(pkg_origins)[:30]
        
        print(f"Seleccionados {len(selected_origins)} orígenes para visualización")
        
        # Recorrer el grafo desde los orígenes seleccionados
        visited_edges = set()
        visited_pkgs = set()
        
        def _traverse(pkg_id: int, depth: int = 0):
            if depth > 10:  # Límite de profundidad
                return
            if pkg_id in visited_pkgs and depth > 0:
                return
            visited_pkgs.add(pkg_id)
            
            pkg_data = all_packages.get(pkg_id, {})
            pkg_name = pkg_data.get("name", str(pkg_id))
            products_str = ", ".join([f"{p}: {q:.0f}kg" for p, q in pkg_data.get("products", {}).items()])
            
            # Determinar color según clasificación
            if pkg_id in pkg_origins:
                color = "#f39c12"  # Naranja - origen
                prefix = "🟠 "
            elif pkg_id in pkg_destinations:
                color = "#2ecc71"  # Verde - destino
                prefix = "🟢 "
            else:
                color = "#9b59b6"  # Morado - intermedio
                prefix = "🟣 "
            
            node_idx = _get_node_idx(
                f"PKG:{pkg_id}",
                f"{prefix}{pkg_name}",
                color,
                {"package_id": pkg_id, "name": pkg_name, "products": products_str}
            )
            
            # Recorrer salidas
            for to_pkg, ref, qty in graph_out.get(pkg_id, []):
                edge_key = (pkg_id, to_pkg, ref)
                if edge_key in visited_edges:
                    continue
                visited_edges.add(edge_key)
                
                # Crear nodo del proceso/referencia
                ref_node_id = f"REF:{ref}"
                ref_idx = _get_node_idx(
                    ref_node_id,
                    ref,
                    "#e74c3c",  # Rojo - proceso
                    {"reference": ref}
                )
                
                # Link: paquete origen -> proceso
                links.append({
                    "source": node_idx,
                    "target": ref_idx,
                    "value": max(1, qty),
                    "color": "rgba(243, 156, 18, 0.4)"  # Naranja transparente
                })
                
                # Recursión al paquete destino
                _traverse(to_pkg, depth + 1)
                
                to_idx = node_index.get(f"PKG:{to_pkg}")
                if to_idx is not None:
                    # Link: proceso -> paquete destino
                    links.append({
                        "source": ref_idx,
                        "target": to_idx,
                        "value": max(1, qty),
                        "color": "rgba(46, 204, 113, 0.4)"  # Verde transparente
                    })
            
            # Si es paquete de venta, conectar a cliente
            if pkg_id in sale_packages:
                sale_data = sale_packages[pkg_id]
                customer_id = sale_data.get("customer_id")
                customer_name = sale_data.get("customer_name", "Cliente")
                
                if customer_id:
                    cust_idx = _get_node_idx(
                        f"CUST:{customer_id}",
                        f"🔵 {customer_name}",
                        "#3498db",  # Azul - cliente
                        {"customer_id": customer_id, "name": customer_name}
                    )
                    
                    links.append({
                        "source": node_idx,
                        "target": cust_idx,
                        "value": max(1, pkg_data.get("qty", 1)),
                        "color": "rgba(52, 152, 219, 0.4)"  # Azul transparente
                    })
        
        # Recorrer desde cada origen seleccionado
        for origin_pkg in selected_origins:
            _traverse(origin_pkg)
        
        print(f"Generados {len(nodes)} nodos y {len(links)} links")
        
        # Paso 7: Calcular posiciones X por profundidad (BFS desde orígenes)
        if nodes:
            pkg_depths = {}
            ref_depths = {}
            cust_depth = 0
            
            # BFS para calcular profundidad
            from collections import deque
            queue = deque()
            
            for origin_pkg in selected_origins:
                node_id = f"PKG:{origin_pkg}"
                if node_id in node_index:
                    queue.append((node_id, 0))
                    pkg_depths[node_id] = 0
            
            while queue:
                current, depth = queue.popleft()
                current_idx = node_index.get(current)
                if current_idx is None:
                    continue
                
                # Encontrar links que salen de este nodo
                for link in links:
                    if link["source"] == current_idx:
                        target_idx = link["target"]
                        target_id = None
                        for nid, idx in node_index.items():
                            if idx == target_idx:
                                target_id = nid
                                break
                        
                        if target_id:
                            new_depth = depth + 1
                            if target_id.startswith("REF:"):
                                if target_id not in ref_depths or ref_depths[target_id] < new_depth:
                                    ref_depths[target_id] = new_depth
                                    queue.append((target_id, new_depth))
                            elif target_id.startswith("PKG:"):
                                if target_id not in pkg_depths or pkg_depths[target_id] < new_depth:
                                    pkg_depths[target_id] = new_depth
                                    queue.append((target_id, new_depth))
                            elif target_id.startswith("CUST:"):
                                cust_depth = max(cust_depth, new_depth)
            
            # Calcular max_depth
            all_depths = list(pkg_depths.values()) + list(ref_depths.values()) + ([cust_depth] if cust_depth else [])
            max_depth = max(all_depths) if all_depths else 1
            
            # Agrupar nodos por profundidad para asignar Y
            depth_groups = {}
            for node_id, depth in {**pkg_depths, **ref_depths}.items():
                if depth not in depth_groups:
                    depth_groups[depth] = []
                depth_groups[depth].append(node_id)
            
            # Asignar posiciones
            for depth, node_ids in depth_groups.items():
                x = 0.05 + (depth / max(max_depth, 1)) * 0.85
                n = len(node_ids)
                for i, node_id in enumerate(node_ids):
                    y = 0.05 + (i / max(n - 1, 1)) * 0.9 if n > 1 else 0.5
                    idx = node_index.get(node_id)
                    if idx is not None:
                        nodes[idx]["x"] = x
                        nodes[idx]["y"] = y
            
            # Posicionar clientes a la derecha
            cust_nodes = [nid for nid in node_index if nid.startswith("CUST:")]
            for i, cust_id in enumerate(cust_nodes):
                idx = node_index.get(cust_id)
                if idx is not None:
                    nodes[idx]["x"] = 0.95
                    n = len(cust_nodes)
                    nodes[idx]["y"] = 0.05 + (i / max(n - 1, 1)) * 0.9 if n > 1 else 0.5
        
        return {"nodes": nodes, "links": links}
    
    def _get_virtual_location_ids(self) -> set:
        """Obtiene IDs de ubicaciones virtuales/producción."""
        # IDs conocidos de ubicaciones virtuales
        known_virtual_ids = {8485, 15}  # Virtual Locations/Ubicación Congelado, Virtual Locations/Ubicación Procesos
        
        try:
            # Buscar ubicaciones de tipo producción
            virtual_locations = self.odoo.search_read(
                "stock.location",
                [("usage", "=", "production")],
                ["id"],
                limit=100
            )
            for loc in virtual_locations:
                known_virtual_ids.add(loc["id"])
        except Exception as e:
            print(f"Error fetching virtual locations: {e}")
        
        return known_virtual_ids



    def _get_container_refs_by_out_package_ids(self, package_ids: List[int], containers: List[Dict]) -> Dict[int, Dict]:
        """Resuelve package_id (pallet OUT) -> {container_id?, origin?} usando pickings outgoing.

        Regla práctica:
        - Considera SOLO pickings `outgoing` (despachos).
        - Si `origin` coincide con un container ya cargado: retorna container_id.
        - Si `origin` existe pero no está en los containers cargados: retorna origin (container virtual por nombre).
        - Si no hay origin/picking usable: el pallet se considera huérfano.
        """
        package_ids = [pid for pid in (package_ids or []) if pid]
        if not package_ids:
            return {}

        container_name_to_id: Dict[str, int] = {}
        for c in containers or []:
            name = c.get("name")
            cid = c.get("id")
            if name and cid:
                container_name_to_id[str(name)] = int(cid)

        # Resultado por defecto: huérfano
        result: Dict[int, Dict] = {pid: {"container_id": None, "origin": None} for pid in package_ids}

        try:
            move_lines = self.odoo.search_read(
                "stock.move.line",
                [
                    ("result_package_id", "in", package_ids),
                    ("picking_id", "!=", False),
                    ("picking_id.picking_type_code", "=", "outgoing"),
                    ("picking_id.state", "in", ["done", "assigned"]),
                ],
                ["result_package_id", "picking_id", "date"],
                limit=5000,
                order="date desc"
            )
        except Exception as e:
            print(f"Error fetching move lines for OUT packages: {e}")
            return result

        picking_ids: List[int] = []
        for ml in move_lines or []:
            picking_rel = ml.get("picking_id")
            if picking_rel:
                picking_ids.append(picking_rel[0] if isinstance(picking_rel, (list, tuple)) else picking_rel)
        picking_ids = list({pid for pid in picking_ids if pid})

        pickings_by_id: Dict[int, Dict] = {}
        if picking_ids:
            try:
                pickings = self.odoo.read("stock.picking", picking_ids, ["id", "origin", "state", "picking_type_code"])
                pickings_by_id = {p.get("id"): p for p in (pickings or []) if p.get("id")}
            except Exception as e:
                print(f"Error fetching pickings for OUT packages: {e}")

        # move_lines ya vienen ordenados desc: tomar el primer match por package
        for ml in move_lines or []:
            pkg_rel = ml.get("result_package_id")
            pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) and pkg_rel else None
            if not pkg_id or result.get(pkg_id, {}).get("origin") is not None or result.get(pkg_id, {}).get("container_id") is not None:
                continue

            picking_rel = ml.get("picking_id")
            picking_id = picking_rel[0] if isinstance(picking_rel, (list, tuple)) and picking_rel else None
            picking = pickings_by_id.get(picking_id, {})
            origin = (picking.get("origin") or "").strip()
            if not origin:
                continue
            if origin in container_name_to_id:
                result[pkg_id] = {"container_id": container_name_to_id[origin], "origin": origin}
            else:
                # container no estaba precargado: devolver solo el nombre para crear un nodo virtual
                result[pkg_id] = {"container_id": None, "origin": origin}

        return result

    def get_sankey_producers(self,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             limit: int = 50,
                             partner_id: Optional[int] = None) -> List[Dict]:
        """Lista productores disponibles (desde pallets IN) para un rango/cliente."""
        containers = self.get_containers(start_date, end_date, partner_id=partner_id)[:limit]

        production_ids: List[int] = []
        for container in containers:
            for fab in container.get("productions", []) or []:
                if (fab.get("name") or "").startswith("VLK"):
                    continue
                if fab.get("id"):
                    production_ids.append(fab["id"])

        # Regla: SOLO fabricaciones con container asociado (sin orphans)

        production_ids = list({pid for pid in production_ids if pid})
        ctx = self._get_sankey_context(production_ids, include_producers=True)
        pallets_by_production = ctx.get("pallets", {})

        producers_map: Dict[int, str] = {}
        for pdata in pallets_by_production.values():
            for p in (pdata.get("consumidos", []) or []):
                for prod in (p.get("producers") or []):
                    pid = prod.get("id")
                    name = prod.get("name")
                    if pid and name:
                        producers_map[pid] = name

        return [{"id": pid, "name": producers_map[pid]} for pid in sorted(producers_map.keys(), key=lambda k: producers_map[k])]
    
    def _get_sankey_context(self, production_ids: List[int], include_producers: bool = False) -> Dict:
        """Obtiene contexto de producciones y pallets para Sankey."""
        production_ids = [pid for pid in (production_ids or []) if pid]

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

            # Componentes (inputs): SOLO raw moves, agrupados por producto
            componentes_by_product: Dict[str, Dict] = {}
            x_studio_total_componentes = 0
            for move_id in move_ids_by_type.get("raw_ids", []) or []:
                move = moves_by_id.get(move_id)
                if not move:
                    continue
                product_name = get_name_from_relation(move.get("product_id"))
                quantity_done = move.get("quantity_done", 0) or 0
                x_studio_value = move.get("x_studio_float_field_hZJh1", 0) or 0
                rec = componentes_by_product.setdefault(
                    product_name,
                    {
                        "product": product_name,
                        "quantity_done": 0,
                        "x_studio_float_field_hZJh1": 0,
                    },
                )
                rec["quantity_done"] += quantity_done
                rec["x_studio_float_field_hZJh1"] += x_studio_value
                x_studio_total_componentes += x_studio_value

            componentes = list(componentes_by_product.values())
            componentes.sort(key=lambda x: x.get("quantity_done", 0) or 0, reverse=True)

            # Subproductos (outputs): SOLO finished moves, agrupados por producto
            sub_by_product: Dict[str, Dict] = {}
            sub_total_qty = 0
            sub_total_done = 0
            for move_id in move_ids_by_type.get("finished_ids", []) or []:
                move = moves_by_id.get(move_id)
                if not move:
                    continue
                product_name = get_name_from_relation(move.get("product_id"))
                pname_l = (product_name or "").lower()
                # Evitar "subproductos" que en realidad son productos de proceso o merma
                if "proceso" in pname_l or "merma" in pname_l:
                    continue
                quantity_done = move.get("quantity_done", 0) or 0
                product_uom_qty = move.get("product_uom_qty", 0) or 0

                rec = sub_by_product.setdefault(
                    product_name,
                    {
                        "product": product_name,
                        "product_uom_qty": 0,
                        "quantity_done": 0,
                    },
                )
                rec["product_uom_qty"] += product_uom_qty
                rec["quantity_done"] += quantity_done
                sub_total_qty += product_uom_qty
                sub_total_done += quantity_done

            subproductos = list(sub_by_product.values())
            subproductos.sort(key=lambda x: x.get("quantity_done", 0) or 0, reverse=True)

            production_details[prod_id] = {
                "componentes": componentes,
                "subproductos": subproductos,
                "x_studio_total": x_studio_total_componentes,
                "subproducts_totals": {
                    "product_uom_qty": sub_total_qty,
                    "quantity_done": sub_total_done,
                },
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

        lot_to_producer = {}
        if include_producers:
            # Resolver productor por lote (batch) para permitir filtrar pallets IN
            # - Solo lo usamos en pallets consumidos (IN)
            lot_ids: set = set()
            for (_prod_id, pkg_id, tipo), _data in pallets_by_key.items():
                if tipo != "consumidos":
                    continue
                for q in quants_by_package.get(pkg_id, []) or []:
                    lot_rel = q.get("lot_id")
                    lot_id = lot_rel[0] if isinstance(lot_rel, (list, tuple)) and lot_rel else None
                    if lot_id:
                        lot_ids.add(lot_id)

            lot_to_producer = self._get_producers_by_lot_ids(list(lot_ids)) if lot_ids else {}

        for (prod_id, pkg_id, tipo), data in pallets_by_key.items():
            pkg_info = package_info.get(pkg_id, {})
            products = build_pallet_products(quants_by_package.get(pkg_id, []))

            # productores detectados desde los lotes dentro del pallet
            producer_ids = set()
            producers = []
            if include_producers:
                for prod in products:
                    lot_id = prod.get("lot_id")
                    if not lot_id:
                        continue
                    producer = lot_to_producer.get(lot_id)
                    if not producer:
                        continue
                    pid = producer.get("id")
                    pname = producer.get("name")
                    if pid and pid not in producer_ids:
                        producer_ids.add(pid)
                        producers.append({"id": pid, "name": pname})

            pallet = {
                "id": pkg_id,
                "name": pkg_info.get("name", str(pkg_id)),
                "pack_date": pkg_info.get("pack_date", ""),
                "qty": data.get("qty", 0),
                "products": products,
                "producer_ids": sorted(list(producer_ids)),
                "producers": producers,
            }
            pallets_by_production[prod_id][tipo].append(pallet)

        return {
            "productions": production_details,
            "pallets": pallets_by_production
        }

    def _get_producers_by_lot_ids(self, lot_ids: List[int]) -> Dict[int, Dict]:
        """Mapea lot_id -> {id, name} del productor (res.partner) usando recepciones desde ubicación vendor."""
        if not lot_ids:
            return {}

        # Buscar move lines por lote
        try:
            move_lines = self.odoo.search_read(
                "stock.move.line",
                [["lot_id", "in", list(set(lot_ids))]],
                ["lot_id", "picking_id", "location_id", "date"],
                limit=5000,
                order="date asc"
            )
        except Exception as e:
            print(f"Error fetching move lines for lots: {e}")
            return {}

        # Elegir, por lote, el primer movimiento que venga desde vendor/proveedor
        lot_to_picking: Dict[int, int] = {}
        for ml in move_lines or []:
            lot_rel = ml.get("lot_id")
            lot_id = lot_rel[0] if isinstance(lot_rel, (list, tuple)) and lot_rel else None
            if not lot_id or lot_id in lot_to_picking:
                continue
            loc_rel = ml.get("location_id")
            loc_name = loc_rel[1] if isinstance(loc_rel, (list, tuple)) and len(loc_rel) > 1 else str(loc_rel)
            if not loc_name:
                continue
            if "vendor" not in loc_name.lower() and "proveedor" not in loc_name.lower():
                continue
            picking_rel = ml.get("picking_id")
            picking_id = picking_rel[0] if isinstance(picking_rel, (list, tuple)) and picking_rel else None
            if picking_id:
                lot_to_picking[lot_id] = picking_id

        if not lot_to_picking:
            return {}

        # Obtener partner_id de pickings
        picking_ids = list(set(lot_to_picking.values()))
        pickings = self.odoo.read("stock.picking", picking_ids, ["id", "partner_id"])
        picking_to_partner: Dict[int, int] = {}
        partner_ids: set = set()
        for p in pickings or []:
            partner_rel = p.get("partner_id")
            partner_id = partner_rel[0] if isinstance(partner_rel, (list, tuple)) and partner_rel else None
            if partner_id:
                picking_to_partner[p["id"]] = partner_id
                partner_ids.add(partner_id)

        if not partner_ids:
            return {}

        partners = self.odoo.read("res.partner", list(partner_ids), ["id", "name"])
        partner_name = {pp["id"]: pp.get("name", "") for pp in (partners or [])}

        lot_to_producer: Dict[int, Dict] = {}
        for lot_id, picking_id in lot_to_picking.items():
            pid = picking_to_partner.get(picking_id)
            if pid:
                lot_to_producer[lot_id] = {"id": pid, "name": partner_name.get(pid, "")}
        return lot_to_producer

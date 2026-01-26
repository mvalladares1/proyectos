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

    def get_proyecciones(self, 
                        start_date: Optional[str] = None, 
                        end_date: Optional[str] = None,
                        partner_id: Optional[int] = None,
                        state: Optional[str] = None) -> List[Dict]:
        """
        Obtiene pedidos de venta para proyección futura.
        Busca directamente en sale.order por commitment_date, 
        sin requerir que tengan fabricaciones creadas.
        """
        # PASO 1: Buscar sale.order por fecha de compromiso
        sale_domain = []
        
        # Filtrar por fecha de compromiso o fecha de pedido
        if start_date:
            sale_domain.append("|")
            sale_domain.append(("commitment_date", ">=", start_date))
            sale_domain.append(("date_order", ">=", start_date))
        if end_date:
            sale_domain.append("|")
            sale_domain.append(("commitment_date", "<=", end_date))
            sale_domain.append(("date_order", "<=", end_date))
        
        # Filtros opcionales
        if partner_id:
            sale_domain.append(("partner_id", "=", partner_id))
        if state:
            sale_domain.append(("state", "=", state))
        
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
        
        try:
            sale_ids = self.odoo.search(
                "sale.order",
                sale_domain,
                limit=1000,
                order="commitment_date desc, date_order desc"
            )
            
            print(f"[PROYECCIONES] Domain: {sale_domain}")
            print(f"[PROYECCIONES] Found {len(sale_ids)} sale orders")
            
            if not sale_ids:
                return []
            
            try:
                sales_raw = self.odoo.read("sale.order", sale_ids, sale_fields)
            except Exception as e:
                print(f"Error fetching sales with extra fields: {e}")
                sales_raw = self.odoo.read("sale.order", sale_ids, fallback_sale_fields)
        except Exception as e:
            print(f"Error fetching sales for proyecciones: {e}")
            return []
        
        # PASO 2: Obtener líneas de venta
        all_line_ids = []
        for s in sales_raw:
            all_line_ids.extend(s.get("order_line", []))
        
        lines_map = {}
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
        
        # PASO 3: Buscar fabricaciones existentes para estos pedidos (si las hay)
        sale_names = [s.get("name") for s in sales_raw if s.get("name")]
        productions_map = {}  # sale_name -> [productions]
        
        if sale_names:
            try:
                prod_domain = [("x_studio_po_asociada", "in", sale_names)]
                prod_fields = [
                    "name", "product_id", "product_qty", "qty_produced",
                    "state", "date_planned_start", "x_studio_po_asociada"
                ]
                
                prod_ids = self.odoo.search("mrp.production", prod_domain)
                if prod_ids:
                    prods_raw = self.odoo.read("mrp.production", prod_ids, prod_fields)
                    
                    for p in prods_raw:
                        po_asociada = p.get("x_studio_po_asociada", "").strip()
                        if not po_asociada:
                            continue
                        
                        if po_asociada not in productions_map:
                            productions_map[po_asociada] = []
                        
                        product = p.get("product_id")
                        product_name = product[1] if isinstance(product, (list, tuple)) else "N/A"
                        
                        productions_map[po_asociada].append({
                            "id": p["id"],
                            "name": p.get("name", ""),
                            "product_name": product_name,
                            "product_qty": p.get("product_qty", 0) or 0,
                            "qty_produced": p.get("qty_produced", 0) or 0,
                            "state": p.get("state", ""),
                            "state_display": local_get_state_display(p.get("state", "")),
                            "date_planned_start": p.get("date_planned_start", "")
                        })
            except Exception as e:
                print(f"Error fetching productions for proyecciones: {e}")
        
        # PASO 4: Construir resultado
        proyecciones = []
        
        for sale in sales_raw:
            sale_id = sale["id"]
            sale_name = sale.get("name", "")
            
            # Partner name
            partner = sale.get("partner_id")
            partner_name = partner[1] if partner and isinstance(partner, (list, tuple)) and len(partner) > 1 else "N/A"
            
            sale_clean = clean_record(sale)
            
            # Líneas
            lines_data = lines_map.get(sale_id, [])
            
            # KG totales
            kg_total = sum([l.get("product_uom_qty", 0) or 0 for l in lines_data])
            
            # KG por producto
            kg_por_producto = {}
            for line in lines_data:
                prod = line.get("product_id", {})
                prod_name = prod.get("name", "N/A") if isinstance(prod, dict) else "N/A"
                kg = line.get("product_uom_qty", 0) or 0
                if prod_name in kg_por_producto:
                    kg_por_producto[prod_name] += kg
                else:
                    kg_por_producto[prod_name] = kg
            
            # Producciones (si existen)
            productions = productions_map.get(sale_name, [])
            kg_producidos = sum([p.get("qty_produced", 0) for p in productions])
            
            kg_disponibles = kg_total - kg_producidos
            avance_pct = (kg_producidos / kg_total * 100) if kg_total > 0 else 0
            
            # Producto principal
            producto_principal = "N/A"
            if lines_data:
                prod = lines_data[0].get("product_id")
                if isinstance(prod, dict):
                    producto_principal = prod.get("name", "N/A")
            
            # Convertir monto a CLP
            currency_id = sale_clean.get("currency_id", {})
            amount_original = sale_clean.get("amount_total", 0)
            amount_clp = self._convert_to_clp(amount_original, currency_id)
            
            proyecciones.append({
                "id": sale_id,
                "name": sale_clean.get("name", ""),
                "partner_id": sale_clean.get("partner_id", {}),
                "partner_name": partner_name,
                "date_order": sale_clean.get("date_order", ""),
                "commitment_date": sale_clean.get("commitment_date", ""),
                "validity_date": sale_clean.get("validity_date", ""),
                "state": sale_clean.get("state", ""),
                "origin": sale_clean.get("origin", ""),
                "currency_id": currency_id,
                "amount_total": amount_clp,
                "amount_original": amount_original,
                "user_id": sale_clean.get("user_id", {}),
                "producto_principal": producto_principal,
                "kg_total": kg_total,
                "kg_producidos": kg_producidos,
                "kg_disponibles": kg_disponibles,
                "kg_por_producto": kg_por_producto,
                "avance_pct": round(avance_pct, 2),
                "num_fabricaciones": len(productions),
                "lineas": lines_data,  # Cambié de "lines" a "lineas" para consistencia
                "productions": productions
            })
        
        return proyecciones

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
        
        Flujo visual:
        PALLET_A → PROCESO_1 → PALLET_B → PROCESO_2 → PALLET_C → CLIENTE
        
        Lógica simplificada:
        - Cada pallet es un nodo único
        - Cada proceso (reference) es un nodo único
        - Conexiones se derivan directamente de los movimientos
        """
        print(f"Generando Sankey data...")
        
        PARTNER_VENDORS_LOCATION_ID = 4
        VIRTUAL_LOCATION_IDS = self._get_virtual_location_ids()
        
        # Paso 1: Buscar movimientos con paquetes
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
            return {"nodes": [], "links": []}
        
        print(f"Encontrados {len(move_lines)} movimientos")
        
        # Estructuras de datos
        pallets = {}  # pkg_id -> {name, qty, products}
        processes = {}  # ref -> {date, is_reception, supplier_id, supplier_name}
        suppliers = {}  # supplier_id -> name
        customers = {}  # customer_id -> name
        
        # Links: (source_type, source_id, target_type, target_id) -> qty
        link_data = {}
        
        reception_picking_ids = set()
        sale_picking_ids = set()
        sale_pallet_pickings = {}  # pkg_id -> picking_id
        
        for ml in move_lines:
            loc_rel = ml.get("location_id")
            loc_dest_rel = ml.get("location_dest_id")
            loc_id = loc_rel[0] if isinstance(loc_rel, (list, tuple)) else loc_rel
            loc_dest_id = loc_dest_rel[0] if isinstance(loc_dest_rel, (list, tuple)) else loc_dest_rel
            
            pkg_rel = ml.get("package_id")
            result_rel = ml.get("result_package_id")
            ref = ml.get("reference") or "Sin Referencia"
            qty = ml.get("qty_done", 0) or 0
            date = ml.get("date", "")
            
            prod_rel = ml.get("product_id")
            prod_name = prod_rel[1] if isinstance(prod_rel, (list, tuple)) and len(prod_rel) > 1 else "N/A"
            
            pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
            pkg_name = pkg_rel[1] if isinstance(pkg_rel, (list, tuple)) and len(pkg_rel) > 1 else None
            
            result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
            result_name = result_rel[1] if isinstance(result_rel, (list, tuple)) and len(result_rel) > 1 else None
            
            picking_rel = ml.get("picking_id")
            picking_id = picking_rel[0] if isinstance(picking_rel, (list, tuple)) else picking_rel
            
            # Helper para registrar pallet
            def register_pallet(pid, pname, pqty, product):
                if pid not in pallets:
                    pallets[pid] = {"name": pname or str(pid), "qty": 0, "products": {}}
                pallets[pid]["qty"] += pqty
                if product not in pallets[pid]["products"]:
                    pallets[pid]["products"][product] = 0
                pallets[pid]["products"][product] += pqty
            
            # Helper para agregar link
            def add_link(st, sid, tt, tid, q):
                key = (st, sid, tt, tid)
                if key not in link_data:
                    link_data[key] = 0
                link_data[key] += q
            
            # Registrar proceso
            if ref not in processes:
                processes[ref] = {"date": date, "is_reception": False, "picking_id": picking_id}
            
            # CASO 1: RECEPCIÓN (viene de proveedor)
            if loc_id == PARTNER_VENDORS_LOCATION_ID:
                target_pkg = result_id or pkg_id
                target_name = result_name or pkg_name
                if target_pkg:
                    register_pallet(target_pkg, target_name, qty, prod_name)
                    processes[ref]["is_reception"] = True
                    processes[ref]["picking_id"] = picking_id
                    reception_picking_ids.add(picking_id)
                    # Link: SUPPLIER → PALLET (se resolverá después)
                    add_link("RECV", ref, "PALLET", target_pkg, qty)
            
            # CASO 2: ENTRADA A PROCESO (pallet → ubicación virtual)
            elif pkg_id and loc_dest_id in VIRTUAL_LOCATION_IDS:
                register_pallet(pkg_id, pkg_name, qty, prod_name)
                # Link: PALLET → PROCESO
                add_link("PALLET", pkg_id, "PROCESS", ref, qty)
            
            # CASO 3: SALIDA DE PROCESO (result_package sale de ubicación virtual)
            if result_id and loc_id in VIRTUAL_LOCATION_IDS:
                register_pallet(result_id, result_name, qty, prod_name)
                # Link: PROCESO → PALLET
                add_link("PROCESS", ref, "PALLET", result_id, qty)
            
            # CASO 4: VENTA (va hacia cliente)
            if loc_dest_id == PARTNER_VENDORS_LOCATION_ID and loc_id != PARTNER_VENDORS_LOCATION_ID:
                target_pkg = result_id or pkg_id
                if target_pkg and picking_id:
                    sale_pallet_pickings[target_pkg] = picking_id
                    sale_picking_ids.add(picking_id)
        
        # Paso 2: Resolver proveedores y clientes
        all_picking_ids = reception_picking_ids | sale_picking_ids
        if all_picking_ids:
            try:
                pickings = self.odoo.read(
                    "stock.picking",
                    list(all_picking_ids),
                    ["id", "partner_id"]
                )
                pickings_by_id = {p["id"]: p for p in pickings}
                
                # Proveedores
                for ref, info in processes.items():
                    if info.get("is_reception") and info.get("picking_id"):
                        picking = pickings_by_id.get(info["picking_id"], {})
                        partner_rel = picking.get("partner_id")
                        if partner_rel:
                            sid = partner_rel[0] if isinstance(partner_rel, (list, tuple)) else partner_rel
                            sname = partner_rel[1] if isinstance(partner_rel, (list, tuple)) and len(partner_rel) > 1 else "Proveedor"
                            suppliers[sid] = sname
                            info["supplier_id"] = sid
                
                # Clientes
                for pkg_id, picking_id in sale_pallet_pickings.items():
                    picking = pickings_by_id.get(picking_id, {})
                    partner_rel = picking.get("partner_id")
                    if partner_rel:
                        cid = partner_rel[0] if isinstance(partner_rel, (list, tuple)) else partner_rel
                        cname = partner_rel[1] if isinstance(partner_rel, (list, tuple)) and len(partner_rel) > 1 else "Cliente"
                        customers[cid] = cname
                        # Link: PALLET → CUSTOMER
                        add_link("PALLET", pkg_id, "CUSTOMER", cid, pallets.get(pkg_id, {}).get("qty", 1))
            except Exception as e:
                print(f"Error fetching pickings: {e}")
        
        # Paso 3: Construir nodos
        nodes = []
        node_index = {}
        
        def add_node(nid, label, color, detail):
            if nid not in node_index:
                node_index[nid] = len(nodes)
                nodes.append({"label": label, "color": color, "detail": detail, "x": None, "y": None})
            return node_index[nid]
        
        # Nodos de proveedores
        for sid, sname in suppliers.items():
            add_node(f"SUPP:{sid}", f"🏭 {sname}", "#9b59b6", {"type": "supplier", "id": sid})
        
        # Nodos de pallets
        for pid, pinfo in pallets.items():
            prods = ", ".join([f"{p}: {q:.0f}kg" for p, q in pinfo["products"].items()])
            add_node(f"PKG:{pid}", f"📦 {pinfo['name']}", "#f39c12", {"type": "pallet", "id": pid, "qty": pinfo["qty"], "products": prods})
        
        # Nodos de procesos (solo los que no son recepciones puras)
        for ref, pinfo in processes.items():
            if not pinfo.get("is_reception"):
                add_node(f"PROC:{ref}", f"🔴 {ref}", "#e74c3c", {"type": "process", "ref": ref, "date": pinfo["date"]})
        
        # Nodos de clientes
        for cid, cname in customers.items():
            add_node(f"CUST:{cid}", f"🔵 {cname}", "#3498db", {"type": "customer", "id": cid})
        
        # Paso 4: Construir links
        links = []
        
        for (st, sid, tt, tid), qty in link_data.items():
            source_nid = None
            target_nid = None
            color = "rgba(200, 200, 200, 0.5)"
            
            if st == "RECV":
                # Recepción: buscar proveedor
                pinfo = processes.get(sid, {})
                supplier_id = pinfo.get("supplier_id")
                if supplier_id:
                    source_nid = f"SUPP:{supplier_id}"
                    color = "rgba(155, 89, 182, 0.5)"
            elif st == "PALLET":
                source_nid = f"PKG:{sid}"
                color = "rgba(243, 156, 18, 0.5)"
            elif st == "PROCESS":
                source_nid = f"PROC:{sid}"
                color = "rgba(46, 204, 113, 0.5)"
            
            if tt == "PALLET":
                target_nid = f"PKG:{tid}"
            elif tt == "PROCESS":
                target_nid = f"PROC:{tid}"
            elif tt == "CUSTOMER":
                target_nid = f"CUST:{tid}"
                color = "rgba(52, 152, 219, 0.5)"
            
            if source_nid and target_nid and source_nid in node_index and target_nid in node_index:
                links.append({
                    "source": node_index[source_nid],
                    "target": node_index[target_nid],
                    "value": qty or 1,
                    "color": color
                })
        
        # Paso 5: Layout simple por capas
        # Capa 0: Proveedores
        # Capa 1: Pallets de recepción  
        # Capa 2-N: Procesos y sus pallets de salida
        # Capa final: Clientes
        
        supp_nodes = [nid for nid in node_index if nid.startswith("SUPP:")]
        cust_nodes = [nid for nid in node_index if nid.startswith("CUST:")]
        proc_nodes = [nid for nid in node_index if nid.startswith("PROC:")]
        pkg_nodes = [nid for nid in node_index if nid.startswith("PKG:")]
        
        def set_pos(nid, x, y):
            if nid in node_index:
                nodes[node_index[nid]]["x"] = x
                nodes[node_index[nid]]["y"] = y
        
        # Proveedores: x=0.05
        for i, nid in enumerate(supp_nodes):
            y = (i + 1) / (len(supp_nodes) + 1)
            set_pos(nid, 0.05, y)
        
        # Clientes: x=0.95
        for i, nid in enumerate(cust_nodes):
            y = (i + 1) / (len(cust_nodes) + 1)
            set_pos(nid, 0.95, y)
        
        # Procesos ordenados por fecha: x entre 0.3 y 0.7
        proc_sorted = sorted(proc_nodes, key=lambda n: processes.get(n.replace("PROC:", ""), {}).get("date", ""))
        for i, nid in enumerate(proc_sorted):
            x = 0.3 + (0.4 * i / max(len(proc_sorted) - 1, 1)) if len(proc_sorted) > 1 else 0.5
            y = (i + 1) / (len(proc_sorted) + 1)
            set_pos(nid, x, y)
        
        # Pallets: posicionar según conexiones
        for nid in pkg_nodes:
            pid = int(nid.replace("PKG:", ""))
            idx = node_index[nid]
            
            # Encontrar nodos conectados
            connected_x = []
            connected_y = []
            is_input = False  # entra a un proceso
            is_output = False  # sale de un proceso
            
            for link in links:
                if link["source"] == idx:
                    target_nid = [k for k, v in node_index.items() if v == link["target"]][0]
                    if target_nid.startswith("PROC:"):
                        is_input = True
                    if nodes[link["target"]]["x"]:
                        connected_x.append(nodes[link["target"]]["x"])
                        connected_y.append(nodes[link["target"]]["y"])
                if link["target"] == idx:
                    source_nid = [k for k, v in node_index.items() if v == link["source"]][0]
                    if source_nid.startswith("PROC:"):
                        is_output = True
                    if nodes[link["source"]]["x"]:
                        connected_x.append(nodes[link["source"]]["x"])
                        connected_y.append(nodes[link["source"]]["y"])
            
            if connected_x:
                avg_x = sum(connected_x) / len(connected_x)
                avg_y = sum(connected_y) / len(connected_y)
                
                # Ajustar x: antes del proceso si es input, después si es output
                if is_input and not is_output:
                    x = avg_x - 0.1
                elif is_output and not is_input:
                    x = avg_x + 0.1
                else:
                    x = avg_x
                
                set_pos(nid, max(0.1, min(0.9, x)), avg_y)
            else:
                set_pos(nid, 0.15, 0.5)
        
        print(f"Generados {len(nodes)} nodos y {len(links)} links")
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
                             limit: int = 100,
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

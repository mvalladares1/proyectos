"""
Auditoría Exhaustiva de Consumo de Insumos - Odoo 16
=====================================================
Script de diagnóstico para analizar problemas de stock negativo,
consumos duplicados y movimientos inconsistentes.

Fecha: 2026-03-10
"""

import xmlrpc.client
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional
import traceback

# ============================================================================
# CONFIGURACIÓN DE CONEXIÓN
# ============================================================================
URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# ============================================================================
# CLASE DE AUDITORÍA
# ============================================================================
class OdooAuditor:
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.common = None
        self.models = None
        self.results = {
            "connection": {},
            "locations": [],
            "rf_insumos_location": None,
            "operation_types": [],
            "products_negative_stock": [],
            "stock_quants": [],
            "stock_moves_analysis": {},
            "mrp_productions": [],
            "manual_moves": [],
            "duplicate_consumptions": [],
            "quant_vs_moves_diff": [],
            "users_operations": {},
            "bom_analysis": [],
            "valuation_analysis": {},
            "config_settings": {},
            "errors": []
        }
    
    def connect(self) -> bool:
        """Establece conexión con Odoo vía XML-RPC"""
        try:
            print("=" * 60)
            print("CONECTANDO A ODOO...")
            print("=" * 60)
            
            self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            
            # Obtener versión
            version = self.common.version()
            print(f"✓ Versión Odoo: {version.get('server_version', 'N/A')}")
            self.results["connection"]["version"] = version
            
            # Autenticar
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            if self.uid:
                print(f"✓ Autenticación exitosa. UID: {self.uid}")
                self.results["connection"]["uid"] = self.uid
                self.results["connection"]["status"] = "connected"
                
                # Conectar a modelos
                self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
                return True
            else:
                print("✗ Error de autenticación")
                self.results["connection"]["status"] = "auth_failed"
                return False
                
        except Exception as e:
            print(f"✗ Error de conexión: {e}")
            self.results["connection"]["status"] = "connection_failed"
            self.results["connection"]["error"] = str(e)
            return False
    
    def execute(self, model: str, method: str, *args, **kwargs):
        """Ejecuta un método en un modelo de Odoo"""
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, list(args), kwargs
        )
    
    def search_read(self, model: str, domain: list = None, fields: list = None, 
                    limit: int = None, order: str = None) -> List[Dict]:
        """Ejecuta search_read en un modelo"""
        domain = domain or []
        options = {}
        if fields:
            options['fields'] = fields
        if limit:
            options['limit'] = limit
        if order:
            options['order'] = order
        return self.execute(model, 'search_read', domain, **options)
    
    def search_count(self, model: str, domain: list = None) -> int:
        """Cuenta registros que cumplen un dominio"""
        domain = domain or []
        return self.execute(model, 'search_count', domain)

    # ========================================================================
    # FASE 1: LEVANTAMIENTO
    # ========================================================================
    
    def analyze_locations(self):
        """Analiza ubicaciones de stock, especialmente RF INSUMOS"""
        print("\n" + "=" * 60)
        print("ANALIZANDO UBICACIONES DE STOCK...")
        print("=" * 60)
        
        try:
            locations = self.search_read(
                'stock.location',
                [('usage', 'in', ['internal', 'production', 'transit', 'inventory'])],
                ['id', 'name', 'complete_name', 'usage', 'company_id', 
                 'location_id', 'active', 'scrap_location']
            )
            
            print(f"✓ {len(locations)} ubicaciones encontradas")
            self.results["locations"] = locations
            
            # Buscar RF INSUMOS
            for loc in locations:
                name_lower = (loc.get('name') or '').lower()
                complete_name = (loc.get('complete_name') or '').lower()
                if 'rf insumos' in name_lower or 'rf insumos' in complete_name:
                    print(f"  → Encontrada ubicación RF INSUMOS: {loc}")
                    self.results["rf_insumos_location"] = loc
                elif 'insumos' in name_lower:
                    print(f"  → Ubicación relacionada: {loc.get('complete_name')}")
            
            # Imprimir ubicaciones internas
            print("\nUbicaciones internas:")
            for loc in locations:
                if loc.get('usage') == 'internal':
                    print(f"  - [{loc['id']}] {loc.get('complete_name', loc.get('name'))}")
                    
        except Exception as e:
            print(f"✗ Error analizando ubicaciones: {e}")
            self.results["errors"].append({"phase": "locations", "error": str(e)})
    
    def analyze_operation_types(self):
        """Analiza tipos de operación (pickings)"""
        print("\n" + "=" * 60)
        print("ANALIZANDO TIPOS DE OPERACIÓN...")
        print("=" * 60)
        
        try:
            picking_types = self.search_read(
                'stock.picking.type',
                [],
                ['id', 'name', 'code', 'warehouse_id', 'default_location_src_id',
                 'default_location_dest_id', 'sequence_code', 'company_id']
            )
            
            print(f"✓ {len(picking_types)} tipos de operación encontrados")
            self.results["operation_types"] = picking_types
            
            for pt in picking_types:
                print(f"  - [{pt['id']}] {pt.get('name')} ({pt.get('code')})")
                
        except Exception as e:
            print(f"✗ Error: {e}")
            self.results["errors"].append({"phase": "operation_types", "error": str(e)})
    
    def analyze_stock_config(self):
        """Analiza configuración de stock (negativos permitidos, etc.)"""
        print("\n" + "=" * 60)
        print("ANALIZANDO CONFIGURACIÓN DE STOCK...")
        print("=" * 60)
        
        try:
            # Verificar si hay config de stock negativo
            # En Odoo, esto puede estar en res.config.settings o ir.config_parameter
            params = self.search_read(
                'ir.config_parameter',
                [('key', 'ilike', 'stock')],
                ['key', 'value']
            )
            
            print("Parámetros de configuración relacionados con stock:")
            for p in params:
                print(f"  - {p['key']}: {p['value']}")
            
            self.results["config_settings"]["ir_params"] = params
            
            # Verificar módulos instalados relacionados
            modules = self.search_read(
                'ir.module.module',
                [('state', '=', 'installed'), 
                 ('name', 'in', ['stock', 'mrp', 'purchase', 'sale_stock', 
                                 'stock_account', 'mrp_account'])],
                ['name', 'state', 'latest_version']
            )
            
            print("\nMódulos relevantes instalados:")
            for m in modules:
                print(f"  - {m['name']} v{m.get('latest_version', 'N/A')}")
            
            self.results["config_settings"]["modules"] = modules
            
        except Exception as e:
            print(f"✗ Error: {e}")
            self.results["errors"].append({"phase": "config", "error": str(e)})
    
    def analyze_product_categories(self):
        """Analiza categorías de productos y su configuración de valoración"""
        print("\n" + "=" * 60)
        print("ANALIZANDO CATEGORÍAS DE PRODUCTOS...")
        print("=" * 60)
        
        try:
            categories = self.search_read(
                'product.category',
                [],
                ['id', 'name', 'complete_name', 'parent_id', 
                 'property_cost_method', 'property_valuation',
                 'property_stock_account_input_categ_id',
                 'property_stock_account_output_categ_id',
                 'property_stock_valuation_account_id']
            )
            
            print(f"✓ {len(categories)} categorías encontradas")
            
            for cat in categories:
                valuation = cat.get('property_valuation', 'N/A')
                cost_method = cat.get('property_cost_method', 'N/A')
                print(f"  - [{cat['id']}] {cat.get('complete_name', cat.get('name'))}")
                print(f"       Valoración: {valuation}, Método costo: {cost_method}")
            
            self.results["config_settings"]["categories"] = categories
            
        except Exception as e:
            print(f"✗ Error: {e}")
            self.results["errors"].append({"phase": "categories", "error": str(e)})

    # ========================================================================
    # FASE 2: DIAGNÓSTICO
    # ========================================================================
    
    def find_negative_stock_products(self):
        """Encuentra productos con stock negativo en quants"""
        print("\n" + "=" * 60)
        print("BUSCANDO PRODUCTOS CON STOCK NEGATIVO...")
        print("=" * 60)
        
        try:
            # Buscar quants con cantidad negativa
            negative_quants = self.search_read(
                'stock.quant',
                [('quantity', '<', 0)],
                ['id', 'product_id', 'location_id', 'quantity', 
                 'reserved_quantity', 'lot_id', 'company_id'],
                order='quantity asc'
            )
            
            print(f"✓ {len(negative_quants)} quants con stock negativo encontrados")
            
            products_negative = {}
            for q in negative_quants:
                prod_id = q['product_id'][0] if q.get('product_id') else None
                prod_name = q['product_id'][1] if q.get('product_id') else 'N/A'
                loc_name = q['location_id'][1] if q.get('location_id') else 'N/A'
                
                if prod_id not in products_negative:
                    products_negative[prod_id] = {
                        'product_id': prod_id,
                        'product_name': prod_name,
                        'quants': []
                    }
                
                products_negative[prod_id]['quants'].append({
                    'location': loc_name,
                    'quantity': q['quantity'],
                    'reserved': q.get('reserved_quantity', 0),
                    'lot': q['lot_id'][1] if q.get('lot_id') else None
                })
                
                print(f"  🔴 {prod_name}")
                print(f"       Ubicación: {loc_name}")
                print(f"       Cantidad: {q['quantity']}")
            
            self.results["products_negative_stock"] = list(products_negative.values())
            
            # Obtener más detalles de los productos
            if products_negative:
                prod_ids = list(products_negative.keys())
                products_detail = self.search_read(
                    'product.product',
                    [('id', 'in', prod_ids)],
                    ['id', 'name', 'default_code', 'type', 'categ_id', 
                     'uom_id', 'tracking', 'qty_available', 'virtual_available']
                )
                
                print(f"\nDetalles de {len(products_detail)} productos con stock negativo:")
                for p in products_detail:
                    print(f"  [{p['id']}] {p.get('default_code', 'N/A')} - {p['name']}")
                    print(f"       Tipo: {p.get('type')}, Categoría: {p.get('categ_id', ['', 'N/A'])[1]}")
                    print(f"       Stock disponible: {p.get('qty_available')}")
                    print(f"       Stock virtual: {p.get('virtual_available')}")
                
                self.results["products_negative_stock_detail"] = products_detail
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.results["errors"].append({"phase": "negative_stock", "error": str(e)})
    
    def analyze_rf_insumos_moves(self):
        """Analiza movimientos específicos de RF INSUMOS"""
        print("\n" + "=" * 60)
        print("ANALIZANDO MOVIMIENTOS DE RF INSUMOS...")
        print("=" * 60)
        
        try:
            # Primero identificar la ubicación exacta de RF INSUMOS
            rf_loc = self.results.get("rf_insumos_location")
            
            if not rf_loc:
                # Buscar más ampliamente
                locations = self.search_read(
                    'stock.location',
                    ['|', ('name', 'ilike', 'insumos'), 
                         ('complete_name', 'ilike', 'insumos')],
                    ['id', 'name', 'complete_name', 'usage']
                )
                print(f"Ubicaciones relacionadas con 'insumos': {len(locations)}")
                for loc in locations:
                    print(f"  - [{loc['id']}] {loc.get('complete_name')}")
                
                if locations:
                    rf_loc = locations[0]
                    self.results["rf_insumos_location"] = rf_loc
            
            if rf_loc:
                loc_id = rf_loc['id']
                print(f"\nAnalizando ubicación: {rf_loc.get('complete_name')}")
                
                # Movimientos DESDE esta ubicación (salidas)
                moves_out = self.search_read(
                    'stock.move',
                    [('location_id', '=', loc_id), ('state', '=', 'done')],
                    ['id', 'name', 'product_id', 'product_uom_qty', 'quantity_done',
                     'date', 'reference', 'origin', 'picking_id', 'create_uid',
                     'raw_material_production_id', 'production_id'],
                    limit=500,
                    order='date desc'
                )
                
                print(f"  → {len(moves_out)} movimientos de salida (últimos 500)")
                
                # Movimientos HACIA esta ubicación (entradas)
                moves_in = self.search_read(
                    'stock.move',
                    [('location_dest_id', '=', loc_id), ('state', '=', 'done')],
                    ['id', 'name', 'product_id', 'product_uom_qty', 'quantity_done',
                     'date', 'reference', 'origin', 'picking_id', 'create_uid'],
                    limit=500,
                    order='date desc'
                )
                
                print(f"  → {len(moves_in)} movimientos de entrada (últimos 500)")
                
                self.results["rf_insumos_moves"] = {
                    "location": rf_loc,
                    "moves_out": moves_out,
                    "moves_in": moves_in
                }
                
                # Analizar patrones
                print("\nPatrones de movimientos de salida:")
                origins = defaultdict(int)
                users = defaultdict(int)
                mrp_related = 0
                manual = 0
                
                for m in moves_out:
                    origin = m.get('origin') or 'Sin origen'
                    origins[origin[:50]] += 1
                    
                    user = m.get('create_uid')
                    if user:
                        users[user[1]] += 1
                    
                    if m.get('raw_material_production_id') or m.get('production_id'):
                        mrp_related += 1
                    elif not m.get('picking_id'):
                        manual += 1
                
                print(f"  - Relacionados con MRP: {mrp_related}")
                print(f"  - Sin picking (posibles manuales): {manual}")
                print(f"\nTop orígenes de movimiento:")
                for orig, count in sorted(origins.items(), key=lambda x: -x[1])[:10]:
                    print(f"    {orig}: {count}")
                
                print(f"\nUsuarios que crearon movimientos:")
                for user, count in sorted(users.items(), key=lambda x: -x[1]):
                    print(f"    {user}: {count} movimientos")
                
                self.results["rf_insumos_patterns"] = {
                    "total_out": len(moves_out),
                    "total_in": len(moves_in),
                    "mrp_related": mrp_related,
                    "manual": manual,
                    "origins": dict(origins),
                    "users": dict(users)
                }
                
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.results["errors"].append({"phase": "rf_insumos_moves", "error": str(e)})
    
    def analyze_mrp_consumptions(self):
        """Analiza consumos desde órdenes de fabricación"""
        print("\n" + "=" * 60)
        print("ANALIZANDO CONSUMOS DESDE MRP...")
        print("=" * 60)
        
        try:
            # Obtener órdenes de producción recientes con sus movimientos
            productions = self.search_read(
                'mrp.production',
                [('state', 'in', ['done', 'progress', 'to_close'])],
                ['id', 'name', 'product_id', 'product_qty', 'qty_producing',
                 'date_planned_start', 'date_finished', 'state', 
                 'bom_id', 'user_id', 'company_id', 'origin'],
                limit=200,
                order='date_planned_start desc'
            )
            
            print(f"✓ {len(productions)} órdenes de producción analizadas")
            
            productions_with_issues = []
            
            for prod in productions[:50]:  # Analizar las 50 más recientes
                prod_id = prod['id']
                
                # Obtener movimientos de consumo (raw materials)
                raw_moves = self.search_read(
                    'stock.move',
                    [('raw_material_production_id', '=', prod_id), 
                     ('state', '=', 'done')],
                    ['id', 'product_id', 'product_uom_qty', 'quantity_done',
                     'date', 'reference', 'create_uid', 'location_id', 'location_dest_id']
                )
                
                # Detectar posibles duplicados
                product_consumptions = defaultdict(list)
                for m in raw_moves:
                    prod_name = m['product_id'][1] if m.get('product_id') else 'N/A'
                    product_consumptions[m['product_id'][0]].append({
                        'move_id': m['id'],
                        'qty': m.get('quantity_done', 0),
                        'date': m.get('date'),
                        'user': m.get('create_uid', [0, 'N/A'])[1]
                    })
                
                # Detectar productos consumidos más de una vez
                duplicates = {k: v for k, v in product_consumptions.items() if len(v) > 1}
                
                if duplicates:
                    prod_info = {
                        'production': prod,
                        'raw_moves': raw_moves,
                        'potential_duplicates': duplicates
                    }
                    productions_with_issues.append(prod_info)
                    
                    print(f"\n⚠️ {prod['name']} - Posibles consumos múltiples:")
                    for prod_id_dup, moves in duplicates.items():
                        print(f"    Producto ID {prod_id_dup}: {len(moves)} consumos")
                        for m in moves:
                            print(f"      - Qty: {m['qty']}, User: {m['user']}, Date: {m['date']}")
            
            self.results["mrp_productions"] = productions
            self.results["mrp_with_duplicate_consumptions"] = productions_with_issues
            
            print(f"\nTotal órdenes con posibles duplicados: {len(productions_with_issues)}")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.results["errors"].append({"phase": "mrp_consumptions", "error": str(e)})
    
    def analyze_manual_inventory_moves(self):
        """Analiza ajustes de inventario manuales"""
        print("\n" + "=" * 60)
        print("ANALIZANDO AJUSTES DE INVENTARIO...")
        print("=" * 60)
        
        try:
            # Buscar ubicación de ajuste de inventario
            inv_locations = self.search_read(
                'stock.location',
                [('usage', '=', 'inventory')],
                ['id', 'name', 'complete_name']
            )
            
            print(f"Ubicaciones de ajuste: {len(inv_locations)}")
            for loc in inv_locations:
                print(f"  - [{loc['id']}] {loc.get('complete_name')}")
            
            if inv_locations:
                inv_loc_ids = [l['id'] for l in inv_locations]
                
                # Movimientos DESDE ubicación de ajuste (entradas al stock)
                adj_moves_in = self.search_read(
                    'stock.move',
                    [('location_id', 'in', inv_loc_ids), ('state', '=', 'done')],
                    ['id', 'product_id', 'product_uom_qty', 'quantity_done',
                     'date', 'reference', 'origin', 'create_uid'],
                    limit=500,
                    order='date desc'
                )
                
                # Movimientos HACIA ubicación de ajuste (salidas del stock)
                adj_moves_out = self.search_read(
                    'stock.move',
                    [('location_dest_id', 'in', inv_loc_ids), ('state', '=', 'done')],
                    ['id', 'product_id', 'product_uom_qty', 'quantity_done',
                     'date', 'reference', 'origin', 'create_uid'],
                    limit=500,
                    order='date desc'
                )
                
                print(f"\nAjustes de inventario:")
                print(f"  - Entradas (ajuste positivo): {len(adj_moves_in)}")
                print(f"  - Salidas (ajuste negativo): {len(adj_moves_out)}")
                
                # Análisis por usuario
                users_adj = defaultdict(lambda: {'in': 0, 'out': 0, 'qty_in': 0, 'qty_out': 0})
                
                for m in adj_moves_in:
                    user = m.get('create_uid', [0, 'Sistema'])[1]
                    users_adj[user]['in'] += 1
                    users_adj[user]['qty_in'] += m.get('quantity_done', 0)
                
                for m in adj_moves_out:
                    user = m.get('create_uid', [0, 'Sistema'])[1]
                    users_adj[user]['out'] += 1
                    users_adj[user]['qty_out'] += m.get('quantity_done', 0)
                
                print("\nAjustes por usuario:")
                for user, data in users_adj.items():
                    print(f"  {user}:")
                    print(f"    Entradas: {data['in']} movs, {data['qty_in']:.2f} uds")
                    print(f"    Salidas: {data['out']} movs, {data['qty_out']:.2f} uds")
                
                self.results["inventory_adjustments"] = {
                    "locations": inv_locations,
                    "moves_in": adj_moves_in,
                    "moves_out": adj_moves_out,
                    "users_summary": dict(users_adj)
                }
                
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.results["errors"].append({"phase": "inventory_adjustments", "error": str(e)})
    
    def analyze_quant_vs_moves(self):
        """Compara stock en quants vs sumatoria de movimientos"""
        print("\n" + "=" * 60)
        print("COMPARANDO QUANTS VS MOVIMIENTOS...")
        print("=" * 60)
        
        try:
            # Obtener productos con stock negativo para analizar
            negative_products = self.results.get("products_negative_stock", [])
            
            if not negative_products:
                print("No hay productos con stock negativo para analizar")
                return
            
            discrepancies = []
            
            for prod_info in negative_products[:20]:  # Limitar a 20
                prod_id = prod_info['product_id']
                prod_name = prod_info['product_name']
                
                # Obtener quants actuales
                quants = self.search_read(
                    'stock.quant',
                    [('product_id', '=', prod_id)],
                    ['id', 'location_id', 'quantity', 'reserved_quantity']
                )
                
                quant_total = sum(q.get('quantity', 0) for q in quants)
                
                # Obtener sumatoria de movimientos done
                # Entradas (location_dest_id = ubicación interna)
                internal_locs = [l['id'] for l in self.results.get("locations", []) 
                                if l.get('usage') == 'internal']
                
                if internal_locs:
                    moves_in = self.search_read(
                        'stock.move',
                        [('product_id', '=', prod_id),
                         ('state', '=', 'done'),
                         ('location_dest_id', 'in', internal_locs),
                         ('location_id', 'not in', internal_locs)],
                        ['id', 'quantity_done']
                    )
                    
                    moves_out = self.search_read(
                        'stock.move',
                        [('product_id', '=', prod_id),
                         ('state', '=', 'done'),
                         ('location_id', 'in', internal_locs),
                         ('location_dest_id', 'not in', internal_locs)],
                        ['id', 'quantity_done']
                    )
                    
                    total_in = sum(m.get('quantity_done', 0) for m in moves_in)
                    total_out = sum(m.get('quantity_done', 0) for m in moves_out)
                    calculated_stock = total_in - total_out
                    
                    diff = abs(quant_total - calculated_stock)
                    
                    if diff > 0.01:  # Tolerancia mínima
                        discrepancy = {
                            'product_id': prod_id,
                            'product_name': prod_name,
                            'quant_total': quant_total,
                            'moves_in': total_in,
                            'moves_out': total_out,
                            'calculated_stock': calculated_stock,
                            'difference': quant_total - calculated_stock
                        }
                        discrepancies.append(discrepancy)
                        
                        print(f"\n⚠️ {prod_name} (ID: {prod_id})")
                        print(f"   Stock en quants: {quant_total:.2f}")
                        print(f"   Entradas: {total_in:.2f}, Salidas: {total_out:.2f}")
                        print(f"   Stock calculado: {calculated_stock:.2f}")
                        print(f"   Diferencia: {quant_total - calculated_stock:.2f}")
            
            self.results["quant_vs_moves_diff"] = discrepancies
            print(f"\nTotal discrepancias encontradas: {len(discrepancies)}")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.results["errors"].append({"phase": "quant_vs_moves", "error": str(e)})
    
    def analyze_users_operations(self):
        """Analiza operaciones por usuario"""
        print("\n" + "=" * 60)
        print("ANALIZANDO OPERACIONES POR USUARIO...")
        print("=" * 60)
        
        try:
            # Obtener usuarios que han creado movimientos de stock
            moves_by_user = self.search_read(
                'stock.move',
                [('state', '=', 'done')],
                ['create_uid', 'picking_type_id', 'raw_material_production_id',
                 'location_id', 'location_dest_id'],
                limit=5000      
            )
            
            user_stats = defaultdict(lambda: {
                'total_moves': 0,
                'mrp_moves': 0,
                'picking_moves': 0,
                'other_moves': 0,
                'picking_types': defaultdict(int)
            })
            
            for m in moves_by_user:
                user = m.get('create_uid', [0, 'Sistema'])
                user_name = user[1] if user else 'Sistema'
                
                user_stats[user_name]['total_moves'] += 1
                
                if m.get('raw_material_production_id'):
                    user_stats[user_name]['mrp_moves'] += 1
                elif m.get('picking_type_id'):
                    user_stats[user_name]['picking_moves'] += 1
                    pt_name = m['picking_type_id'][1]
                    user_stats[user_name]['picking_types'][pt_name] += 1
                else:
                    user_stats[user_name]['other_moves'] += 1
            
            print("\nResumen por usuario:")
            for user, stats in sorted(user_stats.items(), 
                                       key=lambda x: -x[1]['total_moves']):
                print(f"\n{user}:")
                print(f"  Total movimientos: {stats['total_moves']}")
                print(f"  Relacionados con MRP: {stats['mrp_moves']}")
                print(f"  Desde pickings: {stats['picking_moves']}")
                print(f"  Otros (posibles manuales): {stats['other_moves']}")
                if stats['picking_types']:
                    print(f"  Tipos de picking:")
                    for pt, count in stats['picking_types'].items():
                        print(f"    - {pt}: {count}")
            
            self.results["users_operations"] = {k: dict(v) for k, v in user_stats.items()}
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.results["errors"].append({"phase": "users_operations", "error": str(e)})
    
    def analyze_bom_vs_consumption(self):
        """Compara consumo teórico de BOM vs consumo real"""
        print("\n" + "=" * 60)
        print("ANALIZANDO BOM VS CONSUMO REAL...")
        print("=" * 60)
        
        try:
            # Obtener algunas producciones terminadas
            productions = self.search_read(
                'mrp.production',
                [('state', '=', 'done')],
                ['id', 'name', 'product_id', 'product_qty', 'bom_id'],
                limit=50,
                order='date_finished desc'
            )
            
            bom_discrepancies = []
            
            for prod in productions[:20]:
                if not prod.get('bom_id'):
                    continue
                    
                bom_id = prod['bom_id'][0]
                prod_qty = prod.get('product_qty', 0)
                
                # Obtener líneas de BOM
                bom_lines = self.search_read(
                    'mrp.bom.line',
                    [('bom_id', '=', bom_id)],
                    ['product_id', 'product_qty', 'product_uom_id']
                )
                
                # Obtener consumos reales
                real_moves = self.search_read(
                    'stock.move',
                    [('raw_material_production_id', '=', prod['id']),
                     ('state', '=', 'done')],
                    ['product_id', 'quantity_done']
                )
                
                # Comparar
                bom_consumption = {}
                for line in bom_lines:
                    prod_id = line['product_id'][0]
                    expected_qty = line['product_qty'] * prod_qty
                    bom_consumption[prod_id] = {
                        'name': line['product_id'][1],
                        'expected': expected_qty,
                        'actual': 0
                    }
                
                for move in real_moves:
                    prod_id = move['product_id'][0]
                    if prod_id in bom_consumption:
                        bom_consumption[prod_id]['actual'] += move.get('quantity_done', 0)
                    else:
                        bom_consumption[prod_id] = {
                            'name': move['product_id'][1],
                            'expected': 0,
                            'actual': move.get('quantity_done', 0)
                        }
                
                # Detectar discrepancias
                has_discrepancy = False
                for prod_id, data in bom_consumption.items():
                    diff = abs(data['expected'] - data['actual'])
                    if diff > 0.01:
                        has_discrepancy = True
                
                if has_discrepancy:
                    bom_discrepancies.append({
                        'production': prod['name'],
                        'bom': prod['bom_id'][1],
                        'product_qty': prod_qty,
                        'consumption_comparison': bom_consumption
                    })
            
            print(f"\nProducciones con discrepancia BOM vs Real: {len(bom_discrepancies)}")
            
            for disc in bom_discrepancies[:5]:
                print(f"\n{disc['production']} (BOM: {disc['bom']}):")
                for prod_id, data in disc['consumption_comparison'].items():
                    diff = data['actual'] - data['expected']
                    if abs(diff) > 0.01:
                        status = "🔴 EXCESO" if diff > 0 else "🟡 FALTANTE"
                        print(f"  {data['name']}: Esperado={data['expected']:.2f}, Real={data['actual']:.2f} ({status} {abs(diff):.2f})")
            
            self.results["bom_discrepancies"] = bom_discrepancies
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.results["errors"].append({"phase": "bom_analysis", "error": str(e)})
    
    def analyze_valuation_layers(self):
        """Analiza capas de valoración para productos con problemas"""
        print("\n" + "=" * 60)
        print("ANALIZANDO VALORACIÓN DE INVENTARIO...")
        print("=" * 60)
        
        try:
            # Verificar si existe el modelo
            try:
                count = self.search_count('stock.valuation.layer', [])
                print(f"✓ Modelo stock.valuation.layer existe con {count} registros")
            except Exception:
                print("✗ Modelo stock.valuation.layer no disponible")
                return
            
            # Obtener layers para productos con stock negativo
            negative_products = self.results.get("products_negative_stock", [])
            prod_ids = [p['product_id'] for p in negative_products]
            
            if prod_ids:
                layers = self.search_read(
                    'stock.valuation.layer',
                    [('product_id', 'in', prod_ids)],
                    ['product_id', 'quantity', 'value', 'remaining_qty',
                     'remaining_value', 'stock_move_id', 'create_date'],
                    limit=500,
                    order='create_date desc'
                )
                
                print(f"\n{len(layers)} capas de valoración para productos con stock negativo")
                
                # Agrupar por producto
                layers_by_product = defaultdict(list)
                for l in layers:
                    prod_id = l['product_id'][0]
                    layers_by_product[prod_id].append(l)
                
                for prod_id, prod_layers in layers_by_product.items():
                    prod_name = prod_layers[0]['product_id'][1]
                    total_qty = sum(l.get('remaining_qty', 0) for l in prod_layers)
                    total_value = sum(l.get('remaining_value', 0) for l in prod_layers)
                    
                    print(f"\n{prod_name}:")
                    print(f"  Capas: {len(prod_layers)}")
                    print(f"  Cantidad restante total: {total_qty:.2f}")
                    print(f"  Valor restante total: {total_value:.2f}")
                    
                    # Detectar capas con valor negativo
                    negative_layers = [l for l in prod_layers if l.get('remaining_value', 0) < 0]
                    if negative_layers:
                        print(f"  ⚠️ {len(negative_layers)} capas con valor negativo!")
                
                self.results["valuation_analysis"] = {
                    "total_layers": count,
                    "layers_negative_products": layers,
                    "by_product": {k: v for k, v in layers_by_product.items()}
                }
                
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.results["errors"].append({"phase": "valuation", "error": str(e)})
    
    def detect_duplicate_manual_vs_mrp(self):
        """Detecta consumos duplicados entre manuales y MRP"""
        print("\n" + "=" * 60)
        print("DETECTANDO DUPLICIDAD MANUAL VS MRP...")
        print("=" * 60)
        
        try:
            # Para cada producción, verificar si hay movimientos manuales
            # en el mismo período hacia los mismos productos
            
            productions = self.search_read(
                'mrp.production',
                [('state', '=', 'done')],
                ['id', 'name', 'date_finished', 'product_id'],
                limit=100,
                order='date_finished desc'
            )
            
            potential_duplicates = []
            
            for prod in productions[:30]:
                prod_id = prod['id']
                date_finished = prod.get('date_finished')
                
                if not date_finished:
                    continue
                
                # Obtener componentes consumidos en esta producción
                mrp_moves = self.search_read(
                    'stock.move',
                    [('raw_material_production_id', '=', prod_id),
                     ('state', '=', 'done')],
                    ['product_id', 'quantity_done', 'date', 'create_uid']
                )
                
                if not mrp_moves:
                    continue
                
                component_ids = [m['product_id'][0] for m in mrp_moves]
                
                # Buscar movimientos manuales (sin picking ni producción)
                # en ventana de tiempo cercana (±3 días)
                manual_moves = self.search_read(
                    'stock.move',
                    [('product_id', 'in', component_ids),
                     ('state', '=', 'done'),
                     ('raw_material_production_id', '=', False),
                     ('production_id', '=', False),
                     ('picking_id', '=', False)],
                    ['product_id', 'quantity_done', 'date', 'create_uid',
                     'location_id', 'location_dest_id', 'reference'],
                    limit=100
                )
                
                if manual_moves:
                    # Verificar si son transiciones hacia producción
                    suspicious = []
                    for mm in manual_moves:
                        loc_dest = mm.get('location_dest_id', [0, ''])[1].lower()
                        if 'producción' in loc_dest or 'production' in loc_dest:
                            suspicious.append(mm)
                    
                    if suspicious:
                        potential_duplicates.append({
                            'production': prod['name'],
                            'mrp_moves_count': len(mrp_moves),
                            'suspicious_manual_moves': suspicious
                        })
            
            print(f"\nProducciones con posibles consumos duplicados: {len(potential_duplicates)}")
            
            for dup in potential_duplicates[:5]:
                print(f"\n{dup['production']}:")
                print(f"  Movimientos MRP: {dup['mrp_moves_count']}")
                print(f"  Movimientos manuales sospechosos: {len(dup['suspicious_manual_moves'])}")
                for mm in dup['suspicious_manual_moves'][:3]:
                    print(f"    - {mm['product_id'][1]}: {mm.get('quantity_done')} uds")
                    print(f"      Ref: {mm.get('reference')}, User: {mm.get('create_uid', [0, 'N/A'])[1]}")
            
            self.results["duplicate_consumptions"] = potential_duplicates
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.results["errors"].append({"phase": "duplicate_detection", "error": str(e)})
    
    def generate_summary_report(self):
        """Genera resumen del análisis"""
        print("\n" + "=" * 80)
        print("RESUMEN DE AUDITORÍA")
        print("=" * 80)
        
        summary = {
            "fecha_auditoria": datetime.now().isoformat(),
            "conexion": self.results["connection"].get("status"),
            "version_odoo": self.results["connection"].get("version", {}).get("server_version"),
        }
        
        # Ubicaciones
        locations = self.results.get("locations", [])
        internal_locs = [l for l in locations if l.get('usage') == 'internal']
        summary["ubicaciones_internas"] = len(internal_locs)
        
        rf_loc = self.results.get("rf_insumos_location")
        summary["rf_insumos_encontrado"] = bool(rf_loc)
        if rf_loc:
            summary["rf_insumos_ubicacion"] = rf_loc.get('complete_name')
        
        # Productos con stock negativo
        neg_products = self.results.get("products_negative_stock", [])
        summary["productos_stock_negativo"] = len(neg_products)
        
        if neg_products:
            print(f"\n🔴 PRODUCTOS CON STOCK NEGATIVO: {len(neg_products)}")
            for p in neg_products[:10]:
                print(f"   - {p['product_name']}")
                for q in p.get('quants', []):
                    print(f"     {q['location']}: {q['quantity']}")
        
        # Discrepancias quant vs moves
        discrepancies = self.results.get("quant_vs_moves_diff", [])
        summary["discrepancias_quant_moves"] = len(discrepancies)
        
        # Consumos duplicados
        duplicates = self.results.get("mrp_with_duplicate_consumptions", [])
        summary["producciones_consumos_multiples"] = len(duplicates)
        
        # Duplicación manual vs MRP
        dup_manual = self.results.get("duplicate_consumptions", [])
        summary["posibles_duplicados_manual_mrp"] = len(dup_manual)
        
        # Errores
        summary["errores_auditoria"] = len(self.results.get("errors", []))
        
        print("\n" + "-" * 40)
        print("MÉTRICAS CLAVE:")
        print("-" * 40)
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        self.results["summary"] = summary
        return summary
    
    def save_results(self, filename: str = "audit_results.json"):
        """Guarda resultados en archivo JSON"""
        
        # Convertir objetos no serializables
        def clean_for_json(obj):
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(i) for i in obj]
            elif isinstance(obj, (datetime,)):
                return obj.isoformat()
            elif isinstance(obj, defaultdict):
                return dict(obj)
            else:
                return obj
        
        clean_results = clean_for_json(self.results)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(clean_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Resultados guardados en: {filename}")
    
    def run_full_audit(self):
        """Ejecuta auditoría completa"""
        print("\n" + "=" * 80)
        print("INICIANDO AUDITORÍA COMPLETA DE CONSUMO DE INSUMOS")
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        if not self.connect():
            print("No se pudo conectar a Odoo. Abortando auditoría.")
            return False
        
        print("\n>>> FASE 1: LEVANTAMIENTO")
        self.analyze_locations()
        self.analyze_operation_types()
        self.analyze_stock_config()
        self.analyze_product_categories()
        
        print("\n>>> FASE 2: DIAGNÓSTICO")
        self.find_negative_stock_products()
        self.analyze_rf_insumos_moves()
        self.analyze_mrp_consumptions()
        self.analyze_manual_inventory_moves()
        self.analyze_quant_vs_moves()
        self.analyze_users_operations()
        self.analyze_bom_vs_consumption()
        self.analyze_valuation_layers()
        self.detect_duplicate_manual_vs_mrp()
        
        print("\n>>> GENERANDO RESUMEN")
        self.generate_summary_report()
        
        return True


# ============================================================================
# EJECUCIÓN PRINCIPAL
# ============================================================================
if __name__ == "__main__":
    auditor = OdooAuditor(URL, DB, USERNAME, PASSWORD)
    
    if auditor.run_full_audit():
        auditor.save_results("audit_insumos_results.json")
        print("\n" + "=" * 80)
        print("AUDITORÍA COMPLETADA")
        print("=" * 80)
        print("Revisa el archivo 'audit_insumos_results.json' para resultados detallados.")
    else:
        print("\nAuditoría fallida. Revisa los errores.")

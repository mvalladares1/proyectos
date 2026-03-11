"""
VALIDACIONES TÉCNICAS PARA PLAN DE REGULARIZACIÓN
==================================================
Script de validación profunda de hallazgos críticos
para diseñar plan ejecutable de RF INSUMOS.

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

class ValidationAuditor:
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.common = None
        self.models = None
        self.validations = {
            "A1_consumo_operation": {"status": "pending", "findings": []},
            "A2_mrp_consumption_flow": {"status": "pending", "findings": []},
            "A3_product_families": {"status": "pending", "findings": []},
            "A4_vendor_negatives_origin": {"status": "pending", "findings": []},
            "B_future_model": {"status": "pending", "findings": []},
            "C_rf_insumos_plan": {"status": "pending", "findings": []},
            "D_accounting_impact": {"status": "pending", "findings": []},
        }
        self.results = {}
    
    def connect(self) -> bool:
        try:
            print("Conectando a Odoo...")
            self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = self.common.authenticate(self.db, self.username, self.password, {})
            if self.uid:
                print(f"✓ Conectado. UID: {self.uid}")
                self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
                return True
            return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    def execute(self, model: str, method: str, *args, **kwargs):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, list(args), kwargs
        )
    
    def search_read(self, model: str, domain: list = None, fields: list = None, 
                    limit: int = None, order: str = None) -> List[Dict]:
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
        domain = domain or []
        return self.execute(model, 'search_count', domain)

    # ========================================================================
    # FASE A1: VALIDACIÓN TIPO OPERACIÓN CONSUMO
    # ========================================================================
    
    def validate_consumo_operation(self):
        """Auditar en detalle el tipo de operación CONSUMO"""
        print("\n" + "=" * 80)
        print("FASE A1: VALIDACIÓN TIPO OPERACIÓN CONSUMO")
        print("=" * 80)
        
        findings = []
        
        try:
            # 1. Buscar tipo operación CONSUMO por nombre
            consumo_types = self.search_read(
                'stock.picking.type',
                [('name', 'ilike', 'consumo')],
                ['id', 'name', 'code', 'sequence_code', 'active',
                 'default_location_src_id', 'default_location_dest_id',
                 'warehouse_id', 'company_id', 'use_create_lots',
                 'use_existing_lots', 'show_operations']
            )
            
            print(f"\nTipos de operación con 'consumo' en nombre: {len(consumo_types)}")
            
            for ct in consumo_types:
                print(f"\n📋 [{ct['id']}] {ct['name']}")
                print(f"   Código: {ct.get('code')}")
                print(f"   Secuencia: {ct.get('sequence_code')}")
                print(f"   Activo: {ct.get('active')}")
                print(f"   Origen: {ct.get('default_location_src_id')}")
                print(f"   Destino: {ct.get('default_location_dest_id')}")
                
                # Contar pickings de este tipo
                total_pickings = self.search_count('stock.picking', 
                    [('picking_type_id', '=', ct['id'])])
                done_pickings = self.search_count('stock.picking',
                    [('picking_type_id', '=', ct['id']), ('state', '=', 'done')])
                draft_pickings = self.search_count('stock.picking',
                    [('picking_type_id', '=', ct['id']), ('state', '=', 'draft')])
                assigned_pickings = self.search_count('stock.picking',
                    [('picking_type_id', '=', ct['id']), ('state', '=', 'assigned')])
                
                print(f"\n   📊 Estadísticas de uso:")
                print(f"   Total pickings: {total_pickings}")
                print(f"   - Done: {done_pickings}")
                print(f"   - Draft: {draft_pickings}")
                print(f"   - Asignados: {assigned_pickings}")
                
                findings.append({
                    "type": "CONFIRMED",
                    "finding": f"Tipo operación '{ct['name']}' (ID {ct['id']}) tiene {done_pickings} pickings completados",
                    "impact": "ALTO" if done_pickings > 100 else "MEDIO"
                })
                
                # Obtener pickings done para análisis
                if done_pickings > 0:
                    pickings_sample = self.search_read(
                        'stock.picking',
                        [('picking_type_id', '=', ct['id']), ('state', '=', 'done')],
                        ['id', 'name', 'origin', 'partner_id', 'create_uid',
                         'scheduled_date', 'date_done', 'location_id', 'location_dest_id'],
                        limit=100,
                        order='date_done desc'
                    )
                    
                    # Análisis de usuarios
                    users_usage = defaultdict(int)
                    origins = defaultdict(int)
                    
                    for p in pickings_sample:
                        user = p.get('create_uid', [0, 'Sistema'])[1]
                        users_usage[user] += 1
                        origin = p.get('origin') or 'Sin origen'
                        origins[origin[:30]] += 1
                    
                    print(f"\n   👤 Usuarios que usan este tipo (de muestra de {len(pickings_sample)}):")
                    for user, count in sorted(users_usage.items(), key=lambda x: -x[1])[:5]:
                        print(f"      {user}: {count} pickings")
                        
                    print(f"\n   📄 Orígenes de documento:")
                    for origin, count in sorted(origins.items(), key=lambda x: -x[1])[:5]:
                        print(f"      {origin}: {count}")
                    
                    # Verificar si hay correlación con OFs
                    pickings_with_mfg_origin = [p for p in pickings_sample 
                                                if p.get('origin') and 
                                                ('MO' in str(p.get('origin')).upper() or 
                                                 'WH/MO' in str(p.get('origin')).upper())]
                    
                    print(f"\n   🏭 Pickings con origen MO: {len(pickings_with_mfg_origin)}")
                    
                    if len(pickings_with_mfg_origin) == 0:
                        findings.append({
                            "type": "CONFIRMED",
                            "finding": f"Los pickings de '{ct['name']}' NO tienen correlación con OFs",
                            "impact": "Confirma uso como consumo manual independiente"
                        })
                    
                    # Obtener productos afectados
                    moves = self.search_read(
                        'stock.move',
                        [('picking_type_id', '=', ct['id']), ('state', '=', 'done')],
                        ['product_id', 'quantity_done'],
                        limit=500
                    )
                    
                    products_consumed = defaultdict(float)
                    for m in moves:
                        prod = m['product_id'][1] if m.get('product_id') else 'N/A'
                        products_consumed[prod] += m.get('quantity_done', 0)
                    
                    print(f"\n   📦 Top 10 productos consumidos por este tipo:")
                    for prod, qty in sorted(products_consumed.items(), key=lambda x: -x[1])[:10]:
                        print(f"      {prod[:50]}: {qty:,.2f}")
                    
                    self.results["consumo_top_products"] = dict(
                        sorted(products_consumed.items(), key=lambda x: -x[1])[:50]
                    )
            
            # 2. Verificar si bloquear este tipo rompería procesos
            # Buscar pickings draft o asignados (pendientes)
            pending_consumo = []
            for ct in consumo_types:
                pending = self.search_read(
                    'stock.picking',
                    [('picking_type_id', '=', ct['id']), 
                     ('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])],
                    ['id', 'name', 'state', 'scheduled_date'],
                    limit=50
                )
                pending_consumo.extend(pending)
            
            print(f"\n⚠️ Pickings pendientes de tipo CONSUMO: {len(pending_consumo)}")
            if pending_consumo:
                findings.append({
                    "type": "WARNING",
                    "finding": f"Hay {len(pending_consumo)} pickings CONSUMO pendientes que se afectarían",
                    "impact": "Deben completarse o cancelarse antes de bloquear"
                })
                for p in pending_consumo[:10]:
                    print(f"   - {p['name']} ({p['state']})")
            
            self.validations["A1_consumo_operation"]["status"] = "completed"
            self.validations["A1_consumo_operation"]["findings"] = findings
            self.results["consumo_types"] = consumo_types
            self.results["pending_consumo"] = pending_consumo
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.validations["A1_consumo_operation"]["status"] = "error"
            self.validations["A1_consumo_operation"]["findings"].append({
                "type": "ERROR",
                "finding": str(e)
            })

    # ========================================================================
    # FASE A2: VALIDACIÓN FLUJO DE CONSUMO MRP
    # ========================================================================
    
    def validate_mrp_consumption_flow(self):
        """Auditar cómo se consumen componentes en OFs"""
        print("\n" + "=" * 80)
        print("FASE A2: VALIDACIÓN FLUJO DE CONSUMO MRP")
        print("=" * 80)
        
        findings = []
        
        try:
            # 1. Obtener configuración de consumo de producción
            print("\n🔧 Analizando configuración de MRP...")
            
            # Buscar BOMs y su configuración
            boms = self.search_read(
                'mrp.bom',
                [('active', '=', True)],
                ['id', 'product_tmpl_id', 'type', 'consumption', 
                 'ready_to_produce', 'bom_line_ids'],
                limit=50
            )
            
            consumption_modes = defaultdict(int)
            for bom in boms:
                mode = bom.get('consumption', 'N/A')
                consumption_modes[mode] += 1
            
            print(f"\nModos de consumo en BOMs:")
            for mode, count in consumption_modes.items():
                print(f"   {mode}: {count} BOMs")
                
            findings.append({
                "type": "INFO",
                "finding": f"Modos de consumo: {dict(consumption_modes)}",
                "impact": "Determina si consumo es flexible o estricto"
            })
            
            # 2. Analizar órdenes de fabricación recientes
            print("\n🏭 Analizando órdenes de fabricación recientes...")
            
            productions = self.search_read(
                'mrp.production',
                [('state', '=', 'done')],
                ['id', 'name', 'product_id', 'product_qty', 'date_finished',
                 'bom_id', 'consumption', 'location_src_id', 'location_dest_id',
                 'user_id', 'move_raw_ids', 'move_finished_ids'],
                limit=100,
                order='date_finished desc'
            )
            
            print(f"Producciones analizadas: {len(productions)}")
            
            # Analizar cada producción
            productions_analysis = []
            
            for prod in productions[:30]:
                prod_id = prod['id']
                
                # Obtener movimientos de materia prima
                raw_moves = self.search_read(
                    'stock.move',
                    [('raw_material_production_id', '=', prod_id)],
                    ['id', 'product_id', 'product_uom_qty', 'quantity_done',
                     'state', 'location_id', 'location_dest_id', 'date',
                     'create_date', 'write_date', 'create_uid', 'reference']
                )
                
                # Verificar cuándo se consumió
                consumption_timestamps = []
                for rm in raw_moves:
                    if rm.get('state') == 'done':
                        consumption_timestamps.append({
                            'product': rm['product_id'][1] if rm.get('product_id') else 'N/A',
                            'qty': rm.get('quantity_done', 0),
                            'date': rm.get('date'),
                            'location_src': rm.get('location_id', [0, 'N/A'])[1],
                            'location_dest': rm.get('location_dest_id', [0, 'N/A'])[1]
                        })
                
                # Verificar si hay consumos fuera de la OF
                prod_components = [rm['product_id'][0] for rm in raw_moves if rm.get('product_id')]
                
                analysis = {
                    'production': prod['name'],
                    'product': prod['product_id'][1] if prod.get('product_id') else 'N/A',
                    'qty': prod.get('product_qty'),
                    'raw_moves_count': len(raw_moves),
                    'done_moves': len([rm for rm in raw_moves if rm.get('state') == 'done']),
                    'consumption_mode': prod.get('consumption', 'N/A'),
                    'location_src': prod.get('location_src_id', [0, 'N/A'])[1],
                }
                
                # Detectar si consumo es automático o manual
                if raw_moves:
                    first_move_date = min([rm['date'] for rm in raw_moves if rm.get('date')], default=None)
                    prod_date = prod.get('date_finished')
                    if first_move_date and prod_date:
                        # Si las fechas son muy cercanas, es consumo automático
                        analysis['consumption_type'] = 'AUTOMATIC' if first_move_date == prod_date else 'SEPARATE'
                
                productions_analysis.append(analysis)
            
            # Estadísticas de consumo
            auto_consumptions = len([p for p in productions_analysis if p.get('consumption_type') == 'AUTOMATIC'])
            separate_consumptions = len([p for p in productions_analysis if p.get('consumption_type') == 'SEPARATE'])
            
            print(f"\n📊 Análisis de consumo:")
            print(f"   Consumo automático: {auto_consumptions}")
            print(f"   Consumo separado: {separate_consumptions}")
            
            findings.append({
                "type": "CONFIRMED",
                "finding": f"De {len(productions_analysis)} OFs: {auto_consumptions} automático, {separate_consumptions} separado",
                "impact": "El consumo en MRP parece estar funcionando correctamente"
            })
            
            # 3. Verificar configuración de ubicaciones de producción
            print("\n📍 Ubicaciones de consumo en producciones:")
            src_locations = defaultdict(int)
            for p in productions_analysis:
                src_locations[p.get('location_src', 'N/A')] += 1
            
            for loc, count in sorted(src_locations.items(), key=lambda x: -x[1]):
                print(f"   {loc}: {count} producciones")
            
            self.validations["A2_mrp_consumption_flow"]["status"] = "completed"
            self.validations["A2_mrp_consumption_flow"]["findings"] = findings
            self.results["mrp_analysis"] = {
                "bom_consumption_modes": dict(consumption_modes),
                "productions_analysis": productions_analysis[:20],
                "src_locations": dict(src_locations)
            }
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.validations["A2_mrp_consumption_flow"]["status"] = "error"

    # ========================================================================
    # FASE A3: CLASIFICACIÓN POR FAMILIAS DE PRODUCTOS
    # ========================================================================
    
    def classify_by_product_families(self):
        """Clasificar el problema por familias de productos"""
        print("\n" + "=" * 80)
        print("FASE A3: CLASIFICACIÓN POR FAMILIAS DE PRODUCTOS")
        print("=" * 80)
        
        findings = []
        
        try:
            # Obtener categorías de productos
            categories = self.search_read(
                'product.category',
                [],
                ['id', 'name', 'complete_name', 'parent_id',
                 'property_cost_method', 'property_valuation']
            )
            
            print(f"\nCategorías de productos: {len(categories)}")
            
            # Clasificar quants negativos por categoría
            negative_quants = self.search_read(
                'stock.quant',
                [('quantity', '<', 0)],
                ['product_id', 'location_id', 'quantity'],
                limit=2000
            )
            
            print(f"Quants negativos a clasificar: {len(negative_quants)}")
            
            # Obtener info de productos
            product_ids = list(set([q['product_id'][0] for q in negative_quants if q.get('product_id')]))
            
            products_info = {}
            if product_ids:
                products = self.search_read(
                    'product.product',
                    [('id', 'in', product_ids)],
                    ['id', 'name', 'default_code', 'categ_id', 'type',
                     'standard_price', 'qty_available']
                )
                products_info = {p['id']: p for p in products}
            
            # Clasificar por familia basado en código y categoría
            families = {
                'INSUMOS_EMPAQUE': {'codes': ['500'], 'keywords': ['bolsa', 'caja', 'etiqueta', 'film', 'cinta'], 'quants': [], 'total_neg': 0, 'total_value': 0},
                'QUIMICOS': {'codes': [], 'keywords': ['quimico', 'foamchlor', 'cloro', 'detergente'], 'quants': [], 'total_neg': 0, 'total_value': 0},
                'MATERIAS_PRIMAS': {'codes': ['1001', '1002', '300', '400'], 'keywords': ['materia', 'fruta', 'bins'], 'quants': [], 'total_neg': 0, 'total_value': 0},
                'PRODUCTO_PROCESO': {'codes': ['101', '102', '103', '104', '201', '202', '203', '204'], 'keywords': ['proceso', 'bandeja', 'iqf', 'psp', 'block'], 'quants': [], 'total_neg': 0, 'total_value': 0},
                'PRODUCTO_TERMINADO': {'codes': ['301', '302', '401', '402', '601', '602'], 'keywords': ['caja', 'retail', 'kg en'], 'quants': [], 'total_neg': 0, 'total_value': 0},
                'BANDEJAS_RETORNABLES': {'codes': [], 'keywords': ['bandeja', 'bandejon', 'pallet', 'bin', 'productor'], 'quants': [], 'total_neg': 0, 'total_value': 0},
                'OTROS': {'codes': [], 'keywords': [], 'quants': [], 'total_neg': 0, 'total_value': 0}
            }
            
            for q in negative_quants:
                prod_id = q['product_id'][0] if q.get('product_id') else None
                prod_name = q['product_id'][1] if q.get('product_id') else 'N/A'
                qty = q.get('quantity', 0)
                
                prod_info = products_info.get(prod_id, {})
                code = prod_info.get('default_code', '') or ''
                name_lower = prod_name.lower()
                price = prod_info.get('standard_price', 0) or 0
                value = abs(qty) * price
                
                classified = False
                
                # Clasificar por código primero
                for family, config in families.items():
                    if family == 'OTROS':
                        continue
                    for prefix in config['codes']:
                        if code.startswith(prefix):
                            config['quants'].append(q)
                            config['total_neg'] += qty
                            config['total_value'] += value
                            classified = True
                            break
                    if classified:
                        break
                
                # Si no se clasificó por código, intentar por keyword
                if not classified:
                    for family, config in families.items():
                        if family == 'OTROS':
                            continue
                        for kw in config['keywords']:
                            if kw in name_lower:
                                config['quants'].append(q)
                                config['total_neg'] += qty
                                config['total_value'] += value
                                classified = True
                                break
                        if classified:
                            break
                
                # Si aún no se clasificó, va a OTROS
                if not classified:
                    families['OTROS']['quants'].append(q)
                    families['OTROS']['total_neg'] += qty
                    families['OTROS']['total_value'] += value
            
            print("\n📊 CLASIFICACIÓN POR FAMILIAS:")
            print("-" * 80)
            
            for family, data in sorted(families.items(), key=lambda x: x[1]['total_neg']):
                if data['quants']:
                    print(f"\n🏷️ {family}")
                    print(f"   Quants negativos: {len(data['quants'])}")
                    print(f"   Cantidad negativa total: {data['total_neg']:,.2f}")
                    print(f"   Valor estimado afectado: ${data['total_value']:,.0f}")
                    
                    findings.append({
                        "type": "CONFIRMED",
                        "finding": f"Familia {family}: {len(data['quants'])} quants, {data['total_neg']:,.0f} uds negativas",
                        "value_impact": data['total_value'],
                        "priority": "ALTA" if data['total_value'] > 1000000 else "MEDIA" if data['total_value'] > 100000 else "BAJA"
                    })
                    
                    # Top 5 productos de esta familia
                    prod_sums = defaultdict(float)
                    for qu in data['quants']:
                        prod_name = qu['product_id'][1] if qu.get('product_id') else 'N/A'
                        prod_sums[prod_name] += qu['quantity']
                    
                    print(f"   Top 5 productos:")
                    for prod, qty in sorted(prod_sums.items(), key=lambda x: x[1])[:5]:
                        print(f"      {prod[:50]}: {qty:,.2f}")
            
            self.validations["A3_product_families"]["status"] = "completed"
            self.validations["A3_product_families"]["findings"] = findings
            self.results["family_classification"] = {
                family: {
                    "count": len(data['quants']),
                    "total_neg": data['total_neg'],
                    "total_value": data['total_value']
                }
                for family, data in families.items()
            }
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.validations["A3_product_families"]["status"] = "error"

    # ========================================================================
    # FASE A4: VALIDACIÓN ORIGEN NEGATIVOS EN VENDORS
    # ========================================================================
    
    def validate_vendor_negatives_origin(self):
        """Validar origen de negativos en Partners/Vendors"""
        print("\n" + "=" * 80)
        print("FASE A4: VALIDACIÓN ORIGEN NEGATIVOS EN PARTNERS/VENDORS")
        print("=" * 80)
        
        findings = []
        
        try:
            # Obtener ubicación vendor
            vendor_loc = self.search_read(
                'stock.location',
                [('usage', '=', 'supplier')],
                ['id', 'name', 'complete_name']
            )
            
            if not vendor_loc:
                print("No se encontró ubicación de tipo supplier")
                return
            
            vendor_id = vendor_loc[0]['id']
            print(f"\nUbicación vendor: {vendor_loc[0]['complete_name']} (ID: {vendor_id})")
            
            # Obtener quants negativos en vendor
            vendor_neg_quants = self.search_read(
                'stock.quant',
                [('location_id', '=', vendor_id), ('quantity', '<', 0)],
                ['product_id', 'quantity'],
                limit=500
            )
            
            print(f"Quants negativos en vendor: {len(vendor_neg_quants)}")
            
            # Para cada producto afectado, analizar historial de movimientos
            affected_products = {}
            for q in vendor_neg_quants:
                prod_id = q['product_id'][0]
                prod_name = q['product_id'][1]
                if prod_id not in affected_products:
                    affected_products[prod_id] = {
                        'name': prod_name,
                        'negative_qty': 0
                    }
                affected_products[prod_id]['negative_qty'] += q['quantity']
            
            print(f"\nAnalizando {len(affected_products)} productos afectados...")
            
            # Analizar top 10 productos más negativos
            top_negative = sorted(affected_products.items(), key=lambda x: x[1]['negative_qty'])[:10]
            
            origin_analysis = {
                'recepciones_incompletas': 0,
                'devoluciones_mal_ejecutadas': 0,
                'cancelaciones_posteriores': 0,
                'backdating': 0,
                'rutas_defectuosas': 0,
                'otros': 0
            }
            
            for prod_id, info in top_negative:
                print(f"\n🔍 Analizando: {info['name'][:50]}")
                print(f"   Stock negativo en vendor: {info['negative_qty']:,.2f}")
                
                # Obtener movimientos de este producto desde/hacia vendor
                moves_from_vendor = self.search_read(
                    'stock.move',
                    [('product_id', '=', prod_id), 
                     ('location_id', '=', vendor_id),
                     ('state', '=', 'done')],
                    ['id', 'name', 'quantity_done', 'date', 'reference', 
                     'origin', 'picking_id', 'location_dest_id'],
                    limit=50
                )
                
                moves_to_vendor = self.search_read(
                    'stock.move',
                    [('product_id', '=', prod_id), 
                     ('location_dest_id', '=', vendor_id),
                     ('state', '=', 'done')],
                    ['id', 'name', 'quantity_done', 'date', 'reference',
                     'origin', 'picking_id', 'location_id'],
                    limit=50
                )
                
                total_from_vendor = sum(m.get('quantity_done', 0) for m in moves_from_vendor)
                total_to_vendor = sum(m.get('quantity_done', 0) for m in moves_to_vendor)
                
                print(f"   Movimientos desde vendor (recepciones): {len(moves_from_vendor)}, Total: {total_from_vendor:,.2f}")
                print(f"   Movimientos hacia vendor (devoluciones): {len(moves_to_vendor)}, Total: {total_to_vendor:,.2f}")
                print(f"   Balance calculado: {total_from_vendor - total_to_vendor:,.2f}")
                
                # Analizar origen del problema
                # Si hay más salidas desde vendor que entradas, hay recepciones fantasma
                if total_from_vendor > abs(info['negative_qty']) * 2:
                    print(f"   ⚠️ Posible: Recepciones ejecutadas sin stock disponible")
                    origin_analysis['recepciones_incompletas'] += 1
                
                # Verificar si hay devoluciones
                if moves_to_vendor:
                    print(f"   ⚠️ Hay {len(moves_to_vendor)} devoluciones a proveedor")
                    # Verificar si las devoluciones tienen origen coherente
                    devol_origins = [m.get('origin', '') for m in moves_to_vendor]
                    returns = [o for o in devol_origins if 'return' in str(o).lower() or 'dev' in str(o).lower()]
                    if returns:
                        origin_analysis['devoluciones_mal_ejecutadas'] += 1
                
                # Verificar cancelaciones
                cancelled_pickings = self.search_count(
                    'stock.picking',
                    [('product_id', '=', prod_id), ('state', '=', 'cancel')]
                )
                if cancelled_pickings > 0:
                    print(f"   ⚠️ {cancelled_pickings} pickings cancelados para este producto")
                    origin_analysis['cancelaciones_posteriores'] += 1
            
            print("\n📊 RESUMEN DE CAUSAS DETECTADAS:")
            for causa, count in origin_analysis.items():
                if count > 0:
                    print(f"   {causa}: {count} productos")
                    findings.append({
                        "type": "PROBABLE",
                        "finding": f"Causa '{causa}': afecta {count} productos",
                        "impact": "Requiere investigación detallada"
                    })
            
            findings.append({
                "type": "CONFIRMED",
                "finding": f"Stock negativo en vendor afecta {len(affected_products)} productos",
                "impact": "CRÍTICO - Indica recepciones sin compra o devoluciones incorrectas"
            })
            
            self.validations["A4_vendor_negatives_origin"]["status"] = "completed"
            self.validations["A4_vendor_negatives_origin"]["findings"] = findings
            self.results["vendor_analysis"] = {
                "affected_products": len(affected_products),
                "origin_causes": origin_analysis,
                "top_negative_products": [
                    {"id": pid, "name": info['name'], "qty": info['negative_qty']}
                    for pid, info in top_negative
                ]
            }
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.validations["A4_vendor_negatives_origin"]["status"] = "error"

    # ========================================================================
    # FASE D: IMPACTO CONTABLE Y VALORIZACIÓN
    # ========================================================================
    
    def analyze_accounting_impact(self):
        """Cuantificar impacto contable y de valorización"""
        print("\n" + "=" * 80)
        print("FASE D: IMPACTO CONTABLE Y VALORIZACIÓN")
        print("=" * 80)
        
        findings = []
        
        try:
            # 1. Obtener configuración de valorización por categoría
            categories = self.search_read(
                'product.category',
                [],
                ['id', 'name', 'complete_name', 'property_cost_method', 
                 'property_valuation', 'property_stock_account_input_categ_id',
                 'property_stock_account_output_categ_id',
                 'property_stock_valuation_account_id']
            )
            
            print("\n📊 Configuración de valorización por categoría:")
            valuation_config = {}
            for cat in categories:
                valuation = cat.get('property_valuation', 'N/A')
                cost_method = cat.get('property_cost_method', 'N/A')
                if valuation or cost_method:
                    valuation_config[cat['complete_name']] = {
                        'valuation': valuation,
                        'cost_method': cost_method,
                        'input_account': cat.get('property_stock_account_input_categ_id'),
                        'output_account': cat.get('property_stock_account_output_categ_id'),
                        'valuation_account': cat.get('property_stock_valuation_account_id')
                    }
                    print(f"   {cat['complete_name']}: {valuation}, {cost_method}")
            
            # 2. Obtener productos con stock negativo y su valoración
            print("\n💰 Calculando impacto monetario...")
            
            negative_quants = self.search_read(
                'stock.quant',
                [('quantity', '<', 0)],
                ['product_id', 'quantity', 'location_id'],
                limit=2000
            )
            
            product_ids = list(set([q['product_id'][0] for q in negative_quants if q.get('product_id')]))
            
            products_valuation = {}
            if product_ids:
                products = self.search_read(
                    'product.product',
                    [('id', 'in', product_ids)],
                    ['id', 'name', 'default_code', 'standard_price', 
                     'categ_id', 'qty_available']
                )
                products_valuation = {p['id']: p for p in products}
            
            # Calcular impacto por producto
            impact_by_product = []
            total_negative_value = 0
            
            product_impacts = defaultdict(lambda: {'qty': 0, 'value': 0, 'price': 0})
            
            for q in negative_quants:
                prod_id = q['product_id'][0] if q.get('product_id') else None
                qty = q.get('quantity', 0)
                
                if prod_id in products_valuation:
                    prod = products_valuation[prod_id]
                    price = prod.get('standard_price', 0) or 0
                    value = abs(qty) * price
                    
                    product_impacts[prod_id]['qty'] += qty
                    product_impacts[prod_id]['value'] += value
                    product_impacts[prod_id]['price'] = price
                    product_impacts[prod_id]['name'] = prod.get('name', 'N/A')
                    product_impacts[prod_id]['code'] = prod.get('default_code', '')
                    product_impacts[prod_id]['categ'] = prod.get('categ_id', [0, 'N/A'])[1]
                    
                    total_negative_value += value
            
            # Top productos por impacto monetario
            top_by_value = sorted(product_impacts.items(), key=lambda x: -x[1]['value'])[:20]
            
            print(f"\n💵 TOP 20 PRODUCTOS POR IMPACTO MONETARIO:")
            print("-" * 80)
            
            for prod_id, data in top_by_value:
                print(f"\n   [{data.get('code', 'N/A')}] {data['name'][:50]}")
                print(f"   Categoría: {data.get('categ', 'N/A')}")
                print(f"   Stock negativo: {data['qty']:,.2f} uds")
                print(f"   Precio estándar: ${data['price']:,.2f}")
                print(f"   Impacto valorización: ${data['value']:,.0f}")
                
                findings.append({
                    "type": "CONFIRMED",
                    "product_id": prod_id,
                    "product_name": data['name'],
                    "negative_qty": data['qty'],
                    "value_impact": data['value'],
                    "priority": "CRÍTICA" if data['value'] > 10000000 else "ALTA" if data['value'] > 1000000 else "MEDIA"
                })
            
            print(f"\n" + "=" * 80)
            print(f"IMPACTO TOTAL ESTIMADO: ${total_negative_value:,.0f}")
            print("=" * 80)
            
            # 3. Verificar stock.valuation.layer
            print("\n📈 Analizando stock.valuation.layer...")
            
            try:
                # Capas con cantidad restante negativa
                negative_layers = self.search_read(
                    'stock.valuation.layer',
                    [('remaining_qty', '<', 0)],
                    ['product_id', 'quantity', 'remaining_qty', 'value', 
                     'remaining_value', 'unit_cost'],
                    limit=100
                )
                
                print(f"Capas de valoración con cantidad negativa: {len(negative_layers)}")
                
                layers_impact = sum(abs(l.get('remaining_value', 0)) for l in negative_layers)
                print(f"Valor en capas negativas: ${layers_impact:,.0f}")
                
                findings.append({
                    "type": "CONFIRMED",
                    "finding": f"{len(negative_layers)} capas de valoración con remaining_qty < 0",
                    "value_impact": layers_impact,
                    "impact": "Afecta cálculo de costo promedio"
                })
                
            except Exception as e:
                print(f"   ⚠️ No se pudo analizar stock.valuation.layer: {e}")
            
            # 4. Cuentas contables comprometidas
            print("\n📒 Cuentas contables potencialmente afectadas:")
            accounts_affected = set()
            for cat_name, config in valuation_config.items():
                if config.get('valuation_account'):
                    accounts_affected.add(str(config['valuation_account']))
                if config.get('input_account'):
                    accounts_affected.add(str(config['input_account']))
                if config.get('output_account'):
                    accounts_affected.add(str(config['output_account']))
            
            for acc in list(accounts_affected)[:10]:
                print(f"   - {acc}")
            
            self.validations["D_accounting_impact"]["status"] = "completed"
            self.validations["D_accounting_impact"]["findings"] = findings
            self.results["accounting_impact"] = {
                "total_negative_value": total_negative_value,
                "top_products_by_value": [
                    {
                        "id": pid,
                        "name": data['name'],
                        "code": data.get('code'),
                        "qty": data['qty'],
                        "price": data['price'],
                        "value": data['value']
                    }
                    for pid, data in top_by_value
                ],
                "negative_layers_count": len(negative_layers) if 'negative_layers' in dir() else 0,
                "valuation_config": valuation_config
            }
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            self.validations["D_accounting_impact"]["status"] = "error"

    # ========================================================================
    # ANÁLISIS RF INSUMOS ESPECÍFICO
    # ========================================================================
    
    def analyze_rf_insumos_detail(self):
        """Análisis detallado de RF INSUMOS para plan de regularización"""
        print("\n" + "=" * 80)
        print("ANÁLISIS DETALLADO RF INSUMOS")
        print("=" * 80)
        
        findings = []
        
        try:
            # Buscar ubicación RF INSUMOS
            rf_insumos_locs = self.search_read(
                'stock.location',
                [('complete_name', 'ilike', 'RF/Insumos')],
                ['id', 'name', 'complete_name', 'usage', 'location_id'],
                limit=100
            )
            
            print(f"\nUbicaciones RF/Insumos encontradas: {len(rf_insumos_locs)}")
            
            rf_insumos_ids = [l['id'] for l in rf_insumos_locs]
            
            # Obtener quants en estas ubicaciones
            quants_insumos = self.search_read(
                'stock.quant',
                [('location_id', 'in', rf_insumos_ids)],
                ['product_id', 'location_id', 'quantity', 'reserved_quantity'],
                limit=1000
            )
            
            print(f"Quants en RF/Insumos: {len(quants_insumos)}")
            
            # Clasificar por estado
            positive = [q for q in quants_insumos if q.get('quantity', 0) > 0]
            negative = [q for q in quants_insumos if q.get('quantity', 0) < 0]
            zero = [q for q in quants_insumos if q.get('quantity', 0) == 0]
            
            print(f"\n   Positivos: {len(positive)}")
            print(f"   Negativos: {len(negative)}")
            print(f"   Cero: {len(zero)}")
            
            total_positive = sum(q['quantity'] for q in positive)
            total_negative = sum(q['quantity'] for q in negative)
            
            print(f"\n   Stock positivo total: {total_positive:,.2f}")
            print(f"   Stock negativo total: {total_negative:,.2f}")
            
            # Productos únicos
            products_in_insumos = set()
            for q in quants_insumos:
                if q.get('product_id'):
                    products_in_insumos.add(q['product_id'][0])
            
            print(f"\n   Productos únicos en RF/Insumos: {len(products_in_insumos)}")
            
            # Desglose por sub-ubicación
            print("\n📍 Desglose por sub-ubicación:")
            by_subloc = defaultdict(lambda: {'pos': 0, 'neg': 0, 'count': 0})
            
            for q in quants_insumos:
                loc = q['location_id'][1] if q.get('location_id') else 'N/A'
                qty = q.get('quantity', 0)
                by_subloc[loc]['count'] += 1
                if qty > 0:
                    by_subloc[loc]['pos'] += qty
                else:
                    by_subloc[loc]['neg'] += qty
            
            for loc, data in sorted(by_subloc.items(), key=lambda x: x[1]['neg']):
                if data['neg'] < 0 or data['pos'] > 0:
                    print(f"   {loc[:50]}")
                    print(f"      + {data['pos']:,.2f}  - {data['neg']:,.2f}  ({data['count']} quants)")
            
            findings.append({
                "type": "CONFIRMED",
                "finding": f"RF/Insumos tiene {len(negative)} quants negativos sumando {total_negative:,.0f} uds",
                "products_affected": len(products_in_insumos),
                "sublocations": len(by_subloc)
            })
            
            self.results["rf_insumos_detail"] = {
                "locations": rf_insumos_locs,
                "total_quants": len(quants_insumos),
                "positive_quants": len(positive),
                "negative_quants": len(negative),
                "total_positive": total_positive,
                "total_negative": total_negative,
                "unique_products": len(products_in_insumos),
                "by_sublocation": dict(by_subloc)
            }
            
            self.validations["C_rf_insumos_plan"]["findings"] = findings
            
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()

    # ========================================================================
    # GENERACIÓN DE RESUMEN
    # ========================================================================
    
    def generate_validation_summary(self):
        """Genera resumen de validaciones"""
        print("\n" + "=" * 80)
        print("RESUMEN DE VALIDACIONES")
        print("=" * 80)
        
        for phase, data in self.validations.items():
            status = data.get('status', 'pending')
            findings = data.get('findings', [])
            
            status_icon = "✅" if status == "completed" else "⚠️" if status == "error" else "⏳"
            print(f"\n{status_icon} {phase}: {status}")
            
            if findings:
                confirmed = [f for f in findings if f.get('type') == 'CONFIRMED']
                probable = [f for f in findings if f.get('type') == 'PROBABLE']
                pending = [f for f in findings if f.get('type') == 'PENDING']
                
                print(f"   Hallazgos confirmados: {len(confirmed)}")
                print(f"   Hallazgos probables: {len(probable)}")
                print(f"   Hallazgos pendientes: {len(pending)}")
        
        return self.validations
    
    def save_results(self, filename: str = "validation_results.json"):
        """Guarda resultados"""
        def clean(obj):
            if isinstance(obj, dict):
                return {k: clean(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean(i) for i in obj]
            elif isinstance(obj, defaultdict):
                return dict(obj)
            elif isinstance(obj, set):
                return list(obj)
            else:
                return obj
        
        output = {
            "timestamp": datetime.now().isoformat(),
            "validations": self.validations,
            "results": clean(self.results)
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n✓ Resultados guardados en: {filename}")
    
    def run_all_validations(self):
        """Ejecuta todas las validaciones"""
        if not self.connect():
            return False
        
        print("\n" + "=" * 80)
        print("INICIANDO VALIDACIONES TÉCNICAS PARA PLAN DE REGULARIZACIÓN")
        print("=" * 80)
        
        # FASE A: Validaciones críticas
        self.validate_consumo_operation()
        self.validate_mrp_consumption_flow()
        self.classify_by_product_families()
        self.validate_vendor_negatives_origin()
        
        # FASE D: Impacto contable
        self.analyze_accounting_impact()
        
        # Análisis específico RF INSUMOS
        self.analyze_rf_insumos_detail()
        
        # Resumen
        self.generate_validation_summary()
        
        return True


if __name__ == "__main__":
    validator = ValidationAuditor(URL, DB, USERNAME, PASSWORD)
    
    if validator.run_all_validations():
        validator.save_results()
        print("\n" + "=" * 80)
        print("VALIDACIONES COMPLETADAS")
        print("=" * 80)

"""
Auditoría Profunda - Análisis de Causa Raíz
=============================================
Script de diagnóstico detallado para encontrar la causa raíz
del problema de stock negativo y consumos duplicados.

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

class DeepAnalyzer:
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.common = None
        self.models = None
        self.results = {}
    
    def connect(self) -> bool:
        """Establece conexión con Odoo vía XML-RPC"""
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
    # ANÁLISIS RF INSUMOS
    # ========================================================================
    
    def find_rf_insumos(self):
        """Busca todas las ubicaciones relacionadas con RF INSUMOS o insumos"""
        print("\n" + "=" * 70)
        print("BUSCANDO UBICACIONES RF INSUMOS Y RELACIONADAS")
        print("=" * 70)
        
        # Buscar por múltiples patrones
        patterns = ['insumos', 'rf insumos', 'INSUMOS', 'bodega insumos']
        all_matches = []
        
        for pattern in patterns:
            matches = self.search_read(
                'stock.location',
                [('complete_name', 'ilike', pattern)],
                ['id', 'name', 'complete_name', 'usage', 'location_id', 'active']
            )
            all_matches.extend(matches)
        
        # Eliminar duplicados
        seen_ids = set()
        unique_matches = []
        for m in all_matches:
            if m['id'] not in seen_ids:
                seen_ids.add(m['id'])
                unique_matches.append(m)
        
        print(f"\nUbicaciones encontradas con 'insumos': {len(unique_matches)}")
        for loc in unique_matches:
            print(f"  [{loc['id']}] {loc.get('complete_name')} ({loc.get('usage')})")
        
        # También buscar almacenes/warehouses
        warehouses = self.search_read(
            'stock.warehouse',
            [],
            ['id', 'name', 'code', 'lot_stock_id', 'company_id']
        )
        
        print(f"\nAlmacenes: {len(warehouses)}")
        for wh in warehouses:
            print(f"  [{wh['id']}] {wh.get('name')} (Código: {wh.get('code')})")
            print(f"       Ubicación stock: {wh.get('lot_stock_id')}")
        
        self.results["rf_insumos_locations"] = unique_matches
        self.results["warehouses"] = warehouses
        
        return unique_matches
    
    # ========================================================================
    # ANÁLISIS DE CONSUMOS CRÍTICOS
    # ========================================================================
    
    def analyze_stock_by_location_type(self):
        """Analiza stock negativo por tipo de ubicación"""
        print("\n" + "=" * 70)
        print("ANÁLISIS DE STOCK NEGATIVO POR TIPO DE UBICACIÓN")
        print("=" * 70)
        
        # Obtener quants negativos con detalles de ubicación
        negative_quants = self.search_read(
            'stock.quant',
            [('quantity', '<', 0)],
            ['id', 'product_id', 'location_id', 'quantity', 
             'reserved_quantity', 'company_id'],
            order='quantity asc',
            limit=2000
        )
        
        print(f"Total quants negativos: {len(negative_quants)}")
        
        # Agrupar por ubicación padre
        location_groups = defaultdict(lambda: {'count': 0, 'total_qty': 0, 'products': []})
        
        for q in negative_quants:
            loc_name = q['location_id'][1] if q.get('location_id') else 'Unknown'
            location_groups[loc_name]['count'] += 1
            location_groups[loc_name]['total_qty'] += q['quantity']
            if len(location_groups[loc_name]['products']) < 5:
                location_groups[loc_name]['products'].append({
                    'product': q['product_id'][1] if q.get('product_id') else 'N/A',
                    'qty': q['quantity']
                })
        
        print("\nStock negativo por ubicación:")
        for loc, data in sorted(location_groups.items(), key=lambda x: x[1]['total_qty']):
            print(f"\n📍 {loc}")
            print(f"   Quants negativos: {data['count']}")
            print(f"   Cantidad total negativa: {data['total_qty']:,.2f}")
            if data['products']:
                print("   Ejemplos:")
                for p in data['products']:
                    print(f"     - {p['product']}: {p['qty']:,.2f}")
        
        self.results["stock_by_location"] = dict(location_groups)
        return location_groups
    
    def analyze_partners_vendors_issue(self):
        """Analiza el problema específico de 'Partners/Vendors' con stock negativo"""
        print("\n" + "=" * 70)
        print("ANÁLISIS UBICACIÓN 'Partners/Vendors'")
        print("=" * 70)
        
        # Buscar la ubicación Partners/Vendors
        vendor_locs = self.search_read(
            'stock.location',
            [('name', 'ilike', 'vendor')],
            ['id', 'name', 'complete_name', 'usage', 'location_id']
        )
        
        print(f"\nUbicaciones tipo Vendor: {len(vendor_locs)}")
        for loc in vendor_locs:
            print(f"  [{loc['id']}] {loc.get('complete_name')} - usage: {loc.get('usage')}")
        
        # Esta ubicación en Odoo es una ubicación VIRTUAL de tipo 'supplier'
        # NO debería tener stock negativo nunca - es la representación de los proveedores
        # Si hay stock negativo aquí, significa que:
        # 1. Se hicieron recepciones sin la compra
        # 2. Se cancelaron recepciones mal
        # 3. Hay errores en el flujo de compras
        
        if vendor_locs:
            vendor_id = vendor_locs[0]['id']
            
            # Obtener quants en esa ubicación
            vendor_quants = self.search_read(
                'stock.quant',
                [('location_id', '=', vendor_id)],
                ['id', 'product_id', 'quantity'],
                limit=100
            )
            
            print(f"\nQuants en ubicación vendor: {len(vendor_quants)}")
            neg_total = sum(q['quantity'] for q in vendor_quants if q['quantity'] < 0)
            print(f"Total cantidad negativa en vendor: {neg_total:,.2f}")
            
            # Esto es CRÍTICO - No debería haber quants negativos en vendor
            # Indica que se están haciendo recepciones "del aire"
            
        self.results["vendor_location_analysis"] = vendor_locs
    
    def analyze_vlk_location(self):
        """Analiza la ubicación VLK mencionada en los resultados"""
        print("\n" + "=" * 70)
        print("ANÁLISIS UBICACIÓN VLK")
        print("=" * 70)
        
        vlk_locs = self.search_read(
            'stock.location',
            [('complete_name', 'ilike', 'VLK')],
            ['id', 'name', 'complete_name', 'usage', 'location_id', 'company_id']
        )
        
        print(f"\nUbicaciones VLK: {len(vlk_locs)}")
        for loc in vlk_locs:
            print(f"  [{loc['id']}] {loc.get('complete_name')} ({loc.get('usage')})")
            
            # Obtener quants
            quants = self.search_read(
                'stock.quant',
                [('location_id', '=', loc['id']), ('quantity', '!=', 0)],
                ['product_id', 'quantity'],
                limit=50
            )
            neg_count = len([q for q in quants if q['quantity'] < 0])
            pos_count = len([q for q in quants if q['quantity'] > 0])
            print(f"       Quants: {len(quants)} (+ {pos_count}, - {neg_count})")
        
        self.results["vlk_locations"] = vlk_locs
    
    def analyze_production_consumption_flow(self):
        """Analiza el flujo de consumo en producción"""
        print("\n" + "=" * 70)
        print("ANÁLISIS DE FLUJO DE CONSUMO EN PRODUCCIÓN")
        print("=" * 70)
        
        # Obtener producciones recientes terminadas
        productions = self.search_read(
            'mrp.production',
            [('state', '=', 'done')],
            ['id', 'name', 'product_id', 'product_qty', 'qty_producing',
             'date_finished', 'bom_id', 'user_id', 'origin',
             'location_src_id', 'location_dest_id'],
            limit=100,
            order='date_finished desc'
        )
        
        print(f"Producciones terminadas (último 100): {len(productions)}")
        
        analysis = []
        
        for prod in productions[:30]:
            prod_id = prod['id']
            
            # Movimientos de consumo (materia prima)
            raw_moves = self.search_read(
                'stock.move',
                [('raw_material_production_id', '=', prod_id),
                 ('state', '=', 'done')],
                ['product_id', 'product_uom_qty', 'quantity_done',
                 'location_id', 'location_dest_id', 'create_uid', 'date']
            )
            
            # Movimientos de producción (producto terminado)
            finished_moves = self.search_read(
                'stock.move',
                [('production_id', '=', prod_id),
                 ('state', '=', 'done')],
                ['product_id', 'product_uom_qty', 'quantity_done']
            )
            
            # Detectar problemas
            issues = []
            
            # 1. Consumos con cantidad diferente a la demanda
            for rm in raw_moves:
                if rm.get('product_uom_qty') and rm.get('quantity_done'):
                    diff = abs(rm['product_uom_qty'] - rm['quantity_done'])
                    if diff > 0.01:
                        issues.append(f"Consumo difiere: Demanda {rm['product_uom_qty']:.2f} vs Real {rm['quantity_done']:.2f}")
            
            # 2. Verificar ubicación origen de consumo
            src_locs = set()
            for rm in raw_moves:
                src_locs.add(rm['location_id'][1] if rm.get('location_id') else 'Unknown')
            
            if len(src_locs) > 1:
                issues.append(f"Consumo desde múltiples ubicaciones: {src_locs}")
            
            prod_analysis = {
                'production': prod['name'],
                'date': prod.get('date_finished'),
                'product': prod['product_id'][1] if prod.get('product_id') else 'N/A',
                'qty': prod.get('product_qty'),
                'raw_moves_count': len(raw_moves),
                'finished_moves_count': len(finished_moves),
                'source_locations': list(src_locs),
                'issues': issues
            }
            
            if issues:
                print(f"\n⚠️ {prod['name']}")
                print(f"   Producto: {prod_analysis['product']}")
                print(f"   Issues:")
                for issue in issues:
                    print(f"     - {issue}")
            
            analysis.append(prod_analysis)
        
        self.results["production_analysis"] = analysis
    
    def analyze_manual_moves_patterns(self):
        """Analiza patrones de movimientos manuales"""
        print("\n" + "=" * 70)
        print("ANÁLISIS DE MOVIMIENTOS MANUALES/SIN ORIGEN")
        print("=" * 70)
        
        # Movimientos done sin picking_id y sin production relacionada
        manual_moves = self.search_read(
            'stock.move',
            [('state', '=', 'done'),
             ('picking_id', '=', False),
             ('raw_material_production_id', '=', False),
             ('production_id', '=', False)],
            ['id', 'product_id', 'product_uom_qty', 'quantity_done',
             'location_id', 'location_dest_id', 'reference', 'origin',
             'create_uid', 'date', 'company_id'],
            limit=500,
            order='date desc'
        )
        
        print(f"Movimientos manuales/especiales: {len(manual_moves)}")
        
        # Agrupar por tipo de movimiento (basado en ubicaciones)
        move_types = defaultdict(list)
        users_manual = defaultdict(int)
        
        for m in manual_moves:
            src = m.get('location_id', [0, 'Unknown'])[1]
            dest = m.get('location_dest_id', [0, 'Unknown'])[1]
            user = m.get('create_uid', [0, 'Sistema'])[1]
            
            flow_type = f"{src} → {dest}"
            move_types[flow_type].append(m)
            users_manual[user] += 1
        
        print("\nPatrones de flujo (sin picking):")
        for flow, moves in sorted(move_types.items(), key=lambda x: -len(x[1]))[:20]:
            print(f"  {flow}: {len(moves)} movimientos")
        
        print("\nUsuarios con más movimientos manuales:")
        for user, count in sorted(users_manual.items(), key=lambda x: -x[1])[:10]:
            print(f"  {user}: {count}")
        
        # Detectar movimientos sospechosos
        print("\nMovimientos sospechosos (hacia ubicación virtual/producción sin OP):")
        suspicious = []
        for m in manual_moves:
            dest = m.get('location_dest_id', [0, ''])[1].lower()
            src = m.get('location_id', [0, ''])[1].lower()
            
            # Movimientos desde interno hacia producción/virtual sin OP
            if 'producción' in dest or 'production' in dest or 'virtual' in dest:
                suspicious.append(m)
            elif 'virtual' in src or 'vendor' in src.lower():
                suspicious.append(m)
        
        print(f"  Encontrados: {len(suspicious)}")
        for s in suspicious[:10]:
            print(f"    [{s['id']}] {s['product_id'][1][:40] if s.get('product_id') else 'N/A'}")
            print(f"        {s.get('location_id', [0, ''])[1]} → {s.get('location_dest_id', [0, ''])[1]}")
            print(f"        Qty: {s.get('quantity_done')}, User: {s.get('create_uid', [0, 'N/A'])[1]}")
        
        self.results["manual_moves"] = {
            "total": len(manual_moves),
            "flow_types": {k: len(v) for k, v in move_types.items()},
            "users": dict(users_manual),
            "suspicious_count": len(suspicious)
        }
    
    def analyze_inventory_adjustments_detail(self):
        """Analiza ajustes de inventario en detalle"""
        print("\n" + "=" * 70)
        print("ANÁLISIS DETALLADO DE AJUSTES DE INVENTARIO")
        print("=" * 70)
        
        # Buscar ubicaciones de ajuste
        adj_locs = self.search_read(
            'stock.location',
            [('usage', '=', 'inventory')],
            ['id', 'name', 'complete_name']
        )
        
        if not adj_locs:
            print("No se encontraron ubicaciones de ajuste de inventario")
            return
        
        adj_loc_ids = [l['id'] for l in adj_locs]
        print(f"Ubicaciones de ajuste: {[l['complete_name'] for l in adj_locs]}")
        
        # Movimientos desde ajuste (entradas al inventario real)
        adj_in = self.search_read(
            'stock.move',
            [('location_id', 'in', adj_loc_ids), ('state', '=', 'done')],
            ['id', 'product_id', 'quantity_done', 'location_dest_id',
             'create_uid', 'date', 'reference', 'origin'],
            limit=500,
            order='date desc'
        )
        
        # Movimientos hacia ajuste (salidas del inventario real)
        adj_out = self.search_read(
            'stock.move',
            [('location_dest_id', 'in', adj_loc_ids), ('state', '=', 'done')],
            ['id', 'product_id', 'quantity_done', 'location_id',
             'create_uid', 'date', 'reference', 'origin'],
            limit=500,
            order='date desc'
        )
        
        print(f"\nAjustes de entrada (incremento stock): {len(adj_in)}")
        print(f"Ajustes de salida (reducción stock): {len(adj_out)}")
        
        # Calcular totales por usuario
        user_adjustments = defaultdict(lambda: {'in_count': 0, 'in_qty': 0, 'out_count': 0, 'out_qty': 0})
        
        for m in adj_in:
            user = m.get('create_uid', [0, 'Sistema'])[1]
            user_adjustments[user]['in_count'] += 1
            user_adjustments[user]['in_qty'] += m.get('quantity_done', 0)
        
        for m in adj_out:
            user = m.get('create_uid', [0, 'Sistema'])[1]
            user_adjustments[user]['out_count'] += 1
            user_adjustments[user]['out_qty'] += m.get('quantity_done', 0)
        
        print("\nAjustes por usuario:")
        for user, data in sorted(user_adjustments.items(), 
                                  key=lambda x: -(x[1]['in_count'] + x[1]['out_count'])):
            net = data['in_qty'] - data['out_qty']
            print(f"\n  {user}:")
            print(f"    Entradas: {data['in_count']} movs totalizando {data['in_qty']:,.2f}")
            print(f"    Salidas: {data['out_count']} movs totalizando {data['out_qty']:,.2f}")
            print(f"    Efecto neto: {net:,.2f}")
        
        self.results["inventory_adjustments_detail"] = {
            "locations": adj_locs,
            "adjustments_in": adj_in,
            "adjustments_out": adj_out,
            "by_user": dict(user_adjustments)
        }
    
    def analyze_picking_types_usage(self):
        """Analiza uso de tipos de picking"""
        print("\n" + "=" * 70)
        print("ANÁLISIS DE TIPOS DE OPERACIÓN Y USO")
        print("=" * 70)
        
        picking_types = self.search_read(
            'stock.picking.type',
            [],
            ['id', 'name', 'code', 'warehouse_id', 'sequence_code',
             'default_location_src_id', 'default_location_dest_id']
        )
        
        print(f"Tipos de operación: {len(picking_types)}")
        
        for pt in picking_types:
            # Contar pickings de este tipo
            count = self.search_count('stock.picking', [('picking_type_id', '=', pt['id'])])
            done_count = self.search_count('stock.picking', 
                [('picking_type_id', '=', pt['id']), ('state', '=', 'done')])
            
            print(f"\n  [{pt['id']}] {pt.get('name')} ({pt.get('code')})")
            print(f"      Total pickings: {count}, Completados: {done_count}")
            print(f"      Ubicación origen: {pt.get('default_location_src_id')}")
            print(f"      Ubicación destino: {pt.get('default_location_dest_id')}")
        
        self.results["picking_types"] = picking_types
    
    def find_duplicate_consumption_evidence(self):
        """Busca evidencia específica de consumos duplicados"""
        print("\n" + "=" * 70)
        print("BÚSQUEDA DE EVIDENCIA DE CONSUMOS DUPLICADOS")
        print("=" * 70)
        
        # Estrategia: buscar productos donde la suma de consumos MRP
        # más consumos manuales excede claramente las entradas
        
        # Primero identificar productos con stock negativo más críticos
        negative_quants = self.search_read(
            'stock.quant',
            [('quantity', '<', -1000)],  # Solo los muy negativos
            ['product_id', 'quantity', 'location_id'],
            limit=100,
            order='quantity asc'
        )
        
        print(f"Productos con quants muy negativos (<-1000): {len(negative_quants)}")
        
        evidence = []
        
        for q in negative_quants[:10]:
            prod_id = q['product_id'][0]
            prod_name = q['product_id'][1]
            
            # Contar consumos MRP
            mrp_moves = self.search_count(
                'stock.move',
                [('product_id', '=', prod_id),
                 ('state', '=', 'done'),
                 ('raw_material_production_id', '!=', False)]
            )
            
            # Contar movimientos manuales de salida
            # (desde ubicaciones internas hacia producción/virtual sin OP)
            internal_locs = self.search_read(
                'stock.location',
                [('usage', '=', 'internal')],
                ['id']
            )
            internal_ids = [l['id'] for l in internal_locs]
            
            manual_out = self.search_count(
                'stock.move',
                [('product_id', '=', prod_id),
                 ('state', '=', 'done'),
                 ('location_id', 'in', internal_ids),
                 ('raw_material_production_id', '=', False),
                 ('picking_id', '=', False)]
            )
            
            # Entradas totales
            total_in = self.search_count(
                'stock.move',
                [('product_id', '=', prod_id),
                 ('state', '=', 'done'),
                 ('location_dest_id', 'in', internal_ids)]
            )
            
            print(f"\n🔍 {prod_name[:60]}")
            print(f"   Stock negativo: {q['quantity']:,.2f}")
            print(f"   Consumos MRP: {mrp_moves}")
            print(f"   Salidas manuales: {manual_out}")
            print(f"   Total entradas: {total_in}")
            
            if mrp_moves > 0 and manual_out > 0:
                print(f"   ⚠️ POSIBLE DUPLICIDAD: {mrp_moves} MRP + {manual_out} manuales")
                evidence.append({
                    'product_id': prod_id,
                    'product_name': prod_name,
                    'negative_qty': q['quantity'],
                    'mrp_consumptions': mrp_moves,
                    'manual_consumptions': manual_out,
                    'total_entries': total_in
                })
        
        self.results["duplication_evidence"] = evidence
        print(f"\n\nTotal productos con posible duplicidad: {len(evidence)}")
    
    def analyze_bom_configuration(self):
        """Analiza configuración de BOMs"""
        print("\n" + "=" * 70)
        print("ANÁLISIS DE CONFIGURACIÓN DE BOMS")
        print("=" * 70)
        
        boms = self.search_read(
            'mrp.bom',
            [('active', '=', True)],
            ['id', 'product_tmpl_id', 'product_id', 'product_qty',
             'type', 'code', 'ready_to_produce'],
            limit=100
        )
        
        print(f"BOMs activos: {len(boms)}")
        
        # Verificar BOMs con problemas potenciales
        issues = []
        
        for bom in boms[:50]:
            bom_id = bom['id']
            
            # Obtener líneas
            lines = self.search_read(
                'mrp.bom.line',
                [('bom_id', '=', bom_id)],
                ['product_id', 'product_qty', 'product_uom_id']
            )
            
            # Verificar:
            # 1. Componentes con cantidad 0 o negativa
            # 2. Productos duplicados en el mismo BOM
            
            product_counts = defaultdict(int)
            for l in lines:
                prod_id = l['product_id'][0]
                product_counts[prod_id] += 1
                
                if l.get('product_qty', 0) <= 0:
                    issues.append({
                        'bom_id': bom_id,
                        'bom_product': bom.get('product_tmpl_id', [0, 'N/A'])[1],
                        'issue': f"Componente con cantidad <= 0: {l['product_id'][1]}",
                        'qty': l.get('product_qty')
                    })
            
            for prod_id, count in product_counts.items():
                if count > 1:
                    prod_name = next((l['product_id'][1] for l in lines if l['product_id'][0] == prod_id), 'N/A')
                    issues.append({
                        'bom_id': bom_id,
                        'bom_product': bom.get('product_tmpl_id', [0, 'N/A'])[1],
                        'issue': f"Componente duplicado: {prod_name} aparece {count} veces",
                        'count': count
                    })
        
        if issues:
            print(f"\n⚠️ {len(issues)} problemas encontrados en BOMs:")
            for issue in issues[:20]:
                print(f"  BOM para {issue['bom_product'][:40]}")
                print(f"    Issue: {issue['issue']}")
        else:
            print("\nNo se encontraron problemas en la configuración de BOMs")
        
        self.results["bom_issues"] = issues
    
    def create_summary(self):
        """Crea resumen ejecutivo"""
        print("\n" + "=" * 80)
        print("RESUMEN EJECUTIVO - DIAGNÓSTICO DE CAUSA RAÍZ")
        print("=" * 80)
        
        summary = []
        
        # 1. Stock negativo
        neg_by_loc = self.results.get("stock_by_location", {})
        if neg_by_loc:
            summary.append("HALLAZGO 1: STOCK NEGATIVO MASIVO")
            summary.append(f"  - Múltiples ubicaciones con stock negativo")
            summary.append(f"  - Ubicación 'Partners/Vendors' tiene quants negativos (CRÍTICO)")
            summary.append(f"  - Esto indica entradas sin origen válido o cancelaciones mal ejecutadas")
        
        # 2. Movimientos manuales
        manual = self.results.get("manual_moves", {})
        if manual:
            summary.append("\nHALLAZGO 2: MOVIMIENTOS MANUALES SIN CONTROL")
            summary.append(f"  - {manual.get('total', 0)} movimientos sin picking ni OP")
            summary.append(f"  - {manual.get('suspicious_count', 0)} movimientos sospechosos")
        
        # 3. Duplicidad
        dup_evidence = self.results.get("duplication_evidence", [])
        if dup_evidence:
            summary.append("\nHALLAZGO 3: EVIDENCIA DE CONSUMOS DUPLICADOS")
            summary.append(f"  - {len(dup_evidence)} productos con consumos MRP + manuales")
            summary.append("  - Esto confirma la hipótesis de duplicidad")
        
        # 4. Ajustes de inventario
        adj = self.results.get("inventory_adjustments_detail", {})
        if adj:
            by_user = adj.get("by_user", {})
            summary.append("\nHALLAZGO 4: USO EXCESIVO DE AJUSTES DE INVENTARIO")
            for user, data in by_user.items():
                if data.get('out_count', 0) > 50:
                    summary.append(f"  - {user}: {data['out_count']} ajustes de salida")
        
        print("\n".join(summary))
        
        self.results["summary"] = summary
        return summary
    
    def save_results(self, filename: str = "audit_deep_results.json"):
        """Guarda resultados"""
        def clean(obj):
            if isinstance(obj, dict):
                return {k: clean(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean(i) for i in obj]
            elif isinstance(obj, defaultdict):
                return dict(obj)
            else:
                return obj
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(clean(self.results), f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n✓ Resultados guardados en: {filename}")
    
    def run_deep_analysis(self):
        """Ejecuta análisis profundo"""
        if not self.connect():
            return False
        
        self.find_rf_insumos()
        self.analyze_stock_by_location_type()
        self.analyze_partners_vendors_issue()
        self.analyze_vlk_location()
        self.analyze_production_consumption_flow()
        self.analyze_manual_moves_patterns()
        self.analyze_inventory_adjustments_detail()
        self.analyze_picking_types_usage()
        self.find_duplicate_consumption_evidence()
        self.analyze_bom_configuration()
        self.create_summary()
        
        return True


if __name__ == "__main__":
    analyzer = DeepAnalyzer(URL, DB, USERNAME, PASSWORD)
    
    if analyzer.run_deep_analysis():
        analyzer.save_results()
        print("\n" + "=" * 80)
        print("ANÁLISIS PROFUNDO COMPLETADO")
        print("=" * 80)

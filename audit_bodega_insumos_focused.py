"""
AUDITORÍA ENFOCADA: BODEGA DE INSUMOS
======================================
Alcance estricto: Solo RF/Insumos, insumos de empaque, EPP, químicos operativos.
Excluye: Fruta, MP, producto en proceso, producto terminado.

Fecha: 2026-03-10
"""

import xmlrpc.client
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Tuple
import re

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

class BodegaInsumosAuditor:
    """Auditor enfocado exclusivamente en bodega de insumos"""
    
    # Patrones para clasificar productos DENTRO de alcance
    INSUMOS_PATTERNS = {
        'EMPAQUE': [
            r'bolsa', r'caja', r'etiqueta', r'film', r'stretch', r'cinta',
            r'zuncho', r'grapa', r'fleje', r'esquinero', r'tapa', r'sello',
            r'sticker', r'label', r'envase', r'embalaje', r'packaging'
        ],
        'EPP': [
            r'guante', r'mascarilla', r'cofia', r'delantal', r'bota', r'lente',
            r'protector', r'casco', r'overol', r'manga', r'epp', r'seguridad'
        ],
        'QUIMICOS_OPERATIVOS': [
            r'cloro', r'detergente', r'sanitizante', r'desinfectante',
            r'limpiador', r'alcohol', r'jabon', r'foamchlor', r'quimico'
        ],
        'MATERIALES_AUXILIARES': [
            r'pallet', r'paleta', r'madera', r'carton', r'papel', r'plastico',
            r'residuo', r'desecho', r'basura', r'contenedor'
        ]
    }
    
    # Patrones para EXCLUIR (fuera de alcance)
    EXCLUSION_PATTERNS = [
        r'^1001', r'^1002',  # Códigos de fruta/MP
        r'^300', r'^400',    # MP y producto proceso
        r'^100[0-9]', r'^101', r'^102', r'^103', r'^104',  # Procesos
        r'^200', r'^201', r'^202', r'^203', r'^204',  # PSP/PTT
        r'^301', r'^302', r'^401', r'^402',  # Producto elaborado
        r'^601', r'^602',  # Retail
        r'arandano', r'blueberry', r'frambuesa', r'frutilla', r'mora', r'cereza',
        r'iqf', r'psp', r'ptt', r'block', r'bins', r'congelado',
        r'proceso.*lavado', r'proceso.*vaciado', r'proceso.*seleccion',
        r'fruta', r'berry', r'berries', r'kg en caja', r'kg en bandeja'
    ]
    
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.models = None
        self.results = {
            'scope': {'in_scope': [], 'out_of_scope': []},
            'diagnosis': {},
            'critical_products': [],
            'movements': {},
            'users': {},
            'recommendations': {}
        }
    
    def connect(self) -> bool:
        try:
            print("Conectando a Odoo...")
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.password, {})
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
        return self.execute(model, 'search_count', domain or [])
    
    # ========================================================================
    # FASE 1: DELIMITACIÓN DEL ALCANCE
    # ========================================================================
    
    def is_in_scope(self, product_code: str, product_name: str) -> Tuple[bool, str]:
        """Determina si un producto está dentro del alcance (insumos)"""
        code = (product_code or '').lower()
        name = (product_name or '').lower()
        full_text = f"{code} {name}"
        
        # Primero verificar exclusiones (fruta, MP, proceso, terminado)
        for pattern in self.EXCLUSION_PATTERNS:
            if re.search(pattern, full_text, re.IGNORECASE):
                return False, 'EXCLUIDO'
        
        # Verificar si coincide con patrones de insumos
        for category, patterns in self.INSUMOS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, full_text, re.IGNORECASE):
                    return True, category
        
        # Códigos que empiezan con 500 son típicamente insumos
        if code.startswith('500'):
            return True, 'CODIGO_500'
        
        # Por defecto, si está en ubicación RF/Insumos lo consideramos en alcance
        return True, 'UBICACION_INSUMOS'
    
    def classify_products_in_locations(self):
        """Clasifica productos en RF/Insumos como dentro o fuera de alcance"""
        print("\n" + "=" * 80)
        print("FASE 1: DELIMITACIÓN DEL ALCANCE - CLASIFICACIÓN DE PRODUCTOS")
        print("=" * 80)
        
        # Obtener ubicaciones RF/Insumos
        insumos_locations = self.search_read(
            'stock.location',
            [('complete_name', 'ilike', 'RF/Insumos')],
            ['id', 'name', 'complete_name']
        )
        
        location_ids = [l['id'] for l in insumos_locations]
        print(f"\n📍 Ubicaciones RF/Insumos encontradas: {len(insumos_locations)}")
        for loc in insumos_locations[:10]:
            print(f"   - [{loc['id']}] {loc['complete_name']}")
        
        # Obtener quants en esas ubicaciones
        quants = self.search_read(
            'stock.quant',
            [('location_id', 'in', location_ids)],
            ['product_id', 'location_id', 'quantity'],
            limit=2000
        )
        
        print(f"\n📦 Total quants en RF/Insumos: {len(quants)}")
        
        # Obtener info de productos
        product_ids = list(set([q['product_id'][0] for q in quants if q.get('product_id')]))
        products = self.search_read(
            'product.product',
            [('id', 'in', product_ids)],
            ['id', 'name', 'default_code', 'categ_id', 'type']
        )
        products_dict = {p['id']: p for p in products}
        
        # Clasificar
        in_scope = []
        out_of_scope = []
        classification_detail = defaultdict(list)
        
        for q in quants:
            prod_id = q['product_id'][0] if q.get('product_id') else None
            prod_name = q['product_id'][1] if q.get('product_id') else 'N/A'
            
            prod_info = products_dict.get(prod_id, {})
            code = prod_info.get('default_code', '')
            
            is_insumo, category = self.is_in_scope(code, prod_name)
            
            product_data = {
                'id': prod_id,
                'code': code,
                'name': prod_name,
                'location': q['location_id'][1] if q.get('location_id') else 'N/A',
                'quantity': q.get('quantity', 0),
                'category': category
            }
            
            if is_insumo:
                in_scope.append(product_data)
                classification_detail[category].append(product_data)
            else:
                out_of_scope.append(product_data)
        
        # Eliminar duplicados
        in_scope_unique = {}
        for p in in_scope:
            key = p['id']
            if key not in in_scope_unique:
                in_scope_unique[key] = p
            else:
                in_scope_unique[key]['quantity'] += p['quantity']
        
        out_scope_unique = {}
        for p in out_of_scope:
            key = p['id']
            if key not in out_scope_unique:
                out_scope_unique[key] = p
            else:
                out_scope_unique[key]['quantity'] += p['quantity']
        
        print(f"\n" + "=" * 60)
        print("CLASIFICACIÓN DE PRODUCTOS EN RF/INSUMOS")
        print("=" * 60)
        
        print(f"\n✅ DENTRO DE ALCANCE (INSUMOS): {len(in_scope_unique)} productos únicos")
        for category, items in classification_detail.items():
            unique_in_cat = len(set([i['id'] for i in items]))
            print(f"   - {category}: {unique_in_cat} productos")
        
        print(f"\n❌ FUERA DE ALCANCE (NO TOCAR): {len(out_scope_unique)} productos únicos")
        
        # Mostrar ejemplos de cada grupo
        print("\n📋 EJEMPLOS DE PRODUCTOS DENTRO DE ALCANCE:")
        for i, (pid, p) in enumerate(list(in_scope_unique.items())[:15]):
            neg_mark = "⚠️" if p['quantity'] < 0 else ""
            print(f"   {neg_mark} [{p['code']}] {p['name'][:50]}: {p['quantity']:,.2f} ({p['category']})")
        
        print("\n🚫 EJEMPLOS DE PRODUCTOS FUERA DE ALCANCE (NO TOCAR):")
        for i, (pid, p) in enumerate(list(out_scope_unique.items())[:10]):
            print(f"   [{p['code']}] {p['name'][:50]}: {p['quantity']:,.2f}")
        
        self.results['scope']['in_scope'] = list(in_scope_unique.values())
        self.results['scope']['out_of_scope'] = list(out_scope_unique.values())
        self.results['scope']['locations'] = insumos_locations
        
        return in_scope_unique, out_scope_unique, location_ids
    
    # ========================================================================
    # FASE 2: DIAGNÓSTICO SOLO DE INSUMOS
    # ========================================================================
    
    def diagnose_insumos_only(self, in_scope_products: Dict, location_ids: List[int]):
        """Diagnostica problemas SOLO en productos de insumos"""
        print("\n" + "=" * 80)
        print("FASE 2: DIAGNÓSTICO EXCLUSIVO DE INSUMOS")
        print("=" * 80)
        
        # Filtrar productos con stock negativo
        negative_products = {
            pid: p for pid, p in in_scope_products.items() 
            if p['quantity'] < 0
        }
        
        print(f"\n🔴 PRODUCTOS DE INSUMOS CON STOCK NEGATIVO: {len(negative_products)}")
        print("-" * 60)
        
        # Ordenar por más negativo
        sorted_negative = sorted(negative_products.values(), key=lambda x: x['quantity'])
        
        critical_products = []
        for i, p in enumerate(sorted_negative[:30]):
            print(f"\n{i+1}. [{p['code']}] {p['name'][:55]}")
            print(f"   📍 Ubicación: {p['location']}")
            print(f"   📉 Stock: {p['quantity']:,.2f}")
            print(f"   🏷️ Categoría: {p['category']}")
            
            critical_products.append(p)
        
        self.results['critical_products'] = critical_products
        
        # Analizar movimientos de productos negativos
        print("\n" + "=" * 60)
        print("ANÁLISIS DE MOVIMIENTOS DE INSUMOS PROBLEMÁTICOS")
        print("=" * 60)
        
        product_ids_negative = [p['id'] for p in sorted_negative[:20]]
        
        if product_ids_negative:
            # Obtener movimientos de estos productos
            moves = self.search_read(
                'stock.move',
                [
                    ('product_id', 'in', product_ids_negative),
                    ('state', '=', 'done'),
                    '|',
                    ('location_id', 'in', location_ids),
                    ('location_dest_id', 'in', location_ids)
                ],
                ['id', 'name', 'product_id', 'quantity_done', 'date',
                 'location_id', 'location_dest_id', 'picking_id',
                 'picking_type_id', 'origin', 'reference', 'create_uid'],
                limit=500,
                order='date desc'
            )
            
            print(f"\nMovimientos recientes de insumos problemáticos: {len(moves)}")
            
            # Analizar por tipo de operación
            by_picking_type = defaultdict(list)
            by_user = defaultdict(int)
            manual_moves = []
            
            for m in moves:
                pt = m.get('picking_type_id', [0, 'Sin tipo'])[1] if m.get('picking_type_id') else 'Sin picking'
                by_picking_type[pt].append(m)
                
                user = m.get('create_uid', [0, 'Sistema'])[1] if m.get('create_uid') else 'Sistema'
                by_user[user] += 1
                
                # Detectar movimientos manuales (sin picking o sin origen)
                if not m.get('picking_id') or not m.get('origin'):
                    manual_moves.append(m)
            
            print("\n📊 MOVIMIENTOS POR TIPO DE OPERACIÓN:")
            for pt, moves_list in sorted(by_picking_type.items(), key=lambda x: -len(x[1])):
                print(f"   {pt}: {len(moves_list)} movimientos")
            
            print("\n👤 USUARIOS QUE MUEVEN INSUMOS:")
            for user, count in sorted(by_user.items(), key=lambda x: -x[1])[:10]:
                print(f"   {user}: {count} movimientos")
            
            print(f"\n⚠️ MOVIMIENTOS SIN DOCUMENTO ORIGEN: {len(manual_moves)}")
            
            self.results['movements'] = {
                'total': len(moves),
                'by_type': {k: len(v) for k, v in by_picking_type.items()},
                'by_user': dict(by_user),
                'manual_count': len(manual_moves)
            }
        
        return critical_products
    
    # ========================================================================
    # FASE 2.1: ANÁLISIS DEL TIPO CONSUMO (ID 177)
    # ========================================================================
    
    def analyze_consumo_type_for_insumos(self, in_scope_products: Dict, location_ids: List[int]):
        """Analiza el tipo CONSUMO específicamente para insumos"""
        print("\n" + "=" * 80)
        print("ANÁLISIS DEL TIPO CONSUMO (ID 177) EN INSUMOS")
        print("=" * 80)
        
        # Obtener info del tipo CONSUMO
        consumo_type = self.search_read(
            'stock.picking.type',
            [('id', '=', 177)],
            ['id', 'name', 'code', 'default_location_src_id', 
             'default_location_dest_id', 'active', 'warehouse_id']
        )
        
        if consumo_type:
            ct = consumo_type[0]
            print(f"\n📋 TIPO CONSUMO (ID 177):")
            print(f"   Nombre: {ct.get('name')}")
            print(f"   Código: {ct.get('code')}")
            print(f"   Activo: {ct.get('active')}")
            print(f"   Origen: {ct.get('default_location_src_id')}")
            print(f"   Destino: {ct.get('default_location_dest_id')}")
        
        # Obtener pickings CONSUMO que afectan insumos
        product_ids_insumos = list(in_scope_products.keys())
        
        # Pickings de tipo CONSUMO
        consumo_pickings = self.search_read(
            'stock.picking',
            [('picking_type_id', '=', 177), ('state', '=', 'done')],
            ['id', 'name', 'date_done', 'origin', 'create_uid', 'partner_id'],
            limit=500,
            order='date_done desc'
        )
        
        print(f"\n📦 Total pickings CONSUMO completados: {len(consumo_pickings)}")
        
        # Analizar qué productos de INSUMOS se mueven por CONSUMO
        moves_consumo = self.search_read(
            'stock.move',
            [('picking_type_id', '=', 177), ('state', '=', 'done')],
            ['product_id', 'quantity_done', 'date', 'picking_id', 'create_uid'],
            limit=1000
        )
        
        # Filtrar solo insumos
        insumos_in_consumo = []
        non_insumos_in_consumo = []
        
        product_ids_in_moves = set()
        for m in moves_consumo:
            pid = m['product_id'][0] if m.get('product_id') else None
            product_ids_in_moves.add(pid)
            
            if pid in product_ids_insumos:
                insumos_in_consumo.append(m)
            else:
                non_insumos_in_consumo.append(m)
        
        print(f"\n   ✅ Movimientos CONSUMO de INSUMOS: {len(insumos_in_consumo)}")
        print(f"   🚫 Movimientos CONSUMO de NO-INSUMOS: {len(non_insumos_in_consumo)}")
        
        # Top productos de insumos movidos por CONSUMO
        insumos_consumo_qty = defaultdict(float)
        for m in insumos_in_consumo:
            pname = m['product_id'][1] if m.get('product_id') else 'N/A'
            insumos_consumo_qty[pname] += m.get('quantity_done', 0)
        
        print("\n📊 TOP INSUMOS MOVIDOS POR TIPO CONSUMO:")
        for prod, qty in sorted(insumos_consumo_qty.items(), key=lambda x: -x[1])[:15]:
            print(f"   {prod[:55]}: {qty:,.2f}")
        
        # Usuarios que usan CONSUMO para insumos
        users_consumo = defaultdict(int)
        for m in insumos_in_consumo:
            user = m.get('create_uid', [0, 'Sistema'])[1] if m.get('create_uid') else 'Sistema'
            users_consumo[user] += 1
        
        print("\n👤 USUARIOS QUE USAN TIPO CONSUMO PARA INSUMOS:")
        for user, count in sorted(users_consumo.items(), key=lambda x: -x[1])[:10]:
            print(f"   {user}: {count} movimientos")
        
        # Pickings CONSUMO pendientes
        pending_consumo = self.search_read(
            'stock.picking',
            [('picking_type_id', '=', 177), 
             ('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned'])],
            ['id', 'name', 'state', 'scheduled_date']
        )
        
        print(f"\n⏳ PICKINGS CONSUMO PENDIENTES: {len(pending_consumo)}")
        for p in pending_consumo[:10]:
            print(f"   - {p['name']} ({p['state']})")
        
        self.results['consumo_analysis'] = {
            'type_info': consumo_type[0] if consumo_type else None,
            'total_pickings_done': len(consumo_pickings),
            'insumos_moves': len(insumos_in_consumo),
            'non_insumos_moves': len(non_insumos_in_consumo),
            'top_products': dict(sorted(insumos_consumo_qty.items(), key=lambda x: -x[1])[:20]),
            'users': dict(users_consumo),
            'pending_pickings': pending_consumo
        }
        
        return len(insumos_in_consumo), users_consumo, pending_consumo
    
    # ========================================================================
    # FASE 2.2: AJUSTES DE INVENTARIO EN INSUMOS
    # ========================================================================
    
    def analyze_adjustments_insumos(self, in_scope_products: Dict, location_ids: List[int]):
        """Analiza ajustes de inventario solo en insumos"""
        print("\n" + "=" * 80)
        print("AJUSTES DE INVENTARIO EN INSUMOS")
        print("=" * 80)
        
        product_ids_insumos = list(in_scope_products.keys())
        
        # Buscar movimientos de ajuste (scrap o inventory loss)
        inventory_loss_locs = self.search_read(
            'stock.location',
            [('usage', '=', 'inventory')],
            ['id', 'name', 'complete_name']
        )
        inventory_loss_ids = [l['id'] for l in inventory_loss_locs]
        
        # Movimientos hacia/desde inventory loss
        adj_moves = self.search_read(
            'stock.move',
            [
                ('product_id', 'in', product_ids_insumos),
                ('state', '=', 'done'),
                '|',
                ('location_id', 'in', inventory_loss_ids),
                ('location_dest_id', 'in', inventory_loss_ids)
            ],
            ['product_id', 'quantity_done', 'date', 'location_id', 
             'location_dest_id', 'create_uid', 'origin', 'reference'],
            limit=500,
            order='date desc'
        )
        
        print(f"\nAjustes de inventario en INSUMOS: {len(adj_moves)}")
        
        # Clasificar ajustes positivos vs negativos
        positive_adj = []  # Hacia stock
        negative_adj = []  # Hacia inventory loss
        
        for m in adj_moves:
            src_id = m['location_id'][0] if m.get('location_id') else 0
            dest_id = m['location_dest_id'][0] if m.get('location_dest_id') else 0
            
            if dest_id in inventory_loss_ids:
                negative_adj.append(m)
            elif src_id in inventory_loss_ids:
                positive_adj.append(m)
        
        total_neg = sum(m.get('quantity_done', 0) for m in negative_adj)
        total_pos = sum(m.get('quantity_done', 0) for m in positive_adj)
        
        print(f"\n   📉 Ajustes negativos (mermas): {len(negative_adj)} ({total_neg:,.2f} uds)")
        print(f"   📈 Ajustes positivos (correcciones): {len(positive_adj)} ({total_pos:,.2f} uds)")
        print(f"   📊 Balance neto: {total_pos - total_neg:,.2f} uds")
        
        # Usuarios que hacen ajustes
        adj_users = defaultdict(lambda: {'pos': 0, 'neg': 0, 'qty_pos': 0, 'qty_neg': 0})
        for m in positive_adj:
            user = m.get('create_uid', [0, 'Sistema'])[1]
            adj_users[user]['pos'] += 1
            adj_users[user]['qty_pos'] += m.get('quantity_done', 0)
        for m in negative_adj:
            user = m.get('create_uid', [0, 'Sistema'])[1]
            adj_users[user]['neg'] += 1
            adj_users[user]['qty_neg'] += m.get('quantity_done', 0)
        
        print("\n👤 USUARIOS QUE AJUSTAN INSUMOS:")
        for user, data in sorted(adj_users.items(), key=lambda x: -(x[1]['neg'] + x[1]['pos']))[:10]:
            print(f"   {user}: +{data['pos']} ajustes ({data['qty_pos']:,.0f} uds), -{data['neg']} ajustes ({data['qty_neg']:,.0f} uds)")
        
        self.results['adjustments'] = {
            'total': len(adj_moves),
            'negative_count': len(negative_adj),
            'negative_qty': total_neg,
            'positive_count': len(positive_adj),
            'positive_qty': total_pos,
            'by_user': {k: dict(v) for k, v in adj_users.items()}
        }
        
        return adj_moves
    
    # ========================================================================
    # FASE 3: VALIDACIÓN DEL FLUJO OPERATIVO ACTUAL
    # ========================================================================
    
    def analyze_current_flow(self, location_ids: List[int]):
        """Analiza el flujo operativo actual de bodega de insumos"""
        print("\n" + "=" * 80)
        print("FASE 3: FLUJO OPERATIVO ACTUAL DE BODEGA DE INSUMOS")
        print("=" * 80)
        
        # Obtener todos los tipos de operación usados con RF/Insumos
        moves = self.search_read(
            'stock.move',
            [
                ('state', '=', 'done'),
                '|',
                ('location_id', 'in', location_ids),
                ('location_dest_id', 'in', location_ids)
            ],
            ['picking_type_id', 'location_id', 'location_dest_id'],
            limit=2000
        )
        
        # Clasificar por tipo de operación
        flow_analysis = defaultdict(lambda: {'count': 0, 'src': set(), 'dest': set()})
        
        for m in moves:
            pt = m.get('picking_type_id', [0, 'Sin picking'])[1] if m.get('picking_type_id') else 'Sin picking'
            src = m.get('location_id', [0, 'N/A'])[1] if m.get('location_id') else 'N/A'
            dest = m.get('location_dest_id', [0, 'N/A'])[1] if m.get('location_dest_id') else 'N/A'
            
            flow_analysis[pt]['count'] += 1
            flow_analysis[pt]['src'].add(src)
            flow_analysis[pt]['dest'].add(dest)
        
        print("\n📊 TIPOS DE OPERACIÓN USADOS EN RF/INSUMOS:")
        print("-" * 60)
        
        for pt, data in sorted(flow_analysis.items(), key=lambda x: -x[1]['count']):
            print(f"\n🏷️ {pt}: {data['count']} movimientos")
            print(f"   Orígenes: {', '.join(list(data['src'])[:3])}")
            print(f"   Destinos: {', '.join(list(data['dest'])[:3])}")
        
        # Analizar flujo de entrada vs salida de RF/Insumos
        entries = self.search_count('stock.move', [
            ('location_dest_id', 'in', location_ids),
            ('state', '=', 'done')
        ])
        exits = self.search_count('stock.move', [
            ('location_id', 'in', location_ids),
            ('state', '=', 'done')
        ])
        
        print(f"\n📥 Total entradas a RF/Insumos: {entries}")
        print(f"📤 Total salidas de RF/Insumos: {exits}")
        
        self.results['current_flow'] = {
            'by_operation_type': {k: v['count'] for k, v in flow_analysis.items()},
            'total_entries': entries,
            'total_exits': exits
        }
        
        return flow_analysis
    
    # ========================================================================
    # FASE 4: RESUMEN Y RECOMENDACIONES
    # ========================================================================
    
    def generate_summary(self):
        """Genera resumen final con recomendaciones"""
        print("\n" + "=" * 80)
        print("RESUMEN EJECUTIVO - BODEGA DE INSUMOS")
        print("=" * 80)
        
        in_scope = self.results['scope']['in_scope']
        negative_in_scope = [p for p in in_scope if p['quantity'] < 0]
        
        print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          RESUMEN BODEGA DE INSUMOS                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Productos DENTRO de alcance (insumos):     {len(in_scope):>6}                           ║
║  Productos FUERA de alcance (excluidos):    {len(self.results['scope']['out_of_scope']):>6}                           ║
║  Productos de insumos con STOCK NEGATIVO:   {len(negative_in_scope):>6}                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Movimientos tipo CONSUMO en insumos:       {self.results.get('consumo_analysis', {}).get('insumos_moves', 0):>6}                           ║
║  Pickings CONSUMO pendientes:               {len(self.results.get('consumo_analysis', {}).get('pending_pickings', [])):>6}                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Ajustes de inventario en insumos:          {self.results.get('adjustments', {}).get('total', 0):>6}                           ║
║    - Negativos (mermas):                    {self.results.get('adjustments', {}).get('negative_count', 0):>6}                           ║
║    - Positivos (correcciones):              {self.results.get('adjustments', {}).get('positive_count', 0):>6}                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        # Recomendaciones
        print("\n🎯 RECOMENDACIONES PARA BODEGA DE INSUMOS:")
        print("-" * 60)
        
        recommendations = []
        
        # 1. Sobre tipo CONSUMO
        consumo_data = self.results.get('consumo_analysis', {})
        if consumo_data.get('insumos_moves', 0) > 0:
            recommendations.append({
                'priority': 'CRÍTICA',
                'action': 'BLOQUEAR tipo de operación CONSUMO (ID 177)',
                'reason': f'Se usa para {consumo_data.get("insumos_moves", 0)} movimientos sin trazabilidad',
                'alternative': 'Crear tipo "Transferencia a Producción" con documento obligatorio'
            })
        
        # 2. Sobre usuario genérico
        users = consumo_data.get('users', {})
        if 'Bodega Insumos' in users:
            recommendations.append({
                'priority': 'CRÍTICA',
                'action': 'DESACTIVAR usuario genérico "Bodega Insumos"',
                'reason': 'Usuarios genéricos impiden trazabilidad',
                'alternative': 'Crear usuarios nominados por persona'
            })
        
        # 3. Sobre pickings pendientes
        pending = consumo_data.get('pending_pickings', [])
        if pending:
            recommendations.append({
                'priority': 'ALTA',
                'action': f'Cerrar o cancelar {len(pending)} pickings CONSUMO pendientes',
                'reason': 'Deben resolverse antes de bloquear tipo',
                'alternative': 'Evaluar cada uno y completar/cancelar según corresponda'
            })
        
        # 4. Sobre conteo físico
        if len(negative_in_scope) > 0:
            recommendations.append({
                'priority': 'ALTA',
                'action': 'Ejecutar conteo físico de insumos críticos',
                'reason': f'{len(negative_in_scope)} productos con stock negativo',
                'alternative': 'Priorizar top 20 más negativos'
            })
        
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. [{rec['priority']}] {rec['action']}")
            print(f"   Motivo: {rec['reason']}")
            print(f"   Alternativa: {rec['alternative']}")
        
        self.results['recommendations'] = recommendations
        
        return self.results
    
    def save_results(self, filename: str = "audit_bodega_insumos_results.json"):
        """Guarda resultados"""
        def clean(obj):
            if isinstance(obj, dict):
                return {k: clean(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean(i) for i in obj]
            elif isinstance(obj, set):
                return list(obj)
            elif isinstance(obj, defaultdict):
                return dict(obj)
            else:
                return obj
        
        output = {
            "timestamp": datetime.now().isoformat(),
            "scope": "BODEGA_INSUMOS_ONLY",
            "results": clean(self.results)
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n✓ Resultados guardados en: {filename}")
    
    def run_full_audit(self):
        """Ejecuta auditoría completa enfocada en insumos"""
        if not self.connect():
            return None
        
        print("\n" + "=" * 80)
        print("AUDITORÍA ENFOCADA: BODEGA DE INSUMOS")
        print("Alcance: RF/Insumos, empaque, EPP, químicos operativos")
        print("Excluye: Fruta, MP, producto proceso/terminado")
        print("=" * 80)
        
        # FASE 1: Clasificación
        in_scope, out_scope, location_ids = self.classify_products_in_locations()
        
        # FASE 2: Diagnóstico
        self.diagnose_insumos_only(in_scope, location_ids)
        self.analyze_consumo_type_for_insumos(in_scope, location_ids)
        self.analyze_adjustments_insumos(in_scope, location_ids)
        
        # FASE 3: Flujo actual
        self.analyze_current_flow(location_ids)
        
        # FASE 4: Resumen
        self.generate_summary()
        
        return self.results


if __name__ == "__main__":
    auditor = BodegaInsumosAuditor(URL, DB, USERNAME, PASSWORD)
    results = auditor.run_full_audit()
    
    if results:
        auditor.save_results()
        print("\n" + "=" * 80)
        print("AUDITORÍA DE BODEGA DE INSUMOS COMPLETADA")
        print("=" * 80)

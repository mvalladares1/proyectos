"""
Servicio de Rendimiento Productivo.
Incluye funciones para trazabilidad inversa Y datos dashboard para Producción.
OPTIMIZADO: Incluye caché para reducir llamadas repetidas a Odoo.
"""
from typing import Optional, Dict, List
from datetime import datetime
from shared.odoo_client import OdooClient
from backend.cache import get_cache


class RendimientoService:
    """
    Servicio para análisis de rendimiento productivo.
    - Trazabilidad inversa: PT → MP
    - Dashboard consolidado para módulo de Producción
    """
    
    # Categorías a excluir del consumo MP
    EXCLUDED_CATEGORIES = ["insumo", "envase", "etiqueta", "embalaje", "merma"]
    
    # Salas de proceso (vaciado) - Genera merma real
    SALAS_PROCESO = [
        'sala 1', 'sala 2', 'sala 3', 'sala 4', 'sala 5', 'sala 6',
        'linea retail', 'granel', 'proceso'
    ]
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self._cache = get_cache()
    
    # ===========================================
    # FUNCIONES AUXILIARES
    # ===========================================
    
    def _is_operational_cost(self, product_name: str) -> bool:
        """Identifica costos operacionales (electricidad, servicios)"""
        if not product_name:
            return False
        
        name_lower = product_name.lower()
        operational_indicators = [
            "provisión electricidad", "provisión electr",
            "túnel estático", "tunel estatico",
            "electricidad túnel", "costo hora", "($/hr)", "($/h)"
        ]
        
        return any(ind in name_lower for ind in operational_indicators)
    
    def _is_excluded_consumo(self, product_name: str, category_name: str = '') -> bool:
        """Verifica si un producto debe excluirse del consumo MP."""
        if not product_name:
            return True
        
        name_lower = product_name.lower()
        cat_lower = (category_name or '').lower()
        
        # Productos con código [3xxxxx] o [1xxxxx] son productos de proceso
        if product_name.startswith('[3') or product_name.startswith('[1'):
            return False
        
        if self._is_operational_cost(product_name):
            return True
        
        if any(exc in cat_lower for exc in self.EXCLUDED_CATEGORIES):
            return True
        
        pure_packaging = [
            "caja de exportación", "cajas de exportación", 
            "insumo", "envase", "pallet", "etiqueta", "doy pe"
        ]
        
        if any(exc in name_lower for exc in pure_packaging):
            return True
        
        if name_lower.startswith('bolsa') or name_lower.startswith('caja'):
            return True
        
        return False
    
    def _extract_fruit_type(self, product_name: str) -> str:
        """Extrae el tipo de fruta del nombre del producto."""
        if not product_name:
            return 'Otro'
        
        name_lower = product_name.lower()
        
        fruit_mapping = {
            'arándano': 'Arándano', 'arandano': 'Arándano', 'blueberr': 'Arándano',
            'frambuesa': 'Frambuesa', 'raspberry': 'Frambuesa', 'raspberr': 'Frambuesa',
            'mora': 'Mora', 'blackberr': 'Mora',
            'frutilla': 'Frutilla', 'fresa': 'Frutilla', 'strawberr': 'Frutilla',
            'cereza': 'Cereza', 'cherry': 'Cereza', 'guinda': 'Cereza',
            'kiwi': 'Kiwi',
            'manzana': 'Manzana', 'apple': 'Manzana',
        }
        
        for key, value in fruit_mapping.items():
            if key in name_lower:
                return value
        
        return 'Otro'
    
    def _extract_handling(self, product_name: str) -> str:
        """Extrae el manejo (orgánico/convencional) del nombre."""
        if not product_name:
            return 'Otro'
        
        name_lower = product_name.lower()
        
        if 'orgánico' in name_lower or 'organico' in name_lower or 'org.' in name_lower:
            return 'Orgánico'
        elif 'convencional' in name_lower or 'conv.' in name_lower:
            return 'Convencional'
        
        return 'Otro'
    
    def _classify_sala(self, sala_name: str, product_name: str = '') -> tuple:
        """Clasifica una sala o producto como PROCESO o CONGELADO."""
        if not sala_name:
            sala_name = ''
        if not product_name:
            product_name = ''
            
        sala_lower = sala_name.lower()
        prod_lower = product_name.lower()
        
        # Túneles estáticos o procesos de congelación
        if 'túnel' in sala_lower or 'tunel' in sala_lower or 'congelado' in sala_lower:
            return (sala_name or 'Congelado', 'CONGELADO')
        
        if 'estático' in prod_lower or 'estatico' in prod_lower or 'túnel' in prod_lower or 'tunel' in prod_lower:
            return (sala_name or 'Congelado', 'CONGELADO')
        
        # Salas de proceso
        for sp in self.SALAS_PROCESO:
            if sp in sala_lower:
                return (sala_name, 'PROCESO')
        
        # Si tiene sala pero no es túnel, asumimos proceso
        if sala_name:
            return (sala_name, 'PROCESO')
        
        return ('SIN SALA', 'SIN_SALA')
    
    # ===========================================
    # FUNCIONES DE BATCH
    # ===========================================
    
    def get_mos_por_periodo(self, fecha_inicio: str, fecha_fin: str, solo_terminadas: bool = True) -> List[Dict]:
        """Obtiene todas las MOs del período."""
        domain = [
            ['date_planned_start', '>=', f'{fecha_inicio} 00:00:00'],
            ['date_planned_start', '<=', f'{fecha_fin} 23:59:59']
        ]
        
        if solo_terminadas:
            domain.append(['state', '=', 'done'])
        
        mos = self.odoo.search_read(
            'mrp.production',
            domain,
            ['id', 'name', 'product_id', 'state', 'date_planned_start', 'date_finished',
             'x_studio_sala_de_proceso', 'x_studio_dotacin', 'x_studio_hh_efectiva',
             'x_studio_kghora_efectiva', 'x_studio_inicio_de_proceso', 'x_studio_termino_de_proceso',
             'move_raw_ids', 'move_finished_ids', 'move_byproduct_ids'],
            limit=500,
            order='date_planned_start desc'
        )
        
        return mos or []
    
    def get_consumos_batch(self, mos: List[Dict]) -> Dict[int, List[Dict]]:
        """Obtiene consumos de todas las MOs en una sola llamada."""
        all_raw_ids = []
        mo_raw_map = {}
        
        for mo in mos:
            mo_id = mo.get('id')
            raw_ids = mo.get('move_raw_ids', [])
            mo_raw_map[mo_id] = raw_ids
            all_raw_ids.extend(raw_ids)
        
        if not all_raw_ids:
            return {}
        
        # Obtener todos los move lines en batch
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', all_raw_ids]],
            ['move_id', 'product_id', 'lot_id', 'qty_done'],
            limit=5000
        )
        
        # Crear mapa move_id -> mo_id
        move_to_mo = {}
        for mo in mos:
            mo_id = mo.get('id')
            for raw_id in mo.get('move_raw_ids', []):
                move_to_mo[raw_id] = mo_id
        
        # Agrupar por MO
        result = {mo.get('id'): [] for mo in mos}
        
        for ml in move_lines or []:
            move_id_info = ml.get('move_id')
            if not move_id_info:
                continue
            
            move_id = move_id_info[0] if isinstance(move_id_info, (list, tuple)) else move_id_info
            mo_id = move_to_mo.get(move_id)
            
            if mo_id is not None:
                prod = ml.get('product_id')
                prod_name = prod[1] if isinstance(prod, (list, tuple)) and len(prod) > 1 else ''
                
                if not self._is_excluded_consumo(prod_name):
                    lot = ml.get('lot_id')
                    result[mo_id].append({
                        'product_id': prod[0] if isinstance(prod, (list, tuple)) else prod,
                        'product_name': prod_name,
                        'lot_id': lot[0] if isinstance(lot, (list, tuple)) and lot else None,
                        'lot_name': lot[1] if isinstance(lot, (list, tuple)) and len(lot) > 1 else None,
                        'qty_done': ml.get('qty_done', 0) or 0,
                        'especie': self._extract_fruit_type(prod_name),
                        'manejo': self._extract_handling(prod_name)
                    })
        
        return result
    
    def get_produccion_batch(self, mos: List[Dict]) -> Dict[int, List[Dict]]:
        """Obtiene producción de todas las MOs en una sola llamada."""
        all_finished_ids = []
        all_byproduct_ids = []
        
        for mo in mos:
            all_finished_ids.extend(mo.get('move_finished_ids', []))
            all_byproduct_ids.extend(mo.get('move_byproduct_ids', []))
        
        all_prod_ids = list(set(all_finished_ids + all_byproduct_ids))
        
        if not all_prod_ids:
            return {}
        
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', all_prod_ids]],
            ['move_id', 'product_id', 'lot_id', 'qty_done'],
            limit=5000
        )
        
        # Crear mapa move_id -> mo_id
        move_to_mo = {}
        for mo in mos:
            mo_id = mo.get('id')
            for pid in mo.get('move_finished_ids', []) + mo.get('move_byproduct_ids', []):
                move_to_mo[pid] = mo_id
        
        # Agrupar por MO
        result = {mo.get('id'): [] for mo in mos}
        
        for ml in move_lines or []:
            move_id_info = ml.get('move_id')
            if not move_id_info:
                continue
            
            move_id = move_id_info[0] if isinstance(move_id_info, (list, tuple)) else move_id_info
            mo_id = move_to_mo.get(move_id)
            
            if mo_id is not None:
                prod = ml.get('product_id')
                prod_name = prod[1] if isinstance(prod, (list, tuple)) and len(prod) > 1 else ''
                lot = ml.get('lot_id')
                
                result[mo_id].append({
                    'product_id': prod[0] if isinstance(prod, (list, tuple)) else prod,
                    'product_name': prod_name,
                    'lot_id': lot[0] if isinstance(lot, (list, tuple)) and lot else None,
                    'lot_name': lot[1] if isinstance(lot, (list, tuple)) and len(lot) > 1 else None,
                    'qty_done': ml.get('qty_done', 0) or 0
                })
        
        return result
    
    def get_costos_operacionales_batch(self, mos: List[Dict]) -> Dict[int, Dict]:
        """Obtiene costos operacionales (electricidad) de todas las MOs."""
        all_raw_ids = []
        for mo in mos:
            all_raw_ids.extend(mo.get('move_raw_ids', []))
        
        if not all_raw_ids:
            return {}
        
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', all_raw_ids]],
            ['move_id', 'product_id', 'qty_done'],
            limit=5000
        )
        
        move_to_mo = {}
        for mo in mos:
            mo_id = mo.get('id')
            for raw_id in mo.get('move_raw_ids', []):
                move_to_mo[raw_id] = mo_id
        
        result = {mo.get('id'): {'costo_electricidad': 0, 'otros_costos': 0} for mo in mos}
        
        for ml in move_lines or []:
            move_id_info = ml.get('move_id')
            if not move_id_info:
                continue
            
            move_id = move_id_info[0] if isinstance(move_id_info, (list, tuple)) else move_id_info
            mo_id = move_to_mo.get(move_id)
            
            if mo_id is not None:
                prod = ml.get('product_id')
                prod_name = prod[1] if isinstance(prod, (list, tuple)) and len(prod) > 1 else ''
                
                if self._is_operational_cost(prod_name):
                    qty = ml.get('qty_done', 0) or 0
                    result[mo_id]['costo_electricidad'] += qty
        
        return result
    
    # ===========================================
    # GET PROVEEDOR LOTE (para trazabilidad)
    # ===========================================
    
    def get_proveedor_lote(self, lot_id: int) -> Optional[Dict]:
        """Obtiene el proveedor de un lote buscando su recepción original."""
        if not lot_id:
            return None
        
        try:
            move_lines = self.odoo.search_read(
                'stock.move.line',
                [['lot_id', '=', lot_id]],
                ['move_id', 'picking_id', 'location_id', 'date'],
                limit=20,
                order='date asc'
            )
            
            if not move_lines:
                return None
            
            for ml in move_lines:
                loc_id = ml.get('location_id')
                if loc_id:
                    loc_name = loc_id[1] if isinstance(loc_id, (list, tuple)) and len(loc_id) > 1 else str(loc_id)
                    
                    if 'vendor' in loc_name.lower() or 'proveedor' in loc_name.lower():
                        picking_info = ml.get('picking_id')
                        if picking_info:
                            pickings = self.odoo.read('stock.picking', [picking_info[0]], 
                                ['partner_id', 'origin', 'scheduled_date'])
                            if pickings and pickings[0].get('partner_id'):
                                partner = pickings[0]['partner_id']
                                return {
                                    'id': partner[0] if isinstance(partner, (list, tuple)) else partner,
                                    'name': partner[1] if isinstance(partner, (list, tuple)) else str(partner),
                                    'fecha_recepcion': pickings[0].get('scheduled_date'),
                                    'origin': pickings[0].get('origin', '')
                                }
            
            return {'id': None, 'name': 'Producido internamente', 'fecha_recepcion': None, 'origin': ''}
            
        except Exception:
            return None
    
    # ===========================================
    # TRAZABILIDAD INVERSA
    # ===========================================
    
    def get_trazabilidad_inversa(self, lote_pt_name: str) -> Dict:
        """Trazabilidad inversa: dado un lote PT, encuentra los lotes MP originales."""
        lotes = self.odoo.search_read(
            'stock.lot',
            [['name', '=', lote_pt_name]],
            ['id', 'name', 'product_id', 'create_date'],
            limit=1
        )
        
        if not lotes:
            return {'error': 'Lote no encontrado', 'lote_pt': lote_pt_name}
        
        lote_pt = lotes[0]
        lote_pt_id = lote_pt['id']
        
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['lot_id', '=', lote_pt_id]],
            ['move_id', 'date'],
            limit=10,
            order='date asc'
        )
        
        mo_encontrada = None
        for ml in move_lines:
            move_id = ml.get('move_id')
            if move_id:
                moves = self.odoo.read('stock.move', [move_id[0]], ['production_id'])
                if moves and moves[0].get('production_id'):
                    mo_id = moves[0]['production_id'][0]
                    mo_encontrada = self.odoo.read('mrp.production', [mo_id], 
                        ['name', 'move_raw_ids', 'date_planned_start', 'product_id'])[0]
                    break
        
        if not mo_encontrada:
            return {
                'lote_pt': lote_pt_name,
                'producto_pt': lote_pt.get('product_id', [0, ''])[1] if lote_pt.get('product_id') else '',
                'fecha_creacion': str(lote_pt.get('create_date', ''))[:10],
                'mo': None,
                'lotes_mp': [],
                'error': 'No se encontró la MO de producción'
            }
        
        move_raw_ids = mo_encontrada.get('move_raw_ids', [])
        lotes_mp = []
        
        if move_raw_ids:
            consumos = self.odoo.search_read(
                'stock.move.line',
                [['move_id', 'in', move_raw_ids]],
                ['product_id', 'lot_id', 'qty_done'],
                limit=50
            )
            
            for c in consumos:
                prod_info = c.get('product_id')
                prod_name = prod_info[1] if prod_info else ''
                
                if self._is_excluded_consumo(prod_name):
                    continue
                
                lot_info = c.get('lot_id')
                if lot_info:
                    qty = c.get('qty_done', 0) or 0
                    if qty > 0:
                        proveedor_info = self.get_proveedor_lote(lot_info[0])
                        
                        lotes_mp.append({
                            'lot_id': lot_info[0],
                            'lot_name': lot_info[1],
                            'product_name': prod_name,
                            'kg': round(qty, 2),
                            'proveedor': proveedor_info.get('name', 'Desconocido') if proveedor_info else 'Desconocido',
                            'fecha_recepcion': proveedor_info.get('fecha_recepcion', '') if proveedor_info else ''
                        })
        
        return {
            'lote_pt': lote_pt_name,
            'producto_pt': lote_pt.get('product_id', [0, ''])[1] if lote_pt.get('product_id') else '',
            'fecha_creacion': str(lote_pt.get('create_date', ''))[:10],
            'mo': {
                'name': mo_encontrada.get('name', ''),
                'fecha': str(mo_encontrada.get('date_planned_start', ''))[:10]
            },
            'lotes_mp': lotes_mp,
            'total_kg_mp': round(sum(l['kg'] for l in lotes_mp), 2)
        }
    
    # ===========================================
    # DASHBOARD COMPLETO (usado por Producción)
    # ===========================================
    
    def get_dashboard_completo(self, fecha_inicio: str, fecha_fin: str, solo_terminadas: bool = True) -> Dict:
        """
        Obtiene todos los datos del dashboard en una sola llamada.
        Usado por el módulo de Producción para mostrar KPIs y consolidados.
        OPTIMIZADO: Incluye caché de 3 minutos para reducir llamadas repetidas.
        """
        # Intentar obtener del caché
        cache_key = self._cache._make_key(
            "dashboard_completo",
            fecha_inicio, fecha_fin, solo_terminadas
        )
        
        cached_data = self._cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # No está en caché, calcular...
        # 1. Obtener todas las MOs del período
        mos = self.get_mos_por_periodo(fecha_inicio, fecha_fin, solo_terminadas)
        
        if not mos:
            return {
                'overview': {
                    'total_kg_mp': 0, 'total_kg_pt': 0, 'rendimiento_promedio': 0,
                    'merma_total_kg': 0, 'merma_pct': 0, 'mos_procesadas': 0,
                    'lotes_unicos': 0, 'total_hh': 0, 'kg_por_hh': 0,
                    'proceso_kg_mp': 0, 'proceso_kg_pt': 0, 'proceso_rendimiento': 0,
                    'proceso_merma_kg': 0, 'proceso_merma_pct': 0, 'proceso_mos': 0,
                    'proceso_hh': 0, 'proceso_kg_por_hh': 0,
                    'congelado_kg_mp': 0, 'congelado_kg_pt': 0, 'congelado_rendimiento': 0,
                    'congelado_mos': 0, 'total_costo_electricidad': 0
                },
                'consolidado': {'por_fruta': [], 'por_fruta_manejo': []},
                'salas': [],
                'mos': []
            }
        
        # Acumuladores
        total_kg_mp = 0.0
        total_kg_pt = 0.0
        total_hh = 0.0
        total_costo_elec = 0.0
        lotes_set = set()
        
        # Por tipo (proceso vs congelado)
        proceso_kg_mp = 0.0
        proceso_kg_pt = 0.0
        proceso_hh = 0.0
        proceso_mos = 0
        
        congelado_kg_mp = 0.0
        congelado_kg_pt = 0.0
        congelado_mos = 0
        
        # Por fruta
        por_fruta = {}
        por_fruta_manejo = {}
        
        # Por sala
        salas_data = {}
        
        # Lista de MOs procesadas
        mos_resultado = []
        
        # Batch fetch
        consumos_by_mo = self.get_consumos_batch(mos)
        produccion_by_mo = self.get_produccion_batch(mos)
        costos_op_by_mo = self.get_costos_operacionales_batch(mos)
        
        # Procesar cada MO
        for mo in mos:
            try:
                mo_id = mo.get('id')
                
                consumos = consumos_by_mo.get(mo_id, [])
                produccion = produccion_by_mo.get(mo_id, [])
                costos_op = costos_op_by_mo.get(mo_id, {'costo_electricidad': 0})
                
                kg_mp = sum(c.get('qty_done', 0) or 0 for c in consumos)
                
                # FILTRAR kg_pt: Excluir subproductos intermedios
                # Los productos intermedios tienen código [1.x] y contienen "PROCESO" o "TÚNEL"
                kg_pt = 0.0
                kg_pt_debug = []  # Debug temporal
                for p in produccion:
                    product_name = p.get('product_name', '')
                    product_upper = product_name.upper()
                    qty = p.get('qty_done', 0) or 0
                    
                    # Excluir productos intermedios [1.x] PROCESO/TÚNEL
                    is_intermediate = False
                    if product_name.startswith('[1.') or product_name.startswith('[1,'):
                        if 'PROCESO' in product_upper or 'TUNEL' in product_upper or 'TÚNEL' in product_upper:
                            is_intermediate = True
                    
                    kg_pt_debug.append(f"{product_name[:50]}: {qty} kg ({'EXCLUIDO' if is_intermediate else 'INCLUIDO'})")
                    
                    if not is_intermediate:
                        kg_pt += qty
                
                # Debug: imprimir para primera MO
                if mo.get('name', '').endswith('/00104'):
                    print(f"\n{'='*80}")
                    print(f"DEBUG MO: {mo.get('name')}")
                    print(f"Producción:")
                    for line in kg_pt_debug:
                        print(f"  - {line}")
                    print(f"kg_pt FINAL: {kg_pt}")
                    print(f"{'='*80}\n")
                
                costo_elec = costos_op.get('costo_electricidad', 0)
                
                if kg_mp == 0:
                    continue
                
                rendimiento = (kg_pt / kg_mp * 100)
                
                # Clasificar sala
                product_name = ''
                prod = mo.get('product_id')
                if isinstance(prod, (list, tuple)) and len(prod) > 1:
                    product_name = prod[1]
                
                sala_raw = mo.get('x_studio_sala_de_proceso') or ''
                sala, sala_tipo = self._classify_sala(sala_raw, product_name)
                
                # HH
                hh = mo.get('x_studio_hh_efectiva') or 0
                if isinstance(hh, (int, float)):
                    total_hh += hh
                
                # Totales
                total_kg_mp += kg_mp
                total_kg_pt += kg_pt
                total_costo_elec += costo_elec
                
                # Lotes únicos
                for c in consumos:
                    if c.get('lot_id'):
                        lotes_set.add(c['lot_id'])
                
                # Por tipo
                if sala_tipo == 'PROCESO':
                    proceso_kg_mp += kg_mp
                    proceso_kg_pt += kg_pt
                    proceso_hh += hh if isinstance(hh, (int, float)) else 0
                    proceso_mos += 1
                elif sala_tipo == 'CONGELADO':
                    congelado_kg_mp += kg_mp
                    congelado_kg_pt += kg_pt
                    congelado_mos += 1
                
                # Especie y manejo para consolidado
                especies_en_mo = set()
                manejos_en_mo = set()
                
                for c in consumos:
                    esp = c.get('especie', '') or 'Otro'
                    man = c.get('manejo', '') or 'Otro'
                    if esp and esp != 'Otro':
                        especies_en_mo.add(esp)
                    manejos_en_mo.add(man)
                
                if len(especies_en_mo) > 1:
                    tipo_fruta = 'Mix'
                elif len(especies_en_mo) == 1:
                    tipo_fruta = list(especies_en_mo)[0]
                else:
                    tipo_fruta = self._extract_fruit_type(consumos[0].get('product_name', '')) if consumos else 'Otro'
                
                if 'Orgánico' in manejos_en_mo:
                    manejo = 'Orgánico'
                elif 'Convencional' in manejos_en_mo:
                    manejo = 'Convencional'
                else:
                    manejo = list(manejos_en_mo)[0] if manejos_en_mo else 'Otro'
                
                # Solo proceso para consolidado (no congelado)
                if sala_tipo == 'PROCESO':
                    if tipo_fruta not in por_fruta:
                        por_fruta[tipo_fruta] = {'tipo_fruta': tipo_fruta, 'kg_mp': 0, 'kg_pt': 0, 'num_lotes': 0}
                    por_fruta[tipo_fruta]['kg_mp'] += kg_mp
                    por_fruta[tipo_fruta]['kg_pt'] += kg_pt
                    por_fruta[tipo_fruta]['num_lotes'] += len(set(c.get('lot_id') for c in consumos if c.get('lot_id')))
                    
                    key_fm = f"{tipo_fruta}|{manejo}"
                    if key_fm not in por_fruta_manejo:
                        por_fruta_manejo[key_fm] = {'tipo_fruta': tipo_fruta, 'manejo': manejo, 'kg_mp': 0, 'kg_pt': 0}
                    por_fruta_manejo[key_fm]['kg_mp'] += kg_mp
                    por_fruta_manejo[key_fm]['kg_pt'] += kg_pt
                
                # Salas
                if sala not in salas_data:
                    salas_data[sala] = {'sala': sala, 'kg_mp': 0, 'kg_pt': 0, 'hh_total': 0, 
                                       'dotacion_sum': 0, 'duracion_total': 0, 'num_mos': 0}
                
                salas_data[sala]['kg_mp'] += kg_mp
                salas_data[sala]['kg_pt'] += kg_pt
                salas_data[sala]['hh_total'] += hh if isinstance(hh, (int, float)) else 0
                
                dotacion = mo.get('x_studio_dotacin') or 0
                salas_data[sala]['dotacion_sum'] += dotacion if isinstance(dotacion, (int, float)) else 0
                
                # Duración
                duracion_horas = 0
                inicio = mo.get('x_studio_inicio_de_proceso') or mo.get('date_start')
                fin = mo.get('x_studio_termino_de_proceso') or mo.get('date_finished')
                if inicio and fin:
                    try:
                        if isinstance(inicio, str):
                            d0 = datetime.strptime(inicio, "%Y-%m-%d %H:%M:%S")
                        else:
                            d0 = inicio
                        if isinstance(fin, str):
                            d1 = datetime.strptime(fin, "%Y-%m-%d %H:%M:%S")
                        else:
                            d1 = fin
                        duracion_horas = round((d1 - d0).total_seconds() / 3600, 2)
                    except Exception:
                        pass
                
                salas_data[sala]['duracion_total'] += duracion_horas
                salas_data[sala]['num_mos'] += 1
                
                # MO resultado
                fecha_raw = mo.get('date_planned_start', '') or ''
                fecha = str(fecha_raw)[:10] if fecha_raw else ''
                kg_por_hora = mo.get('x_studio_kghora_efectiva') or 0
                
                mos_resultado.append({
                    'mo_id': mo.get('id', 0),
                    'mo_name': mo.get('name', ''),
                    'product_name': product_name,
                    'especie': tipo_fruta,
                    'manejo': manejo,
                    'kg_mp': round(kg_mp, 2),
                    'kg_pt': round(kg_pt, 2),
                    'rendimiento': round(rendimiento, 2),
                    'merma': round(kg_mp - kg_pt, 2),
                    'costo_electricidad': costo_elec,
                    'duracion_horas': duracion_horas,
                    'hh': hh if isinstance(hh, (int, float)) else 0,
                    'kg_por_hora': kg_por_hora if isinstance(kg_por_hora, (int, float)) else 0,
                    'dotacion': dotacion if isinstance(dotacion, (int, float)) else 0,
                    'sala': sala,
                    'sala_tipo': sala_tipo,
                    'fecha': fecha
                })
                
            except Exception:
                continue
        
        # Calcular KPIs finales
        rendimiento_promedio = (total_kg_pt / total_kg_mp * 100) if total_kg_mp > 0 else 0
        merma_total = total_kg_mp - total_kg_pt
        merma_pct = (merma_total / total_kg_mp * 100) if total_kg_mp > 0 else 0
        kg_por_hh = (total_kg_pt / total_hh) if total_hh > 0 else 0
        
        proceso_rendimiento = (proceso_kg_pt / proceso_kg_mp * 100) if proceso_kg_mp > 0 else 0
        proceso_merma = proceso_kg_mp - proceso_kg_pt
        proceso_merma_pct = (proceso_merma / proceso_kg_mp * 100) if proceso_kg_mp > 0 else 0
        proceso_kg_por_hh = (proceso_kg_pt / proceso_hh) if proceso_hh > 0 else 0
        
        congelado_rendimiento = (congelado_kg_pt / congelado_kg_mp * 100) if congelado_kg_mp > 0 else 0
        
        # Overview
        overview = {
            'total_kg_mp': round(total_kg_mp, 2),
            'total_kg_pt': round(total_kg_pt, 2),
            'rendimiento_promedio': round(rendimiento_promedio, 2),
            'merma_total_kg': round(merma_total, 2),
            'merma_pct': round(merma_pct, 2),
            'mos_procesadas': len(mos),
            'lotes_unicos': len(lotes_set),
            'total_hh': round(total_hh, 2),
            'kg_por_hh': round(kg_por_hh, 2),
            # Proceso
            'proceso_kg_mp': round(proceso_kg_mp, 2),
            'proceso_kg_pt': round(proceso_kg_pt, 2),
            'proceso_rendimiento': round(proceso_rendimiento, 2),
            'proceso_merma_kg': round(proceso_merma, 2),
            'proceso_merma_pct': round(proceso_merma_pct, 2),
            'proceso_mos': proceso_mos,
            'proceso_hh': round(proceso_hh, 2),
            'proceso_kg_por_hh': round(proceso_kg_por_hh, 2),
            # Congelado
            'congelado_kg_mp': round(congelado_kg_mp, 2),
            'congelado_kg_pt': round(congelado_kg_pt, 2),
            'congelado_rendimiento': round(congelado_rendimiento, 2),
            'congelado_mos': congelado_mos,
            # Costos
            'total_costo_electricidad': round(total_costo_elec, 2)
        }
        
        # Consolidado por fruta
        resultado_fruta = []
        for _, data in por_fruta.items():
            kg_mp = data['kg_mp']
            kg_pt = data['kg_pt']
            resultado_fruta.append({
                **data,
                'rendimiento': round((kg_pt / kg_mp * 100) if kg_mp > 0 else 0, 2),
                'merma': round(kg_mp - kg_pt, 2)
            })
        resultado_fruta.sort(key=lambda x: x['kg_pt'], reverse=True)
        
        resultado_fruta_manejo = []
        for _, data in por_fruta_manejo.items():
            kg_mp = data['kg_mp']
            kg_pt = data['kg_pt']
            resultado_fruta_manejo.append({
                **data,
                'rendimiento': round((kg_pt / kg_mp * 100) if kg_mp > 0 else 0, 2),
                'merma': round(kg_mp - kg_pt, 2)
            })
        resultado_fruta_manejo.sort(key=lambda x: (x['tipo_fruta'], -x['kg_pt']))
        
        consolidado = {
            'por_fruta': resultado_fruta,
            'por_fruta_manejo': resultado_fruta_manejo
        }
        
        # Salas
        resultado_salas = []
        for sala, data in salas_data.items():
            kg_pt = data['kg_pt']
            kg_mp = data['kg_mp']
            hh = data['hh_total']
            duracion = data['duracion_total']
            num_mos = data['num_mos']
            dotacion_prom = data['dotacion_sum'] / num_mos if num_mos > 0 else 0
            
            resultado_salas.append({
                'sala': sala,
                'kg_mp': round(kg_mp, 2),
                'kg_pt': round(kg_pt, 2),
                'rendimiento': round((kg_pt / kg_mp * 100) if kg_mp > 0 else 0, 2),
                'merma': round(kg_mp - kg_pt, 2),
                'kg_por_hh': round(kg_pt / hh if hh > 0 else 0, 2),
                'kg_por_hora': round(kg_pt / duracion if duracion > 0 else 0, 2),
                'kg_por_operario': round(kg_pt / dotacion_prom if dotacion_prom > 0 else 0, 2),
                'hh_total': round(hh, 2),
                'dotacion_promedio': round(dotacion_prom, 1),
                'num_mos': num_mos
            })
        resultado_salas.sort(key=lambda x: x['kg_pt'], reverse=True)
        
        # MOs ordenadas
        mos_resultado.sort(key=lambda x: x['fecha'], reverse=True)
        
        result = {
            'overview': overview,
            'consolidado': consolidado,
            'salas': resultado_salas,
            'mos': mos_resultado
        }
        
        # Guardar en caché con TTL de 180 segundos (3 minutos)
        self._cache.set(cache_key, result, ttl=180)
        
        return result

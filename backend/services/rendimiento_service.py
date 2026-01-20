"""
Servicio de Rendimiento Productivo.
Incluye funciones para trazabilidad inversa Y datos dashboard para Producción.
OPTIMIZADO: Incluye caché para reducir llamadas repetidas a Odoo.
"""
from typing import Optional, Dict, List
from datetime import datetime
from shared.odoo_client import OdooClient
from backend.cache import get_cache
from .rendimiento.helpers import (
    is_operational_cost,
    is_excluded_consumo,
    extract_fruit_type,
    extract_handling,
    classify_sala
)


class RendimientoService:
    """
    Servicio para análisis de rendimiento productivo.
    - Trazabilidad inversa: PT → MP
    - Dashboard consolidado para módulo de Producción
    """
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self._cache = get_cache()
    
    # ===========================================
    # FUNCIONES AUXILIARES - Delegadas a helpers
    # ===========================================
    
    def _is_operational_cost(self, product_name: str) -> bool:
        """Identifica costos operacionales (electricidad, servicios)"""
        return is_operational_cost(product_name)
    
    def _is_excluded_consumo(self, product_name: str, category_name: str = '') -> bool:
        """Verifica si un producto debe excluirse del consumo MP."""
        return is_excluded_consumo(product_name, category_name)
    
    def _extract_fruit_type(self, product_name: str) -> str:
        """Extrae el tipo de fruta del nombre del producto."""
        return extract_fruit_type(product_name)
    
    def _extract_handling(self, product_name: str) -> str:
        """Extrae el manejo (orgánico/convencional) del nombre."""
        return extract_handling(product_name)
    
    def _classify_sala(self, sala_name: str, product_name: str = '') -> tuple:
        """Clasifica una sala o producto como PROCESO o CONGELADO."""
        # Helper retorna (tipo, nombre) - Necesitamos invertir para compatibilidad
        tipo, nombre = classify_sala(sala_name, product_name)
        return (nombre, tipo)
    
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
             'x_studio_sala_de_proceso', 'x_studio_dotacin', 'x_studio_hh_efectiva', 'x_studio_hh',
             'x_studio_kghora_efectiva', 'x_studio_inicio_de_proceso', 'x_studio_termino_de_proceso',
             'x_studio_horas_detencion_totales', 'x_studio_kghh_efectiva',
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
        # Límite alto para evitar truncamiento con muchas MOs
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', all_raw_ids]],
            ['move_id', 'product_id', 'lot_id', 'qty_done'],
            limit=50000
        )
        
        # Obtener info de productos (especie y manejo desde product.template)
        product_ids_set = set()
        for ml in move_lines or []:
            prod = ml.get('product_id')
            if prod:
                pid = prod[0] if isinstance(prod, (list, tuple)) else prod
                product_ids_set.add(pid)
        
        # Obtener product.product para sacar product_tmpl_id
        product_info_map = {}
        if product_ids_set:
            products = self.odoo.search_read(
                'product.product',
                [['id', 'in', list(product_ids_set)]],
                ['id', 'product_tmpl_id'],
                limit=20000
            )
            
            # Obtener templates con manejo y tipo de fruta
            template_ids = set()
            for p in products:
                tmpl = p.get('product_tmpl_id')
                if tmpl:
                    tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
                    template_ids.add(tmpl_id)
            
            template_map = {}
            if template_ids:
                templates = self.odoo.read(
                    'product.template',
                    list(template_ids),
                    ['id', 'x_studio_categora_tipo_de_manejo', 'x_studio_sub_categora']
                )
                for t in templates:
                    manejo = t.get('x_studio_categora_tipo_de_manejo', '')
                    if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                        manejo = manejo[1]
                    
                    tipo_fruta = t.get('x_studio_sub_categora', '')
                    if isinstance(tipo_fruta, (list, tuple)) and len(tipo_fruta) > 1:
                        tipo_fruta = tipo_fruta[1]
                    
                    template_map[t['id']] = {
                        'manejo': manejo or 'Otro',
                        'tipo_fruta': tipo_fruta or 'Otro'
                    }
            
            # Mapear product_id -> especie/manejo
            for p in products:
                pid = p.get('id')
                tmpl = p.get('product_tmpl_id')
                tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl if tmpl else None
                tmpl_data = template_map.get(tmpl_id, {'manejo': 'Otro', 'tipo_fruta': 'Otro'})
                product_info_map[pid] = tmpl_data
        
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
                prod_id = prod[0] if isinstance(prod, (list, tuple)) else prod
                prod_name = prod[1] if isinstance(prod, (list, tuple)) and len(prod) > 1 else ''
                
                # Obtener especie y manejo reales desde product.template
                prod_info = product_info_map.get(prod_id, {'manejo': 'Otro', 'tipo_fruta': 'Otro'})
                especie = prod_info['tipo_fruta']
                manejo = prod_info['manejo']
                
                # Excluir si no tiene especie Y manejo (es insumo)
                if is_excluded_consumo(prod_name, especie=especie, manejo=manejo):
                    continue
                
                lot = ml.get('lot_id')
                
                result[mo_id].append({
                    'product_id': prod_id,
                    'product_name': prod_name,
                    'lot_id': lot[0] if isinstance(lot, (list, tuple)) and lot else None,
                    'lot_name': lot[1] if isinstance(lot, (list, tuple)) and len(lot) > 1 else None,
                    'qty_done': ml.get('qty_done', 0) or 0,
                    'especie': especie,
                    'manejo': manejo
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
        
        # Límite alto para evitar truncamiento con muchas MOs
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', all_prod_ids]],
            ['move_id', 'product_id', 'lot_id', 'qty_done'],
            limit=50000
        )
        
        # Obtener info de productos (especie y manejo desde product.template)
        product_ids_set = set()
        for ml in move_lines or []:
            prod = ml.get('product_id')
            if prod:
                pid = prod[0] if isinstance(prod, (list, tuple)) else prod
                product_ids_set.add(pid)
        
        # Obtener product.product para sacar product_tmpl_id
        product_info_map = {}
        if product_ids_set:
            products = self.odoo.search_read(
                'product.product',
                [['id', 'in', list(product_ids_set)]],
                ['id', 'product_tmpl_id'],
                limit=20000
            )
            
            # Obtener templates con manejo y tipo de fruta
            template_ids = set()
            for p in products:
                tmpl = p.get('product_tmpl_id')
                if tmpl:
                    tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
                    template_ids.add(tmpl_id)
            
            template_map = {}
            if template_ids:
                templates = self.odoo.read(
                    'product.template',
                    list(template_ids),
                    ['id', 'x_studio_categora_tipo_de_manejo', 'x_studio_sub_categora', 'categ_id']
                )
                for t in templates:
                    manejo = t.get('x_studio_categora_tipo_de_manejo', '')
                    if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
                        manejo = manejo[1]
                    
                    tipo_fruta = t.get('x_studio_sub_categora', '')
                    if isinstance(tipo_fruta, (list, tuple)) and len(tipo_fruta) > 1:
                        tipo_fruta = tipo_fruta[1]
                    
                    # Obtener categoría para identificar merma
                    categ = t.get('categ_id')
                    categ_name = categ[1] if isinstance(categ, (list, tuple)) and len(categ) > 1 else ''
                    
                    template_map[t['id']] = {
                        'manejo': manejo or 'Otro',
                        'tipo_fruta': tipo_fruta or 'Otro',
                        'categ_name': categ_name
                    }
            
            # Mapear product_id -> especie/manejo
            for p in products:
                pid = p.get('id')
                tmpl = p.get('product_tmpl_id')
                tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl if tmpl else None
                tmpl_data = template_map.get(tmpl_id, {'manejo': 'Otro', 'tipo_fruta': 'Otro'})
                product_info_map[pid] = tmpl_data
        
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
                prod_id = prod[0] if isinstance(prod, (list, tuple)) else prod
                prod_name = prod[1] if isinstance(prod, (list, tuple)) and len(prod) > 1 else ''
                lot = ml.get('lot_id')
                
                # Obtener especie, manejo y categoría desde product.template
                prod_info = product_info_map.get(prod_id, {'manejo': 'Otro', 'tipo_fruta': 'Otro', 'categ_name': ''})
                categ_name = prod_info.get('categ_name', '')
                
                # Identificar si es merma (categoría contiene "MERMA")
                is_merma = 'MERMA' in categ_name.upper() if categ_name else False
                
                # Identificar si es proceso intermedio:
                # - Solo productos con nombre exacto "[X] PROCESO..." o "[X.Y] PROCESO..."  
                # - NO productos terminados con código de producto (ejemplo: [401274000])
                is_proceso = False
                if prod_name:
                    # Productos intermedios específicos: [3] Proceso de Vaciado, [1.x] PROCESO, etc.
                    if prod_name.startswith('[3]') and 'PROCESO' in prod_name.upper():
                        is_proceso = True
                    elif prod_name.startswith('[1.') and 'PROCESO' in prod_name.upper():
                        is_proceso = True
                    elif prod_name.startswith('[2.') and 'PROCESO' in prod_name.upper():
                        is_proceso = True
                    elif prod_name.startswith('[4]') and 'PROCESO' in prod_name.upper():
                        is_proceso = True
                    # Solo categoría PROCESO (sin código de producto largo)
                    elif 'PROCESOS' in categ_name.upper() and not any(c.isdigit() for c in prod_name[1:7]):
                        is_proceso = True
                
                result[mo_id].append({
                    'product_id': prod_id,
                    'product_name': prod_name,
                    'lot_id': lot[0] if isinstance(lot, (list, tuple)) and lot else None,
                    'lot_name': lot[1] if isinstance(lot, (list, tuple)) and len(lot) > 1 else None,
                    'qty_done': ml.get('qty_done', 0) or 0,
                    'especie': prod_info['tipo_fruta'],
                    'manejo': prod_info['manejo'],
                    'categ_name': categ_name,
                    'is_merma': is_merma,
                    'is_proceso': is_proceso
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
    # TRAZABILIDAD COMPLETA POR PALLETS
    # ===========================================
    
    def get_trazabilidad_pallets(self, pallet_names: List[str]) -> Dict:
        """
        Trazabilidad completa de uno o varios pallets.
        Rastrea desde el pallet físico hasta el productor original,
        pasando por todas las etapas de producción.
        
        Args:
            pallet_names: Lista de nombres de pallets a rastrear
        
        Returns:
            Dict con trazabilidad completa de todos los pallets
        """
        resultados = []
        
        for pallet_name in pallet_names:
            try:
                trazabilidad = self._rastrear_pallet_completo(pallet_name)
                resultados.append(trazabilidad)
            except Exception as e:
                resultados.append({
                    'pallet': pallet_name,
                    'error': str(e),
                    'cadena': []
                })
        
        return {
            'pallets_rastreados': len(resultados),
            'pallets': resultados,
            'fecha_consulta': datetime.now().isoformat()
        }
    
    def _rastrear_pallet_completo(self, pallet_name: str) -> Dict:
        """Rastrea un pallet completo hasta el productor."""
        
        # 1. Buscar el pallet
        pallet = self.odoo.search_read(
            'stock.quant.package',
            [['name', '=', pallet_name]],
            ['id', 'name', 'location_id'],
            limit=1
        )
        
        if not pallet:
            return {
                'pallet': pallet_name,
                'error': f'Pallet {pallet_name} no encontrado',
                'cadena': []
            }
        
        pallet_id = pallet[0]['id']
        
        # 2. Buscar movimientos del pallet
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['result_package_id', '=', pallet_id]],
            ['id', 'lot_id', 'product_id', 'qty_done', 'picking_id', 'date'],
            order='date desc',
            limit=10
        )
        
        if not move_lines:
            return {
                'pallet': pallet_name,
                'error': 'No se encontraron movimientos para este pallet',
                'cadena': []
            }
        
        # 3. Tomar el lote más reciente
        lote_pt = move_lines[0].get('lot_id')
        if not lote_pt:
            return {
                'pallet': pallet_name,
                'error': 'El pallet no tiene lote asignado',
                'cadena': []
            }
        
        lote_pt_id = lote_pt[0]
        lote_pt_name = lote_pt[1]
        product_pt = move_lines[0].get('product_id')
        qty_pt = move_lines[0].get('qty_done', 0)
        
        # 4. Rastrear recursivamente
        cadena = []
        lotes_procesados = set()
        self._rastrear_lote_recursivo(lote_pt_id, cadena, lotes_procesados, nivel=0)
        
        # 5. Calcular resumen
        resumen = self._generar_resumen_pallet(cadena, qty_pt)
        
        return {
            'pallet': pallet_name,
            'lote_pt': lote_pt_name,
            'producto_pt': product_pt[1] if product_pt else 'N/A',
            'kg_pt': round(qty_pt, 2),
            'cadena': cadena,
            'resumen': resumen
        }
    
    def _rastrear_lote_recursivo(self, lot_id: int, cadena: List[Dict], 
                                  lotes_procesados: set, nivel: int = 0):
        """Rastrea recursivamente un lote hasta encontrar el origen."""
        
        # Evitar loops infinitos
        if lot_id in lotes_procesados:
            return
        
        lotes_procesados.add(lot_id)
        
        # Obtener info del lote
        lote = self.odoo.search_read(
            'stock.lot',
            [['id', '=', lot_id]],
            ['id', 'name', 'product_id', 'create_date'],
            limit=1
        )
        
        if not lote:
            return
        
        lote_info = lote[0]
        product_info = lote_info.get('product_id')
        
        # Buscar primer movimiento del lote (creación)
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['lot_id', '=', lot_id]],
            ['id', 'move_id', 'date', 'location_id'],
            order='date asc',
            limit=1
        )
        
        if not move_lines:
            return
        
        move_id = move_lines[0]['move_id'][0]
        fecha_creacion = str(move_lines[0].get('date', ''))[:19]
        
        # Obtener el stock.move
        moves = self.odoo.search_read(
            'stock.move',
            [['id', '=', move_id]],
            ['id', 'production_id', 'raw_material_production_id']
        )
        
        if not moves:
            return
        
        move = moves[0]
        mo_ref = move.get('production_id')
        
        if not mo_ref:
            # Es MP (no fue producido)
            productor_info = self.get_proveedor_lote(lot_id)
            
            cadena.append({
                'nivel': nivel,
                'tipo': 'MATERIA_PRIMA',
                'lot_id': lot_id,
                'lot_name': lote_info['name'],
                'product_name': product_info[1] if product_info else 'N/A',
                'fecha': fecha_creacion[:10],
                'productor': productor_info.get('name', 'Desconocido') if productor_info else 'Desconocido',
                'fecha_recepcion': str(productor_info.get('fecha_recepcion', ''))[:10] if productor_info and productor_info.get('fecha_recepcion') else 'N/A'
            })
            return
        
        # Es un producto intermedio o final (fue producido por una MO)
        mo_id = mo_ref[0]
        
        # Obtener detalles de la MO
        mos = self.odoo.search_read(
            'mrp.production',
            [['id', '=', mo_id]],
            ['id', 'name', 'move_raw_ids', 'date_planned_start', 'x_studio_sala_de_proceso'],
            limit=1
        )
        
        if not mos:
            return
        
        mo = mos[0]
        move_raw_ids = mo.get('move_raw_ids', [])
        
        # Obtener consumos
        consumos = []
        if move_raw_ids:
            consumos_data = self.odoo.search_read(
                'stock.move.line',
                [
                    ['move_id', 'in', move_raw_ids],
                    ['lot_id', '!=', False]
                ],
                ['id', 'product_id', 'lot_id', 'qty_done']
            )
            
            for c in consumos_data:
                prod_info = c.get('product_id')
                prod_name = prod_info[1] if prod_info else ''
                
                # Filtrar insumos
                if self._is_excluded_consumo(prod_name):
                    continue
                
                lot_info = c.get('lot_id')
                if lot_info:
                    consumos.append({
                        'lot_id': lot_info[0],
                        'lot_name': lot_info[1],
                        'product_name': prod_name,
                        'qty_done': round(c.get('qty_done', 0), 2)
                    })
        
        # Agregar registro a la cadena
        cadena.append({
            'nivel': nivel,
            'tipo': 'PROCESO',
            'lot_id': lot_id,
            'lot_name': lote_info['name'],
            'product_name': product_info[1] if product_info else 'N/A',
            'fecha': fecha_creacion[:10],
            'mo_id': mo['id'],
            'mo_name': mo['name'],
            'sala': mo.get('x_studio_sala_de_proceso', 'N/A'),
            'fecha_mo': str(mo.get('date_planned_start', ''))[:10],
            'consumos': consumos,
            'total_kg_consumido': round(sum(c['qty_done'] for c in consumos), 2)
        })
        
        # Rastrear recursivamente cada lote consumido
        for consumo in consumos:
            self._rastrear_lote_recursivo(
                consumo['lot_id'], 
                cadena, 
                lotes_procesados, 
                nivel + 1
            )
    
    def _generar_resumen_pallet(self, cadena: List[Dict], qty_pt: float) -> Dict:
        """Genera resumen de rendimiento del pallet."""
        
        procesos = [r for r in cadena if r['tipo'] == 'PROCESO']
        mp = [r for r in cadena if r['tipo'] == 'MATERIA_PRIMA']
        
        # Calcular kg total de MP
        total_kg_mp = 0.0
        if procesos:
            # Buscar el proceso de nivel más alto (vaciado)
            nivel_max = max(r['nivel'] for r in procesos)
            procesos_max_nivel = [r for r in procesos if r['nivel'] == nivel_max]
            
            for p in procesos_max_nivel:
                total_kg_mp += p.get('total_kg_consumido', 0)
        
        # Rendimiento total
        rendimiento = (qty_pt / total_kg_mp * 100) if total_kg_mp > 0 else 0
        
        # Etapas
        etapas = []
        for p in sorted(procesos, key=lambda x: x['nivel'], reverse=True):
            etapas.append({
                'etapa': p.get('sala', 'N/A'),
                'mo': p['mo_name'],
                'fecha': p['fecha_mo']
            })
        
        # Productores
        productores = list(set(r['productor'] for r in mp if r.get('productor')))
        
        return {
            'total_procesos': len(procesos),
            'total_lotes_mp': len(mp),
            'kg_mp_total': round(total_kg_mp, 2),
            'kg_pt': round(qty_pt, 2),
            'rendimiento_total': round(rendimiento, 2),
            'merma_kg': round(total_kg_mp - qty_pt, 2),
            'merma_pct': round(100 - rendimiento, 2),
            'etapas': etapas,
            'productores': productores
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
        total_kg_merma = 0.0  # Nueva: Total de merma
        total_hh = 0.0
        total_costo_elec = 0.0
        lotes_set = set()
        
        # Por tipo (proceso vs congelado)
        proceso_kg_mp = 0.0
        proceso_kg_pt = 0.0
        proceso_kg_merma = 0.0  # Nueva: Merma en proceso
        proceso_hh = 0.0
        proceso_mos = 0
        
        congelado_kg_mp = 0.0
        congelado_kg_pt = 0.0
        congelado_kg_merma = 0.0  # Nueva: Merma en congelado
        congelado_mos = 0
        congelado_lotes = set()
        congelado_proveedores = set()
        
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
                
                # FILTRAR kg_pt: Usar is_merma e is_proceso de categ_id
                # - is_merma: Categoría contiene "MERMA" (PRODUCTOS / MERMA DE PROCESOS)
                # - is_proceso: Producto [3] o categoría PROCESO (productos intermedios)
                kg_pt = 0.0
                kg_merma = 0.0
                kg_proceso = 0.0
                for p in produccion:
                    product_name = p.get('product_name', '')
                    qty = p.get('qty_done', 0) or 0
                    
                    # Usar flags de categoría
                    is_merma = p.get('is_merma', False)
                    is_proceso = p.get('is_proceso', False)
                    
                    if is_merma:
                        kg_merma += qty
                    elif is_proceso:
                        kg_proceso += qty
                    else:
                        # PT válido
                        kg_pt += qty
                
                
                costo_elec = costos_op.get('costo_electricidad', 0)
                
                if kg_mp == 0:
                    continue
                
                # Fallback: si no hay merma identificada por categ_id Y kg_pt < kg_mp, usar diferencia
                # Si kg_pt >= kg_mp (rendimiento >= 100%), NO agregar merma calculada
                if kg_merma == 0 and kg_pt < kg_mp:
                    merma_calculada = kg_mp - kg_pt - kg_proceso
                    kg_merma = max(0, merma_calculada)  # Solo si es positiva
                
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
                total_kg_merma += kg_merma  # Nueva: acumular merma
                total_costo_elec += costo_elec
                
                # Lotes únicos
                for c in consumos:
                    if c.get('lot_id'):
                        lotes_set.add(c['lot_id'])
                
                # Por tipo
                if sala_tipo == 'PROCESO':
                    proceso_kg_mp += kg_mp
                    proceso_kg_pt += kg_pt
                    proceso_kg_merma += kg_merma  # Nueva: merma en proceso
                    proceso_hh += hh if isinstance(hh, (int, float)) else 0
                    proceso_mos += 1
                elif sala_tipo == 'CONGELADO':
                    congelado_kg_mp += kg_mp
                    congelado_kg_pt += kg_pt
                    congelado_kg_merma += kg_merma  # Nueva: merma en congelado
                    congelado_mos += 1
                    # Agregar lotes únicos para congelado
                    for c in consumos:
                        if c.get('lot_id'):
                            congelado_lotes.add(c['lot_id'])
                        # Agregar proveedores únicos
                        if c.get('proveedor'):
                            congelado_proveedores.add(c['proveedor'])
                
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
                    salas_data[sala] = {
                        'sala': sala, 
                        'kg_mp': 0, 
                        'kg_pt': 0, 
                        'hh_total': 0,
                        'hh_efectiva_total': 0,
                        'detenciones_total': 0,
                        'dotacion_sum': 0, 
                        'duracion_total': 0, 
                        'num_mos': 0,
                        'costo_electricidad': 0,  # Costo eléctrico acumulado
                        'total_electricidad': 0   # Total kWh
                    }
                
                salas_data[sala]['kg_mp'] += kg_mp
                salas_data[sala]['kg_pt'] += kg_pt
                salas_data[sala]['hh_total'] += hh if isinstance(hh, (int, float)) else 0
                
                # Acumular electricidad por sala
                salas_data[sala]['costo_electricidad'] += costo_elec
                salas_data[sala]['total_electricidad'] += costo_elec  # kWh = mismo valor por ahora
                
                # HH Efectiva
                hh_efectiva = mo.get('x_studio_hh_efectiva') or 0
                salas_data[sala]['hh_efectiva_total'] += hh_efectiva if isinstance(hh_efectiva, (int, float)) else 0
                
                # Detenciones
                detenciones = mo.get('x_studio_horas_detencion_totales') or 0
                salas_data[sala]['detenciones_total'] += detenciones if isinstance(detenciones, (int, float)) else 0
                
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
                    'kg_merma': round(kg_merma, 2),  # Nueva: Merma real identificada por categ_id
                    'rendimiento': round(rendimiento, 2),
                    'merma_pct': round((kg_merma / kg_mp * 100) if kg_mp > 0 else 0, 2),  # % de merma
                    'costo_electricidad': costo_elec,
                    'duracion_horas': duracion_horas,
                    'hh': hh if isinstance(hh, (int, float)) else 0,
                    'kg_por_hora': kg_por_hora if isinstance(kg_por_hora, (int, float)) else 0,
                    'dotacion': dotacion if isinstance(dotacion, (int, float)) else 0,
                    'sala': sala,
                    'sala_original': mo.get('x_studio_sala_de_proceso', '') or '',
                    'sala_tipo': sala_tipo,
                    'fecha': fecha
                })
                
            except Exception:
                continue
        
        # Calcular KPIs finales
        rendimiento_promedio = (total_kg_pt / total_kg_mp * 100) if total_kg_mp > 0 else 0
        # Usar merma REAL identificada por categ_id (no diferencia calculada)
        merma_pct = (total_kg_merma / total_kg_mp * 100) if total_kg_mp > 0 else 0
        kg_por_hh = (total_kg_pt / total_hh) if total_hh > 0 else 0
        
        proceso_rendimiento = (proceso_kg_pt / proceso_kg_mp * 100) if proceso_kg_mp > 0 else 0
        proceso_merma_pct = (proceso_kg_merma / proceso_kg_mp * 100) if proceso_kg_mp > 0 else 0
        proceso_kg_por_hh = (proceso_kg_pt / proceso_hh) if proceso_hh > 0 else 0
        
        congelado_rendimiento = (congelado_kg_pt / congelado_kg_mp * 100) if congelado_kg_mp > 0 else 0
        congelado_merma_pct = (congelado_kg_merma / congelado_kg_mp * 100) if congelado_kg_mp > 0 else 0
        
        # Overview
        overview = {
            'total_kg_mp': round(total_kg_mp, 2),
            'total_kg_pt': round(total_kg_pt, 2),
            'total_kg_merma': round(total_kg_merma, 2),  # Nueva: Merma real
            'rendimiento_promedio': round(rendimiento_promedio, 2),
            'merma_total_kg': round(total_kg_merma, 2),  # Usa merma real
            'merma_pct': round(merma_pct, 2),
            'mos_procesadas': len(mos),
            'lotes_unicos': len(lotes_set),
            'total_hh': round(total_hh, 2),
            'kg_por_hh': round(kg_por_hh, 2),
            # Proceso
            'proceso_kg_mp': round(proceso_kg_mp, 2),
            'proceso_kg_pt': round(proceso_kg_pt, 2),
            'proceso_kg_merma': round(proceso_kg_merma, 2),  # Nueva: Merma proceso
            'proceso_rendimiento': round(proceso_rendimiento, 2),
            'proceso_merma_kg': round(proceso_kg_merma, 2),  # Usa merma real
            'proceso_merma_pct': round(proceso_merma_pct, 2),
            'proceso_mos': proceso_mos,
            'proceso_hh': round(proceso_hh, 2),
            'proceso_kg_por_hh': round(proceso_kg_por_hh, 2),
            # Congelado
            'congelado_kg_mp': round(congelado_kg_mp, 2),
            'congelado_kg_pt': round(congelado_kg_pt, 2),
            'congelado_kg_merma': round(congelado_kg_merma, 2),  # Nueva: Merma congelado
            'congelado_rendimiento': round(congelado_rendimiento, 2),
            'congelado_merma_pct': round(congelado_merma_pct, 2),  # Nueva: % merma congelado
            'congelado_mos': congelado_mos,
            'congelado_lotes': len(congelado_lotes),
            'congelado_proveedores': len(congelado_proveedores),
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
            hh_efectiva = data['hh_efectiva_total']
            detenciones = data['detenciones_total']
            duracion = data['duracion_total']
            num_mos = data['num_mos']
            dotacion_prom = data['dotacion_sum'] / num_mos if num_mos > 0 else 0
            
            # Calcular KPIs adicionales
            kg_por_hora_efectiva = kg_pt / hh_efectiva if hh_efectiva > 0 else 0
            kg_por_hh_efectiva = kg_pt / hh_efectiva if hh_efectiva > 0 else 0
            detenciones_promedio = detenciones / num_mos if num_mos > 0 else 0
            hh_promedio = hh / num_mos if num_mos > 0 else 0
            hh_efectiva_promedio = hh_efectiva / num_mos if num_mos > 0 else 0
            
            # Electricidad
            costo_elec = data.get('costo_electricidad', 0)
            total_elec = data.get('total_electricidad', 0)
            kwh_por_kg = total_elec / kg_pt if kg_pt > 0 else 0
            
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
                'hh_promedio': round(hh_promedio, 2),
                'hh_efectiva_total': round(hh_efectiva, 2),
                'hh_efectiva_promedio': round(hh_efectiva_promedio, 2),
                'kg_por_hora_efectiva': round(kg_por_hora_efectiva, 2),
                'kg_por_hh_efectiva': round(kg_por_hh_efectiva, 2),
                'detenciones_total': round(detenciones, 2),
                'detenciones_promedio': round(detenciones_promedio, 2),
                'dotacion_promedio': round(dotacion_prom, 1),
                'num_mos': num_mos,
                # Electricidad (para túneles)
                'costo_electricidad': round(costo_elec, 2),
                'total_electricidad': round(total_elec, 2),
                'kwh_por_kg': round(kwh_por_kg, 4)
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

"""
Servicio de Rendimiento Productivo - Análisis de trazabilidad por lote.
Calcula rendimiento, merma y eficiencia basándose en lotes de fruta.
"""
from typing import Optional, Dict, List, Any
from datetime import datetime
from fastapi import HTTPException

from shared.odoo_client import OdooClient
from backend.utils import clean_record
from backend.cache import get_cache, OdooCache


class RendimientoService:
    """
    Servicio para análisis de rendimiento productivo por lote.
    Trazabilidad: Lote MP → MO → Lote PT
    """
    
    # Tipos de fruta a incluir (solo estos productos)
    TIPOS_FRUTA = ['arándano', 'arandano', 'frambuesa', 'frutilla', 'mora', 'cereza', 'grosella']
    
    # Categorías/productos a excluir del rendimiento
    EXCLUDED_CATEGORIES = ['insumo', 'envase', 'etiqueta', 'embalaje', 'caja', 'bolsa', 'pallet', 'bandeja']
    EXCLUDED_PRODUCTS = ['proceso', 'provisión', 'provision', 'electricidad', 'servicio']
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self._cache = get_cache()
    
    def _is_fruta(self, product_name: str) -> bool:
        """Verifica si un producto es de tipo fruta."""
        if not product_name:
            return False
        name_lower = product_name.lower()
        return any(fruta in name_lower for fruta in self.TIPOS_FRUTA)
    
    def _is_excluded(self, product_name: str, category_name: str = '') -> bool:
        """Verifica si un producto debe excluirse del cálculo."""
        if not product_name:
            return True
        name_lower = product_name.lower()
        cat_lower = (category_name or '').lower()
        
        # Excluir por categoría
        if any(exc in cat_lower for exc in self.EXCLUDED_CATEGORIES):
            return True
        # Excluir por nombre
        if any(exc in name_lower for exc in self.EXCLUDED_PRODUCTS + self.EXCLUDED_CATEGORIES):
            return True
        return False
    
    def get_mos_por_periodo(self, fecha_inicio: str, fecha_fin: str, limit: int = 500) -> List[Dict]:
        """
        Obtiene MOs terminadas en el período con sus datos de rendimiento.
        Solo incluye MOs con productos de tipo fruta.
        """
        domain = [
            ['state', '=', 'done'],
            ['date_finished', '!=', False],
            ['date_finished', '>=', fecha_inicio],
            ['date_finished', '<=', fecha_fin + ' 23:59:59']
        ]
        
        # Campos básicos que siempre existen
        basic_fields = [
            'name', 'product_id', 'product_qty', 'qty_produced',
            'date_start', 'date_finished', 'state',
            'move_raw_ids', 'move_finished_ids'
        ]
        
        # Campos custom (pueden no existir)
        custom_fields = [
            'x_studio_dotacin', 'x_studio_hh', 'x_studio_hh_efectiva',
            'x_studio_kghh_efectiva', 'x_studio_kghora_efectiva',
            'x_studio_horas_detencion_totales', 'x_studio_merma_bolsas',
            'x_studio_inicio_de_proceso', 'x_studio_termino_de_proceso',
            'x_studio_sala_de_proceso'
        ]
        
        # Intentar con todos los campos
        try:
            mos = self.odoo.search_read(
                'mrp.production',
                domain,
                basic_fields + custom_fields,
                limit=limit,
                order='date_finished desc'
            )
        except Exception:
            # Fallback: solo campos básicos
            mos = self.odoo.search_read(
                'mrp.production',
                domain,
                basic_fields,
                limit=limit,
                order='date_finished desc'
            )
        
        return [clean_record(mo) for mo in mos]
    
    def get_consumos_mo(self, mo: Dict) -> List[Dict]:
        """
        Obtiene los consumos de MP de una MO con detalle de lotes.
        Filtra solo productos de fruta.
        """
        move_raw_ids = mo.get('move_raw_ids', [])
        if not move_raw_ids:
            return []
        
        # Obtener move.lines con lotes
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', move_raw_ids]],
            ['product_id', 'lot_id', 'qty_done', 'date'],
            limit=100
        )
        
        consumos = []
        for ml in move_lines:
            prod_info = ml.get('product_id')
            prod_name = prod_info[1] if prod_info else ''
            
            # Solo incluir productos de fruta
            if not self._is_fruta(prod_name) or self._is_excluded(prod_name):
                continue
            
            lot_info = ml.get('lot_id')
            consumos.append({
                'product_id': prod_info[0] if prod_info else None,
                'product_name': prod_name,
                'lot_id': lot_info[0] if lot_info else None,
                'lot_name': lot_info[1] if lot_info else 'SIN LOTE',
                'qty_done': ml.get('qty_done', 0),
                'date': ml.get('date')
            })
        
        return consumos
    
    def get_produccion_mo(self, mo: Dict) -> List[Dict]:
        """
        Obtiene la producción de PT de una MO con detalle de lotes.
        Filtra solo productos de fruta.
        """
        move_finished_ids = mo.get('move_finished_ids', [])
        if not move_finished_ids:
            return []
        
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', move_finished_ids]],
            ['product_id', 'lot_id', 'qty_done', 'date'],
            limit=100
        )
        
        produccion = []
        for ml in move_lines:
            prod_info = ml.get('product_id')
            prod_name = prod_info[1] if prod_info else ''
            
            # Solo incluir productos de fruta (PT)
            if not self._is_fruta(prod_name) or self._is_excluded(prod_name):
                continue
            
            lot_info = ml.get('lot_id')
            produccion.append({
                'product_id': prod_info[0] if prod_info else None,
                'product_name': prod_name,
                'lot_id': lot_info[0] if lot_info else None,
                'lot_name': lot_info[1] if lot_info else 'SIN LOTE',
                'qty_done': ml.get('qty_done', 0),
                'date': ml.get('date')
            })
        
        return produccion
    
    def get_proveedor_lote(self, lot_id: int) -> Optional[Dict]:
        """
        Obtiene el proveedor de un lote buscando su recepción original.
        """
        if not lot_id:
            return None
        
        # Buscar primer movimiento del lote (recepción)
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['lot_id', '=', lot_id]],
            ['move_id', 'date'],
            limit=1,
            order='date asc'
        )
        
        if not move_lines:
            return None
        
        move_id = move_lines[0].get('move_id')
        if not move_id:
            return None
        
        # Obtener picking del movimiento
        moves = self.odoo.read('stock.move', [move_id[0]], ['picking_id'])
        if not moves or not moves[0].get('picking_id'):
            return None
        
        picking_id = moves[0]['picking_id'][0]
        pickings = self.odoo.read('stock.picking', [picking_id], ['partner_id', 'scheduled_date'])
        
        if pickings and pickings[0].get('partner_id'):
            partner = pickings[0]['partner_id']
            return {
                'id': partner[0],
                'name': partner[1],
                'fecha_recepcion': pickings[0].get('scheduled_date')
            }
        
        return None
    
    def get_overview(self, fecha_inicio: str, fecha_fin: str) -> Dict:
        """
        Obtiene KPIs consolidados del período.
        """
        mos = self.get_mos_por_periodo(fecha_inicio, fecha_fin)
        
        total_kg_mp = 0.0
        total_kg_pt = 0.0
        total_hh = 0.0
        mos_procesadas = 0
        lotes_set = set()
        proveedores_set = set()
        
        rendimientos_por_mo = []
        
        for mo in mos:
            consumos = self.get_consumos_mo(mo)
            produccion = self.get_produccion_mo(mo)
            
            if not consumos:
                continue
            
            kg_mp = sum(c['qty_done'] for c in consumos)
            kg_pt = sum(p['qty_done'] for p in produccion)
            
            if kg_mp == 0:
                continue
            
            total_kg_mp += kg_mp
            total_kg_pt += kg_pt
            hh = mo.get('x_studio_hh_efectiva') or mo.get('x_studio_hh') or 0
            total_hh += hh
            mos_procesadas += 1
            
            rend = (kg_pt / kg_mp * 100) if kg_mp > 0 else 0
            rendimientos_por_mo.append(rend)
            
            # Recolectar lotes únicos
            for c in consumos:
                if c['lot_id']:
                    lotes_set.add(c['lot_id'])
        
        rendimiento_promedio = sum(rendimientos_por_mo) / len(rendimientos_por_mo) if rendimientos_por_mo else 0
        merma_total = total_kg_mp - total_kg_pt
        merma_pct = (merma_total / total_kg_mp * 100) if total_kg_mp > 0 else 0
        kg_por_hh = (total_kg_pt / total_hh) if total_hh > 0 else 0
        
        return {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'total_kg_mp': round(total_kg_mp, 2),
            'total_kg_pt': round(total_kg_pt, 2),
            'rendimiento_promedio': round(rendimiento_promedio, 2),
            'merma_total_kg': round(merma_total, 2),
            'merma_pct': round(merma_pct, 2),
            'total_hh': round(total_hh, 2),
            'kg_por_hh': round(kg_por_hh, 2),
            'mos_procesadas': mos_procesadas,
            'lotes_unicos': len(lotes_set)
        }
    
    def get_rendimiento_por_lote(self, fecha_inicio: str, fecha_fin: str) -> List[Dict]:
        """
        Obtiene rendimiento detallado por lote de MP.
        """
        mos = self.get_mos_por_periodo(fecha_inicio, fecha_fin)
        
        # Agrupar por lote
        lotes_data = {}
        
        for mo in mos:
            consumos = self.get_consumos_mo(mo)
            produccion = self.get_produccion_mo(mo)
            
            kg_pt_mo = sum(p['qty_done'] for p in produccion)
            kg_mp_mo = sum(c['qty_done'] for c in consumos)
            
            if kg_mp_mo == 0:
                continue
            
            # Distribuir PT proporcionalmente entre lotes consumidos
            for c in consumos:
                lot_id = c['lot_id']
                if not lot_id:
                    continue
                
                lot_key = lot_id
                if lot_key not in lotes_data:
                    lotes_data[lot_key] = {
                        'lot_id': lot_id,
                        'lot_name': c['lot_name'],
                        'product_name': c['product_name'],
                        'kg_consumidos': 0,
                        'kg_producidos': 0,
                        'mos': [],
                        'proveedor': None
                    }
                
                lotes_data[lot_key]['kg_consumidos'] += c['qty_done']
                
                # Proporción de PT que corresponde a este lote
                proporcion = c['qty_done'] / kg_mp_mo if kg_mp_mo > 0 else 0
                lotes_data[lot_key]['kg_producidos'] += kg_pt_mo * proporcion
                
                if mo['name'] not in lotes_data[lot_key]['mos']:
                    lotes_data[lot_key]['mos'].append(mo['name'])
        
        # Calcular rendimiento y obtener proveedor
        resultado = []
        for lot_id, data in lotes_data.items():
            kg_c = data['kg_consumidos']
            kg_p = data['kg_producidos']
            
            data['rendimiento'] = round((kg_p / kg_c * 100) if kg_c > 0 else 0, 2)
            data['merma'] = round(kg_c - kg_p, 2)
            data['merma_pct'] = round((data['merma'] / kg_c * 100) if kg_c > 0 else 0, 2)
            data['kg_consumidos'] = round(kg_c, 2)
            data['kg_producidos'] = round(kg_p, 2)
            data['num_mos'] = len(data['mos'])
            
            # Obtener proveedor (solo para primeros lotes por performance)
            if len(resultado) < 50:
                proveedor = self.get_proveedor_lote(lot_id)
                data['proveedor'] = proveedor['name'] if proveedor else 'Desconocido'
            else:
                data['proveedor'] = 'Pendiente'
            
            resultado.append(data)
        
        # Ordenar por kg consumidos desc
        resultado.sort(key=lambda x: x['kg_consumidos'], reverse=True)
        
        return resultado
    
    def get_rendimiento_por_proveedor(self, fecha_inicio: str, fecha_fin: str) -> List[Dict]:
        """
        Agrupa el rendimiento por proveedor.
        """
        lotes = self.get_rendimiento_por_lote(fecha_inicio, fecha_fin)
        
        # Agrupar por proveedor
        proveedores_data = {}
        
        for lote in lotes:
            prov = lote.get('proveedor', 'Desconocido')
            if prov not in proveedores_data:
                proveedores_data[prov] = {
                    'proveedor': prov,
                    'kg_consumidos': 0,
                    'kg_producidos': 0,
                    'lotes': 0
                }
            
            proveedores_data[prov]['kg_consumidos'] += lote['kg_consumidos']
            proveedores_data[prov]['kg_producidos'] += lote['kg_producidos']
            proveedores_data[prov]['lotes'] += 1
        
        # Calcular rendimiento por proveedor
        resultado = []
        for prov, data in proveedores_data.items():
            kg_c = data['kg_consumidos']
            kg_p = data['kg_producidos']
            
            data['rendimiento'] = round((kg_p / kg_c * 100) if kg_c > 0 else 0, 2)
            data['merma'] = round(kg_c - kg_p, 2)
            data['kg_consumidos'] = round(kg_c, 2)
            data['kg_producidos'] = round(kg_p, 2)
            
            resultado.append(data)
        
        # Ordenar por kg consumidos desc
        resultado.sort(key=lambda x: x['kg_consumidos'], reverse=True)
        
        return resultado
    
    def get_rendimiento_mos(self, fecha_inicio: str, fecha_fin: str) -> List[Dict]:
        """
        Obtiene análisis de rendimiento por MO individual.
        """
        mos = self.get_mos_por_periodo(fecha_inicio, fecha_fin)
        
        resultado = []
        for mo in mos:
            consumos = self.get_consumos_mo(mo)
            produccion = self.get_produccion_mo(mo)
            
            kg_mp = sum(c['qty_done'] for c in consumos)
            kg_pt = sum(p['qty_done'] for p in produccion)
            
            if kg_mp == 0:
                continue
            
            rendimiento = (kg_pt / kg_mp * 100) if kg_mp > 0 else 0
            hh = mo.get('x_studio_hh_efectiva') or mo.get('x_studio_hh') or 0
            kg_por_hora = mo.get('x_studio_kghora_efectiva') or 0
            dotacion = mo.get('x_studio_dotacin') or 0
            
            # Calcular duración
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
                except:
                    pass
            
            resultado.append({
                'mo_id': mo['id'],
                'mo_name': mo['name'],
                'product_name': mo.get('product_id', {}).get('name', '') if isinstance(mo.get('product_id'), dict) else (mo.get('product_id', [None, ''])[1] if mo.get('product_id') else ''),
                'kg_mp': round(kg_mp, 2),
                'kg_pt': round(kg_pt, 2),
                'rendimiento': round(rendimiento, 2),
                'merma': round(kg_mp - kg_pt, 2),
                'duracion_horas': duracion_horas,
                'hh': hh,
                'kg_por_hora': kg_por_hora,
                'dotacion': dotacion,
                'sala': mo.get('x_studio_sala_de_proceso', ''),
                'fecha': mo.get('date_finished', '')[:10] if mo.get('date_finished') else '',
                'num_lotes_mp': len(set(c['lot_id'] for c in consumos if c['lot_id'])),
                'num_lotes_pt': len(set(p['lot_id'] for p in produccion if p['lot_id']))
            })
        
        # Ordenar por fecha desc
        resultado.sort(key=lambda x: x['fecha'], reverse=True)
        
        return resultado

"""
Servicio de Rendimiento Productivo - Análisis de trazabilidad por lote.
Calcula rendimiento, merma y eficiencia basándose en lotes de materia prima.

LÓGICA BASADA EN produccion_service.py:
- Consumos MP: Todo excepto insumos/envases
- Producción PT: Todo excepto "Proceso Retail" y merma
- Rendimiento = PT / MP * 100
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
    
    # ===== EXCLUSIONES (basado en produccion_service) =====
    # Categorías a excluir del consumo MP
    EXCLUDED_CATEGORIES = ["insumo", "envase", "etiqueta", "embalaje", "merma"]
    
    # Palabras en nombre de producto que indican insumo/envase
    EXCLUDED_PRODUCT_NAMES = [
        "caja", "bolsa", "insumo", "envase", "pallet", "etiqueta",
        "doy pe", "cajas de exportación", "caja exportación"
    ]
    
    # Productos a excluir de la producción
    EXCLUDED_PRODUCTION = ["proceso retail", "proceso", "merma"]
    
    # Códigos de fruta para extraer tipo
    FRUIT_CODES = {
        'ar': 'Arándano', 'arandano': 'Arándano', 'blueberry': 'Arándano',
        'fb': 'Frambuesa', 'frambuesa': 'Frambuesa', 'raspberry': 'Frambuesa',
        'ft': 'Frutilla', 'frutilla': 'Frutilla', 'strawberry': 'Frutilla',
        'mr': 'Mora', 'mora': 'Mora', 'blackberry': 'Mora',
        'cz': 'Cereza', 'cereza': 'Cereza', 'cherry': 'Cereza',
        'gs': 'Grosella', 'grosella': 'Grosella', 'currant': 'Grosella'
    }
    
    # Códigos de manejo
    HANDLING_CODES = {
        'conv': 'Convencional', 'convencional': 'Convencional',
        'org': 'Orgánico', 'organico': 'Orgánico', 'organic': 'Orgánico',
        'iqf': 'IQF', 'fresco': 'Fresco', 'fresh': 'Fresco'
    }
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self._cache = get_cache()
    
    def _is_excluded_consumo(self, product_name: str, category_name: str = '') -> bool:
        """
        Verifica si un producto debe excluirse del consumo MP.
        Excluye: insumos, envases, cajas, bolsas, etc.
        """
        if not product_name:
            return True
        
        name_lower = product_name.lower()
        cat_lower = (category_name or '').lower()
        
        # Excluir por categoría
        if any(exc in cat_lower for exc in self.EXCLUDED_CATEGORIES):
            return True
        
        # Excluir por nombre
        if any(exc in name_lower for exc in self.EXCLUDED_PRODUCT_NAMES):
            return True
        
        return False
    
    def _is_excluded_produccion(self, product_name: str, category_name: str = '') -> bool:
        """
        Verifica si un producto debe excluirse de la producción.
        Excluye: "Proceso Retail", merma
        """
        if not product_name:
            return True
        
        name_lower = product_name.lower()
        cat_lower = (category_name or '').lower()
        
        # Excluir "Proceso Retail" y merma
        if any(exc in name_lower for exc in self.EXCLUDED_PRODUCTION):
            return True
        
        # Excluir merma por categoría
        if "merma" in cat_lower:
            return True
        
        return False
    
    def _extract_fruit_type(self, product_name: str) -> str:
        """
        Extrae el tipo de fruta del nombre del producto.
        Ejemplo: '[101122000] AR HB Conv. IQF en Bandeja' -> 'Arándano'
        """
        if not product_name:
            return 'Desconocido'
        
        name_lower = product_name.lower()
        
        # Buscar código de fruta
        for code, fruit in self.FRUIT_CODES.items():
            if code in name_lower or f'[{code[:2].upper()}' in product_name:
                return fruit
        
        return 'Otro'
    
    def _extract_handling(self, product_name: str) -> str:
        """
        Extrae el tipo de manejo del nombre del producto.
        Ejemplo: '[101122000] AR HB Conv. IQF en Bandeja' -> 'Convencional'
        """
        if not product_name:
            return 'Desconocido'
        
        name_lower = product_name.lower()
        
        for code, handling in self.HANDLING_CODES.items():
            if code in name_lower:
                return handling
        
        return 'Otro'
    
    def get_mos_por_periodo(self, fecha_inicio: str, fecha_fin: str, limit: int = 500) -> List[Dict]:
        """
        Obtiene MOs terminadas/por cerrar en el período.
        Usa date_planned_start (fecha prevista) para filtrar.
        Incluye state 'done' y 'to_close' (producción terminada pendiente de cierre).
        """
        domain = [
            ['state', 'in', ['done', 'to_close']],  # Incluir ambos estados
            ['date_planned_start', '!=', False],
            ['date_planned_start', '>=', fecha_inicio],
            ['date_planned_start', '<=', fecha_fin + ' 23:59:59']
        ]
        
        basic_fields = [
            'name', 'product_id', 'product_qty', 'qty_produced',
            'date_start', 'date_finished', 'date_planned_start', 'state',
            'move_raw_ids', 'move_finished_ids'
        ]
        
        custom_fields = [
            'x_studio_dotacin', 'x_studio_hh', 'x_studio_hh_efectiva',
            'x_studio_kghh_efectiva', 'x_studio_kghora_efectiva',
            'x_studio_inicio_de_proceso', 'x_studio_termino_de_proceso',
            'x_studio_sala_de_proceso'
        ]
        
        try:
            mos = self.odoo.search_read(
                'mrp.production',
                domain,
                basic_fields + custom_fields,
                limit=limit,
                order='date_planned_start desc'
            )
        except Exception:
            mos = self.odoo.search_read(
                'mrp.production',
                domain,
                basic_fields,
                limit=limit,
                order='date_planned_start desc'
            )
        
        return [clean_record(mo) for mo in mos]
    
    def get_consumos_mo(self, mo: Dict) -> List[Dict]:
        """
        Obtiene los consumos de MP de una MO.
        Excluye insumos, envases, cajas, bolsas.
        """
        move_raw_ids = mo.get('move_raw_ids', [])
        if not move_raw_ids:
            return []
        
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', move_raw_ids]],
            ['product_id', 'lot_id', 'qty_done', 'date', 'product_category_name'],
            limit=200
        )
        
        consumos = []
        for ml in move_lines:
            try:
                prod_info = ml.get('product_id')
                prod_name = prod_info[1] if prod_info else ''
                category = ml.get('product_category_name', '') or ''
                
                # Excluir insumos/envases
                if self._is_excluded_consumo(prod_name, category):
                    continue
                
                qty = ml.get('qty_done', 0) or 0
                if qty <= 0:
                    continue
                
                lot_info = ml.get('lot_id')
                consumos.append({
                    'product_id': prod_info[0] if prod_info else None,
                    'product_name': prod_name,
                    'lot_id': lot_info[0] if lot_info else None,
                    'lot_name': lot_info[1] if lot_info else 'SIN LOTE',
                    'qty_done': qty,
                    'date': ml.get('date'),
                    'category': category
                })
            except Exception:
                continue
        
        return consumos
    
    def get_produccion_mo(self, mo: Dict) -> List[Dict]:
        """
        Obtiene la producción de PT de una MO.
        Excluye "Proceso Retail" y merma.
        """
        move_finished_ids = mo.get('move_finished_ids', [])
        if not move_finished_ids:
            return []
        
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', move_finished_ids]],
            ['product_id', 'lot_id', 'qty_done', 'date', 'product_category_name'],
            limit=200
        )
        
        produccion = []
        for ml in move_lines:
            try:
                prod_info = ml.get('product_id')
                prod_name = prod_info[1] if prod_info else ''
                category = ml.get('product_category_name', '') or ''
                
                # Excluir "Proceso Retail" y merma
                if self._is_excluded_produccion(prod_name, category):
                    continue
                
                qty = ml.get('qty_done', 0) or 0
                if qty <= 0:
                    continue
                
                lot_info = ml.get('lot_id')
                produccion.append({
                    'product_id': prod_info[0] if prod_info else None,
                    'product_name': prod_name,
                    'lot_id': lot_info[0] if lot_info else None,
                    'lot_name': lot_info[1] if lot_info else 'SIN LOTE',
                    'qty_done': qty,
                    'date': ml.get('date'),
                    'category': category
                })
            except Exception:
                continue
        
        return produccion
    
    def get_proveedor_lote(self, lot_id: int) -> Optional[Dict]:
        """
        Obtiene el proveedor de un lote buscando su recepción original.
        Busca específicamente el movimiento desde 'Vendors' o picking de recepción.
        """
        if not lot_id:
            return None
        
        try:
            # Obtener TODOS los movimientos del lote para encontrar la recepción
            move_lines = self.odoo.search_read(
                'stock.move.line',
                [['lot_id', '=', lot_id]],
                ['move_id', 'picking_id', 'location_id', 'location_dest_id', 'date'],
                limit=20,
                order='date asc'
            )
            
            if not move_lines:
                return None
            
            # Buscar el movimiento que viene desde 'Vendors'
            for ml in move_lines:
                loc_id = ml.get('location_id')
                if loc_id:
                    loc_name = loc_id[1] if isinstance(loc_id, (list, tuple)) and len(loc_id) > 1 else str(loc_id)
                    
                    # Si viene de Vendors/Proveedores
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
            
            # Si no encontramos desde Vendors, buscar picking de tipo Recepción MP
            for ml in move_lines:
                picking_info = ml.get('picking_id')
                if picking_info:
                    pickings = self.odoo.read('stock.picking', [picking_info[0]], 
                        ['partner_id', 'origin', 'scheduled_date', 'picking_type_id'])
                    if pickings:
                        p = pickings[0]
                        picking_type = p.get('picking_type_id')
                        # Si es Recepciones MP (ID=1)
                        if picking_type:
                            type_id = picking_type[0] if isinstance(picking_type, (list, tuple)) else picking_type
                            type_name = picking_type[1] if isinstance(picking_type, (list, tuple)) and len(picking_type) > 1 else ''
                            
                            if type_id == 1 or 'recep' in type_name.lower():
                                partner = p.get('partner_id')
                                if partner:
                                    return {
                                        'id': partner[0] if isinstance(partner, (list, tuple)) else partner,
                                        'name': partner[1] if isinstance(partner, (list, tuple)) else str(partner),
                                        'fecha_recepcion': p.get('scheduled_date'),
                                        'origin': p.get('origin', '')
                                    }
            
            # Si no encontramos recepción, puede ser un lote producido internamente
            return {'id': None, 'name': 'Producido internamente', 'fecha_recepcion': None, 'origin': ''}
            
        except Exception:
            pass
        
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
        rendimientos = []
        
        for mo in mos:
            try:
                consumos = self.get_consumos_mo(mo)
                produccion = self.get_produccion_mo(mo)
                
                kg_mp = sum(c.get('qty_done', 0) or 0 for c in consumos)
                kg_pt = sum(p.get('qty_done', 0) or 0 for p in produccion)
                
                if kg_mp > 0:
                    total_kg_mp += kg_mp
                    total_kg_pt += kg_pt
                    mos_procesadas += 1
                    
                    rend = (kg_pt / kg_mp * 100)
                    rendimientos.append(rend)
                    
                    # HH
                    hh = mo.get('x_studio_hh_efectiva') or mo.get('x_studio_hh') or 0
                    if isinstance(hh, (int, float)):
                        total_hh += hh
                    
                    # Lotes únicos
                    for c in consumos:
                        if c.get('lot_id'):
                            lotes_set.add(c['lot_id'])
            except Exception:
                continue
        
        # Usar rendimiento PONDERADO por volumen (más preciso para KPIs)
        rendimiento_promedio = (total_kg_pt / total_kg_mp * 100) if total_kg_mp > 0 else 0
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
        
        lotes_data = {}
        
        for mo in mos:
            try:
                consumos = self.get_consumos_mo(mo)
                produccion = self.get_produccion_mo(mo)
                
                kg_pt_mo = sum(p.get('qty_done', 0) or 0 for p in produccion)
                kg_mp_mo = sum(c.get('qty_done', 0) or 0 for c in consumos)
                
                if kg_mp_mo == 0:
                    continue
                
                # Distribuir PT proporcionalmente entre lotes consumidos
                for c in consumos:
                    lot_id = c.get('lot_id')
                    if not lot_id:
                        continue
                    
                    if lot_id not in lotes_data:
                        lotes_data[lot_id] = {
                            'lot_id': lot_id,
                            'lot_name': c.get('lot_name', 'SIN LOTE'),
                            'product_name': c.get('product_name', ''),
                            'kg_consumidos': 0,
                            'kg_producidos': 0,
                            'mos': [],
                            'proveedor': None
                        }
                    
                    qty_consumo = c.get('qty_done', 0) or 0
                    lotes_data[lot_id]['kg_consumidos'] += qty_consumo
                    
                    # Proporción de PT que corresponde a este lote
                    proporcion = qty_consumo / kg_mp_mo if kg_mp_mo > 0 else 0
                    lotes_data[lot_id]['kg_producidos'] += kg_pt_mo * proporcion
                    
                    mo_name = mo.get('name', '')
                    if mo_name and mo_name not in lotes_data[lot_id]['mos']:
                        lotes_data[lot_id]['mos'].append(mo_name)
            except Exception:
                continue
        
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
            
            # Obtener proveedor, OC y fecha recepción (solo para primeros 100 lotes)
            if len(resultado) < 100:
                try:
                    proveedor_info = self.get_proveedor_lote(lot_id)
                    if proveedor_info:
                        data['proveedor'] = proveedor_info.get('name', 'Desconocido')
                        data['orden_compra'] = proveedor_info.get('origin', '')
                        fecha_rec = proveedor_info.get('fecha_recepcion')
                        data['fecha_recepcion'] = str(fecha_rec)[:10] if fecha_rec else ''
                    else:
                        data['proveedor'] = 'Desconocido'
                        data['orden_compra'] = ''
                        data['fecha_recepcion'] = ''
                except Exception:
                    data['proveedor'] = 'Desconocido'
                    data['orden_compra'] = ''
                    data['fecha_recepcion'] = ''
            else:
                data['proveedor'] = 'Pendiente'
                data['orden_compra'] = ''
                data['fecha_recepcion'] = ''
            
            # Extraer tipo de fruta y manejo del nombre del producto
            data['tipo_fruta'] = self._extract_fruit_type(data.get('product_name', ''))
            data['manejo'] = self._extract_handling(data.get('product_name', ''))
            
            resultado.append(data)
        
        resultado.sort(key=lambda x: x['kg_consumidos'], reverse=True)
        return resultado
    
    def get_rendimiento_por_proveedor(self, fecha_inicio: str, fecha_fin: str) -> List[Dict]:
        """
        Agrupa el rendimiento por proveedor.
        """
        lotes = self.get_rendimiento_por_lote(fecha_inicio, fecha_fin)
        
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
        
        resultado = []
        for prov, data in proveedores_data.items():
            kg_c = data['kg_consumidos']
            kg_p = data['kg_producidos']
            
            data['rendimiento'] = round((kg_p / kg_c * 100) if kg_c > 0 else 0, 2)
            data['merma'] = round(kg_c - kg_p, 2)
            data['kg_consumidos'] = round(kg_c, 2)
            data['kg_producidos'] = round(kg_p, 2)
            
            resultado.append(data)
        
        resultado.sort(key=lambda x: x['kg_consumidos'], reverse=True)
        return resultado
    
    def get_rendimiento_mos(self, fecha_inicio: str, fecha_fin: str) -> List[Dict]:
        """
        Obtiene análisis de rendimiento por MO individual.
        """
        mos = self.get_mos_por_periodo(fecha_inicio, fecha_fin)
        
        resultado = []
        for mo in mos:
            try:
                consumos = self.get_consumos_mo(mo)
                produccion = self.get_produccion_mo(mo)
                
                kg_mp = sum(c.get('qty_done', 0) or 0 for c in consumos)
                kg_pt = sum(p.get('qty_done', 0) or 0 for p in produccion)
                
                if kg_mp == 0:
                    continue
                
                rendimiento = (kg_pt / kg_mp * 100)
                
                # Campos personalizados
                hh = mo.get('x_studio_hh_efectiva') or mo.get('x_studio_hh') or 0
                if not isinstance(hh, (int, float)):
                    hh = 0
                kg_por_hora = mo.get('x_studio_kghora_efectiva') or 0
                if not isinstance(kg_por_hora, (int, float)):
                    kg_por_hora = 0
                dotacion = mo.get('x_studio_dotacin') or 0
                if not isinstance(dotacion, (int, float)):
                    dotacion = 0
                
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
                    except Exception:
                        pass
                
                # Nombre del producto
                product_name = ''
                prod = mo.get('product_id')
                if isinstance(prod, (list, tuple)) and len(prod) > 1:
                    product_name = prod[1]
                elif isinstance(prod, dict):
                    product_name = prod.get('name', '')
                
                # Fecha (usar date_planned_start)
                fecha_raw = mo.get('date_planned_start', '') or mo.get('date_finished', '') or ''
                fecha = str(fecha_raw)[:10] if fecha_raw and len(str(fecha_raw)) >= 10 else ''
                
                resultado.append({
                    'mo_id': mo.get('id', 0),
                    'mo_name': mo.get('name', ''),
                    'product_name': product_name,
                    'kg_mp': round(kg_mp, 2),
                    'kg_pt': round(kg_pt, 2),
                    'rendimiento': round(rendimiento, 2),
                    'merma': round(kg_mp - kg_pt, 2),
                    'duracion_horas': duracion_horas,
                    'hh': hh,
                    'kg_por_hora': kg_por_hora,
                    'dotacion': dotacion,
                    'sala': mo.get('x_studio_sala_de_proceso', '') or '',
                    'fecha': fecha,
                    'num_lotes_mp': len(set(c.get('lot_id') for c in consumos if c.get('lot_id'))),
                    'num_lotes_pt': len(set(p.get('lot_id') for p in produccion if p.get('lot_id')))
                })
            except Exception:
                continue
        
        resultado.sort(key=lambda x: x['fecha'], reverse=True)
        return resultado
    
    def get_detalle_pt_por_lote(self, fecha_inicio: str, fecha_fin: str) -> Dict[int, List[Dict]]:
        """
        Obtiene el detalle de productos PT generados por cada lote MP.
        Retorna un dict: lot_id -> [lista de productos PT con cantidades]
        """
        mos = self.get_mos_por_periodo(fecha_inicio, fecha_fin)
        
        lote_pt_detalle = {}  # lot_id -> [productos PT]
        
        for mo in mos:
            try:
                consumos = self.get_consumos_mo(mo)
                produccion = self.get_produccion_mo(mo)
                
                # Calcular totales para proporción
                kg_mp_total = sum(c.get('qty_done', 0) or 0 for c in consumos)
                if kg_mp_total == 0:
                    continue
                
                # Para cada lote consumido, asignar proporcionalmente los PT
                for c in consumos:
                    lot_id = c.get('lot_id')
                    if not lot_id:
                        continue
                    
                    qty_consumo = c.get('qty_done', 0) or 0
                    proporcion = qty_consumo / kg_mp_total if kg_mp_total > 0 else 0
                    
                    if lot_id not in lote_pt_detalle:
                        lote_pt_detalle[lot_id] = {}
                    
                    # Agregar cada producto PT proporcional
                    for p in produccion:
                        pt_name = p.get('product_name', '')
                        pt_lot = p.get('lot_name', 'SIN LOTE')
                        pt_qty = (p.get('qty_done', 0) or 0) * proporcion
                        
                        key = f"{pt_name}|{pt_lot}"
                        if key not in lote_pt_detalle[lot_id]:
                            lote_pt_detalle[lot_id][key] = {
                                'product_name': pt_name,
                                'lot_name': pt_lot,
                                'kg': 0,
                                'tipo_fruta': self._extract_fruit_type(pt_name)
                            }
                        lote_pt_detalle[lot_id][key]['kg'] += pt_qty
            except Exception:
                continue
        
        # Convertir dict a lista y redondear
        resultado = {}
        for lot_id, productos in lote_pt_detalle.items():
            resultado[lot_id] = [
                {**v, 'kg': round(v['kg'], 2)} 
                for v in productos.values() 
                if v['kg'] > 0.01
            ]
        
        return resultado
    
    def get_ranking_proveedores(self, fecha_inicio: str, fecha_fin: str, top_n: int = 5) -> Dict:
        """
        Obtiene ranking de proveedores: Top N y Bottom N por rendimiento.
        """
        proveedores = self.get_rendimiento_por_proveedor(fecha_inicio, fecha_fin)
        
        # Filtrar proveedores válidos (con kg > 100)
        prov_validos = [p for p in proveedores if p['kg_consumidos'] > 100 and p['proveedor'] != 'Desconocido']
        
        # Ordenar por rendimiento
        prov_ordenados = sorted(prov_validos, key=lambda x: x['rendimiento'], reverse=True)
        
        top = prov_ordenados[:top_n]
        bottom = prov_ordenados[-top_n:] if len(prov_ordenados) > top_n else []
        bottom.reverse()  # Para que el peor esté primero
        
        # Calcular promedios
        rend_promedio = sum(p['rendimiento'] for p in prov_validos) / len(prov_validos) if prov_validos else 0
        kg_total = sum(p['kg_consumidos'] for p in prov_validos)
        
        return {
            'top': top,
            'bottom': bottom,
            'promedio_rendimiento': round(rend_promedio, 2),
            'total_proveedores': len(prov_validos),
            'kg_total': round(kg_total, 2)
        }
    
    def get_productividad_por_sala(self, fecha_inicio: str, fecha_fin: str) -> List[Dict]:
        """
        Calcula KPIs de productividad agrupados por sala de proceso.
        """
        mos = self.get_rendimiento_mos(fecha_inicio, fecha_fin)
        
        salas_data = {}
        
        for mo in mos:
            sala = mo.get('sala', '') or 'Sin Sala'
            
            if sala not in salas_data:
                salas_data[sala] = {
                    'sala': sala,
                    'kg_mp': 0,
                    'kg_pt': 0,
                    'hh_total': 0,
                    'dotacion_sum': 0,
                    'duracion_total': 0,
                    'num_mos': 0
                }
            
            salas_data[sala]['kg_mp'] += mo.get('kg_mp', 0)
            salas_data[sala]['kg_pt'] += mo.get('kg_pt', 0)
            salas_data[sala]['hh_total'] += mo.get('hh', 0) or 0
            salas_data[sala]['dotacion_sum'] += mo.get('dotacion', 0) or 0
            salas_data[sala]['duracion_total'] += mo.get('duracion_horas', 0) or 0
            salas_data[sala]['num_mos'] += 1
        
        # Calcular KPIs
        resultado = []
        for sala, data in salas_data.items():
            kg_pt = data['kg_pt']
            kg_mp = data['kg_mp']
            hh = data['hh_total']
            duracion = data['duracion_total']
            num_mos = data['num_mos']
            dotacion_prom = data['dotacion_sum'] / num_mos if num_mos > 0 else 0
            
            resultado.append({
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
                'duracion_promedio': round(duracion / num_mos if num_mos > 0 else 0, 2),
                'num_mos': num_mos
            })
        
        resultado.sort(key=lambda x: x['kg_pt'], reverse=True)
        return resultado
    
    def get_trazabilidad_inversa(self, lote_pt_name: str) -> Dict:
        """
        Trazabilidad inversa: dado un lote PT, encuentra los lotes MP originales.
        """
        # Buscar el lote PT
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
        
        # Buscar el movimiento donde se produjo este lote (debe ser en move_finished_ids)
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['lot_id', '=', lote_pt_id]],
            ['move_id', 'date', 'location_id', 'location_dest_id', 'qty_done'],
            limit=10,
            order='date asc'
        )
        
        # Buscar el movimiento de producción
        mo_encontrada = None
        for ml in move_lines:
            move_id = ml.get('move_id')
            if move_id:
                moves = self.odoo.read('stock.move', [move_id[0]], ['production_id', 'raw_material_production_id'])
                if moves:
                    m = moves[0]
                    if m.get('production_id'):
                        mo_id = m['production_id'][0]
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
        
        # Obtener los lotes MP consumidos en esa MO
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
                
                # Excluir insumos/envases
                if self._is_excluded_consumo(prod_name):
                    continue
                
                lot_info = c.get('lot_id')
                if lot_info:
                    qty = c.get('qty_done', 0) or 0
                    if qty > 0:
                        # Obtener proveedor del lote MP
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
    
    def get_consolidado_fruta(self, fecha_inicio: str, fecha_fin: str) -> Dict:
        """
        Consolida KPIs agrupados por Tipo de Fruta, Manejo y Producto.
        Para vista ejecutiva del jefe.
        """
        lotes = self.get_rendimiento_por_lote(fecha_inicio, fecha_fin)
        mos_data = self.get_rendimiento_mos(fecha_inicio, fecha_fin)
        
        # Calcular totales de MOs para promedios
        mos_totals = {
            'hh_total': sum(m.get('hh', 0) or 0 for m in mos_data),
            'duracion_total': sum(m.get('duracion_horas', 0) or 0 for m in mos_data),
            'dotacion_sum': sum(m.get('dotacion', 0) or 0 for m in mos_data),
            'num_mos': len(mos_data)
        }
        
        # Agrupar por Fruta
        por_fruta = {}
        # Agrupar por Fruta + Manejo
        por_fruta_manejo = {}
        # Agrupar por Producto
        por_producto = {}
        
        for lote in lotes:
            tipo_fruta = lote.get('tipo_fruta', 'Otro')
            manejo = lote.get('manejo', 'Otro')
            producto = lote.get('product_name', 'Desconocido')
            
            kg_mp = lote.get('kg_consumidos', 0)
            kg_pt = lote.get('kg_producidos', 0)
            
            # === Por Fruta ===
            if tipo_fruta not in por_fruta:
                por_fruta[tipo_fruta] = {
                    'tipo_fruta': tipo_fruta,
                    'kg_mp': 0, 'kg_pt': 0, 'num_lotes': 0, 'proveedores': set()
                }
            por_fruta[tipo_fruta]['kg_mp'] += kg_mp
            por_fruta[tipo_fruta]['kg_pt'] += kg_pt
            por_fruta[tipo_fruta]['num_lotes'] += 1
            por_fruta[tipo_fruta]['proveedores'].add(lote.get('proveedor', ''))
            
            # === Por Fruta + Manejo ===
            key_fm = f"{tipo_fruta}|{manejo}"
            if key_fm not in por_fruta_manejo:
                por_fruta_manejo[key_fm] = {
                    'tipo_fruta': tipo_fruta,
                    'manejo': manejo,
                    'kg_mp': 0, 'kg_pt': 0, 'num_lotes': 0, 'proveedores': set()
                }
            por_fruta_manejo[key_fm]['kg_mp'] += kg_mp
            por_fruta_manejo[key_fm]['kg_pt'] += kg_pt
            por_fruta_manejo[key_fm]['num_lotes'] += 1
            por_fruta_manejo[key_fm]['proveedores'].add(lote.get('proveedor', ''))
            
            # === Por Producto ===
            if producto not in por_producto:
                por_producto[producto] = {
                    'producto': producto,
                    'tipo_fruta': tipo_fruta,
                    'manejo': manejo,
                    'kg_mp': 0, 'kg_pt': 0, 'num_lotes': 0
                }
            por_producto[producto]['kg_mp'] += kg_mp
            por_producto[producto]['kg_pt'] += kg_pt
            por_producto[producto]['num_lotes'] += 1
        
        # Calcular KPIs para cada agrupación
        def calcular_kpis(data, mos_totals):
            kg_mp = data['kg_mp']
            kg_pt = data['kg_pt']
            
            # Proporcionar KPIs de MO basados en proporción de kg
            total_kg_mp_global = sum(l.get('kg_consumidos', 0) for l in lotes)
            proporcion = kg_mp / total_kg_mp_global if total_kg_mp_global > 0 else 0
            
            hh_proporcional = mos_totals['hh_total'] * proporcion
            duracion_proporcional = mos_totals['duracion_total'] * proporcion
            
            return {
                **data,
                'kg_mp': round(kg_mp, 2),
                'kg_pt': round(kg_pt, 2),
                'rendimiento': round((kg_pt / kg_mp * 100) if kg_mp > 0 else 0, 2),
                'merma': round(kg_mp - kg_pt, 2),
                'merma_pct': round(((kg_mp - kg_pt) / kg_mp * 100) if kg_mp > 0 else 0, 2),
                'kg_por_hh': round(kg_pt / hh_proporcional if hh_proporcional > 0 else 0, 2),
                'kg_por_hora': round(kg_pt / duracion_proporcional if duracion_proporcional > 0 else 0, 2),
                'num_proveedores': len(data.get('proveedores', set()))
            }
        
        # Procesar resultados
        resultado_fruta = []
        for key, data in por_fruta.items():
            d = calcular_kpis(data.copy(), mos_totals)
            d.pop('proveedores', None)
            resultado_fruta.append(d)
        resultado_fruta.sort(key=lambda x: x['kg_pt'], reverse=True)
        
        resultado_fruta_manejo = []
        for key, data in por_fruta_manejo.items():
            d = calcular_kpis(data.copy(), mos_totals)
            d.pop('proveedores', None)
            resultado_fruta_manejo.append(d)
        resultado_fruta_manejo.sort(key=lambda x: (x['tipo_fruta'], -x['kg_pt']))
        
        resultado_producto = []
        for key, data in por_producto.items():
            d = calcular_kpis(data.copy(), mos_totals)
            resultado_producto.append(d)
        resultado_producto.sort(key=lambda x: x['kg_pt'], reverse=True)
        
        # Resumen global
        total_kg_mp = sum(d['kg_mp'] for d in resultado_fruta)
        total_kg_pt = sum(d['kg_pt'] for d in resultado_fruta)
        
        return {
            'resumen': {
                'total_kg_mp': round(total_kg_mp, 2),
                'total_kg_pt': round(total_kg_pt, 2),
                'rendimiento_global': round((total_kg_pt / total_kg_mp * 100) if total_kg_mp > 0 else 0, 2),
                'merma_global': round(total_kg_mp - total_kg_pt, 2),
                'num_frutas': len(resultado_fruta),
                'num_lotes': sum(d['num_lotes'] for d in resultado_fruta),
                'total_hh': round(mos_totals['hh_total'], 2),
                'total_mos': mos_totals['num_mos']
            },
            'por_fruta': resultado_fruta,
            'por_fruta_manejo': resultado_fruta_manejo,
            'por_producto': resultado_producto[:50]  # Limitar productos
        }


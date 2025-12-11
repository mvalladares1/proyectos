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
        
        rendimiento_promedio = sum(rendimientos) / len(rendimientos) if rendimientos else 0
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
            
            # Obtener proveedor (solo para primeros 50 lotes por performance)
            if len(resultado) < 50:
                try:
                    proveedor = self.get_proveedor_lote(lot_id)
                    data['proveedor'] = proveedor['name'] if proveedor else 'Desconocido'
                except Exception:
                    data['proveedor'] = 'Desconocido'
            else:
                data['proveedor'] = 'Pendiente'
            
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

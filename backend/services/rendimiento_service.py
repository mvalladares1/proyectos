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
    
    # === CLASIFICACIÓN DE SALAS ===
    # Identificadores de túneles/congelado (no generan merma, rendimiento ~100%)
    TUNNEL_KEYWORDS = ['tunel', 'túnel', 'estatico', 'estático', 'congelado', 'tunnel']
    
    @classmethod
    def get_sala_tipo(cls, sala_name: str, product_name: str = None) -> str:
        """
        Clasifica una MO como PROCESO o CONGELADO.
        
        PROCESO = Salas de vaciado, líneas retail/granel (generan merma)
        CONGELADO = Túneles estáticos (solo congelan, ~100% rendimiento)
        
        La clasificación se hace por:
        1. Nombre de la sala (x_studio_sala_de_proceso)
        2. Nombre del producto (si contiene keywords de congelado)
        """
        # Prioridad 1: Verificar nombre del producto
        if product_name:
            prod_lower = product_name.lower()
            # Si el producto contiene palabras clave de congelado/túnel
            if any(keyword in prod_lower for keyword in ['túnel', 'tunel', 'congelado túnel', 'tunnel', 'estatico', 'estático', 'cámara']):
                return 'CONGELADO'
        
        # Prioridad 2: Verificar sala
        if not sala_name or sala_name == 'Sin Sala':
            # Si no tiene sala pero el producto indica congelado, ya se clasificó arriba
            return 'SIN_SALA'
        
        sala_lower = sala_name.lower()
        
        # Detectar túneles/congelado por sala
        if any(keyword in sala_lower for keyword in cls.TUNNEL_KEYWORDS):
            return 'CONGELADO'
        
        return 'PROCESO'
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self._cache = get_cache()
    
    def _is_excluded_consumo(self, product_name: str, category_name: str = '') -> bool:
        """
        Verifica si un producto debe excluirse del consumo MP.
        Excluye SOLO: insumos puros, envases puros (no productos de proceso).
        
        IMPORTANTE: Productos con código [300xxx] son productos de proceso,
        NO deben excluirse aunque tengan "caja" o "bolsa" en la descripción
        del embalaje (ej: "AR S/V Conv. 13.61 kg en Caja").
        """
        if not product_name:
            return True
        
        name_lower = product_name.lower()
        cat_lower = (category_name or '').lower()
        
        # Si tiene código de producto [3xxxxx] o [1xxxxx], NO excluir (es producto de proceso)
        if product_name.startswith('[3') or product_name.startswith('[1'):
            return False
        
        # Excluir costos operacionales (se capturan por separado)
        if self._is_operational_cost(product_name):
            return True
        
        # Excluir por categoría
        if any(exc in cat_lower for exc in self.EXCLUDED_CATEGORIES):
            return True
        
        # Excluir por nombre - SOLO si es claramente un insumo/envase puro
        # No excluir productos de proceso que tienen "caja" o "bolsa" en descripción
        pure_packaging_indicators = [
            "caja de exportación", "cajas de exportación", 
            "insumo", "envase", "pallet", "etiqueta", "doy pe"
        ]
        
        if any(exc in name_lower for exc in pure_packaging_indicators):
            return True
        
        # Si el producto ES una bolsa o caja suelta (no tiene código [xxx])
        if name_lower.startswith('bolsa') or name_lower.startswith('caja'):
            return True
        
        return False
    
    def _is_operational_cost(self, product_name: str) -> bool:
        """
        Identifica si un producto es un costo operacional (electricidad, servicios, etc.)
        Estos se excluyen de MP pero se capturan como KPI separado.
        """
        if not product_name:
            return False
        
        name_lower = product_name.lower()
        operational_indicators = [
            "provisión electricidad",
            "provisión electr",
            "túnel estático",
            "tunel estatico",
            "electricidad túnel",
            "costo hora",
            "($/hr)",
            "($/h)"
        ]
        
        return any(ind in name_lower for ind in operational_indicators)
    
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
    
    def get_mos_por_periodo(self, fecha_inicio: str, fecha_fin: str, limit: int = 500, solo_terminadas: bool = True) -> List[Dict]:
        """
        Obtiene MOs en el período.
        Usa date_planned_start (fecha prevista) para filtrar.
        
        Args:
            solo_terminadas: Si True, solo incluye state 'done'. Si False, incluye 'done' y 'to_close'.
        """
        if solo_terminadas:
            state_filter = ['state', '=', 'done']
        else:
            state_filter = ['state', 'in', ['done', 'to_close', 'progress']]
        
        domain = [
            state_filter,
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
    
    def get_consumos_batch(self, mos: List[Dict]) -> Dict[int, List[Dict]]:
        """
        OPTIMIZADO: Obtiene consumos de TODAS las MOs en batch.
        Retorna: Dict[mo_id -> List[consumos]]
        Reduce llamadas API de N*3 a ~3 totales.
        """
        # Recolectar todos los move_raw_ids de todas las MOs
        all_move_raw_ids = []
        mo_id_to_move_ids = {}
        
        for mo in mos:
            mo_id = mo.get('id')
            move_raw_ids = mo.get('move_raw_ids', [])
            mo_id_to_move_ids[mo_id] = set(move_raw_ids)
            all_move_raw_ids.extend(move_raw_ids)
        
        if not all_move_raw_ids:
            return {mo.get('id'): [] for mo in mos}
        
        # UNA sola llamada para obtener TODAS las líneas de movimiento
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', all_move_raw_ids]],
            ['move_id', 'product_id', 'lot_id', 'qty_done', 'date'],
            limit=10000
        )
        
        # Obtener IDs únicos de productos
        product_ids = list(set(
            ml.get('product_id')[0] 
            for ml in move_lines 
            if ml.get('product_id')
        ))
        
        # UNA sola llamada para obtener datos de productos
        products_data = {}
        template_data = {}
        
        if product_ids:
            try:
                products = self.odoo.read(
                    'product.product',
                    product_ids,
                    ['name', 'categ_id', 'product_tmpl_id']
                )
                
                template_ids = set()
                for p in products:
                    products_data[p['id']] = p
                    tmpl = p.get('product_tmpl_id')
                    if tmpl:
                        tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
                        template_ids.add(tmpl_id)
                
                # UNA sola llamada para templates
                if template_ids:
                    templates = self.odoo.read(
                        'product.template',
                        list(template_ids),
                        ['id', 'name', 'x_studio_categora_tipo_de_manejo', 'x_studio_sub_categora']
                    )
                    for t in templates:
                        template_data[t['id']] = t
            except Exception:
                pass
        
        # Crear mapa de move_id -> mo_id
        move_to_mo = {}
        for mo_id, move_ids in mo_id_to_move_ids.items():
            for move_id in move_ids:
                move_to_mo[move_id] = mo_id
        
        # Procesar todas las líneas y agrupar por MO
        result = {mo.get('id'): [] for mo in mos}
        
        for ml in move_lines:
            try:
                move_info = ml.get('move_id')
                move_id = move_info[0] if isinstance(move_info, (list, tuple)) else move_info
                mo_id = move_to_mo.get(move_id)
                
                if not mo_id:
                    continue
                
                prod_info = ml.get('product_id')
                if not prod_info:
                    continue
                
                prod_id = prod_info[0]
                prod_name = prod_info[1] if len(prod_info) > 1 else ''
                
                prod_data = products_data.get(prod_id, {})
                categ = prod_data.get('categ_id')
                category_name = categ[1] if categ and isinstance(categ, (list, tuple)) else ''
                
                if self._is_excluded_consumo(prod_name, category_name):
                    continue
                
                qty = ml.get('qty_done', 0) or 0
                if qty <= 0:
                    continue
                
                lot_info = ml.get('lot_id')
                
                # Obtener manejo y especie
                tmpl = prod_data.get('product_tmpl_id')
                tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl if tmpl else None
                tmpl_data = template_data.get(tmpl_id, {}) if tmpl_id else {}
                
                manejo_raw = tmpl_data.get('x_studio_categora_tipo_de_manejo', '') or ''
                especie_raw = tmpl_data.get('x_studio_sub_categora', '') or ''
                
                if isinstance(manejo_raw, (list, tuple)) and len(manejo_raw) > 1:
                    manejo_raw = manejo_raw[1]
                
                manejo = 'Otro'
                if manejo_raw:
                    manejo_str = str(manejo_raw).lower()
                    if 'org' in manejo_str:
                        manejo = 'Orgánico'
                    elif 'conv' in manejo_str:
                        manejo = 'Convencional'
                
                if isinstance(especie_raw, (list, tuple)) and len(especie_raw) > 1:
                    especie_raw = especie_raw[1]
                especie = str(especie_raw) if especie_raw else 'Otro'
                
                result[mo_id].append({
                    'product_id': prod_id,
                    'product_name': prod_name,
                    'lot_id': lot_info[0] if lot_info else None,
                    'lot_name': lot_info[1] if lot_info else 'SIN LOTE',
                    'qty_done': qty,
                    'date': ml.get('date'),
                    'category': category_name,
                    'manejo': manejo,
                    'especie': especie
                })
            except Exception:
                continue
        
        return result
    
    def get_produccion_batch(self, mos: List[Dict]) -> Dict[int, List[Dict]]:
        """
        OPTIMIZADO: Obtiene producción de TODAS las MOs en batch.
        Retorna: Dict[mo_id -> List[produccion]]
        """
        all_move_finished_ids = []
        mo_id_to_move_ids = {}
        
        for mo in mos:
            mo_id = mo.get('id')
            move_finished_ids = mo.get('move_finished_ids', [])
            mo_id_to_move_ids[mo_id] = set(move_finished_ids)
            all_move_finished_ids.extend(move_finished_ids)
        
        if not all_move_finished_ids:
            return {mo.get('id'): [] for mo in mos}
        
        # UNA sola llamada
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', all_move_finished_ids]],
            ['move_id', 'product_id', 'lot_id', 'qty_done', 'date', 'product_category_name'],
            limit=5000
        )
        
        # Mapa move_id -> mo_id
        move_to_mo = {}
        for mo_id, move_ids in mo_id_to_move_ids.items():
            for move_id in move_ids:
                move_to_mo[move_id] = mo_id
        
        result = {mo.get('id'): [] for mo in mos}
        
        for ml in move_lines:
            try:
                move_info = ml.get('move_id')
                move_id = move_info[0] if isinstance(move_info, (list, tuple)) else move_info
                mo_id = move_to_mo.get(move_id)
                
                if not mo_id:
                    continue
                
                prod_info = ml.get('product_id')
                prod_name = prod_info[1] if prod_info else ''
                category = ml.get('product_category_name', '') or ''
                
                if self._is_excluded_produccion(prod_name, category):
                    continue
                
                qty = ml.get('qty_done', 0) or 0
                if qty <= 0:
                    continue
                
                lot_info = ml.get('lot_id')
                result[mo_id].append({
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
        
        return result
    
    def get_consumos_mo(self, mo: Dict) -> List[Dict]:
        """
        Obtiene los consumos de MP de una MO.
        Incluye campos x_studio_categora_tipo_manejo (Org/Conv) y x_studio_sub_categora (especie).
        Solo excluye insumos/envases reales, no productos de proceso.
        """
        move_raw_ids = mo.get('move_raw_ids', [])
        if not move_raw_ids:
            return []
        
        # Obtener líneas de movimiento
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', move_raw_ids]],
            ['product_id', 'lot_id', 'qty_done', 'date'],
            limit=500
        )
        
        if not move_lines:
            return []
        
        # Obtener IDs únicos de productos para consulta batch
        product_ids = list(set(
            ml.get('product_id')[0] 
            for ml in move_lines 
            if ml.get('product_id')
        ))
        
        # Consultar productos para obtener product_tmpl_id
        products_data = {}
        template_data = {}
        
        if product_ids:
            try:
                # Paso 1: Obtener product.product con product_tmpl_id
                products = self.odoo.read(
                    'product.product',
                    product_ids,
                    ['name', 'categ_id', 'product_tmpl_id']
                )
                
                # Recolectar template IDs
                template_ids = set()
                for p in products:
                    products_data[p['id']] = p
                    tmpl = p.get('product_tmpl_id')
                    if tmpl:
                        tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl
                        template_ids.add(tmpl_id)
                
                # Paso 2: Obtener product.template con campos Studio
                if template_ids:
                    templates = self.odoo.read(
                        'product.template',
                        list(template_ids),
                        ['id', 'name', 'x_studio_categora_tipo_de_manejo', 'x_studio_sub_categora']
                    )
                    for t in templates:
                        template_data[t['id']] = t
                        
            except Exception as e:
                # Si falla, intentar sin campos Studio
                try:
                    products = self.odoo.read(
                        'product.product',
                        product_ids,
                        ['name', 'categ_id', 'product_tmpl_id']
                    )
                    for p in products:
                        products_data[p['id']] = p
                except Exception:
                    pass
        
        consumos = []
        for ml in move_lines:
            try:
                prod_info = ml.get('product_id')
                if not prod_info:
                    continue
                
                prod_id = prod_info[0]
                prod_name = prod_info[1] if len(prod_info) > 1 else ''
                
                # Obtener datos del producto
                prod_data = products_data.get(prod_id, {})
                
                # Obtener categoría
                categ = prod_data.get('categ_id')
                category_name = categ[1] if categ and isinstance(categ, (list, tuple)) else ''
                
                # Excluir SOLO insumos/envases reales (cajas, bolsas, etc.)
                # NO excluir productos de proceso que tienen código [300xxx]
                if self._is_excluded_consumo(prod_name, category_name):
                    continue
                
                qty = ml.get('qty_done', 0) or 0
                if qty <= 0:
                    continue
                
                lot_info = ml.get('lot_id')
                
                # Obtener template_id para acceder a campos Studio
                tmpl = prod_data.get('product_tmpl_id')
                tmpl_id = tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl if tmpl else None
                tmpl_data = template_data.get(tmpl_id, {}) if tmpl_id else {}
                
                # Obtener manejo y especie de campos Studio del TEMPLATE
                manejo_raw = tmpl_data.get('x_studio_categora_tipo_de_manejo', '') or ''
                especie_raw = tmpl_data.get('x_studio_sub_categora', '') or ''
                
                # Si manejo_raw es tupla/lista (selection field), tomar el valor legible
                if isinstance(manejo_raw, (list, tuple)) and len(manejo_raw) > 1:
                    manejo_raw = manejo_raw[1]
                
                # Normalizar manejo (puede venir como "Org." u "Orgánico", "Conv." o "Convencional")
                manejo = 'Otro'
                if manejo_raw:
                    manejo_str = str(manejo_raw).lower()
                    if 'org' in manejo_str:
                        manejo = 'Orgánico'
                    elif 'conv' in manejo_str:
                        manejo = 'Convencional'
                    else:
                        manejo = str(manejo_raw)
                
                # Normalizar especie (también puede ser selection field)
                if isinstance(especie_raw, (list, tuple)) and len(especie_raw) > 1:
                    especie_raw = especie_raw[1]
                especie = str(especie_raw) if especie_raw else self._extract_fruit_type(prod_name)
                
                consumos.append({
                    'product_id': prod_id,
                    'product_name': prod_name,
                    'lot_id': lot_info[0] if lot_info else None,
                    'lot_name': lot_info[1] if lot_info else 'SIN LOTE',
                    'qty_done': qty,
                    'date': ml.get('date'),
                    'category': category_name,
                    'manejo': manejo,
                    'especie': especie
                })
            except Exception:
                continue
        
        return consumos
    
    def get_costos_operacionales_mo(self, mo: Dict) -> Dict:
        """
        Obtiene costos operacionales de una MO (electricidad, servicios, etc.)
        Estos NO son MP pero son KPIs importantes.
        
        Retorna dict con:
        - costo_electricidad: Provisión Electricidad Túnel Estático
        - otros_costos: Otros costos operacionales
        """
        move_raw_ids = mo.get('move_raw_ids', [])
        if not move_raw_ids:
            return {'costo_electricidad': 0.0, 'otros_costos': 0.0}
        
        # Obtener movimientos (stock.move) para ver costos
        moves = self.odoo.search_read(
            'stock.move',
            [['id', 'in', move_raw_ids]],
            ['product_id', 'product_uom_qty', 'quantity_done', 'price_unit'],
            limit=100
        )
        
        costo_electricidad = 0.0
        otros_costos = 0.0
        
        for move in moves:
            try:
                prod = move.get('product_id')
                prod_name = prod[1] if isinstance(prod, (list, tuple)) and len(prod) > 1 else ''
                
                if self._is_operational_cost(prod_name):
                    qty = move.get('quantity_done', 0) or 0
                    price = move.get('price_unit', 0) or 0
                    costo = qty * price
                    
                    if 'electricidad' in prod_name.lower() or 'túnel' in prod_name.lower():
                        costo_electricidad += costo
                    else:
                        otros_costos += costo
            except Exception:
                continue
        
        return {
            'costo_electricidad': round(costo_electricidad, 2),
            'otros_costos': round(otros_costos, 2)
        }
    
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

    def get_dashboard_completo(self, fecha_inicio: str, fecha_fin: str, solo_terminadas: bool = True) -> Dict:
        """
        OPTIMIZADO: Obtiene TODOS los datos del dashboard en una sola pasada.
        Reduce drásticamente las llamadas a la API de Odoo.
        
        En lugar de hacer 4 endpoints separados (cada uno repitiendo get_mos_por_periodo),
        este método:
        1. Obtiene MOs una sola vez
        2. Procesa consumos y producción para cada MO una sola vez
        3. Calcula todos los KPIs y agrupaciones en una pasada
        
        Args:
            solo_terminadas: Si True, solo MOs con state='done'. Si False, incluye 'to_close' y 'progress'.
        
        Retorna: overview, consolidado, mos, salas - todo en un solo dict
        """
        # 1. Obtener MOs del período (ÚNICA llamada a Odoo para MOs)
        mos = self.get_mos_por_periodo(fecha_inicio, fecha_fin, solo_terminadas=solo_terminadas)
        
        # Acumuladores GLOBALES para overview (todos los procesos)
        total_kg_mp = 0.0
        total_kg_pt = 0.0
        total_hh = 0.0
        total_costo_electricidad = 0.0
        mos_procesadas = 0
        lotes_set = set()
        
        # === ACUMULADORES SEPARADOS: PROCESO vs CONGELADO ===
        # PROCESO = salas de vaciado, líneas retail/granel (generan merma real)
        proceso_kg_mp = 0.0
        proceso_kg_pt = 0.0
        proceso_hh = 0.0
        proceso_mos = 0
        
        # CONGELADO = túneles estáticos (solo congelan, ~100% rendimiento)
        congelado_kg_mp = 0.0
        congelado_kg_pt = 0.0
        congelado_hh = 0.0
        congelado_mos = 0
        
        # Acumuladores para consolidado por fruta (solo PROCESO)
        por_fruta = {}
        por_fruta_manejo = {}
        
        # Acumuladores para salas
        salas_data = {}
        
        # Lista de MOs procesadas (para detalle)
        mos_resultado = []
        
        # === OPTIMIZACIÓN: PRE-FETCH EN BATCH ===
        # Obtener consumos y producción de TODAS las MOs en pocas llamadas
        consumos_by_mo = self.get_consumos_batch(mos)
        produccion_by_mo = self.get_produccion_batch(mos)
        
        # 2. Procesar cada MO (SIN llamadas API adicionales - ya tenemos todo en memoria)
        for mo in mos:
            try:
                mo_id = mo.get('id')
                
                # Usar datos pre-cargados en batch
                consumos = consumos_by_mo.get(mo_id, [])
                produccion = produccion_by_mo.get(mo_id, [])
                
                # Obtener costos operacionales (electricidad)
                costos_op = self.get_costos_operacionales_mo(mo)
                
                kg_mp = sum(c.get('qty_done', 0) or 0 for c in consumos)
                kg_pt = sum(p.get('qty_done', 0) or 0 for p in produccion)
                costo_elec = costos_op.get('costo_electricidad', 0)  # Costo electricidad de esta MO
                
                if kg_mp == 0:
                    continue
                
                rendimiento = (kg_pt / kg_mp * 100)
                
                # Obtener nombre del producto para clasificación
                product_name = ''
                prod = mo.get('product_id')
                if isinstance(prod, (list, tuple)) and len(prod) > 1:
                    product_name = prod[1]
                elif isinstance(prod, dict):
                    product_name = prod.get('name', '')
                
                # Obtener sala y clasificarla (ahora también usando nombre del producto)
                sala = mo.get('x_studio_sala_de_proceso', '') or 'Sin Sala'
                sala_tipo = self.get_sala_tipo(sala, product_name)
                
                # === Acumular para Overview GLOBAL ===
                total_kg_mp += kg_mp
                total_kg_pt += kg_pt
                total_costo_electricidad += costo_elec
                mos_procesadas += 1
                
                hh = mo.get('x_studio_hh_efectiva') or mo.get('x_studio_hh') or 0
                if isinstance(hh, (int, float)):
                    total_hh += hh
                
                for c in consumos:
                    if c.get('lot_id'):
                        lotes_set.add(c['lot_id'])
                
                # === Acumular SEPARADOS por tipo de sala ===
                if sala_tipo == 'PROCESO':
                    proceso_kg_mp += kg_mp
                    proceso_kg_pt += kg_pt
                    proceso_hh += hh if isinstance(hh, (int, float)) else 0
                    proceso_mos += 1
                elif sala_tipo == 'CONGELADO':
                    congelado_kg_mp += kg_mp
                    congelado_kg_pt += kg_pt
                    congelado_hh += hh if isinstance(hh, (int, float)) else 0
                    congelado_mos += 1
                
                # === Acumular para Consolidado por Fruta ===
                # Detectar especie y manejo de los consumos usando campos Studio
                if consumos:
                    # Obtener todas las especies únicas en los consumos de esta MO
                    especies_en_mo = set()
                    manejos_en_mo = set()
                    for c in consumos:
                        esp = c.get('especie', '') or 'Otro'
                        man = c.get('manejo', '') or 'Otro'
                        if esp and esp != 'Otro' and esp != 'Desconocido':
                            especies_en_mo.add(esp)
                        manejos_en_mo.add(man)
                    
                    # Si hay más de una especie, es Mix
                    if len(especies_en_mo) > 1:
                        tipo_fruta = 'Mix'
                    elif len(especies_en_mo) == 1:
                        tipo_fruta = list(especies_en_mo)[0]
                    else:
                        # Fallback a extracción del nombre
                        tipo_fruta = self._extract_fruit_type(consumos[0].get('product_name', ''))
                    
                    # Para manejo, usar el más común o el primero
                    if 'Orgánico' in manejos_en_mo:
                        manejo = 'Orgánico'
                    elif 'Convencional' in manejos_en_mo:
                        manejo = 'Convencional'
                    else:
                        manejo = list(manejos_en_mo)[0] if manejos_en_mo else 'Otro'
                    
                    # SOLO acumular para consolidado si es PROCESO (NO congelado)
                    # El congelado infla los números porque tiene rendimiento ~100%
                    if sala_tipo == 'PROCESO':
                        # Por Fruta
                        if tipo_fruta not in por_fruta:
                            por_fruta[tipo_fruta] = {
                                'tipo_fruta': tipo_fruta,
                                'kg_mp': 0, 'kg_pt': 0, 'num_lotes': 0
                            }
                        por_fruta[tipo_fruta]['kg_mp'] += kg_mp
                        por_fruta[tipo_fruta]['kg_pt'] += kg_pt
                        por_fruta[tipo_fruta]['num_lotes'] += len(set(c.get('lot_id') for c in consumos if c.get('lot_id')))
                        
                        # Por Fruta + Manejo
                        key_fm = f"{tipo_fruta}|{manejo}"
                        if key_fm not in por_fruta_manejo:
                            por_fruta_manejo[key_fm] = {
                                'tipo_fruta': tipo_fruta,
                                'manejo': manejo,
                                'kg_mp': 0, 'kg_pt': 0, 'num_lotes': 0
                            }
                        por_fruta_manejo[key_fm]['kg_mp'] += kg_mp
                        por_fruta_manejo[key_fm]['kg_pt'] += kg_pt
                        por_fruta_manejo[key_fm]['num_lotes'] += 1
                
                # === Acumular para Salas ===
                # sala ya está definido arriba
                if sala not in salas_data:
                    salas_data[sala] = {
                        'sala': sala,
                        'sala_tipo': sala_tipo,  # Nuevo: PROCESO, CONGELADO o SIN_SALA
                        'kg_mp': 0, 'kg_pt': 0,
                        'hh_total': 0, 'dotacion_sum': 0,
                        'duracion_total': 0, 'num_mos': 0
                    }
                
                salas_data[sala]['kg_mp'] += kg_mp
                salas_data[sala]['kg_pt'] += kg_pt
                salas_data[sala]['hh_total'] += hh if isinstance(hh, (int, float)) else 0
                
                dotacion = mo.get('x_studio_dotacin') or 0
                salas_data[sala]['dotacion_sum'] += dotacion if isinstance(dotacion, (int, float)) else 0
                
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
                
                salas_data[sala]['duracion_total'] += duracion_horas
                salas_data[sala]['num_mos'] += 1
                
                # === Agregar a lista de MOs ===
                product_name = ''
                prod = mo.get('product_id')
                if isinstance(prod, (list, tuple)) and len(prod) > 1:
                    product_name = prod[1]
                elif isinstance(prod, dict):
                    product_name = prod.get('name', '')
                
                fecha_raw = mo.get('date_planned_start', '') or mo.get('date_finished', '') or ''
                fecha = str(fecha_raw)[:10] if fecha_raw and len(str(fecha_raw)) >= 10 else ''
                
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
                    'sala_tipo': sala_tipo,  # Nuevo: PROCESO, CONGELADO, SIN_SALA
                    'fecha': fecha
                })
                
            except Exception:
                continue
        
        # 3. Calcular KPIs finales
        
        # Overview GLOBAL (todos los procesos)
        rendimiento_promedio = (total_kg_pt / total_kg_mp * 100) if total_kg_mp > 0 else 0
        merma_total = total_kg_mp - total_kg_pt
        merma_pct = (merma_total / total_kg_mp * 100) if total_kg_mp > 0 else 0
        kg_por_hh = (total_kg_pt / total_hh) if total_hh > 0 else 0
        
        # KPIs de PROCESO (vaciado - el número real de rendimiento)
        proceso_rendimiento = (proceso_kg_pt / proceso_kg_mp * 100) if proceso_kg_mp > 0 else 0
        proceso_merma = proceso_kg_mp - proceso_kg_pt
        proceso_merma_pct = (proceso_merma / proceso_kg_mp * 100) if proceso_kg_mp > 0 else 0
        proceso_kg_por_hh = (proceso_kg_pt / proceso_hh) if proceso_hh > 0 else 0
        
        # KPIs de CONGELADO (túneles - ~100% pero volumen diferente)
        congelado_rendimiento = (congelado_kg_pt / congelado_kg_mp * 100) if congelado_kg_mp > 0 else 0
        
        overview = {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            # KPIs globales (referencia)
            'total_kg_mp': round(total_kg_mp, 2),
            'total_kg_pt': round(total_kg_pt, 2),
            'rendimiento_promedio': round(rendimiento_promedio, 2),
            'merma_total_kg': round(merma_total, 2),
            'merma_pct': round(merma_pct, 2),
            'total_hh': round(total_hh, 2),
            'kg_por_hh': round(kg_por_hh, 2),
            'mos_procesadas': mos_procesadas,
            'lotes_unicos': len(lotes_set),
            'total_costo_electricidad': round(total_costo_electricidad, 0),
            
            # === KPIs de PROCESO (vaciado) - EL NÚMERO REAL ===
            'proceso_kg_mp': round(proceso_kg_mp, 2),
            'proceso_kg_pt': round(proceso_kg_pt, 2),
            'proceso_rendimiento': round(proceso_rendimiento, 2),
            'proceso_merma_kg': round(proceso_merma, 2),
            'proceso_merma_pct': round(proceso_merma_pct, 2),
            'proceso_hh': round(proceso_hh, 2),
            'proceso_kg_por_hh': round(proceso_kg_por_hh, 2),
            'proceso_mos': proceso_mos,
            
            # === KPIs de CONGELADO (túneles) ===
            'congelado_kg_mp': round(congelado_kg_mp, 2),
            'congelado_kg_pt': round(congelado_kg_pt, 2),
            'congelado_rendimiento': round(congelado_rendimiento, 2),
            'congelado_hh': round(congelado_hh, 2),
            'congelado_mos': congelado_mos
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
        
        return {
            'overview': overview,
            'consolidado': consolidado,
            'salas': resultado_salas,
            'mos': mos_resultado
        }

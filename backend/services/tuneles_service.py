"""
Servicio para automatización de órdenes de fabricación en túneles estáticos.
Maneja la lógica de creación de componentes y subproductos con sufijo -C.
"""

import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from shared.odoo_client import OdooClient


# Configuración de túneles y productos
TUNELES_CONFIG = {
    'TE1': {
        'producto_proceso_id': 15984,
        'producto_proceso_nombre': '[1.1] PROCESO CONGELADO TÚNEL ESTÁTICO 1',
        'sucursal': 'RF',
        'ubicacion_origen_id': 5452,
        'ubicacion_origen_nombre': 'RF/Stock/Camara 0°C REAL',
        'ubicacion_destino_id': 8479,
        'ubicacion_destino_nombre': 'Tránsito/Salida Túneles Estáticos',
        'sala_proceso': 'Tunel - Estatico 1',
        'picking_type_id': 192  # Rio Futuro: Congelar TE1 → RF/MO/CongTE1/XXXXX
    },
    'TE2': {
        'producto_proceso_id': 15985,
        'producto_proceso_nombre': '[1.2] PROCESO CONGELADO TÚNEL ESTÁTICO 2',
        'sucursal': 'RF',
        'ubicacion_origen_id': 5452,
        'ubicacion_origen_nombre': 'RF/Stock/Camara 0°C REAL',
        'ubicacion_destino_id': 8479,
        'ubicacion_destino_nombre': 'Tránsito/Salida Túneles Estáticos',
        'sala_proceso': 'Tunel - Estatico 2',
        'picking_type_id': 190  # Rio Futuro: Congelar TE2 → RF/MO/CongTE2/XXXXX
    },
    'TE3': {
        'producto_proceso_id': 15986,
        'producto_proceso_nombre': '[1.3] PROCESO CONGELADO TÚNEL ESTÁTICO 3',
        'sucursal': 'RF',
        'ubicacion_origen_id': 5452,
        'ubicacion_origen_nombre': 'RF/Stock/Camara 0°C REAL',
        'ubicacion_destino_id': 8479,
        'ubicacion_destino_nombre': 'Tránsito/Salida Túneles Estáticos',
        'sala_proceso': 'Tunel - Estatico 3',
        'picking_type_id': 191  # Rio Futuro: Congelar TE3 → RF/MO/CongTE3/XXXXX
    },
    'VLK': {
        'producto_proceso_id': 16446,
        'producto_proceso_nombre': '[1.1.1] PROCESO CONGELADO TÚNEL ESTÁTICO VLK',
        'sucursal': 'VLK',
        'ubicacion_origen_id': 8528,
        'ubicacion_origen_nombre': 'VLK/Camara 0°',
        'ubicacion_destino_id': 8532,
        'ubicacion_destino_nombre': 'Tránsito VLK/Salida Túnel Estático',
        'sala_proceso': 'Tunel - Estatico VLK',
        'picking_type_id': 219  # VILKUN: Congelar TE VLK → MO/CongTE/XXXXX
    }
}

# Mapeo de productos: fresco → congelado
PRODUCTOS_TRANSFORMACION = {
    15999: 16183,  # [102122000] FB MK Conv. IQF en Bandeja → [202122000] FB MK Conv. IQF Congelado en Bandeja
    16016: 16182,  # [102121000] FB S/V Conv. IQF en Bandeja → [202121000] FB S/V Conv. IQF Congelado en Bandeja
}

# Provisión eléctrica
PRODUCTO_ELECTRICIDAD_ID = 15033  # [ETE] Provisión Electricidad Túnel Estático ($/hr)
UOM_DOLARES_KG_ID = 210  # $/Kg - UoM para provisión eléctrica

# Ubicaciones virtuales
UBICACION_VIRTUAL_CONGELADO_ID = 8485  # Virtual Locations/Ubicación Congelado
UBICACION_VIRTUAL_PROCESOS_ID = 15     # Virtual Locations/Ubicación Procesos


class TunelesService:
    """Servicio para gestión de túneles estáticos."""
    
    def __init__(self, odoo: OdooClient):
        self.odoo = odoo
    
    def get_tuneles_disponibles(self) -> List[Dict]:
        """Obtiene la lista de túneles disponibles."""
        return [
            {
                'codigo': codigo,
                'nombre': config['producto_proceso_nombre'],
                'sucursal': config['sucursal']
            }
            for codigo, config in TUNELES_CONFIG.items()
        ]
    
    def validar_pallets_batch(self, codigos_pallets: List[str], buscar_ubicacion: bool = False) -> List[Dict]:
        """
        Valida múltiples pallets buscando por PACKAGE (PACK000XXXX) en 2 llamadas a Odoo.
        
        Args:
            codigos_pallets: Lista de códigos de PACKAGES (ej: PACK0010337)
            buscar_ubicacion: Si True, busca la ubicación real del pallet
            
        Returns:
            Lista de dicts con validación de cada pallet
        """
        if not codigos_pallets:
            return []
        
        resultados = []
        
        # LLAMADA 1: Buscar TODOS los packages en una sola llamada
        packages = self.odoo.search_read(
            'stock.quant.package',
            [('name', 'in', codigos_pallets)],
            ['id', 'name']
        )
        
        # Crear mapa de packages por código
        packages_map = {pkg['name']: pkg for pkg in packages}
        
        # Identificar pallets no encontrados
        codigos_encontrados = set(packages_map.keys())
        codigos_no_encontrados = set(codigos_pallets) - codigos_encontrados
        
        # === OPTIMIZACIÓN: Buscar recepciones pendientes en BATCH para pallets no encontrados ===
        reception_info_map = {}
        
        if codigos_no_encontrados:
            # LLAMADA BATCH: Buscar todos los packages por nombre
            packages_pendientes = self.odoo.search_read(
                'stock.quant.package',
                [('name', 'in', list(codigos_no_encontrados))],
                ['id', 'name']
            )
            
            if packages_pendientes:
                pkg_ids_pendientes = [p['id'] for p in packages_pendientes]
                pkg_name_to_id = {p['name']: p['id'] for p in packages_pendientes}
                
                # LLAMADA BATCH: Buscar todos los move_lines de estos packages
                move_lines_batch = self.odoo.search_read(
                    'stock.move.line',
                    [
                        '|',
                        ('result_package_id', 'in', pkg_ids_pendientes),
                        ('package_id', 'in', pkg_ids_pendientes),
                        ('picking_id', '!=', False)
                    ],
                    ['picking_id', 'product_id', 'qty_done', 'reserved_uom_qty', 'result_package_id', 'package_id'],
                    limit=100,
                    order='id desc'
                )
                
                # Obtener picking_ids únicos
                picking_ids_batch = list(set([ml['picking_id'][0] for ml in move_lines_batch if ml.get('picking_id')]))
                
                # LLAMADA BATCH: Obtener estado de todos los pickings de una vez
                pickings_batch = {}
                if picking_ids_batch:
                    pickings_data = self.odoo.search_read(
                        'stock.picking',
                        [('id', 'in', picking_ids_batch)],
                        ['id', 'state'],
                        limit=100
                    )
                    pickings_batch = {p['id']: p['state'] for p in pickings_data}
                
                # Procesar move_lines y asociar a packages
                for ml in move_lines_batch:
                    # Determinar qué package se está usando
                    pkg_id = None
                    if ml.get('result_package_id'):
                        pkg_id = ml['result_package_id'][0]
                    elif ml.get('package_id'):
                        pkg_id = ml['package_id'][0]
                    
                    if not pkg_id:
                        continue
                    
                    # Buscar el código del pallet
                    pkg_code = next((name for name, pid in pkg_name_to_id.items() if pid == pkg_id), None)
                    if not pkg_code:
                        continue
                    
                    # Verificar estado del picking
                    picking_id = ml['picking_id'][0]
                    picking_name = ml['picking_id'][1]
                    picking_state = pickings_batch.get(picking_id)
                    
                    if picking_state and picking_state not in ['done', 'cancel']:
                        # Solo guardar si aún no tenemos info para este pallet
                        if pkg_code not in reception_info_map:
                            base_url = os.environ.get('ODOO_URL', 'https://riofuturo.odoo.com')
                            odoo_url = f"{base_url}/web#id={picking_id}&model=stock.picking&view_type=form"
                            kg = ml['qty_done'] if ml['qty_done'] and ml['qty_done'] > 0 else ml.get('reserved_uom_qty', 0)
                            
                            reception_info_map[pkg_code] = {
                                'found_in_reception': True,
                                'picking_name': picking_name,
                                'picking_id': picking_id,
                                'state': picking_state,
                                'odoo_url': odoo_url,
                                'product_name': ml['product_id'][1] if ml['product_id'] else 'Desconocido',
                                'kg': kg,
                                'product_id': ml['product_id'][0] if ml['product_id'] else None
                            }
        
        # Agregar resultados de no encontrados
        for codigo in codigos_no_encontrados:
            reception_info = reception_info_map.get(codigo)

            if reception_info:
                resultados.append({
                    'existe': False, # Falso en stock disponible
                    'codigo': codigo,
                    'error': f'Pallet en recepción pendiente: {reception_info["picking_name"]}',
                    'reception_info': reception_info,
                    'kg': reception_info['kg'],
                    'product_id': reception_info['product_id'],
                    'producto_nombre': reception_info['product_name']
                })
            else:
                resultados.append({
                    'existe': False,
                    'codigo': codigo,
                    'error': f'Paquete {codigo} no encontrado en Odoo',
                    'reception_info': None
                })
        
        # Si no hay packages encontrados, retornar
        if not packages:
            return resultados
        
        # LLAMADA 2: Buscar TODOS los quants asociados a esos packages
        package_ids = [pkg['id'] for pkg in packages]
        quants = self.odoo.search_read(
            'stock.quant',
            [('package_id', 'in', package_ids), ('quantity', '>', 0)],
            ['package_id', 'lot_id', 'quantity', 'location_id', 'product_id']
        )
        
        # Agrupar quants por package_id
        quants_por_package = {}
        for quant in quants:
            pkg_id = quant['package_id'][0]
            if pkg_id not in quants_por_package:
                quants_por_package[pkg_id] = []
            quants_por_package[pkg_id].append(quant)
        
        # === OPTIMIZACIÓN BATCH: Buscar recepciones pendientes para packages sin stock ===
        packages_sin_stock = [packages_map[codigo] for codigo in codigos_encontrados 
                             if not quants_por_package.get(packages_map[codigo]['id'])]
        
        reception_info_sin_stock = {}
        if packages_sin_stock:
            pkg_ids_sin_stock = [p['id'] for p in packages_sin_stock]
            pkg_id_to_name = {p['id']: p['name'] for p in packages_sin_stock}
            
            # LLAMADA BATCH: Buscar move_lines
            move_lines_sin_stock = self.odoo.search_read(
                'stock.move.line',
                [
                    ('result_package_id', 'in', pkg_ids_sin_stock),
                    ('picking_id', '!=', False)
                ],
                ['picking_id', 'product_id', 'qty_done', 'reserved_uom_qty', 'lot_id', 'result_package_id'],
                limit=100,
                order='id desc'
            )
            
            # Obtener picking_ids
            picking_ids_sin_stock = list(set([ml['picking_id'][0] for ml in move_lines_sin_stock if ml.get('picking_id')]))
            
            # LLAMADA BATCH: Estado de pickings
            pickings_sin_stock = {}
            if picking_ids_sin_stock:
                pickings_data = self.odoo.search_read(
                    'stock.picking',
                    [('id', 'in', picking_ids_sin_stock)],
                    ['id', 'state']
                )
                pickings_sin_stock = {p['id']: p['state'] for p in pickings_data}
            
            # Procesar y asociar
            for ml in move_lines_sin_stock:
                pkg_id = ml['result_package_id'][0] if ml.get('result_package_id') else None
                if not pkg_id or pkg_id not in pkg_id_to_name:
                    continue
                
                codigo = pkg_id_to_name[pkg_id]
                if codigo in reception_info_sin_stock:
                    continue  # Ya tenemos info
                
                picking_id = ml['picking_id'][0]
                picking_name = ml['picking_id'][1]
                picking_state = pickings_sin_stock.get(picking_id)
                
                if picking_state and picking_state not in ['done', 'cancel']:
                    base_url = os.environ.get('ODOO_URL', 'https://riofuturo.odoo.com')
                    odoo_url = f"{base_url}/web#id={picking_id}&model=stock.picking&view_type=form"
                    kg = ml['qty_done'] if ml['qty_done'] and ml['qty_done'] > 0 else ml.get('reserved_uom_qty', 0)
                    lot_id = ml['lot_id'][0] if ml.get('lot_id') else None
                    lot_name = ml['lot_id'][1] if ml.get('lot_id') else None
                    
                    reception_info_sin_stock[codigo] = {
                        'found_in_reception': True,
                        'picking_name': picking_name,
                        'picking_id': picking_id,
                        'state': picking_state,
                        'odoo_url': odoo_url,
                        'product_name': ml['product_id'][1] if ml['product_id'] else 'Desconocido',
                        'kg': kg,
                        'product_id': ml['product_id'][0] if ml['product_id'] else None,
                        'lot_id': lot_id,
                        'lot_name': lot_name
                    }
        
        # Procesar cada package encontrado
        for codigo in codigos_encontrados:
            package = packages_map[codigo]
            pkg_quants = quants_por_package.get(package['id'], [])
            
            if not pkg_quants:
                # Package existe pero sin stock - usar info precargada
                reception_info = reception_info_sin_stock.get(codigo)
                
                if reception_info:
                    resultados.append({
                        'existe': False,
                        'codigo': codigo,
                        'error': f'Pallet en recepción pendiente: {reception_info["picking_name"]}',
                        'reception_info': reception_info,
                        'kg': reception_info['kg'],
                        'product_id': reception_info['product_id'],
                        'producto_nombre': reception_info['product_name']
                    })
                else:
                    resultados.append({
                        'existe': True,
                        'codigo': codigo,
                        'kg': 0.0,
                        'ubicacion_id': None,
                        'ubicacion_nombre': None,
                        'producto_id': None,
                        'package_id': package['id'],
                        'advertencia': 'Paquete sin stock disponible'
                    })
                continue
            
            # Sumar cantidades
            kg_total = sum(q['quantity'] for q in pkg_quants)
            
            # Usar primera ubicación y producto
            ubicacion = pkg_quants[0]['location_id']
            producto_id = pkg_quants[0]['product_id'][0] if pkg_quants[0]['product_id'] else None
            lote_id = pkg_quants[0]['lot_id'][0] if pkg_quants[0].get('lot_id') else None
            lote_nombre = pkg_quants[0]['lot_id'][1] if pkg_quants[0].get('lot_id') else None
            
            resultados.append({
                'existe': True,
                'codigo': codigo,
                'kg': kg_total,
                'ubicacion_id': ubicacion[0] if ubicacion else None,
                'ubicacion_nombre': ubicacion[1] if ubicacion else None,
                'producto_id': producto_id,
                'producto_nombre': pkg_quants[0]['product_id'][1] if pkg_quants[0]['product_id'] else None,
                'package_id': package['id'],
                'lote_id': lote_id,
                'lote_nombre': lote_nombre
            })
        
        return resultados
    
    def validar_pallet(self, codigo_pallet: str, buscar_ubicacion: bool = False) -> Dict:
        """
        Valida un solo pallet buscando por PACKAGE (wrapper sobre validar_pallets_batch).
        
        Args:
            codigo_pallet: Código del PACKAGE (ej: PACK0010337)
            buscar_ubicacion: Si True, busca la ubicación real del pallet
            
        Returns:
            Dict con: existe, kg, ubicacion_id, ubicacion_nombre, producto_id, package_id
        """
        resultados = self.validar_pallets_batch([codigo_pallet], buscar_ubicacion)
        return resultados[0] if resultados else {
            'existe': False,
            'codigo': codigo_pallet,
            'error': 'Error al validar pallet'
        }
    
    def verificar_pendientes(self, mo_id: int) -> Dict:
        """
        Verifica el estado de las recepciones pendientes de una MO.
        
        Args:
            mo_id: ID de la orden de fabricación
            
        Returns:
            Dict con: mo_name, has_pending, pickings (con estado actual), all_ready
        """
        import json
        
        try:
            # Leer la MO
            mo = self.odoo.search_read(
                'mrp.production',
                [('id', '=', mo_id)],
                ['name', 'x_studio_pending_receptions', 'state'],
                limit=1
            )
            
            if not mo:
                return {'success': False, 'error': 'MO no encontrada'}
            
            mo = mo[0]
            pending_json = mo.get('x_studio_pending_receptions')
            
            # Si no hay datos JSON o está vacío
            if not pending_json:
                return {
                    'success': True,
                    'mo_name': mo['name'],
                    'has_pending': False,
                    'all_ready': True,
                    'pickings': []
                }
            
            # Parsear JSON
            try:
                pending_data = json.loads(pending_json) if isinstance(pending_json, str) else pending_json
            except:
                return {
                    'success': True,
                    'mo_name': mo['name'],
                    'has_pending': True,
                    'all_ready': False,
                    'pickings': [],
                    'error': 'Error al parsear JSON de pendientes'
                }
            
            # Si pending es False, no hay pendientes
            if not pending_data.get('pending', True):
                return {
                    'success': True,
                    'mo_name': mo['name'],
                    'has_pending': False,
                    'all_ready': True,
                    'pickings': []
                }
            
            picking_ids = pending_data.get('picking_ids', [])
            
            # Verificar estado de cada picking
            pickings = self.odoo.search_read(
                'stock.picking',
                [('id', 'in', picking_ids)],
                ['name', 'state', 'id']
            )
            
            pickings_info = []
            all_done = True
            
            for p in pickings:
                is_done = p['state'] == 'done'
                pickings_info.append({
                    'id': p['id'],
                    'name': p['name'],
                    'state': p['state'],
                    'is_done': is_done
                })
                if not is_done:
                    all_done = False
            
            return {
                'success': True,
                'mo_id': mo_id,
                'mo_name': mo['name'],
                'mo_state': mo['state'],
                'has_pending': True,
                'all_ready': all_done,
                'pickings': pickings_info,
                'pending_count': len([p for p in pickings_info if not p['is_done']]),
                'ready_count': len([p for p in pickings_info if p['is_done']])
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def completar_pendientes(self, mo_id: int) -> Dict:
        """
        Quita el flag de pendientes cuando todas las recepciones están validadas.
        
        Args:
            mo_id: ID de la orden de fabricación
            
        Returns:
            Dict con: success, mensaje
        """
        try:
            # Primero verificar que todas estén listas
            verificacion = self.verificar_pendientes(mo_id)
            
            if not verificacion.get('success'):
                return verificacion
            
            if not verificacion.get('all_ready'):
                pending = verificacion.get('pending_count', 0)
                return {
                    'success': False,
                    'error': f'Aún hay {pending} recepciones pendientes de validar'
                }
            
            # Limpiar el JSON de pendientes (marcar como completado)
            import json
            completed_data = json.dumps({
                'pending': False,
                'completed_at': datetime.now().isoformat()
            })
            # Usar execute_kw directamente con formato correcto
            self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'mrp.production', 'write',
                [[mo_id], {'x_studio_pending_receptions': completed_data}]
            )
            
            return {
                'success': True,
                'mo_id': mo_id,
                'mo_name': verificacion['mo_name'],
                'mensaje': 'Flag de pendientes removido. MO lista para confirmar.'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def obtener_detalle_pendientes(self, mo_id: int) -> Dict:
        """
        Obtiene el detalle de los pallets pendientes de una MO,
        verificando cuáles ya tienen stock disponible.
        
        Args:
            mo_id: ID de la orden de fabricación
            
        Returns:
            Dict con: success, mo_name, pallets (lista con estado de cada uno)
        """
        try:
            import json
            
            # Leer MO y su JSON de pendientes
            mo_data = self.odoo.read('mrp.production', [mo_id], 
                ['name', 'x_studio_pending_receptions', 'move_raw_ids'])[0]
            
            mo_name = mo_data['name']
            pending_json = mo_data.get('x_studio_pending_receptions')
            
            if not pending_json:
                return {
                    'success': True,
                    'mo_id': mo_id,
                    'mo_name': mo_name,
                    'tiene_pendientes': False,
                    'pallets': [],
                    'mensaje': 'Esta MO no tiene pendientes registrados'
                }
            
            # Parsear JSON
            pending_data = json.loads(pending_json) if isinstance(pending_json, str) else pending_json
            
            if not pending_data.get('pending'):
                return {
                    'success': True,
                    'mo_id': mo_id,
                    'mo_name': mo_name,
                    'tiene_pendientes': False,
                    'pallets': [],
                    'mensaje': 'Pendientes ya fueron completados'
                }
            
            pallets_info = pending_data.get('pallets', [])
            picking_ids = pending_data.get('picking_ids', [])
            
            # Obtener info de pickings para mostrar nombre
            picking_names = {}
            if picking_ids:
                pickings = self.odoo.search_read(
                    'stock.picking',
                    [('id', 'in', picking_ids)],
                    ['id', 'name', 'state']
                )
                picking_names = {p['id']: {'name': p['name'], 'state': p['state']} for p in pickings}
            
            # Obtener los componentes actuales de la MO para saber cuáles ya se agregaron
            move_raw_ids = mo_data.get('move_raw_ids', [])
            componentes_existentes = set()
            if move_raw_ids:
                moves = self.odoo.search_read(
                    'stock.move.line',
                    [('move_id', 'in', move_raw_ids)],
                    ['package_id']
                )
                for m in moves:
                    if m.get('package_id'):
                        componentes_existentes.add(m['package_id'][1])  # Nombre del package
            
            # Verificar disponibilidad de cada pallet
            resultado_pallets = []
            for p in pallets_info:
                codigo = p.get('codigo', '')
                kg = p.get('kg', 0)
                producto_id = p.get('producto_id')
                picking_id = p.get('picking_id')
                
                # Verificar si el pallet ya fue agregado como componente
                ya_agregado = codigo in componentes_existentes
                
                # Verificar si tiene stock disponible
                quants = self.odoo.search_read(
                    'stock.quant',
                    [
                        ('package_id.name', '=', codigo),
                        ('quantity', '>', 0),
                        ('location_id.usage', '=', 'internal')
                    ],
                    ['quantity', 'location_id', 'product_id', 'lot_id'],
                    limit=1
                )
                
                tiene_stock = len(quants) > 0
                
                picking_info = picking_names.get(picking_id, {})
                picking_state = picking_info.get('state', 'unknown')
                picking_name = picking_info.get('name', 'N/A')
                
                # Determinar estado
                if ya_agregado:
                    estado = 'agregado'
                    estado_label = '✅ Ya agregado'
                elif tiene_stock:
                    estado = 'disponible'
                    estado_label = '🟢 Disponible'
                else:
                    estado = 'pendiente'
                    estado_label = '🟠 Pendiente'
                
                resultado_pallets.append({
                    'codigo': codigo,
                    'kg': kg,
                    'producto_id': producto_id,
                    'picking_id': picking_id,
                    'picking_name': picking_name,
                    'picking_state': picking_state,
                    'estado': estado,
                    'estado_label': estado_label,
                    'tiene_stock': tiene_stock,
                    'ya_agregado': ya_agregado,
                    'quant_info': quants[0] if quants else None
                })
            
            # Contar estados
            total = len(resultado_pallets)
            agregados = sum(1 for p in resultado_pallets if p['estado'] == 'agregado')
            disponibles = sum(1 for p in resultado_pallets if p['estado'] == 'disponible')
            pendientes = sum(1 for p in resultado_pallets if p['estado'] == 'pendiente')
            
            # Ordenar pallets: disponibles primero, luego pendientes
            resultado_pallets_ordenados = sorted(resultado_pallets, 
                key=lambda x: (0 if x['estado'] == 'agregado' else 1 if x['estado'] == 'disponible' else 2))
            
            # Obtener componentes (move_raw_ids) con detalle
            componentes = []
            electricidad_total = 0
            move_raw_ids = mo_data.get('move_raw_ids', [])
            if move_raw_ids:
                # Obtener los moves
                raw_moves = self.odoo.search_read(
                    'stock.move',
                    [('id', 'in', move_raw_ids)],
                    ['product_id', 'product_uom_qty', 'quantity_done', 'state', 'reference']
                )
                
                for move in raw_moves:
                    producto_nombre = move['product_id'][1] if move['product_id'] else 'N/A'
                    kg = move.get('quantity_done', 0) or move.get('product_uom_qty', 0)
                    
                    # Detectar electricidad
                    es_electricidad = 'ETE' in producto_nombre or 'Electricidad' in producto_nombre
                    if es_electricidad:
                        # Calcular costo (asumiendo precio ~$35.10 por kg según imagen)
                        electricidad_total = kg * 35.10
                    
                    # Obtener move_lines para lote y package
                    move_lines = self.odoo.search_read(
                        'stock.move.line',
                        [('move_id', '=', move['id'])],
                        ['lot_id', 'package_id', 'qty_done', 'location_id']
                    )
                    
                    for line in move_lines:
                        componentes.append({
                            'producto': producto_nombre,
                            'lote': line['lot_id'][1] if line.get('lot_id') else 'Sin lote',
                            'pallet': line['package_id'][1] if line.get('package_id') else 'Sin pallet',
                            'kg': line.get('qty_done', 0),
                            'ubicacion': line['location_id'][1] if line.get('location_id') else 'N/A',
                            'es_electricidad': es_electricidad
                        })
            
            # Obtener subproductos (move_finished_ids) - leer de la MO
            subproductos = []
            mo_full = self.odoo.read('mrp.production', [mo_id], ['move_finished_ids'])[0]
            move_finished_ids = mo_full.get('move_finished_ids', [])
            if move_finished_ids:
                finished_moves = self.odoo.search_read(
                    'stock.move',
                    [('id', 'in', move_finished_ids)],
                    ['product_id', 'product_uom_qty', 'quantity_done', 'state']
                )
                
                for move in finished_moves:
                    producto_nombre = move['product_id'][1] if move['product_id'] else 'N/A'
                    
                    move_lines = self.odoo.search_read(
                        'stock.move.line',
                        [('move_id', '=', move['id'])],
                        ['lot_id', 'package_id', 'qty_done', 'location_dest_id']
                    )
                    
                    for line in move_lines:
                        subproductos.append({
                            'producto': producto_nombre,
                            'lote': line['lot_id'][1] if line.get('lot_id') else 'Sin lote',
                            'pallet': line['package_id'][1] if line.get('package_id') else 'Sin pallet',
                            'kg': line.get('qty_done', 0),
                            'ubicacion': line['location_dest_id'][1] if line.get('location_dest_id') else 'N/A'
                        })
            
            return {
                'success': True,
                'mo_id': mo_id,
                'mo_name': mo_name,
                'tiene_pendientes': pendientes > 0,
                'pallets': resultado_pallets_ordenados,
                'resumen': {
                    'total': total,
                    'agregados': agregados,
                    'disponibles': disponibles,
                    'pendientes': pendientes
                },
                'todos_listos': pendientes == 0 and disponibles == 0,
                'hay_disponibles_sin_agregar': disponibles > 0,
                'componentes': componentes,
                'subproductos': subproductos,
                'electricidad_total': electricidad_total
            }
            
        except Exception as e:
            import traceback
            return {
                'success': False, 
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def agregar_componentes_disponibles(self, mo_id: int) -> Dict:
        """
        Agrega como componentes los pallets que ahora están disponibles.
        
        Args:
            mo_id: ID de la orden de fabricación
            
        Returns:
            Dict con: success, agregados (cantidad), mensaje
        """
        try:
            import json
            
            # Obtener detalle actual
            detalle = self.obtener_detalle_pendientes(mo_id)
            if not detalle.get('success'):
                return detalle
            
            if not detalle.get('hay_disponibles_sin_agregar'):
                return {
                    'success': True,
                    'agregados': 0,
                    'mensaje': 'No hay pallets disponibles pendientes de agregar'
                }
            
            # Obtener config del túnel basado en la MO
            mo_data = self.odoo.read('mrp.production', [mo_id], 
                ['name', 'product_id', 'x_studio_pending_receptions'])[0]
            mo_name = mo_data['name']
            
            # Identificar túnel por producto
            config = None
            for codigo, cfg in TUNELES_CONFIG.items():
                if cfg['producto_proceso_id'] == mo_data['product_id'][0]:
                    config = cfg
                    break
            
            if not config:
                return {
                    'success': False,
                    'error': 'No se pudo identificar el túnel de esta MO'
                }
            
            ubicacion_virtual = UBICACION_VIRTUAL_CONGELADO_ID if config['sucursal'] == 'RF' else UBICACION_VIRTUAL_PROCESOS_ID
            
            # Procesar pallets disponibles
            agregados = 0
            pallets_agregados = []
            pending_json = mo_data.get('x_studio_pending_receptions')
            pending_data = json.loads(pending_json) if isinstance(pending_json, str) else pending_json
            
            for pallet in detalle['pallets']:
                if pallet['estado'] != 'disponible':
                    continue
                
                codigo = pallet['codigo']
                producto_id = pallet['producto_id']
                quant_info = pallet.get('quant_info', {})
                kg = quant_info.get('quantity', pallet['kg'])
                lote_id = quant_info.get('lot_id', [None])[0] if quant_info.get('lot_id') else None
                ubicacion_id = quant_info.get('location_id', [None])[0] if quant_info.get('location_id') else config['ubicacion_origen_id']
                
                # Buscar el package_id
                package = self.odoo.search_read(
                    'stock.quant.package',
                    [('name', '=', codigo)],
                    ['id'],
                    limit=1
                )
                package_id = package[0]['id'] if package else None
                
                # --- MEJORA: Buscar stock.move existente para NO duplicar demanda ---
                # Buscamos el move_id que ya creamos al inicio (el que tiene la demanda)
                moves = self.odoo.search_read(
                    'stock.move',
                    [
                        ('raw_material_production_id', '=', mo_id),
                        ('product_id', '=', producto_id),
                        ('state', '!=', 'cancel')
                    ],
                    ['id'],
                    limit=1
                )
                
                if moves:
                    move_id = moves[0]['id']
                    print(f"DEBUG: Reutilizando stock.move {move_id} para pallet {codigo}")
                else:
                    # Fallback por si alguien borró la línea manual en Odoo
                    move_data = {
                        'name': mo_name,
                        'product_id': producto_id,
                        'product_uom_qty': kg,
                        'product_uom': 12,  # kg
                        'location_id': ubicacion_id,
                        'location_dest_id': ubicacion_virtual,
                        'state': 'draft',
                        'raw_material_production_id': mo_id,
                        'company_id': 1,
                        'reference': mo_name
                    }
                    move_id = self.odoo.execute('stock.move', 'create', move_data)
                    print(f"DEBUG: Creado nuevo stock.move {move_id} (fallback) para pallet {codigo}")
                
                # Crear stock.move.line con qty_done
                move_line_data = {
                    'move_id': move_id,
                    'product_id': producto_id,
                    'qty_done': kg,
                    'reserved_uom_qty': kg,
                    'product_uom_id': 12,
                    'location_id': ubicacion_id,
                    'location_dest_id': ubicacion_virtual,
                    'state': 'draft',
                    'reference': mo_name,
                    'company_id': 1
                }
                
                if lote_id:
                    move_line_data['lot_id'] = lote_id
                if package_id:
                    move_line_data['package_id'] = package_id
                
                self.odoo.execute('stock.move.line', 'create', move_line_data)

                # --- NUEVO: También crear la línea de SUBPRODUCTO (-C) ---
                # Ya que también se saltó al crear la MO
                try:
                    # Determinar producto de salida
                    # Transformar código: primer dígito 1 → 2 para variante congelada
                    producto_id_output = producto_id # Fallback
                    prod_input_data = self.odoo.read('product.product', [producto_id], ['default_code'])[0]
                    codigo_input = prod_input_data.get('default_code')
                    if codigo_input and len(codigo_input) >= 1 and codigo_input[0] == '1':
                        codigo_output = '2' + codigo_input[1:]
                        prod_output_ids = self.odoo.search('product.product', [('default_code', '=', codigo_output)])
                        if prod_output_ids:
                            producto_id_output = prod_output_ids[0]

                    # Buscar el stock.move de salida existente en la MO
                    moves_out = self.odoo.search_read(
                        'stock.move',
                        [
                            ('production_id', '=', mo_id),
                            ('product_id', '=', producto_id_output),
                            ('state', '!=', 'cancel')
                        ],
                        ['id'],
                        limit=1
                    )
                    
                    if moves_out:
                        move_out_id = moves_out[0]['id']
                        
                        # Generar nombres para lote y package -C
                        # Prioridad: usar lote de origen si existe
                        lote_name_out = f"{pallet.get('lote_nombre') or pallet.get('codigo') or codigo}-C"
                        
                        # Limpiar nombre del pallet para el sufijo -C
                        clean_code = codigo[4:] if codigo.startswith('PACK') else codigo[3:] if codigo.startswith('PAC') else codigo
                        package_name_out = f"PACK{clean_code}-C"
                        
                        # Buscar/Crear Lote y Package de salida
                        lote_id_out = self._buscar_o_crear_lote(lote_name_out, producto_id_output)
                        pkgs_out = self.odoo.search('stock.quant.package', [('name', '=', package_name_out)])
                        if pkgs_out:
                            package_id_out = pkgs_out[0]
                        else:
                            package_id_out = self.odoo.execute('stock.quant.package', 'create', {'name': package_name_out, 'company_id': 1})
                        
                        # Crear la línea de subproducto (stock.move.line)
                        subprod_line = {
                            'move_id': move_out_id,
                            'product_id': producto_id_output,
                            'qty_done': kg,
                            'product_uom_id': 12, # kg
                            'location_id': ubicacion_virtual,
                            'location_dest_id': config['ubicacion_destino_id'],
                            'lot_id': lote_id_out,
                            'result_package_id': package_id_out,
                            'state': 'draft',
                            'reference': mo_name,
                            'company_id': 1
                        }
                        self.odoo.execute('stock.move.line', 'create', subprod_line)
                        print(f"DEBUG: Creada línea de subproducto {package_name_out} para pallet {codigo}")
                except Exception as e_sub:
                    print(f"ERROR: No se pudo crear subproducto para {codigo}: {e_sub}")
                
                agregados += 1
                pallets_agregados.append(codigo)
            
            # Actualizar JSON: marcar pallets como procesados
            pallets_actualizados = []
            for p in pending_data.get('pallets', []):
                if p.get('codigo') in pallets_agregados:
                    p['procesado'] = True
                    p['procesado_at'] = datetime.now().isoformat()
                pallets_actualizados.append(p)
            
            pending_data['pallets'] = pallets_actualizados
            
            # Verificar si quedan pendientes
            pendientes_restantes = sum(1 for p in pallets_actualizados 
                                       if not p.get('procesado'))
            if pendientes_restantes == 0:
                pending_data['pending'] = False
                pending_data['completed_at'] = datetime.now().isoformat()
            
            # Guardar JSON actualizado
            self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'mrp.production', 'write',
                [[mo_id], {'x_studio_pending_receptions': json.dumps(pending_data)}]
            )
            
            return {
                'success': True,
                'agregados': agregados,
                'pallets_agregados': pallets_agregados,
                'pendientes_restantes': pendientes_restantes,
                'mensaje': f'Se agregaron {agregados} componentes. Quedan {pendientes_restantes} pendientes.'
            }
            
        except Exception as e:
            import traceback
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def listar_ordenes_recientes(
        self, 
        tunel: Optional[str] = None, 
        estado: Optional[str] = None, 
        limit: int = 50,
        solo_pendientes: bool = False
    ) -> List[Dict]:
        """
        Lista las órdenes de fabricación recientes de túneles estáticos con información extendida.
        
        Args:
            tunel: Filtrar por túnel (TE1, TE2, TE3, VLK)
            estado: Filtrar por estado de Odoo (draft, confirmed, progress, done, cancel)
            limit: Límite de resultados
            solo_pendientes: Si True, solo retorna órdenes con stock pendiente (en JSON)
            
        Returns:
            Lista de dicts con información de cada orden
        """
        try:
            import json
            
            # Construir dominio base: Solo productos de túneles
            producto_ids = [cfg['producto_proceso_id'] for cfg in TUNELES_CONFIG.values()]
            domain = [('product_id', 'in', producto_ids)]
            
            # Filtrar por túnel específico
            if tunel and tunel in TUNELES_CONFIG:
                domain = [('product_id', '=', TUNELES_CONFIG[tunel]['producto_proceso_id'])]
            
            # Filtrar por estado de Odoo
            if estado == 'pendientes':
                # 'pendientes' tradicional: estados activos
                domain.append(('state', 'in', ['draft', 'confirmed', 'progress']))
            elif estado == 'done':
                domain.append(('state', '=', 'done'))
            elif estado == 'cancel':
                domain.append(('state', '=', 'cancel'))
            elif estado and estado in ['draft', 'confirmed', 'progress']:
                domain.append(('state', '=', estado))
            
            # Filtro especial: Solo órdenes que tienen el flag de pendientes en el JSON de Studio
            if solo_pendientes:
                domain.append(('x_studio_pending_receptions', '!=', False))
            
            # Buscar órdenes
            ordenes = self.odoo.search_read(
                'mrp.production',
                domain,
                [
                    'id', 'name', 'product_id', 'product_qty', 'state',
                    'create_date', 'date_planned_start',
                    'x_studio_pending_receptions',
                    'move_raw_ids', 'move_finished_ids'
                ],
                limit=limit,
                order='create_date desc'
            )
            
            resultado = []
            
            for orden in ordenes:
                # 1. Identificar túnel
                tunel_codigo = None
                for codigo, cfg in TUNELES_CONFIG.items():
                    if orden['product_id'] and cfg['producto_proceso_id'] == orden['product_id'][0]:
                        tunel_codigo = codigo
                        break
                
                # 2. Verificar si tiene pendientes REALES en el JSON
                tiene_pendientes = False
                pending_json = orden.get('x_studio_pending_receptions')
                if pending_json:
                    try:
                        p_data = json.loads(pending_json) if isinstance(pending_json, str) else pending_json
                        tiene_pendientes = p_data.get('pending', False)
                    except:
                        pass
                
                # Si pedimos solo pendientes y esta no tiene, saltar
                if solo_pendientes and not tiene_pendientes:
                    continue
                
                # 3. Calcular electricidad y contar componentes reales (no-servicios)
                componentes_count = 0
                electricidad_costo = 0
                move_raw_ids = orden.get('move_raw_ids', [])
                
                if move_raw_ids:
                    # Contar move_lines para mayor precisión si es necesario, 
                    # pero para el listado usamos move_ids por performance a menos que sea necesario
                    # Aquí usamos el conteo de move_raw_ids como fallback rápido
                    componentes_count = len(move_raw_ids)
                    
                    # Intentar obtener costo de electricidad si ya existe el movimiento
                    # (Se calculó en la creación: Kg * $35.10 aprox)
                    # Por ahora usamos la fórmula rápida para el listado
                    electricidad_costo = orden.get('product_qty', 0) * 35.10
                
                # 4. Contar subproductos
                subproductos_count = len(orden.get('move_finished_ids', []))
                
                resultado.append({
                    'id': orden['id'],
                    'nombre': orden['name'],
                    'mo_name': orden['name'],
                    'tunel': tunel_codigo,
                    'producto': orden['product_id'][1] if orden['product_id'] else 'N/A',
                    'producto_nombre': orden['product_id'][1] if orden['product_id'] else 'N/A',
                    'kg_total': orden.get('product_qty', 0),
                    'estado': orden.get('state', 'draft'),
                    'fecha_creacion': orden.get('create_date'),
                    'fecha_planificada': orden.get('date_planned_start'),
                    'tiene_pendientes': tiene_pendientes,
                    'componentes_count': componentes_count,
                    'subproductos_count': subproductos_count,
                    'electricidad_costo': electricidad_costo,
                    'pallets_count': componentes_count
                })
            
            return resultado
            
        except Exception as e:
            print(f"Error en listar_ordenes_recientes: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def crear_orden_fabricacion(
        self,
        tunel: str,
        pallets: List[Dict[str, float]],
        buscar_ubicacion_auto: bool = False,
        responsable_id: Optional[int] = None
    ) -> Dict:
        """
        Crea una orden de fabricación para un túnel estático.
        
        Args:
            tunel: Código del túnel (TE1, TE2, TE3, VLK)
            pallets: Lista de dicts con {codigo: str, kg: float}
            buscar_ubicacion_auto: Si True, busca ubicación real del pallet
            responsable_id: ID del usuario responsable
            
        Returns:
            Dict con: success, mo_id, mo_name, total_kg, errores, advertencias
        """
        if tunel not in TUNELES_CONFIG:
            return {
                'success': False,
                'error': f'Túnel {tunel} no válido. Opciones: {list(TUNELES_CONFIG.keys())}'
            }
        
        config = TUNELES_CONFIG[tunel]
        errores = []
        advertencias = []
        
        # 0. VALIDAR DUPLICADOS: Verificar que los pallets no estén en otras MOs activas
        codigos_pallets = [p['codigo'] for p in pallets]
        
        # Buscar packages con estos códigos
        packages = self.odoo.search_read(
            'stock.quant.package',
            [('name', 'in', codigos_pallets)],
            ['id', 'name']
        )
        package_ids = [pkg['id'] for pkg in packages]
        packages_map = {pkg['name']: pkg['id'] for pkg in packages}
        
        if package_ids:
            # Buscar en stock.move.line si estos packages están en MOs no canceladas/terminadas
            move_lines = self.odoo.search_read(
                'stock.move.line',
                [
                    ('package_id', 'in', package_ids),
                    ('production_id', '!=', False)
                ],
                ['package_id', 'production_id'],
                limit=100
            )
            
            if move_lines:
                # Verificar estado de las MOs encontradas
                mo_ids = list(set([ml['production_id'][0] for ml in move_lines]))
                mos = self.odoo.search_read(
                    'mrp.production',
                    [('id', 'in', mo_ids), ('state', 'not in', ['done', 'cancel'])],
                    ['id', 'name', 'state']
                )
                
                if mos:
                    # Mapear package_id a mo_name
                    pkg_to_mo = {}
                    for ml in move_lines:
                        pkg_id = ml['package_id'][0]
                        mo_id = ml['production_id'][0]
                        mo_match = [m for m in mos if m['id'] == mo_id]
                        if mo_match:
                            pkg_to_mo[pkg_id] = mo_match[0]['name']
                    
                    # Verificar si algún pallet de la lista está en estas MOs
                    for codigo in codigos_pallets:
                        pkg_id = packages_map.get(codigo)
                        if pkg_id and pkg_id in pkg_to_mo:
                            errores.append(f"{codigo}: Ya está en orden {pkg_to_mo[pkg_id]} (activa)")
        
        if errores:
            return {
                'success': False,
                'errores': errores,
                'error': f"Pallets ya usados en otras órdenes activas: {', '.join(codigos_pallets[:3])}"
            }
        
        # 1. Validar todos los pallets primero
        pallets_validados = []
        for pallet in pallets:
            # --- NUEVO FLUJO: Pallets que están en Recepción Pendiente ---
            if pallet.get('pendiente_recepcion'):
                # Validamos que traiga data mínima
                if not pallet.get('producto_id'):
                     errores.append(f"{pallet['codigo']}: Pallet pendiente sin producto identificado")
                     continue
                
                pallets_validados.append({
                    'codigo': pallet['codigo'],
                    'kg': float(pallet.get('kg', 0)),
                    'lote_id': pallet.get('lot_id'),  # Puede venir del frontend
                    'lote_nombre': pallet.get('lot_name'),  # Nombre del lote desde recepción
                    'producto_id': int(pallet['producto_id']),
                    'ubicacion_id': config['ubicacion_origen_id'], 
                    'package_id': None,  # No asignamos package aún
                    'manual': False,
                    'pendiente_recepcion': True,  # Flag para saber que es especial
                    'picking_id': pallet.get('picking_id')  # Guardar picking_id para JSON
                })
                # DEBUG: Log de datos del pallet pendiente
                print(f"DEBUG Pallet Pendiente: codigo={pallet['codigo']}, lot_name={pallet.get('lot_name')}, lot_id={pallet.get('lot_id')}")
                advertencias.append(f"Pallet {pallet['codigo']} agregado desde Recepción Pendiente (Sin reserva stock)")
                continue

            # --- MEJORA: Soporte para Pallets Manuales (Legacy/Fallback) ---
            if pallet.get('manual'):
                # Si es manual, confiamos en los datos enviados
                if not pallet.get('producto_id'):
                    errores.append(f"{pallet['codigo']}: Pallet manual debe incluir producto_id")
                    continue
                if not pallet.get('kg') or pallet['kg'] <= 0:
                    errores.append(f"{pallet['codigo']}: Pallet manual debe incluir Kg > 0")
                    continue
                
                pallets_validados.append({
                    'codigo': pallet['codigo'],
                    'kg': pallet['kg'],
                    'lote_id': None, # Sin lote en Odoo
                    'producto_id': pallet['producto_id'],
                    'ubicacion_id': config['ubicacion_origen_id'], # Usar ubicación por defecto del túnel
                    'package_id': None, # Sin package en Odoo
                    'manual': True # Marcamos como manual
                })
                advertencias.append(f"Pallet {pallet['codigo']} ingresado manualmente sin trazabilidad")
                continue
            
            # Flujo normal: Validar en Odoo
            validacion = self.validar_pallet(pallet['codigo'], buscar_ubicacion_auto)
            
            if not validacion['existe']:
                errores.append(validacion['error'])
                continue
            
            # Si no tiene kg en Odoo, usar el ingresado manualmente
            kg = validacion['kg'] if validacion['kg'] > 0 else pallet.get('kg', 0)
            
            if kg <= 0:
                advertencias.append(f"{pallet['codigo']}: Sin stock, debe ingresar kg manualmente")
                kg = pallet.get('kg', 0)
                if kg <= 0:
                    errores.append(f"{pallet['codigo']}: Debe especificar cantidad en Kg")
                    continue
            
            pallets_validados.append({
                'codigo': pallet['codigo'],
                'kg': kg,
                'lote_id': validacion.get('lote_id'),
                'lote_nombre': validacion.get('lote_nombre'),  # Nombre del lote original
                'producto_id': validacion.get('producto_id'),
                'ubicacion_id': validacion.get('ubicacion_id', config['ubicacion_origen_id']),
                'package_id': validacion.get('package_id'),  # ID del paquete origen
                'manual': False
            })
        
        if errores:
            return {
                'success': False,
                'errores': errores,
                'advertencias': advertencias
            }
        
        if not pallets_validados:
            return {
                'success': False,
                'error': 'No hay pallets válidos para procesar'
            }
        
        # 2. Calcular totales por producto
        productos_totales = {}
        for pallet in pallets_validados:
            prod_id = pallet['producto_id']
            if prod_id not in productos_totales:
                productos_totales[prod_id] = {
                    'kg': 0,
                    'pallets': []
                }
            productos_totales[prod_id]['kg'] += pallet['kg']
            productos_totales[prod_id]['pallets'].append(pallet)
        
        total_kg = sum(p['kg'] for p in pallets_validados)
        
        # 3. Crear la orden de fabricación
        try:
            # --- MEJORA: Fechas sincronizadas ---
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            mo_data = {
                'product_id': config['producto_proceso_id'],
                'product_qty': total_kg,
                'product_uom_id': 12,  # kg
                'location_src_id': config['ubicacion_origen_id'],
                'location_dest_id': config['ubicacion_destino_id'],
                'picking_type_id': config['picking_type_id'],  # Tipo de operación para correlativo
                'state': 'draft',  # Borrador
                'company_id': 1,  # RIO FUTURO PROCESOS SPA
                'date_planned_start': now,
                'date_planned_finished': now,
                'x_studio_inicio_de_proceso': now,
                'x_studio_termino_de_proceso': now,
            }
            
            if responsable_id:
                mo_data['user_id'] = responsable_id
            
            mo_id = self.odoo.execute('mrp.production', 'create', mo_data)
            
            # --- MEJORA: Limpiar componentes del BoM por defecto ---
            # Al crear la MO, Odoo inserta componentes del BoM. Debemos borrarlos.
            mo_data_read = self.odoo.read('mrp.production', [mo_id], ['move_raw_ids', 'name'])[0]
            if mo_data_read.get('move_raw_ids'):
                self.odoo.execute('stock.move', 'unlink', mo_data_read['move_raw_ids'])
            
            mo_name = mo_data_read['name']
            
            # --- NUEVO: Detectar pallets pendientes y marcar MO ---
            pallets_pendientes = [p for p in pallets_validados if p.get('pendiente_recepcion')]
            has_pending = len(pallets_pendientes) > 0
            
            if has_pending:
                # Crear estructura JSON con datos de pendientes
                pending_data = {
                    'pending': True,
                    'created_at': datetime.now().isoformat(),
                    'pallets': []
                }
                
                picking_ids_set = set()
                for p in pallets_pendientes:  # Usar pallets_validados filtrados
                    if p.get('picking_id'):
                        picking_ids_set.add(p['picking_id'])
                    pending_data['pallets'].append({
                        'codigo': p['codigo'],
                        'picking_id': p.get('picking_id'),
                        'kg': p.get('kg', 0),
                        'producto_id': p.get('producto_id')
                    })
                
                pending_data['picking_ids'] = list(picking_ids_set)
                
                # Actualizar MO con JSON de pendientes
                try:
                    import json
                    pending_json = json.dumps(pending_data)
                    print(f"DEBUG: Intentando guardar JSON en MO {mo_id}: {pending_json[:100]}...")
                    # Usar execute_kw directamente con formato correcto para write
                    write_result = self.odoo.models.execute_kw(
                        self.odoo.db, self.odoo.uid, self.odoo.password,
                        'mrp.production', 'write',
                        [[mo_id], {'x_studio_pending_receptions': pending_json}]
                    )
                    print(f"DEBUG: Resultado del write: {write_result}")
                    if write_result:
                        advertencias.append(f"MO marcada con {len(pallets_pendientes)} pallets pendientes de recepción")
                    else:
                        advertencias.append(f"Write retornó False para guardar pendientes")
                except Exception as e:
                    print(f"DEBUG: Error en write: {e}")
                    advertencias.append(f"Error al guardar pendientes: {e}")
            
            # 4. Crear componentes (move_raw_ids)
            componentes_creados = self._crear_componentes(
                mo_id, 
                mo_name, 
                productos_totales, 
                config
            )

            # NOTA: Electricidad ya se agrega en _crear_componentes

            # 5. Crear subproductos (move_finished_ids)
            subproductos_creados = self._crear_subproductos(
                mo_id,
                mo_name,
                productos_totales,
                config
            )
            
            return {
                'success': True,
                'mo_id': mo_id,
                'mo_name': mo_name,
                'total_kg': total_kg,
                'pallets_count': len(pallets_validados),
                'componentes_count': componentes_creados,
                'subproductos_count': subproductos_creados,
                'advertencias': advertencias,
                'has_pending': has_pending,
                'pending_count': len(pallets_pendientes),
                'mensaje': f'Orden {mo_name} creada con {componentes_creados} componentes y {subproductos_creados} subproductos' + 
                          (f' ({len(pallets_pendientes)} pallets pendientes de recepción)' if has_pending else '')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error al crear orden de fabricación: {str(e)}'
            }
    
    def _buscar_o_crear_lotes_batch(self, lotes_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Busca o crea múltiples lotes en batch (OPTIMIZADO).
        
        Args:
            lotes_data: Lista de dicts con 'codigo' y 'producto_id'
            Ejemplo: [{'codigo': 'PAC0002683-C', 'producto_id': 16183}, ...]
            
        Returns:
            Dict mapeando codigo → lote_id
        """
        if not lotes_data:
            return {}
        
        # DEDUPLICAR entrada: evitar crear el mismo lote 2 veces en la misma llamada
        seen_keys = set()
        lotes_data_uniq = []
        for d in lotes_data:
            key = (d['codigo'], d['producto_id'])
            if key not in seen_keys:
                seen_keys.add(key)
                lotes_data_uniq.append(d)
        
        codigos = [d['codigo'] for d in lotes_data_uniq]
        producto_ids = list(set(d['producto_id'] for d in lotes_data_uniq))
        
        # LLAMADA 1: Buscar todos los lotes existentes por nombre Y producto
        lotes_existentes = self.odoo.search_read(
            'stock.lot',
            [('name', 'in', codigos), ('product_id', 'in', producto_ids)],
            ['name', 'id', 'product_id']
        )
        
        # Crear mapa con clave compuesta: (nombre, producto_id) -> lot_id
        lotes_existentes_set = {}
        for lot in lotes_existentes:
            key = (lot['name'], lot['product_id'][0] if lot['product_id'] else 0)
            lotes_existentes_set[key] = lot['id']
        
        # Mapa simple por nombre para retornar
        lotes_map = {}
        faltantes = []
        
        for d in lotes_data_uniq:
            key = (d['codigo'], d['producto_id'])
            if key in lotes_existentes_set:
                # Ya existe, reusar
                lotes_map[d['codigo']] = lotes_existentes_set[key]
            else:
                # No existe, necesita crearse
                faltantes.append(d)
        
        # LLAMADA 2: Crear SOLO los faltantes (ya deduplicados)
        if faltantes:
            print(f"DEBUG _buscar_o_crear_lotes_batch: Creando {len(faltantes)} lotes: {[(d['codigo'], d['producto_id']) for d in faltantes]}")
            nuevos_ids = self.odoo.execute('stock.lot', 'create', [
                {
                    'name': d['codigo'],
                    'product_id': d['producto_id'],
                    'company_id': 1
                }
                for d in faltantes
            ])
            
            # Si es un solo registro, execute retorna int, sino lista
            if isinstance(nuevos_ids, int):
                nuevos_ids = [nuevos_ids]
            
            # Agregar nuevos al mapa
            for d, nuevo_id in zip(faltantes, nuevos_ids):
                lotes_map[d['codigo']] = nuevo_id
        
        return lotes_map
    
    def _buscar_o_crear_packages_batch(self, package_names: List[str]) -> Dict[str, int]:
        """
        Busca o crea múltiples packages en batch (OPTIMIZADO).
        
        Args:
            package_names: Lista de nombres de packages (ej: ['PACK0002683-C', ...])
            
        Returns:
            Dict mapeando package_name → package_id
        """
        if not package_names:
            return {}
        
        # LLAMADA 1: Buscar todos los packages existentes
        packages_existentes = self.odoo.search_read(
            'stock.quant.package',
            [('name', 'in', package_names)],
            ['name', 'id']
        )
        
        packages_map = {pkg['name']: pkg['id'] for pkg in packages_existentes}
        
        # Identificar los que faltan
        faltantes = [name for name in package_names if name not in packages_map]
        
        # LLAMADA 2: Crear TODOS los faltantes en una sola llamada
        if faltantes:
            nuevos_ids = self.odoo.execute('stock.quant.package', 'create', [
                {'name': name, 'company_id': 1}
                for name in faltantes
            ])
            
            # Si es un solo registro, execute retorna int, sino lista
            if isinstance(nuevos_ids, int):
                nuevos_ids = [nuevos_ids]
            
            # Agregar nuevos al mapa
            for name, nuevo_id in zip(faltantes, nuevos_ids):
                packages_map[name] = nuevo_id
        
        return packages_map
    
    def _buscar_o_crear_lote(self, codigo_lote: str, producto_id: int) -> int:
        """
        Busca un lote por nombre, si no existe lo crea.
        
        Args:
            codigo_lote: Código del lote (ej: PAC0002683 o PAC0002683-C)
            producto_id: ID del producto al que pertenece el lote
            
        Returns:
            ID del lote
        """
        # Buscar lote existente
        lotes = self.odoo.search('stock.lot', [
            ('name', '=', codigo_lote),
            ('product_id', '=', producto_id)
        ])
        
        if lotes:
            return lotes[0]
        
        # Crear nuevo lote
        lote_data = {
            'name': codigo_lote,
            'product_id': producto_id,
            'company_id': 1
        }
        
        lote_id = self.odoo.execute('stock.lot', 'create', lote_data)
        return lote_id
    
    def _crear_componentes(
        self, 
        mo_id: int, 
        mo_name: str,
        productos_totales: Dict,
        config: Dict
    ) -> int:
        """
        Crea los movimientos de componentes (move_raw_ids) para la orden.
        
        Args:
            mo_id: ID de la orden de fabricación
            mo_name: Nombre de la orden
            productos_totales: Dict con {producto_id: {kg, pallets}}
            config: Configuración del túnel
            
        Returns:
            Cantidad de movimientos creados
        """
        print(f"DEBUG _crear_componentes: mo_id={mo_id}, mo_name={mo_name}, productos={len(productos_totales)}")
        movimientos_creados = 0
        ubicacion_virtual = UBICACION_VIRTUAL_CONGELADO_ID if config['sucursal'] == 'RF' else UBICACION_VIRTUAL_PROCESOS_ID
        
        for producto_id, data in productos_totales.items():
            # Crear stock.move principal
            move_data = {
                'name': mo_name,
                'product_id': producto_id,
                'product_uom_qty': data['kg'],
                'product_uom': 12,  # kg
                'location_id': config['ubicacion_origen_id'],
                'location_dest_id': ubicacion_virtual,
                'state': 'draft',
                'raw_material_production_id': mo_id,  # Relación con MO
                'company_id': 1,
                'reference': mo_name
            }
            
            move_id = self.odoo.execute('stock.move', 'create', move_data)
            
            # Crear stock.move.line por cada pallet
            for pallet in data['pallets']:
                # --- NUEVO: Si es pendiente de recepción, NO crear la línea física ---
                if pallet.get('pendiente_recepcion'):
                    print(f"DEBUG: Saltando stock.move.line para pallet PENDIENTE: {pallet['codigo']}")
                    continue

                # Obtener lote_id del quant del pallet (viene de la validación)
                lote_id = pallet.get('lote_id')
                package_id = pallet.get('package_id')  # ID del package origen
                
                move_line_data = {
                    'move_id': move_id,
                    'product_id': producto_id,
                    'qty_done': pallet['kg'],
                    'reserved_uom_qty': pallet['kg'],
                    'product_uom_id': 12,  # kg
                    'location_id': pallet.get('ubicacion_id', config['ubicacion_origen_id']),
                    'location_dest_id': ubicacion_virtual,
                    'state': 'draft',
                    'reference': mo_name,
                    'company_id': 1
                }
                
                # Agregar lote si existe
                if lote_id:
                    move_line_data['lot_id'] = lote_id
                
                # Agregar package de origen si existe
                if package_id:
                    move_line_data['package_id'] = package_id
                
                self.odoo.execute('stock.move.line', 'create', move_line_data)
            
            movimientos_creados += 1
        
        # --- Agregar componente de Electricidad ---
        # Producto: Provisión Electricidad Túnel Estático ($/hr)
        try:
            total_kg = sum(data['kg'] for data in productos_totales.values())
            ete_id = None
            
            # Intento 1: Buscar por código exacto 'ETE'
            ete_products = self.odoo.models.execute_kw(
                self.odoo.db, self.odoo.uid, self.odoo.password,
                'product.product', 'search_read',
                [[('default_code', '=', 'ETE')]],
                {'fields': ['id', 'name', 'uom_id'], 'limit': 1}  # También traer uom_id
            )
            
            ete_uom_id = 12  # Fallback a kg
            if ete_products:
                ete_id = ete_products[0]['id']
                if ete_products[0].get('uom_id'):
                    ete_uom_id = ete_products[0]['uom_id'][0]  # Odoo retorna [id, name]
                print(f"DEBUG: Electricidad encontrada por código ETE: ID={ete_id}, UoM={ete_uom_id}")
            else:
                # Intento 2: Buscar por nombre que contenga 'Electricidad' y 'Túnel'
                ete_products = self.odoo.models.execute_kw(
                    self.odoo.db, self.odoo.uid, self.odoo.password,
                    'product.product', 'search_read',
                    [[('name', 'ilike', 'Electricidad'), ('name', 'ilike', 'Túnel')]],
                    {'fields': ['id', 'name', 'uom_id'], 'limit': 1}
                )
                if ete_products:
                    ete_id = ete_products[0]['id']
                    if ete_products[0].get('uom_id'):
                        ete_uom_id = ete_products[0]['uom_id'][0]
                    print(f"DEBUG: Electricidad encontrada por nombre: ID={ete_id}, UoM={ete_uom_id}")
                else:
                    # Fallback: Usar ID fijo
                    ete_id = PRODUCTO_ELECTRICIDAD_ID
                    print(f"DEBUG: Usando ID fijo de electricidad: {ete_id}")

            # Crear el movimiento de electricidad
            if ete_id:
                elect_move = {
                    'name': mo_name,
                    'product_id': ete_id,
                    'product_uom_qty': total_kg,
                    'product_uom': ete_uom_id,  # Usar UoM del producto
                    'location_id': config['ubicacion_origen_id'],
                    'location_dest_id': ubicacion_virtual,
                    'state': 'draft',
                    'raw_material_production_id': mo_id,
                    'company_id': 1,
                    'reference': mo_name
                }
                elect_move_id = self.odoo.models.execute_kw(
                    self.odoo.db, self.odoo.uid, self.odoo.password,
                    'stock.move', 'create', [elect_move]
                )
                
                # Crear stock.move.line con qty_done para que aparezca en "Hecho"
                if elect_move_id:
                    elect_line = {
                        'move_id': elect_move_id,
                        'product_id': ete_id,
                        'qty_done': total_kg,
                        'reserved_uom_qty': total_kg,
                        'product_uom_id': ete_uom_id,  # Usar UoM del producto
                        'location_id': config['ubicacion_origen_id'],
                        'location_dest_id': ubicacion_virtual,
                        'state': 'draft',
                        'company_id': 1
                    }
                    self.odoo.models.execute_kw(
                        self.odoo.db, self.odoo.uid, self.odoo.password,
                        'stock.move.line', 'create', [elect_line]
                    )
                
                movimientos_creados += 1
                print(f"DEBUG: Electricidad agregada correctamente con qty_done={total_kg}")
        except Exception as e:
            import traceback
            print(f"ERROR Electricidad: {e}")
            print(f"ERROR Traceback: {traceback.format_exc()}")
        
        return movimientos_creados
    
    def _crear_subproductos(
        self,
        mo_id: int,
        mo_name: str,
        productos_totales: Dict,
        config: Dict
    ) -> int:
        """
        Crea los movimientos de subproductos (move_finished_ids) para la orden.
        Genera lotes con sufijo -C y result_package_id.
        
        Args:
            mo_id: ID de la orden de fabricación
            mo_name: Nombre de la orden
            productos_totales: Dict con {producto_id: {kg, pallets}}
            config: Configuración del túnel
            
        Returns:
            Cantidad de movimientos creados
        """
        movimientos_creados = 0
        ubicacion_virtual = UBICACION_VIRTUAL_CONGELADO_ID if config['sucursal'] == 'RF' else UBICACION_VIRTUAL_PROCESOS_ID
        
        for producto_id_input, data in productos_totales.items():
            # Obtener producto congelado (output) - DINÁMICO
            # La lógica es: código 10xxxxxx → 20xxxxxx (cambiar primer dígito de 1 a 2)
            producto_id_output = None
            
            try:
                # Obtener el código del producto de entrada
                prod_input = self.odoo.search_read(
                    'product.product',
                    [('id', '=', producto_id_input)],
                    ['default_code', 'name'],
                    limit=1
                )
                
                if prod_input and prod_input[0].get('default_code'):
                    codigo_input = prod_input[0]['default_code']
                    
                    # Transformar código: primer dígito 1 → 2 para variante congelada
                    if codigo_input and len(codigo_input) >= 1 and codigo_input[0] == '1':
                        codigo_output = '2' + codigo_input[1:]
                        
                        # Buscar producto con el nuevo código
                        prod_output = self.odoo.search_read(
                            'product.product',
                            [('default_code', '=', codigo_output)],
                            ['id', 'name'],
                            limit=1
                        )
                        
                        if prod_output:
                            producto_id_output = prod_output[0]['id']
                            print(f"DEBUG Transformación: {codigo_input} ({prod_input[0]['name']}) → {codigo_output} ({prod_output[0]['name']})")
                        else:
                            print(f"DEBUG: Producto congelado {codigo_output} no encontrado, usando mismo producto")
                    else:
                        print(f"DEBUG: Código {codigo_input} no empieza con 1, usando fallback estático")
                else:
                    print(f"DEBUG: Producto ID {producto_id_input} sin código, usando fallback estático")
                    
            except Exception as e:
                print(f"ERROR buscando producto congelado: {e}")
            
            # Fallback: usar mapeo estático o mismo producto
            if not producto_id_output:
                producto_id_output = PRODUCTOS_TRANSFORMACION.get(producto_id_input, producto_id_input)
            
            # Crear stock.move principal
            move_data = {
                'name': mo_name,
                'product_id': producto_id_output,
                'product_uom_qty': data['kg'],
                'product_uom': 12,  # kg
                'location_id': ubicacion_virtual,
                'location_dest_id': config['ubicacion_destino_id'],
                'state': 'draft',
                'production_id': mo_id,  # Relación con MO (finished)
                'company_id': 1,
                'reference': mo_name
            }
            
            move_id = self.odoo.execute('stock.move', 'create', move_data)
            
            # ✅ OPTIMIZADO: Preparar TODOS los lotes y packages de una vez
            lotes_data = []
            package_names = []
            
            for pallet in data['pallets']:
                # LOTE: Usar nombre del lote original + sufijo -C
                # Prioridad: lote_nombre (backend) -> lot_name (frontend) -> codigo (fallback)
                lote_origen = pallet.get('lote_nombre') or pallet.get('lot_name') or pallet.get('codigo')
                lote_output_name = f"{lote_origen}-C"
                
                # DEBUG: Log detallado del lote
                print(f"DEBUG Subprod: pallet={pallet.get('codigo')}, lote_nombre={pallet.get('lote_nombre')}, lot_name={pallet.get('lot_name')}, lote_origen={lote_origen}, lote_output={lote_output_name}")
                
                lotes_data.append({
                    'codigo': lote_output_name,
                    'producto_id': producto_id_output
                })
                
                # PACKAGE: Extraer solo el número y generar nombre correcto
                codigo_pallet = pallet['codigo']
                # Extraer solo el número (quitar PACK o PAC)
                if codigo_pallet.startswith('PACK'):
                    numero_pallet = codigo_pallet[4:]  # Quitar 'PACK'
                elif codigo_pallet.startswith('PAC'):
                    numero_pallet = codigo_pallet[3:]  # Quitar 'PAC'
                else:
                    numero_pallet = codigo_pallet
                package_name = f"PACK{numero_pallet}-C"
                
                package_names.append(package_name)
            
            # ✅ Crear TODOS los lotes en batch (2 llamadas máximo)
            lotes_map = self._buscar_o_crear_lotes_batch(lotes_data)
            
            # ✅ Crear TODOS los packages en batch (2 llamadas máximo)
            packages_map = self._buscar_o_crear_packages_batch(package_names)
            
            # Ahora crear los move.lines
            for idx, pallet in enumerate(data['pallets']):
                # --- NUEVO: Si es pendiente de recepción, NO crear la línea física de salida ---
                if pallet.get('pendiente_recepcion'):
                    print(f"DEBUG: Saltando stock.move.line (subproducto) para pallet PENDIENTE: {pallet['codigo']}")
                    continue

                # LOTE: Usar nombre del lote original + sufijo -C
                # Prioridad: lote_nombre (backend) -> lot_name (frontend) -> codigo (fallback)
                lote_origen = pallet.get('lote_nombre') or pallet.get('lot_name') or pallet.get('codigo')
                lote_output_name = f"{lote_origen}-C"
                
                # PACKAGE: Extraer solo el número y generar nombre correcto
                codigo_pallet = pallet['codigo']
                if codigo_pallet.startswith('PACK'):
                    numero_pallet = codigo_pallet[4:]  # Quitar 'PACK'
                elif codigo_pallet.startswith('PAC'):
                    numero_pallet = codigo_pallet[3:]  # Quitar 'PAC'
                else:
                    numero_pallet = codigo_pallet
                package_name = f"PACK{numero_pallet}-C"
                
                # Obtener IDs del mapa (ya creados en batch)
                lote_id_output = lotes_map.get(lote_output_name)
                package_id = packages_map.get(package_name)
                
                move_line_data = {
                    'move_id': move_id,
                    'product_id': producto_id_output,
                    'lot_id': lote_id_output,
                    'result_package_id': package_id,
                    'qty_done': pallet['kg'],
                    'reserved_uom_qty': 0.0,  # Los subproductos no tienen reserva
                    'product_uom_id': 12,  # kg
                    'location_id': ubicacion_virtual,
                    'location_dest_id': config['ubicacion_destino_id'],
                    'state': 'draft',
                    'reference': mo_name,
                    'company_id': 1
                }
                
                self.odoo.execute('stock.move.line', 'create', move_line_data)
            
            movimientos_creados += 1
        
        return movimientos_creados
    


def get_tuneles_service(odoo: OdooClient) -> TunelesService:
    """Factory function para obtener el servicio de túneles."""
    return TunelesService(odoo)

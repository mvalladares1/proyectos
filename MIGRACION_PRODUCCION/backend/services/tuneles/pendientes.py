"""
Gestión de pendientes para túneles.
Maneja verificación, detalle y actualización de pallets pendientes en órdenes de fabricación.
"""
import json
from typing import Dict, List
from datetime import datetime
from shared.odoo_client import OdooClient


def verificar_pendientes(odoo: OdooClient, mo_id: int) -> Dict:
    """
    Verifica el estado de las recepciones pendientes de una MO.
    
    Args:
        odoo: Cliente Odoo
        mo_id: ID de la orden de fabricación
        
    Returns:
        Dict con: mo_name, has_pending, pickings, all_ready
    """
    try:
        mo = odoo.search_read(
            'mrp.production',
            [('id', '=', mo_id)],
            ['name', 'x_studio_pending_receptions', 'state'],
            limit=1
        )
        
        if not mo:
            return {'success': False, 'error': 'MO no encontrada'}
        
        mo = mo[0]
        pending_json = mo.get('x_studio_pending_receptions')
        
        if not pending_json:
            return {
                'success': True,
                'mo_name': mo['name'],
                'has_pending': False,
                'all_ready': True,
                'pickings': []
            }
        
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
        
        if not pending_data.get('pending', True):
            return {
                'success': True,
                'mo_name': mo['name'],
                'has_pending': False,
                'all_ready': True,
                'pickings': []
            }
        
        picking_ids = pending_data.get('picking_ids', [])
        
        pickings = odoo.search_read(
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


def obtener_detalle_pendientes(odoo: OdooClient, mo_id: int) -> Dict:
    """
    Obtiene el detalle de los pallets pendientes de una MO.
    
    Args:
        odoo: Cliente Odoo
        mo_id: ID de la orden de fabricación
        
    Returns:
        Dict con: success, mo_name, pallets (lista con estado de cada uno)
    """
    try:
        mo_data = odoo.read('mrp.production', [mo_id], 
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
        
        # Obtener info de pickings
        picking_names = {}
        if picking_ids:
            pickings = odoo.search_read(
                'stock.picking',
                [('id', 'in', picking_ids)],
                ['id', 'name', 'state']
            )
            picking_names = {p['id']: {'name': p['name'], 'state': p['state']} for p in pickings}
        
        # Obtener componentes existentes
        move_raw_ids = mo_data.get('move_raw_ids', [])
        componentes_existentes = set()
        if move_raw_ids:
            moves = odoo.search_read(
                'stock.move.line',
                [
                    ('move_id', 'in', move_raw_ids),
                    ('package_id', '!=', False),
                    ('qty_done', '>', 0)
                ],
                ['package_id']
            )
            for m in moves:
                if m.get('package_id'):
                    componentes_existentes.add(m['package_id'][1])
        
        # Verificar cada pallet
        resultado_pallets = []
        json_modificado = False
        
        for p in pallets_info:
            codigo = p.get('codigo', '')
            kg = p.get('kg', 0)
            producto_id = p.get('producto_id')
            picking_id = p.get('picking_id')
            estado_anterior = p.get('estado_ultima_revision', 'pendiente')
            timestamp_agregado = p.get('timestamp_agregado')
            
            ya_agregado = timestamp_agregado is not None
            
            # Verificar stock disponible
            quants = odoo.search_read(
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
                estado_actual = 'agregado'
                estado_label = '✅ Ya agregado'
            elif tiene_stock:
                estado_actual = 'disponible'
                estado_label = '🟢 Disponible'
            else:
                estado_actual = 'pendiente'
                estado_label = '🟠 Pendiente'
            
            cambio_detectado = (estado_actual != estado_anterior)
            nuevo_disponible = cambio_detectado and estado_actual == 'disponible'
            
            if cambio_detectado:
                p['estado_ultima_revision'] = estado_actual
                p['timestamp_ultima_revision'] = datetime.now().isoformat()
                if nuevo_disponible:
                    p['fecha_disponible'] = datetime.now().isoformat()
                json_modificado = True
            
            resultado_pallets.append({
                'codigo': codigo,
                'kg': kg,
                'producto_id': producto_id,
                'picking_id': picking_id,
                'picking_name': picking_name,
                'picking_state': picking_state,
                'estado': estado_actual,
                'estado_anterior': estado_anterior,
                'estado_label': estado_label,
                'cambio_detectado': cambio_detectado,
                'nuevo_disponible': nuevo_disponible,
                'tiene_stock': tiene_stock,
                'ya_agregado': ya_agregado,
                'quant_info': quants[0] if quants else None
            })
        
        # Contar estados
        total = len(resultado_pallets)
        agregados = sum(1 for p in resultado_pallets if p['estado'] == 'agregado')
        disponibles = sum(1 for p in resultado_pallets if p['estado'] == 'disponible')
        pendientes = sum(1 for p in resultado_pallets if p['estado'] == 'pendiente')
        
        # Ordenar pallets
        resultado_pallets_ordenados = sorted(resultado_pallets, 
            key=lambda x: (0 if x['estado'] == 'agregado' else 1 if x['estado'] == 'disponible' else 2))
        
        return {
            'success': True,
            'mo_id': mo_id,
            'mo_name': mo_name,
            'tiene_pendientes': True,
            'pallets': resultado_pallets_ordenados,
            'resumen': {
                'total': total,
                'agregados': agregados,
                'disponibles': disponibles,
                'pendientes': pendientes
            },
            'json_modificado': json_modificado
        }
        
    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def completar_pendientes(odoo: OdooClient, mo_id: int) -> Dict:
    """
    Completa los pendientes solo si TODOS los pallets están agregados.
    
    Args:
        odoo: Cliente Odoo
        mo_id: ID de la orden de fabricación
        
    Returns:
        Dict con: success, mensaje o error
    """
    try:
        detalle = obtener_detalle_pendientes(odoo, mo_id)
        if not detalle.get('success'):
            return detalle
        
        # Validación estricta
        pallets_sin_agregar = [
            p for p in detalle.get('pallets', []) 
            if p['estado'] in ['pendiente', 'disponible']
        ]
        
        if pallets_sin_agregar:
            return {
                'success': False,
                'error': f"Aún quedan {len(pallets_sin_agregar)} pallet(s) sin agregar",
                'pendientes_restantes': [p['codigo'] for p in pallets_sin_agregar]
            }
        
        # Leer y actualizar JSON
        mo_data = odoo.read('mrp.production', [mo_id], ['x_studio_pending_receptions', 'name'])[0]
        pending_json = mo_data.get('x_studio_pending_receptions')
        pending_data = json.loads(pending_json) if isinstance(pending_json, str) else pending_json
        
        cleaned_data = {
            'pending': False,
            'completed_at': datetime.now().isoformat(),
            'completed_by': 'automatizaciones_validacion',
            'pallets_count': len(detalle.get('pallets', [])),
            'created_at': pending_data.get('created_at'),
            'historial_revisiones': [{
                'timestamp': datetime.now().isoformat(),
                'accion': 'completar_pendientes',
                'total_pallets': len(detalle.get('pallets', [])),
                'mensaje': 'Todos los pallets agregados - JSON optimizado'
            }]
        }
        
        odoo.execute('mrp.production', 'write', [mo_id], {
            'x_studio_pending_receptions': json.dumps(cleaned_data)
        })
        
        return {
            'success': True,
            'mo_id': mo_id,
            'mo_name': mo_data['name'],
            'mensaje': f"Completados {len(detalle.get('pallets', []))} pendientes"
        }
        
    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def reset_estado_pendientes(odoo: OdooClient, mo_id: int) -> Dict:
    """
    Resetea el estado de todos los pallets pendientes para re-validación.
    
    Args:
        odoo: Cliente Odoo
        mo_id: ID de la orden de fabricación
        
    Returns:
        Dict con: success, mensaje
    """
    try:
        mo_data = odoo.read('mrp.production', [mo_id], ['x_studio_pending_receptions', 'name'])[0]
        pending_json = mo_data.get('x_studio_pending_receptions')
        
        if not pending_json:
            return {
                'success': False,
                'error': 'Esta orden no tiene JSON de pendientes'
            }
        
        pending_data = json.loads(pending_json) if isinstance(pending_json, str) else pending_json
        
        pallets_reseteados = 0
        for pallet in pending_data.get('pallets', []):
            if 'timestamp_agregado' in pallet:
                del pallet['timestamp_agregado']
                pallets_reseteados += 1
            pallet['estado_ultima_revision'] = 'pendiente'
            pallet['timestamp_ultima_revision'] = datetime.now().isoformat()
        
        if 'historial_revisiones' not in pending_data:
            pending_data['historial_revisiones'] = []
        
        pending_data['historial_revisiones'].append({
            'timestamp': datetime.now().isoformat(),
            'accion': 'reset_estado',
            'pallets_reseteados': pallets_reseteados,
            'mensaje': 'Reset manual para re-validación'
        })
        
        odoo.execute('mrp.production', 'write', [mo_id], {
            'x_studio_pending_receptions': json.dumps(pending_data)
        })
        
        return {
            'success': True,
            'mo_id': mo_id,
            'mo_name': mo_data['name'],
            'pallets_reseteados': pallets_reseteados,
            'mensaje': f'Estado reseteado: {pallets_reseteados} pallet(s)'
        }
        
    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

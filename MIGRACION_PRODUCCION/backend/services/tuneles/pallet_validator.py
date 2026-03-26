"""
Validación de pallets para túneles.
Gestiona verificación de disponibilidad y recepción de pallets.
"""
import os
from typing import List, Dict
from shared.odoo_client import OdooClient


def validar_pallets_batch(odoo: OdooClient, codigos_pallets: List[str], 
                          buscar_ubicacion: bool = False) -> List[Dict]:
    """
    Valida múltiples pallets buscando por PACKAGE (PACK000XXXX) en batch.
    
    Args:
        odoo: Cliente Odoo
        codigos_pallets: Lista de códigos de PACKAGES (ej: PACK0010337)
        buscar_ubicacion: Si True, busca la ubicación real del pallet
        
    Returns:
        Lista de dicts con validación de cada pallet
    """
    if not codigos_pallets:
        return []
    
    resultados = []
    
    # LLAMADA 1: Buscar TODOS los packages en una sola llamada
    packages = odoo.search_read(
        'stock.quant.package',
        [('name', 'in', codigos_pallets)],
        ['id', 'name']
    )
    
    # FIX: Manejar packages duplicados - puede haber múltiples packages con el mismo nombre
    # Necesitamos verificar cuál tiene stock antes de decidir
    packages_by_name = {}
    for pkg in packages:
        name = pkg['name']
        if name not in packages_by_name:
            packages_by_name[name] = []
        packages_by_name[name].append(pkg)
    
    # Identificar pallets no encontrados
    codigos_encontrados = set(packages_by_name.keys())
    codigos_no_encontrados = set(codigos_pallets) - codigos_encontrados
    
    # Buscar recepciones pendientes para no encontrados
    reception_info_map = _buscar_recepciones_pendientes(
        odoo, codigos_no_encontrados, {}
    )
    
    # Agregar resultados de no encontrados
    for codigo in codigos_no_encontrados:
        reception_info = reception_info_map.get(codigo)
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
                'existe': False,
                'codigo': codigo,
                'error': f'Paquete {codigo} no encontrado en Odoo',
                'reception_info': None
            })
    
    if not packages:
        return resultados
    
    # LLAMADA 2: Buscar TODOS los quants asociados a esos packages
    package_ids = [pkg['id'] for pkg in packages]
    quants = odoo.search_read(
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
    
    # FIX: Para cada código, seleccionar el package correcto (el que tiene stock)
    packages_seleccionados = {}
    for codigo in codigos_encontrados:
        pkg_list = packages_by_name[codigo]
        
        # Si hay múltiples packages, elegir el que tiene stock
        pkg_con_stock = None
        for pkg in pkg_list:
            if quants_por_package.get(pkg['id']):
                pkg_con_stock = pkg
                break
        
        # Si ninguno tiene stock, usar el primero
        packages_seleccionados[codigo] = pkg_con_stock if pkg_con_stock else pkg_list[0]
    
    # Buscar recepciones para packages sin stock
    packages_sin_stock = [
        packages_seleccionados[codigo] for codigo in codigos_encontrados 
        if not quants_por_package.get(packages_seleccionados[codigo]['id'])
    ]
    
    reception_info_sin_stock = _buscar_recepciones_sin_stock(odoo, packages_sin_stock)
    
    # Procesar cada package encontrado
    for codigo in codigos_encontrados:
        package = packages_seleccionados[codigo]
        pkg_quants = quants_por_package.get(package['id'], [])
        
        if not pkg_quants:
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


def _buscar_recepciones_pendientes(odoo: OdooClient, codigos_no_encontrados: set, 
                                   packages_map: Dict) -> Dict:
    """Busca recepciones pendientes para packages no encontrados."""
    if not codigos_no_encontrados:
        return {}
    
    reception_info_map = {}
    
    packages_pendientes = odoo.search_read(
        'stock.quant.package',
        [('name', 'in', list(codigos_no_encontrados))],
        ['id', 'name']
    )
    
    if not packages_pendientes:
        return {}
    
    pkg_ids_pendientes = [p['id'] for p in packages_pendientes]
    pkg_name_to_id = {p['name']: p['id'] for p in packages_pendientes}
    
    # Buscar move_lines
    move_lines_batch = odoo.search_read(
        'stock.move.line',
        [
            '|',
            ('result_package_id', 'in', pkg_ids_pendientes),
            ('package_id', 'in', pkg_ids_pendientes),
            ('picking_id', '!=', False)
        ],
        ['picking_id', 'product_id', 'qty_done', 'reserved_uom_qty', 
         'result_package_id', 'package_id', 'lot_id'],
        limit=100,
        order='id desc'
    )
    
    # Obtener picking_ids únicos
    picking_ids_batch = list(set([
        ml['picking_id'][0] for ml in move_lines_batch if ml.get('picking_id')
    ]))
    
    # Estado de pickings
    pickings_batch = {}
    if picking_ids_batch:
        pickings_data = odoo.search_read(
            'stock.picking',
            [('id', 'in', picking_ids_batch)],
            ['id', 'state'],
            limit=100
        )
        pickings_batch = {p['id']: p['state'] for p in pickings_data}
    
    # Procesar move_lines
    for ml in move_lines_batch:
        pkg_id = None
        if ml.get('result_package_id'):
            pkg_id = ml['result_package_id'][0]
        elif ml.get('package_id'):
            pkg_id = ml['package_id'][0]
        
        if not pkg_id:
            continue
        
        pkg_code = next((name for name, pid in pkg_name_to_id.items() if pid == pkg_id), None)
        if not pkg_code:
            continue
        
        picking_id = ml['picking_id'][0]
        picking_name = ml['picking_id'][1]
        picking_state = pickings_batch.get(picking_id)
        
        if picking_state and picking_state not in ['done', 'cancel']:
            if pkg_code not in reception_info_map:
                base_url = os.environ.get('ODOO_URL', 'https://riofuturo.odoo.com')
                odoo_url = f"{base_url}/web#id={picking_id}&model=stock.picking&view_type=form"
                kg = ml['qty_done'] if ml['qty_done'] and ml['qty_done'] > 0 else ml.get('reserved_uom_qty', 0)
                
                lot_id = ml['lot_id'][0] if ml.get('lot_id') else None
                lot_name = ml['lot_id'][1] if ml.get('lot_id') else None

                reception_info_map[pkg_code] = {
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
    
    return reception_info_map


def _buscar_recepciones_sin_stock(odoo: OdooClient, packages_sin_stock: List) -> Dict:
    """Busca recepciones para packages que existen pero sin stock."""
    if not packages_sin_stock:
        return {}
    
    reception_info_sin_stock = {}
    
    pkg_ids_sin_stock = [p['id'] for p in packages_sin_stock]
    pkg_id_to_name = {p['id']: p['name'] for p in packages_sin_stock}
    
    move_lines_sin_stock = odoo.search_read(
        'stock.move.line',
        [
            ('result_package_id', 'in', pkg_ids_sin_stock),
            ('picking_id', '!=', False)
        ],
        ['picking_id', 'product_id', 'qty_done', 'reserved_uom_qty', 'lot_id', 'result_package_id'],
        limit=100,
        order='id desc'
    )
    
    picking_ids_sin_stock = list(set([
        ml['picking_id'][0] for ml in move_lines_sin_stock if ml.get('picking_id')
    ]))
    
    pickings_sin_stock = {}
    if picking_ids_sin_stock:
        pickings_data = odoo.search_read(
            'stock.picking',
            [('id', 'in', picking_ids_sin_stock)],
            ['id', 'state']
        )
        pickings_sin_stock = {p['id']: p['state'] for p in pickings_data}
    
    for ml in move_lines_sin_stock:
        pkg_id = ml['result_package_id'][0] if ml.get('result_package_id') else None
        if not pkg_id or pkg_id not in pkg_id_to_name:
            continue
        
        codigo = pkg_id_to_name[pkg_id]
        if codigo in reception_info_sin_stock:
            continue
        
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
    
    return reception_info_sin_stock


def check_pallets_duplicados(odoo: OdooClient, codigos_pallets: List[str]) -> List[Dict]:
    """
    Verifica si los pallets ya están en uso en otras órdenes activas.
    
    Args:
        odoo: Cliente Odoo
        codigos_pallets: Lista de códigos de pallets
        
    Returns:
        Lista de advertencias
    """
    if not codigos_pallets:
        return []
    
    advertencias = []
    
    # Buscar los packages
    packages = odoo.search_read(
        'stock.quant.package',
        [('name', 'in', codigos_pallets)],
        ['id', 'name']
    )
    
    if not packages:
        return []
    
    package_ids = [p['id'] for p in packages]
    package_names = {p['id']: p['name'] for p in packages}
    
    # Buscar move_lines que usen estos packages en órdenes activas
    move_lines = odoo.search_read(
        'stock.move.line',
        [
            ('package_id', 'in', package_ids),
            ('reference', 'like', 'MO%'),
            ('state', 'not in', ['done', 'cancel'])
        ],
        ['package_id', 'reference', 'move_id'],
        limit=200
    )
    
    # Agrupar por package
    for ml in move_lines:
        pkg_id = ml['package_id'][0]
        pkg_name = package_names.get(pkg_id)
        if pkg_name:
            advertencias.append({
                'codigo': pkg_name,
                'referencia': ml.get('reference', 'N/A'),
                'mensaje': f'Pallet {pkg_name} ya está en uso en {ml.get("reference", "otra orden")}'
            })
    
    return advertencias

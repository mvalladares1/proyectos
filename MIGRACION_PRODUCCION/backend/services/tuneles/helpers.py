"""
Funciones auxiliares para gestión de lotes y packages.
"""
from typing import List, Dict
from shared.odoo_client import OdooClient


def buscar_o_crear_lotes_batch(odoo: OdooClient, lotes_data: List[Dict]) -> Dict[str, int]:
    """
    Busca o crea múltiples lotes en batch (OPTIMIZADO).
    
    Args:
        odoo: Cliente Odoo
        lotes_data: Lista de dicts con {'codigo': str, 'producto_id': int}
        
    Returns:
        Dict mapeando código_lote -> lote_id
    """
    if not lotes_data:
        return {}
    
    # Extraer códigos únicos
    codigos = list(set([lote['codigo'] for lote in lotes_data]))
    
    # LLAMADA 1: Buscar TODOS los lotes existentes
    lotes_existentes = odoo.search_read(
        'stock.lot',
        [('name', 'in', codigos)],
        ['name', 'id', 'product_id']
    )
    
    # Crear mapa de existentes
    lotes_map = {}
    for lote in lotes_existentes:
        lotes_map[lote['name']] = lote['id']
    
    # Identificar los que faltan
    faltantes = []
    for lote_data in lotes_data:
        if lote_data['codigo'] not in lotes_map:
            faltantes.append(lote_data)
    
    # LLAMADA 2: Crear TODOS los faltantes en una sola llamada
    if faltantes:
        nuevos_ids = odoo.execute('stock.lot', 'create', [
            {
                'name': lote['codigo'],
                'product_id': lote['producto_id'],
                'company_id': 1
            }
            for lote in faltantes
        ])
        
        # Si es un solo registro, execute retorna int, sino lista
        if isinstance(nuevos_ids, int):
            nuevos_ids = [nuevos_ids]
        
        # Agregar nuevos al mapa
        for lote_data, nuevo_id in zip(faltantes, nuevos_ids):
            lotes_map[lote_data['codigo']] = nuevo_id
    
    return lotes_map


def buscar_o_crear_packages_batch(odoo: OdooClient, package_names: List[str]) -> Dict[str, int]:
    """
    Busca o crea múltiples packages en batch (OPTIMIZADO).
    
    Args:
        odoo: Cliente Odoo
        package_names: Lista de nombres de packages
        
    Returns:
        Dict mapeando nombre_package -> package_id
    """
    if not package_names:
        return {}
    
    # Eliminar duplicados
    package_names = list(set(package_names))
    
    # LLAMADA 1: Buscar TODOS los packages existentes
    packages_existentes = odoo.search_read(
        'stock.quant.package',
        [('name', 'in', package_names)],
        ['name', 'id']
    )
    
    packages_map = {pkg['name']: pkg['id'] for pkg in packages_existentes}
    
    # Identificar los que faltan
    faltantes = [name for name in package_names if name not in packages_map]
    
    # LLAMADA 2: Crear TODOS los faltantes en una sola llamada
    if faltantes:
        nuevos_ids = odoo.execute('stock.quant.package', 'create', [
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


def buscar_o_crear_lote(odoo: OdooClient, codigo_lote: str, producto_id: int) -> int:
    """
    Busca un lote por nombre, si no existe lo crea.
    
    Args:
        odoo: Cliente Odoo
        codigo_lote: Código del lote (ej: PAC0002683 o PAC0002683-C)
        producto_id: ID del producto al que pertenece el lote
        
    Returns:
        ID del lote
    """
    # Buscar lote existente
    lotes = odoo.search('stock.lot', [
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
    
    lote_id = odoo.execute('stock.lot', 'create', lote_data)
    return lote_id

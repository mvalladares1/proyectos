"""
Funciones auxiliares para clasificación de productos y salas.
"""
from typing import Tuple
from .constants import (
    EXCLUDED_CATEGORIES, 
    SALAS_PROCESO, 
    FRUIT_MAPPING,
    OPERATIONAL_INDICATORS,
    PURE_PACKAGING
)


def is_operational_cost(product_name: str) -> bool:
    """
    Identifica costos operacionales (electricidad, servicios).
    
    Args:
        product_name: Nombre del producto
        
    Returns:
        True si es costo operacional
    """
    if not product_name:
        return False
    
    name_lower = product_name.lower()
    return any(ind in name_lower for ind in OPERATIONAL_INDICATORS)


def is_excluded_consumo(product_name: str, category_name: str = '') -> bool:
    """
    Verifica si un producto debe excluirse del consumo MP.
    
    Args:
        product_name: Nombre del producto
        category_name: Nombre de la categoría
        
    Returns:
        True si debe excluirse
    """
    if not product_name:
        return True
    
    name_lower = product_name.lower()
    cat_lower = (category_name or '').lower()
    
    # Productos con código [3xxxxx] o [1xxxxx] son productos de proceso
    if product_name.startswith('[3') or product_name.startswith('[1'):
        return False
    
    if is_operational_cost(product_name):
        return True
    
    if any(exc in cat_lower for exc in EXCLUDED_CATEGORIES):
        return True
    
    if any(exc in name_lower for exc in PURE_PACKAGING):
        return True
    
    if name_lower.startswith('bolsa') or name_lower.startswith('caja'):
        return True
    
    return False


def extract_fruit_type(product_name: str) -> str:
    """
    Extrae el tipo de fruta del nombre del producto.
    
    Args:
        product_name: Nombre del producto
        
    Returns:
        Nombre de la fruta o 'Otro'
    """
    if not product_name:
        return 'Otro'
    
    name_lower = product_name.lower()
    
    for key, value in FRUIT_MAPPING.items():
        if key in name_lower:
            return value
    
    return 'Otro'


def extract_handling(product_name: str) -> str:
    """
    Extrae el manejo (orgánico/convencional) del nombre.
    
    Args:
        product_name: Nombre del producto
        
    Returns:
        'Orgánico', 'Convencional' o 'Otro'
    """
    if not product_name:
        return 'Otro'
    
    name_lower = product_name.lower()
    
    if 'orgánico' in name_lower or 'organico' in name_lower or 'org.' in name_lower:
        return 'Orgánico'
    elif 'convencional' in name_lower or 'conv.' in name_lower:
        return 'Convencional'
    
    return 'Otro'


def classify_sala(sala_name: str, product_name: str = '') -> Tuple[str, str]:
    """
    Clasifica una sala o producto como PROCESO o CONGELADO.
    
    Args:
        sala_name: Nombre de la sala
        product_name: Nombre del producto (opcional)
        
    Returns:
        Tuple (tipo, nombre_normalizado)
    """
    if not sala_name:
        sala_name = ''
    
    sala_lower = sala_name.lower().strip()
    product_lower = (product_name or '').lower()
    
    # Salas de proceso conocidas
    if any(s in sala_lower for s in SALAS_PROCESO):
        return ('PROCESO', sala_name)
    
    # Congelado por keywords
    if 'congel' in sala_lower or 'tunel' in sala_lower or 'túnel' in sala_lower:
        return ('CONGELADO', sala_name)
    
    # IQF es proceso
    if 'iqf' in sala_lower or 'iqf' in product_lower:
        return ('PROCESO', sala_name)
    
    # Fallback: si tiene número de sala, es proceso
    if 'sala' in sala_lower and any(char.isdigit() for char in sala_lower):
        return ('PROCESO', sala_name)
    
    return ('CONGELADO', sala_name)

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


def is_excluded_consumo(product_name: str, category_name: str = '', especie: str = None, manejo: str = None) -> bool:
    """
    Verifica si un producto debe excluirse del consumo MP.
    
    Lógica simple:
    - Si tiene especie Y manejo configurados → ES FRUTA → INCLUIR (return False)
    - Si NO tiene especie O NO tiene manejo → ES INSUMO → EXCLUIR (return True)
    
    Args:
        product_name: Nombre del producto
        category_name: Nombre de la categoría
        especie: Especie del producto (de x_studio_sub_categora)
        manejo: Manejo del producto (de x_studio_categora_tipo_de_manejo)
        
    Returns:
        True si debe excluirse (es insumo), False si debe incluirse (es fruta)
    """
    if not product_name:
        return True
    
    # Si tiene especie Y manejo válidos → es fruta → NO excluir
    if especie and especie != 'Otro' and especie != 'SIN ESPECIE' and \
       manejo and manejo != 'Otro' and manejo != 'SIN MANEJO':
        return False
    
    # Si no tiene especie o manejo → es insumo → EXCLUIR
    return True


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
    
    # PRIORIDAD 1: Túnel Continuo detectado por PRODUCTO (no por sala)
    # Ej: "[1.4] PROCESO CONGELADO TÚNEL CONTINUO"
    if 'tunel continuo' in product_lower or 'túnel continuo' in product_lower:
        return ('CONGELADO', 'Túnel Continuo')
    
    # PRIORIDAD 2: Congelado explícito por sala - túneles estáticos
    if 'tunel' in sala_lower or 'túnel' in sala_lower:
        if 'estatico' in sala_lower or 'estático' in sala_lower:
            return ('CONGELADO', sala_name)
        # Otros túneles sin especificar
        return ('CONGELADO', sala_name)
    
    # PRIORIDAD 3: Cámaras de congelado
    if 'congel' in sala_lower or 'camara' in sala_lower or 'cámara' in sala_lower:
        return ('CONGELADO', sala_name)
    
    # PRIORIDAD 4: Salas de proceso conocidas (incluye vilkun y sin sala)
    if any(s in sala_lower for s in SALAS_PROCESO):
        return ('PROCESO', sala_name)
    
    # PRIORIDAD 5: IQF es proceso
    if 'iqf' in sala_lower or 'iqf' in product_lower:
        return ('PROCESO', sala_name)
    
    # PRIORIDAD 6: Si tiene número de sala, es proceso
    if 'sala' in sala_lower and any(char.isdigit() for char in sala_lower):
        return ('PROCESO', sala_name)
    
    # FALLBACK: Default es PROCESO para salas no identificadas
    return ('PROCESO', sala_name if sala_name else 'Sin Sala')

"""
Utilidades compartidas para los servicios del backend.
Centraliza funciones comunes para evitar duplicación de código.
"""
from typing import Dict, List, Any, Union


def clean_record(record: Dict) -> Dict:
    """
    Limpia un registro de Odoo convirtiendo tuplas/listas en diccionarios.
    
    Convierte:
    - Relaciones many2one: (id, nombre) -> {"id": id, "name": nombre}
      IMPORTANTE: Solo si el segundo elemento es string (nombre), no int
    - Relaciones many2many/one2many: [id1, id2, ...] -> se mantienen como lista
    
    Args:
        record: Diccionario con datos de Odoo
        
    Returns:
        Diccionario con datos limpios
    """
    if not record:
        return {}
    
    cleaned = {}
    for key, value in record.items():
        # Many2one: exactamente 2 elementos, primero int (ID), segundo string (nombre)
        if isinstance(value, (list, tuple)) and len(value) == 2 and isinstance(value[0], int) and isinstance(value[1], str):
            cleaned[key] = {"id": value[0], "name": value[1]}
        elif isinstance(value, list) and value and all(isinstance(x, int) for x in value):
            # Es una relación many2many o one2many: [id1, id2, ...] - mantener como lista
            cleaned[key] = value
        else:
            cleaned[key] = value
    return cleaned


def clean_records(records: List[Dict]) -> List[Dict]:
    """Limpia una lista de registros de Odoo."""
    return [clean_record(r) for r in records]


def get_name_from_relation(value: Any, default: str = "N/A") -> str:
    """
    Extrae el nombre de una relación many2one de Odoo.
    
    Maneja tanto el formato crudo (tuple/list) como el limpio (dict).
    
    Args:
        value: Valor de la relación (puede ser tuple, list, dict o None)
        default: Valor por defecto si no se puede extraer
        
    Returns:
        Nombre de la relación o el valor por defecto
    """
    if not value:
        return default
    if isinstance(value, dict):
        return value.get("name", default)
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return value[1]
    return default


def get_id_from_relation(value: Any, default: int = None) -> int:
    """
    Extrae el ID de una relación many2one de Odoo.
    
    Args:
        value: Valor de la relación
        default: Valor por defecto si no se puede extraer
        
    Returns:
        ID de la relación o el valor por defecto
    """
    if not value:
        return default
    if isinstance(value, dict):
        return value.get("id", default)
    if isinstance(value, (list, tuple)) and len(value) >= 1:
        return value[0]
    return default


# Mapeo de estados de fabricación a texto legible
MRP_STATE_DISPLAY = {
    "draft": "Borrador",
    "confirmed": "Confirmada",
    "planned": "Planificada",
    "progress": "En Progreso",
    "to_close": "Por Cerrar",
    "done": "Finalizada",
    "cancel": "Cancelada"
}


def get_state_display(state: str) -> str:
    """Convierte el estado técnico de MRP a texto legible."""
    return MRP_STATE_DISPLAY.get(state, state)

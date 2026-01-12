"""
Constantes para el módulo de Containers.
"""

# Mapeo de estados técnicos a texto legible
STATE_MAP = {
    "draft": "Borrador",
    "confirmed": "Confirmada",
    "planned": "Planificada",
    "progress": "En Progreso",
    "to_close": "Por Cerrar",
    "done": "Finalizada",
    "cancel": "Cancelada"
}


def get_state_display(state: str) -> str:
    """Convierte el estado técnico a texto legible."""
    return STATE_MAP.get(state, state)

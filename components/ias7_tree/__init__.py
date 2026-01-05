"""
IAS7 Tree - Custom Streamlit Component for Estado de Flujo de Efectivo (NIIF IAS 7)

Usage:
    from components.ias7_tree import ias7_tree
    
    ias7_tree(
        actividades=[...],
        modo="consolidado",
        efectivo_inicial=1000000,
        efectivo_final=1200000,
        theme="dark"
    )
"""
import os
import streamlit.components.v1 as components

# Determine if we're in development or production mode
_RELEASE = os.getenv("IAS7_RELEASE", "false").lower() == "true"

# Get the component path
_component_path = os.path.join(os.path.dirname(__file__), "frontend", "build")

if _RELEASE or os.path.exists(_component_path):
    # Production: use built files
    _component_func = components.declare_component(
        "ias7_tree",
        path=_component_path
    )
else:
    # Development: use dev server
    _component_func = components.declare_component(
        "ias7_tree",
        url="http://localhost:3001"
    )


def ias7_tree(
    actividades: list,
    modo: str = "consolidado",
    efectivo_inicial: float = 0,
    efectivo_final: float = 0,
    variacion_neta: float = 0,
    cuentas_sin_clasificar: int = 0,
    theme: str = "dark",
    height: int = None,
    key: str = None
):
    """
    Renderiza el Estado de Flujo de Efectivo (NIIF IAS 7 - Método Directo).
    
    Args:
        actividades: Lista de actividades con estructura IAS 7
            [
                {
                    "key": "OPERACION",
                    "nombre": "1. Flujos de efectivo...",
                    "subtotal": 1000000,
                    "subtotal_nombre": "Flujos de efectivo netos...",
                    "conceptos": [...],
                    "color": "#2ecc71"
                },
                ...
            ]
        modo: "real" | "proyectado" | "consolidado"
        efectivo_inicial: Efectivo al inicio del período
        efectivo_final: Efectivo al final del período
        variacion_neta: Variación neta del efectivo
        cuentas_sin_clasificar: Número de cuentas pendientes de clasificar
        theme: "dark" | "light"
        height: Altura del componente en pixels (None = auto)
        key: Key único para el componente
        
    Returns:
        None (o valor si se implementan callbacks)
    """
    return _component_func(
        actividades=actividades,
        modo=modo,
        efectivo_inicial=efectivo_inicial,
        efectivo_final=efectivo_final,
        variacion_neta=variacion_neta,
        cuentas_sin_clasificar=cuentas_sin_clasificar,
        theme=theme,
        key=key,
        default=None
    )


# Función helper para transformar datos del backend al formato esperado
def transform_backend_to_component(flujo_data: dict, modo: str = "consolidado") -> dict:
    """
    Transforma la respuesta del backend al formato esperado por el componente.
    
    Args:
        flujo_data: Respuesta del endpoint /api/v1/flujo-caja/
        modo: Modo de visualización
        
    Returns:
        Dict con estructura para ias7_tree()
    """
    actividades_raw = flujo_data.get("actividades", {})
    conciliacion = flujo_data.get("conciliacion", {})
    drill_down = flujo_data.get("drill_down", {})
    
    # Colores por actividad
    colores = {
        "OPERACION": "#2ecc71",
        "INVERSION": "#3498db", 
        "FINANCIAMIENTO": "#9b59b6"
    }
    
    actividades = []
    for key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
        if key in actividades_raw:
            act = actividades_raw[key]
            
            # Enriquecer conceptos con drill-down
            conceptos = act.get("conceptos", [])
            for concepto in conceptos:
                c_id = concepto.get("id")
                if c_id and c_id in drill_down:
                    concepto["cuentas"] = drill_down[c_id]
            
            actividades.append({
                "key": key,
                "nombre": act.get("nombre", key),
                "subtotal": act.get("subtotal", 0),
                "subtotal_nombre": act.get("subtotal_nombre", f"Subtotal {key}"),
                "conceptos": conceptos,
                "color": colores.get(key, "#718096")
            })
    
    return {
        "actividades": actividades,
        "modo": modo,
        "efectivo_inicial": conciliacion.get("efectivo_inicial", 0),
        "efectivo_final": conciliacion.get("efectivo_final", 0),
        "variacion_neta": conciliacion.get("incremento_neto", 0),
        "cuentas_sin_clasificar": len(flujo_data.get("cuentas_sin_clasificar", []))
    }

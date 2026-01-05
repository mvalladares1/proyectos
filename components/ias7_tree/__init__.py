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
# Force RELEASE to true to avoid any env var confusion
_RELEASE = True 
# _RELEASE = os.getenv("IAS7_RELEASE", "false").lower() == "true"

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
    Mergea flujo Real (actividades) y Proyectado (proyeccion).
    """
    actividades_real = flujo_data.get("actividades", {})
    proyeccion_data = flujo_data.get("proyeccion", {})
    actividades_proy = proyeccion_data.get("actividades", {})
    
    conciliacion = flujo_data.get("conciliacion", {})
    # drill_down contiene el desglose de cuentas REALES
    drill_down_real = flujo_data.get("drill_down", {})
    
    # Colores por actividad
    colores = {
        "OPERACION": "#2ecc71",
        "INVERSION": "#3498db", 
        "FINANCIAMIENTO": "#9b59b6"
    }
    
    actividades_output = []
    
    # Iteramos las 3 actividades principales
    for key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
        # Datos Real
        act_real = actividades_real.get(key, {})
        conceptos_real = act_real.get("conceptos", [])
        
        # Datos Proyectado
        act_proy = actividades_proy.get(key, {})
        conceptos_proy = act_proy.get("conceptos", [])
        
        # Mapeo por ID para mergear
        # {codigo: {real: node, proy: node}}
        nodes_map = {}
        
        # 1. Procesar Real
        for c in conceptos_real:
            c_id = c.get("id") or c.get("codigo")
            if c_id:
                nodes_map.setdefault(c_id, {})["real"] = c
                
        # 2. Procesar Proyectado
        for c in conceptos_proy:
            c_id = c.get("codigo")
            if c_id:
                nodes_map.setdefault(c_id, {})["proy"] = c
                
        # 3. Construir lista unificada de conceptos
        conceptos_merged = []
        subtotal_real = act_real.get("subtotal", 0)
        subtotal_proy = act_proy.get("subtotal", 0)
        
        # Usamos el orden definido en ESTRUCTURA_FLUJO (que backend ya debería respetar)
        # O ordenamos por código
        all_ids = sorted(nodes_map.keys())
        
        for c_id in all_ids:
            data = nodes_map[c_id]
            node_real = data.get("real", {})
            node_proy = data.get("proy", {})
            
            # Base info (preferir Real, luego Proy - nombre debería ser igual)
            nombre = node_real.get("nombre") or node_proy.get("nombre") or "Sin Nombre"
            nivel = node_real.get("nivel", 3) # Default level 3
            tipo = node_real.get("tipo", "LINEA")
            
            # Montos
            monto_r = node_real.get("monto", 0)
            monto_p = node_proy.get("monto", 0)
            
            # Drill-down: Cuentas (Real) y Documentos (Proyectado)
            cuentas = []
            if c_id in drill_down_real:
                cuentas = drill_down_real[c_id]
                
            documentos = node_proy.get("documentos", [])
            
            # Warning flag: si hay documentos sin etiqueta
            has_warning = False
            if documentos:
                has_warning = any(d.get("sin_etiqueta", False) for d in documentos)
            
            # Monto Display según modo (aunque el frontend también puede calcularlo)
            monto_disp = 0
            if modo == "real":
                monto_disp = monto_r
            elif modo == "proyectado":
                monto_disp = monto_p
            else:
                monto_disp = monto_r + monto_p

            conceptos_merged.append({
                "id": c_id,
                "nombre": nombre,
                "tipo": tipo,
                "nivel": nivel,
                "monto_real": monto_r,
                "monto_proyectado": monto_p,
                "monto_display": monto_disp,
                "cuentas": cuentas,
                "documentos": documentos,
                "has_warning": has_warning
            })
            
        actividades_output.append({
            "key": key,
            "nombre": act_real.get("nombre") or act_proy.get("nombre") or key,
            "subtotal": subtotal_real + subtotal_proy if modo == "consolidado" else (subtotal_real if modo == "real" else subtotal_proy),
            "subtotal_nombre": act_real.get("subtotal_nombre") or f"Flujos netos {key}",
            "conceptos": conceptos_merged,
            "color": colores.get(key, "#718096")
        })
    
    return {
        "actividades": actividades_output,
        "modo": modo,
        "efectivo_inicial": conciliacion.get("efectivo_inicial", 0),
        "efectivo_final": conciliacion.get("efectivo_final", 0),
        "variacion_neta": conciliacion.get("incremento_neto", 0),
        "cuentas_sin_clasificar": len(flujo_data.get("cuentas_sin_clasificar", []))
    }

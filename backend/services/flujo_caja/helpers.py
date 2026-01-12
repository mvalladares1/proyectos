"""
Funciones auxiliares para cálculos de flujo de caja.
"""
from typing import Dict, List


def sumar_hijos(parent_id: str, montos: Dict[str, float], conceptos: List[Dict]) -> float:
    """
    Suma los montos de todos los hijos directos e indirectos de un nodo.
    Solo suma LINEAs para evitar doble conteo.
    
    Args:
        parent_id: ID del concepto padre
        montos: Dict con montos por concepto_id
        conceptos: Lista de conceptos del catálogo
        
    Returns:
        Total sumado de los hijos
    """
    total = 0.0
    prefix = parent_id + "."
    
    for concepto in conceptos:
        c_id = concepto.get("id", "")
        c_tipo = concepto.get("tipo", "")
        
        # Solo sumar LINEAs que son hijos (directos o indirectos)
        if c_tipo == "LINEA":
            if c_id.startswith(prefix) or concepto.get("parent") == parent_id:
                total += montos.get(c_id, 0.0)
    
    return total


def migrar_codigo_antiguo(codigo_antiguo: str, migracion_codigos: Dict[str, str]) -> str:
    """
    Convierte códigos antiguos (OP01, IN01) a nuevos (1.1.1, 2.1).
    
    Args:
        codigo_antiguo: Código en formato antiguo
        migracion_codigos: Dict de mapeo de códigos antiguos a nuevos
        
    Returns:
        Código en formato nuevo
    """
    return migracion_codigos.get(codigo_antiguo, codigo_antiguo)


def build_categorias_dropdown(conceptos: List[Dict], emojis_actividad: Dict[str, str]) -> List[Dict]:
    """
    Construye la lista de categorías para el dropdown del editor.
    
    Args:
        conceptos: Lista de conceptos del catálogo
        emojis_actividad: Dict con emojis por actividad
        
    Returns:
        Lista de dicts con formato {"label": "...", "value": "..."}
    """
    lineas = [c for c in conceptos if c.get("tipo") == "LINEA"]
    sorted_lineas = sorted(lineas, key=lambda x: x.get("order", 999))
    
    resultado = []
    for c in sorted_lineas:
        actividad = c.get("actividad", "")
        emoji = emojis_actividad.get(actividad, "⚪")
        
        resultado.append({
            "label": f"{emoji} {c['id']} - {c['nombre'][:60]}",
            "value": c['id']
        })
    
    # Agregar NEUTRAL al final
    resultado.append({
        "label": "⚪ NEUTRAL - Transferencias internas (no impacta flujo)",
        "value": "NEUTRAL"
    })
    
    return resultado


def aggregate_montos_by_concepto(
    conceptos: List[Dict],
    montos_por_linea: Dict[str, float],
    proyeccion_por_linea: Dict[str, float],
    modo: str = "consolidado"
) -> List[Dict]:
    """
    Agrega montos por concepto, calculando totales de nodos padres.
    
    Args:
        conceptos: Lista de conceptos del catálogo
        montos_por_linea: Dict con montos reales por concepto_id
        proyeccion_por_linea: Dict con montos proyectados por concepto_id
        modo: 'real', 'proyectado' o 'consolidado'
        
    Returns:
        Lista de conceptos con montos calculados
    """
    proyeccion_por_linea = proyeccion_por_linea or {}
    sorted_conceptos = sorted(conceptos, key=lambda x: x.get("order", 999))
    
    resultado = []
    
    for concepto in sorted_conceptos:
        c_id = concepto.get("id")
        c_tipo = concepto.get("tipo")
        
        if c_tipo == "LINEA":
            # Montos directos
            monto_real = montos_por_linea.get(c_id, 0.0)
            monto_proy = proyeccion_por_linea.get(c_id, 0.0)
        elif c_tipo in ("HEADER", "TOTAL"):
            # Sumar hijos
            monto_real = sumar_hijos(c_id, montos_por_linea, conceptos)
            monto_proy = sumar_hijos(c_id, proyeccion_por_linea, conceptos)
        else:
            # DATA u otros
            monto_real = montos_por_linea.get(c_id, 0.0)
            monto_proy = proyeccion_por_linea.get(c_id, 0.0)
        
        # Determinar monto a mostrar según modo
        if modo == "real":
            monto_display = monto_real
        elif modo == "proyectado":
            monto_display = monto_proy
        else:  # consolidado
            monto_display = monto_real + monto_proy
        
        resultado.append({
            "id": c_id,
            "nombre": concepto.get("nombre"),
            "tipo": c_tipo,
            "nivel": concepto.get("nivel", 3),
            "parent": concepto.get("parent"),
            "order": concepto.get("order"),
            "signo": concepto.get("signo", 1),
            "actividad": concepto.get("actividad"),
            "monto_real": round(monto_real, 0),
            "monto_proyectado": round(monto_proy, 0),
            "monto_display": round(monto_display, 0)
        })
    
    return resultado

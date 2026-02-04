"""
Componente G6 Graph para visualización de grafos tipo Sankey.
Usa AntV G6 con layout dagre para crear diagramas de flujo customizables.
"""
from pathlib import Path
import streamlit.components.v1 as components

_COMPONENT_NAME = "g6_graph"
_RELEASE = True

if _RELEASE:
    parent_dir = Path(__file__).parent
    build_dir = parent_dir / "frontend" / "build"
    _component_func = components.declare_component(_COMPONENT_NAME, path=str(build_dir))
else:
    _component_func = components.declare_component(
        _COMPONENT_NAME,
        url="http://localhost:3001"
    )


def g6_graph(
    nodes,
    edges,
    layout="dagre",
    direction="LR",
    height=800,
    key=None
):
    """
    Renderiza un grafo usando G6 con layout dagre (tipo Sankey).
    
    Args:
        nodes: Lista de nodos [{"id": "1", "label": "Node 1", "color": "#5B8FF9", ...}]
        edges: Lista de edges [{"source": "1", "target": "2", "value": 100, ...}]
        layout: Tipo de layout ("dagre", "force", "circular")
        direction: Dirección del flujo ("LR", "RL", "TB", "BT")
        height: Altura del grafo en pixels
        key: Key único para el componente
        
    Returns:
        Evento de interacción (click en nodo/edge)
    """
    component_value = _component_func(
        nodes=nodes,
        edges=edges,
        layout=layout,
        direction=direction,
        height=height,
        key=key,
        default=None
    )
    
    return component_value


__all__ = ["g6_graph"]

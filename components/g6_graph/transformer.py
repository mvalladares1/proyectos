"""
Transformador de datos de Sankey a formato G6.
Convierte la estructura de nodos/links de Plotly Sankey al formato de G6.
"""
from typing import Dict, List


def transform_sankey_to_g6(sankey_data: Dict) -> Dict:
    """
    Transforma datos de Sankey (formato Plotly) a formato G6.
    
    Args:
        sankey_data: Dict con formato {
            "nodes": [{"label": "...", "color": "...", "detail": "..."}, ...],
            "links": [{"source": idx, "target": idx, "value": num, "color": "..."}, ...]
        }
    
    Returns:
        Dict con formato {
            "nodes": [{"id": "0", "label": "...", "color": "...", ...}, ...],
            "edges": [{"source": "0", "target": "1", "value": num, ...}, ...]
        }
    """
    nodes = []
    edges = []
    
    # Transformar nodos
    for idx, node in enumerate(sankey_data.get("nodes", [])):
        g6_node = {
            "id": str(idx),
            "label": node.get("label", ""),
            "color": node.get("color", "#5B8FF9"),
            "detail": node.get("detail", ""),
            # Ajustar tamaño según longitud del label
            "size": [
                max(150, min(300, len(node.get("label", "")) * 8)),
                60
            ]
        }
        nodes.append(g6_node)
    
    # Transformar links a edges
    for link in sankey_data.get("links", []):
        source = str(link.get("source", 0))
        target = str(link.get("target", 0))
        value = link.get("value", 1)
        
        g6_edge = {
            "source": source,
            "target": target,
            "value": value,
            "label": f"{value:,.0f}" if value >= 100 else f"{value:.1f}",
            "color": link.get("color", "rgba(180,180,180,0.5)"),
            "opacity": 0.5
        }
        edges.append(g6_edge)
    
    return {
        "nodes": nodes,
        "edges": edges
    }


__all__ = ["transform_sankey_to_g6"]

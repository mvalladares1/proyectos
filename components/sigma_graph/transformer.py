"""
Transformador de datos de Plotly Sankey a formato Sigma.js.
"""
from typing import Dict, List


def transform_sankey_to_sigma(sankey_data: Dict) -> Dict:
    """
    Convierte datos de Plotly Sankey a formato Sigma.js.
    
    Args:
        sankey_data: Dict con nodes y links de Plotly Sankey
        
    Returns:
        Dict con nodes y edges para Sigma.js
    """
    nodes = []
    edges = []
    
    # Convertir nodos
    for i, node in enumerate(sankey_data.get("nodes", [])):
        nodes.append({
            "id": str(i),
            "label": node.get("label", f"Node {i}"),
            "color": node.get("color", "#5B8FF9"),
            "size": 10,
            "x": 0,  # Sigma.js calculará las posiciones
            "y": 0,
            "detail": node.get("detail", "")
        })
    
    # Convertir edges
    for i, link in enumerate(sankey_data.get("links", [])):
        source = str(link.get("source", 0))
        target = str(link.get("target", 0))
        value = link.get("value", 1)
        
        edges.append({
            "id": f"e{i}",
            "source": source,
            "target": target,
            "label": f"{value} unidades",
            "size": max(1, min(10, value / 100)),  # Grosor proporcional
            "color": "#cccccc"
        })
    
    return {
        "nodes": nodes,
        "edges": edges
    }

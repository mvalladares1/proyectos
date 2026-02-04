"""
Transformador de datos de Plotly Sankey a formato Sigma.js.
"""
from typing import Dict, List, Tuple
from datetime import datetime


NODE_LEVELS = {
    "SUPPLIER": 0,
    "RECEPTION": 1,
    "PALLET_IN": 2,
    "PROCESS": 3,
    "PALLET_OUT": 4,
    "CUSTOMER": 5,
}


def _parse_date_from_detail(detail: Dict) -> str:
    if not isinstance(detail, dict):
        return ""
    for key in ("date", "date_done", "scheduled_date"):
        value = detail.get(key)
        if value:
            return str(value)[:10]
    return ""


def _safe_parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d")
    except Exception:
        return None


def _compute_timeline_positions(nodes: List[Dict]) -> Tuple[List[Dict], Dict]:
    dates = []
    for n in nodes:
        date_str = n.get("date", "")
        dt = _safe_parse_date(date_str)
        if dt:
            dates.append(dt)

    if not dates:
        return nodes, {"min": None, "max": None}

    min_date = min(dates)
    max_date = max(dates)
    total_days = (max_date - min_date).days or 1

    # Configuración de layout
    margin_x = 0.1
    margin_y = 0.08
    usable_width = 1 - 2 * margin_x
    usable_height = 1 - 2 * margin_y
    level_count = max(NODE_LEVELS.values()) + 1
    y_spacing = usable_height / max(1, level_count - 1)

    # Contador por (date, level) para separar nodos
    bucket_offsets: Dict[Tuple[str, int], int] = {}
    max_bucket = 6

    positioned = []
    for n in nodes:
        node = {**n}
        date_str = node.get("date", "")
        dt = _safe_parse_date(date_str) or min_date
        level = NODE_LEVELS.get(node.get("type", "PROCESS"), 3)

        days_from_start = (dt - min_date).days
        x = margin_x + (days_from_start / total_days) * usable_width
        y = margin_y + level * y_spacing

        bucket_key = (dt.strftime("%Y-%m-%d"), level)
        offset_idx = bucket_offsets.get(bucket_key, 0)
        bucket_offsets[bucket_key] = (offset_idx + 1) % max_bucket

        # Distribuir ligeramente en Y para evitar colisiones
        jitter = (offset_idx - (max_bucket / 2)) * 0.01
        node["x"] = x
        node["y"] = max(0, min(1, y + jitter))
        positioned.append(node)

    return positioned, {"min": min_date.strftime("%Y-%m-%d"), "max": max_date.strftime("%Y-%m-%d")}


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
        detail = node.get("detail", {})
        node_type = node.get("type") or (detail.get("type") if isinstance(detail, dict) else None) or "PROCESS"
        date_str = _parse_date_from_detail(detail)
        nodes.append({
            "id": str(i),
            "label": node.get("label", f"Node {i}"),
            "color": node.get("color", "#5B8FF9"),
            "size": 10,
            "x": 0,
            "y": 0,
            "detail": detail,
            "type": node_type,
            "date": date_str,
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
            "size": 2,  # Grosor estándar para todos los edges
            "color": "#cccccc"
        })
    
    # Calcular posiciones tipo timeline
    nodes, date_range = _compute_timeline_positions(nodes)

    return {
        "nodes": nodes,
        "edges": edges,
        "date_range": date_range,
    }

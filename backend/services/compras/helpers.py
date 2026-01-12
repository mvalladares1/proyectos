"""
Funciones auxiliares para el módulo de Compras.
"""
from typing import Dict, List


def clean_record(rec: Dict) -> Dict:
    """Limpia registros de Odoo para serialización JSON."""
    out = {}
    for k, v in rec.items():
        if v is False:
            out[k] = None
        elif isinstance(v, (list, tuple)) and len(v) == 2 and isinstance(v[0], int):
            out[k] = v[1]  # Extraer nombre de Many2one
            out[f"{k}_id"] = v[0]
        else:
            out[k] = v
    return out


def compute_receive_status(odoo, po_ids: List[int]) -> Dict[int, str]:
    """
    Calcula el estado de recepción de las POs.
    Retorna: {po_id: 'No recepcionada' | 'Recepción parcial' | 
                     'Recepcionada totalmente' | 'No se recepciona'}
    """
    if not po_ids:
        return {}
    
    # Leer líneas de PO
    try:
        lines = odoo.search_read(
            'purchase.order.line',
            [['order_id', 'in', po_ids]],
            ['order_id', 'product_qty', 'qty_received'],
            limit=5000
        )
    except Exception:
        return {pid: "No se recepciona" for pid in po_ids}
    
    # Agrupar líneas por PO
    grouped = {pid: [] for pid in po_ids}
    for line in lines:
        oid = line['order_id'][0] if isinstance(line.get('order_id'), (list, tuple)) else line.get('order_id')
        if oid:
            grouped.setdefault(oid, []).append(line)
    
    result = {}
    
    for pid, lst in grouped.items():
        # Sin líneas → no se recepciona
        if not lst:
            result[pid] = "No se recepciona"
            continue
        
        # Todas las líneas con qty=0 → servicios
        if all(float(l.get('product_qty') or 0) == 0 for l in lst):
            result[pid] = "No se recepciona"
            continue
        
        any_received = False
        fully_received = True
        
        for l in lst:
            ordered = float(l.get('product_qty') or 0)
            received = float(l.get('qty_received') or 0)
            
            if ordered == 0:
                continue
            
            if received > 0:
                any_received = True
            
            if received < ordered:
                fully_received = False
        
        if not any_received:
            result[pid] = "No recepcionada"
        elif fully_received:
            result[pid] = "Recepcionada totalmente"
        else:
            result[pid] = "Recepción parcial"
    
    return result


def compute_approval_status(po_state: str, approvals_count: int, 
                            required_count: int = None) -> str:
    """Calcula el estado de aprobación de una PO."""
    if po_state == "cancel":
        return "Rechazada"
    
    if po_state in ("purchase", "done"):
        return "Aprobada"
    
    if required_count is None or required_count == 0:
        return "En revisión" if approvals_count == 0 else "Parcialmente aprobada"
    
    if approvals_count == 0:
        return "En revisión"
    elif approvals_count < required_count:
        return "Parcialmente aprobada"
    else:
        return "Aprobada"

"""
Funciones auxiliares y builders para el módulo de Pedidos de Venta.
"""
from typing import List, Dict
from backend.utils import get_name_from_relation


def build_pallet_products(quants: List[Dict]) -> List[Dict]:
    """Construye lista de productos desde quants."""
    products = []
    for quant in quants:
        product_name = quant.get("name")
        if not product_name:
            product_name = get_name_from_relation(quant.get("product_id"))
        lot_rel = quant.get("lot_id")
        lot_id = lot_rel[0] if isinstance(lot_rel, (list, tuple)) and lot_rel else None
        products.append({
            "product": product_name,
            "lot_id": lot_id,
            "lot": get_name_from_relation(quant.get("lot_id")),
            "quantity": quant.get("quantity", 0)
        })
    return products


def build_container_detail(container: Dict) -> Dict:
    """Construye detalle de container para Sankey."""
    return {
        "id": container.get("id"),
        "name": container.get("name", ""),
        "partner": container.get("partner_name", "N/A"),
        "date_order": container.get("date_order", ""),
        "kg_total": container.get("kg_total", 0),
        "kg_producidos": container.get("kg_producidos", 0),
        "avance_pct": container.get("avance_pct", 0)
    }


def build_fabrication_detail(fab: Dict, production_detail: Dict) -> Dict:
    """Construye detalle de fabricación para Sankey."""
    return {
        "id": fab.get("id"),
        "name": fab.get("name", ""),
        "product": fab.get("product_name", "N/A"),
        "state": fab.get("state_display", fab.get("state", "")),
        "kg_producidos": fab.get("kg_producidos", 0),
        "sala": fab.get("sala_proceso", "N/A"),
        "componentes": production_detail.get("componentes", []),
        "subproductos": production_detail.get("subproductos", []),
        "x_studio_total": production_detail.get("x_studio_total", 0),
        "subproducts_totals": production_detail.get("subproducts_totals", {})
    }


def build_pallet_detail(pallet: Dict) -> Dict:
    """Construye detalle de pallet para Sankey."""
    return {
        "id": pallet.get("id"),
        "name": pallet.get("name", ""),
        "pack_date": pallet.get("pack_date", ""),
        "qty": pallet.get("qty", 0),
        "products": pallet.get("products", [])
    }

"""
Servicio para gestión de Stock y Cámaras
Migrado del dashboard original de producción
"""
from typing import List, Dict, Optional
from datetime import datetime

from shared.odoo_client import OdooClient


def clean_record(record: Dict) -> Dict:
    """Limpia un registro de Odoo convirtiendo tuplas en diccionarios"""
    if not record:
        return {}
    
    cleaned = {}
    for key, value in record.items():
        if isinstance(value, (list, tuple)) and len(value) == 2 and isinstance(value[0], int):
            # Es una relación many2one: (id, nombre)
            cleaned[key] = {"id": value[0], "name": value[1]}
        elif isinstance(value, list) and value and isinstance(value[0], int):
            # Es una relación many2many o one2many: [id1, id2, ...]
            cleaned[key] = value
        else:
            cleaned[key] = value
    return cleaned


class StockService:
    """Servicio para operaciones de Stock y Cámaras"""

    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)

    def get_chambers_stock(self) -> List[Dict]:
        """
        Obtiene stock agrupado por camara (ubicacion) y especie/condicion.
        Usa search_read limitado para mantener rendimiento y garantizar datos.
        """
        domain = [
            ("quantity", ">", 0),
            ("location_id.usage", "=", "internal"),
            ("location_id.active", "=", True)
        ]
        fields = ["location_id", "product_id", "quantity", "package_id"]

        try:
            quants = self.odoo.search_read(
                "stock.quant",
                domain,
                fields,
                limit=50000
            )
        except Exception as e:
            print(f"Error fetching quants: {e}")
            return []

        if not quants:
            return []

        loc_ids = sorted({
            q["location_id"][0]
            for q in quants
            if q.get("location_id") and isinstance(q["location_id"], (list, tuple))
        })
        if not loc_ids:
            return []

        pallets_per_location: Dict[int, set] = {}
        for q in quants:
            loc = q.get("location_id")
            pkg = q.get("package_id")
            if loc and pkg and isinstance(loc, (list, tuple)) and isinstance(pkg, (list, tuple)):
                pallets_per_location.setdefault(loc[0], set()).add(pkg[0])

        fields_loc = [
            "name",
            "display_name",
            "location_id",
            "usage",
            "active",
            "x_capacity_pallets",
            "pallet_capacity",
        ]

        try:
            locations = self.odoo.read("stock.location", loc_ids, fields_loc)
        except Exception as e:
            print(f"Error fetching locations: {e}")
            locations = []

        chambers = {}
        for loc in locations:
            clean_loc = clean_record(loc)
            loc_id = clean_loc["id"]
            if loc.get("usage") != "internal" or not loc.get("active", True):
                continue
            parent = loc.get("location_id")
            parent_name = parent[1] if parent and isinstance(parent, (list, tuple)) and len(parent) > 1 else "Sin Padre"
            
            occupied = len(pallets_per_location.get(loc_id, set()))

            capacity_candidates = [
                loc.get("x_capacity_pallets"),
                loc.get("pallet_capacity"),
            ]
            capacity = next((c for c in capacity_candidates if isinstance(c, (int, float)) and c > 0), None)
            if capacity is None:
                capacity = max(occupied, 50)

            chambers[loc_id] = {
                "id": loc_id,
                "name": clean_loc["name"],
                "full_name": clean_loc["display_name"],
                "parent_name": parent_name,
                "capacity_pallets": capacity,
                "occupied_pallets": occupied,
                "stock_data": {}
            }

        if not chambers:
            # Fallback minimal data directly from quant info
            for q in quants:
                loc = q.get("location_id")
                if not loc or not isinstance(loc, (list, tuple)) or len(loc) < 2:
                    continue
                loc_id, loc_name = loc
                chambers.setdefault(loc_id, {
                    "id": loc_id,
                    "name": loc_name,
                    "full_name": loc_name,
                    "parent_name": "N/D",
                    "capacity_pallets": len(pallets_per_location.get(loc_id, set())) or 50,
                    "occupied_pallets": len(pallets_per_location.get(loc_id, set())),
                    "stock_data": {}
                })

        product_ids = {
            q["product_id"][0]
            for q in quants
            if q.get("product_id") and isinstance(q["product_id"], (list, tuple))
        }
        products_info = {}
        if product_ids:
            try:
                p_data = self.odoo.read(
                    "product.product",
                    list(product_ids),
                    ["categ_id", "name"]
                )
                for p in p_data:
                    products_info[p["id"]] = {
                        "category": p["categ_id"][1] if p.get("categ_id") and isinstance(p.get("categ_id"), (list, tuple)) else "Sin Categoria",
                        "name": p.get("name", "")
                    }
            except Exception as e:
                print(f"Error fetching products: {e}")

        for q in quants:
            loc = q.get("location_id")
            prod = q.get("product_id")
            if not loc or not prod:
                continue
            if not isinstance(loc, (list, tuple)) or len(loc) < 1:
                continue
            if not isinstance(prod, (list, tuple)) or len(prod) < 1:
                continue
            loc_id = loc[0]
            if loc_id not in chambers:
                continue

            qty = q.get("quantity", 0) or 0
            p_info = products_info.get(prod[0])
            if p_info:
                species = p_info["category"]
                condition = "Organico" if "org" in p_info["name"].lower() else "Convencional"
            else:
                species = "Desconocido"
                condition = "N/A"

            key = f"{species} - {condition}"
            chambers[loc_id]["stock_data"][key] = chambers[loc_id]["stock_data"].get(key, 0) + qty

        result = [data for data in chambers.values() if data["stock_data"]]
        return result

    def get_pallets(self, location_id: int, category: Optional[str] = None) -> List[Dict]:
        """
        Obtiene el detalle de pallets de una ubicación, opcionalmente filtrado por categoría/especie.
        """
        domain = [
            ("location_id", "=", location_id),
            ("quantity", ">", 0),
            ("package_id", "!=", False)  # Solo pallets
        ]
        
        fields = [
            "package_id", "product_id", "lot_id", "quantity", 
            "in_date", "location_id"
        ]
        
        try:
            quant_ids = self.odoo.search(
                "stock.quant",
                domain,
                limit=5000,
                order="in_date desc"
            )
            quants = self.odoo.read("stock.quant", quant_ids, fields) if quant_ids else []
        except Exception as e:
            print(f"Error fetching pallets: {e}")
            return []
            
        # Filtrar y formatear
        pallets = []
        
        # Necesitamos categorías para filtrar
        product_ids = set(q["product_id"][0] for q in quants if q.get("product_id") and isinstance(q.get("product_id"), (list, tuple)))
        products_map = {}
        if product_ids:
            p_data = self.odoo.read("product.product", list(product_ids), ["categ_id", "name"])
            for p in p_data:
                products_map[p["id"]] = p
        
        for q in quants:
            prod_id = q["product_id"][0] if q.get("product_id") and isinstance(q.get("product_id"), (list, tuple)) else None
            if not prod_id: 
                continue
                
            p_info = products_map.get(prod_id, {})
            categ = p_info.get("categ_id")
            if categ and isinstance(categ, (list, tuple)) and len(categ) > 1:
                cat_name = categ[1]
            else:
                cat_name = "Sin Categoría"
            prod_name = p_info.get("name", "N/A")
            
            # Heurística de condición
            condition = "Orgánico" if "org" in prod_name.lower() else "Convencional"
            species_condition = f"{cat_name} - {condition}"
            
            # Filtro
            if category and category != species_condition:
                continue
            
            # Procesar fecha de entrada
            in_date = q.get("in_date")
            in_date_str = ""
            days_old = 0
            if in_date:
                try:
                    if isinstance(in_date, str):
                        dt = datetime.fromisoformat(in_date.replace('Z', '+00:00'))
                    else:
                        dt = in_date
                    in_date_str = dt.strftime("%Y-%m-%d")
                    days_old = (datetime.now() - dt.replace(tzinfo=None)).days
                except:
                    pass
                
            pallets.append({
                "pallet": q["package_id"][1] if q["package_id"] else "Sin Pallet",
                "product": prod_name,
                "lot": q["lot_id"][1] if q["lot_id"] else "N/A",
                "quantity": q["quantity"],
                "category": cat_name,
                "condition": condition,
                "species_condition": species_condition,
                "location": q["location_id"][1],
                "in_date": in_date_str,
                "days_old": days_old
            })
            
        return pallets

    def get_lots_by_category(self, category: str, location_ids: Optional[List[int]] = None) -> List[Dict]:
        """
        Obtiene lotes agrupados por categoría con información de antigüedad.
        category: Especie - Condición (ej: "PRODUCTOS / PTT - Convencional")
        """
        # Parsear categoría y condición
        parts = category.rsplit(" - ", 1)
        cat_name = parts[0] if len(parts) > 0 else category
        condition_filter = parts[1] if len(parts) > 1 else None
        
        # Dominio base
        domain = [
            ("quantity", ">", 0),
            ("lot_id", "!=", False),
            ("location_id.usage", "=", "internal")
        ]
        
        if location_ids:
            domain.append(("location_id", "in", location_ids))
        
        fields = [
            "lot_id", "product_id", "quantity", "in_date", 
            "location_id", "package_id"
        ]
        
        try:
            quant_ids = self.odoo.search(
                "stock.quant",
                domain,
                limit=20000,
                order="in_date desc"
            )
            quants = self.odoo.read("stock.quant", quant_ids, fields) if quant_ids else []
        except Exception as e:
            print(f"Error fetching lots: {e}")
            return []
        
        # Obtener info de productos
        product_ids = set(q["product_id"][0] for q in quants if q.get("product_id"))
        products_map = {}
        if product_ids:
            try:
                p_data = self.odoo.read("product.product", list(product_ids), ["categ_id", "name"])
                for p in p_data:
                    products_map[p["id"]] = p
            except:
                pass
        
        # Agrupar por lote
        lots_data = {}
        
        for q in quants:
            prod_id = q["product_id"][0] if q.get("product_id") else None
            lot_id = q["lot_id"][0] if q.get("lot_id") else None
            
            if not prod_id or not lot_id:
                continue
            
            p_info = products_map.get(prod_id, {})
            p_cat = p_info.get("categ_id", [0, ""])[1] if p_info.get("categ_id") else ""
            p_name = p_info.get("name", "")
            p_condition = "Orgánico" if "org" in p_name.lower() else "Convencional"
            p_species_condition = f"{p_cat} - {p_condition}"
            
            # Filtrar por categoría
            if p_species_condition != category:
                continue
            
            lot_name = q["lot_id"][1]
            
            # Procesar fecha
            in_date = q.get("in_date")
            in_date_str = ""
            days_old = 0
            if in_date:
                try:
                    if isinstance(in_date, str):
                        dt = datetime.fromisoformat(in_date.replace('Z', '+00:00'))
                    else:
                        dt = in_date
                    in_date_str = dt.strftime("%Y-%m-%d")
                    days_old = (datetime.now() - dt.replace(tzinfo=None)).days
                except:
                    pass
            
            # Agrupar
            if lot_name not in lots_data:
                lots_data[lot_name] = {
                    "lot": lot_name,
                    "product": p_name,
                    "category": p_cat,
                    "condition": p_condition,
                    "quantity": 0,
                    "pallets": 0,
                    "in_date": in_date_str,
                    "days_old": days_old,
                    "locations": set()
                }
            
            lots_data[lot_name]["quantity"] += q["quantity"]
            if q.get("package_id"):
                lots_data[lot_name]["pallets"] += 1
            if q.get("location_id"):
                lots_data[lot_name]["locations"].add(q["location_id"][1])
        
        # Formatear resultado
        result = []
        for lot_name, data in lots_data.items():
            data["locations"] = list(data["locations"])
            result.append(data)
        
        # Ordenar por antigüedad (más viejo primero)
        result.sort(key=lambda x: x["days_old"], reverse=True)
        
        return result

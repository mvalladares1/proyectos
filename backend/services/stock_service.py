"""
Servicio para gestión de Stock y Cámaras
Migrado del dashboard original de producción
OPTIMIZADO: Incluye caché para ubicaciones y productos
"""
from typing import List, Dict, Optional
from datetime import datetime

from shared.odoo_client import OdooClient
from backend.utils import clean_record
from backend.cache import get_cache, OdooCache


class StockService:
    """Servicio para operaciones de Stock y Cámaras"""

    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self._cache = get_cache()
    
    def _get_products_cached(self, product_ids: List[int]) -> Dict[int, Dict]:
        """
        Obtiene información de productos usando caché.
        TTL: 30 minutos (productos cambian poco).
        """
        if not product_ids:
            return {}
        
        cache_key = f"products:{hash(tuple(sorted(product_ids)))}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            p_data = self.odoo.read("product.product", list(product_ids), ["categ_id", "name"])
            products_map = {p["id"]: p for p in p_data}
            self._cache.set(cache_key, products_map, ttl=OdooCache.TTL_PRODUCTOS)
            return products_map
        except Exception as e:
            print(f"Error fetching products: {e}")
            return {}
    
    def _get_locations_cached(self, location_ids: List[int]) -> List[Dict]:
        """
        Obtiene información de ubicaciones usando caché.
        TTL: 1 hora (ubicaciones cambian muy raramente).
        """
        if not location_ids:
            return []
        
        cache_key = f"locations:{hash(tuple(sorted(location_ids)))}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        fields_loc = [
            "name", "display_name", "location_id", "usage",
            "active", "x_capacity_pallets", "pallet_capacity"
        ]
        
        try:
            locations = self.odoo.read("stock.location", list(location_ids), fields_loc)
            self._cache.set(cache_key, locations, ttl=OdooCache.TTL_UBICACIONES)
            return locations
        except Exception as e:
            print(f"Error fetching locations: {e}")
            return []

    def get_chambers_stock(self) -> List[Dict]:
        """
        Obtiene stock agrupado por cámara padre (Camara 1, 2, 3 de -25°C, Camara 0°C).
        Las posiciones individuales se agregan a su cámara padre.
        La capacidad se cuenta por número de posiciones hijas.
        """
        # PASO 1: Obtener todos los quants con stock
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

        # PASO 2: Obtener todas las ubicaciones relevantes
        loc_ids = list({
            q["location_id"][0]
            for q in quants
            if q.get("location_id") and isinstance(q["location_id"], (list, tuple))
        })
        if not loc_ids:
            return []

        # Obtener info de ubicaciones (con padre)
        fields_loc = ["name", "display_name", "location_id", "usage", "active"]
        try:
            locations = self.odoo.read("stock.location", loc_ids, fields_loc)
        except Exception as e:
            print(f"Error fetching locations: {e}")
            return []

        # Crear mapa de ubicación -> info y encontrar padres
        loc_map = {}
        parent_ids = set()
        for loc in locations:
            loc_id = loc["id"]
            parent = loc.get("location_id")
            parent_id = parent[0] if parent and isinstance(parent, (list, tuple)) else None
            parent_name = parent[1] if parent and isinstance(parent, (list, tuple)) and len(parent) > 1 else ""
            loc_map[loc_id] = {
                "name": loc.get("name", ""),
                "display_name": loc.get("display_name", ""),
                "parent_id": parent_id,
                "parent_name": parent_name
            }
            if parent_id:
                parent_ids.add(parent_id)

        # PASO 3: Obtener info de padres y abuelos (carga recursiva hasta 3 niveles)
        all_parent_ids = set(parent_ids)
        for level in range(3):  # Hasta 3 niveles de padres
            if not parent_ids:
                break
            try:
                parent_locs = self.odoo.read("stock.location", list(parent_ids), ["name", "display_name", "location_id"])
                new_parent_ids = set()
                for ploc in parent_locs:
                    grandparent = ploc.get("location_id")
                    gp_id = grandparent[0] if grandparent and isinstance(grandparent, (list, tuple)) else None
                    gp_name = grandparent[1] if grandparent and isinstance(grandparent, (list, tuple)) and len(grandparent) > 1 else ""
                    
                    loc_map[ploc["id"]] = {
                        "name": ploc.get("name", ""),
                        "display_name": ploc.get("display_name", ""),
                        "parent_id": gp_id,
                        "parent_name": gp_name
                    }
                    
                    if gp_id and gp_id not in all_parent_ids and gp_id not in loc_map:
                        new_parent_ids.add(gp_id)
                        all_parent_ids.add(gp_id)
                
                parent_ids = new_parent_ids
            except Exception as e:
                print(f"Error fetching parent locations level {level}: {e}")
                break

        # PASO 4: Identificar cámaras principales
        # Nombres exactos de las cámaras que queremos mostrar
        CAMARAS_PRINCIPALES_NOMBRES = [
            "Camara 1 de -25°C",
            "Camara 2 de -25°C", 
            "Camara 3 de -25°C",
            "Camara 0°C",
        ]
        
        # Crear set de IDs de cámaras principales
        camaras_principales_ids = set()
        for loc_id, loc_info in loc_map.items():
            loc_name = loc_info.get("name", "")
            for cam_nombre in CAMARAS_PRINCIPALES_NOMBRES:
                # Comparar ignorando acentos y mayúsculas
                if cam_nombre.lower().replace("°", "").replace("º", "") in loc_name.lower().replace("°", "").replace("º", ""):
                    camaras_principales_ids.add(loc_id)
                    break
        
        # Función para determinar a qué cámara principal pertenece una ubicación
        def get_parent_chamber(loc_id):
            """Busca recursivamente la cámara padre principal"""
            if loc_id in camaras_principales_ids:
                return loc_id
            
            if loc_id not in loc_map:
                return None
            
            loc_info = loc_map[loc_id]
            parent_id = loc_info.get("parent_id")
            
            if parent_id and parent_id != loc_id:
                # Verificar si el padre es una cámara principal
                if parent_id in camaras_principales_ids:
                    return parent_id
                # Si no, buscar recursivamente
                return get_parent_chamber(parent_id)
            
            return None

        # PASO 5: Contar posiciones por cámara y calcular pallets
        chamber_positions = {}  # {chamber_id: set of position_ids}
        chamber_pallets = {}    # {chamber_id: set of pallet_ids}
        
        for loc_id in loc_ids:
            chamber_id = get_parent_chamber(loc_id)
            if chamber_id:
                chamber_positions.setdefault(chamber_id, set()).add(loc_id)

        for q in quants:
            loc = q.get("location_id")
            pkg = q.get("package_id")
            if loc and isinstance(loc, (list, tuple)):
                loc_id = loc[0]
                chamber_id = get_parent_chamber(loc_id)
                if chamber_id and pkg and isinstance(pkg, (list, tuple)):
                    chamber_pallets.setdefault(chamber_id, set()).add(pkg[0])

        # PASO 6: Crear estructura de cámaras
        chambers = {}
        for chamber_id in chamber_positions.keys():
            if chamber_id not in loc_map:
                continue
            info = loc_map[chamber_id]
            chambers[chamber_id] = {
                "id": chamber_id,
                "name": info["name"],
                "full_name": info["display_name"],
                "parent_name": info.get("parent_name", ""),
                "capacity_pallets": len(chamber_positions.get(chamber_id, set())),  # Capacidad = posiciones
                "occupied_pallets": len(chamber_pallets.get(chamber_id, set())),
                "stock_data": {},
                "child_location_ids": list(chamber_positions.get(chamber_id, set()))
            }

        # PASO 7: Obtener info de productos
        product_ids = {
            q["product_id"][0]
            for q in quants
            if q.get("product_id") and isinstance(q["product_id"], (list, tuple))
        }
        
        products_raw = self._get_products_cached(list(product_ids))
        products_info = {}
        for pid, p in products_raw.items():
            cat = p.get("categ_id")
            products_info[pid] = {
                "category": cat[1] if cat and isinstance(cat, (list, tuple)) else "Sin Categoria",
                "name": p.get("name", "")
            }

        # PASO 8: Agregar stock por cámara y tipo fruta/manejo
        for q in quants:
            loc = q.get("location_id")
            prod = q.get("product_id")
            if not loc or not prod:
                continue
            if not isinstance(loc, (list, tuple)) or not isinstance(prod, (list, tuple)):
                continue
            
            loc_id = loc[0]
            chamber_id = get_parent_chamber(loc_id)
            if not chamber_id or chamber_id not in chambers:
                continue

            qty = q.get("quantity", 0) or 0
            p_info = products_info.get(prod[0])
            
            if p_info:
                cat_name = p_info["category"].upper()
                prod_name = p_info["name"].upper()
                
                # Detectar Tipo Fruta (orden importante: más específico primero)
                tipo_fruta = "Otro"
                
                # Primero buscar por código de producto (AR, FB, FR, MO, CR)
                if " AR " in f" {prod_name} " or "AR_" in prod_name or prod_name.startswith("AR ") or "ARANDANO" in prod_name or "ARÁNDANO" in prod_name or "ARANDANO" in cat_name:
                    tipo_fruta = "Arándano"
                elif " FB " in f" {prod_name} " or "FB_" in prod_name or prod_name.startswith("FB ") or "FRAMBUESA" in prod_name or "FRAMBUESA" in cat_name:
                    tipo_fruta = "Frambuesa"
                elif " FR " in f" {prod_name} " or "FR_" in prod_name or prod_name.startswith("FR ") or "FRUTILLA" in prod_name or "FRUTILLA" in cat_name:
                    tipo_fruta = "Frutilla"
                elif " MO " in f" {prod_name} " or "MO_" in prod_name or prod_name.startswith("MO ") or "MORA" in prod_name or "MORA" in cat_name:
                    tipo_fruta = "Mora"
                elif " CR " in f" {prod_name} " or "CR_" in prod_name or prod_name.startswith("CR ") or "CEREZA" in prod_name or "CEREZA" in cat_name:
                    tipo_fruta = "Cereza"
                
                # Detectar Manejo
                if " ORG " in f" {prod_name} " or "ORG_" in prod_name or "_ORG" in prod_name or "ORGANICO" in prod_name or "ORGÁNICO" in prod_name:
                    manejo = "Orgánico"
                elif " CONV " in f" {prod_name} " or "CONV_" in prod_name or "_CONV" in prod_name or "CONVENCIONAL" in prod_name:
                    manejo = "Convencional"
                else:
                    manejo = "Convencional"
            else:
                tipo_fruta = "Desconocido"
                manejo = "N/A"

            key = f"{tipo_fruta} - {manejo}"
            chambers[chamber_id]["stock_data"][key] = chambers[chamber_id]["stock_data"].get(key, 0) + qty

        result = [data for data in chambers.values() if data["stock_data"]]
        return result

    def get_pallets(self, location_id: int, category: Optional[str] = None) -> List[Dict]:
        """
        Obtiene el detalle de pallets de una ubicación (puede ser cámara padre).
        Si es una cámara padre, busca en todas sus ubicaciones hijas.
        Opcionalmente filtrado por categoría (Tipo Fruta - Manejo).
        """
        # Primero, buscar todas las ubicaciones hijas de esta ubicación
        try:
            # Buscar ubicaciones que tengan esta ubicación como padre (recursivo)
            child_locations = self.odoo.search(
                "stock.location",
                [
                    "|",
                    ("id", "=", location_id),
                    ("location_id", "child_of", location_id),
                    ("usage", "=", "internal"),
                    ("active", "=", True)
                ]
            )
            if not child_locations:
                child_locations = [location_id]
        except Exception as e:
            print(f"Error fetching child locations: {e}")
            child_locations = [location_id]
        
        domain = [
            ("location_id", "in", child_locations),
            ("quantity", ">", 0),
            ("package_id", "!=", False)  # Solo pallets
        ]
        
        fields = [
            "package_id", "product_id", "lot_id", "quantity", 
            "in_date", "location_id"
        ]
        
        try:
            quants = self.odoo.search_read(
                "stock.quant",
                domain,
                fields,
                limit=5000,
                order="in_date desc"
            )
        except Exception as e:
            print(f"Error fetching pallets: {e}")
            return []
            
        pallets = []
        
        # Obtener info de productos
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
            cat_name = categ[1] if categ and isinstance(categ, (list, tuple)) and len(categ) > 1 else "Sin Categoría"
            prod_name = p_info.get("name", "N/A")
            prod_upper = prod_name.upper()
            cat_upper = cat_name.upper()
            
            # Detectar Tipo Fruta
            tipo_fruta = "Otro"
            if " AR " in f" {prod_upper} " or "AR_" in prod_upper or prod_upper.startswith("AR ") or "ARANDANO" in prod_upper or "ARÁNDANO" in prod_upper or "ARANDANO" in cat_upper:
                tipo_fruta = "Arándano"
            elif " FB " in f" {prod_upper} " or "FB_" in prod_upper or prod_upper.startswith("FB ") or "FRAMBUESA" in prod_upper or "FRAMBUESA" in cat_upper:
                tipo_fruta = "Frambuesa"
            elif " FR " in f" {prod_upper} " or "FR_" in prod_upper or prod_upper.startswith("FR ") or "FRUTILLA" in prod_upper or "FRUTILLA" in cat_upper:
                tipo_fruta = "Frutilla"
            elif " MO " in f" {prod_upper} " or "MO_" in prod_upper or prod_upper.startswith("MO ") or "MORA" in prod_upper or "MORA" in cat_upper:
                tipo_fruta = "Mora"
            elif " CR " in f" {prod_upper} " or "CR_" in prod_upper or prod_upper.startswith("CR ") or "CEREZA" in prod_upper or "CEREZA" in cat_upper:
                tipo_fruta = "Cereza"
            
            # Detectar Manejo
            if " ORG " in f" {prod_upper} " or "ORG_" in prod_upper or "_ORG" in prod_upper or "ORGANICO" in prod_upper or "ORGÁNICO" in prod_upper:
                manejo = "Orgánico"
            elif " CONV " in f" {prod_upper} " or "CONV_" in prod_upper or "_CONV" in prod_upper or "CONVENCIONAL" in prod_upper:
                manejo = "Convencional"
            else:
                manejo = "Convencional"
            
            tipo_fruta_manejo = f"{tipo_fruta} - {manejo}"
            
            # Filtro por categoría (Tipo Fruta - Manejo)
            if category and category != tipo_fruta_manejo:
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
                "tipo_fruta": tipo_fruta,
                "manejo": manejo,
                "tipo_fruta_manejo": tipo_fruta_manejo,
                "condition": manejo,
                "species_condition": tipo_fruta_manejo,
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
        
        # OPTIMIZADO: usar search_read en lugar de search + read separados
        try:
            quants = self.odoo.search_read(
                "stock.quant",
                domain,
                fields,
                limit=20000,
                order="in_date desc"
            )
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

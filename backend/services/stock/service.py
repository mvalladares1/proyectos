"""
Servicio para gestión de Stock y Cámaras
Migrado del dashboard original de producción
OPTIMIZADO: Incluye caché para ubicaciones y productos

REFACTORIZADO: Constantes y helpers extraídos a módulos separados.
"""
from typing import List, Dict, Optional
from datetime import datetime

from shared.odoo_client import OdooClient
from backend.utils import clean_record
from backend.cache import get_cache, OdooCache

from .constants import UBICACIONES_ESPECIFICAS, VLK_PATRONES, CACHE_TTL_PRODUCTOS, CACHE_TTL_UBICACIONES
from .helpers import detect_fruit_type, detect_manejo, is_excluded_category


class StockService:
    """Servicio para operaciones de Stock y Cámaras"""

    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self._cache = get_cache()
    
    def move_pallet(self, pallet_code: str, location_dest_id: int) -> Dict:
        """
        Mueve un pallet a una ubicación destino.
        Lógica Dual:
        1. Si es Stock Real (Quant): Crea Transferencia Interna para TODOS los quants del paquete.
        2. Si es Pre-Recepción (Moving Line): Actualiza destino en TODAS las líneas de recepción abiertas del paquete.
        """
        
        # 0. Buscar el record del paquete (necesario para ambos casos)
        packages = self.odoo.search_read(
            "stock.quant.package", 
            [("name", "=", pallet_code)], 
            ["id", "name"]
        )
        
        if not packages:
            return {"success": False, "message": f"❌ Código {pallet_code} no encontrado en sistema (Package)."}
            
        package_id = packages[0]["id"]

        # 1. Buscar en Stock Real (Quants)
        quants = self.odoo.search_read(
            "stock.quant",
            [("package_id", "=", package_id), ("quantity", ">", 0)],
            ["location_id", "product_id", "quantity", "product_uom_id"]
        )
        
        if quants:
            # Agrupar quants por ubicación actual (en teoría deberían estar todos en la misma, pero por seguridad)
            locations_found = set(q["location_id"][0] for q in quants)
            
            # Si ya están en el destino, informar
            if len(locations_found) == 1 and list(locations_found)[0] == location_dest_id:
                return {"success": False, "message": f"El pallet ya está en la ubicación destino."}

            
            # Buscar picking type interno dinamicamente
            picking_type_id = 5 # Default
            picking_types = self.odoo.search_read(
                "stock.picking.type",
                [("code", "=", "internal"), ("warehouse_id", "!=", False)],
                ["id"],
                limit=1
            )
            if picking_types:
                picking_type_id = picking_types[0]["id"]
            
            # Buscar transportista ADMINISTRADOR
            carrier_id = None
            carriers = self.odoo.search_read(
                "res.partner",
                [("name", "=", "ADMINISTRADOR")],
                ["id"],
                limit=1
            )
            if carriers:
                carrier_id = carriers[0]["id"]
            
            # Crear un único Picking para todos los movimientos
            # Usamos la primera ubicación encontrada como origen del picking (lo más común)
            first_loc_id = quants[0]["location_id"][0]
            
            picking_vals = {
                "picking_type_id": picking_type_id,
                "location_id": first_loc_id,
                "location_dest_id": location_dest_id,
                "origin": f"Dashboard Move Multi: {pallet_code}",
                "move_type": "direct",
                "x_studio_es_transferencia_interna": True,  # Marcar como transferencia interna
            }
            
            # Agregar transportista si se encontró
            if carrier_id:
                picking_vals["x_studio_rut_transportista"] = carrier_id
            
            picking_id = self.odoo.execute("stock.picking", "create", picking_vals)
            
            # Crear un Stock Move por cada Quant
            for q in quants:
                move_vals = {
                    "name": f"Movimiento {pallet_code} - {q['product_id'][1]}",
                    "picking_id": picking_id,
                    "product_id": q["product_id"][0],
                    "product_uom_qty": q["quantity"],
                    "product_uom": q["product_uom_id"][0] if q.get("product_uom_id") else 1,
                    "location_id": q["location_id"][0],
                    "location_dest_id": location_dest_id
                }
                self.odoo.execute("stock.move", "create", move_vals)
            
            # Solo confirmar el Picking (NO asignar ni validar automáticamente)
            # El usuario debe ir a Odoo y hacer: Comprobar Disponibilidad -> Validar manualmente
            self.odoo.execute("stock.picking", "action_confirm", [picking_id])
            
            # Obtener el nombre de la transferencia creada
            picking_data = self.odoo.read("stock.picking", [picking_id], ["name"])
            picking_name = picking_data[0]["name"] if picking_data else f"ID {picking_id}"
            
            return {
                "success": True, 
                "message": f"✅ Transferencia {picking_name} creada para {pallet_code} ({len(quants)} items). Ir a Odoo para VALIDAR.",
                "picking_id": picking_id,
                "picking_name": picking_name,
                "type": "transfer"
            }

        # 2. Buscar en Pre-Recepción (Stock Entrante no validado)
        
        move_lines = self.odoo.search_read(
            "stock.move.line",
            [
                ("result_package_id", "=", package_id),
                ("state", "not in", ["done", "cancel"]),
                ("picking_id.picking_type_code", "=", "incoming")
            ],
            ["id", "picking_id", "location_dest_id"]
        )
        
        if move_lines:
            line_ids = [ml["id"] for ml in move_lines]
            picking_names = list(set(ml["picking_id"][1] for ml in move_lines))
            
            # Actualizar destino en TODAS las líneas
            self.odoo.execute(
                "stock.move.line", 
                "write", 
                line_ids,
                {"location_dest_id": location_dest_id}
            )
            
            res_msg = f"✅ Reasignado en {', '.join(picking_names)}: Destino cambiado para {len(line_ids)} líneas."
            return {
                "success": True,
                "message": res_msg,
                "type": "realloc"
            }
            
        return {"success": False, "message": f"❌ Pallet {pallet_code} no tiene quants activos ni recepciones pendientes."}
    
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
            p_data = self.odoo.read("product.product", list(product_ids), ["categ_id", "name", "x_studio_categora_tipo_de_manejo"])
            products_map = {p["id"]: p for p in p_data}
            self._cache.set(cache_key, products_map, ttl=CACHE_TTL_PRODUCTOS)
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
            self._cache.set(cache_key, locations, ttl=CACHE_TTL_UBICACIONES)
            return locations
        except Exception as e:
            print(f"Error fetching locations: {e}")
            return []

    def get_chambers_stock(self, fecha_desde: str = None, fecha_hasta: str = None) -> List[Dict]:
        """
        Obtiene stock agrupado por cámara padre (Camara 1, 2, 3 de -25°C, Camara 0°C de RF/Stock).
        Las posiciones individuales se agregan a su cámara padre.
        La capacidad se define manualmente o se cuenta por hijos.
        
        Args:
            fecha_desde: Fecha inicio para filtrar pallets (formato YYYY-MM-DD)
            fecha_hasta: Fecha fin para filtrar pallets (formato YYYY-MM-DD)
        """
        # Copia local de ubicaciones específicas para modificar
        ubicaciones_config = dict(UBICACIONES_ESPECIFICAS)
        
        try:
            # Buscar por IDs específicos
            ubicacion_ids = list(ubicaciones_config.keys())
            camaras_por_id = self.odoo.search_read(
                "stock.location",
                [
                    ("id", "in", ubicacion_ids),
                    ("usage", "=", "internal"),
                    ("active", "=", True)
                ],
                ["id", "name", "display_name", "location_id"]
            )
            
            # Buscar cámaras VLK adicionales por nombre
            camaras_vlk_extra = []
            for vlk in VLK_PATRONES:
                found = self.odoo.search_read(
                    "stock.location",
                    [
                        ("display_name", "ilike", f"%VLK%{vlk['patron']}%"),
                        ("usage", "=", "internal"),
                        ("active", "=", True)
                    ],
                    ["id", "name", "display_name", "location_id"],
                    limit=1
                )
                if found:
                    # Agregar capacidad al config
                    ubicaciones_config[found[0]["id"]] = {
                        "nombre": found[0]["display_name"],
                        "capacidad": vlk["capacidad"]
                    }
                    camaras_vlk_extra.extend(found)
            
            # Combinar resultados
            camaras_encontradas = camaras_por_id + camaras_vlk_extra
            
        except Exception as e:
            print(f"Error buscando cámaras: {e}")
            import traceback
            traceback.print_exc()
            return []

        # Crear mapa de cámaras directamente desde las ubicaciones encontradas
        camaras_map = {}
        
        for cam in camaras_encontradas:
            cam_id = cam.get("id")
            name = cam.get("name", "")
            display_name = cam.get("display_name", "")
            parent = cam.get("location_id")
            
            # Obtener configuración específica para esta ubicación
            config = ubicaciones_config.get(cam_id, {"capacidad": 100})
            
            camaras_map[cam_id] = {
                "id": cam_id,
                "name": name,
                "full_name": display_name,
                "parent_name": parent[1] if parent and isinstance(parent, (list, tuple)) else "",
                "capacity_pallets": config.get("capacidad", 100),
                "occupied_pallets": 0,
                "stock_data": {},
                "child_location_ids": []
            }

        if not camaras_map:
            return []

        # PASO 2: Para cada cámara, obtener todas sus ubicaciones hijas
        for cam_id in camaras_map.keys():
            try:
                child_locs = self.odoo.search(
                    "stock.location",
                    [
                        ("location_id", "child_of", cam_id),
                        ("usage", "=", "internal"),
                        ("active", "=", True)
                    ]
                )
                camaras_map[cam_id]["child_location_ids"] = child_locs
                camaras_map[cam_id]["capacity_pallets"] = len(child_locs)  # Capacidad = posiciones
            except Exception as e:
                print(f"Error obteniendo hijos de cámara {cam_id}: {e}")
                camaras_map[cam_id]["child_location_ids"] = [cam_id]
                camaras_map[cam_id]["capacity_pallets"] = 1

        # Crear mapa inverso: location_id -> chamber_id
        loc_to_chamber = {}
        for cam_id, cam_data in camaras_map.items():
            for loc_id in cam_data["child_location_ids"]:
                loc_to_chamber[loc_id] = cam_id

        # PASO 3: Obtener todos los quants de las ubicaciones hijas
        all_child_locs = list(loc_to_chamber.keys())
        if not all_child_locs:
            return list(camaras_map.values())

        # Construir domain con filtros de fecha
        quants_domain = [
            ("location_id", "in", all_child_locs),
            ("quantity", ">", 0)
        ]
        
        # Agregar filtros de fecha si se especifican
        if fecha_desde:
            quants_domain.append(("in_date", ">=", fecha_desde))
        if fecha_hasta:
            quants_domain.append(("in_date", "<=", f"{fecha_hasta} 23:59:59"))

        try:
            quants = self.odoo.search_read(
                "stock.quant",
                quants_domain,
                ["location_id", "product_id", "quantity", "package_id", "in_date"],
                limit=50000
            )
        except Exception as e:
            print(f"Error fetching quants: {e}")
            return list(camaras_map.values())

        # Contar pallets por cámara
        for q in quants:
            loc = q.get("location_id")
            pkg = q.get("package_id")
            if loc and isinstance(loc, (list, tuple)):
                loc_id = loc[0]
                cam_id = loc_to_chamber.get(loc_id)
                if cam_id and pkg and isinstance(pkg, (list, tuple)):
                    # Usar un set temporal para contar pallets únicos
                    if "pallet_set" not in camaras_map[cam_id]:
                        camaras_map[cam_id]["pallet_set"] = set()
                    camaras_map[cam_id]["pallet_set"].add(pkg[0])

        # Actualizar conteo de pallets ocupados
        for cam_id in camaras_map:
            if "pallet_set" in camaras_map[cam_id]:
                camaras_map[cam_id]["occupied_pallets"] = len(camaras_map[cam_id]["pallet_set"])
                del camaras_map[cam_id]["pallet_set"]

        # PASO 4: Obtener info de productos
        product_ids = {
            q["product_id"][0]
            for q in quants
            if q.get("product_id") and isinstance(q["product_id"], (list, tuple))
        }
        
        products_raw = self._get_products_cached(list(product_ids))
        products_info = {}
        for pid, p in products_raw.items():
            cat = p.get("categ_id")
            manejo_raw = p.get("x_studio_categora_tipo_de_manejo", "")
            manejo = detect_manejo(manejo_raw)
            products_info[pid] = {
                "category": cat[1] if cat and isinstance(cat, (list, tuple)) else "Sin Categoria",
                "name": p.get("name", ""),
                "manejo": manejo
            }

        # PASO 5: Agregar stock por cámara y tipo fruta/manejo
        for q in quants:
            loc = q.get("location_id")
            prod = q.get("product_id")
            if not loc or not prod:
                continue
            if not isinstance(loc, (list, tuple)) or not isinstance(prod, (list, tuple)):
                continue
            
            loc_id = loc[0]
            cam_id = loc_to_chamber.get(loc_id)
            if not cam_id or cam_id not in camaras_map:
                continue

            qty = q.get("quantity", 0) or 0
            p_info = products_info.get(prod[0])
            
            if p_info:
                cat_name = p_info["category"]
                prod_name = p_info["name"]
                
                # Excluir categorías que no son productos de fruta
                if is_excluded_category(cat_name):
                    continue
                
                # Detectar Tipo Fruta usando helper
                tipo_fruta = detect_fruit_type(prod_name, cat_name)
                manejo = p_info.get("manejo", "Convencional")
            else:
                tipo_fruta = "Desconocido"
                manejo = "N/A"

            key = f"{tipo_fruta} - {manejo}"
            camaras_map[cam_id]["stock_data"][key] = camaras_map[cam_id]["stock_data"].get(key, 0) + qty

        # Retornar solo cámaras con stock (o todas si se requiere)
        return list(camaras_map.values())

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
            ("quantity", ">", 0)
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
            p_data = self.odoo.read("product.product", list(product_ids), ["categ_id", "name", "x_studio_categora_tipo_de_manejo"])
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
            
            # Excluir categorías que no son productos de fruta
            if is_excluded_category(cat_name):
                continue
            
            # Detectar Tipo Fruta usando helper
            tipo_fruta = detect_fruit_type(prod_name, cat_name)
            
            # Obtener Manejo del campo x_studio_categora_tipo_de_manejo
            manejo_raw = p_info.get("x_studio_categora_tipo_de_manejo", "")
            manejo = detect_manejo(manejo_raw)
            
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
                p_data = self.odoo.read("product.product", list(product_ids), ["categ_id", "name", "x_studio_categora_tipo_de_manejo"])
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
            
            # Excluir categorías que no son productos de fruta
            if is_excluded_category(p_cat):
                continue
            
            # Detectar Tipo Fruta usando helper
            tipo_fruta = detect_fruit_type(p_name, p_cat)
            
            # Obtener Manejo del campo x_studio_categora_tipo_de_manejo
            manejo_raw = p_info.get("x_studio_categora_tipo_de_manejo", "")
            manejo = detect_manejo(manejo_raw)
            
            p_species_condition = f"{tipo_fruta} - {manejo}"
            
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
                    "category": tipo_fruta,
                    "condition": manejo,
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

    def get_pallet_info(self, pallet_code: str) -> Dict:
        """
        Obtiene información detallada de un pallet/tarja para validación.
        Retorna ubicación actual, productos, cantidades y estado.
        """
        # Buscar el paquete
        packages = self.odoo.search_read(
            "stock.quant.package", 
            [("name", "=", pallet_code)], 
            ["id", "name"]
        )
        
        if not packages:
            return {"found": False, "message": f"Pallet '{pallet_code}' no encontrado en el sistema"}
        
        package_id = packages[0]["id"]
        
        # 1. Buscar en Stock Real (Quants)
        quants = self.odoo.search_read(
            "stock.quant",
            [("package_id", "=", package_id), ("quantity", ">", 0)],
            ["location_id", "product_id", "quantity", "lot_id", "in_date"]
        )
        
        if quants:
            # Pallet está en inventario
            location = quants[0]["location_id"]
            products = []
            total_qty = 0
            
            for q in quants:
                if q.get("product_id"):
                    products.append({
                        "name": q["product_id"][1],
                        "quantity": q["quantity"],
                        "lot": q["lot_id"][1] if q.get("lot_id") else "N/A"
                    })
                    total_qty += q["quantity"]
            
            return {
                "found": True,
                "status": "in_stock",
                "pallet_code": pallet_code,
                "location_id": location[0],
                "location_name": location[1],
                "products": products,
                "total_quantity": total_qty,
                "items_count": len(quants)
            }
        
        # 2. Buscar en Pre-Recepción (Stock Entrante no validado)
        move_lines = self.odoo.search_read(
            "stock.move.line",
            [
                ("result_package_id", "=", package_id),
                ("state", "not in", ["done", "cancel"])
            ],
            ["picking_id", "location_dest_id", "product_id", "qty_done", "lot_id"]
        )
        
        if move_lines:
            picking = move_lines[0].get("picking_id", [None, ""])
            location = move_lines[0].get("location_dest_id", [None, ""])
            products = []
            total_qty = 0
            
            for ml in move_lines:
                if ml.get("product_id"):
                    products.append({
                        "name": ml["product_id"][1],
                        "quantity": ml.get("qty_done", 0),
                        "lot": ml["lot_id"][1] if ml.get("lot_id") else "N/A"
                    })
                    total_qty += ml.get("qty_done", 0)
            
            return {
                "found": True,
                "status": "in_reception",
                "pallet_code": pallet_code,
                "picking_name": picking[1] if picking else "N/A",
                "location_dest_name": location[1] if location else "N/A",
                "products": products,
                "total_quantity": total_qty,
                "items_count": len(move_lines)
            }
        
        return {
            "found": True,
            "status": "empty",
            "pallet_code": pallet_code,
            "message": "Pallet existe pero no tiene stock ni recepciones pendientes"
        }

    def get_ubicacion_by_barcode(self, barcode: str) -> Dict:
        """
        Busca una ubicación por su código de barras.
        Retorna información básica de la ubicación encontrada.
        """
        try:
            locations = self.odoo.search_read(
                "stock.location",
                [
                    "|",
                    ("barcode", "=", barcode),
                    ("name", "=", barcode),
                    ("usage", "=", "internal"),
                    ("active", "=", True)
                ],
                ["id", "name", "display_name", "barcode"],
                limit=1
            )
            
            if not locations:
                return {"found": False, "message": f"Ubicación '{barcode}' no encontrada"}
            
            loc = locations[0]
            return {
                "found": True,
                "id": loc["id"],
                "name": loc["name"],
                "display_name": loc["display_name"],
                "barcode": loc.get("barcode", "")
            }
        except Exception as e:
            return {"found": False, "message": f"Error buscando ubicación: {e}"}

    def move_multiple_pallets(self, pallet_codes: List[str], location_dest_id: int, usuario_id: int = None) -> Dict:
        """
        Mueve múltiples pallets a una ubicación destino usando movimiento DIRECTO.
        NO crea transferencias internas - actualiza quants directamente.
        Registra cada movimiento en x_trasferencias_dashboard_v2.
        
        Args:
            pallet_codes: Lista de códigos de paquetes a mover
            location_dest_id: ID de ubicación destino
            usuario_id: ID del usuario que ejecuta el movimiento (para el log)
            
        Returns:
            Dict con resumen de éxitos y errores
        """
        results = {
            "success_count": 0,
            "error_count": 0,
            "details": [],
            "total_kg": 0.0
        }
        
        # ============================================================
        # VALIDACIONES GLOBALES (previas al loop)
        # ============================================================
        
        # 1. Validar que la ubicación destino existe y es válida
        try:
            location_dest = self.odoo.search_read(
                "stock.location",
                [("id", "=", location_dest_id)],
                ["id", "name", "usage", "active"],
                limit=1
            )
            
            if not location_dest:
                return {
                    "success_count": 0,
                    "error_count": len(pallet_codes),
                    "details": [{"pallet": code, "success": False, "message": "❌ Ubicación destino no existe"} for code in pallet_codes],
                    "total_kg": 0.0,
                    "global_error": "Ubicación destino inválida"
                }
            
            # 2. Validar que la ubicación destino NO sea virtual/temporal
            if location_dest[0]["usage"] not in ["internal", "view"]:
                return {
                    "success_count": 0,
                    "error_count": len(pallet_codes),
                    "details": [{"pallet": code, "success": False, "message": f"❌ No se puede mover a ubicación tipo '{location_dest[0]['usage']}'"} for code in pallet_codes],
                    "total_kg": 0.0,
                    "global_error": f"Ubicación destino es de tipo '{location_dest[0]['usage']}' (debe ser 'internal' o 'view')"
                }
            
            # 3. Validar que la ubicación esté activa
            if not location_dest[0].get("active", True):
                return {
                    "success_count": 0,
                    "error_count": len(pallet_codes),
                    "details": [{"pallet": code, "success": False, "message": "❌ Ubicación destino desactivada"} for code in pallet_codes],
                    "total_kg": 0.0,
                    "global_error": "Ubicación destino está desactivada"
                }
                
        except Exception as e:
            return {
                "success_count": 0,
                "error_count": len(pallet_codes),
                "details": [{"pallet": code, "success": False, "message": f"❌ Error validando destino: {str(e)}"} for code in pallet_codes],
                "total_kg": 0.0,
                "global_error": f"Error al validar ubicación destino: {str(e)}"
            }
        
        # ============================================================
        # PROCESAMIENTO POR PALLET
        # ============================================================
        
        for code in pallet_codes:
            try:
                # 1. Buscar el paquete
                packages = self.odoo.search_read(
                    "stock.quant.package", 
                    [("name", "=", code)], 
                    ["id", "name"]
                )
                
                if not packages:
                    results["error_count"] += 1
                    results["details"].append({
                        "pallet": code,
                        "success": False,
                        "message": f"❌ Paquete no encontrado"
                    })
                    continue
                
                package_id = packages[0]["id"]
                
                # 2. Buscar quants del paquete (STOCK REAL)
                quants = self.odoo.search_read(
                    "stock.quant",
                    [("package_id", "=", package_id), ("quantity", ">", 0)],
                    ["id", "location_id", "product_id", "lot_id", "quantity", "reserved_quantity"]
                )
                
                # ============================================================
                # CASO A: PALLET EN STOCK REAL (tiene quants)
                # ============================================================
                if quants:
                reserved = [q for q in quants if q.get("reserved_quantity", 0) > 0]
                if reserved:
                    total_reserved = sum(q.get("reserved_quantity", 0) for q in reserved)
                    results["error_count"] += 1
                    results["details"].append({
                        "pallet": code,
                        "success": False,
                        "message": f"❌ Tiene {len(reserved)} quants con {total_reserved:.2f} kg reservados - liberar primero en Odoo"
                    })
                    continue
                
                # 4. VALIDACIÓN: Verificar que todos los quants estén en la MISMA ubicación origen
                unique_locations = set(q["location_id"][0] for q in quants)
                if len(unique_locations) > 1:
                    location_names = ", ".join([q["location_id"][1] for q in quants[:3]])  # Mostrar primeras 3
                    results["error_count"] += 1
                    results["details"].append({
                        "pallet": code,
                        "success": False,
                        "message": f"❌ Quants en {len(unique_locations)} ubicaciones diferentes ({location_names}...) - inconsistencia de datos"
                    })
                    continue
                
                location_orig_id = quants[0]["location_id"][0]
                location_orig_name = quants[0]["location_id"][1]
                
                # 5. VALIDACIÓN: Verificar que origen sea ubicación interna
                try:
                    origin_location = self.odoo.search_read(
                        "stock.location",
                        [("id", "=", location_orig_id)],
                        ["usage"],
                        limit=1
                    )
                    
                    if origin_location and origin_location[0]["usage"] not in ["internal", "view"]:
                        results["error_count"] += 1
                        results["details"].append({
                            "pallet": code,
                            "success": False,
                            "message": f"❌ Origen es tipo '{origin_location[0]['usage']}' (no movible directamente)"
                        })
                        continue
                except:
                    pass  # Si falla, continuar (no bloquear por esto)
                
                # 6. VALIDACIÓN: Verificar que origen y destino sean diferentes
                if location_orig_id == location_dest_id:
                    results["error_count"] += 1
                    results["details"].append({
                        "pallet": code,
                        "success": False,
                        "message": f"⚠️ Ya está en {location_orig_name}"
                    })
                    continue
                
                # 7. MOVIMIENTO DIRECTO (con rollback en caso de error)
                total_kg = 0.0
                detalles_productos = []
                quants_moved = []  # Para rollback si falla
                
                try:
                    for quant in quants:
                        # Guardar estado previo para posible rollback
                        quants_moved.append({
                            "id": quant["id"],
                            "original_location": location_orig_id
                        })
                        
                        # Actualizar ubicación del quant
                        self.odoo.execute("stock.quant", "write", [quant["id"]], {
                            "location_id": location_dest_id
                        })
                        
                        total_kg += quant["quantity"]
                        
                        # Guardar detalle para el log
                        producto = quant["product_id"][1] if quant.get("product_id") else "Sin producto"
                        lote = quant["lot_id"][1] if quant.get("lot_id") else "Sin lote"
                        detalles_productos.append(f"- {producto} / {lote}: {quant['quantity']} kg")
                        
                except Exception as move_error:
                    # ROLLBACK: Revertir todos los quants ya movidos
                    for qm in quants_moved:
                        try:
                            self.odoo.execute("stock.quant", "write", [qm["id"]], {
                                "location_id": qm["original_location"]
                            })
                        except:
                            pass  # Si falla el rollback, al menos lo intentamos
                    
                    results["error_count"] += 1
                    results["details"].append({
                        "pallet": code,
                        "success": False,
                        "message": f"❌ Error al mover quants (revertido): {str(move_error)}"
                    })
                    continue
                
                # 8. Registrar en log de transferencias (NO debe fallar el movimiento si esto falla)
                try:
                    # Validar que el modelo de log existe
                    log_model_exists = self.odoo.search_read(
                        "ir.model",
                        [("model", "=", "x_trasferencias_dashboard_v2")],
                        ["id"],
                        limit=1
                    )
                    
                    if not log_model_exists:
                        print(f"⚠️ Modelo de log no existe - movimiento exitoso pero sin registro")
                    else:
                        log_vals = {
                            "x_name": f"MOV-{code}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                            "x_fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "x_paquete_id": package_id,
                            "x_ubicacion_origen_id": location_orig_id,
                            "x_ubicacion_destino_id": location_dest_id,
                            "x_usuario_id": usuario_id if usuario_id else False,
                            "x_total_kg": total_kg,
                            "x_cantidad_quants": len(quants),
                            "x_detalles": "\n".join(detalles_productos),
                            "x_estado": "completado",
                            "x_origen_sistema": "dashboard"
                        }
                        
                        self.odoo.execute("x_trasferencias_dashboard_v2", "create", log_vals)
                        
                except Exception as log_error:
                    # No fallar el movimiento si el log falla - solo advertir
                    print(f"⚠️ Error al registrar log para {code}: {log_error}")
                    # El movimiento continúa siendo exitoso
                
                # 9. Éxito
                results["success_count"] += 1
                results["total_kg"] += total_kg
                
                # Obtener nombre de ubicación destino para mensaje más claro
                location_dest_name = location_dest[0]["name"] if location_dest else f"ID {location_dest_id}"
                
                results["details"].append({
                    "pallet": code,
                    "success": True,
                    "message": f"✅ {len(quants)} quants ({total_kg:.2f} kg) → {location_dest_name}",
                    "kg": total_kg,
                    "quants_count": len(quants),
                    "from": location_orig_name,
                    "to": location_dest_name
                })
                
                # ============================================================
                # CASO B: PALLET EN PRE-RECEPCIÓN (sin quants, buscar en recepciones)
                # ============================================================
                else:
                    # Buscar en Stock Entrante no validado (recepciones pendientes)
                    move_lines = self.odoo.search_read(
                        "stock.move.line",
                        [
                            ("result_package_id", "=", package_id),
                            ("state", "not in", ["done", "cancel"]),
                            ("picking_id.picking_type_code", "=", "incoming")
                        ],
                        ["id", "picking_id", "location_dest_id", "product_id", "lot_id", "qty_done"]
                    )
                    
                    if not move_lines:
                        results["error_count"] += 1
                        results["details"].append({
                            "pallet": code,
                            "success": False,
                            "message": f"❌ Sin stock disponible y sin recepciones pendientes"
                        })
                        continue
                    
                    # Actualizar destino en TODAS las líneas de recepción
                    try:
                        line_ids = [ml["id"] for ml in move_lines]
                        picking_names = list(set(ml["picking_id"][1] for ml in move_lines))
                        
                        self.odoo.execute(
                            "stock.move.line", 
                            "write", 
                            line_ids,
                            {"location_dest_id": location_dest_id}
                        )
                        
                        # Calcular KG (qty_done es la cantidad que se está recibiendo)
                        total_kg = sum(ml.get("qty_done", 0) for ml in move_lines)
                        
                        # Detalles para el log
                        detalles_productos = []
                        for ml in move_lines:
                            producto = ml["product_id"][1] if ml.get("product_id") else "Sin producto"
                            lote = ml["lot_id"][1] if ml.get("lot_id") else "Sin lote"
                            qty = ml.get("qty_done", 0)
                            if qty > 0:
                                detalles_productos.append(f"- {producto} / {lote}: {qty} kg")
                        
                        # Registrar en log
                        try:
                            log_vals = {
                                "x_name": f"MOV-REC-{code}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                "x_fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "x_paquete_id": package_id,
                                "x_ubicacion_origen_id": False,  # No tiene origen definido aún (está en recepción)
                                "x_ubicacion_destino_id": location_dest_id,
                                "x_usuario_id": usuario_id if usuario_id else False,
                                "x_total_kg": total_kg,
                                "x_cantidad_quants": len(move_lines),
                                "x_detalles": f"RECEPCIÓN: {', '.join(picking_names)}\n" + "\n".join(detalles_productos),
                                "x_estado": "completado",
                                "x_origen_sistema": "dashboard"
                            }
                            
                            self.odoo.execute("x_trasferencias_dashboard_v2", "create", log_vals)
                        except Exception as log_error:
                            print(f"⚠️ Error al registrar log para recepción {code}: {log_error}")
                        
                        # Éxito
                        results["success_count"] += 1
                        results["total_kg"] += total_kg
                        
                        location_dest_name = location_dest[0]["name"] if location_dest else f"ID {location_dest_id}"
                        
                        results["details"].append({
                            "pallet": code,
                            "success": True,
                            "message": f"✅ Recepción: {len(move_lines)} líneas ({total_kg:.2f} kg) → {location_dest_name} [{', '.join(picking_names)}]",
                            "kg": total_kg,
                            "lines_count": len(move_lines),
                            "type": "reception",
                            "pickings": picking_names,
                            "to": location_dest_name
                        })
                        
                    except Exception as reception_error:
                        results["error_count"] += 1
                        results["details"].append({
                            "pallet": code,
                            "success": False,
                            "message": f"❌ Error al actualizar recepción: {str(reception_error)}"
                        })
                        continue
                
            except Exception as e:
                # Error inesperado en el procesamiento del pallet
                results["error_count"] += 1
                results["details"].append({
                    "pallet": code,
                    "success": False,
                    "message": f"❌ Error inesperado: {str(e)}"
                })
        
        return results

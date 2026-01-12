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
    
    def move_pallet(self, pallet_code: str, location_dest_id: int) -> Dict:
        """
        Mueve un pallet a una ubicación destino con validaciones completas.
        Lógica Dual:
        1. Si es Stock Real (Quant): Crea Transferencia Interna para TODOS los quants del paquete.
        2. Si es Pre-Recepción (Moving Line): Actualiza destino en TODAS las líneas de recepción abiertas del paquete.
        
        Validaciones implementadas:
        - Ubicación destino válida (existe, activa, tipo interno)
        - Stock mínimo (excepto recepciones pendientes)
        - Movimientos pendientes (excepto recepciones pendientes)
        - Bloqueos/Cuarentena
        """
        
        # VALIDACIÓN 1: Verificar que ubicación destino existe y es válida
        dest_locations = self.odoo.search_read(
            "stock.location",
            [("id", "=", location_dest_id)],
            ["id", "name", "usage", "active"]
        )
        
        if not dest_locations:
            return {"success": False, "message": f"❌ Ubicación destino no existe (ID: {location_dest_id})"}
        
        dest_location = dest_locations[0]
        
        if not dest_location.get("active", True):
            return {"success": False, "message": f"❌ Ubicación destino está inactiva: {dest_location['name']}"}
        
        if dest_location.get("usage") != "internal":
            return {"success": False, "message": f"❌ Solo se permiten ubicaciones internas. Tipo: {dest_location.get('usage')}"}
        
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
            ["location_id", "product_id", "quantity", "product_uom_id", "lot_id"]
        )
        
        if quants:
            # VALIDACIÓN 2: Stock mínimo (solo para stock real, no recepciones)
            total_quantity = sum(q["quantity"] for q in quants)
            if total_quantity <= 0:
                return {"success": False, "message": f"❌ Pallet sin stock disponible (cantidad: {total_quantity})"}
            
            # VALIDACIÓN 3: Verificar bloqueos/cuarentena en lotes
            # Obtener todos los lotes de los quants
            lot_ids = [q["lot_id"][0] for q in quants if q.get("lot_id")]
            if lot_ids:
                lots = self.odoo.search_read(
                    "stock.lot",
                    [("id", "in", lot_ids)],
                    ["id", "name", "x_studio_estado_calidad", "x_studio_bloqueado"]
                )
                
                for lot in lots:
                    # Verificar si está bloqueado
                    if lot.get("x_studio_bloqueado"):
                        return {"success": False, "message": f"🚫 Lote {lot['name']} está bloqueado"}
                    
                    # Verificar estado de calidad (cuarentena)
                    estado_calidad = lot.get("x_studio_estado_calidad", "").lower()
                    if estado_calidad in ["cuarentena", "rechazado", "bloqueado"]:
                        return {"success": False, "message": f"🚫 Lote {lot['name']} en {estado_calidad}"}
            
            # VALIDACIÓN 4: Verificar movimientos pendientes (excepto recepciones)
            # Buscar pickings en estado draft/waiting/confirmed/assigned que NO sean recepciones
            pending_moves = self.odoo.search_read(
                "stock.move",
                [
                    ("product_id", "in", [q["product_id"][0] for q in quants]),
                    ("state", "in", ["draft", "waiting", "confirmed", "assigned"]),
                    ("picking_id.picking_type_code", "!=", "incoming")  # Excluir recepciones
                ],
                ["id", "picking_id", "product_id", "state"]
            )
            
            if pending_moves:
                # Verificar si alguno de estos movimientos involucra el mismo paquete
                for move in pending_moves:
                    move_lines = self.odoo.search_read(
                        "stock.move.line",
                        [
                            ("move_id", "=", move["id"]),
                            "|",
                            ("package_id", "=", package_id),
                            ("result_package_id", "=", package_id)
                        ],
                        ["id", "picking_id"]
                    )
                    
                    if move_lines:
                        picking_name = move_lines[0]["picking_id"][1] if move_lines[0].get("picking_id") else "Desconocido"
                        return {"success": False, "message": f"⚠️ Pallet tiene movimiento pendiente en: {picking_name}"}
            
            # Agrupar quants por ubicación actual
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
            
            # Crear un único Picking para todos los movimientos
            # Usamos la primera ubicación encontrada como origen del picking
            first_loc_id = quants[0]["location_id"][0]
            
            picking_vals = {
                "picking_type_id": picking_type_id,
                "location_id": first_loc_id,
                "location_dest_id": location_dest_id,
                "origin": f"Dashboard Move Multi: {pallet_code}",
                "move_type": "direct"
            }
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
            
            # Confirmar y Asignar Picking
            self.odoo.execute("stock.picking", "action_confirm", [picking_id])
            self.odoo.execute("stock.picking", "action_assign", [picking_id])
            
            # Buscar las move lines creadas y asignar package y qty_done
            # NOTA: En Odoo 16, stock.move.line usa reserved_uom_qty, no product_uom_qty
            m_lines = self.odoo.search_read(
                "stock.move.line",
                [("picking_id", "=", picking_id)],
                ["id", "product_id", "reserved_uom_qty"]
            )
            
            for ml in m_lines:
                # Intentar matchear con el quant original por producto (simplificado)
                # En un flujo directo, la qty_done suele ser igual a la reserved_uom_qty
                self.odoo.execute(
                    "stock.move.line", 
                    "write", 
                    [ml["id"]],
                    {
                        "package_id": package_id, 
                        "result_package_id": package_id, 
                        "qty_done": ml["reserved_uom_qty"]
                    }
                )
            
            # Validar Picking
            self.odoo.execute("stock.picking", "button_validate", [picking_id])
            
            return {
                "success": True, 
                "message": f"✅ Transferencia Realizada: {pallet_code} ({len(quants)} items) movido a destino.",
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

    def get_chambers_stock(self, fecha_desde: str = None, fecha_hasta: str = None) -> List[Dict]:
        """
        Obtiene stock agrupado por cámara padre (Camara 1, 2, 3 de -25°C, Camara 0°C de RF/Stock).
        Las posiciones individuales se agregan a su cámara padre.
        La capacidad se define manualmente o se cuenta por hijos.
        
        Args:
            fecha_desde: Fecha inicio para filtrar pallets (formato YYYY-MM-DD)
            fecha_hasta: Fecha fin para filtrar pallets (formato YYYY-MM-DD)
        """
        # PASO 1: Configuración de ubicaciones específicas a mostrar
        # Incluye cámaras RF y VLK
        UBICACIONES_ESPECIFICAS = {
            # RF/Stock
            5452: {"nombre": "Camara 0°C REAL", "capacidad": 200},
            8474: {"nombre": "Inventario Real", "capacidad": 500},
            # VLK - cámaras conocidas
            8528: {"nombre": "VLK/Camara 0°", "capacidad": 200},
            8497: {"nombre": "VLK/Stock", "capacidad": 500},
        }
        
        # Patrones para buscar cámaras VLK adicionales por nombre
        VLK_PATRONES = [
            {"patron": "Camara 1 -25", "capacidad": 200},
            {"patron": "Camara 2 -25", "capacidad": 200},
        ]
        
        try:
            # Buscar por IDs específicos
            ubicacion_ids = list(UBICACIONES_ESPECIFICAS.keys())
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
                    UBICACIONES_ESPECIFICAS[found[0]["id"]] = {
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
            config = UBICACIONES_ESPECIFICAS.get(cam_id, {"capacidad": 100})
            
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
            print(f"  OK: {name} (ID={cam_id}, cap={config.get('capacidad')})")

        if not camaras_map:
            print("No se encontraron ubicaciones específicas")
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
                print(f"  {camaras_map[cam_id]['name']}: {len(child_locs)} posiciones hijas")
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
            # El campo puede ser "Convencional", "Orgánico" o False/None
            if manejo_raw and isinstance(manejo_raw, str):
                manejo = "Orgánico" if "org" in manejo_raw.lower() else "Convencional"
            else:
                manejo = "Convencional"
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
                cat_name = p_info["category"].upper()
                prod_name = p_info["name"].upper()
                
                # Excluir categorías que no son productos de fruta
                CATEGORIAS_EXCLUIDAS = [
                    "INVENTARIABLES", "BANDEJAS", "ACTIVO", "SERVICIOS",
                    "EQUIPOS", "MUEBLES", "EJEMPLODS", "OTROS", "ALL1"
                ]
                if any(excl in cat_name for excl in CATEGORIAS_EXCLUIDAS):
                    continue
                
                # Detectar Tipo Fruta (orden importante: más específico primero)
                tipo_fruta = "Otro"
                
                # Primero buscar por código de producto (AR, FB, FR, FT, MO, CR, MIX)
                if " AR " in f" {prod_name} " or "AR_" in prod_name or prod_name.startswith("AR ") or "ARANDANO" in prod_name or "ARÁNDANO" in prod_name or "ARANDANO" in cat_name:
                    tipo_fruta = "Arándano"
                elif " FB " in f" {prod_name} " or "FB_" in prod_name or prod_name.startswith("FB ") or "FRAMBUESA" in prod_name or "FRAMBUESA" in cat_name:
                    tipo_fruta = "Frambuesa"
                elif " FR " in f" {prod_name} " or "FR_" in prod_name or prod_name.startswith("FR ") or " FT " in f" {prod_name} " or "FT_" in prod_name or prod_name.startswith("FT ") or "FRUTILLA" in prod_name or "FRUTILLA" in cat_name:
                    tipo_fruta = "Frutilla"
                elif " MO " in f" {prod_name} " or "MO_" in prod_name or prod_name.startswith("MO ") or "MORA" in prod_name or "MORA" in cat_name:
                    tipo_fruta = "Mora"
                elif " CR " in f" {prod_name} " or "CR_" in prod_name or prod_name.startswith("CR ") or "CEREZA" in prod_name or "CEREZA" in cat_name:
                    tipo_fruta = "Cereza"
                elif "MIX" in prod_name or "MIXED" in prod_name or "CREATIVE" in prod_name:
                    tipo_fruta = "Mix"
                
                # Usar el manejo del campo x_studio_categora_tipo_de_manejo
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
            # Ya no filtramos por package_id para mostrar todo el stock
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
            prod_upper = prod_name.upper()
            cat_upper = cat_name.upper()
            
            # Excluir categorías que no son productos de fruta
            CATEGORIAS_EXCLUIDAS = [
                "INVENTARIABLES", "BANDEJAS", "ACTIVO", "SERVICIOS",
                "EQUIPOS", "MUEBLES", "EJEMPLODS", "OTROS", "ALL1"
            ]
            if any(excl in cat_upper for excl in CATEGORIAS_EXCLUIDAS):
                continue
            
            # Detectar Tipo Fruta
            tipo_fruta = "Otro"
            if " AR " in f" {prod_upper} " or "AR_" in prod_upper or prod_upper.startswith("AR ") or "ARANDANO" in prod_upper or "ARÁNDANO" in prod_upper or "ARANDANO" in cat_upper:
                tipo_fruta = "Arándano"
            elif " FB " in f" {prod_upper} " or "FB_" in prod_upper or prod_upper.startswith("FB ") or "FRAMBUESA" in prod_upper or "FRAMBUESA" in cat_upper:
                tipo_fruta = "Frambuesa"
            elif " FR " in f" {prod_upper} " or "FR_" in prod_upper or prod_upper.startswith("FR ") or " FT " in f" {prod_upper} " or "FT_" in prod_upper or prod_upper.startswith("FT ") or "FRUTILLA" in prod_upper or "FRUTILLA" in cat_upper:
                tipo_fruta = "Frutilla"
            elif " MO " in f" {prod_upper} " or "MO_" in prod_upper or prod_upper.startswith("MO ") or "MORA" in prod_upper or "MORA" in cat_upper:
                tipo_fruta = "Mora"
            elif " CR " in f" {prod_upper} " or "CR_" in prod_upper or prod_upper.startswith("CR ") or "CEREZA" in prod_upper or "CEREZA" in cat_upper:
                tipo_fruta = "Cereza"
            elif "MIX" in prod_upper or "MIXED" in prod_upper or "CREATIVE" in prod_upper:
                tipo_fruta = "Mix"
            
            # Obtener Manejo del campo x_studio_categora_tipo_de_manejo
            manejo_raw = p_info.get("x_studio_categora_tipo_de_manejo", "")
            if manejo_raw and isinstance(manejo_raw, str):
                manejo = "Orgánico" if "org" in manejo_raw.lower() else "Convencional"
            else:
                manejo = "Convencional"
            
            tipo_fruta_manejo = f"{tipo_fruta} - {manejo}"
            
            # NOTA: Ya no excluimos "Otro" para poder ver qué productos hay
            # Si necesitas excluir ciertos productos específicos, agrégalos aquí
            
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
            prod_upper = p_name.upper()
            cat_upper = p_cat.upper()
            
            # Excluir categorías que no son productos de fruta
            CATEGORIAS_EXCLUIDAS = [
                "INVENTARIABLES", "BANDEJAS", "ACTIVO", "SERVICIOS",
                "EQUIPOS", "MUEBLES", "EJEMPLODS", "OTROS", "ALL1"
            ]
            if any(excl in cat_upper for excl in CATEGORIAS_EXCLUIDAS):
                continue
            
            # Detectar Tipo Fruta (misma lógica que get_pallets)
            tipo_fruta = "Otro"
            if " AR " in f" {prod_upper} " or "AR_" in prod_upper or prod_upper.startswith("AR ") or "ARANDANO" in prod_upper or "ARÁNDANO" in prod_upper or "ARANDANO" in cat_upper:
                tipo_fruta = "Arándano"
            elif " FB " in f" {prod_upper} " or "FB_" in prod_upper or prod_upper.startswith("FB ") or "FRAMBUESA" in prod_upper or "FRAMBUESA" in cat_upper:
                tipo_fruta = "Frambuesa"
            elif " FR " in f" {prod_upper} " or "FR_" in prod_upper or prod_upper.startswith("FR ") or " FT " in f" {prod_upper} " or "FT_" in prod_upper or prod_upper.startswith("FT ") or "FRUTILLA" in prod_upper or "FRUTILLA" in cat_upper:
                tipo_fruta = "Frutilla"
            elif " MO " in f" {prod_upper} " or "MO_" in prod_upper or prod_upper.startswith("MO ") or "MORA" in prod_upper or "MORA" in cat_upper:
                tipo_fruta = "Mora"
            elif " CR " in f" {prod_upper} " or "CR_" in prod_upper or prod_upper.startswith("CR ") or "CEREZA" in prod_upper or "CEREZA" in cat_upper:
                tipo_fruta = "Cereza"
            elif "MIX" in prod_upper or "MIXED" in prod_upper or "CREATIVE" in prod_upper:
                tipo_fruta = "Mix"
            
            # Obtener Manejo del campo x_studio_categora_tipo_de_manejo
            manejo_raw = p_info.get("x_studio_categora_tipo_de_manejo", "")
            if manejo_raw and isinstance(manejo_raw, str):
                manejo = "Orgánico" if "org" in manejo_raw.lower() else "Convencional"
            else:
                manejo = "Convencional"
            
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
        
        # 2. Buscar en Recepciones Pendientes
        move_lines = self.odoo.search_read(
            "stock.move.line",
            [
                ("result_package_id", "=", package_id),
                ("state", "not in", ["done", "cancel"])
            ],
            ["picking_id", "location_dest_id", "product_id", "reserved_uom_qty"]
        )
        
        if move_lines:
            picking = move_lines[0]["picking_id"]
            dest = move_lines[0]["location_dest_id"]
            products = []
            
            for ml in move_lines:
                if ml.get("product_id"):
                    products.append({
                        "name": ml["product_id"][1],
                        "quantity": ml["reserved_uom_qty"]
                    })
            
            return {
                "found": True,
                "status": "pending_reception",
                "pallet_code": pallet_code,
                "picking_id": picking[0],
                "picking_name": picking[1],
                "destination_id": dest[0] if dest else None,
                "destination_name": dest[1] if dest else "N/A",
                "products": products,
                "items_count": len(move_lines)
            }
        
        return {
            "found": False, 
            "message": f"Pallet '{pallet_code}' existe pero no tiene stock ni recepciones pendientes"
        }

    def get_ubicacion_by_barcode(self, barcode: str) -> Dict:
        """
        Busca una ubicación por su código de barras.
        Retorna información básica de la ubicación encontrada.
        """
        try:
            locations = self.odoo.search_read(
                "stock.location",
                [("barcode", "=", barcode), ("usage", "=", "internal")],
                ["id", "name", "display_name", "barcode"]
            )
            
            if not locations:
                return {
                    "found": False,
                    "message": f"No se encontró ubicación con código de barras: {barcode}"
                }
            
            loc = locations[0]
            return {
                "found": True,
                "id": loc["id"],
                "name": loc["name"],
                "display_name": loc.get("display_name", loc["name"]),
                "barcode": loc.get("barcode", "")
            }
        except Exception as e:
            return {
                "found": False,
                "message": f"Error buscando ubicación: {str(e)}"
            }

    def move_multiple_pallets(self, pallet_codes: List[str], location_dest_id: int) -> Dict:
        """
        Mueve múltiples pallets a una ubicación destino.
        Retorna resumen de éxitos y errores.
        """
        results = {
            "total": len(pallet_codes),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        for pallet_code in pallet_codes:
            try:
                result = self.move_pallet(pallet_code, location_dest_id)
                if result.get("success"):
                    results["success"] += 1
                    results["details"].append({
                        "pallet": pallet_code,
                        "status": "ok",
                        "message": result.get("message", "Movido correctamente")
                    })
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "pallet": pallet_code,
                        "status": "error",
                        "message": result.get("message", "Error desconocido")
                    })
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "pallet": pallet_code,
                    "status": "error",
                    "message": str(e)
                })
        
        return results

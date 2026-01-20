"""
Servicio de Trazabilidad - Obtiene datos crudos de movimientos de paquetes.
Este servicio es la fuente de datos para los transformadores de Sankey y React Flow.
"""
from typing import List, Dict, Optional, Set
from shared.odoo_client import OdooClient


class TraceabilityService:
    """Servicio para obtener datos de trazabilidad de paquetes."""
    
    PARTNER_VENDORS_LOCATION_ID = 4  # Partners/Vendors location
    PARTNER_CUSTOMERS_LOCATION_ID = 5  # Partners/Customers location
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self._virtual_location_ids = None
    
    def get_traceability_by_identifier(
        self,
        identifier: str,
        limit: int = 10000
    ) -> Dict:
        """
        Obtiene trazabilidad completa por identificador (venta o paquete).
        
        Args:
            identifier: Puede ser:
                - Código de venta (ej: S00574) → busca todos los pallets de esa venta
                - Nombre de paquete → busca ese paquete específico
        
        Returns:
            Dict con estructura similar a get_traceability_data
        """
        # Detectar si es venta (S + números) o paquete
        is_sale = identifier.startswith("S") and identifier[1:].isdigit() if len(identifier) > 1 else False
        
        if is_sale:
            return self._get_traceability_by_sale(identifier, limit)
        else:
            return self._get_traceability_by_package(identifier, limit)
    
    def _get_traceability_by_sale(self, sale_origin: str, limit: int) -> Dict:
        """Busca trazabilidad desde una venta específica."""
        try:
            # Buscar pickings de esa venta
            pickings = self.odoo.search_read(
                "stock.picking",
                [("origin", "=", sale_origin)],
                ["id"],
                limit=10
            )
            
            if not pickings:
                print(f"[TraceabilityService] No se encontró venta: {sale_origin}")
                return self._empty_result()
            
            picking_ids = [p["id"] for p in pickings]
            
            # Buscar movimientos de esos pickings
            move_lines = self.odoo.search_read(
                "stock.move.line",
                [
                    ("picking_id", "in", picking_ids),
                    "|",
                    ("package_id", "!=", False),
                    ("result_package_id", "!=", False),
                    ("qty_done", ">", 0),
                    ("state", "=", "done"),
                ],
                ["package_id", "result_package_id"],
                limit=100
            )
            
            # Extraer package_ids de la venta
            package_ids = set()
            for ml in move_lines:
                pkg_rel = ml.get("package_id")
                result_rel = ml.get("result_package_id")
                
                if pkg_rel:
                    pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
                    if pkg_id:
                        package_ids.add(pkg_id)
                
                if result_rel:
                    result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
                    if result_id:
                        package_ids.add(result_id)
            
            if not package_ids:
                print(f"[TraceabilityService] No se encontraron paquetes en venta: {sale_origin}")
                return self._empty_result()
            
            print(f"[TraceabilityService] Venta {sale_origin}: {len(package_ids)} paquetes encontrados")
            
            # Buscar toda la historia de esos paquetes
            return self._get_traceability_for_packages(list(package_ids), limit)
            
        except Exception as e:
            print(f"[TraceabilityService] Error en trazabilidad por venta: {e}")
            return self._empty_result()
    
    def _get_traceability_by_package(self, package_name: str, limit: int) -> Dict:
        """Busca trazabilidad de un paquete específico por nombre."""
        try:
            # Buscar directamente en stock.move.line por nombre de paquete
            move_lines = self.odoo.search_read(
                "stock.move.line",
                [
                    "|",
                    ("package_id.name", "=", package_name),
                    ("result_package_id.name", "=", package_name),
                    ("qty_done", ">", 0),
                    ("state", "=", "done"),
                ],
                ["package_id", "result_package_id"],
                limit=100
            )
            
            if not move_lines:
                print(f"[TraceabilityService] No se encontró paquete: {package_name}")
                return self._empty_result()
            
            # Extraer package_ids
            package_ids = set()
            for ml in move_lines:
                pkg_rel = ml.get("package_id")
                result_rel = ml.get("result_package_id")
                
                if pkg_rel:
                    pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
                    if pkg_id:
                        package_ids.add(pkg_id)
                
                if result_rel:
                    result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
                    if result_id:
                        package_ids.add(result_id)
            
            if not package_ids:
                print(f"[TraceabilityService] No se encontraron IDs para paquete: {package_name}")
                return self._empty_result()
            
            print(f"[TraceabilityService] Paquete encontrado: {package_name} ({len(package_ids)} IDs)")
            
            # Buscar toda la historia de esos paquetes
            return self._get_traceability_for_packages(list(package_ids), limit)
            
        except Exception as e:
            print(f"[TraceabilityService] Error en trazabilidad por paquete: {e}")
            return self._empty_result()
    
    def _get_traceability_for_packages(self, package_ids: List[int], limit: int) -> Dict:
        """Obtiene la trazabilidad completa de paquetes específicos."""
        virtual_ids = self._get_virtual_location_ids()
        
        # Buscar TODOS los movimientos de esos paquetes (sin filtro de fecha)
        domain = [
            "|",
            ("package_id", "in", package_ids),
            ("result_package_id", "in", package_ids),
            ("qty_done", ">", 0),
            ("state", "=", "done"),
        ]
        
        fields = [
            "id", "reference", "package_id", "result_package_id",
            "lot_id", "qty_done", "product_id", "location_id", 
            "location_dest_id", "date", "picking_id"
        ]
        
        try:
            move_lines = self.odoo.search_read(
                "stock.move.line",
                domain,
                fields,
                limit=limit,
                order="date asc"
            )
        except Exception as e:
            print(f"[TraceabilityService] Error fetching move lines: {e}")
            return self._empty_result()
        
        if not move_lines:
            return self._empty_result()
        
        print(f"[TraceabilityService] Procesando {len(move_lines)} movimientos")
        
        # Procesar movimientos
        result = self._process_move_lines(move_lines, virtual_ids)
        result["move_lines"] = move_lines
        
        # Resolver proveedores y clientes
        self._resolve_partners(result)
        
        # Enriquecer con fechas
        self._enrich_with_pallet_dates(result)
        self._enrich_with_mrp_dates(result)
        
        return result

    def get_traceability_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10000
    ) -> Dict:
        """
        Obtiene todos los datos de trazabilidad de paquetes en un período.
        
        Estrategia:
        1. Busca movimientos en el rango de fechas (eventos principales)
        2. Identifica todos los pallets involucrados
        3. Trae TODOS los movimientos de esos pallets (flujo completo sin filtro fecha)
        
        Returns:
            Dict con:
            - pallets: {pkg_id: {name, qty, products: {prod: qty}}}
            - processes: {ref: {date, is_reception, picking_id, supplier_id?}}
            - suppliers: {id: name}
            - customers: {id: name}
            - links: [(source_type, source_id, target_type, target_id, qty)]
            - move_lines: Lista de movimientos originales (para debug)
        """
        virtual_ids = self._get_virtual_location_ids()
        
        # PASO 1: Buscar movimientos con paquetes en el rango de fechas (eventos principales)
        domain = [
            "|",
            ("package_id", "!=", False),
            ("result_package_id", "!=", False),
            ("qty_done", ">", 0),
            ("state", "=", "done"),
        ]
        if start_date:
            domain.append(("date", ">=", start_date))
        if end_date:
            domain.append(("date", "<=", end_date))

        fields = [
            "id", "reference", "package_id", "result_package_id",
            "lot_id", "qty_done", "product_id", "location_id", 
            "location_dest_id", "date", "picking_id"
        ]
        
        try:
            initial_move_lines = self.odoo.search_read(
                "stock.move.line",
                domain,
                fields,
                limit=limit,
                order="date asc"
            )
        except Exception as e:
            print(f"[TraceabilityService] Error fetching initial move lines: {e}")
            return self._empty_result()
        
        if not initial_move_lines:
            return self._empty_result()
        
        print(f"[TraceabilityService] Found {len(initial_move_lines)} move lines in date range")
        
        # PASO 2: Extraer todos los package_ids involucrados
        package_ids = set()
        for ml in initial_move_lines:
            pkg_rel = ml.get("package_id")
            result_rel = ml.get("result_package_id")
            
            if pkg_rel:
                pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
                if pkg_id:
                    package_ids.add(pkg_id)
            
            if result_rel:
                result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
                if result_id:
                    package_ids.add(result_id)
        
        if not package_ids:
            print("[TraceabilityService] No packages found in date range")
            return self._empty_result()
        
        print(f"[TraceabilityService] Found {len(package_ids)} unique packages, fetching full history...")
        
        # PASO 3: Traer TODOS los movimientos de esos pallets (sin filtro de fecha)
        full_domain = [
            "|",
            ("package_id", "in", list(package_ids)),
            ("result_package_id", "in", list(package_ids)),
            ("qty_done", ">", 0),
            ("state", "=", "done"),
        ]
        
        try:
            all_move_lines = self.odoo.search_read(
                "stock.move.line",
                full_domain,
                fields,
                limit=limit * 3,  # Aumentar límite para historia completa
                order="date asc"
            )
        except Exception as e:
            print(f"[TraceabilityService] Error fetching full move lines: {e}")
            return self._empty_result()
        
        print(f"[TraceabilityService] Processing {len(all_move_lines)} total move lines (full history)")
        
        # Procesar movimientos con historia completa
        result = self._process_move_lines(all_move_lines, virtual_ids)
        result["move_lines"] = all_move_lines  # Para debug
        result["initial_packages_count"] = len(package_ids)
        
        # Resolver proveedores y clientes
        self._resolve_partners(result)
        
        # Enriquecer con fechas adicionales
        self._enrich_with_pallet_dates(result)
        self._enrich_with_mrp_dates(result)
        
        return result
    
    def _empty_result(self) -> Dict:
        """Retorna estructura vacía."""
        return {
            "pallets": {},
            "processes": {},
            "suppliers": {},
            "customers": {},
            "links": [],
            "move_lines": []
        }
    
    def _process_move_lines(self, move_lines: List[Dict], virtual_ids: Set[int]) -> Dict:
        """Procesa los movimientos y extrae pallets, procesos y conexiones."""
        pallets = {}
        processes = {}
        suppliers = {}
        customers = {}
        links = []
        
        reception_picking_ids = set()
        sale_picking_ids = set()
        sale_pallet_pickings = {}  # pkg_id -> picking_id
        
        for ml in move_lines:
            loc_rel = ml.get("location_id")
            loc_dest_rel = ml.get("location_dest_id")
            loc_id = loc_rel[0] if isinstance(loc_rel, (list, tuple)) else loc_rel
            loc_dest_id = loc_dest_rel[0] if isinstance(loc_dest_rel, (list, tuple)) else loc_dest_rel
            
            pkg_rel = ml.get("package_id")
            result_rel = ml.get("result_package_id")
            ref = ml.get("reference") or "Sin Referencia"
            qty = ml.get("qty_done", 0) or 0
            date = ml.get("date", "")
            
            prod_rel = ml.get("product_id")
            prod_name = prod_rel[1] if isinstance(prod_rel, (list, tuple)) and len(prod_rel) > 1 else "N/A"
            
            pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
            pkg_name = pkg_rel[1] if isinstance(pkg_rel, (list, tuple)) and len(pkg_rel) > 1 else None
            
            result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
            result_name = result_rel[1] if isinstance(result_rel, (list, tuple)) and len(result_rel) > 1 else None
            
            picking_rel = ml.get("picking_id")
            picking_id = picking_rel[0] if isinstance(picking_rel, (list, tuple)) else picking_rel
            
            lot_rel = ml.get("lot_id")
            lot_id = lot_rel[0] if isinstance(lot_rel, (list, tuple)) else lot_rel
            lot_name = lot_rel[1] if isinstance(lot_rel, (list, tuple)) and len(lot_rel) > 1 else None
            
            # Registrar proceso
            if ref not in processes:
                processes[ref] = {
                    "date": date,
                    "is_reception": False,
                    "picking_id": picking_id,
                    "supplier_id": None,
                    "lot_ids": set()
                }
            if lot_id:
                processes[ref]["lot_ids"].add(lot_id)
            
            # CASO 1: RECEPCIÓN (viene de proveedor)
            if loc_id == self.PARTNER_VENDORS_LOCATION_ID:
                target_pkg = result_id or pkg_id
                target_name = result_name or pkg_name
                if target_pkg:
                    self._register_pallet(pallets, target_pkg, target_name, qty, prod_name, date, lot_name, "IN")
                    processes[ref]["is_reception"] = True
                    processes[ref]["picking_id"] = picking_id
                    reception_picking_ids.add(picking_id)
                    # Link: RECEPTION → PALLET
                    links.append(("RECV", ref, "PALLET", target_pkg, qty))
            
            # CASO 2: ENTRADA A PROCESO (pallet → ubicación virtual)
            elif pkg_id and loc_dest_id in virtual_ids:
                self._register_pallet(pallets, pkg_id, pkg_name, qty, prod_name, date, lot_name, "IN")
                # Link: PALLET → PROCESO
                links.append(("PALLET", pkg_id, "PROCESS", ref, qty))
            
            # CASO 3: SALIDA DE PROCESO (result_package sale de ubicación virtual)
            if result_id and loc_id in virtual_ids:
                self._register_pallet(pallets, result_id, result_name, qty, prod_name, date, lot_name, "OUT")
                # Link: PROCESO → PALLET
                links.append(("PROCESS", ref, "PALLET", result_id, qty))
            
            # CASO 4: VENTA (va hacia cliente - Partners/Customers)
            # Verificar que el picking origin empiece con "S" (ej: S00574)
            if loc_dest_id == self.PARTNER_CUSTOMERS_LOCATION_ID and loc_id != self.PARTNER_CUSTOMERS_LOCATION_ID:
                target_pkg = pkg_id  # En ventas, el paquete de origen es el que se vendió
                if target_pkg and picking_id:
                    sale_pallet_pickings[target_pkg] = picking_id
                    sale_picking_ids.add(picking_id)
        
        # Convertir sets a lists para serialización
        for ref, pinfo in processes.items():
            pinfo["lot_ids"] = list(pinfo["lot_ids"])
        
        return {
            "pallets": pallets,
            "processes": processes,
            "suppliers": suppliers,
            "customers": customers,
            "links": links,
            "reception_picking_ids": list(reception_picking_ids),
            "sale_picking_ids": list(sale_picking_ids),
            "sale_pallet_pickings": sale_pallet_pickings
        }
    
    def _register_pallet(
        self,
        pallets: Dict,
        pid: int,
        pname: str,
        qty: float,
        product: str,
        date: str,
        lot_name: str,
        direction: str  # "IN" o "OUT"
    ):
        """Registra un pallet con sus productos."""
        if pid not in pallets:
            pallets[pid] = {
                "name": pname or str(pid),
                "qty": 0,
                "products": {},
                "first_date": date,
                "last_date": date,
                "lot_names": set(),
                "direction": direction  # IN = entra a proceso, OUT = sale de proceso
            }
        
        pallets[pid]["qty"] += qty
        pallets[pid]["last_date"] = date
        
        if product not in pallets[pid]["products"]:
            pallets[pid]["products"][product] = 0
        pallets[pid]["products"][product] += qty
        
        if lot_name:
            pallets[pid]["lot_names"].add(lot_name)
        
        # Actualizar dirección si sale de proceso
        if direction == "OUT":
            pallets[pid]["direction"] = "OUT"
    
    def _resolve_partners(self, result: Dict):
        """Resuelve proveedores y clientes desde los pickings."""
        reception_picking_ids = result.get("reception_picking_ids", [])
        sale_picking_ids = result.get("sale_picking_ids", [])
        sale_pallet_pickings = result.get("sale_pallet_pickings", {})
        
        all_picking_ids = set(reception_picking_ids) | set(sale_picking_ids)
        if not all_picking_ids:
            return
        
        try:
            pickings = self.odoo.read(
                "stock.picking",
                list(all_picking_ids),
                ["id", "partner_id", "scheduled_date", "origin", "date_done"]
            )
            pickings_by_id = {p["id"]: p for p in pickings}
            
            # Proveedores
            for ref, pinfo in result["processes"].items():
                if pinfo.get("is_reception") and pinfo.get("picking_id"):
                    picking = pickings_by_id.get(pinfo["picking_id"], {})
                    partner_rel = picking.get("partner_id")
                    if partner_rel:
                        sid = partner_rel[0] if isinstance(partner_rel, (list, tuple)) else partner_rel
                        sname = partner_rel[1] if isinstance(partner_rel, (list, tuple)) and len(partner_rel) > 1 else "Proveedor"
                        result["suppliers"][sid] = sname
                        pinfo["supplier_id"] = sid
            
            # Clientes - Filtrar solo ventas (origin empieza con "S")
            for pkg_id, picking_id in sale_pallet_pickings.items():
                picking = pickings_by_id.get(picking_id, {})
                origin = picking.get("origin", "")
                
                # Verificar que sea una venta (origin empieza con S seguido de números)
                if not origin or not origin.startswith("S"):
                    continue
                
                # Verificar que después de S haya números (ej: S00574)
                try:
                    int(origin[1:])  # Intentar convertir lo que sigue después de "S"
                except (ValueError, IndexError):
                    continue  # No es un formato de venta válido
                
                partner_rel = picking.get("partner_id")
                date_done = picking.get("date_done", "")  # Fecha de concreción de la venta
                scheduled_date = picking.get("scheduled_date", "")
                
                if partner_rel:
                    cid = partner_rel[0] if isinstance(partner_rel, (list, tuple)) else partner_rel
                    cname = partner_rel[1] if isinstance(partner_rel, (list, tuple)) and len(partner_rel) > 1 else "Cliente"
                    # Guardar cliente con fecha de concreción
                    if cid not in result["customers"]:
                        result["customers"][cid] = {
                            "name": cname,
                            "date_done": date_done,  # Fecha real de venta concretada
                            "scheduled_date": scheduled_date,
                            "sale_order": origin  # Referencia de venta
                        }
                    # Link: PALLET → CUSTOMER
                    pallet_qty = result["pallets"].get(pkg_id, {}).get("qty", 1)
                    result["links"].append(("PALLET", pkg_id, "CUSTOMER", cid, pallet_qty))
        except Exception as e:
            print(f"[TraceabilityService] Error resolving partners: {e}")
        
        # Limpiar campos temporales
        result.pop("reception_picking_ids", None)
        result.pop("sale_picking_ids", None)
        result.pop("sale_pallet_pickings", None)
        
        # Convertir sets a lists para serialización
        for pid, pinfo in result["pallets"].items():
            pinfo["lot_names"] = list(pinfo.get("lot_names", set()))
    
    def _get_virtual_location_ids(self) -> Set[int]:
        """Obtiene IDs de ubicaciones virtuales/producción."""
        if self._virtual_location_ids is not None:
            return self._virtual_location_ids
        
        # IDs conocidos de ubicaciones virtuales
        known_virtual_ids = {8485, 15}
        
        try:
            virtual_locations = self.odoo.search_read(
                "stock.location",
                [("usage", "=", "production")],
                ["id"],
                limit=100
            )
            for loc in virtual_locations:
                known_virtual_ids.add(loc["id"])
        except Exception as e:
            print(f"[TraceabilityService] Error fetching virtual locations: {e}")
        
        self._virtual_location_ids = known_virtual_ids
        return known_virtual_ids
    
    def _enrich_with_pallet_dates(self, result: Dict):
        """Obtiene create_date de stock.quant.package para cada pallet."""
        pallet_ids = list(result["pallets"].keys())
        if not pallet_ids:
            return
        
        try:
            packages = self.odoo.read(
                "stock.quant.package",
                pallet_ids,
                ["id", "create_date"]
            )
            for pkg in packages:
                pid = pkg["id"]
                if pid in result["pallets"]:
                    result["pallets"][pid]["create_date"] = pkg.get("create_date", "")
        except Exception as e:
            print(f"[TraceabilityService] Error fetching package dates: {e}")
    
    def _enrich_with_mrp_dates(self, result: Dict):
        """Obtiene fechas de inicio/término de mrp.production para procesos."""
        # Buscar MOs que coincidan con las referencias de procesos
        process_refs = [ref for ref, p in result["processes"].items() if not p.get("is_reception")]
        if not process_refs:
            return
        
        try:
            # Buscar MOs por nombre (origin o name)
            mrp_orders = self.odoo.search_read(
                "mrp.production",
                ["|", ("name", "in", process_refs), ("origin", "in", process_refs)],
                ["id", "name", "origin", "x_studio_inicio_de_proceso", "x_studio_termino_de_proceso"],
                limit=len(process_refs) * 2
            )
            
            # Crear mapa de MO por referencia
            mrp_by_ref = {}
            for mo in mrp_orders:
                if mo.get("name") in process_refs:
                    mrp_by_ref[mo["name"]] = mo
                if mo.get("origin") in process_refs:
                    mrp_by_ref[mo["origin"]] = mo
            
            # Enriquecer procesos con fechas MRP
            for ref, pinfo in result["processes"].items():
                if ref in mrp_by_ref:
                    mo = mrp_by_ref[ref]
                    pinfo["mrp_start"] = mo.get("x_studio_inicio_de_proceso", "")
                    pinfo["mrp_end"] = mo.get("x_studio_termino_de_proceso", "")
                    pinfo["mrp_id"] = mo.get("id")
        except Exception as e:
            print(f"[TraceabilityService] Error fetching MRP dates: {e}")

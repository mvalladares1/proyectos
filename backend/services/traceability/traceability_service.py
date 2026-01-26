"""
Servicio de Trazabilidad - Obtiene datos crudos de movimientos de paquetes.
Este servicio es la fuente de datos para los transformadores de Sankey y React Flow.
"""
from typing import List, Dict, Optional, Set
from shared.odoo_client import OdooClient
from datetime import datetime
import pytz


class TraceabilityService:
    """Servicio para obtener datos de trazabilidad de paquetes."""
    
    PARTNER_VENDORS_LOCATION_ID = 4  # Partners/Vendors location
    PARTNER_CUSTOMERS_LOCATION_ID = 5  # Partners/Customers location
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self._virtual_location_ids = None
        self.chile_tz = pytz.timezone('America/Santiago')
        self.utc_tz = pytz.UTC
    
    def _convert_utc_to_chile(self, utc_datetime_str: str) -> str:
        """Convierte fecha UTC a hora de Chile."""
        if not utc_datetime_str:
            return ""
        
        try:
            # Parsear fecha UTC (formato: "2024-01-15 14:30:00")
            utc_dt = datetime.strptime(utc_datetime_str, "%Y-%m-%d %H:%M:%S")
            utc_dt = self.utc_tz.localize(utc_dt)
            
            # Convertir a Chile
            chile_dt = utc_dt.astimezone(self.chile_tz)
            
            return chile_dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError) as e:
            print(f"[TraceabilityService] Error converting datetime: {utc_datetime_str} - {e}")
            return utc_datetime_str
    
    def get_traceability_by_identifier(
        self,
        identifier: str,
        limit: int = 10000,
        include_siblings: bool = True
    ) -> Dict:
        """
        Obtiene trazabilidad completa por identificador (venta, paquete o guía).
        
        Args:
            identifier: Puede ser:
                - Código de venta (ej: S00574) → busca todos los pallets de esa venta
                - Nombre de paquete → busca ese paquete específico
                - Guía de despacho (si mode="guide") → busca por número de guía
            include_siblings: Si True, incluye pallets hermanos del mismo proceso.
                             Si False, solo sigue la cadena conectada directa.
        
        Returns:
            Dict con estructura similar a get_traceability_data
        """
        # Detectar si es venta (S + números) o paquete
        is_sale = identifier.startswith("S") and identifier[1:].isdigit() if len(identifier) > 1 else False
        
        if is_sale:
            return self._get_traceability_by_sale(identifier, limit, include_siblings)
        else:
            return self._get_traceability_by_package(identifier, limit, include_siblings)
    
    def _get_traceability_by_sale(self, sale_origin: str, limit: int, include_siblings: bool = True) -> Dict:
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
            
            # Buscar toda la historia de esos paquetes según el modo seleccionado
            return self._get_traceability_for_packages(list(package_ids), limit, include_siblings=include_siblings)
            
        except Exception as e:
            print(f"[TraceabilityService] Error en trazabilidad por venta: {e}")
            return self._empty_result()
    
    def _get_traceability_by_delivery_guide(self, delivery_guide: str, limit: int, include_siblings: bool = True) -> Dict:
        """Busca trazabilidad desde una guía de despacho HACIA ADELANTE."""
        try:
            # Buscar recepciones con esa guía de despacho
            pickings = self.odoo.search_read(
                "stock.picking",
                [
                    ("x_studio_gua_de_despacho", "=", delivery_guide),
                    ("state", "=", "done")
                ],
                ["id", "name"],
                limit=10
            )
            
            if not pickings:
                print(f"[TraceabilityService] No se encontró recepción con guía: {delivery_guide}")
                return self._empty_result()
            
            print(f"[TraceabilityService] Guía {delivery_guide}: {len(pickings)} recepciones encontradas")
            
            picking_ids = [p["id"] for p in pickings]
            
            # Buscar pallets de estas recepciones (result_package_id)
            move_lines = self.odoo.search_read(
                "stock.move.line",
                [
                    ("picking_id", "in", picking_ids),
                    ("result_package_id", "!=", False),
                    ("qty_done", ">", 0),
                    ("state", "=", "done"),
                ],
                ["result_package_id"],
                limit=500
            )
            
            # Extraer package_ids de la recepción
            package_ids = set()
            for ml in move_lines:
                result_rel = ml.get("result_package_id")
                if result_rel:
                    result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
                    if result_id:
                        package_ids.add(result_id)
            
            if not package_ids:
                print(f"[TraceabilityService] No se encontraron pallets en guía: {delivery_guide}")
                return self._empty_result()
            
            print(f"[TraceabilityService] Guía {delivery_guide}: {len(package_ids)} pallets encontrados")
            
            # Trazabilidad HACIA ADELANTE de esos pallets
            return self._get_forward_traceability_for_packages(list(package_ids), limit, include_siblings=include_siblings)
            
        except Exception as e:
            print(f"[TraceabilityService] Error en trazabilidad por guía: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_result()
    
    def _get_traceability_by_package(self, package_name: str, limit: int, include_siblings: bool = False) -> Dict:
        """Busca trazabilidad de un paquete específico por nombre hacia ATRÁS."""
        try:
            # Primero buscar el ID del paquete en stock.quant.package
            packages = self.odoo.search_read(
                "stock.quant.package",
                [("name", "ilike", package_name)],
                ["id", "name"],
                limit=10
            )
            
            print(f"[TraceabilityService] stock.quant.package ilike '{package_name}': {len(packages)} encontrados")
            for p in packages:
                print(f"   - ID: {p['id']}, Name: {p['name']}")
            
            if not packages:
                print(f"[TraceabilityService] No se encontró paquete: {package_name}")
                return self._empty_result()
            
            package_ids = [p["id"] for p in packages]
            
            print(f"[TraceabilityService] Paquete {package_name}: {len(package_ids)} IDs encontrados")
            
            # Buscar hacia ATRÁS según el modo seleccionado
            return self._get_traceability_for_packages(package_ids, limit, include_siblings=include_siblings)
            
        except Exception as e:
            print(f"[TraceabilityService] Error en trazabilidad por paquete: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_result()
    
    def _get_traceability_for_packages(
        self, 
        initial_package_ids: List[int], 
        limit: int,
        include_siblings: bool = True
    ) -> Dict:
        """
        Trazabilidad hacia ATRÁS desde los paquetes iniciales.
        
        Args:
            initial_package_ids: IDs de paquetes iniciales
            limit: Límite de registros por query
            include_siblings: 
                - True: Trae TODOS los movimientos de cada proceso (todos los hermanos)
                - False: "Conexión directa" - Trae todo pero filtra para mostrar solo la cadena conectada
        
        Estrategia: Siempre recopilamos TODOS los datos (como "Todos"), 
        y luego si include_siblings=False, filtramos para quedarnos solo con la cadena conectada.
        """
        virtual_ids = self._get_virtual_location_ids()
        
        fields = [
            "id", "reference", "package_id", "result_package_id",
            "lot_id", "qty_done", "product_id", "location_id", 
            "location_dest_id", "date", "picking_id"
        ]
        
        # Control de expansión
        all_move_lines = []
        processed_move_ids = set()
        processed_references = set()
        
        # Cola de paquetes a trazabilizar
        packages_to_trace = set(initial_package_ids)
        traced_packages = set()
        
        max_iterations = 50
        iteration = 0
        
        mode_msg = "CON todos los hermanos" if include_siblings else "Conexión directa"
        print(f"[TraceabilityService] Iniciando trazabilidad hacia ATRÁS ({mode_msg}) desde {len(packages_to_trace)} paquetes")
        
        # =====================================================
        # FASE 1: Recopilar TODOS los movimientos (como "Todos")
        # =====================================================
        while packages_to_trace and iteration < max_iterations:
            iteration += 1
            
            current_packages = list(packages_to_trace - traced_packages)
            if not current_packages:
                break
                
            print(f"[TraceabilityService] Iteración {iteration}: {len(current_packages)} paquetes a procesar")
            
            try:
                # Buscar dónde estos paquetes son SALIDA (result_package_id) - proceso que los creó
                # O dónde son ENTRADA (package_id) - para encontrar referencias relacionadas
                out_moves = self.odoo.search_read(
                    "stock.move.line",
                    [
                        "|",
                        ("result_package_id", "in", current_packages),
                        ("package_id", "in", current_packages),
                        ("qty_done", ">", 0),
                        ("state", "=", "done"),
                    ],
                    fields,
                    limit=limit,
                    order="date asc"
                )
                
                # Recopilar referencias
                new_references = set()
                for ml in out_moves:
                    if ml["id"] not in processed_move_ids:
                        all_move_lines.append(ml)
                        processed_move_ids.add(ml["id"])
                    
                    ref = ml.get("reference")
                    if ref and ref not in processed_references:
                        new_references.add(ref)
                
                # Para cada proceso, obtener movimientos según include_siblings
                for ref in new_references:
                    ref_moves = self.odoo.search_read(
                        "stock.move.line",
                        [
                            ("reference", "=", ref),
                            ("qty_done", ">", 0),
                            ("state", "=", "done"),
                        ],
                        fields,
                        limit=500,
                        order="date asc"
                    )
                    
                    for ml in ref_moves:
                        if ml["id"] not in processed_move_ids:
                            all_move_lines.append(ml)
                            processed_move_ids.add(ml["id"])
                        
                        # Los INPUTS que NO vienen de recepción se siguen hacia atrás
                        # PERO: si include_siblings=False, solo seguir inputs que realmente se necesitan
                        pkg_rel = ml.get("package_id")
                        result_rel = ml.get("result_package_id")
                        loc_id = ml.get("location_id")
                        loc_id = loc_id[0] if isinstance(loc_id, (list, tuple)) else loc_id
                        
                        # Si es modo "conexión directa", solo seguir packages que son outputs del proceso
                        # (los que encontramos en out_moves), no todos los inputs del proceso
                        if not include_siblings:
                            # Solo agregar a la cola si este movimiento produce uno de current_packages
                            if result_rel:
                                result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
                                if result_id in current_packages:
                                    # Este movimiento produce uno de nuestros paquetes, seguir su input
                                    if pkg_rel and loc_id != self.PARTNER_VENDORS_LOCATION_ID:
                                        pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
                                        if pkg_id:
                                            packages_to_trace.add(pkg_id)
                        else:
                            # Modo "Todos": seguir todos los inputs
                            if pkg_rel:
                                pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
                                if pkg_id and loc_id != self.PARTNER_VENDORS_LOCATION_ID:
                                    packages_to_trace.add(pkg_id)
                    
                    processed_references.add(ref)
                
                traced_packages.update(current_packages)
                
            except Exception as e:
                print(f"[TraceabilityService] Error en iteración {iteration}: {e}")
                import traceback
                traceback.print_exc()
                break
        
        # Buscar movimientos de RECEPCIÓN
        try:
            all_package_ids = set()
            for ml in all_move_lines:
                pkg_rel = ml.get("package_id")
                result_rel = ml.get("result_package_id")
                
                if pkg_rel:
                    pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
                    if pkg_id:
                        all_package_ids.add(pkg_id)
                
                if result_rel:
                    result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
                    if result_id:
                        all_package_ids.add(result_id)
            
            if all_package_ids:
                reception_moves = self.odoo.search_read(
                    "stock.move.line",
                    [
                        ("result_package_id", "in", list(all_package_ids)),
                        ("location_id", "=", self.PARTNER_VENDORS_LOCATION_ID),
                        ("qty_done", ">", 0),
                        ("state", "=", "done"),
                    ],
                    fields,
                    limit=500,
                    order="date asc"
                )
                
                for ml in reception_moves:
                    if ml["id"] not in processed_move_ids:
                        all_move_lines.append(ml)
                        processed_move_ids.add(ml["id"])
                
                print(f"[TraceabilityService] Encontrados {len(reception_moves)} movimientos de recepción")
        except Exception as e:
            print(f"[TraceabilityService] Error buscando recepciones: {e}")
        
        # Buscar movimientos de VENTA
        try:
            out_package_ids = set()
            for ml in all_move_lines:
                result_rel = ml.get("result_package_id")
                if result_rel:
                    result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
                    if result_id:
                        out_package_ids.add(result_id)
            
            if out_package_ids:
                sale_moves = self.odoo.search_read(
                    "stock.move.line",
                    [
                        ("package_id", "in", list(out_package_ids)),
                        ("location_dest_id", "=", self.PARTNER_CUSTOMERS_LOCATION_ID),
                        ("qty_done", ">", 0),
                        ("state", "=", "done"),
                    ],
                    fields,
                    limit=500,
                    order="date asc"
                )
                
                for ml in sale_moves:
                    if ml["id"] not in processed_move_ids:
                        all_move_lines.append(ml)
                        processed_move_ids.add(ml["id"])
                
                print(f"[TraceabilityService] Encontrados {len(sale_moves)} movimientos de venta")
        except Exception as e:
            print(f"[TraceabilityService] Error buscando ventas: {e}")
        
        print(f"[TraceabilityService] Total ANTES de filtrar: {len(all_move_lines)} movimientos")
        
        if not all_move_lines:
            return self._empty_result()
        
        # Procesar movimientos (siempre procesamos todo como "Todos")
        result = self._process_move_lines(all_move_lines, virtual_ids)
        result["move_lines"] = all_move_lines
        
        # Resolver proveedores y clientes (pasar initial_package_ids para filtrar ventas)
        self._resolve_partners(result, initial_package_ids)
        
        # Enriquecer con fechas
        self._enrich_with_pallet_dates(result)
        self._enrich_with_mrp_dates(result)
        
        # =====================================================
        # FASE 2: Si include_siblings=False, filtrar el resultado procesado
        # =====================================================
        if not include_siblings:
            result = self._filter_direct_connection_result(result, initial_package_ids)
        
        return result
    
    def _get_forward_traceability_for_packages(
        self, 
        initial_package_ids: List[int], 
        limit: int,
        include_siblings: bool = True
    ) -> Dict:
        """
        Trazabilidad hacia ADELANTE desde los paquetes iniciales (típicamente de una recepción).
        
        Sigue la cadena completa:
        1. Pallets iniciales (de recepción)
        2. Esos pallets como INPUT (package_id) de procesos → obtiene OUTPUT (result_package_id)
        3. Esos OUTPUT como INPUT de otros procesos → más OUTPUT
        4. Y así hasta llegar a clientes
        
        Args:
            initial_package_ids: IDs de paquetes iniciales (ej: pallets de recepción)
            limit: Límite de registros por query
            include_siblings: 
                - True: Trae TODOS los movimientos de cada proceso (todos los hermanos)
                - False: "Conexión directa" - solo la cadena conectada
        """
        virtual_ids = self._get_virtual_location_ids()
        
        fields = [
            "id", "reference", "package_id", "result_package_id",
            "lot_id", "qty_done", "product_id", "location_id", 
            "location_dest_id", "date", "picking_id"
        ]
        
        all_move_lines = []
        processed_move_ids = set()
        processed_references = set()
        
        # Cola de paquetes a trazabilizar HACIA ADELANTE
        packages_to_trace = set(initial_package_ids)
        traced_packages = set()
        
        max_iterations = 50
        iteration = 0
        
        mode_msg = "CON todos los hermanos" if include_siblings else "Conexión directa"
        print(f"[TraceabilityService] Iniciando trazabilidad HACIA ADELANTE ({mode_msg}) desde {len(packages_to_trace)} paquetes")
        
        # =====================================================
        # FASE 1: Recopilar TODOS los movimientos hacia ADELANTE
        # =====================================================
        while packages_to_trace and iteration < max_iterations:
            iteration += 1
            
            current_packages = list(packages_to_trace - traced_packages)
            if not current_packages:
                break
                
            print(f"[TraceabilityService] Iteración {iteration}: {len(current_packages)} paquetes a procesar")
            
            try:
                # Buscar dónde estos paquetes son ENTRADA (package_id) de procesos
                in_moves = self.odoo.search_read(
                    "stock.move.line",
                    [
                        ("package_id", "in", current_packages),
                        ("qty_done", ">", 0),
                        ("state", "=", "done"),
                    ],
                    fields,
                    limit=limit,
                    order="date asc"
                )
                
                # Recopilar referencias de procesos
                new_references = set()
                for ml in in_moves:
                    if ml["id"] not in processed_move_ids:
                        all_move_lines.append(ml)
                        processed_move_ids.add(ml["id"])
                    
                    ref = ml.get("reference")
                    if ref and ref not in processed_references:
                        new_references.add(ref)
                
                # Para cada proceso, obtener TODOS los movimientos (inputs y outputs)
                for ref in new_references:
                    ref_moves = self.odoo.search_read(
                        "stock.move.line",
                        [
                            ("reference", "=", ref),
                            ("qty_done", ">", 0),
                            ("state", "=", "done"),
                        ],
                        fields,
                        limit=500,
                        order="date asc"
                    )
                    
                    for ml in ref_moves:
                        if ml["id"] not in processed_move_ids:
                            all_move_lines.append(ml)
                            processed_move_ids.add(ml["id"])
                        
                        # Los OUTPUTS generados se siguen hacia adelante
                        result_rel = ml.get("result_package_id")
                        loc_dest_id = ml.get("location_dest_id")
                        loc_dest_id = loc_dest_id[0] if isinstance(loc_dest_id, (list, tuple)) else loc_dest_id
                        
                        if result_rel:
                            result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
                            # Solo seguir si NO va a clientes (seguir la cadena interna)
                            if result_id and loc_dest_id != self.PARTNER_CUSTOMERS_LOCATION_ID:
                                packages_to_trace.add(result_id)
                    
                    processed_references.add(ref)
                
                traced_packages.update(current_packages)
                
            except Exception as e:
                print(f"[TraceabilityService] Error en iteración {iteration}: {e}")
                import traceback
                traceback.print_exc()
                break
        
        # Buscar movimientos hacia CLIENTES (salidas finales)
        try:
            all_package_ids = set()
            for ml in all_move_lines:
                pkg_rel = ml.get("package_id")
                result_rel = ml.get("result_package_id")
                
                if pkg_rel:
                    pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
                    if pkg_id:
                        all_package_ids.add(pkg_id)
                
                if result_rel:
                    result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
                    if result_id:
                        all_package_ids.add(result_id)
            
            if all_package_ids:
                customer_moves = self.odoo.search_read(
                    "stock.move.line",
                    [
                        ("package_id", "in", list(all_package_ids)),
                        ("location_dest_id", "=", self.PARTNER_CUSTOMERS_LOCATION_ID),
                        ("qty_done", ">", 0),
                        ("state", "=", "done"),
                    ],
                    fields,
                    limit=1000,
                    order="date asc"
                )
                
                for ml in customer_moves:
                    if ml["id"] not in processed_move_ids:
                        all_move_lines.append(ml)
                        processed_move_ids.add(ml["id"])
                
                print(f"[TraceabilityService] Encontrados {len(customer_moves)} movimientos hacia clientes")
        except Exception as e:
            print(f"[TraceabilityService] Error buscando movimientos a clientes: {e}")
        
        # Buscar movimientos de RECEPCIÓN (para incluir los pallets iniciales en el diagrama)
        try:
            reception_moves = self.odoo.search_read(
                "stock.move.line",
                [
                    ("result_package_id", "in", initial_package_ids),
                    ("location_id", "=", self.PARTNER_VENDORS_LOCATION_ID),
                    ("qty_done", ">", 0),
                    ("state", "=", "done"),
                ],
                fields,
                limit=500,
                order="date asc"
            )
            
            for ml in reception_moves:
                if ml["id"] not in processed_move_ids:
                    all_move_lines.append(ml)
                    processed_move_ids.add(ml["id"])
            
            print(f"[TraceabilityService] Encontrados {len(reception_moves)} movimientos de recepción")
        except Exception as e:
            print(f"[TraceabilityService] Error buscando recepciones: {e}")
        
        print(f"[TraceabilityService] Total movimientos hacia ADELANTE: {len(all_move_lines)}")
        
        if not all_move_lines:
            return self._empty_result()
        
        # Procesar movimientos
        result = self._process_move_lines(all_move_lines, virtual_ids)
        result["move_lines"] = all_move_lines
        
        # Resolver proveedores y clientes
        self._resolve_partners(result)
        
        # Enriquecer con fechas
        self._enrich_with_pallet_dates(result)
        self._enrich_with_mrp_dates(result)
        
        # =====================================================
        # FASE 2: Si include_siblings=False, filtrar el resultado procesado
        # =====================================================
        if not include_siblings:
            result = self._filter_forward_direct_connection(result, initial_package_ids)
        
        return result
    
    def _filter_forward_direct_connection(
        self, 
        result: Dict,
        initial_package_ids: List[int]
    ) -> Dict:
        """
        Filtra resultado de trazabilidad HACIA ADELANTE para quedarnos solo con la cadena conectada.
        
        Estrategia:
        1. Empezar desde los pallets iniciales (recepción)
        2. Hacer BFS hacia ADELANTE siguiendo los links
        3. Incluir solo nodos que están en la cadena directa desde la recepción
        """
        pallets = result.get("pallets", {})
        processes = result.get("processes", {})
        suppliers = result.get("suppliers", {})
        customers = result.get("customers", {})
        links = result.get("links", [])
        
        print(f"[TraceabilityService] Filtrando FORWARD conexión directa desde {len(initial_package_ids)} pallets iniciales")
        print(f"[TraceabilityService] Antes del filtro: {len(pallets)} pallets, {len(processes)} procesos, {len(links)} links")
        
        # Construir grafo dirigido desde los links
        graph_forward = {}  # source -> [targets]
        graph_backward = {}  # target -> [sources]
        
        for link in links:
            source_type, source_id, target_type, target_id, qty = link
            
            source_node = f"{source_type}:{source_id}"
            target_node = f"{target_type}:{target_id}"
            
            if source_node not in graph_forward:
                graph_forward[source_node] = []
            graph_forward[source_node].append(target_node)
            
            if target_node not in graph_backward:
                graph_backward[target_node] = []
            graph_backward[target_node].append(source_node)
        
        # BFS desde pallets iniciales HACIA ADELANTE
        connected_nodes = set()
        queue = []
        
        # Agregar pallets iniciales
        for pkg_id in initial_package_ids:
            node = f"PALLET:{pkg_id}"
            connected_nodes.add(node)
            queue.append(node)
        
        # Agregar recepciones que generaron estos pallets (hacia atrás solo un paso)
        for pkg_id in initial_package_ids:
            node = f"PALLET:{pkg_id}"
            for source in graph_backward.get(node, []):
                if source.startswith("RECV:"):
                    connected_nodes.add(source)
                    # Agregar el proveedor de esta recepción
                    ref = source.replace("RECV:", "")
                    proc_info = processes.get(ref, {})
                    supplier_id = proc_info.get("supplier_id")
                    if supplier_id:
                        connected_nodes.add(f"SUPPLIER:{supplier_id}")
        
        # BFS hacia ADELANTE
        visited = set()
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            # Seguir todos los targets (hacia adelante)
            for target in graph_forward.get(current, []):
                if target not in connected_nodes:
                    connected_nodes.add(target)
                    # Solo agregar a la cola si es un pallet (para seguir la cadena)
                    # Los procesos y clientes se agregan pero no se expanden más
                    if target.startswith("PALLET:"):
                        queue.append(target)
                    elif target.startswith("PROCESS:"):
                        queue.append(target)
                        # Cuando llegamos a un proceso, incluir TODOS sus outputs
                        for proc_target in graph_forward.get(target, []):
                            if proc_target.startswith("PALLET:") and proc_target not in connected_nodes:
                                connected_nodes.add(proc_target)
                                queue.append(proc_target)
        
        print(f"[TraceabilityService] Nodos conectados hacia adelante: {len(connected_nodes)}")
        
        # Filtrar pallets
        filtered_pallets = {}
        for pid, pinfo in pallets.items():
            if f"PALLET:{pid}" in connected_nodes:
                filtered_pallets[pid] = pinfo
        
        # Filtrar procesos
        filtered_processes = {}
        for ref, pinfo in processes.items():
            proc_node = f"RECV:{ref}" if pinfo.get("is_reception") else f"PROCESS:{ref}"
            if proc_node in connected_nodes:
                filtered_processes[ref] = pinfo
        
        # Filtrar proveedores
        filtered_suppliers = {}
        for sid, sinfo in suppliers.items():
            if f"SUPPLIER:{sid}" in connected_nodes:
                filtered_suppliers[sid] = sinfo
        
        # Filtrar clientes
        filtered_customers = {}
        for cid, cinfo in customers.items():
            if f"CUSTOMER:{cid}" in connected_nodes:
                filtered_customers[cid] = cinfo
        
        # Filtrar links
        filtered_links = []
        for link in links:
            source_type, source_id, target_type, target_id, qty = link
            source_node = f"{source_type}:{source_id}"
            target_node = f"{target_type}:{target_id}"
            
            if source_node in connected_nodes and target_node in connected_nodes:
                filtered_links.append(link)
        
        print(f"[TraceabilityService] Después del filtro: {len(filtered_pallets)} pallets, {len(filtered_processes)} procesos, {len(filtered_links)} links")
        
        return {
            "pallets": filtered_pallets,
            "processes": filtered_processes,
            "suppliers": filtered_suppliers,
            "customers": filtered_customers,
            "links": filtered_links,
            "reception_picking_ids": result.get("reception_picking_ids", []),
            "sale_picking_ids": result.get("sale_picking_ids", []),
            "sale_pallet_pickings": result.get("sale_pallet_pickings", {}),
            "move_lines": result.get("move_lines", [])
        }
    
    def _filter_direct_connection_result(
        self, 
        result: Dict,
        initial_package_ids: List[int]
    ) -> Dict:
        """
        Filtra el resultado procesado para quedarnos solo con la cadena conectada.
        
        Estrategia:
        1. Usar los links ya construidos para hacer BFS desde los pallets iniciales
        2. Marcar todos los nodos alcanzables (hacia atrás y adelante)
        3. Filtrar el resultado para quedarnos solo con nodos conectados
        """
        pallets = result.get("pallets", {})
        processes = result.get("processes", {})
        suppliers = result.get("suppliers", {})
        customers = result.get("customers", {})
        links = result.get("links", [])
        
        print(f"[TraceabilityService] Filtrando conexión directa desde {len(initial_package_ids)} pallets iniciales")
        print(f"[TraceabilityService] Antes del filtro: {len(pallets)} pallets, {len(processes)} procesos, {len(links)} links")
        
        # Construir grafo bidireccional desde los links
        # node_id -> tipo:id (ej: "PALLET:123", "PROCESS:ref", "RECV:ref")
        graph_forward = {}  # source -> [targets]
        graph_backward = {}  # target -> [sources]
        
        for link in links:
            source_type, source_id, target_type, target_id, qty = link
            
            source_node = f"{source_type}:{source_id}"
            target_node = f"{target_type}:{target_id}"
            
            if source_node not in graph_forward:
                graph_forward[source_node] = []
            graph_forward[source_node].append(target_node)
            
            if target_node not in graph_backward:
                graph_backward[target_node] = []
            graph_backward[target_node].append(source_node)
        
        # BFS desde pallets iniciales (hacia atrás y adelante)
        connected_nodes = set()
        queue = []
        
        for pkg_id in initial_package_ids:
            node = f"PALLET:{pkg_id}"
            connected_nodes.add(node)
            queue.append(node)
        
        # Primero: incluir todos los procesos del primer nivel (hermanos)
        first_level_processes = set()
        for pkg_id in initial_package_ids:
            node = f"PALLET:{pkg_id}"
            # Buscar procesos donde este pallet es output
            for source in graph_backward.get(node, []):
                if source.startswith("PROCESS:") or source.startswith("RECV:"):
                    first_level_processes.add(source)
                    connected_nodes.add(source)
        
        # Agregar todos los outputs (hermanos) de los procesos del primer nivel
        for proc_node in first_level_processes:
            for target in graph_forward.get(proc_node, []):
                if target.startswith("PALLET:"):
                    connected_nodes.add(target)
                    queue.append(target)
        
        # Agregar los procesos a la cola para seguir hacia atrás
        queue.extend(first_level_processes)
        
        # BFS hacia atrás (inputs)
        visited = set(initial_package_ids)
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            # Agregar todos los nodos de entrada (hacia atrás)
            for source in graph_backward.get(current, []):
                if source not in connected_nodes:
                    connected_nodes.add(source)
                    queue.append(source)
        
        # Agregar proveedores y clientes conectados
        for node in list(connected_nodes):
            if node.startswith("RECV:"):
                # Buscar proveedor de esta recepción
                ref = node.replace("RECV:", "")
                proc_info = processes.get(ref, {})
                supplier_id = proc_info.get("supplier_id")
                if supplier_id:
                    connected_nodes.add(f"SUPPLIER:{supplier_id}")
        
        for node in list(connected_nodes):
            if node.startswith("PALLET:"):
                # Buscar si este pallet va a un cliente
                for target in graph_forward.get(node, []):
                    if target.startswith("CUSTOMER:"):
                        connected_nodes.add(target)
        
        print(f"[TraceabilityService] Nodos conectados: {len(connected_nodes)}")
        
        # Filtrar pallets
        filtered_pallets = {}
        for pid, pinfo in pallets.items():
            if f"PALLET:{pid}" in connected_nodes:
                filtered_pallets[pid] = pinfo
        
        # Filtrar procesos
        filtered_processes = {}
        for ref, pinfo in processes.items():
            proc_node = f"RECV:{ref}" if pinfo.get("is_reception") else f"PROCESS:{ref}"
            if proc_node in connected_nodes:
                filtered_processes[ref] = pinfo
        
        # Filtrar proveedores
        filtered_suppliers = {}
        for sid, sinfo in suppliers.items():
            if f"SUPPLIER:{sid}" in connected_nodes:
                filtered_suppliers[sid] = sinfo
        
        # Filtrar clientes
        filtered_customers = {}
        for cid, cinfo in customers.items():
            if f"CUSTOMER:{cid}" in connected_nodes:
                filtered_customers[cid] = cinfo
        
        # Filtrar links
        filtered_links = []
        for link in links:
            source_type, source_id, target_type, target_id, qty = link
            source_node = f"{source_type}:{source_id}"
            target_node = f"{target_type}:{target_id}"
            
            if source_node in connected_nodes and target_node in connected_nodes:
                filtered_links.append(link)
        
        print(f"[TraceabilityService] Después del filtro: {len(filtered_pallets)} pallets, {len(filtered_processes)} procesos, {len(filtered_links)} links")
        
        return {
            "pallets": filtered_pallets,
            "processes": filtered_processes,
            "suppliers": filtered_suppliers,
            "customers": filtered_customers,
            "links": filtered_links,
            "reception_picking_ids": result.get("reception_picking_ids", []),
            "sale_picking_ids": result.get("sale_picking_ids", []),
            "sale_pallet_pickings": result.get("sale_pallet_pickings", {}),
            "move_lines": result.get("move_lines", [])
        }

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
    
    def _resolve_partners(self, result: Dict, initial_package_ids: List[int] = None):
        """Resuelve proveedores y clientes desde los pickings.
        
        Args:
            result: Diccionario con datos procesados
            initial_package_ids: IDs de paquetes iniciales para filtrar solo ventas de esos pallets
        """
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
                ["id", "partner_id", "scheduled_date", "origin", "date_done", "name", "x_studio_gua_de_despacho", "x_studio_many2one_field_f1eVZ"]
            )
            pickings_by_id = {p["id"]: p for p in pickings}
            
            # Proveedores
            for ref, pinfo in result["processes"].items():
                if pinfo.get("is_reception") and pinfo.get("picking_id"):
                    picking = pickings_by_id.get(pinfo["picking_id"], {})
                    partner_rel = picking.get("partner_id")
                    date_done_utc = picking.get("date_done", "")
                    scheduled_date_utc = picking.get("scheduled_date", "")
                    
                    # Información adicional de la recepción
                    albaran = picking.get("name", "")  # Referencia del albarán
                    guia_despacho = picking.get("x_studio_gua_de_despacho", "")
                    origen = picking.get("origin", "")  # Documento de origen
                    transportista_rel = picking.get("x_studio_many2one_field_f1eVZ")
                    transportista = ""
                    if transportista_rel:
                        transportista = transportista_rel[1] if isinstance(transportista_rel, (list, tuple)) and len(transportista_rel) > 1 else ""
                    
                    # Convertir fechas UTC a hora Chile
                    date_done = self._convert_utc_to_chile(date_done_utc)
                    scheduled_date = self._convert_utc_to_chile(scheduled_date_utc)
                    
                    # Guardar información adicional en el proceso de recepción
                    pinfo["scheduled_date"] = scheduled_date
                    pinfo["date_done"] = date_done
                    pinfo["albaran"] = albaran
                    pinfo["guia_despacho"] = guia_despacho
                    pinfo["origen"] = origen
                    pinfo["transportista"] = transportista
                    
                    if partner_rel:
                        sid = partner_rel[0] if isinstance(partner_rel, (list, tuple)) else partner_rel
                        sname = partner_rel[1] if isinstance(partner_rel, (list, tuple)) and len(partner_rel) > 1 else "Proveedor"
                        
                        # Guardar proveedor con toda la información
                        if sid not in result["suppliers"]:
                            result["suppliers"][sid] = {
                                "name": sname,
                                "date_done": date_done,
                                "scheduled_date": scheduled_date,
                                "albaran": albaran,
                                "guia_despacho": guia_despacho,
                                "origen": origen,
                                "transportista": transportista
                            }
                        pinfo["supplier_id"] = sid
            
            # Clientes - Agrupar por origin (código de venta) primero
            # FILTRAR: Solo procesar pallets que están en initial_package_ids si se proporcionó
            sales_by_origin = {}  # origin -> {info, pallets[]}
            
            # Filtrar sale_pallet_pickings si tenemos initial_package_ids
            filtered_sale_pickings = sale_pallet_pickings
            if initial_package_ids:
                initial_set = set(initial_package_ids)
                filtered_sale_pickings = {pkg_id: picking_id for pkg_id, picking_id in sale_pallet_pickings.items() if pkg_id in initial_set}
                print(f"[TraceabilityService] Filtrando ventas: {len(sale_pallet_pickings)} pallets totales → {len(filtered_sale_pickings)} pallets iniciales")
            
            print(f"[TraceabilityService] Procesando {len(filtered_sale_pickings)} pallets de venta")
            
            for pkg_id, picking_id in filtered_sale_pickings.items():
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
                
                if origin not in sales_by_origin:
                    partner_rel = picking.get("partner_id")
                    date_done_utc = picking.get("date_done", "")
                    scheduled_date_utc = picking.get("scheduled_date", "")
                    
                    # Convertir fechas UTC a hora Chile
                    date_done = self._convert_utc_to_chile(date_done_utc)
                    scheduled_date = self._convert_utc_to_chile(scheduled_date_utc)
                    
                    cname = "Cliente"
                    if partner_rel:
                        cname = partner_rel[1] if isinstance(partner_rel, (list, tuple)) and len(partner_rel) > 1 else "Cliente"
                    
                    sales_by_origin[origin] = {
                        "name": cname,
                        "date_done": date_done,
                        "scheduled_date": scheduled_date,
                        "sale_order": origin,
                        "pallets": []
                    }
                    print(f"[TraceabilityService] Nueva venta detectada: {origin} - {cname}")
                
                sales_by_origin[origin]["pallets"].append(pkg_id)
            
            print(f"[TraceabilityService] Total ventas únicas: {len(sales_by_origin)}")
            for origin, sale_info in sales_by_origin.items():
                print(f"  - {origin}: {len(sale_info['pallets'])} pallets")
            
            # Crear UN nodo por venta y sus links
            for origin, sale_info in sales_by_origin.items():
                result["customers"][origin] = {
                    "name": sale_info["name"],
                    "date_done": sale_info["date_done"],
                    "scheduled_date": sale_info["scheduled_date"],
                    "sale_order": origin
                }
                
                # Crear links de todos los pallets a este nodo de venta
                for pkg_id in sale_info["pallets"]:
                    pallet_qty = result["pallets"].get(pkg_id, {}).get("qty", 1)
                    result["links"].append(("PALLET", pkg_id, "CUSTOMER", origin, pallet_qty))
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
        """Obtiene pack_date de stock.quant.package para cada pallet."""
        pallet_ids = list(result["pallets"].keys())
        if not pallet_ids:
            return
        
        try:
            packages = self.odoo.read(
                "stock.quant.package",
                pallet_ids,
                ["id", "pack_date", "create_date"]
            )
            for pkg in packages:
                pid = pkg["id"]
                if pid in result["pallets"]:
                    # Usar pack_date si existe, si no usar create_date, si no dejar first_date del movimiento
                    pack_date = pkg.get("pack_date", "")
                    create_date = pkg.get("create_date", "")
                    result["pallets"][pid]["pack_date"] = pack_date or create_date or result["pallets"][pid].get("first_date", "")
        except Exception as e:
            print(f"[TraceabilityService] Error fetching package dates: {e}")
    
    def _enrich_with_mrp_dates(self, result: Dict):
        """Obtiene fechas de inicio/término y producto de mrp.production para procesos."""
        # Buscar MOs que coincidan con las referencias de procesos
        process_refs = [ref for ref, p in result["processes"].items() if not p.get("is_reception")]
        if not process_refs:
            return
        
        try:
            # Buscar MOs por nombre (origin o name)
            mrp_orders = self.odoo.search_read(
                "mrp.production",
                ["|", ("name", "in", process_refs), ("origin", "in", process_refs)],
                ["id", "name", "origin", "x_studio_inicio_de_proceso", "x_studio_termino_de_proceso", "product_id"],
                limit=len(process_refs) * 2
            )
            
            # Crear mapa de MO por referencia
            mrp_by_ref = {}
            for mo in mrp_orders:
                if mo.get("name") in process_refs:
                    mrp_by_ref[mo["name"]] = mo
                if mo.get("origin") in process_refs:
                    mrp_by_ref[mo["origin"]] = mo
            
            # Enriquecer procesos con fechas y producto MRP
            for ref, pinfo in result["processes"].items():
                if ref in mrp_by_ref:
                    mo = mrp_by_ref[ref]
                    
                    # Convertir fechas UTC a hora Chile
                    mrp_start_utc = mo.get("x_studio_inicio_de_proceso", "")
                    mrp_end_utc = mo.get("x_studio_termino_de_proceso", "")
                    
                    pinfo["mrp_start"] = self._convert_utc_to_chile(mrp_start_utc)
                    pinfo["mrp_end"] = self._convert_utc_to_chile(mrp_end_utc)
                    pinfo["mrp_id"] = mo.get("id")
                    
                    # Extraer product_id
                    product_rel = mo.get("product_id")
                    if product_rel:
                        product_id = product_rel[0] if isinstance(product_rel, (list, tuple)) else product_rel
                        product_name = product_rel[1] if isinstance(product_rel, (list, tuple)) and len(product_rel) > 1 else ""
                        pinfo["product_id"] = product_id
                        pinfo["product_name"] = product_name
        except Exception as e:
            print(f"[TraceabilityService] Error fetching MRP dates: {e}")

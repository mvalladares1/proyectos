"""
Cache de trazabilidad con grafo en memoria.
Clasifica movimientos en: Recepciones, Ventas, Procesos Internos.
"""
import os
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from threading import Lock

from diskcache import Cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Singleton
_cache_instance = None
_cache_lock = Lock()


class TraceabilityCache:
    """
    Cache de trazabilidad con persistencia en disco.
    Mantiene datos de stock.move.line y modelos relacionados.
    """
    
    # IDs de ubicaciones especiales
    PARTNER_VENDORS_LOCATION_ID = 4  # Recepciones
    PARTNER_CUSTOMERS_LOCATION_ID = 5  # Ventas
    
    # Versión del esquema de datos. Incrementar para invalidar cache de disco.
    CACHE_VERSION = "v3"
    
    def __init__(self):
        self._initialized = True
        self._loading = False
        self._last_refresh = None
        
        # Disk cache
        cache_dir = os.environ.get('CACHE_DIR', '/app/data/cache')
        os.makedirs(cache_dir, exist_ok=True)
        self.disk_cache = Cache(cache_dir)
        
        # Datos en memoria
        self.move_lines: Dict[int, dict] = {}
        self.packages: Dict[int, dict] = {}
        self.productions: Dict[int, dict] = {}
        self.pickings: Dict[int, dict] = {}
        self.partners: Dict[int, dict] = {}
        self.products: Dict[int, dict] = {}
        self.locations: Dict[int, dict] = {}
        
        # Grafo de relaciones (CORREGIDO):
        # package_origins[pkg_id] = [move_ids donde pkg_id aparece como ORIGEN (package_id)]
        self.package_origins: Dict[int, List[int]] = defaultdict(list)
        # package_destinations[pkg_id] = [move_ids donde pkg_id aparece como DESTINO (result_package_id)]
        self.package_destinations: Dict[int, List[int]] = defaultdict(list)
        
        self.is_loaded = False
        
        # Intentar cargar desde disco
        self._load_from_disk()
    
    def _load_from_disk(self):
        """Carga datos desde disco si existen y la versión coincide."""
        try:
            cached_version = self.disk_cache.get('version')
            if cached_version != self.CACHE_VERSION:
                logger.warning(f"Versión de cache obsoleta ({cached_version} vs {self.CACHE_VERSION}). Ignorando datos de disco.")
                return

            if 'move_lines' in self.disk_cache:
                self.move_lines = self.disk_cache['move_lines']
                self.packages = self.disk_cache.get('packages', {})
                self.productions = self.disk_cache.get('productions', {})
                self.pickings = self.disk_cache.get('pickings', {})
                self.partners = self.disk_cache.get('partners', {})
                self.products = self.disk_cache.get('products', {})
                self.locations = self.disk_cache.get('locations', {})
                self._last_refresh = self.disk_cache.get('last_refresh')
                
                self._build_graph()
                self.is_loaded = True
                logger.info(f"Cache cargado desde disco: {len(self.move_lines)} move_lines")
        except Exception as e:
            logger.warning(f"No se pudo cargar cache de disco: {e}")
    
    def _save_to_disk(self):
        """Persiste datos a disco."""
        try:
            self.disk_cache['version'] = self.CACHE_VERSION
            self.disk_cache['move_lines'] = self.move_lines
            self.disk_cache['packages'] = self.packages
            self.disk_cache['productions'] = self.productions
            self.disk_cache['pickings'] = self.pickings
            self.disk_cache['partners'] = self.partners
            self.disk_cache['products'] = self.products
            self.disk_cache['locations'] = self.locations
            self.disk_cache['last_refresh'] = self._last_refresh
            logger.info("Cache guardado en disco")
        except Exception as e:
            logger.error(f"Error guardando cache: {e}")
    
    def _normalize_data(self, data: List[Dict]) -> List[Dict]:
        """
        Normaliza datos de Odoo.
        Convierte listas [id, name] a solo id (int).
        Convierte False a None.
        """
        normalized = []
        for record in data:
            new_record = {}
            for k, v in record.items():
                if isinstance(v, (list, tuple)):
                    # Es un campo many2one [id, name]
                    new_record[k] = v[0] if v else None
                elif v is False:
                    # Odoo devuelve False para nulls
                    new_record[k] = None
                else:
                    new_record[k] = v
            normalized.append(new_record)
        return normalized

    def _build_graph(self):
        """
        Construye grafo de relaciones desde move_lines.
        
        Lógica:
        - package_origins[pkg_id] = [move_ids] donde pkg_id es el ORIGEN (package_id)
        - package_destinations[pkg_id] = [move_ids] donde pkg_id es el DESTINO (result_package_id)
        
        Esto permite trazabilidad:
        - Backward: buscar moves donde el pallet fue DESTINO, seguir por sus ORIGENES
        - Forward: buscar moves donde el pallet fue ORIGEN, seguir por sus DESTINOS
        """
        self.package_origins.clear()
        self.package_destinations.clear()
        
        for ml_id, ml in self.move_lines.items():
            pkg_from = ml.get('package_id')  # Ya normalizado a int o None
            pkg_to = ml.get('result_package_id')  # Ya normalizado a int o None
            
            # Si hay package_id, este move tiene a ese paquete como ORIGEN
            if pkg_from:
                self.package_origins[pkg_from].append(ml_id)
            
            # Si hay result_package_id, este move tiene a ese paquete como DESTINO
            if pkg_to:
                self.package_destinations[pkg_to].append(ml_id)
        
        logger.info(
            f"Grafo construido: {len(self.package_origins):,} nodos origen, "
            f"{len(self.package_destinations):,} nodos destino"
        )
    
    def _classify_move(self, move: dict) -> str:
        """
        Clasifica un movimiento según su contexto.
        
        Returns:
            "RECEPCION" | "VENTA" | "PROCESO" | "AJUSTE"
        """
        location_id = move.get('location_id')  # Ya normalizado
        location_dest_id = move.get('location_dest_id')  # Ya normalizado
        reference = move.get('reference', '') or ''
        
        # Recepción: viene de Partners/Vendors
        if location_id == self.PARTNER_VENDORS_LOCATION_ID or 'IN' in reference:
            return "RECEPCION"
        
        # Venta: va a Partners/Customers
        if location_dest_id == self.PARTNER_CUSTOMERS_LOCATION_ID or 'OUT' in reference:
            return "VENTA"
        
        # Producción: referencia con MO
        if 'MO' in reference:
            return "PROCESO"
        
        # Ajuste interno
        return "AJUSTE"
    
    def _classify_all_moves(self):
        """Clasifica todos los movimientos y guarda estadísticas."""
        stats = defaultdict(int)
        for ml_id, ml in self.move_lines.items():
            ml['move_type'] = self._classify_move(ml)
            stats[ml['move_type']] += 1
        
        logger.info(f"Clasificación de movimientos: {dict(stats)}")
    
    async def load_all(self):
        """Carga todos los datos desde Odoo."""
        if self._loading:
            logger.info("Carga ya en progreso")
            return
        
        self._loading = True
        start = time.time()
        logger.info("Iniciando carga completa desde Odoo...")
        
        try:
            from shared.odoo_client import OdooClient
            client = OdooClient()
            
            # Cargar move lines (el más pesado)
            logger.info("Cargando stock.move.line...")
            move_lines = client.search_read_batch(
                'stock.move.line',
                [('state', '=', 'done')],
                ['id', 'date', 'product_id', 'qty_done', 'reference', 
                 'package_id', 'result_package_id', 'lot_id', 'location_id',
                 'location_dest_id', 'picking_id', 'move_id', 'state'],
                order='date desc',
                batch_size=5000
            )
            move_lines = self._normalize_data(move_lines)
            self.move_lines = {ml['id']: ml for ml in move_lines}
            logger.info(f"  → {len(self.move_lines):,} move_lines")
            
            # Cargar paquetes
            logger.info("Cargando stock.quant.package...")
            packages = client.search_read_batch(
                'stock.quant.package',
                [],
                ['id', 'name', 'pack_date', 'location_id'],
                batch_size=5000
            )
            packages = self._normalize_data(packages)
            self.packages = {p['id']: p for p in packages}
            logger.info(f"  → {len(self.packages):,} packages")
            
            # Cargar producciones
            logger.info("Cargando mrp.production...")
            productions = client.search_read_batch(
                'mrp.production',
                [],
                ['id', 'name', 'date_planned_start', 'date_finished', 'state', 'product_id'],
                batch_size=5000
            )
            productions = self._normalize_data(productions)
            self.productions = {p['id']: p for p in productions}
            logger.info(f"  → {len(self.productions):,} productions")
            
            # Cargar pickings
            logger.info("Cargando stock.picking...")
            pickings = client.search_read_batch(
                'stock.picking',
                [],
                ['id', 'name', 'scheduled_date', 'date_done', 'state', 'partner_id', 'picking_type_id'],
                batch_size=5000
            )
            pickings = self._normalize_data(pickings)
            self.pickings = {p['id']: p for p in pickings}
            logger.info(f"  → {len(self.pickings):,} pickings")
            
            # Cargar partners
            logger.info("Cargando res.partner...")
            partners = client.search_read_batch(
                'res.partner',
                [('is_company', '=', True)],
                ['id', 'name', 'supplier_rank', 'customer_rank'],
                batch_size=5000
            )
            partners = self._normalize_data(partners)
            self.partners = {p['id']: p for p in partners}
            logger.info(f"  → {len(self.partners):,} partners")
            
            # Cargar productos
            logger.info("Cargando product.product...")
            products = client.search_read_batch(
                'product.product',
                [],
                ['id', 'name', 'default_code', 'categ_id'],
                batch_size=5000
            )
            products = self._normalize_data(products)
            self.products = {p['id']: p for p in products}
            logger.info(f"  → {len(self.products):,} products")
            
            # Cargar ubicaciones
            logger.info("Cargando stock.location...")
            locations = client.search_read_batch(
                'stock.location',
                [],
                ['id', 'name', 'complete_name', 'usage'],
                batch_size=5000
            )
            locations = self._normalize_data(locations)
            self.locations = {loc['id']: loc for loc in locations}
            logger.info(f"  → {len(self.locations):,} locations")
            
            # Construir grafo
            self._build_graph()
            
            # Clasificar movimientos
            self._classify_all_moves()
            
            # Guardar en disco
            self._last_refresh = datetime.now()
            self._save_to_disk()
            
            self.is_loaded = True
            elapsed = time.time() - start
            logger.info(f"Carga completa en {elapsed:.1f}s ({elapsed/60:.1f} min)")
            
        except Exception as e:
            logger.error(f"Error en carga: {e}")
            raise
        finally:
            self._loading = False
    
    async def refresh_incremental(self):
        """Actualiza solo registros nuevos desde última sincronización."""
        if not self.is_loaded or self._loading:
            return
        
        if not self._last_refresh:
            await self.load_all()
            return
        
        self._loading = True
        start = time.time()
        
        try:
            from shared.odoo_client import OdooClient
            client = OdooClient()
            
            since = self._last_refresh.strftime('%Y-%m-%d %H:%M:%S')
            
            # Solo move lines nuevos
            new_moves = client.search_read_batch(
                'stock.move.line',
                [('state', '=', 'done'), ('write_date', '>', since)],
                ['id', 'date', 'product_id', 'qty_done', 'reference',
                 'package_id', 'result_package_id', 'lot_id', 'location_id',
                 'location_dest_id', 'picking_id', 'move_id', 'state'],
                batch_size=5000
            )
            
            new_moves = self._normalize_data(new_moves)
            
            for ml in new_moves:
                self.move_lines[ml['id']] = ml
            
            if new_moves:
                self._build_graph()
                self._classify_all_moves()
                self._last_refresh = datetime.now()
                self._save_to_disk()
                logger.info(f"Refresh: {len(new_moves)} nuevos move_lines en {time.time()-start:.1f}s")
            
        except Exception as e:
            logger.error(f"Error en refresh: {e}")
        finally:
            self._loading = False
    
    def get_package_traceability_backward(self, package_id: int, max_depth: int = 50) -> List[dict]:
        """
        Trazabilidad hacia atrás: de dónde viene este pallet.
        
        Lógica:
        1. Buscar moves donde este pallet fue DESTINO (result_package_id)
        2. Para cada move, seguir hacia su ORIGEN (package_id)
        3. Repetir recursivamente hasta encontrar recepciones o max_depth
        
        Args:
            package_id: ID del paquete a rastrear
            max_depth: Profundidad máxima (evitar ciclos infinitos)
            
        Returns:
            Lista de move_lines ordenados cronológicamente
        """
        visited = set()
        result = []
        
        def traverse(pkg_id: int, depth: int = 0):
            if depth > max_depth or pkg_id in visited:
                return
            visited.add(pkg_id)
            
            # Movimientos donde este pallet fue DESTINO (result_package_id = pkg_id)
            move_ids = self.package_destinations.get(pkg_id, [])
            
            for move_id in move_ids:
                move = self.move_lines.get(move_id)
                if not move:
                    continue
                
                result.append(move)
                
                # Seguir hacia atrás por package_id (origen de este move)
                origin_pkg = move.get('package_id')
                if origin_pkg:
                    traverse(origin_pkg, depth + 1)
        
        traverse(package_id)
        
        # Ordenar por fecha
        result.sort(key=lambda x: x.get('date', ''))
        return result
    
    def get_package_traceability_forward(self, package_id: int, max_depth: int = 50) -> List[dict]:
        """
        Trazabilidad hacia adelante: a dónde fue este pallet.
        
        Lógica:
        1. Buscar moves donde este pallet fue ORIGEN (package_id)
        2. Para cada move, seguir hacia su DESTINO (result_package_id)
        3. Repetir recursivamente hasta encontrar ventas o max_depth
        
        Args:
            package_id: ID del paquete a rastrear
            max_depth: Profundidad máxima (evitar ciclos infinitos)
            
        Returns:
            Lista de move_lines ordenados cronológicamente
        """
        visited = set()
        result = []
        
        def traverse(pkg_id: int, depth: int = 0):
            if depth > max_depth or pkg_id in visited:
                return
            visited.add(pkg_id)
            
            # Movimientos donde este pallet fue ORIGEN (package_id = pkg_id)
            move_ids = self.package_origins.get(pkg_id, [])
            
            for move_id in move_ids:
                move = self.move_lines.get(move_id)
                if not move:
                    continue
                
                result.append(move)
                
                # Seguir hacia adelante por result_package_id (destino de este move)
                dest_pkg = move.get('result_package_id')
                if dest_pkg:
                    traverse(dest_pkg, depth + 1)
        
        traverse(package_id)
        
        # Ordenar por fecha
        result.sort(key=lambda x: x.get('date', ''))
        return result
    
    def get_package_traceability(self, package_id: int, direction: str = "both", max_depth: int = 50) -> Dict:
        """
        Obtiene trazabilidad de un paquete (método legacy para compatibilidad).
        
        Args:
            package_id: ID del paquete
            direction: "backward" (orígenes), "forward" (destinos), "both"
            max_depth: Profundidad máxima de búsqueda
        
        Returns:
            Dict con moves y metadatos
        """
        backward_moves = []
        forward_moves = []
        
        if direction in ("backward", "both"):
            backward_moves = self.get_package_traceability_backward(package_id, max_depth)
        
        if direction in ("forward", "both"):
            forward_moves = self.get_package_traceability_forward(package_id, max_depth)
        
        all_moves = backward_moves + forward_moves
        
        # Deduplicar por ID
        seen = set()
        unique_moves = []
        for move in all_moves:
            if move['id'] not in seen:
                seen.add(move['id'])
                unique_moves.append(move)
        
        return {
            "moves": unique_moves,
            "total": len(unique_moves),
            "package": self.packages.get(package_id, {})
        }
    
    def get_package_graph(self, package_id: int, direction: str = "both", max_depth: int = 50) -> Dict:
        """
        Obtiene grafo de relaciones para visualización.
        Incluye paquetes, ubicaciones y movimientos.
        
        Args:
            package_id: ID del paquete central
            direction: "backward", "forward", o "both"
            max_depth: Profundidad máxima
            
        Returns:
            Dict con nodes y edges para visualización
        """
        nodes = {}
        edges = []
        visited_packages = set()
        
        def add_location_node(loc_id: int, loc_type: str):
            """Agrega nodo de ubicación si no existe."""
            node_id = f"LOC-{loc_id}"
            if node_id not in nodes:
                loc = self.locations.get(loc_id, {})
                nodes[node_id] = {
                    "id": node_id,
                    "type": "location",
                    "location_type": loc_type,
                    "name": loc.get("name", f"Location {loc_id}"),
                    "complete_name": loc.get("complete_name", ""),
                }
            return node_id
        
        def traverse(pkg_id: int, depth: int, dir: str):
            if depth > max_depth or pkg_id in visited_packages:
                return
            visited_packages.add(pkg_id)
            
            # Agregar nodo del paquete
            pkg = self.packages.get(pkg_id, {})
            nodes[f"PKG-{pkg_id}"] = {
                "id": f"PKG-{pkg_id}",
                "type": "package",
                "package_id": pkg_id,
                "name": pkg.get("name", f"PKG-{pkg_id}"),
                "pack_date": pkg.get("pack_date"),
            }
            
            # Backward: buscar orígenes
            if dir in ("backward", "both"):
                move_ids = self.package_destinations.get(pkg_id, [])
                for move_id in move_ids:
                    move = self.move_lines.get(move_id)
                    if not move:
                        continue
                    
                    origin_pkg = move.get('package_id')
                    if origin_pkg:
                        # Conexión paquete → paquete
                        edges.append({
                            "source": f"PKG-{origin_pkg}",
                            "target": f"PKG-{pkg_id}",
                            "move_id": move_id,
                            "move_type": move.get('move_type', 'UNKNOWN'),
                            "reference": move.get('reference'),
                            "date": move.get('date'),
                            "qty": move.get('qty_done')
                        })
                        traverse(origin_pkg, depth + 1, "backward")
                    else:
                        # No hay paquete origen, viene de una ubicación
                        loc_id = move.get('location_id')
                        if loc_id:
                            source_node = add_location_node(loc_id, "origin")
                            edges.append({
                                "source": source_node,
                                "target": f"PKG-{pkg_id}",
                                "move_id": move_id,
                                "move_type": move.get('move_type', 'UNKNOWN'),
                                "reference": move.get('reference'),
                                "date": move.get('date'),
                                "qty": move.get('qty_done')
                            })
            
            # Forward: buscar destinos
            if dir in ("forward", "both"):
                move_ids = self.package_origins.get(pkg_id, [])
                for move_id in move_ids:
                    move = self.move_lines.get(move_id)
                    if not move:
                        continue
                    
                    dest_pkg = move.get('result_package_id')
                    if dest_pkg:
                        # Conexión paquete → paquete
                        edges.append({
                            "source": f"PKG-{pkg_id}",
                            "target": f"PKG-{dest_pkg}",
                            "move_id": move_id,
                            "move_type": move.get('move_type', 'UNKNOWN'),
                            "reference": move.get('reference'),
                            "date": move.get('date'),
                            "qty": move.get('qty_done')
                        })
                        traverse(dest_pkg, depth + 1, "forward")
                    else:
                        # No hay paquete destino, va a una ubicación
                        loc_id = move.get('location_dest_id')
                        if loc_id:
                            target_node = add_location_node(loc_id, "destination")
                            edges.append({
                                "source": f"PKG-{pkg_id}",
                                "target": target_node,
                                "move_id": move_id,
                                "move_type": move.get('move_type', 'UNKNOWN'),
                                "reference": move.get('reference'),
                                "date": move.get('date'),
                                "qty": move.get('qty_done')
                            })
        
        traverse(package_id, 0, direction)
        
        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }
    
    def get_all_package_relationships(self) -> Dict:
        """
        Obtiene TODAS las relaciones paquete→paquete del grafo.
        ADVERTENCIA: Puede ser muy grande (180k moves).
        
        Returns:
            Dict con estadísticas y sample de relaciones
        """
        relationships = defaultdict(set)
        
        # Construir relaciones desde move_lines
        for ml_id, ml in self.move_lines.items():
            pkg_from = ml.get('package_id')
            pkg_to = ml.get('result_package_id')
            
            if pkg_from and pkg_to and pkg_from != pkg_to:
                relationships[pkg_from].add(pkg_to)
        
        # Convertir sets a lists para JSON
        relationships_list = {
            pkg: list(dests) for pkg, dests in relationships.items()
        }
        
        total_relationships = sum(len(dests) for dests in relationships.values())
        
        return {
            "total_packages_with_destinations": len(relationships),
            "total_relationships": total_relationships,
            "sample": dict(list(relationships_list.items())[:10]),  # Muestra 10
            "stats": {
                "packages_with_1_dest": sum(1 for d in relationships.values() if len(d) == 1),
                "packages_with_2_5_dest": sum(1 for d in relationships.values() if 2 <= len(d) <= 5),
                "packages_with_5plus_dest": sum(1 for d in relationships.values() if len(d) > 5),
            }
        }
    
    def get_package_debug_info(self, package_id: int) -> Dict:
        """
        Información de debug para un paquete.
        Muestra si tiene movimientos y cuáles son.
        """
        pkg = self.packages.get(package_id, {})
        
        # Movimientos donde es origen
        origin_move_ids = self.package_origins.get(package_id, [])
        origin_moves = [self.move_lines.get(mid) for mid in origin_move_ids if mid in self.move_lines]
        
        # Movimientos donde es destino
        dest_move_ids = self.package_destinations.get(package_id, [])
        dest_moves = [self.move_lines.get(mid) for mid in dest_move_ids if mid in self.move_lines]
        
        return {
            "package": pkg,
            "has_moves_as_origin": len(origin_move_ids),
            "has_moves_as_destination": len(dest_move_ids),
            "origin_moves_sample": origin_moves[:3],  # Muestra 3
            "destination_moves_sample": dest_moves[:3],  # Muestra 3
            "in_graph_origins": package_id in self.package_origins,
            "in_graph_destinations": package_id in self.package_destinations
        }
    
    def export_full_graph_gexf(self) -> str:
        """
        Exporta el grafo completo en formato GEXF (Gephi).
        Incluye todos los paquetes, ubicaciones y sus relaciones.
        
        Returns:
            String con XML en formato GEXF
        """
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        
        # Crear estructura GEXF
        gexf = Element('gexf', {
            'xmlns': 'http://www.gexf.net/1.2draft',
            'version': '1.2'
        })
        
        graph = SubElement(gexf, 'graph', {
            'mode': 'static',
            'defaultedgetype': 'directed'
        })
        
        # Atributos de nodos
        attributes = SubElement(graph, 'attributes', {'class': 'node'})
        SubElement(attributes, 'attribute', {'id': '0', 'title': 'type', 'type': 'string'})
        SubElement(attributes, 'attribute', {'id': '1', 'title': 'pack_date', 'type': 'string'})
        SubElement(attributes, 'attribute', {'id': '2', 'title': 'location_name', 'type': 'string'})
        
        # Atributos de aristas
        edge_attributes = SubElement(graph, 'attributes', {'class': 'edge'})
        SubElement(edge_attributes, 'attribute', {'id': '0', 'title': 'move_type', 'type': 'string'})
        SubElement(edge_attributes, 'attribute', {'id': '1', 'title': 'reference', 'type': 'string'})
        SubElement(edge_attributes, 'attribute', {'id': '2', 'title': 'date', 'type': 'string'})
        SubElement(edge_attributes, 'attribute', {'id': '3', 'title': 'qty', 'type': 'double'})
        
        nodes = SubElement(graph, 'nodes')
        edges = SubElement(graph, 'edges')
        
        # Agregar nodos de paquetes
        for pkg_id, pkg in self.packages.items():
            node = SubElement(nodes, 'node', {
                'id': f'PKG-{pkg_id}',
                'label': pkg.get('name', f'PKG-{pkg_id}')
            })
            attvalues = SubElement(node, 'attvalues')
            SubElement(attvalues, 'attvalue', {'for': '0', 'value': 'package'})
            if pkg.get('pack_date'):
                SubElement(attvalues, 'attvalue', {'for': '1', 'value': str(pkg['pack_date'])})
        
        # Agregar nodos de ubicaciones usadas
        location_nodes = set()
        
        # Agregar aristas de movimientos
        edge_id = 0
        for ml_id, ml in self.move_lines.items():
            pkg_from = ml.get('package_id')
            pkg_to = ml.get('result_package_id')
            
            source = None
            target = None
            
            # Determinar source
            if pkg_from:
                source = f'PKG-{pkg_from}'
            else:
                loc_id = ml.get('location_id')
                if loc_id:
                    source = f'LOC-{loc_id}'
                    if source not in location_nodes:
                        location_nodes.add(source)
                        loc = self.locations.get(loc_id, {})
                        node = SubElement(nodes, 'node', {
                            'id': source,
                            'label': loc.get('name', f'LOC-{loc_id}')
                        })
                        attvalues = SubElement(node, 'attvalues')
                        SubElement(attvalues, 'attvalue', {'for': '0', 'value': 'location'})
                        SubElement(attvalues, 'attvalue', {'for': '2', 'value': loc.get('complete_name', '')})
            
            # Determinar target
            if pkg_to:
                target = f'PKG-{pkg_to}'
            else:
                loc_id = ml.get('location_dest_id')
                if loc_id:
                    target = f'LOC-{loc_id}'
                    if target not in location_nodes:
                        location_nodes.add(target)
                        loc = self.locations.get(loc_id, {})
                        node = SubElement(nodes, 'node', {
                            'id': target,
                            'label': loc.get('name', f'LOC-{loc_id}')
                        })
                        attvalues = SubElement(node, 'attvalues')
                        SubElement(attvalues, 'attvalue', {'for': '0', 'value': 'location'})
                        SubElement(attvalues, 'attvalue', {'for': '2', 'value': loc.get('complete_name', '')})
            
            # Crear arista si hay source y target
            if source and target:
                edge = SubElement(edges, 'edge', {
                    'id': str(edge_id),
                    'source': source,
                    'target': target
                })
                attvalues = SubElement(edge, 'attvalues')
                SubElement(attvalues, 'attvalue', {'for': '0', 'value': ml.get('move_type', 'UNKNOWN')})
                SubElement(attvalues, 'attvalue', {'for': '1', 'value': ml.get('reference', '')})
                SubElement(attvalues, 'attvalue', {'for': '2', 'value': ml.get('date', '')})
                SubElement(attvalues, 'attvalue', {'for': '3', 'value': str(ml.get('qty_done', 0))})
                edge_id += 1
        
        # Convertir a string con formato
        rough_string = tostring(gexf, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent='  ')


def get_cache() -> TraceabilityCache:
    """Singleton del cache."""
    global _cache_instance
    with _cache_lock:
        if _cache_instance is None:
            _cache_instance = TraceabilityCache()
        return _cache_instance

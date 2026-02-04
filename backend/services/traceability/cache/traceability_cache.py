"""
Caché de trazabilidad con grafo en memoria.
Mantiene stock.move.line y modelos relacionados para consultas instantáneas.
"""
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from threading import Lock
import asyncio

from diskcache import Cache
from shared.odoo_client import OdooClient

logger = logging.getLogger(__name__)


class TraceabilityCache:
    """
    Singleton que mantiene caché de trazabilidad.
    
    Estructura:
    - Datos en memoria (dicts) para acceso instantáneo
    - Grafo de relaciones package_id -> move_lines
    - Persistencia en disco con diskcache
    - Refresh incremental cada 5 minutos
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Evitar reinicialización
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._loading = False
        self._last_refresh = None
        
        # Disk cache - usar path absoluto para compatibilidad con Docker
        cache_dir = os.environ.get('CACHE_DIR', '/app/cache/traceability')
        # Crear directorio si no existe
        os.makedirs(cache_dir, exist_ok=True)
        self.disk_cache = Cache(cache_dir)
        
        # Datos en memoria
        self.move_lines: Dict[int, dict] = {}
        self.packages: Dict[int, dict] = {}
        self.productions: Dict[int, dict] = {}
        self.pickings: Dict[int, dict] = {}
        self.sales: Dict[int, dict] = {}
        self.purchases: Dict[int, dict] = {}
        self.partners: Dict[int, dict] = {}
        self.products: Dict[int, dict] = {}
        self.locations: Dict[int, dict] = {}
        
        # Grafo de trazabilidad
        # package_id -> list[move_line_ids] donde es origen
        self.package_origins: Dict[int, List[int]] = defaultdict(list)
        # package_id -> list[move_line_ids] donde es destino
        self.package_destinations: Dict[int, List[int]] = defaultdict(list)
        
        # Estado
        self.is_loaded = False
        self.load_start_time = None
        self.load_end_time = None
        
        logger.info("TraceabilityCache inicializado")
    
    async def load_all(self, force_reload: bool = False):
        """
        Carga completa de todos los modelos.
        Intenta cargar de disco, si falla o es muy antiguo, carga de Odoo.
        """
        if self._loading:
            logger.warning("Ya hay una carga en progreso")
            return
        
        self._loading = True
        self.load_start_time = datetime.now()
        
        try:
            # Intentar cargar de disco
            if not force_reload and self._load_from_disk():
                logger.info("Caché cargado desde disco")
                # Hacer refresh incremental
                await self.refresh_incremental()
            else:
                # Carga completa desde Odoo
                logger.info("Cargando datos desde Odoo...")
                await self._load_from_odoo()
                self._save_to_disk()
                logger.info("Datos guardados en disco")
            
            self._build_graph()
            self.is_loaded = True
            self.load_end_time = datetime.now()
            self._last_refresh = datetime.now()
            
            elapsed = (self.load_end_time - self.load_start_time).total_seconds()
            logger.info(f"Caché cargado completamente en {elapsed:.1f}s")
            logger.info(f"  - Move lines: {len(self.move_lines):,}")
            logger.info(f"  - Packages: {len(self.packages):,}")
            logger.info(f"  - Productions: {len(self.productions):,}")
            
        except Exception as e:
            logger.error(f"Error cargando caché: {e}", exc_info=True)
            raise
        finally:
            self._loading = False
    
    def _load_from_disk(self) -> bool:
        """Intenta cargar desde disco. Retorna True si exitoso."""
        try:
            metadata = self.disk_cache.get('metadata')
            if not metadata:
                logger.info("No hay caché en disco")
                return False
            
            last_save = metadata.get('last_save')
            if not last_save:
                return False
            
            # Si el caché tiene más de 1 día, recargar
            age = datetime.now() - datetime.fromisoformat(last_save)
            if age > timedelta(days=1):
                logger.info(f"Caché muy antiguo ({age}), recargando")
                return False
            
            logger.info("Cargando desde disco...")
            self.move_lines = self.disk_cache.get('move_lines', {})
            self.packages = self.disk_cache.get('packages', {})
            self.productions = self.disk_cache.get('productions', {})
            self.pickings = self.disk_cache.get('pickings', {})
            self.sales = self.disk_cache.get('sales', {})
            self.purchases = self.disk_cache.get('purchases', {})
            self.partners = self.disk_cache.get('partners', {})
            self.products = self.disk_cache.get('products', {})
            self.locations = self.disk_cache.get('locations', {})
            
            logger.info(f"Cargado {len(self.move_lines):,} move_lines desde disco")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando desde disco: {e}")
            return False
    
    def _save_to_disk(self):
        """Guarda datos en disco."""
        try:
            self.disk_cache.set('metadata', {
                'last_save': datetime.now().isoformat(),
                'record_counts': {
                    'move_lines': len(self.move_lines),
                    'packages': len(self.packages),
                    'productions': len(self.productions),
                }
            })
            self.disk_cache.set('move_lines', self.move_lines)
            self.disk_cache.set('packages', self.packages)
            self.disk_cache.set('productions', self.productions)
            self.disk_cache.set('pickings', self.pickings)
            self.disk_cache.set('sales', self.sales)
            self.disk_cache.set('purchases', self.purchases)
            self.disk_cache.set('partners', self.partners)
            self.disk_cache.set('products', self.products)
            self.disk_cache.set('locations', self.locations)
            
        except Exception as e:
            logger.error(f"Error guardando en disco: {e}")
    
    async def _load_from_odoo(self):
        """Carga completa desde Odoo."""
        try:
            odoo = OdooClient()
        except Exception as e:
            logger.error(f"No se pudo conectar a Odoo: {e}")
            logger.warning("Caché de trazabilidad NO disponible. Usando método legacy.")
            return
        
        # 1. Move lines (el más pesado)
        logger.info("Cargando move_lines...")
        await self._load_model_batched(
            odoo,
            "stock.move.line",
            [("state", "=", "done"), ("qty_done", ">", 0)],
            ["id", "reference", "package_id", "result_package_id", "date",
             "location_id", "location_dest_id", "product_id", "qty_done", 
             "move_id", "picking_id", "state"],
            self.move_lines,
            batch_size=30000
        )
        
        # 2. Packages
        logger.info("Cargando packages...")
        await self._load_model_batched(
            odoo,
            "stock.quant.package",
            [],
            ["id", "name", "location_id"],
            self.packages,
            batch_size=30000
        )
        
        # 3. Productions
        logger.info("Cargando productions...")
        await self._load_model_simple(
            odoo,
            "mrp.production",
            [("state", "in", ["done", "progress", "confirmed"])],
            ["id", "name", "product_id", "product_qty", "date_start", 
             "date_finished", "state"],
            self.productions
        )
        
        # 4. Pickings
        logger.info("Cargando pickings...")
        await self._load_model_batched(
            odoo,
            "stock.picking",
            [("state", "=", "done")],
            ["id", "name", "partner_id", "scheduled_date", "date_done",
             "picking_type_id", "origin", "sale_id", "purchase_id"],
            self.pickings,
            batch_size=10000
        )
        
        # 5-9. Otros modelos (más pequeños)
        logger.info("Cargando otros modelos...")
        
        await self._load_model_simple(
            odoo, "sale.order",
            [("state", "in", ["sale", "done"])],
            ["id", "name", "partner_id", "date_order", "state"],
            self.sales
        )
        
        await self._load_model_simple(
            odoo, "purchase.order",
            [("state", "in", ["purchase", "done"])],
            ["id", "name", "partner_id", "date_order", "state"],
            self.purchases
        )
        
        await self._load_model_simple(
            odoo, "res.partner",
            [("active", "=", True)],
            ["id", "name", "vat", "city"],
            self.partners
        )
        
        await self._load_model_simple(
            odoo, "product.product",
            [("active", "=", True)],
            ["id", "name", "default_code"],
            self.products
        )
        
        await self._load_model_simple(
            odoo, "stock.location",
            [("usage", "in", ["internal", "transit"])],
            ["id", "name", "complete_name", "usage"],
            self.locations
        )
    
    async def _load_model_batched(self, odoo: OdooClient, model: str, 
                                   domain: List, fields: List[str],
                                   target_dict: Dict[int, dict], 
                                   batch_size: int = 30000):
        """Carga un modelo en batches para evitar timeouts."""
        offset = 0
        total_loaded = 0
        
        while True:
            # Buscar IDs en este batch
            batch_domain = domain + [("id", ">", offset)] if offset > 0 else domain
            
            records = odoo.search_read(
                model, batch_domain, fields,
                limit=batch_size, order="id asc"
            )
            
            if not records:
                break
            
            for record in records:
                target_dict[record['id']] = record
                offset = max(offset, record['id'])
            
            total_loaded += len(records)
            logger.info(f"  {model}: {total_loaded:,} registros...")
            
            if len(records) < batch_size:
                break
            
            # Pequeña pausa para no saturar
            await asyncio.sleep(0.1)
        
        logger.info(f"  {model}: {total_loaded:,} registros total")
    
    async def _load_model_simple(self, odoo: OdooClient, model: str,
                                  domain: List, fields: List[str],
                                  target_dict: Dict[int, dict]):
        """Carga un modelo simple (pocos registros)."""
        records = odoo.search_read(model, domain, fields)
        for record in records:
            target_dict[record['id']] = record
        logger.info(f"  {model}: {len(records):,} registros")
    
    def _build_graph(self):
        """Construye el grafo de trazabilidad."""
        logger.info("Construyendo grafo de trazabilidad...")
        
        self.package_origins.clear()
        self.package_destinations.clear()
        
        for move_id, move in self.move_lines.items():
            # package_id -> move_line (origen)
            pkg_id = move.get('package_id')
            if pkg_id and isinstance(pkg_id, (list, tuple)):
                pkg_id = pkg_id[0]
            if pkg_id:
                self.package_origins[pkg_id].append(move_id)
            
            # result_package_id -> move_line (destino)
            result_pkg_id = move.get('result_package_id')
            if result_pkg_id and isinstance(result_pkg_id, (list, tuple)):
                result_pkg_id = result_pkg_id[0]
            if result_pkg_id:
                self.package_destinations[result_pkg_id].append(move_id)
        
        logger.info(f"Grafo construido: {len(self.package_origins):,} nodos origen")
    
    async def refresh_incremental(self):
        """Actualiza solo registros nuevos desde último refresh."""
        if not self.is_loaded:
            logger.warning("Caché no está cargado, no se puede hacer refresh")
            return
        
        logger.info("Refresh incremental iniciado...")
        odoo = OdooClient()
        
        try:
            # Obtener último ID de move_lines
            max_id = max(self.move_lines.keys()) if self.move_lines else 0
            
            # Traer solo registros nuevos
            new_records = odoo.search_read(
                "stock.move.line",
                [("id", ">", max_id), ("state", "=", "done"), ("qty_done", ">", 0)],
                ["id", "reference", "package_id", "result_package_id", "date",
                 "location_id", "location_dest_id", "product_id", "qty_done",
                 "move_id", "picking_id", "state"],
                limit=5000
            )
            
            if new_records:
                for record in new_records:
                    self.move_lines[record['id']] = record
                
                # Actualizar grafo con nuevos registros
                for move_id, move in [(r['id'], r) for r in new_records]:
                    pkg_id = move.get('package_id')
                    if pkg_id and isinstance(pkg_id, (list, tuple)):
                        pkg_id = pkg_id[0]
                    if pkg_id:
                        self.package_origins[pkg_id].append(move_id)
                    
                    result_pkg_id = move.get('result_package_id')
                    if result_pkg_id and isinstance(result_pkg_id, (list, tuple)):
                        result_pkg_id = result_pkg_id[0]
                    if result_pkg_id:
                        self.package_destinations[result_pkg_id].append(move_id)
                
                logger.info(f"Refresh: {len(new_records)} nuevos move_lines")
                
                # Guardar en disco
                self._save_to_disk()
            else:
                logger.info("Refresh: sin registros nuevos")
            
            self._last_refresh = datetime.now()
            
        except Exception as e:
            logger.error(f"Error en refresh incremental: {e}", exc_info=True)
    
    def get_package_traceability_backward(self, package_id: int, 
                                         max_depth: int = 50) -> List[dict]:
        """
        Trazabilidad hacia atrás: de dónde viene este pallet.
        Retorna lista de move_lines en orden cronológico.
        """
        visited = set()
        result = []
        
        def traverse(pkg_id: int, depth: int = 0):
            if depth > max_depth or pkg_id in visited:
                return
            visited.add(pkg_id)
            
            # Movimientos donde este pallet fue DESTINO (result_package_id)
            move_ids = self.package_destinations.get(pkg_id, [])
            
            for move_id in move_ids:
                move = self.move_lines.get(move_id)
                if not move:
                    continue
                
                result.append(move)
                
                # Seguir hacia atrás por package_id
                origin_pkg = move.get('package_id')
                if origin_pkg and isinstance(origin_pkg, (list, tuple)):
                    origin_pkg = origin_pkg[0]
                if origin_pkg:
                    traverse(origin_pkg, depth + 1)
        
        traverse(package_id)
        
        # Ordenar por fecha
        result.sort(key=lambda x: x.get('date', ''))
        return result
    
    def get_package_traceability_forward(self, package_id: int,
                                        max_depth: int = 50) -> List[dict]:
        """
        Trazabilidad hacia adelante: a dónde fue este pallet.
        Retorna lista de move_lines en orden cronológico.
        """
        visited = set()
        result = []
        
        def traverse(pkg_id: int, depth: int = 0):
            if depth > max_depth or pkg_id in visited:
                return
            visited.add(pkg_id)
            
            # Movimientos donde este pallet fue ORIGEN (package_id)
            move_ids = self.package_origins.get(pkg_id, [])
            
            for move_id in move_ids:
                move = self.move_lines.get(move_id)
                if not move:
                    continue
                
                result.append(move)
                
                # Seguir hacia adelante por result_package_id
                dest_pkg = move.get('result_package_id')
                if dest_pkg and isinstance(dest_pkg, (list, tuple)):
                    dest_pkg = dest_pkg[0]
                if dest_pkg:
                    traverse(dest_pkg, depth + 1)
        
        traverse(package_id)
        
        # Ordenar por fecha
        result.sort(key=lambda x: x.get('date', ''))
        return result
    
    def get_status(self) -> dict:
        """Estado del caché."""
        return {
            "is_loaded": self.is_loaded,
            "loading": self._loading,
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
            "load_start": self.load_start_time.isoformat() if self.load_start_time else None,
            "load_end": self.load_end_time.isoformat() if self.load_end_time else None,
            "counts": {
                "move_lines": len(self.move_lines),
                "packages": len(self.packages),
                "productions": len(self.productions),
                "pickings": len(self.pickings),
                "sales": len(self.sales),
                "purchases": len(self.purchases),
                "partners": len(self.partners),
                "products": len(self.products),
                "locations": len(self.locations),
            }
        }


# Singleton global
_cache_instance = None

def get_cache() -> TraceabilityCache:
    """Obtiene la instancia del caché (singleton)."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = TraceabilityCache()
    return _cache_instance

"""
Sistema de Caché para consultas a Odoo.
Reduce llamadas redundantes a la API almacenando datos en memoria con TTL.
"""
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Callable
from threading import Lock
import hashlib
import json


class OdooCache:
    """
    Caché en memoria con TTL (Time To Live) para datos de Odoo.
    
    Thread-safe para uso con FastAPI.
    
    Uso:
        cache = OdooCache(default_ttl=300)  # 5 minutos
        
        # Guardar dato
        cache.set("ubicaciones", data)
        
        # Recuperar dato
        data = cache.get("ubicaciones")  # None si expiró
        
        # Usar con decorator
        @cache.cached(ttl=600)
        def get_productos():
            return odoo.search_read(...)
    """
    
    # TTL predefinidos por tipo de dato (en segundos)
    TTL_UBICACIONES = 3600      # 1 hora - cambian muy raramente
    TTL_PRODUCTOS = 1800        # 30 min - cambios poco frecuentes
    TTL_CATEGORIAS = 1800       # 30 min - cambios poco frecuentes
    TTL_PARTNERS = 1800         # 30 min - cambios poco frecuentes
    TTL_KPIS = 300              # 5 min - datos dinámicos
    TTL_STOCK = 180             # 3 min - datos muy dinámicos
    
    def __init__(self, default_ttl: int = 300):
        """
        Inicializa el caché.
        
        Args:
            default_ttl: Tiempo de vida por defecto en segundos (default: 5 min)
        """
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self._lock = Lock()
        self._default_ttl = default_ttl
        self._stats = {"hits": 0, "misses": 0}
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Genera una clave única basada en los argumentos."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
        return f"{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Obtiene un valor del caché.
        
        Args:
            key: Clave del dato
            
        Returns:
            Valor almacenado o None si no existe o expiró
        """
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if datetime.now() < expiry:
                    self._stats["hits"] += 1
                    return value
                else:
                    # Expirado, eliminar
                    del self._cache[key]
            
            self._stats["misses"] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """
        Almacena un valor en el caché.
        
        Args:
            key: Clave del dato
            value: Valor a almacenar
            ttl: Tiempo de vida en segundos (usa default si no se especifica)
        """
        ttl = ttl or self._default_ttl
        expiry = datetime.now() + timedelta(seconds=ttl)
        
        with self._lock:
            self._cache[key] = (value, expiry)
    
    def invalidate(self, key: str) -> bool:
        """
        Invalida (elimina) una entrada del caché.
        
        Args:
            key: Clave a invalidar
            
        Returns:
            True si se eliminó, False si no existía
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def invalidate_prefix(self, prefix: str) -> int:
        """
        Invalida todas las entradas que empiezan con un prefijo.
        
        Args:
            prefix: Prefijo de las claves a invalidar
            
        Returns:
            Número de entradas eliminadas
        """
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)
    
    def clear(self) -> None:
        """Limpia todo el caché."""
        with self._lock:
            self._cache.clear()
            self._stats = {"hits": 0, "misses": 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché.
        
        Returns:
            Diccionario con hits, misses, hit_rate y entries
        """
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": round(hit_rate, 2),
                "entries": len(self._cache)
            }
    
    def cached(self, prefix: str = "default", ttl: int = None):
        """
        Decorator para funciones que deben usar caché.
        
        Args:
            prefix: Prefijo para la clave de caché
            ttl: Tiempo de vida en segundos
            
        Ejemplo:
            @cache.cached(prefix="productos", ttl=1800)
            def get_productos(categoria_id: int):
                return odoo.search_read(...)
        """
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                # Generar clave única
                cache_key = self._make_key(prefix, *args, **kwargs)
                
                # Intentar obtener del caché
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Ejecutar función y cachear resultado
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            
            # Preservar metadata de la función
            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper
        
        return decorator


# Instancia global del caché (singleton)
# Se usa en todos los servicios para compartir el caché
odoo_cache = OdooCache(default_ttl=300)


def get_cache() -> OdooCache:
    """Retorna la instancia global del caché."""
    return odoo_cache

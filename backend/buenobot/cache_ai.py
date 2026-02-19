"""
BUENOBOT v3.0 - AI Response Cache

Cache de respuestas de IA por commit_sha + evidence_hash.
Evita llamadas repetidas a la API y ahorra costos.
"""
import json
import hashlib
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

from .config import get_ai_config

logger = logging.getLogger(__name__)


class AICache:
    """
    Cache de respuestas IA.
    
    Estrategia de cache:
    - Key: commit_sha + evidence_hash + engine
    - Storage: JSON files en directorio cache
    - TTL: Configurable (default 24h)
    - Invalidación: Por commit nuevo o manual
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.config = get_ai_config()
        
        if not self.config.cache_enabled:
            self.enabled = False
            return
        
        self.enabled = True
        
        # Directorio de cache
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # Por defecto en .buenobot_cache dentro del proyecto
            self.cache_dir = Path(
                os.environ.get(
                    "BUENOBOT_CACHE_DIR",
                    Path(__file__).parent.parent.parent / ".buenobot_cache" / "ai"
                )
            )
        
        # Crear directorio si no existe
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"AI cache directory: {self.cache_dir}")
        except Exception as e:
            logger.warning(f"Could not create cache dir: {e}")
            self.enabled = False
        
        # TTL en segundos
        self.ttl_seconds = self.config.cache_ttl_hours * 3600
    
    def _compute_key(
        self,
        commit_sha: Optional[str],
        evidence_hash: str,
        engine: str
    ) -> str:
        """Computa key de cache"""
        components = f"{commit_sha or 'nocommit'}:{evidence_hash}:{engine}"
        return hashlib.sha256(components.encode()).hexdigest()[:24]
    
    def _get_cache_path(self, key: str) -> Path:
        """Obtiene path del archivo de cache"""
        # Usar primeros 2 chars como subdirectorio para evitar demasiados archivos
        subdir = key[:2]
        return self.cache_dir / subdir / f"{key}.json"
    
    def get(
        self,
        commit_sha: Optional[str],
        evidence_hash: str,
        engine: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene respuesta del cache.
        
        Args:
            commit_sha: Hash del commit
            evidence_hash: Hash del EvidencePack
            engine: Motor usado (local, openai, mock)
        
        Returns:
            Dict con respuesta IA si existe y es válido, None si no
        """
        if not self.enabled:
            return None
        
        key = self._compute_key(commit_sha, evidence_hash, engine)
        cache_path = self._get_cache_path(key)
        
        try:
            if not cache_path.exists():
                return None
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            # Verificar TTL
            cached_at = datetime.fromisoformat(cached.get("cached_at", "1970-01-01"))
            if datetime.utcnow() - cached_at > timedelta(seconds=self.ttl_seconds):
                logger.debug(f"Cache expired for key {key}")
                cache_path.unlink(missing_ok=True)
                return None
            
            logger.debug(f"Cache hit for key {key}")
            return cached.get("response")
            
        except Exception as e:
            logger.warning(f"Cache read error for {key}: {e}")
            return None
    
    def set(
        self,
        commit_sha: Optional[str],
        evidence_hash: str,
        engine: str,
        response: Dict[str, Any]
    ) -> bool:
        """
        Guarda respuesta en cache.
        
        Args:
            commit_sha: Hash del commit
            evidence_hash: Hash del EvidencePack
            engine: Motor usado
            response: Respuesta IA a cachear
        
        Returns:
            True si se guardó correctamente
        """
        if not self.enabled:
            return False
        
        key = self._compute_key(commit_sha, evidence_hash, engine)
        cache_path = self._get_cache_path(key)
        
        try:
            # Crear subdirectorio
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            cache_entry = {
                "key": key,
                "commit_sha": commit_sha,
                "evidence_hash": evidence_hash,
                "engine": engine,
                "cached_at": datetime.utcnow().isoformat(),
                "response": response
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, indent=2)
            
            logger.debug(f"Cache set for key {key}")
            return True
            
        except Exception as e:
            logger.warning(f"Cache write error for {key}: {e}")
            return False
    
    def invalidate(
        self,
        commit_sha: Optional[str] = None,
        evidence_hash: Optional[str] = None
    ) -> int:
        """
        Invalida entradas de cache.
        
        Args:
            commit_sha: Si se especifica, invalida por commit
            evidence_hash: Si se especifica, invalida por hash
        
        Returns:
            Número de entradas invalidadas
        """
        if not self.enabled:
            return 0
        
        invalidated = 0
        
        try:
            for subdir in self.cache_dir.iterdir():
                if not subdir.is_dir():
                    continue
                    
                for cache_file in subdir.glob("*.json"):
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cached = json.load(f)
                        
                        should_delete = False
                        
                        if commit_sha and cached.get("commit_sha") == commit_sha:
                            should_delete = True
                        elif evidence_hash and cached.get("evidence_hash") == evidence_hash:
                            should_delete = True
                        
                        if should_delete:
                            cache_file.unlink()
                            invalidated += 1
                            
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
        
        if invalidated > 0:
            logger.info(f"Invalidated {invalidated} cache entries")
        
        return invalidated
    
    def clear(self) -> int:
        """
        Limpia todo el cache.
        
        Returns:
            Número de entradas eliminadas
        """
        if not self.enabled:
            return 0
        
        cleared = 0
        
        try:
            for subdir in self.cache_dir.iterdir():
                if not subdir.is_dir():
                    continue
                    
                for cache_file in subdir.glob("*.json"):
                    try:
                        cache_file.unlink()
                        cleared += 1
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")
        
        logger.info(f"Cleared {cleared} cache entries")
        return cleared
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cache.
        
        Returns:
            Dict con stats
        """
        if not self.enabled:
            return {"enabled": False}
        
        total_entries = 0
        total_size_bytes = 0
        by_engine = {}
        expired = 0
        
        try:
            for subdir in self.cache_dir.iterdir():
                if not subdir.is_dir():
                    continue
                    
                for cache_file in subdir.glob("*.json"):
                    total_entries += 1
                    total_size_bytes += cache_file.stat().st_size
                    
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cached = json.load(f)
                        
                        engine = cached.get("engine", "unknown")
                        by_engine[engine] = by_engine.get(engine, 0) + 1
                        
                        cached_at = datetime.fromisoformat(cached.get("cached_at", "1970-01-01"))
                        if datetime.utcnow() - cached_at > timedelta(seconds=self.ttl_seconds):
                            expired += 1
                            
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.warning(f"Cache stats error: {e}")
        
        return {
            "enabled": True,
            "total_entries": total_entries,
            "total_size_kb": round(total_size_bytes / 1024, 2),
            "by_engine": by_engine,
            "expired": expired,
            "ttl_hours": self.config.cache_ttl_hours,
            "cache_dir": str(self.cache_dir)
        }


# Singleton instance
_cache_instance: Optional[AICache] = None


def get_ai_cache() -> AICache:
    """Obtiene instancia singleton del cache"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = AICache()
    return _cache_instance

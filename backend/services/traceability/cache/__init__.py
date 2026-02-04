"""
Sistema de caché para trazabilidad.
Mantiene todos los modelos en memoria con refresh incremental.
"""
from .traceability_cache import TraceabilityCache, get_cache

__all__ = ["TraceabilityCache", "get_cache"]

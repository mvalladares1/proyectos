"""
FastAPI Main Application - Rio Futuro Dashboards API
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routers import (
    auth,
    produccion,
    bandejas,
    stock,
    containers,
    demo,
    estado_resultado,
    presupuesto,
    permissions,
    recepcion,
    rendimiento,
    compras,
    automatizaciones,
    comercial,
    flujo_caja,
    reconciliacion,
    odf_reconciliation,
    aprobaciones_fletes,
    etiquetas
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación.
    Carga el caché al iniciar, ejecuta refresh periódico.
    """
    # Startup
    logger.info("Iniciando aplicación...")
    
    # Importar y cargar caché
    from backend.services.traceability.cache import get_cache
    
    cache = get_cache()
    
    # Cargar caché en background
    asyncio.create_task(cache.load_all())
    
    # Task para refresh periódico (cada 5 minutos)
    async def periodic_refresh():
        while True:
            await asyncio.sleep(300)  # 5 minutos
            try:
                await cache.refresh_incremental()
            except Exception as e:
                logger.error(f"Error en refresh periódico: {e}")
    
    refresh_task = asyncio.create_task(periodic_refresh())
    
    logger.info("Caché de trazabilidad iniciado en background")
    
    yield
    
    # Shutdown
    logger.info("Cerrando aplicación...")
    refresh_task.cancel()


# Crear aplicación
app = FastAPI(
    title="Rio Futuro Dashboards API",
    description="API unificada para los dashboards de Rio Futuro",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip Compression para respuestas grandes (mejora transferencia de datos)
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)  # Comprimir respuestas >1KB

# Registrar routers
app.include_router(auth.router)
app.include_router(produccion.router)
app.include_router(bandejas.router)
app.include_router(stock.router)
app.include_router(containers.router)
app.include_router(demo.router)
app.include_router(estado_resultado.router)
app.include_router(presupuesto.router)
app.include_router(permissions.router)
app.include_router(recepcion.router)
app.include_router(rendimiento.router)
app.include_router(compras.router)
app.include_router(automatizaciones.router)
app.include_router(comercial.router)
app.include_router(flujo_caja.router)
app.include_router(reconciliacion.router)
app.include_router(odf_reconciliation.router)
app.include_router(aprobaciones_fletes.router)
app.include_router(etiquetas.router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Rio Futuro Dashboards API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check para monitoreo"""
    return {"status": "healthy"}


# ============ Traceability Cache Endpoints ============
from backend.services.traceability.cache import get_cache


@app.get("/api/v1/traceability/cache/status")
async def cache_status():
    """
    Estado del caché de trazabilidad.
    Retorna: is_loaded, last_refresh, record counts, etc.
    """
    cache = get_cache()
    return cache.get_status()


@app.post("/api/v1/traceability/cache/reload")
async def cache_reload():
    """
    Fuerza recarga completa del caché (puede demorar ~5 minutos).
    """
    cache = get_cache()
    asyncio.create_task(cache.load_all(force_reload=True))
    return {"status": "ok", "message": "Cache reload iniciado en background"}


@app.post("/api/v1/traceability/cache/refresh")
async def cache_refresh():
    """
    Fuerza refresh incremental inmediato.
    """
    cache = get_cache()
    await cache.refresh_incremental()
    return {"status": "ok", "message": "Cache refreshed"}


# ============ Legacy Cache Management Endpoints ============
from backend.cache import get_cache


@app.get("/api/v1/cache/stats")
async def cache_stats():
    """
    Obtiene estadísticas del caché legacy (OdooCache).
    Retorna: hits, misses, hit_rate (%), entries activas
    """
    return get_cache().get_stats()


@app.post("/api/v1/cache/clear")
async def cache_clear():
    """
    Limpia todo el caché legacy (OdooCache). Usar con precaución.
    """
    get_cache().clear()
    return {"status": "ok", "message": "Cache cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )

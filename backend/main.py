"""
FastAPI Main Application - Rio Futuro Dashboards API
"""
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
    recepcion
)

# Crear aplicación
app = FastAPI(
    title="Rio Futuro Dashboards API",
    description="API unificada para los dashboards de Rio Futuro",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# ============ Cache Management Endpoints ============
from backend.cache import get_cache


@app.get("/api/v1/cache/stats")
async def cache_stats():
    """
    Obtiene estadísticas del caché.
    Retorna: hits, misses, hit_rate (%), entries activas
    """
    return get_cache().get_stats()


@app.post("/api/v1/cache/clear")
async def cache_clear():
    """
    Limpia todo el caché. Usar con precaución.
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

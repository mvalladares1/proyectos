"""
FastAPI Main Application - Rio Futuro Dashboards API
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# IMPORTANTE: Importamos 'metrics' además de Instrumentator
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST

from backend.config import settings
from backend.routers import (
    auth, produccion, bandejas, stock, containers, demo,
    estado_resultado, presupuesto, permissions, recepcion,
    rendimiento, compras, automatizaciones, comercial,
    flujo_caja, reconciliacion, odf_reconciliation,
    aprobaciones_fletes, etiquetas, proformas
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación."""
    logger.info("Iniciando aplicación...")
    yield
    logger.info("Cerrando aplicación...")

# Crear aplicación
app = FastAPI(
    title="Rio Futuro Dashboards API",
    description="API unificada para los dashboards de Rio Futuro",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

IN_PROGRESS_METRIC = Gauge(
    "http_requests_inprogress", 
    "Número de peticiones HTTP en curso",
    ["app_name", "handler", "method"]
)

# --- CONFIGURACIÓN AVANZADA DE MÉTRICAS ---
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    
)

instrumentator.add(
    metrics.default(
        metric_name="http_request_duration_seconds",
        should_include_handler=True,
        should_include_method=True,
        should_include_status=True
    )
)

# Ejecutamos la instrumentación
instrumentator.instrument(app)

@app.middleware("http")
async def track_inprogress(request, call_next):
    handler = request.scope.get("path", "unknown")
    method = request.method
    
    if handler == "/metrics":
        return await call_next(request)
        
    IN_PROGRESS_METRIC.labels(app_name="rio_api", handler=handler, method=method).inc()
    try:
        response = await call_next(request)
        return response
    finally:
        IN_PROGRESS_METRIC.labels(app_name="rio_api", handler=handler, method=method).dec()

@app.get("/metrics")
def metrics_endpoint():
    from fastapi import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# --- MIDDLEWARES ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# --- RUTAS ---
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
app.include_router(proformas.router)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Rio Futuro Dashboards API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
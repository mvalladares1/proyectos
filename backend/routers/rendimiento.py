"""
Router de Rendimiento Productivo - Análisis de eficiencia por lote
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.rendimiento_service import RendimientoService

router = APIRouter(prefix="/api/v1/rendimiento", tags=["rendimiento"])


@router.get("/overview")
async def get_overview(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    Obtiene KPIs consolidados de rendimiento para el período.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_overview(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lotes")
async def get_rendimiento_lotes(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    Obtiene rendimiento detallado por lote de MP.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_rendimiento_por_lote(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proveedores")
async def get_rendimiento_proveedores(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    Obtiene rendimiento agrupado por proveedor.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_rendimiento_por_proveedor(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mos")
async def get_rendimiento_mos(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    Obtiene análisis de rendimiento por MO individual.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_rendimiento_mos(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

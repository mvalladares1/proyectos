"""
Router de Producción - Órdenes de fabricación y métricas
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from backend.services.produccion_service import ProduccionService

router = APIRouter(prefix="/api/v1/produccion", tags=["produccion"])


@router.get("/ordenes")
async def get_ordenes_fabricacion(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)")
):
    """
    Obtiene las órdenes de fabricación de Odoo.
    """
    try:
        service = ProduccionService(username=username, password=password)
        return service.get_ordenes_fabricacion(
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ordenes/{of_id}")
async def get_orden_detalle(
    of_id: int,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene el detalle completo de una orden de fabricación.
    Incluye componentes, subproductos, detenciones, consumo y KPIs.
    """
    try:
        service = ProduccionService(username=username, password=password)
        return service.get_of_detail(of_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kpis")
async def get_kpis_produccion(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene los KPIs de producción.
    """
    try:
        service = ProduccionService(username=username, password=password)
        return service.get_kpis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resumen")
async def get_resumen_produccion(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene un resumen general de producción.
    """
    try:
        service = ProduccionService(username=username, password=password)
        return service.get_resumen()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clasificacion")
async def get_clasificacion_pallets(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    tipo_fruta: Optional[str] = Query(None, description="Filtrar por tipo de fruta"),
    tipo_manejo: Optional[str] = Query(None, description="Filtrar por tipo de manejo")
):
    """
    Obtiene la clasificación de pallets (IQF A y RETAIL).
    
    Compara stock.move.line.result_package_id con x_mrp_production_line_d413e.x_name
    y suma los kg según la clasificación en x_studio_observaciones.
    
    Retorna:
        - iqf_a_kg: Kilogramos clasificados como IQF A
        - retail_kg: Kilogramos clasificados como RETAIL
        - total_kg: Total de kilogramos
        - detalle: Lista de pallets con su clasificación
    """
    try:
        service = ProduccionService(username=username, password=password)
        return service.get_clasificacion_pallets(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo_fruta=tipo_fruta,
            tipo_manejo=tipo_manejo
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

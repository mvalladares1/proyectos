"""
Router de Compras - Endpoints para gestión de Órdenes de Compra
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.compras_service import ComprasService

router = APIRouter(prefix="/api/v1/compras", tags=["compras"])


@router.get("/overview")
async def get_overview(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    KPIs consolidados de compras para el período.
    """
    try:
        service = ComprasService(username=username, password=password)
        return service.get_overview(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ordenes")
async def get_ordenes_compra(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    status_filter: Optional[str] = Query(None, description="Filtro estado aprobación"),
    receive_filter: Optional[str] = Query(None, description="Filtro estado recepción"),
    search_text: Optional[str] = Query(None, description="Buscar por número PO")
):
    """
    Lista de órdenes de compra con estados de aprobación y recepción.
    """
    try:
        service = ComprasService(username=username, password=password)
        return service.get_ordenes_compra(
            fecha_inicio, fecha_fin,
            status_filter=status_filter,
            receive_filter=receive_filter,
            search_text=search_text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineas-credito")
async def get_lineas_credito(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde para calcular uso (YYYY-MM-DD)")
):
    """
    Lista de proveedores con línea de crédito activa y detalle de uso.
    """
    try:
        service = ComprasService(username=username, password=password)
        return service.get_lineas_credito(fecha_desde=fecha_desde)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineas-credito/resumen")
async def get_lineas_credito_resumen(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde para calcular uso (YYYY-MM-DD)")
):
    """
    KPIs consolidados de líneas de crédito.
    """
    try:
        service = ComprasService(username=username, password=password)
        return service.get_lineas_credito_resumen(fecha_desde=fecha_desde)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orden/{po_id}/lineas")
async def get_orden_lineas(
    po_id: int,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene las líneas de producto de una orden de compra.
    """
    try:
        service = ComprasService(username=username, password=password)
        return service.get_orden_lineas(po_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

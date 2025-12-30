"""
Router de Stock - Gestión de cámaras, pallets y lotes
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional
from pydantic import BaseModel

from backend.services.stock_service import StockService

router = APIRouter(prefix="/api/v1/stock", tags=["stock"])

class MoveRequest(BaseModel):
    pallet_code: str
    target_location_id: int
    username: str
    password: str

@router.post("/move")
async def move_pallet(request: MoveRequest):
    """
    Mueve un pallet a una ubicación destino.
    Maneja tanto Stock Real (Transferencia) como Pre-Recepción (Reasignación).
    """
    try:
        service = StockService(username=request.username, password=request.password)
        result = service.move_pallet(request.pallet_code, request.target_location_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/camaras")
async def get_camaras_stock(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (formato YYYY-MM-DD) para filtrar por fecha de ingreso"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (formato YYYY-MM-DD) para filtrar por fecha de ingreso")
):
    """
    Obtiene stock agrupado por cámaras (ubicaciones).
    Incluye capacidad y posiciones ocupadas por especie/condición.
    Opcionalmente filtra por rango de fechas de ingreso de pallets.
    """
    try:
        service = StockService(username=username, password=password)
        return service.get_chambers_stock(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pallets")
async def get_pallets(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    location_id: int = Query(..., description="ID de la ubicación/cámara"),
    category: Optional[str] = Query(None, description="Filtro por Especie - Condición")
):
    """
    Obtiene lista de pallets detallada de una ubicación.
    Opcionalmente filtrado por categoría (Especie - Condición).
    """
    try:
        service = StockService(username=username, password=password)
        return service.get_pallets(location_id, category)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lotes")
async def get_lotes_by_category(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    category: str = Query(..., description="Categoría en formato 'Especie - Condición'"),
    location_ids: Optional[str] = Query(None, description="IDs de ubicaciones separados por coma")
):
    """
    Obtiene lotes agrupados por categoría con información de antigüedad.
    Útil para análisis FIFO y trazabilidad.
    """
    try:
        loc_ids = None
        if location_ids:
            loc_ids = [int(x.strip()) for x in location_ids.split(",") if x.strip()]
        
        service = StockService(username=username, password=password)
        return service.get_lots_by_category(category, loc_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

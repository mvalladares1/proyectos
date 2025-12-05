"""
Router de Stock - Gestión de cámaras, pallets y lotes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.stock_service import StockService

router = APIRouter(prefix="/api/v1/stock", tags=["stock"])


@router.get("/camaras")
async def get_camaras_stock(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene stock agrupado por cámaras (ubicaciones).
    Incluye capacidad y posiciones ocupadas por especie/condición.
    """
    try:
        service = StockService(username=username, password=password)
        return service.get_chambers_stock()
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

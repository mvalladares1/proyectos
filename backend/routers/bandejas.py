"""
Router de Bandejas - Movimientos y stock de bandejas
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.bandejas_service import BandejasService

router = APIRouter(prefix="/api/v1/bandejas", tags=["bandejas"])


@router.get("/movimientos-entrada")
async def get_movimientos_entrada(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    offset: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(5000, ge=1, le=10000, description="Máximo de registros a retornar")
):
    """
    Obtiene los movimientos de entrada de bandejas (recepción de productores).
    """
    try:
        service = BandejasService(username=username, password=password)
        data = service.get_movimientos_entrada(fecha_desde=fecha_desde, offset=offset, limit=limit)
        return {"data": data.to_dict(orient='records') if not data.empty else []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/movimientos-salida")
async def get_movimientos_salida(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    offset: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(5000, ge=1, le=10000, description="Máximo de registros a retornar")
):
    """
    Obtiene los movimientos de salida de bandejas (despacho a productores).
    """
    try:
        service = BandejasService(username=username, password=password)
        data = service.get_movimientos_salida(fecha_desde=fecha_desde, offset=offset, limit=limit)
        return {"data": data.to_dict(orient='records') if not data.empty else []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock")
async def get_stock_bandejas(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene el stock actual de bandejas por tipo (Limpia/Sucia).
    """
    try:
        service = BandejasService(username=username, password=password)
        data = service.get_stock()
        return {"data": data.to_dict(orient='records') if not data.empty else []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resumen-productor")
async def get_resumen_por_productor(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    anio: Optional[int] = Query(None, description="Filtrar por año"),
    mes: Optional[int] = Query(None, description="Filtrar por mes (1-12)")
):
    """
    Obtiene el resumen de bandejas por productor.
    """
    try:
        service = BandejasService(username=username, password=password)
        data = service.get_resumen_por_productor(anio=anio, mes=mes)
        return {"data": data.to_dict(orient='records') if not data.empty else []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

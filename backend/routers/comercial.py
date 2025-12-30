"""
Router de Relación Comercial
Endpoints para el Dashboard de Clientes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from ..services.comercial_service import comercial_service

router = APIRouter(
    prefix="/comercial",
    tags=["comercial"]
)

@router.get("/data")
async def get_comercial_data(
    anio: Optional[List[int]] = Query(None),
    mes: Optional[List[int]] = Query(None),
    trimestre: Optional[List[str]] = Query(None),
    cliente: Optional[List[str]] = Query(None),
    especie: Optional[List[str]] = Query(None)
) -> Dict[str, Any]:
    """
    Obtiene datos del Dashboard de Relación Comercial con filtros opcionales.
    """
    try:
        filters = {}
        if anio: filters['anio'] = anio
        if mes: filters['mes'] = mes
        if trimestre: filters['trimestre'] = trimestre
        if cliente: filters['cliente'] = cliente
        if especie: filters['especie'] = especie
        
        data = comercial_service.get_relacion_comercial_data(filters if filters else None)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filters")
async def get_filter_values() -> Dict[str, List[Any]]:
    """
    Obtiene valores únicos para los filtros del dashboard.
    """
    try:
        return comercial_service.get_filter_values()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

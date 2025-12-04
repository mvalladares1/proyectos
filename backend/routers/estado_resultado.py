from fastapi import APIRouter, Query
from typing import Optional

from backend.services.estado_resultado_service import (
    get_estado_resultado,
    get_cuentas_contables,
    get_centros_costo
)

router = APIRouter(prefix="/api/v1/estado-resultado", tags=["EstadoResultado"])


@router.get("/", summary="Obtener Estado de Resultado completo")
def estado_resultado(
    fecha_inicio: str = Query("2025-01-01", description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    centro_costo: Optional[int] = Query(None, description="ID del centro de costo")
):
    return get_estado_resultado(fecha_inicio, fecha_fin, centro_costo)


@router.get("/cuentas", summary="Obtener cuentas contables")
def cuentas_contables():
    return get_cuentas_contables()


@router.get("/centros-costo", summary="Obtener centros de costo")
def centros_costo():
    return get_centros_costo()

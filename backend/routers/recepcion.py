"""
Router de Recepciones MP - Materia Prima
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.recepcion_service import get_recepciones_mp

router = APIRouter(prefix="/api/v1/recepciones-mp", tags=["recepciones-mp"])


@router.get("/")
async def get_recepciones(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    productor_id: Optional[int] = Query(None, description="ID del productor")
):
    """
    Obtiene las recepciones de materia prima con datos de calidad.
    """
    try:
        data = get_recepciones_mp(username, password, fecha_inicio, fecha_fin, productor_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

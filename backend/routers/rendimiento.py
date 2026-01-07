"""
Router de Rendimiento Productivo
Incluye trazabilidad inversa y endpoints para el módulo de Producción
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List

from backend.services.rendimiento_service import RendimientoService

router = APIRouter(prefix="/api/v1/rendimiento", tags=["rendimiento"])


@router.get("/trazabilidad-inversa/{lote_pt_name}")
async def get_trazabilidad_inversa(
    lote_pt_name: str,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Trazabilidad inversa: dado un lote PT, encuentra los lotes MP originales.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_trazabilidad_inversa(lote_pt_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trazabilidad-pallets")
async def get_trazabilidad_pallets(
    pallet_names: List[str] = Body(..., description="Lista de nombres de pallets"),
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Trazabilidad completa de uno o varios pallets.
    Rastrea desde el pallet físico hasta el productor original.
    
    Body:
        pallet_names: Lista de nombres de pallets (ej: ["PALLET-001", "PALLET-002"])
    
    Returns:
        - pallets_rastreados: Número de pallets procesados
        - pallets: Lista con trazabilidad completa de cada pallet
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_trazabilidad_pallets(pallet_names)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard_completo(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    solo_terminadas: bool = Query(True, description="Solo MOs en estado 'done'")
):
    """
    USADO POR PRODUCCIÓN: Obtiene datos consolidados del dashboard.
    
    Retorna:
    - overview: KPIs consolidados (proceso, congelado, etc.)
    - consolidado: Datos por fruta/manejo
    - salas: Productividad por sala
    - mos: Lista de MOs con rendimiento
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_dashboard_completo(fecha_inicio, fecha_fin, solo_terminadas=solo_terminadas)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview")
async def get_overview(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    LEGACY: KPIs consolidados de rendimiento.
    Usa el endpoint /dashboard para datos más completos.
    """
    try:
        service = RendimientoService(username=username, password=password)
        data = service.get_dashboard_completo(fecha_inicio, fecha_fin)
        return data.get('overview', {}) if data else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

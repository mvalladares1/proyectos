"""
Router de Containers/Ventas - Seguimiento de producción por pedido
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.containers_service import ContainersService

router = APIRouter(prefix="/api/v1/containers", tags=["containers"])


@router.get("/")
async def get_containers(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    start_date: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    partner_id: Optional[int] = Query(None, description="ID del cliente"),
    state: Optional[str] = Query(None, description="Estado del pedido")
):
    """
    Obtiene lista de containers/ventas con su avance de producción.
    Busca desde fabricaciones que tienen PO asociada (x_studio_po_asociada_1).
    """
    try:
        service = ContainersService(username=username, password=password)
        return service.get_containers(
            start_date=start_date,
            end_date=end_date,
            partner_id=partner_id,
            state=state
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_containers_summary(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene resumen global de containers para KPIs.
    """
    try:
        service = ContainersService(username=username, password=password)
        return service.get_containers_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/partners/list")
async def get_partners(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene lista de clientes que tienen pedidos con fabricaciones.
    Útil para filtros.
    """
    try:
        service = ContainersService(username=username, password=password)
        return service.get_partners_with_orders()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sankey")
async def get_sankey_data(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    start_date: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    limit: int = Query(50, description="Número máximo de containers")
):
    """
    Obtiene datos para diagrama Sankey de trazabilidad.
    Muestra Container → Fabricación → Pallets (consumidos y de salida).
    """
    try:
        service = ContainersService(username=username, password=password)
        return service.get_sankey_data(start_date=start_date, end_date=end_date, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{sale_id}")
async def get_container_detail(
    sale_id: int,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene detalle completo de un container/venta específico.
    Incluye todas las fabricaciones vinculadas y líneas de pedido.
    """
    try:
        service = ContainersService(username=username, password=password)
        container = service.get_container_detail(sale_id)
        if not container:
            raise HTTPException(status_code=404, detail="Container no encontrado")
        return container
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
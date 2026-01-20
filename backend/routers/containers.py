"""
Router de Pedidos de Venta - Seguimiento de producción por pedido
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.containers import ContainersService
from backend.services.traceability import (
    TraceabilityService,
    transform_to_sankey,
    transform_to_reactflow
)

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
    Obtiene lista de pedidos de venta con su avance de producción.
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
    Obtiene resumen global de pedidos de venta para KPIs.
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
):
    """
    Obtiene datos para diagrama Sankey de trazabilidad basado en stock.move.line.
    Muestra IN → Proceso (reference) → OUT → Cliente (ventas).
    """
    try:
        service = ContainersService(username=username, password=password)
        return service.get_sankey_data(
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sankey/producers")
async def get_sankey_producers(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    start_date: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    partner_id: Optional[int] = Query(None, description="ID del cliente (filtro pedidos de venta)"),
    limit: int = Query(50, description="Número máximo de pedidos de venta")
):
    """Obtiene productores disponibles (desde pallets IN) para poblar filtros del Sankey."""
    try:
        service = ContainersService(username=username, password=password)
        return service.get_sankey_producers(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            partner_id=partner_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ NUEVOS ENDPOINTS DE TRAZABILIDAD ============

@router.get("/traceability/data")
async def get_traceability_data(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    start_date: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
):
    """
    Obtiene datos crudos de trazabilidad.
    Retorna pallets, procesos, proveedores, clientes y conexiones.
    """
    try:
        service = TraceabilityService(username=username, password=password)
        data = service.get_traceability_data(start_date=start_date, end_date=end_date)
        # Remover move_lines del response para reducir tamaño
        data.pop("move_lines", None)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traceability/sankey")
async def get_traceability_sankey(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    start_date: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
):
    """
    Obtiene datos de trazabilidad transformados a formato Sankey (Plotly).
    """
    try:
        service = TraceabilityService(username=username, password=password)
        data = service.get_traceability_data(start_date=start_date, end_date=end_date)
        return transform_to_sankey(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traceability/reactflow")
async def get_traceability_reactflow(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    start_date: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
):
    """
    Obtiene datos de trazabilidad transformados a formato React Flow.
    Para usar con streamlit-flow-component.
    """
    try:
        service = TraceabilityService(username=username, password=password)
        data = service.get_traceability_data(start_date=start_date, end_date=end_date)
        return transform_to_reactflow(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traceability/by-identifier")
async def get_traceability_by_identifier(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    identifier: str = Query(..., description="Venta (ej: S00574) o Paquete"),
):
    """
    Obtiene trazabilidad completa por identificador.
    - Si es S + números (ej: S00574) → busca todos los pallets de esa venta
    - Si no → busca ese paquete específico
    Retorna datos crudos (pallets, procesos, proveedores, clientes, links).
    """
    try:
        service = TraceabilityService(username=username, password=password)
        data = service.get_traceability_by_identifier(identifier=identifier)
        data.pop("move_lines", None)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traceability/by-identifier/visjs")
async def get_traceability_by_identifier_visjs(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    identifier: str = Query(..., description="Venta (ej: S00574) o Paquete"),
):
    """
    Obtiene trazabilidad por identificador transformada a formato vis.js Network.
    """
    try:
        service = TraceabilityService(username=username, password=password)
        data = service.get_traceability_by_identifier(identifier=identifier)
        return transform_to_visjs(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ FIN ENDPOINTS DE TRAZABILIDAD ============


@router.get("/{sale_id}")
async def get_container_detail(
    sale_id: int,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene detalle completo de un pedido de venta específico.
    Incluye todas las fabricaciones vinculadas y líneas de pedido.
    """
    try:
        service = ContainersService(username=username, password=password)
        container = service.get_container_detail(sale_id)
        if not container:
            raise HTTPException(status_code=404, detail="Pedido de venta no encontrado")
        return container
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
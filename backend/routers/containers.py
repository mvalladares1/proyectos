"""
Router de Pedidos de Venta - Seguimiento de producción por pedido
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.containers import ContainersService
from backend.services.traceability import (
    TraceabilityService,
    transform_to_sankey,
    transform_to_reactflow,
    transform_to_visjs
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
    include_siblings: bool = Query(True, description="Incluir pallets hermanos del mismo proceso"),
):
    """
    Obtiene trazabilidad completa por identificador.
    - Si es S + números (ej: S00574) → busca todos los pallets de esa venta
    - Si no → busca ese paquete específico
    - include_siblings: True = traer todos los movimientos del proceso, False = solo cadena directa
    Retorna datos crudos (pallets, procesos, proveedores, clientes, links).
    """
    try:
        service = TraceabilityService(username=username, password=password)
        data = service.get_traceability_by_identifier(identifier=identifier, include_siblings=include_siblings)
        data.pop("move_lines", None)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traceability/by-delivery-guide")
async def get_traceability_by_delivery_guide(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    guide: str = Query(..., description="Número de guía de despacho"),
    include_siblings: bool = Query(True, description="Incluir pallets hermanos del mismo proceso"),
):
    """
    Obtiene trazabilidad desde una guía de despacho HACIA ADELANTE.
    Busca la recepción con esa guía y rastrea todos los pallets hasta clientes.
    """
    try:
        service = TraceabilityService(username=username, password=password)
        data = service._get_traceability_by_delivery_guide(delivery_guide=guide, limit=10000, include_siblings=include_siblings)
        data.pop("move_lines", None)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traceability/search-by-guide-pattern")
async def search_by_guide_pattern(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    guide_pattern: str = Query(..., description="Patrón de guía (ej: 503)"),
):
    """
    Busca recepciones que coincidan con el patrón de guía.
    Por ejemplo: '503' encuentra '503', '503.', '503a', '503-a', 'A503'
    pero NO '3503', '5031', '15034'.
    Retorna lista de recepciones con productor, fecha, albarán.
    """
    try:
        from shared.odoo_client import OdooClient
        client = OdooClient(username=username, password=password)
        
        # Buscar pickings con guía que contenga el patrón en cualquier parte
        # Usamos operador '=ilike' para búsqueda case-insensitive y con wildcards
        pickings = client.search_read(
            "stock.picking",
            [
                ("x_studio_gua_de_despacho", "=ilike", f"%{guide_pattern}%"),
                ("state", "=", "done"),
                ("picking_type_id", "in", [1, 217, 164])  # RFP, VILKUN, SAN JOSE
            ],
            ["id", "name", "x_studio_gua_de_despacho", "partner_id", "scheduled_date", "picking_type_id"],
            limit=100
        )
        
        # Filtrar para asegurar que el patrón sea un número completo
        # Por ejemplo: si busco "503", quiero "503", "503.", "503a", "503-a", "A503"
        # pero NO quiero "3503", "5031", "15034"
        import re
        filtered_pickings = []
        # Regex: el patrón debe estar rodeado de no-dígitos (o inicio/fin de string)
        pattern_regex = re.compile(r'(?<!\d)' + re.escape(guide_pattern) + r'(?!\d)', re.IGNORECASE)
        
        for p in pickings:
            guia = p.get("x_studio_gua_de_despacho", "")
            if guia and pattern_regex.search(guia):
                filtered_pickings.append(p)
        
        # Formatear respuesta
        recepciones = []
        for p in filtered_pickings:
            partner_rel = p.get("partner_id")
            partner_name = partner_rel[1] if isinstance(partner_rel, (list, tuple)) and len(partner_rel) > 1 else "Productor"
            
            recepciones.append({
                "picking_id": p["id"],
                "albaran": p.get("name", ""),
                "guia_despacho": p.get("x_studio_gua_de_despacho", ""),
                "productor": partner_name,
                "fecha": p.get("scheduled_date", ""),
                "picking_type_id": p.get("picking_type_id", [None])[0] if isinstance(p.get("picking_type_id"), list) else p.get("picking_type_id")
            })
        
        return {"recepciones": recepciones, "total": len(recepciones)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traceability/by-picking-id")
async def get_traceability_by_picking_id(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    picking_id: int = Query(..., description="ID del picking de recepción"),
    include_siblings: bool = Query(True, description="Incluir pallets hermanos del mismo proceso"),
):
    """
    Obtiene trazabilidad desde un picking específico HACIA ADELANTE.
    Sigue toda la cadena: recepción → procesos → más procesos → clientes.
    """
    try:
        service = TraceabilityService(username=username, password=password)
        
        # Buscar pallets de este picking (result_package_id de la recepción)
        move_lines = service.odoo.search_read(
            "stock.move.line",
            [
                ("picking_id", "=", picking_id),
                ("result_package_id", "!=", False),
                ("qty_done", ">", 0),
                ("state", "=", "done"),
            ],
            ["result_package_id"],
            limit=500
        )
        
        # Extraer package_ids
        package_ids = set()
        for ml in move_lines:
            result_rel = ml.get("result_package_id")
            if result_rel:
                result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
                if result_id:
                    package_ids.add(result_id)
        
        if not package_ids:
            return {"error": "No se encontraron pallets en este picking"}
        
        # Obtener trazabilidad HACIA ADELANTE de esos pallets
        data = service._get_forward_traceability_for_packages(list(package_ids), limit=10000, include_siblings=include_siblings)
        data.pop("move_lines", None)
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traceability/by-identifier/visjs")
async def get_traceability_by_identifier_visjs(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    identifier: str = Query(..., description="Venta (ej: S00574) o Paquete"),
    include_siblings: bool = Query(True, description="Incluir pallets hermanos del mismo proceso"),
):
    """
    Obtiene trazabilidad por identificador transformada a formato vis.js Network.
    """
    try:
        service = TraceabilityService(username=username, password=password)
        data = service.get_traceability_by_identifier(identifier=identifier, include_siblings=include_siblings)
        return transform_to_visjs(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traceability/by-identifier/sankey")
async def get_traceability_by_identifier_sankey(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    identifier: str = Query(..., description="Venta (ej: S00574) o Paquete"),
    include_siblings: bool = Query(True, description="Incluir pallets hermanos del mismo proceso"),
):
    """
    Obtiene trazabilidad por identificador transformada a formato Sankey (Plotly).
    """
    try:
        service = TraceabilityService(username=username, password=password)
        data = service.get_traceability_by_identifier(identifier=identifier, include_siblings=include_siblings)
        return transform_to_sankey(data)
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
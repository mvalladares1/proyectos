"""
Router de Pedidos de Venta - Seguimiento de producción por pedido
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

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


@router.get("/proyecciones")
async def get_proyecciones(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    start_date: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    partner_id: Optional[int] = Query(None, description="ID del cliente"),
    state: Optional[str] = Query(None, description="Estado del pedido (sale, draft, etc.)")
):
    """
    Obtiene pedidos de venta para proyección futura.
    Busca directamente en sale.order por commitment_date, sin requerir fabricaciones.
    """
    try:
        service = ContainersService(username=username, password=password)
        return service.get_proyecciones(
            start_date=start_date,
            end_date=end_date,
            partner_id=partner_id,
            state=state
        )
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


@router.get("/traceability/by-supplier")
async def get_traceability_by_supplier(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    supplier_id: int = Query(..., description="ID del proveedor"),
    start_date: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    include_siblings: bool = Query(True, description="Incluir pallets hermanos del mismo proceso"),
):
    """
    Obtiene trazabilidad de todas las recepciones de un proveedor en un rango de fechas.
    Por ejemplo: todas las recepciones de un proveedor en los últimos 7 días.
    """
    try:
        from shared.odoo_client import OdooClient
        client = OdooClient(username=username, password=password)
        
        # Buscar recepciones del proveedor en el rango de fechas
        pickings = client.search_read(
            "stock.picking",
            [
                ("partner_id", "=", supplier_id),
                ("picking_type_id", "in", [1, 217, 164]),  # RFP, VILKUN, SAN JOSE
                ("state", "=", "done"),
                ("scheduled_date", ">=", f"{start_date} 00:00:00"),
                ("scheduled_date", "<=", f"{end_date} 23:59:59"),
            ],
            ["id", "name", "scheduled_date"],
            limit=100
        )
        
        if not pickings:
            return {"error": f"No se encontraron recepciones del proveedor en el rango {start_date} - {end_date}"}
        
        # Obtener todos los package_ids de estas recepciones
        picking_ids = [p["id"] for p in pickings]
        move_lines = client.search_read(
            "stock.move.line",
            [
                ("picking_id", "in", picking_ids),
                ("result_package_id", "!=", False),
                ("qty_done", ">", 0),
                ("state", "=", "done"),
            ],
            ["result_package_id"],
            limit=5000
        )
        
        # Extraer package_ids únicos
        package_ids = set()
        for ml in move_lines:
            result_rel = ml.get("result_package_id")
            if result_rel:
                result_id = result_rel[0] if isinstance(result_rel, (list, tuple)) else result_rel
                if result_id:
                    package_ids.add(result_id)
        
        if not package_ids:
            return {"error": "No se encontraron pallets en las recepciones"}
        
        # Obtener trazabilidad HACIA ADELANTE de todos esos pallets
        service = TraceabilityService(username=username, password=password)
        data = service._get_forward_traceability_for_packages(
            list(package_ids), 
            limit=10000, 
            include_siblings=include_siblings
        )
        data.pop("move_lines", None)
        
        # Agregar metadata sobre la búsqueda
        data["search_metadata"] = {
            "supplier_id": supplier_id,
            "start_date": start_date,
            "end_date": end_date,
            "total_recepciones": len(pickings),
            "total_pallets": len(package_ids)
        }
        
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traceability/by-sale")
async def get_traceability_by_sale(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    sale_identifier: str = Query(None, description="Código de venta (opcional si hay fechas)"),
    start_date: str = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    end_date: str = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    include_siblings: bool = Query(False, description="Incluir pallets hermanos del mismo proceso"),
    output_format: str = Query("sankey", description="Formato de salida: 'sankey' o 'raw'")
):
    """
    Obtiene trazabilidad de ventas con dos modos:
    1. Venta específica (con sale_identifier) con filtro opcional de fechas
    2. Todas las ventas de un período (sin sale_identifier pero con fechas obligatorias)
    """
    try:
        # Validar que al menos uno esté presente
        if not sale_identifier and not (start_date and end_date):
            raise HTTPException(
                status_code=400, 
                detail="Debes proporcionar sale_identifier O ambas fechas (start_date y end_date)"
            )
        
        service = TraceabilityService(username=username, password=password)
        client = service.odoo
        
        # Estrategia: buscar por sale.order primero, luego obtener sus pickings
        if sale_identifier:
            # Búsqueda específica por código de venta
            sale_domain = [
                ("picking_type_id.code", "=", "outgoing"),
                ("state", "=", "done"),
                ("origin", "!=", False),
                ("origin", "=ilike", sale_identifier)
            ]
            
            # Agregar filtro de fechas si se proporciona (usar date_done en picking)
            if start_date:
                sale_domain.append(("date_done", ">=", f"{start_date} 00:00:00"))
            if end_date:
                sale_domain.append(("date_done", "<=", f"{end_date} 23:59:59"))
            
            pickings = client.search_read(
                "stock.picking",
                sale_domain,
                ["id", "name", "origin", "date_done"],
                limit=10
            )
        else:
            # Búsqueda por período: usar sale.order con date_order
            sale_order_domain = [
                ("state", "in", ["sale", "done"]),
            ]
            
            if start_date:
                sale_order_domain.append(("date_order", ">=", f"{start_date} 00:00:00"))
            if end_date:
                sale_order_domain.append(("date_order", "<=", f"{end_date} 23:59:59"))
            
            # Buscar órdenes de venta
            sale_orders = client.search_read(
                "sale.order",
                sale_order_domain,
                ["id", "name"],
                limit=50
            )
            
            if not sale_orders:
                return {"error": f"No se encontraron órdenes de venta en el rango {start_date} - {end_date}"}
            
            # Obtener los names (códigos S*) de las órdenes
            sale_order_names = [so["name"] for so in sale_orders]
            
            # Buscar pickings outgoing con esos origins
            pickings = client.search_read(
                "stock.picking",
                [
                    ("picking_type_id.code", "=", "outgoing"),
                    ("state", "=", "done"),
                    ("origin", "in", sale_order_names)
                ],
                ["id", "name", "origin", "date_done"],
                limit=200
            )
        
        if not pickings:
            if sale_identifier:
                date_msg = f" en el rango {start_date} - {end_date}" if start_date or end_date else ""
                return {"error": f"No se encontraron ventas con código {sale_identifier}{date_msg}"}
            else:
                return {"error": f"No se encontraron ventas en el rango {start_date} - {end_date}"}
        
        # Agrupar por origin para contar ventas reales
        ventas_por_origin = {}
        for p in pickings:
            origin = p.get("origin", "")
            if origin and origin.startswith("S"):
                if origin not in ventas_por_origin:
                    ventas_por_origin[origin] = []
                ventas_por_origin[origin].append(p["id"])
        
        # Si es búsqueda de venta específica y hay múltiples pickings del mismo origin, usar todos
        # Si es por período, ya están limitados
        picking_ids = set()
        for origin, pids in ventas_por_origin.items():
            picking_ids.update(pids)
        
        # Obtener package_ids de todas las ventas seleccionadas
        def _chunked(iterable, size):
            iterable = list(iterable)
            for i in range(0, len(iterable), size):
                yield iterable[i:i + size]

        move_lines = []
        for picking_chunk in _chunked(list(picking_ids), 500):
            chunk_lines = client.search_read(
                "stock.move.line",
                [
                    ("picking_id", "in", picking_chunk),
                    ("package_id", "!=", False),
                    ("qty_done", ">", 0),
                    ("state", "=", "done"),
                ],
                ["package_id"],
                limit=5000
            )
            move_lines.extend(chunk_lines)
        
        # Extraer package_ids únicos
        package_ids = set()
        for ml in move_lines:
            pkg_rel = ml.get("package_id")
            if pkg_rel:
                pkg_id = pkg_rel[0] if isinstance(pkg_rel, (list, tuple)) else pkg_rel
                if pkg_id:
                    package_ids.add(pkg_id)
        
        if not package_ids:
            return {"error": "No se encontraron pallets en las ventas"}
        
        # Obtener trazabilidad completa de todos esos pallets
        # Para búsquedas por período, usar límite más conservador
        trace_limit = 3000 if sale_identifier else 1500
        data = service._get_traceability_for_packages(
            list(package_ids),
            limit=trace_limit,
            include_siblings=include_siblings,
            filter_sale_origins=list(ventas_por_origin.keys()) if not sale_identifier else None
        )
        
        data.pop("move_lines", None)
        
        # Agregar metadata
        data["search_metadata"] = {
            "sale_identifier": sale_identifier,
            "start_date": start_date,
            "end_date": end_date,
            "total_sales": len(ventas_por_origin),  # Número de códigos S únicos
            "total_pickings": len(picking_ids),     # Total de pickings
            "total_pallets": len(package_ids),
            "filtered_by_date": bool(start_date or end_date)
        }
        
        # Transformar si es necesario
        if output_format == "sankey":
            from backend.services.traceability import transform_to_sankey
            return transform_to_sankey(data)
        
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



"""
Router de Producción - Órdenes de fabricación y métricas
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from backend.services.produccion_service import ProduccionService

router = APIRouter(prefix="/api/v1/produccion", tags=["produccion"])


@router.get("/ordenes")
async def get_ordenes_fabricacion(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)")
):
    """
    Obtiene las órdenes de fabricación de Odoo.
    """
    try:
        service = ProduccionService(username=username, password=password)
        return service.get_ordenes_fabricacion(
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ordenes/{of_id}")
async def get_orden_detalle(
    of_id: int,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene el detalle completo de una orden de fabricación.
    Incluye componentes, subproductos, detenciones, consumo y KPIs.
    """
    try:
        service = ProduccionService(username=username, password=password)
        return service.get_of_detail(of_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kpis")
async def get_kpis_produccion(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene los KPIs de producción.
    """
    try:
        service = ProduccionService(username=username, password=password)
        return service.get_kpis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resumen")
async def get_resumen_produccion(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene un resumen general de producción.
    """
    try:
        service = ProduccionService(username=username, password=password)
        return service.get_resumen()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clasificacion")
async def get_clasificacion_pallets(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    tipo_fruta: Optional[str] = Query(None, description="Filtrar por tipo de fruta"),
    tipo_manejo: Optional[str] = Query(None, description="Filtrar por tipo de manejo"),
    sala_proceso: Optional[str] = Query(None, description="Filtrar por sala de proceso"),
    tipo_operacion: Optional[str] = Query("Todas", description="Filtrar por planta (Todas, VILKUN, RIO FUTURO)")
):
    """
    Obtiene la clasificación de pallets por grado (1-7).
    """
    try:
        service = ProduccionService(username=username, password=password)
        return service.get_clasificacion_pallets(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo_fruta=tipo_fruta,
            tipo_manejo=tipo_manejo,
            sala_proceso=sala_proceso,
            tipo_operacion=tipo_operacion
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/report_clasificacion")
async def download_report_clasificacion(
    data: dict
):
    """
    Genera y descarga el informe de clasificación en PDF.
    """
    try:
        from backend.services.produccion_report_service import generate_clasificacion_report_pdf
        from fastapi.responses import StreamingResponse
        import io

        pdf_bytes = generate_clasificacion_report_pdf(
            resumen_grados=data.get('resumen_grados', []),
            detalle_pallets=data.get('detalle_pallets', []),
            fecha_inicio=data.get('fecha_inicio', ''),
            fecha_fin=data.get('fecha_fin', ''),
            planta=data.get('planta', ''),
            sala=data.get('sala', ''),
            total_kg=data.get('total_kg', 0)
        )
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Informe_Clasificacion_{datetime.now().strftime('%Y%m%d')}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================== KG POR LÍNEA =====================

@router.get("/kg-por-linea")
async def get_kg_por_linea(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    planta: Optional[str] = Query(None, description="Filtrar por planta")
):
    """
    Obtiene los KG/Hora por cada línea/sala de proceso en un rango de fechas.
    """
    try:
        from backend.services.monitor_produccion_service import MonitorProduccionService
        service = MonitorProduccionService(username=username, password=password)
        return service.get_kg_por_linea(fecha_inicio, fecha_fin, planta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================== MONITOR DIARIO DE PRODUCCIÓN =====================

@router.get("/monitor/activos")
async def get_procesos_activos(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha: str = Query(..., description="Fecha (YYYY-MM-DD)"),
    planta: Optional[str] = Query(None, description="Filtrar por planta"),
    sala: Optional[str] = Query(None, description="Filtrar por sala"),
    producto: Optional[str] = Query(None, description="Filtrar por producto")
):
    """
    Obtiene procesos activos (no done ni cancel) para una fecha.
    """
    try:
        from backend.services.monitor_produccion_service import MonitorProduccionService
        service = MonitorProduccionService(username=username, password=password)
        return service.get_procesos_activos(fecha, planta, sala, producto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitor/cerrados")
async def get_procesos_cerrados_dia(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    planta: Optional[str] = Query(None, description="Filtrar por planta"),
    sala: Optional[str] = Query(None, description="Filtrar por sala"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    producto: Optional[str] = Query(None, description="Filtrar por producto")
):
    """
    Obtiene procesos que se cerraron (pasaron a done) en un rango de fechas.
    """
    try:
        from backend.services.monitor_produccion_service import MonitorProduccionService
        service = MonitorProduccionService(username=username, password=password)
        return service.get_procesos_cerrados_dia(fecha, planta, sala, fecha_fin, producto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitor/evolucion")
async def get_evolucion_procesos(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    planta: Optional[str] = Query(None, description="Filtrar por planta"),
    sala: Optional[str] = Query(None, description="Filtrar por sala"),
    producto: Optional[str] = Query(None, description="Filtrar por producto")
):
    """
    Obtiene la evolución de procesos creados vs cerrados en un rango de fechas.
    """
    try:
        from backend.services.monitor_produccion_service import MonitorProduccionService
        service = MonitorProduccionService(username=username, password=password)
        return service.get_evolucion_rango(fecha_inicio, fecha_fin, planta, sala, producto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitor/snapshot")
async def guardar_snapshot(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha: str = Query(..., description="Fecha del snapshot (YYYY-MM-DD)"),
    planta: Optional[str] = Query(None, description="Planta específica")
):
    """
    Guarda un snapshot del estado actual de procesos.
    """
    try:
        from backend.services.monitor_produccion_service import MonitorProduccionService
        service = MonitorProduccionService(username=username, password=password)
        return service.guardar_snapshot(fecha, planta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitor/snapshots")
async def obtener_snapshots(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha: Optional[str] = Query(None, description="Filtrar por fecha"),
    limit: int = Query(50, description="Límite de resultados")
):
    """
    Obtiene snapshots guardados.
    """
    try:
        from backend.services.monitor_produccion_service import MonitorProduccionService
        service = MonitorProduccionService(username=username, password=password)
        return service.obtener_snapshots(fecha, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitor/salas")
async def get_salas_disponibles(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene la lista de salas de proceso disponibles.
    """
    try:
        from backend.services.monitor_produccion_service import MonitorProduccionService
        service = MonitorProduccionService(username=username, password=password)
        return service.get_salas_disponibles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitor/productos")
async def get_productos_disponibles(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene la lista de productos de fabricación disponibles.
    """
    try:
        from backend.services.monitor_produccion_service import MonitorProduccionService
        service = MonitorProduccionService(username=username, password=password)
        return service.get_productos_disponibles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitor/report_pdf")
async def download_monitor_report_pdf(data: dict):
    """
    Genera y descarga el reporte PDF del monitor de producción.
    """
    try:
        from backend.services.monitor_report_service import generate_monitor_report_pdf
        from fastapi.responses import StreamingResponse
        import io

        pdf_bytes = generate_monitor_report_pdf(
            fecha_inicio=data.get('fecha_inicio', ''),
            fecha_fin=data.get('fecha_fin', ''),
            planta=data.get('planta', 'Todas'),
            sala=data.get('sala', 'Todas'),
            procesos_pendientes=data.get('procesos_pendientes', []),
            procesos_cerrados=data.get('procesos_cerrados', []),
            evolucion=data.get('evolucion', []),
            totales=data.get('totales', {})
        )
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Monitor_Produccion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pallets-disponibles")
async def get_pallets_disponibles(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    planta: Optional[str] = Query(None, description="Filtrar por planta"),
    producto_id: Optional[int] = Query(None, description="Filtrar por producto"),
    proveedor_id: Optional[int] = Query(None, description="Filtrar por proveedor"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    pallet_codigo: Optional[str] = Query(None, description="Buscar pallet por código")
):
    """
    Obtiene pallets disponibles que NO están en ninguna fabricación.
    Excluye ubicaciones de stock final y cámaras.
    """
    try:
        from backend.services.pallets_disponibles_service import PalletsDisponiblesService
        service = PalletsDisponiblesService(username=username, password=password)
        return service.get_pallets_disponibles(planta, producto_id, proveedor_id,
                                                fecha_desde, fecha_hasta, pallet_codigo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pallets-disponibles/productos-2026")
async def get_productos_2026(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene productos únicos del año 2026 basados en lotes existentes.
    """
    try:
        from backend.services.pallets_disponibles_service import PalletsDisponiblesService
        service = PalletsDisponiblesService(username=username, password=password)
        return {"productos": service.get_productos_2026()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pallets-disponibles/proveedores")
async def get_proveedores_compras(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene proveedores (productores) del módulo de compras.
    """
    try:
        from backend.services.pallets_disponibles_service import PalletsDisponiblesService
        service = PalletsDisponiblesService(username=username, password=password)
        return {"proveedores": service.get_proveedores_compras()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/productos_pt")
async def get_productos_pt(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
):
    """
    Obtiene la lista de productos terminados (códigos 3x/4x) de Odoo.
    Retorna lista de {code, name} para usar en filtros.
    """
    try:
        service = ProduccionService(username=username, password=password)
        # Buscar productos con default_code que empiece con 3 o 4 (producto terminado)
        domain = [
            '|',
            ('default_code', '=like', '3%'),
            ('default_code', '=like', '4%'),
        ]
        product_ids = service.odoo.search('product.product', domain, limit=500)
        products = service.odoo.read('product.product', product_ids, ['default_code', 'name'])
        resultado = []
        for p in products:
            code = (p.get('default_code') or '').strip()
            name = (p.get('name') or '').strip()
            if code:
                resultado.append({"code": code, "name": name})
        resultado.sort(key=lambda x: x['code'])
        return {"productos": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# TRAZABILIDAD DE PALLETS
# =====================================================================

@router.get("/trazabilidad")
async def trazar_pallet(
    pallet_name: str = Query(..., description="Nombre del pallet a trazar (ej: PACK0012345)"),
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
):
    """
    Traza un pallet hacia atrás a través de órdenes de fabricación
    hasta llegar a materia prima (MP/fresco) y sus recepciones.
    """
    try:
        from backend.services.trazabilidad_pallet_service import TrazabilidadPalletService
        service = TrazabilidadPalletService(username=username, password=password)
        return service.trazar_pallet(pallet_name)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

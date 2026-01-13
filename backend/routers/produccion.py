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

"""
Router de Rendimiento Productivo - Análisis de eficiencia por lote
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.rendimiento_service import RendimientoService

router = APIRouter(prefix="/api/v1/rendimiento", tags=["rendimiento"])


@router.get("/overview")
async def get_overview(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    Obtiene KPIs consolidados de rendimiento para el período.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_overview(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard_completo(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    OPTIMIZADO: Obtiene TODOS los datos del dashboard en una sola llamada.
    
    Retorna:
    - overview: KPIs consolidados
    - consolidado: Datos por fruta/manejo
    - salas: Productividad por sala
    - mos: Lista de MOs con rendimiento
    
    Reduce llamadas a Odoo de ~4N a ~2N (donde N = número de MOs).
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_dashboard_completo(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lotes")
async def get_rendimiento_lotes(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    Obtiene rendimiento detallado por lote de MP.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_rendimiento_por_lote(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proveedores")
async def get_rendimiento_proveedores(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    Obtiene rendimiento agrupado por proveedor.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_rendimiento_por_proveedor(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mos")
async def get_rendimiento_mos(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    Obtiene análisis de rendimiento por MO individual.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_rendimiento_mos(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ranking")
async def get_ranking_proveedores(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    top_n: int = Query(5, description="Cantidad de top/bottom proveedores")
):
    """
    Obtiene ranking de Top N y Bottom N proveedores por rendimiento.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_ranking_proveedores(fecha_inicio, fecha_fin, top_n)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/salas")
async def get_productividad_salas(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    Obtiene KPIs de productividad agrupados por sala de proceso.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_productividad_por_sala(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pt-detalle")
async def get_pt_detalle(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    Obtiene detalle de productos PT generados por cada lote MP.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_detalle_pt_por_lote(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/consolidado")
async def get_consolidado_fruta(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    Vista ejecutiva: KPIs consolidados por Tipo de Fruta, Manejo y Producto.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_consolidado_fruta(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report.pdf")
async def get_report_pdf(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    Genera un informe PDF de rendimiento de producción.
    """
    from fastapi.responses import Response
    from backend.services.produccion_report_service import generate_produccion_report_pdf
    
    try:
        service = RendimientoService(username=username, password=password)
        
        # Obtener datos usando el método unificado que tiene proceso_* y congelado_*
        dashboard_data = service.get_dashboard_completo(fecha_inicio, fecha_fin)
        
        overview = dashboard_data.get('overview', {})
        consolidado = dashboard_data.get('consolidado', {})
        mos = dashboard_data.get('mos', [])
        salas = dashboard_data.get('salas', [])
        
        # Generar PDF
        pdf_bytes = generate_produccion_report_pdf(
            overview=overview,
            consolidado=consolidado,
            mos=mos,
            salas=salas,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=produccion_{fecha_inicio}_a_{fecha_fin}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

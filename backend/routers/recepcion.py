from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from backend.services.recepcion_service import get_recepciones_mp
from backend.services.recepciones_gestion_service import RecepcionesGestionService
from backend.services.report_service import generate_recepcion_report_pdf
from backend.services.excel_service import generate_recepciones_excel
from fastapi.responses import StreamingResponse
from io import BytesIO

router = APIRouter(prefix="/api/v1/recepciones-mp", tags=["recepciones-mp"])


@router.get("/")
async def get_recepciones(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    productor_id: Optional[int] = Query(None, description="ID del productor"),
    solo_hechas: bool = Query(True, description="Si es True, solo muestra recepciones en estado 'hecho'. Si es False, muestra todas."),
    origen: Optional[List[str]] = Query(None, description="Orígenes a filtrar: RFP, VILKUN, o ambos. Si no se especifica, muestra ambos.")
):
    """
    Obtiene las recepciones de materia prima con datos de calidad.
    
    Parámetros:
        origen: Lista de orígenes. Valores válidos: "RFP" (ID 1), "VILKUN" (ID 217).
                Si no se especifica, muestra recepciones de ambos orígenes.
    """
    # DEBUG: Log incoming origen parameter
    print(f"[DEBUG router] origen recibido en endpoint: {origen}, tipo: {type(origen)}")
    
    try:
        data = get_recepciones_mp(username, password, fecha_inicio, fecha_fin, productor_id, solo_hechas, origen)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/report')
async def get_recepciones_report(
    username: str,
    password: str,
    fecha_inicio: str,
    fecha_fin: str,
    include_prev_week: bool = False,
    include_month_accum: bool = False,
    solo_hechas: bool = True,
):
    """Genera y entrega un PDF con el informe de recepciones para el rango solicitado."""
    try:
        pdf_bytes = generate_recepcion_report_pdf(username, password, fecha_inicio, fecha_fin, include_prev_week, include_month_accum, solo_hechas=solo_hechas)
        buf = BytesIO(pdf_bytes)
        filename = f"informe_recepciones_{fecha_inicio}_a_{fecha_fin}.pdf"
        return StreamingResponse(buf, media_type='application/pdf', headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.get('/report.xlsx')
async def get_recepciones_report_xlsx(
    username: str,
    password: str,
    fecha_inicio: str,
    fecha_fin: str,
    include_prev_week: bool = False,
    include_month_accum: bool = False,
    solo_hechas: bool = True,
    tipo_fruta: Optional[List[str]] = Query(None),
    clasificacion: Optional[List[str]] = Query(None),
    manejo: Optional[List[str]] = Query(None),
    productor: Optional[List[str]] = Query(None),
):
    """Genera y entrega un Excel (.xlsx) con detalle de recepciones y productos desglosados."""
    try:
        xlsx_bytes = generate_recepciones_excel(
            username, password, fecha_inicio, fecha_fin, 
            include_prev_week, include_month_accum, solo_hechas=solo_hechas,
            filter_tipo_fruta=tipo_fruta, filter_clasificacion=clasificacion,
            filter_manejo=manejo, filter_productor=productor
        )
        buf = BytesIO(xlsx_bytes)
        filename = f"informe_recepciones_{fecha_inicio}_a_{fecha_fin}.xlsx"
        return StreamingResponse(buf, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
#              ENDPOINTS DE GESTIÓN DE RECEPCIONES
# ============================================================

@router.get('/gestion')
async def get_recepciones_gestion(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    status_filter: Optional[str] = Query(None, description="Filtro estado validación"),
    qc_filter: Optional[str] = Query(None, description="Filtro estado QC"),
    search_text: Optional[str] = Query(None, description="Buscar por número de albarán")
):
    """
    Lista de recepciones con estados de validación y control de calidad.
    Similar al endpoint /compras/ordenes pero para recepciones de MP.
    """
    try:
        service = RecepcionesGestionService(username=username, password=password)
        return service.get_recepciones_gestion(
            fecha_inicio, fecha_fin,
            status_filter=status_filter,
            qc_filter=qc_filter,
            search_text=search_text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/gestion/overview')
async def get_recepciones_gestion_overview(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    KPIs consolidados de gestión de recepciones.
    """
    try:
        service = RecepcionesGestionService(username=username, password=password)
        return service.get_overview(fecha_inicio, fecha_fin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
#              ENDPOINTS DE CURVA DE ABASTECIMIENTO
# ============================================================

from backend.services.abastecimiento_service import (
    get_proyecciones_por_semana,
    get_proyecciones_por_especie,
    get_especies_disponibles,
    get_semanas_disponibles,
    get_precios_por_especie,
    get_precios_detalle_productor
)

@router.get('/abastecimiento/precios-detalle')
async def get_precios_detalle_abastecimiento(
    planta: Optional[List[str]] = Query(None, description="Plantas a filtrar: RFP, VILKUN"),
    especie: Optional[List[str]] = Query(None, description="Especies a filtrar")
):
    """
    Obtiene los precios proyectados por PRODUCTOR y especie.
    Retorna precio promedio ponderado por kg para cada combinación.
    """
    try:
        return get_precios_detalle_productor(planta=planta, especie=especie)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/abastecimiento/proyectado')
async def get_proyecciones_abastecimiento(
    planta: Optional[List[str]] = Query(None, description="Plantas a filtrar: RFP, VILKUN"),
    especie: Optional[List[str]] = Query(None, description="Especies a filtrar")
):
    """
    Obtiene las proyecciones de abastecimiento por semana desde el Excel.
    """
    try:
        return get_proyecciones_por_semana(planta=planta, especie=especie)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/abastecimiento/especies')
async def get_especies_abastecimiento():
    """
    Obtiene las especies disponibles en el Excel de abastecimiento.
    """
    try:
        return get_especies_disponibles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/abastecimiento/semanas')
async def get_semanas_abastecimiento():
    """
    Obtiene las semanas disponibles en el Excel de abastecimiento.
    """
    try:
        return get_semanas_disponibles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/abastecimiento/precios')
async def get_precios_abastecimiento(
    planta: Optional[List[str]] = Query(None, description="Plantas a filtrar: RFP, VILKUN"),
    especie: Optional[List[str]] = Query(None, description="Especies a filtrar")
):
    """
    Obtiene los precios proyectados por especie desde el Excel.
    Retorna precio promedio ponderado por kg para cada especie.
    """
    try:
        return get_precios_por_especie(planta=planta, especie=especie)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


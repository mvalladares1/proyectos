"""
Router de Recepciones MP - Materia Prima
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.recepcion_service import get_recepciones_mp
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


@router.get('/report')
async def get_recepciones_report(
    username: str,
    password: str,
    fecha_inicio: str,
    fecha_fin: str,
    include_prev_week: bool = False,
    include_month_accum: bool = False,
):
    """Genera y entrega un PDF con el informe de recepciones para el rango solicitado."""
    try:
        pdf_bytes = generate_recepcion_report_pdf(username, password, fecha_inicio, fecha_fin, include_prev_week, include_month_accum)
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
):
    """Genera y entrega un Excel (.xlsx) con detalle de recepciones y productos desglosados."""
    try:
        xlsx_bytes = generate_recepciones_excel(username, password, fecha_inicio, fecha_fin, include_prev_week, include_month_accum)
        buf = BytesIO(xlsx_bytes)
        filename = f"informe_recepciones_{fecha_inicio}_a_{fecha_fin}.xlsx"
        return StreamingResponse(buf, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

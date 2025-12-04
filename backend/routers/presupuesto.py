from fastapi import APIRouter, Query, UploadFile, File
from typing import Optional
from io import BytesIO

import pandas as pd

from backend.services.presupuesto_service import (
    DATA_DIR,
    get_presupuesto,
    comparar_real_vs_ppto
)
from backend.services.estado_resultado_service import get_estado_resultado

router = APIRouter(prefix="/api/v1/presupuesto", tags=["Presupuesto"])


@router.get("/", summary="Obtener presupuesto")
def presupuesto(
    año: int = Query(2025, alias="año", description="Año del presupuesto (2025 o 2026)"),
    mes: Optional[str] = Query(None, description="Mes específico (YYYY-MM)"),
    centro_costo: Optional[str] = Query(None, description="Centro de costo")
):
    return get_presupuesto(año, mes, centro_costo)


@router.post("/upload/{anio}", summary="Subir archivo de presupuesto")
async def upload_presupuesto(
    anio: int,
    file: UploadFile = File(...)
):
    contents = await file.read()
    filename = f"BD_PPTO_{anio}.xlsx"
    filepath = DATA_DIR / filename
    filepath.write_bytes(contents)

    excel_file = pd.ExcelFile(BytesIO(contents))
    hojas = excel_file.sheet_names
    df_preview = pd.read_excel(BytesIO(contents), sheet_name=0, nrows=5)

    return {
        "message": f"Archivo de presupuesto {anio} subido correctamente",
        "filename": filename,
        "hojas_disponibles": hojas,
        "columnas": list(df_preview.columns),
        "filas_ejemplo": len(df_preview)
    }


@router.get("/comparacion", summary="Comparar Real vs Presupuesto")
def comparacion_real_vs_ppto(
    año: int = Query(2025, description="Año a comparar"),
    mes: Optional[str] = Query(None, description="Mes específico (YYYY-MM)")
):
    ppto = get_presupuesto(año, mes)
    if isinstance(ppto, dict) and "error" in ppto:
        return ppto

    fecha_inicio = f"{año}-01-01"
    fecha_fin = f"{año}-12-31" if not mes else f"{mes}-31"

    datos_reales = get_estado_resultado(fecha_inicio, fecha_fin)
    if isinstance(datos_reales, dict) and "error" in datos_reales:
        return datos_reales

    estructura = datos_reales.get("estructura", {})
    reales_ytd = {cat: data.get("total", 0) for cat, data in estructura.items()}

    comparacion = comparar_real_vs_ppto(reales_ytd, ppto.get("ytd", {}))

    return {
        "año": año,
        "mes": mes,
        "comparacion": comparacion,
        "reales_ytd": reales_ytd,
        "ppto_ytd": ppto.get("ytd", {})
    }

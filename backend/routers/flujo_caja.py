"""
Router de Flujo de Caja - API endpoints para Estado de Flujo de Efectivo.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Optional
import json

from backend.services.flujo_caja_service import FlujoCajaService

router = APIRouter(prefix="/api/v1/flujo-caja", tags=["Flujo de Caja"])


@router.get("/")
async def get_flujo_efectivo(
    fecha_inicio: str,
    fecha_fin: str,
    username: str,
    password: str,
    company_id: Optional[int] = None
):
    """
    Obtiene el Estado de Flujo de Efectivo para el período indicado.
    
    Args:
        fecha_inicio: Fecha inicio del período (YYYY-MM-DD)
        fecha_fin: Fecha fin del período (YYYY-MM-DD)
        username: Usuario Odoo
        password: Contraseña Odoo
        company_id: ID de compañía (opcional)
    
    Returns:
        Estado de Flujo de Efectivo estructurado según NIIF IAS 7
    """
    try:
        service = FlujoCajaService(username=username, password=password)
        resultado = service.get_flujo_efectivo(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            company_id=company_id
        )
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mapeo")
async def get_mapeo(
    username: str,
    password: str
):
    """
    Obtiene el mapeo actual de cuentas contables a líneas del flujo.
    """
    try:
        service = FlujoCajaService(username=username, password=password)
        return {
            "mapeo": service.get_mapeo(),
            "estructura": {
                "OPERACION": "Actividades de Operación",
                "INVERSION": "Actividades de Inversión", 
                "FINANCIAMIENTO": "Actividades de Financiamiento"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mapeo")
async def update_mapeo(
    mapeo: dict,
    username: str,
    password: str
):
    """
    Actualiza el mapeo de cuentas contables.
    
    El mapeo debe tener la estructura:
    {
        "cuentas_efectivo": {
            "prefijos": ["110", "111"],
            "codigos_especificos": []
        },
        "mapeo_lineas": {
            "OP01": {"prefijos": ["410", "411"], "descripcion": "Ventas"},
            ...
        }
    }
    """
    try:
        service = FlujoCajaService(username=username, password=password)
        if service.guardar_mapeo(mapeo):
            return {"status": "ok", "message": "Mapeo actualizado correctamente"}
        else:
            raise HTTPException(status_code=500, detail="Error guardando mapeo")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mapeo/upload")
async def upload_mapeo(
    file: UploadFile = File(...),
    username: str = "",
    password: str = ""
):
    """
    Carga mapeo desde archivo JSON.
    """
    try:
        content = await file.read()
        mapeo = json.loads(content.decode('utf-8'))
        
        service = FlujoCajaService(username=username, password=password)
        if service.guardar_mapeo(mapeo):
            return {
                "status": "ok",
                "filename": file.filename,
                "message": "Mapeo cargado correctamente"
            }
        else:
            raise HTTPException(status_code=500, detail="Error guardando mapeo")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Archivo JSON inválido")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cuentas-efectivo")
async def get_cuentas_efectivo(
    username: str,
    password: str
):
    """
    Obtiene las cuentas configuradas como efectivo y equivalentes.
    """
    try:
        service = FlujoCajaService(username=username, password=password)
        cuentas = service.get_cuentas_efectivo_detalle()
        return {
            "cuentas": cuentas,
            "total": len(cuentas)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/estructura")
async def get_estructura():
    """
    Obtiene la estructura del Estado de Flujo de Efectivo según NIIF IAS 7.
    """
    from backend.services.flujo_caja_service import ESTRUCTURA_FLUJO
    return {
        "estructura": ESTRUCTURA_FLUJO,
        "version": "NIIF IAS 7 - Método Directo"
    }


@router.get("/diagnostico")
async def get_diagnostico(
    fecha_inicio: str,
    fecha_fin: str,
    username: str,
    password: str,
    company_id: Optional[int] = None
):
    """
    Obtiene diagnóstico de cuentas no clasificadas para ajustar el mapeo.
    
    Retorna las cuentas que generan "Otros no clasificados" con su código,
    nombre y monto total para facilitar la clasificación manual.
    """
    try:
        service = FlujoCajaService(username=username, password=password)
        diagnostico = service.get_diagnostico_no_clasificados(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            company_id=company_id
        )
        return diagnostico
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


"""
Router de Flujo de Caja - API endpoints para Estado de Flujo de Efectivo.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Optional
import json
import logging

# Importar desde módulo modularizado
from backend.services.flujo_caja_service import FlujoCajaService

logger = logging.getLogger(__name__)

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
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        logger.error(f"Error en get_flujo_efectivo: {error_detail}")
        print(f"ERROR FLUJO CAJA: {error_detail}", flush=True)
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/mensual")
async def get_flujo_mensualizado(
    fecha_inicio: str,
    fecha_fin: str,
    username: str,
    password: str,
    company_id: Optional[int] = None
):
    """
    Obtiene el Estado de Flujo de Efectivo con granularidad MENSUAL.
    
    Retorna datos agrupados por mes para visualización tipo Excel con columnas por mes.
    
    Args:
        fecha_inicio: Fecha inicio del período (YYYY-MM-DD)
        fecha_fin: Fecha fin del período (YYYY-MM-DD)
        username: Usuario Odoo
        password: Contraseña Odoo
        company_id: ID de compañía (opcional)
    
    Returns:
        {
            "meses": ["2026-01", "2026-02", ...],
            "actividades": {
                "OPERACION": {
                    "conceptos": [
                        {"id": "1.1.1", "nombre": "Ventas", "montos_por_mes": {"2026-01": 1000, ...}}
                    ]
                }
            },
            "efectivo_por_mes": {"2026-01": {...}, ...}
        }
    """
    try:
        service = FlujoCajaService(username=username, password=password)
        resultado = service.get_flujo_mensualizado(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            company_id=company_id
        )
        return resultado
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        logger.error(f"Error en get_flujo_mensualizado: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/semanal")
async def get_flujo_semanal(
    fecha_inicio: str,
    fecha_fin: str,
    username: str,
    password: str,
    company_id: Optional[int] = None
):
    """
    Obtiene el Estado de Flujo de Efectivo con granularidad SEMANAL.
    
    Retorna datos agrupados por semana (ISO week) para visualización con columnas por semana.
    
    Args:
        fecha_inicio: Fecha inicio del período (YYYY-MM-DD)
        fecha_fin: Fecha fin del período (YYYY-MM-DD)
        username: Usuario Odoo
        password: Contraseña Odoo
        company_id: ID de compañía (opcional)
    
    Returns:
        {
            "semanas": ["2026-W01", "2026-W02", ...],
            "actividades": {
                "OPERACION": {
                    "conceptos": [
                        {"id": "1.1.1", "nombre": "Ventas", "montos_por_semana": {"2026-W01": 1000, ...}}
                    ]
                }
            },
            "efectivo_por_semana": {"2026-W01": {...}, ...}
        }
    """
    try:
        service = FlujoCajaService(username=username, password=password)
        resultado = service.get_flujo_mensualizado(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            company_id=company_id,
            agrupacion='semanal'
        )
        return resultado
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        logger.error(f"Error en get_flujo_semanal: {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)


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


@router.post("/mapeo-cuenta")
async def guardar_mapeo_cuenta(
    codigo: str,
    categoria: str,
    nombre: str = "",
    username: str = "",
    password: str = "",
    impacto_estimado: float = None
):
    """
    Guarda o actualiza el mapeo de una cuenta individual.
    
    Args:
        codigo: Código de la cuenta contable
        categoria: Categoría de flujo (OP01, IN03, FI01, NEUTRAL, FX_EFFECT, etc.)
        nombre: Nombre descriptivo de la cuenta
        impacto_estimado: Monto estimado del impacto de esta cuenta
    """
    # Validar categoría - Aceptar códigos legacy (OP01) Y nuevos IAS 7 (1.1.1)
    categorias_validas = [
        # Códigos IAS 7 nuevos (FASE 1)
        "1.1.1", "1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.2.5", "1.2.6",
        "2.1", "2.2", "2.3", "2.4", "2.5",
        "3.0.1", "3.0.2", "3.1.1", "3.1.2", "3.1.3", "3.1.4", "3.1.5", "3.2.3",
        "4.2",
        # Códigos legacy (retrocompatibilidad)
        "OP01", "OP02", "OP03", "OP04", "OP05", "OP06", "OP07",
        "IN01", "IN02", "IN03", "IN04", "IN05", "IN06",
        "FI01", "FI02", "FI03", "FI04", "FI05", "FI06", "FI07",
        # Técnicos
        "NEUTRAL", "FX_EFFECT"
    ]
    if categoria not in categorias_validas:
        raise HTTPException(status_code=400, detail=f"Categoría inválida: {categoria}")
    
    try:
        service = FlujoCajaService(username=username, password=password)
        if service.guardar_mapeo_cuenta(codigo, categoria, nombre, impacto_estimado=impacto_estimado):
            return {
                "status": "ok",
                "message": f"Cuenta {codigo} mapeada a {categoria}",
                "cuenta": {"codigo": codigo, "categoria": categoria, "nombre": nombre}
            }
        else:
            raise HTTPException(status_code=500, detail="Error guardando mapeo")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/mapeo/all")
async def reset_mapeo_completo(
    username: str = "",
    password: str = ""
):
    """
    ⚠️ PELIGRO: Resetea COMPLETAMENTE todo el mapeo de cuentas.
    Requiere confirmación explícita desde frontend.
    """
    try:
        service = FlujoCajaService(username=username, password=password)
        if service.reset_mapeo():
            return {"status": "ok", "message": "Mapeo reseteado completamente"}
        else:
            raise HTTPException(status_code=500, detail="Error reseteando mapeo")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/mapeo-cuenta/{codigo}")
async def eliminar_mapeo_cuenta(
    codigo: str,
    username: str = "",
    password: str = ""
):
    """
    Elimina el mapeo de una cuenta.
    """
    try:
        service = FlujoCajaService(username=username, password=password)
        if service.eliminar_mapeo_cuenta(codigo):
            return {"status": "ok", "message": f"Mapeo de cuenta {codigo} eliminado"}
        else:
            raise HTTPException(status_code=500, detail="Error eliminando mapeo")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categorias")
async def get_categorias():
    """
    Retorna las categorías disponibles para clasificar cuentas.
    """
    return {
        "operacion": [
            {"codigo": "OP01", "nombre": "Cobros procedentes de las ventas de bienes y prestación de servicios"},
            {"codigo": "OP02", "nombre": "Pagos a proveedores por el suministro de bienes y servicios"},
            {"codigo": "OP03", "nombre": "Pagos a y por cuenta de los empleados"},
            {"codigo": "OP04", "nombre": "Intereses pagados"},
            {"codigo": "OP05", "nombre": "Intereses recibidos"},
            {"codigo": "OP06", "nombre": "Impuestos a las ganancias reembolsados (pagados)"},
            {"codigo": "OP07", "nombre": "Otras entradas (salidas) de efectivo operativas"}
        ],
        "inversion": [
            {"codigo": "IN01", "nombre": "Flujos para obtener el control de subsidiarias"},
            {"codigo": "IN02", "nombre": "Flujos en compra de participaciones no controladoras"},
            {"codigo": "IN03", "nombre": "Compras de propiedades, planta y equipo"},
            {"codigo": "IN04", "nombre": "Compras de activos intangibles"},
            {"codigo": "IN05", "nombre": "Dividendos recibidos"},
            {"codigo": "IN06", "nombre": "Ventas de propiedades, planta y equipo"}
        ],
        "financiamiento": [
            {"codigo": "FI01", "nombre": "Importes procedentes de préstamos de largo plazo"},
            {"codigo": "FI02", "nombre": "Importes procedentes de préstamos de corto plazo"},
            {"codigo": "FI03", "nombre": "Préstamos de entidades relacionadas"},
            {"codigo": "FI04", "nombre": "Pagos de préstamos"},
            {"codigo": "FI05", "nombre": "Pagos de préstamos a entidades relacionadas"},
            {"codigo": "FI06", "nombre": "Pagos de pasivos por arrendamientos financieros"},
            {"codigo": "FI07", "nombre": "Dividendos pagados"}
        ],
        "tecnicas": [
            {"codigo": "NEUTRAL", "nombre": "Transferencias internas (no impacta flujo)"},
            {"codigo": "FX_EFFECT", "nombre": "Diferencias de tipo de cambio sobre efectivo"}
        ]
    }

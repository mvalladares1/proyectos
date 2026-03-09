"""
Router de Flujo de Caja - API endpoints para Estado de Flujo de Efectivo.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
import json
import logging

# Importar desde módulo modularizado
from backend.services.flujo_caja_service import FlujoCajaService
from backend.services import distribuciones_oc_service

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
    company_id: Optional[int] = None,
    incluir_proyecciones: Optional[bool] = False
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
        incluir_proyecciones: Si True, incluye presupuestos de venta (draft/sent) como Facturas Proyectadas (opcional)
    
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
            company_id=company_id,
            incluir_proyecciones=incluir_proyecciones
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
    company_id: Optional[int] = None,
    incluir_proyecciones: Optional[bool] = False
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
        incluir_proyecciones: Si True, incluye presupuestos de venta (draft/sent) como Facturas Proyectadas (opcional)
    
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
            agrupacion='semanal',
            incluir_proyecciones=incluir_proyecciones
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

# ─── Configuración Global de Efectivo Inicial ─────────────────────────────────

import os
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel

# Ruta al archivo de configuración
CONFIG_FILE = Path(__file__).parent.parent / "data" / "flujo_caja_config.json"


class EfectivoInicialConfig(BaseModel):
    valor: float
    usar_personalizado: bool = True


class EfectivoInicialResponse(BaseModel):
    valor: Optional[float]
    usar_personalizado: bool
    actualizado_por: Optional[str]
    actualizado_en: Optional[str]


def _load_config() -> dict:
    """Carga la configuración del archivo JSON."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "efectivo_inicial": {
            "valor": None,
            "usar_personalizado": False,
            "actualizado_por": None,
            "actualizado_en": None
        }
    }


def _save_config(config: dict):
    """Guarda la configuración al archivo JSON."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


@router.get("/config/efectivo-inicial")
async def get_efectivo_inicial_config():
    """
    Obtiene la configuración actual del efectivo inicial.
    
    Returns:
        Configuración del efectivo inicial (valor, si usar personalizado, quién lo actualizó)
    """
    config = _load_config()
    return config.get("efectivo_inicial", {
        "valor": None,
        "usar_personalizado": False,
        "actualizado_por": None,
        "actualizado_en": None
    })


@router.post("/config/efectivo-inicial")
async def set_efectivo_inicial_config(
    valor: float,
    usar_personalizado: bool = True,
    username: Optional[str] = None
):
    """
    Establece la configuración del efectivo inicial.
    
    Este valor será usado globalmente por todos los usuarios cuando usar_personalizado=True.
    Si usar_personalizado=False, se calculará automáticamente desde Odoo.
    
    Args:
        valor: Valor del efectivo inicial en CLP
        usar_personalizado: Si True, usa el valor personalizado. Si False, calcula desde Odoo.
        username: Usuario que realiza el cambio (para auditoría)
    
    Returns:
        Configuración actualizada
    """
    config = _load_config()
    config["efectivo_inicial"] = {
        "valor": valor,
        "usar_personalizado": usar_personalizado,
        "actualizado_por": username,
        "actualizado_en": datetime.now().isoformat()
    }
    _save_config(config)
    
    logger.info(f"Efectivo inicial actualizado a ${valor:,.0f} por {username}")
    
    return config["efectivo_inicial"]


@router.delete("/config/efectivo-inicial")
async def reset_efectivo_inicial_config(username: Optional[str] = None):
    """
    Resetea la configuración del efectivo inicial para usar el valor calculado de Odoo.
    
    Args:
        username: Usuario que realiza el cambio (para auditoría)
    
    Returns:
        Configuración reseteada
    """
    config = _load_config()
    config["efectivo_inicial"] = {
        "valor": None,
        "usar_personalizado": False,
        "actualizado_por": username,
        "actualizado_en": datetime.now().isoformat()
    }
    _save_config(config)
    
    logger.info(f"Efectivo inicial reseteado a cálculo automático por {username}")
    
    return config["efectivo_inicial"]


# ============================================================================
# DISTRIBUCIONES DE OC - CRUD
# ============================================================================

class DistribucionItem(BaseModel):
    """Un item de distribución con fecha y monto."""
    fecha: str  # YYYY-MM-DD
    monto: float


class DistribucionOCRequest(BaseModel):
    """Request para crear/actualizar distribución de OC."""
    oc_id: int
    oc_name: str
    proveedor: str
    monto_total: float
    distribuciones: List[DistribucionItem]
    proveedor_id: Optional[int] = None
    created_by: Optional[str] = None


class PlantillaDistribucionRequest(BaseModel):
    """Request para generar plantilla de distribución."""
    monto_total: float
    tipo: str  # "cuotas_iguales", "semanal", "quincenal", "mensual"
    num_cuotas: int
    fecha_inicio: str  # YYYY-MM-DD
    intervalo_dias: Optional[int] = None
    # Datos opcionales de la OC para enriquecer respuesta
    oc_id: Optional[int] = None
    oc_name: Optional[str] = None
    proveedor: Optional[str] = None


@router.get("/distribuciones-oc")
async def listar_distribuciones_oc():
    """
    Lista todas las distribuciones de OCs activas.
    
    Returns:
        Lista de distribuciones con sus detalles
    """
    try:
        return distribuciones_oc_service.listar_distribuciones()
    except Exception as e:
        logger.error(f"Error listando distribuciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/distribuciones-oc/{oc_id}")
async def obtener_distribucion_oc(oc_id: int):
    """
    Obtiene la distribución de una OC específica.
    
    Args:
        oc_id: ID de la OC en Odoo
        
    Returns:
        Distribución si existe, 404 si no
    """
    try:
        distribucion = distribuciones_oc_service.obtener_distribucion(oc_id)
        if not distribucion:
            raise HTTPException(status_code=404, detail=f"No existe distribución para OC {oc_id}")
        return distribucion
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo distribución {oc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/distribuciones-oc")
async def crear_actualizar_distribucion_oc(request: DistribucionOCRequest):
    """
    Crea o actualiza la distribución de una OC.
    
    La suma de las distribuciones debe ser igual al monto_total.
    Si ya existe una distribución para la OC, se actualiza.
    
    Args:
        request: Datos de la distribución
        
    Returns:
        Distribución creada/actualizada
    """
    try:
        distribuciones_list = [d.model_dump() for d in request.distribuciones]
        
        result = distribuciones_oc_service.crear_o_actualizar_distribucion(
            oc_id=request.oc_id,
            oc_name=request.oc_name,
            proveedor=request.proveedor,
            monto_total=request.monto_total,
            distribuciones=distribuciones_list,
            proveedor_id=request.proveedor_id,
            created_by=request.created_by
        )
        
        logger.info(f"Distribución OC {request.oc_id} creada/actualizada: {len(distribuciones_list)} cuotas")
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creando distribución: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/distribuciones-oc/{oc_id}")
async def eliminar_distribucion_oc(oc_id: int):
    """
    Elimina la distribución de una OC.
    
    Usar cuando la OC se factura o se cancela.
    
    Args:
        oc_id: ID de la OC en Odoo
        
    Returns:
        Confirmación de eliminación
    """
    try:
        eliminada = distribuciones_oc_service.eliminar_distribucion(oc_id)
        if not eliminada:
            raise HTTPException(status_code=404, detail=f"No existe distribución para OC {oc_id}")
        
        logger.info(f"Distribución OC {oc_id} eliminada")
        return {"success": True, "message": f"Distribución OC {oc_id} eliminada"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando distribución {oc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/distribuciones-oc/generar-plantilla")
async def generar_plantilla_distribucion(request: PlantillaDistribucionRequest):
    """
    Genera una distribución automática basada en plantilla.
    
    NO guarda la distribución, solo la sugiere para que el usuario la revise.
    
    Args:
        request: Parámetros de la plantilla
        
    Returns:
        Distribución sugerida (lista de {fecha, monto})
    """
    try:
        distribuciones = distribuciones_oc_service.generar_plantilla_distribucion(
            monto_total=request.monto_total,
            tipo=request.tipo,
            num_cuotas=request.num_cuotas,
            fecha_inicio=request.fecha_inicio,
            intervalo_dias=request.intervalo_dias
        )
        
        # Enriquecer respuesta con datos de OC si se proporcionaron
        response = {
            "monto_total": request.monto_total,
            "tipo": request.tipo,
            "num_cuotas": request.num_cuotas,
            "distribuciones": distribuciones
        }
        
        if request.oc_id:
            response["oc_id"] = request.oc_id
        if request.oc_name:
            response["oc_name"] = request.oc_name
        if request.proveedor:
            response["proveedor"] = request.proveedor
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generando plantilla: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocs-sin-facturar")
async def listar_ocs_sin_facturar(
    username: str,
    password: str
):
    """
    Lista OCs confirmadas sin facturar (candidatas a distribuir).
    
    Args:
        username: Usuario Odoo
        password: Contraseña Odoo
        
    Returns:
        Lista de OCs con sus datos básicos y si tienen distribución
    """
    try:
        service = FlujoCajaService(username=username, password=password)
        
        # Consultar OCs sin facturar
        campos_oc = [
            'id', 'name', 'partner_id', 'amount_total', 'date_order',
            'date_planned', 'currency_id', 'x_studio_fecha_de'
        ]
        
        ocs = service.odoo.search_read(
            'purchase.order',
            [
                ['state', '=', 'purchase'],
                ['invoice_ids', '=', False]
            ],
            campos_oc,
            limit=10000
        )
        
        # Obtener IDs de OCs para verificar cuáles tienen distribución
        oc_ids = [oc['id'] for oc in ocs]
        distribuciones = distribuciones_oc_service.obtener_distribuciones_por_ids(oc_ids)
        
        # Formatear resultado
        from backend.services.currency_service import CurrencyService
        
        resultado = []
        for oc in ocs:
            partner_data = oc.get('partner_id', [0, 'Sin proveedor'])
            partner_id = partner_data[0] if isinstance(partner_data, (list, tuple)) else 0
            partner_name = partner_data[1] if isinstance(partner_data, (list, tuple)) and len(partner_data) > 1 else 'Sin proveedor'
            
            amount_total = float(oc.get('amount_total') or 0)
            
            # Convertir moneda si es necesario
            currency_data = oc.get('currency_id')
            currency_name = currency_data[1] if isinstance(currency_data, (list, tuple)) and len(currency_data) > 1 else 'CLP'
            if currency_name:
                currency_upper = str(currency_name).upper()
                if 'USD' in currency_upper:
                    amount_total = CurrencyService.convert_usd_to_clp(amount_total)
                elif 'UF' in currency_upper or 'CLF' in currency_upper:
                    amount_total = CurrencyService.convert_uf_to_clp(amount_total)
            
            # Determinar fecha proyectada actual
            fecha_pago = oc.get('x_studio_fecha_de')
            fecha_planned = oc.get('date_planned')
            fecha_proyectada = fecha_pago or fecha_planned or oc.get('date_order')
            if fecha_proyectada:
                fecha_proyectada = str(fecha_proyectada)[:10]
            
            resultado.append({
                "oc_id": oc['id'],
                "name": oc.get('name', ''),
                "proveedor": partner_name,
                "proveedor_id": partner_id,
                "monto_total": amount_total,
                "moneda_original": currency_name,
                "fecha_oc": str(oc.get('date_order', ''))[:10] if oc.get('date_order') else None,
                "fecha_proyectada": fecha_proyectada,
                "tiene_distribucion": oc['id'] in distribuciones,
                "num_cuotas": len(distribuciones.get(oc['id'], []))
            })
        
        # Ordenar: primero las que no tienen distribución, luego por monto descendente
        resultado.sort(key=lambda x: (x['tiene_distribucion'], -x['monto_total']))
        
        return {
            "total": len(resultado),
            "con_distribucion": sum(1 for r in resultado if r['tiene_distribucion']),
            "sin_distribucion": sum(1 for r in resultado if not r['tiene_distribucion']),
            "ocs": resultado
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error listando OCs sin facturar: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
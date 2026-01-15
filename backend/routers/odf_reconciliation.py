"""
Router para Reconciliación de ODFs
====================================

Endpoints para reconciliar ODFs con Sale Orders y actualizar
campos de seguimiento (KG totales, consumidos, disponibles).
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Optional, List
from datetime import datetime, date

from backend.services.odf_reconciliation_service import ODFReconciliationService
from backend.services.trigger_so_asociada_service import TriggerSOAsociadaService
from shared.odoo_client import OdooClient

router = APIRouter(prefix="/api/v1/odf-reconciliation", tags=["ODF Reconciliation"])


def get_reconciliation_service() -> ODFReconciliationService:
    """Dependency para obtener servicio de reconciliación autenticado."""
    odoo = OdooClient()
    return ODFReconciliationService(odoo)


def get_trigger_service() -> TriggerSOAsociadaService:
    """Dependency para obtener servicio de trigger SO Asociada."""
    odoo = OdooClient()
    return TriggerSOAsociadaService(odoo)


@router.post("/odf/{odf_id}/reconciliar")
async def reconciliar_odf_single(
    odf_id: int,
    dry_run: bool = Query(False, description="Si es True, solo simula sin escribir a Odoo"),
    service: ODFReconciliationService = Depends(get_reconciliation_service)
) -> Dict:
    """
    Reconcilia una ODF específica.
    
    **Proceso:**
    1. Lee x_studio_po_asociada (ej: "S00843, S00912")
    2. Obtiene líneas de las SOs
    3. Obtiene subproductos de la ODF
    4. Match productos y calcula totales
    5. Escribe x_studio_kg_* a Odoo
    
    **Parámetros:**
    - odf_id: ID de la ODF a reconciliar
    - dry_run: Si es True, solo calcula sin escribir (para preview)
    
    **Retorna:**
    - kg_totales_po: Total kg de todas las SOs
    - kg_consumidos_po: Total kg producidos que coinciden con SOs
    - kg_disponibles_po: Totales - Consumidos
    - desglose_productos: Detalle por producto
    """
    try:
        resultado = service.reconciliar_odf(odf_id, dry_run=dry_run)
        return resultado
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al reconciliar ODF {odf_id}: {str(e)}"
        )


@router.post("/reconciliar-rango")
async def reconciliar_por_fecha(
    fecha_inicio: date = Query(..., description="Fecha inicial (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha final (YYYY-MM-DD)"),
    dry_run: bool = Query(False, description="Si es True, solo simula"),
    service: ODFReconciliationService = Depends(get_reconciliation_service)
) -> Dict:
    """
    Reconcilia todas las ODFs en un rango de fechas.
    
    **Uso típico:**
    - Dashboard con filtro de fechas
    - Scheduled job diario (ej: 18:00 hrs)
    
    **Retorna:**
    - total_odfs: Total encontradas
    - odfs_reconciliadas: Actualizadas correctamente
    - odfs_sin_po: Sin POs asociadas
    - odfs_error: Con errores
    - resultados: Array con detalle de cada ODF
    """
    try:
        resultado = service.reconciliar_odfs_por_fecha(
            fecha_inicio=fecha_inicio.isoformat(),
            fecha_fin=fecha_fin.isoformat(),
            dry_run=dry_run
        )
        return resultado
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al reconciliar ODFs: {str(e)}"
        )


@router.get("/odf/{odf_id}/preview")
async def preview_reconciliacion(
    odf_id: int,
    service: ODFReconciliationService = Depends(get_reconciliation_service)
) -> Dict:
    """
    Preview de reconciliación sin escribir a Odoo.
    
    Útil para mostrar al usuario qué se actualizará antes de confirmar.
    """
    try:
        resultado = service.reconciliar_odf(odf_id, dry_run=True)
        return resultado
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar preview: {str(e)}"
        )


@router.get("/parsear-pos/{po_string}")
async def parsear_pos_string(
    po_string: str,
    service: ODFReconciliationService = Depends(get_reconciliation_service)
) -> Dict:
    """
    Utilitario para parsear campo x_studio_po_asociada.
    
    **Ejemplos:**
    -


# ============================================================================
# ENDPOINTS PARA TRIGGER DE SO ASOCIADA
# ============================================================================

@router.get("/odfs-sin-so-asociada")
async def listar_odfs_sin_so_asociada(
    limit: Optional[int] = Query(None, description="Límite de registros"),
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    service: TriggerSOAsociadaService = Depends(get_trigger_service)
) -> Dict:
    """
    Lista ODFs que tienen PO Cliente pero no SO Asociada.
    
    Estos ODFs necesitan que se triggee la automatización.
    
    **Retorna:**
    - total: Cantidad de ODFs pendientes
    - odfs: Array con información de cada ODF
    """
    try:
        odfs_pendientes = service.get_odfs_pendientes(
            limit=limit,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return {
            "success": True,
            "total": len(odfs_pendientes),
            "odfs": odfs_pendientes
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al listar ODFs sin SO Asociada: {str(e)}"
        )


@router.post("/trigger-so-asociada/{odf_id}")
async def trigger_so_asociada_individual(
    odf_id: int,
    wait_seconds: float = Query(2.0, description="Segundos a esperar entre operaciones"),
    service: TriggerSOAsociadaService = Depends(get_trigger_service)
) -> Dict:
    """
    Triggea la automatización de SO Asociada para un ODF específico.
    
    **Proceso:**
    1. Lee el valor de PO Cliente
    2. Borra el campo PO Cliente
    3. Espera (wait_seconds)
    4. Reescribe el campo PO Cliente
    5. Espera (wait_seconds)
    6. La automatización de Odoo carga SO Asociada
    
    **Retorna:**
    - success: True si se cargó SO Asociada
    - odf_name: Nombre del ODF
    - po_cliente: Valor del PO Cliente
    - so_asociada: Valor cargado por la automatización
    """
    try:
        resultado = service.trigger_so_asociada(odf_id, wait_seconds)
        
        if not resultado['success']:
            raise HTTPException(
                status_code=400, 
                detail=resultado.get('error', 'Error desconocido')
            )
        
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al triggear SO Asociada: {str(e)}"
        )


@router.post("/trigger-so-asociada-bulk")
async def trigger_so_asociada_bulk(
    odf_ids: Optional[List[int]] = Query(None, description="IDs de ODFs a procesar"),
    limit: Optional[int] = Query(None, description="Límite de ODFs a procesar"),
    wait_seconds: float = Query(2.0, description="Segundos a esperar entre operaciones"),
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    service: TriggerSOAsociadaService = Depends(get_trigger_service)
) -> Dict:
    """
    Triggea la automatización de SO Asociada para múltiples ODFs.
    
    Si no se especifican odf_ids, procesa todos los ODFs pendientes
    (que tienen PO Cliente pero no SO Asociada).
    
    **Uso típico:**
    - Procesar todos los pendientes: No enviar odf_ids
    - Procesar solo algunos: Enviar array de IDs
    - Filtrar por fechas: Enviar fecha_inicio y fecha_fin
    
    **Retorna:**
    - total: Total de ODFs procesados
    - exitosos: Cantidad de ODFs con SO Asociada cargada
    - fallidos: Cantidad de ODFs con error
    - resultados: Array con detalle de cada ODF
    """
    try:
        resumen = service.trigger_bulk(
            odf_ids=odf_ids,
            limit=limit,
            wait_seconds=wait_seconds,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return resumen
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en procesamiento bulk: {str(e)}"
        ) "S00843" → ["S00843"]
    - "S00843, S00912" → ["S00843", "S00912"]
    - "S00843,S00912,S00915" → ["S00843", "S00912", "S00915"]
    """
    pos = service.parse_pos_asociadas(po_string)
    return {
        'input': po_string,
        'parsed': pos,
        'count': len(pos)
    }

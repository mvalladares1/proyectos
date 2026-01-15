"""
Router para Reconciliación de Producción
=========================================

Expone endpoints para analizar ODFs con múltiples SO.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List
from datetime import datetime

from backend.services.produccion_reconciliacion_service import ProduccionReconciliador
from shared.odoo_client import OdooClient

router = APIRouter(prefix="/api/v1/produccion-reconciliacion", tags=["Produccion Reconciliación"])


def get_reconciliador() -> ProduccionReconciliador:
    """Dependency para obtener reconciliador autenticado."""
    odoo = OdooClient()
    return ProduccionReconciliador(odoo)


@router.get("/odf/{odf_id}")
async def reconciliar_odf(odf_id: int) -> Dict:
    """Reconcilia una ODF completa."""
    reconciliador = get_reconciliador()
    try:
        resultado = reconciliador.reconciliar_odf(odf_id)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al reconciliar ODF {odf_id}: {str(e)}")


@router.get("/odf/{odf_id}/resumen")
async def resumen_odf(odf_id: int) -> Dict:
    """Versión simplificada: solo resumen y alertas."""
    reconciliador = get_reconciliador()
    try:
        resultado = reconciliador.reconciliar_odf(odf_id)
        return {
            'resumen': resultado['resumen'],
            'alertas': resultado['alertas'],
            'analisis_so': resultado['analisis_so']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen ODF {odf_id}: {str(e)}")


@router.get("/odf/{odf_id}/segmentos")
async def segmentos_odf(odf_id: int) -> List[Dict]:
    """Solo los segmentos de SO detectados."""
    reconciliador = get_reconciliador()
    try:
        consumos = reconciliador.get_consumos_odf(odf_id)
        segmentos = reconciliador.detectar_transiciones_so(consumos)
        return segmentos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al detectar segmentos ODF {odf_id}: {str(e)}")


@router.post("/odf/batch")
async def reconciliar_batch(odf_ids: List[int]) -> Dict:
    """Reconcilia múltiples ODFs en batch."""
    reconciliador = get_reconciliador()
    resultados = []
    errores = []
    
    for odf_id in odf_ids:
        try:
            resultado = reconciliador.reconciliar_odf(odf_id)
            resultados.append(resultado)
        except Exception as e:
            errores.append({'odf_id': odf_id, 'error': str(e)})
    
    return {
        'procesadas': len(resultados),
        'errores': len(errores),
        'resultados': resultados,
        'errores_detalle': errores
    }

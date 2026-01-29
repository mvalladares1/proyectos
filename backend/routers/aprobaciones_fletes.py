"""
Router para gestión de aprobaciones de OC de fletes/transportes.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from backend.services.aprobaciones_fletes_service import AprobacionesFletesService

router = APIRouter(prefix='/api/v1/aprobaciones-fletes', tags=['Aprobaciones Fletes'])


@router.get('/pendientes')
async def get_ocs_pendientes(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
):
    """
    Obtiene OCs de fletes pendientes de aprobación con datos consolidados de Odoo + Logística.
    """
    try:
        service = AprobacionesFletesService(username=username, password=password)
        datos = service.consolidar_datos_aprobacion()
        return {
            'success': True,
            'total': len(datos),
            'data': datos
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/kpis')
async def get_kpis_fletes(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    dias: int = Query(30, description="Días hacia atrás para calcular KPIs"),
):
    """
    Obtiene KPIs de órdenes de fletes en los últimos N días.
    """
    try:
        service = AprobacionesFletesService(username=username, password=password)
        kpis = service.get_kpis_fletes(dias=dias)
        return {
            'success': True,
            'kpis': kpis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/aprobar')
async def aprobar_oc(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    oc_id: int = Query(..., description="ID de la OC a aprobar"),
):
    """
    Aprueba una orden de compra de flete.
    """
    try:
        service = AprobacionesFletesService(username=username, password=password)
        resultado = service.aprobar_oc(oc_id)
        
        if resultado:
            return {
                'success': True,
                'message': f'OC ID {oc_id} aprobada correctamente'
            }
        else:
            raise HTTPException(status_code=400, detail=f'No se pudo aprobar la OC {oc_id}')
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/aprobar-multiples')
async def aprobar_multiples(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    oc_ids: List[int] = Query(..., description="Lista de IDs de OCs a aprobar"),
):
    """
    Aprueba múltiples órdenes de compra de fletes.
    """
    try:
        service = AprobacionesFletesService(username=username, password=password)
        resultado = service.aprobar_multiples_ocs(oc_ids)
        
        return {
            'success': True,
            'resultado': resultado
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/rutas-logistica')
async def get_rutas_logistica(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    con_oc: bool = Query(True, description="Solo rutas con OC generada"),
):
    """
    Obtiene rutas del sistema de logística.
    """
    try:
        service = AprobacionesFletesService(username=username, password=password)
        rutas = service.get_rutas_logistica(con_oc=con_oc)
        
        return {
            'success': True,
            'total': len(rutas),
            'data': rutas
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/maestro-costos')
async def get_maestro_costos(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
):
    """
    Obtiene el maestro de costos presupuestados de rutas.
    """
    try:
        service = AprobacionesFletesService(username=username, password=password)
        costos = service.get_maestro_costos()
        
        return {
            'success': True,
            'total': len(costos),
            'data': costos
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
Router para gestión de aprobaciones de OC de fletes/transportes.
"""

from fastapi import APIRouter, Query, HTTPException, Body
from typing import List, Optional
from pydantic import BaseModel
from backend.services.aprobaciones_fletes_service import AprobacionesFletesService


class RutasPorOcsRequest(BaseModel):
    oc_names: List[str]
    incluir_metadata: bool = False

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


@router.post('/rutas-por-ocs')
async def get_rutas_por_ocs(request: RutasPorOcsRequest):
    """
    Obtiene rutas cruzadas con lista de OCs.
    
    Hace el cruce: OC name → RT correlativo → detalles de ruta.
    Usa endpoint live primero y backup como fallback si faltan rutas.
    
    Body:
        oc_names: Lista de nombres de OC
        incluir_metadata: Si True, retorna también sin_rt y sin_ruta
    
    Returns:
        - data: Dict mapeando OC name → ruta data
        - sin_rt: OCs que no tienen RT en route-ocs (nunca tendrán ruta)
        - sin_ruta: OCs con RT pero sin datos de ruta en live/backup
    """
    try:
        # No necesita credenciales Odoo, solo llama a APIs de logística
        service = AprobacionesFletesService(username="", password="")
        resultado = service.get_rutas_para_ocs(request.oc_names, incluir_metadata=True)
        
        response = {
            'success': True,
            'total_solicitadas': len(request.oc_names),
            'total_encontradas': len(resultado['rutas']),
            'data': resultado['rutas']
        }
        
        if request.incluir_metadata:
            response['sin_rt'] = resultado['sin_rt']
            response['sin_ruta'] = resultado['sin_ruta']
        
        return response
    
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

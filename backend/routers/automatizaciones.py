"""
Router de API para automatizaciones de túneles estáticos.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from shared.odoo_client import get_odoo_client, OdooClient
# Importar desde módulo modularizado
from backend.services.tuneles_service import TunelesService, get_tuneles_service


router = APIRouter(prefix="/api/v1/automatizaciones", tags=["automatizaciones"])


# ============ Modelos Pydantic ============

class PalletInput(BaseModel):
    """Modelo para input de pallet."""
    codigo: str = Field(..., description="Código del pallet (ej: PAC0002683)")
    kg: Optional[float] = Field(None, description="Kg manual si el pallet no tiene stock")
    # Campos para pallets en recepción pendiente
    pendiente_recepcion: Optional[bool] = Field(False, description="Si viene de recepción pendiente")
    producto_id: Optional[int] = Field(None, description="ID del producto en Odoo")
    picking_id: Optional[int] = Field(None, description="ID del picking/recepción")
    lot_id: Optional[int] = Field(None, description="ID del lote")
    # Campo para pallets manuales
    manual: Optional[bool] = Field(False, description="Si fue ingresado manualmente")


class ValidarPalletsRequest(BaseModel):
    """Request para validar lista de pallets."""
    pallets: List[str] = Field(..., description="Lista de códigos de pallets")
    buscar_ubicacion: bool = Field(False, description="Buscar ubicación real del pallet")


class CrearOrdenRequest(BaseModel):
    """Request para crear orden de fabricación."""
    tunel: str = Field(..., description="Código del túnel (TE1, TE2, TE3, VLK)")
    pallets: List[PalletInput] = Field(..., description="Lista de pallets con cantidades")
    buscar_ubicacion_auto: bool = Field(False, description="Buscar ubicación automáticamente")
    responsable_id: Optional[int] = Field(None, description="ID del usuario responsable")


class ReceptionInfo(BaseModel):
    """Información de recepción pendiente."""
    found_in_reception: bool = True
    picking_name: str
    picking_id: int
    state: str
    odoo_url: str
    product_name: Optional[str] = None
    kg: Optional[float] = None
    product_id: Optional[int] = None
    lot_id: Optional[int] = None
    lot_name: Optional[str] = None


class PalletValidado(BaseModel):
    """Respuesta de validación de pallet."""
    codigo: str
    existe: bool
    kg: Optional[float] = None
    ubicacion_nombre: Optional[str] = None
    producto_id: Optional[int] = None
    producto_nombre: Optional[str] = None
    advertencia: Optional[str] = None
    error: Optional[str] = None
    reception_info: Optional[ReceptionInfo] = None
    product_id: Optional[int] = None  # Cuando viene de recepción



class TunelInfo(BaseModel):
    """Información de un túnel."""
    codigo: str
    nombre: str
    sucursal: str


class OrdenInfo(BaseModel):
    """Información de una orden de fabricación."""
    id: int
    nombre: str
    tunel: Optional[str]
    producto: str
    kg_total: float
    estado: str
    fecha_creacion: Optional[str]
    fecha_planificada: Optional[str]
    tiene_pendientes: bool = False
    componentes_count: int = 0
    subproductos_count: int = 0
    electricidad_costo: float = 0


class CrearOrdenResponse(BaseModel):
    """Respuesta de creación de orden."""
    success: bool
    mo_id: Optional[int] = None
    mo_name: Optional[str] = None
    total_kg: Optional[float] = None
    pallets_count: Optional[int] = None
    componentes_count: Optional[int] = None
    subproductos_count: Optional[int] = None
    mensaje: Optional[str] = None
    errores: Optional[List[str]] = None
    advertencias: Optional[List[str]] = None
    error: Optional[str] = None


# ============ Endpoints ============

@router.get("/tuneles-estaticos/procesos", response_model=List[TunelInfo])
async def listar_procesos(
    odoo: OdooClient = Depends(get_odoo_client),
):
    """
    Lista los procesos de túneles estáticos disponibles.
    """
    try:
        service = get_tuneles_service(odoo)
        tuneles = service.get_tuneles_disponibles()
        return tuneles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tuneles-estaticos/validar-pallets", response_model=List[PalletValidado])
async def validar_pallets(
    request: ValidarPalletsRequest,
    odoo: OdooClient = Depends(get_odoo_client),
):
    """
    Valida una lista de pallets y obtiene su información (OPTIMIZADO - batch).
    """
    try:
        service = get_tuneles_service(odoo)
        
        # ✅ OPTIMIZADO: Una sola llamada al servicio (2 llamadas a Odoo internamente)
        resultados = service.validar_pallets_batch(request.pallets, request.buscar_ubicacion)
        
        return resultados
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tuneles-estaticos/duplicados", response_model=List[str])
async def check_duplicados(
    request: ValidarPalletsRequest,
    odoo: OdooClient = Depends(get_odoo_client),
):
    """
    Verifica si los pallets ya están asignados a otra orden activa.
    Retorna lista de advertencias (ej: "PACK001: Ya está en orden MO/123 (activa)")
    """
    try:
        service = get_tuneles_service(odoo)
        duplicados = service.check_pallets_duplicados(request.pallets)
        return duplicados
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tuneles-estaticos/crear", response_model=CrearOrdenResponse)
async def crear_orden(
    request: CrearOrdenRequest,
    odoo: OdooClient = Depends(get_odoo_client),
):
    """
    Crea una orden de fabricación para túnel estático.
    """
    try:
        service = get_tuneles_service(odoo)
        
        # Convertir PalletInput a dict con todos los campos
        pallets = [
            {
                'codigo': p.codigo, 
                'kg': p.kg,
                'pendiente_recepcion': p.pendiente_recepcion,
                'producto_id': p.producto_id,
                'picking_id': p.picking_id,
                'lot_id': p.lot_id,
                'manual': p.manual
            }
            for p in request.pallets
        ]
        
        resultado = service.crear_orden_fabricacion(
            tunel=request.tunel,
            pallets=pallets,
            buscar_ubicacion_auto=request.buscar_ubicacion_auto,
            responsable_id=request.responsable_id
        )
        
        if not resultado.get('success'):
            raise HTTPException(
                status_code=400,
                detail=resultado.get('error') or resultado.get('errores')
            )
        
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tuneles-estaticos/ordenes", response_model=List[OrdenInfo])
async def listar_ordenes(
    tunel: Optional[str] = None,
    estado: Optional[str] = None,
    limit: int = 50,
    solo_pendientes: bool = False,
    odoo: OdooClient = Depends(get_odoo_client),
):
    """
    Lista las órdenes de fabricación recientes de túneles estáticos.
    
    Args:
        tunel: Filtrar por túnel (TE1, TE2, TE3, VLK)
        estado: Filtrar por estado (draft, confirmed, progress, done, cancel)
        limit: Límite de resultados (default: 50)
        solo_pendientes: Filtrar por órdenes con stock pendiente
    """
    try:
        service = get_tuneles_service(odoo)
        ordenes = service.listar_ordenes_recientes(tunel, estado, limit, solo_pendientes)
        return ordenes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tuneles-estaticos/ordenes/{orden_id}")
async def obtener_orden_detalle(
    orden_id: int,
    odoo: OdooClient = Depends(get_odoo_client),
):
    """
    Obtiene el detalle completo de una orden de fabricación.
    """
    try:
        # Leer orden completa
        ordenes = odoo.read('mrp.production', [orden_id], [
            'name', 'product_id', 'product_qty', 'state',
            'create_date', 'date_planned_start', 'date_planned_finished',
            'move_raw_ids', 'move_finished_ids',
            'location_src_id', 'location_dest_id',
            'user_id', 'company_id'
        ])
        
        if not ordenes:
            raise HTTPException(status_code=404, detail=f"Orden {orden_id} no encontrada")
        
        orden = ordenes[0]
        
        # Leer componentes
        componentes = []
        if orden['move_raw_ids']:
            moves = odoo.read('stock.move', orden['move_raw_ids'], [
                'product_id', 'product_uom_qty', 'state', 'move_line_ids'
            ])
            for move in moves:
                componentes.append({
                    'producto': move['product_id'][1] if move['product_id'] else 'N/A',
                    'cantidad': move['product_uom_qty'],
                    'estado': move['state'],
                    'lineas_count': len(move.get('move_line_ids', []))
                })
        
        # Leer subproductos
        subproductos = []
        if orden['move_finished_ids']:
            moves = odoo.read('stock.move', orden['move_finished_ids'], [
                'product_id', 'product_uom_qty', 'state', 'move_line_ids'
            ])
            for move in moves:
                subproductos.append({
                    'producto': move['product_id'][1] if move['product_id'] else 'N/A',
                    'cantidad': move['product_uom_qty'],
                    'estado': move['state'],
                    'lineas_count': len(move.get('move_line_ids', []))
                })
        
        return {
            'id': orden['id'],
            'nombre': orden['name'],
            'producto': orden['product_id'][1] if orden['product_id'] else 'N/A',
            'cantidad': orden['product_qty'],
            'estado': orden['state'],
            'fecha_creacion': orden.get('create_date'),
            'fecha_inicio_planificada': orden.get('date_planned_start'),
            'fecha_fin_planificada': orden.get('date_planned_finished'),
            'ubicacion_origen': orden['location_src_id'][1] if orden.get('location_src_id') else 'N/A',
            'ubicacion_destino': orden['location_dest_id'][1] if orden.get('location_dest_id') else 'N/A',
            'responsable': orden['user_id'][1] if orden.get('user_id') else 'N/A',
            'compania': orden['company_id'][1] if orden.get('company_id') else 'N/A',
            'componentes': componentes,
            'subproductos': subproductos
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tuneles-estaticos/ordenes/{orden_id}/pendientes")
async def obtener_detalle_pendientes(
    orden_id: int,
    username: str,
    password: str,
):
    """
    Obtiene el detalle de los pallets pendientes de una MO,
    verificando cuáles ya tienen stock disponible.
    
    Returns:
        Dict con: mo_name, pallets (con estado cada uno), resumen
    """
    try:
        odoo = get_odoo_client(username=username, password=password)
        service = get_tuneles_service(odoo)
        resultado = service.obtener_detalle_pendientes(orden_id)
        
        if not resultado.get('success'):
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tuneles-estaticos/ordenes/{orden_id}/agregar-disponibles")
async def agregar_componentes_disponibles(
    orden_id: int,
    username: str,
    password: str,
):
    """
    Agrega como componentes los pallets que ahora están disponibles.
    
    Returns:
        Dict con: success, agregados (cantidad), pendientes_restantes
    """
    try:
        odoo = get_odoo_client(username=username, password=password)
        service = get_tuneles_service(odoo)
        resultado = service.agregar_componentes_disponibles(orden_id)
        
        if not resultado.get('success'):
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tuneles-estaticos/ordenes/{orden_id}/reset-pendientes")
async def reset_pendientes(
    orden_id: int,
    username: str,
    password: str,
):
    """
    SOLO PARA DEBUG: Resetea el estado de los pallets pendientes,
    eliminando todos los timestamps de agregado para forzar re-validación.
    
    Returns:
        Dict con: success, mensaje
    """
    try:
        odoo = get_odoo_client(username=username, password=password)
        service = get_tuneles_service(odoo)
        resultado = service.reset_estado_pendientes(orden_id)
        
        if not resultado.get('success'):
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tuneles-estaticos/ordenes/{orden_id}/completar-pendientes")
async def completar_pendientes(
    orden_id: int,
    username: str,
    password: str,
):
    """
    Completa los pendientes de una MO cuando todas las recepciones están validadas.
    Quita el flag x_studio_pending_receptions.
    
    Returns:
        Dict con: success, mensaje
    """
    try:
        odoo = get_odoo_client(username=username, password=password)
        service = get_tuneles_service(odoo)
        resultado = service.completar_pendientes(orden_id)
        
        if not resultado.get('success'):
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tuneles-estaticos/ubicacion-by-barcode")
async def get_ubicacion_by_barcode(
    barcode: str,
    username: str = None,
    password: str = None,
    url: str = None,
    db: str = None
):
    """
    Busca una ubicación (cámara) por su código de barras.
    """
    try:
        # Crear cliente Odoo (usará .env si username/password no se proporcionan)
        odoo = get_odoo_client(username=username, password=password, url=url, db=db)
        
        locations = odoo.search_read(
            "stock.location",
            [("barcode", "=", barcode), ("usage", "=", "internal")],
            ["id", "name", "display_name", "barcode"]
        )
        
        if not locations:
            return {
                "found": False,
                "message": f"No se encontró ubicación con código: {barcode}"
            }
        
        loc = locations[0]
        return {
            "found": True,
            "id": loc["id"],
            "name": loc["name"],
            "display_name": loc.get("display_name", loc["name"]),
            "barcode": loc.get("barcode", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

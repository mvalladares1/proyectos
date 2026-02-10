"""
Router de API para automatizaciones de túneles estáticos.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from shared.odoo_client import get_odoo_client, OdooClient
# Importar desde módulo modularizado
from backend.services.tuneles_service import TunelesService, get_tuneles_service
from backend.services.revertir_consumo_service import RevertirConsumoService


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
            error_msg = resultado.get('error') or resultado.get('errores') or 'Error desconocido'
            print(f"[TUNELES] Error en crear_orden: {error_msg}", flush=True)
            print(f"[TUNELES] Resultado completo: {resultado}", flush=True)
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        print(f"[TUNELES] Orden creada exitosamente: {resultado.get('mo_name')}", flush=True)
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[TUNELES] Excepcion en crear_orden: {e}", flush=True)
        print(f"[TUNELES] Traceback: {traceback.format_exc()}", flush=True)
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


# ============ Revertir Consumo ODF ============

class RevertirConsumoRequest(BaseModel):
    """Request para revertir consumo de ODF."""
    odf_name: str = Field(..., description="Nombre de la orden de fabricación (ej: VLK/CongTE109)")


@router.post("/revertir-consumo-odf")
async def revertir_consumo_odf(
    request: RevertirConsumoRequest,
    username: str = None,
    password: str = None,
    url: str = None,
    db: str = None
):
    """
    Revierte el consumo de una orden de fabricación de desmontaje.
    
    - Recupera componentes (MP) a sus paquetes originales
    - Elimina subproductos (pone cantidades en 0)
    """
    try:
        service = RevertirConsumoService(
            username=username, 
            password=password,
            url=url,
            db=db
        )
        
        resultado = service.revertir_consumo_odf(request.odf_name)
        return resultado
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/revertir-consumo-odf/preview")
async def preview_reversion_odf(
    request: RevertirConsumoRequest,
    username: str = None,
    password: str = None,
    url: str = None,
    db: str = None
):
    """
    Analiza lo que se haría al revertir una ODF SIN ejecutar cambios.
    Retorna un preview detallado para confirmación del usuario.
    """
    try:
        service = RevertirConsumoService(
            username=username, 
            password=password,
            url=url,
            db=db
        )
        
        resultado = service.preview_reversion_odf(request.odf_name)
        return resultado
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ AUTOMATIZACIÓN PROCESOS ============
# Endpoints para agregar pallets a órdenes existentes como componentes/subproductos

class ProcesosValidarPalletsRequest(BaseModel):
    """Request para validar pallets para agregar a orden."""
    pallets: List[str] = Field(..., description="Lista de códigos de pallets")
    tipo: str = Field(..., description="componentes o subproductos")
    orden_id: int = Field(..., description="ID de la orden de fabricación")


class ProcesosAgregarPalletsRequest(BaseModel):
    """Request para agregar pallets a orden."""
    orden_id: int = Field(..., description="ID de la orden de fabricación o picking")
    tipo: str = Field(..., description="componentes o subproductos")
    pallets: List[dict] = Field(..., description="Lista de pallets con info")
    modelo: str = Field('mrp.production', description="Modelo: mrp.production o stock.picking")


@router.get("/procesos/buscar-orden")
async def buscar_orden_procesos(
    orden: str,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
):
    """
    Busca una orden de fabricación o transferencia por nombre o número.
    
    Args:
        orden: Nombre completo (MO/RF/00123, WH/Transf/00936) o solo número (00123)
    """
    try:
        odoo = get_odoo_client(username=username, password=password)
        # Construir dominio de búsqueda
        domain = []
        
        if orden.isdigit():
            domain = [('name', 'ilike', orden)]
        elif '/' in orden:
            # Usar ilike para ignorar mayúsculas/minúsculas
            domain = [('name', 'ilike', orden)]
        else:
            domain = [('name', 'ilike', orden)]
        
        # Primero buscar en mrp.production
        ordenes = odoo.search_read(
            'mrp.production',
            domain,
            ['name', 'product_id', 'product_qty', 'state', 
             'move_raw_ids', 'move_finished_ids', 'create_date'],
            limit=1,
            order='create_date desc'
        )
        
        if ordenes:
            mo = ordenes[0]
            return {
                'success': True,
                'orden': {
                    'id': mo['id'],
                    'nombre': mo['name'],
                    'producto': mo['product_id'][1] if mo['product_id'] else 'N/A',
                    'producto_id': mo['product_id'][0] if mo['product_id'] else None,
                    'cantidad': mo['product_qty'],
                    'estado': mo['state'],
                    'componentes_count': len(mo.get('move_raw_ids', [])),
                    'subproductos_count': len(mo.get('move_finished_ids', [])),
                    'modelo': 'mrp.production',
                }
            }
        
        # Si no se encontró en mrp.production, buscar en stock.picking
        pickings = odoo.search_read(
            'stock.picking',
            domain,
            ['name', 'state', 'location_id', 'location_dest_id',
             'move_ids', 'picking_type_id', 'create_date'],
            limit=1,
            order='create_date desc'
        )
        
        if pickings:
            pk = pickings[0]
            return {
                'success': True,
                'orden': {
                    'id': pk['id'],
                    'nombre': pk['name'],
                    'producto': pk['picking_type_id'][1] if pk['picking_type_id'] else 'Transferencia',
                    'producto_id': None,
                    'cantidad': len(pk.get('move_ids', [])),
                    'estado': pk['state'],
                    'componentes_count': len(pk.get('move_ids', [])),
                    'subproductos_count': 0,
                    'modelo': 'stock.picking',
                }
            }
        
        return {'success': False, 'error': f'Orden "{orden}" no encontrada en fabricación ni transferencias'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/procesos/validar-pallets")
async def validar_pallets_procesos(
    request: ProcesosValidarPalletsRequest,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
):
    """
    Valida pallets para agregar a una orden existente.
    Extrae lote, kg, producto y ubicación de cada pallet.
    """
    try:
        odoo = get_odoo_client(username=username, password=password)
        resultados = []
        
        for codigo in request.pallets:
            # Normalizar código
            codigo_normalizado = codigo.strip().upper()
            if codigo_normalizado.startswith('PAC') and not codigo_normalizado.startswith('PACK'):
                codigo_normalizado = 'PACK' + codigo_normalizado[3:]
            
            # Buscar package
            packages = odoo.search_read(
                'stock.quant.package',
                [('name', '=', codigo_normalizado)],
                ['id', 'name'],
                limit=1
            )
            
            if not packages:
                resultados.append({
                    'codigo': codigo_normalizado,
                    'valido': False,
                    'error': 'Package no encontrado'
                })
                continue
            
            package_id = packages[0]['id']
            
            # Buscar quant con stock
            quants = odoo.search_read(
                'stock.quant',
                [
                    ('package_id', '=', package_id),
                    ('quantity', '>', 0)
                ],
                ['product_id', 'quantity', 'lot_id', 'location_id'],
                limit=1
            )
            
            if not quants:
                # Intentar buscar sin filtro de cantidad (puede estar reservado)
                quants = odoo.search_read(
                    'stock.quant',
                    [('package_id', '=', package_id)],
                    ['product_id', 'quantity', 'lot_id', 'location_id'],
                    limit=1
                )
            
            if not quants:
                resultados.append({
                    'codigo': codigo_normalizado,
                    'valido': False,
                    'error': 'Sin stock en este package'
                })
                continue
            
            quant = quants[0]
            
            resultados.append({
                'codigo': codigo_normalizado,
                'valido': True,
                'kg': quant['quantity'],
                'producto_id': quant['product_id'][0] if quant['product_id'] else None,
                'producto_nombre': quant['product_id'][1] if quant['product_id'] else 'N/A',
                'lote_id': quant['lot_id'][0] if quant['lot_id'] else None,
                'lote_nombre': quant['lot_id'][1] if quant['lot_id'] else codigo_normalizado,
                'ubicacion_id': quant['location_id'][0] if quant['location_id'] else None,
                'package_id': package_id,
            })
        
        return {'pallets': resultados}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/procesos/agregar-pallets")
async def agregar_pallets_procesos(
    request: ProcesosAgregarPalletsRequest,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
):
    """
    Agrega pallets a una orden existente como componentes o subproductos.
    
    Para COMPONENTES (move_raw_ids): crea stock.move + stock.move.line
    Para SUBPRODUCTOS (move_finished_ids): crea stock.move + stock.move.line con lote-C
    """
    try:
        from backend.services.tuneles.constants import (
            UBICACION_VIRTUAL_CONGELADO_ID,
            UBICACION_VIRTUAL_PROCESOS_ID,
        )
        
        odoo = get_odoo_client(username=username, password=password)
        
        es_picking = request.modelo == 'stock.picking'
        
        if es_picking:
            # === STOCK.PICKING (Transferencias) ===
            ordenes = odoo.read('stock.picking', [request.orden_id], [
                'name', 'state', 'location_id', 'location_dest_id'
            ])
            if not ordenes:
                return {'success': False, 'error': f'Transferencia {request.orden_id} no encontrada'}
            orden = ordenes[0]
            mo_name = orden['name']
        else:
            # === MRP.PRODUCTION (Órdenes de Fabricación) ===
            ordenes = odoo.read('mrp.production', [request.orden_id], [
                'name', 'product_id', 'state', 'location_src_id', 'location_dest_id'
            ])
            if not ordenes:
                return {'success': False, 'error': f'Orden {request.orden_id} no encontrada'}
            orden = ordenes[0]
            mo_name = orden['name']
        
        # Determinar ubicación virtual según sucursal
        if 'RF' in mo_name:
            ubicacion_virtual = UBICACION_VIRTUAL_CONGELADO_ID
        else:
            ubicacion_virtual = UBICACION_VIRTUAL_PROCESOS_ID
        
        pallets_agregados = 0
        kg_total = 0
        errores = []
        
        for pallet in request.pallets:
            try:
                codigo = pallet['codigo']
                kg = pallet.get('kg', 0)
                producto_id = pallet.get('producto_id')
                lote_id = pallet.get('lote_id')
                lote_nombre = pallet.get('lote_nombre', codigo)
                ubicacion_id = pallet.get('ubicacion_id')
                package_id = pallet.get('package_id')
                
                if not producto_id:
                    errores.append(f"{codigo}: Sin producto_id")
                    continue
                
                if es_picking:
                    # === STOCK.PICKING (Transferencias) ===
                    
                    # Buscar o crear lote si no existe
                    if not lote_id and lote_nombre:
                        lotes_existentes = odoo.search(
                            'stock.lot',
                            [('name', '=', lote_nombre), ('product_id', '=', producto_id)]
                        )
                        if lotes_existentes:
                            lote_id = lotes_existentes[0]
                        else:
                            lote_id = odoo.execute('stock.lot', 'create', {
                                'name': lote_nombre,
                                'product_id': producto_id,
                                'company_id': 1
                            })
                    
                    # Buscar o crear package si no existe
                    if not package_id and codigo:
                        pkgs_existentes = odoo.search(
                            'stock.quant.package',
                            [('name', '=', codigo)]
                        )
                        if pkgs_existentes:
                            package_id = pkgs_existentes[0]
                        else:
                            package_id = odoo.execute('stock.quant.package', 'create', {
                                'name': codigo,
                                'company_id': 1
                            })
                    
                    # Buscar move existente para el producto en el picking
                    existing_moves = odoo.search_read(
                        'stock.move',
                        [
                            ('picking_id', '=', request.orden_id),
                            ('product_id', '=', producto_id),
                            ('state', '!=', 'cancel')
                        ],
                        ['id'],
                        limit=1
                    )
                    
                    if existing_moves:
                        move_id = existing_moves[0]['id']
                    else:
                        move_data = {
                            'name': mo_name,
                            'product_id': producto_id,
                            'product_uom_qty': kg,
                            'product_uom': 12,
                            'location_id': orden['location_id'][0],
                            'location_dest_id': orden['location_dest_id'][0],
                            'state': 'draft',
                            'picking_id': request.orden_id,
                            'company_id': 1,
                            'reference': mo_name
                        }
                        move_id = odoo.execute('stock.move', 'create', move_data)
                    
                    # Crear stock.move.line
                    move_line_data = {
                        'move_id': move_id,
                        'product_id': producto_id,
                        'qty_done': kg,
                        'reserved_uom_qty': kg,
                        'product_uom_id': 12,
                        'location_id': orden['location_id'][0],
                        'location_dest_id': orden['location_dest_id'][0],
                        'state': 'draft',
                        'reference': mo_name,
                        'company_id': 1
                    }
                    
                    if lote_id:
                        move_line_data['lot_id'] = lote_id
                    if package_id:
                        move_line_data['package_id'] = package_id
                    
                    odoo.execute('stock.move.line', 'create', move_line_data)
                
                elif request.tipo == 'componentes':
                    # === COMPONENTES (move_raw_ids) ===
                    
                    # Buscar o crear lote si no existe
                    if not lote_id and lote_nombre:
                        lotes_existentes = odoo.search(
                            'stock.lot',
                            [('name', '=', lote_nombre), ('product_id', '=', producto_id)]
                        )
                        if lotes_existentes:
                            lote_id = lotes_existentes[0]
                        else:
                            lote_id = odoo.execute('stock.lot', 'create', {
                                'name': lote_nombre,
                                'product_id': producto_id,
                                'company_id': 1
                            })
                    
                    # Buscar o crear package si no existe
                    if not package_id and codigo:
                        pkgs_existentes = odoo.search(
                            'stock.quant.package',
                            [('name', '=', codigo)]
                        )
                        if pkgs_existentes:
                            package_id = pkgs_existentes[0]
                        else:
                            package_id = odoo.execute('stock.quant.package', 'create', {
                                'name': codigo,
                                'company_id': 1
                            })
                    
                    # Buscar move existente para el producto (para reutilizar)
                    existing_moves = odoo.search_read(
                        'stock.move',
                        [
                            ('raw_material_production_id', '=', request.orden_id),
                            ('product_id', '=', producto_id),
                            ('state', '!=', 'cancel')
                        ],
                        ['id'],
                        limit=1
                    )
                    
                    if existing_moves:
                        move_id = existing_moves[0]['id']
                    else:
                        # Crear nuevo stock.move
                        move_data = {
                            'name': mo_name,
                            'product_id': producto_id,
                            'product_uom_qty': kg,
                            'product_uom': 12,  # kg
                            'location_id': ubicacion_id or orden['location_src_id'][0],
                            'location_dest_id': ubicacion_virtual,
                            'state': 'draft',
                            'raw_material_production_id': request.orden_id,
                            'company_id': 1,
                            'reference': mo_name
                        }
                        move_id = odoo.execute('stock.move', 'create', move_data)
                    
                    # Crear stock.move.line
                    move_line_data = {
                        'move_id': move_id,
                        'product_id': producto_id,
                        'qty_done': kg,
                        'reserved_uom_qty': kg,
                        'product_uom_id': 12,
                        'location_id': ubicacion_id or orden['location_src_id'][0],
                        'location_dest_id': ubicacion_virtual,
                        'state': 'draft',
                        'reference': mo_name,
                        'company_id': 1
                    }
                    
                    if lote_id:
                        move_line_data['lot_id'] = lote_id
                    if package_id:
                        move_line_data['package_id'] = package_id
                    
                    odoo.execute('stock.move.line', 'create', move_line_data)
                    
                else:
                    # === SUBPRODUCTOS (move_finished_ids) ===
                    # Buscar producto congelado (1xxxxxx -> 2xxxxxx)
                    producto_output_id = producto_id
                    
                    try:
                        prod_info = odoo.search_read(
                            'product.product',
                            [('id', '=', producto_id)],
                            ['default_code'],
                            limit=1
                        )
                        if prod_info and prod_info[0].get('default_code'):
                            codigo_prod = prod_info[0]['default_code']
                            if codigo_prod and len(codigo_prod) >= 1 and codigo_prod[0] == '1':
                                codigo_congelado = '2' + codigo_prod[1:]
                                prod_congelado = odoo.search_read(
                                    'product.product',
                                    [('default_code', '=', codigo_congelado)],
                                    ['id'],
                                    limit=1
                                )
                                if prod_congelado:
                                    producto_output_id = prod_congelado[0]['id']
                    except Exception as e:
                        print(f"Error buscando producto congelado: {e}")
                    
                    # Generar lote con sufijo -C
                    lote_output_name = f"{lote_nombre}-C"
                    
                    # Buscar o crear lote
                    lotes_existentes = odoo.search(
                        'stock.lot',
                        [('name', '=', lote_output_name), ('product_id', '=', producto_output_id)]
                    )
                    
                    if lotes_existentes:
                        lote_output_id = lotes_existentes[0]
                    else:
                        lote_output_id = odoo.execute('stock.lot', 'create', {
                            'name': lote_output_name,
                            'product_id': producto_output_id,
                            'company_id': 1
                        })
                    
                    # Generar package con sufijo -C
                    if codigo.startswith('PACK'):
                        numero = codigo[4:]
                    elif codigo.startswith('PAC'):
                        numero = codigo[3:]
                    else:
                        numero = codigo
                    package_output_name = f"PACK{numero}-C"
                    
                    # Buscar o crear package
                    pkgs_existentes = odoo.search(
                        'stock.quant.package',
                        [('name', '=', package_output_name)]
                    )
                    
                    if pkgs_existentes:
                        package_output_id = pkgs_existentes[0]
                    else:
                        package_output_id = odoo.execute('stock.quant.package', 'create', {
                            'name': package_output_name,
                            'company_id': 1
                        })
                    
                    # Buscar move existente para el producto output
                    existing_moves = odoo.search_read(
                        'stock.move',
                        [
                            ('production_id', '=', request.orden_id),
                            ('product_id', '=', producto_output_id),
                            ('state', '!=', 'cancel')
                        ],
                        ['id'],
                        limit=1
                    )
                    
                    if existing_moves:
                        move_id = existing_moves[0]['id']
                    else:
                        # Crear stock.move para subproducto
                        move_data = {
                            'name': mo_name,
                            'product_id': producto_output_id,
                            'product_uom_qty': kg,
                            'product_uom': 12,
                            'location_id': ubicacion_virtual,
                            'location_dest_id': orden['location_dest_id'][0],
                            'state': 'draft',
                            'production_id': request.orden_id,
                            'company_id': 1,
                            'reference': mo_name
                        }
                        move_id = odoo.execute('stock.move', 'create', move_data)
                    
                    # Crear stock.move.line con result_package_id
                    move_line_data = {
                        'move_id': move_id,
                        'product_id': producto_output_id,
                        'qty_done': kg,
                        'reserved_uom_qty': kg,
                        'product_uom_id': 12,
                        'location_id': ubicacion_virtual,
                        'location_dest_id': orden['location_dest_id'][0],
                        'state': 'draft',
                        'reference': mo_name,
                        'company_id': 1,
                        'lot_id': lote_output_id,
                        'result_package_id': package_output_id
                    }
                    
                    odoo.execute('stock.move.line', 'create', move_line_data)
                
                pallets_agregados += 1
                kg_total += kg
                
            except Exception as e:
                errores.append(f"{pallet.get('codigo', 'N/A')}: {str(e)}")
                print(f"Error agregando pallet {pallet}: {e}")
        
        return {
            'success': pallets_agregados > 0,
            'mensaje': f"{pallets_agregados} pallets agregados a {request.tipo}",
            'pallets_agregados': pallets_agregados,
            'kg_total': kg_total,
            'errores': errores if errores else None
        }
    
    except Exception as e:
        import traceback
        print(f"Error en agregar_pallets_procesos: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

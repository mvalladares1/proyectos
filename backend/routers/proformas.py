"""
Router para Gestión de Proformas (USD → CLP y CLP directas)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from backend.services.proforma_ajuste_service import (
    get_facturas_borrador,
    get_proveedores_con_borradores,
    get_detalle_factura,
    cambiar_moneda_factura,
    eliminar_linea_factura
)

router = APIRouter(prefix="/api/v1/proformas", tags=["proformas"])


@router.get("/proveedores")
async def obtener_proveedores(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="Contraseña Odoo")
):
    """
    Obtiene lista de proveedores que tienen facturas en borrador en USD.
    """
    try:
        proveedores = get_proveedores_con_borradores(username, password)
        return proveedores
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/borradores")
async def obtener_facturas_borrador(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="Contraseña Odoo"),
    proveedor_id: Optional[int] = Query(None, description="ID del proveedor"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    solo_usd: bool = Query(False, description="Si True, solo retorna facturas en USD"),
    moneda_filtro: Optional[str] = Query(None, description="Filtrar por moneda: USD, CLP, o None para todas")
):
    """
    Obtiene facturas de proveedor en borrador con valores USD y CLP.
    """
    try:
        facturas = get_facturas_borrador(
            username, password,
            proveedor_id=proveedor_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            solo_usd=solo_usd,
            moneda_filtro=moneda_filtro
        )
        return facturas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detalle/{factura_id}")
async def obtener_detalle_factura(
    factura_id: int,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="Contraseña Odoo")
):
    """
    Obtiene detalle completo de una factura específica.
    """
    try:
        detalle = get_detalle_factura(username, password, factura_id)
        return detalle
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cambiar_moneda/{factura_id}")
async def ejecutar_cambio_moneda(
    factura_id: int,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="Contraseña Odoo"),
    moneda_destino: str = Query("CLP", description="Moneda destino")
):
    """
    Cambia la moneda de una factura en borrador (USD → CLP o viceversa).
    
    ⚠️ OPERACIÓN DE ESCRITURA - Modifica la factura en Odoo.
    """
    try:
        resultado = cambiar_moneda_factura(
            username, password, 
            factura_id, 
            moneda_destino
        )
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/linea/{linea_id}")
async def eliminar_linea(
    linea_id: int,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="Contraseña Odoo")
):
    """
    Elimina una línea de factura en Odoo.
    
    ⚠️ OPERACIÓN DE ESCRITURA - Elimina permanentemente la línea.
    """
    try:
        resultado = eliminar_linea_factura(username, password, linea_id)
        if not resultado.get("success"):
            raise HTTPException(status_code=400, detail=resultado.get("error"))
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


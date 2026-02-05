"""
Router para Ajuste de Proformas USD → CLP
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from backend.services.proforma_ajuste_service import (
    get_facturas_borrador,
    get_proveedores_con_borradores,
    get_detalle_factura,
    cambiar_moneda_factura
)

router = APIRouter(prefix="/proformas", tags=["proformas"])


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
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)")
):
    """
    Obtiene facturas de proveedor en borrador con valores USD y CLP.
    """
    try:
        facturas = get_facturas_borrador(
            username, password,
            proveedor_id=proveedor_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
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

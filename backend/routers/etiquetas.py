"""
Router para gestión de etiquetas de pallets
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from typing import List, Dict, Optional

router = APIRouter(prefix="/etiquetas", tags=["Etiquetas Pallet"])


@router.get("/buscar_ordenes")
async def buscar_ordenes(
    termino: str = Query(..., description="Término de búsqueda"),
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Busca órdenes de producción por nombre o referencia.
    """
    try:
        from backend.services.etiquetas_pallet_service import EtiquetasPalletService
        service = EtiquetasPalletService(username=username, password=password)
        return service.buscar_ordenes(termino)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pallets_orden")
async def obtener_pallets_orden(
    orden_name: str = Query(..., description="Nombre de la orden"),
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene todos los pallets de una orden de producción.
    """
    try:
        from backend.services.etiquetas_pallet_service import EtiquetasPalletService
        service = EtiquetasPalletService(username=username, password=password)
        return service.obtener_pallets_orden(orden_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info_etiqueta/{package_id}")
async def obtener_info_etiqueta(
    package_id: int,
    cliente: str = Query("", description="Nombre del cliente"),
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene la información completa para generar una etiqueta de pallet.
    """
    try:
        from backend.services.etiquetas_pallet_service import EtiquetasPalletService
        service = EtiquetasPalletService(username=username, password=password)
        info = service.obtener_info_etiqueta(package_id, cliente)
        
        if not info:
            raise HTTPException(status_code=404, detail="No se encontró información del pallet")
        
        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generar_etiqueta_pdf")
async def generar_etiqueta_pdf(datos: Dict):
    """
    Genera un PDF de etiqueta a partir de los datos proporcionados.
    """
    try:
        from backend.utils.generador_etiquetas import GeneradorEtiquetasPDF
        
        generador = GeneradorEtiquetasPDF()
        pdf_bytes = generador.generar_etiqueta(datos)
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=etiqueta_{datos.get('numero_pallet', 'pallet')}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generar_etiquetas_multiples_pdf")
async def generar_etiquetas_multiples_pdf(lista_datos: List[Dict]):
    """
    Genera un PDF con múltiples etiquetas.
    """
    try:
        from backend.utils.generador_etiquetas import GeneradorEtiquetasPDF
        
        generador = GeneradorEtiquetasPDF()
        pdf_bytes = generador.generar_etiquetas_multiples(lista_datos)
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=etiquetas_pallets.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

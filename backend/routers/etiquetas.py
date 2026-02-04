"""
Router para gestión de etiquetas de pallets
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from typing import List, Dict, Optional

router = APIRouter(prefix="/api/v1/etiquetas", tags=["Etiquetas Pallet"])


@router.get("/clientes")
async def obtener_clientes(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Obtiene la lista de clientes desde res.partner.
    """
    try:
        from backend.services.etiquetas_pallet_service import EtiquetasPalletService
        service = EtiquetasPalletService(username=username, password=password)
        return service.obtener_clientes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/imprimir_zebra")
async def imprimir_zebra(
    zpl: str,
    ip: str = Query(..., description="IP de la impresora Zebra"),
    puerto: int = Query(9100, description="Puerto de la impresora")
):
    """
    Envía código ZPL a una impresora Zebra por TCP/IP.
    """
    import socket
    
    try:
        # Crear socket y conectar
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 segundos timeout
        sock.connect((ip, puerto))
        
        # Enviar ZPL
        sock.sendall(zpl.encode('utf-8'))
        sock.close()
        
        return {"success": True, "message": f"Etiqueta enviada a {ip}:{puerto}"}
    except socket.timeout:
        raise HTTPException(status_code=408, detail=f"Timeout conectando a {ip}:{puerto}")
    except socket.error as e:
        raise HTTPException(status_code=500, detail=f"Error de conexión: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
Router para gestión de etiquetas de pallets
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from typing import List, Dict, Optional
from fastapi import Body

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
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio_proceso: Optional[str] = Query(None, description="Fecha de inicio del proceso actual (ISO 8601)"),
    orden_actual: Optional[str] = Query(None, description="Nombre de la orden actual (para correlativo robusto)")
):
    """
    Obtiene la información completa para generar una etiqueta de pallet.
    """
    try:
        from backend.services.etiquetas_pallet_service import EtiquetasPalletService
        service = EtiquetasPalletService(username=username, password=password)
        info = service.obtener_info_etiqueta(package_id, cliente, fecha_inicio_proceso=fecha_inicio_proceso, orden_actual=orden_actual)
        
        if not info:
            raise HTTPException(status_code=404, detail="No se encontró información del pallet")
        
        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reservar")
async def reservar_cartones(datos: Dict = Body(...)):
    """
    Reserva N cartones para un pallet de forma atómica y devuelve el inicio reservado.
    Body JSON esperado: {username, password, package_id, package_name, qty, orden_actual, usuario}
    """
    try:
        username = datos.get('username')
        password = datos.get('password')
        package_id = int(datos.get('package_id'))
        package_name = datos.get('package_name', '')
        qty = int(datos.get('qty', 0))
        orden_actual = datos.get('orden_actual', '')
        usuario = datos.get('usuario', '')

        from backend.services.etiquetas_pallet_service import EtiquetasPalletService
        service = EtiquetasPalletService(username=username, password=password)
        ensure_block_size = int(datos.get('ensure_block_size') or 0)
        if ensure_block_size > 0:
            # Solo generar bloque de 90 si el producto es IQF A (NUA)
            try:
                info = service.obtener_info_etiqueta(package_id=package_id, cliente='', fecha_inicio_proceso=None, orden_actual=orden_actual)
            except Exception:
                info = None

            nombre_prod = (info.get('nombre_producto') if info else package_name or '').upper()
            if 'IQF A' in nombre_prod or 'LACO' in nombre_prod:
                block_size = ensure_block_size
                lista = []
                for i in range(int(block_size)):
                    item = {
                        'nombre_producto': info.get('nombre_producto') if info else package_name,
                        'codigo_producto': info.get('codigo_producto') if info else '',
                        'peso_pallet_kg': info.get('peso_pallet_kg') if info else 0,
                        'cantidad_cajas': info.get('cantidad_cajas') if info else 0,
                        'fecha_elaboracion': info.get('fecha_elaboracion') if info else '',
                        'fecha_vencimiento': info.get('fecha_vencimiento') if info else '',
                        'lote_produccion': info.get('lote_produccion') if info else '',
                        'numero_pallet': info.get('numero_pallet') if info else package_name,
                    }
                    lista.append(item)
                # Generar PDF con todas las etiquetas y guardarlo
                try:
                    import os
                    from backend.utils.generador_etiquetas import GeneradorEtiquetasPDF
                    generador = GeneradorEtiquetasPDF()
                    pdf_bytes = generador.generar_etiquetas_multiples(lista)
                    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
                    os.makedirs(data_dir, exist_ok=True)
                    out_path = os.path.join(data_dir, f'etiquetas_block_{package_id}.pdf')
                    with open(out_path, 'wb') as f:
                        f.write(pdf_bytes)
                    return {'start_carton': 1, 'qty': int(block_size), 'pdf_path': out_path}
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Error generando etiquetas NUA: {e}")
            # Si no es IQF A, usar la lógica normal
            res = service.reservar_cartones(package_id=package_id, package_name=package_name, qty=qty, orden_actual=orden_actual, usuario=usuario)
            return res
        else:
            res = service.reservar_cartones(package_id=package_id, package_name=package_name, qty=qty, orden_actual=orden_actual, usuario=usuario)
            return res
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

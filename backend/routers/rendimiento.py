"""
Router de Rendimiento Productivo
Incluye trazabilidad inversa y endpoints para el módulo de Producción
Nuevos análisis: Compras, Ventas, Producción, Inventario, Stock Teórico Anual
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List

from backend.services.rendimiento_service import RendimientoService
from backend.services.analisis_compras_service import AnalisisComprasService
from backend.services.analisis_ventas_service import AnalisisVentasService
from backend.services.analisis_produccion_service import AnalisisProduccionService
from backend.services.analisis_inventario_service import AnalisisInventarioService
from backend.services.analisis_stock_teorico_service import AnalisisStockTeoricoService
from shared.odoo_client import OdooClient

router = APIRouter(prefix="/api/v1/rendimiento", tags=["rendimiento"])


@router.get("/trazabilidad-inversa/{lote_pt_name}")
async def get_trazabilidad_inversa(
    lote_pt_name: str,
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Trazabilidad inversa: dado un lote PT, encuentra los lotes MP originales.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_trazabilidad_inversa(lote_pt_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trazabilidad-pallets")
async def get_trazabilidad_pallets(
    pallet_names: List[str],
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo")
):
    """
    Trazabilidad completa de uno o varios pallets.
    Rastrea desde el pallet físico hasta el productor original.
    
    Request body debe ser una lista JSON:
    ```json
    ["PALLET-001", "PALLET-002"]
    ```
    
    Query params:
    - username: Usuario Odoo
    - password: API Key Odoo
    
    Returns:
        - pallets_rastreados: Número de pallets procesados
        - pallets: Lista con trazabilidad completa de cada pallet
    """
    try:
        # DEBUG: Log de entrada
        print(f"🔍 BACKEND DEBUG - Endpoint /trazabilidad-pallets llamado")
        print(f"🔍 BACKEND DEBUG - pallet_names (tipo: {type(pallet_names)}): {pallet_names}")
        print(f"🔍 BACKEND DEBUG - username: {username}")
        
        service = RendimientoService(username=username, password=password)
        result = service.get_trazabilidad_pallets(pallet_names)
        
        print(f"🔍 BACKEND DEBUG - Resultado exitoso: {len(result.get('pallets', []))} pallets")
        return result
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ BACKEND ERROR - Exception: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/dashboard")
async def get_dashboard_completo(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    solo_terminadas: bool = Query(True, description="Solo MOs en estado 'done'")
):
    """
    USADO POR PRODUCCIÓN: Obtiene datos consolidados del dashboard.
    
    Retorna:
    - overview: KPIs consolidados (proceso, congelado, etc.)
    - consolidado: Datos por fruta/manejo
    - salas: Productividad por sala
    - mos: Lista de MOs con rendimiento
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_dashboard_completo(fecha_inicio, fecha_fin, solo_terminadas=solo_terminadas)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inventario-trazabilidad")
async def get_inventario_trazabilidad(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_desde: str = Query(..., description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: str = Query(..., description="Fecha hasta (YYYY-MM-DD)")
):
    """
    Análisis de inventario: compras vs ventas por tipo de fruta y manejo.
    Usado para calcular merma y stock teórico.
    SOLO incluye productos con tipo_fruta Y manejo clasificados.
    """
    try:
        service = RendimientoService(username=username, password=password)
        return service.get_inventario_trazabilidad(fecha_desde, fecha_hasta)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview")
async def get_overview(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)")
):
    """
    LEGACY: KPIs consolidados de rendimiento.
    Usa el endpoint /dashboard para datos más completos.
    """
    try:
        service = RendimientoService(username=username, password=password)
        data = service.get_dashboard_completo(fecha_inicio, fecha_fin)
        return data.get('overview', {}) if data else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ====================================================================
# NUEVOS ENDPOINTS - ANÁLISIS SEPARADOS
# ====================================================================

@router.get("/analisis-compras")
async def get_analisis_compras(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_desde: str = Query(..., description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: str = Query(..., description="Fecha hasta (YYYY-MM-DD)")
):
    """
    Análisis de compras de materia prima (MP/PSP).
    Solo facturas de proveedor con productos clasificados.
    
    Returns:
        - resumen: totales generales
        - por_tipo: desglose por tipo de fruta y manejo
        - top_proveedores: principales proveedores
        - tendencia_precios: evolución mensual de precios
        - detalle: líneas individuales
    """
    try:
        odoo = OdooClient(username=username, password=password)
        service = AnalisisComprasService(odoo=odoo)
        return service.get_analisis_compras(fecha_desde, fecha_hasta)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analisis-ventas")
async def get_analisis_ventas(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_desde: str = Query(..., description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: str = Query(..., description="Fecha hasta (YYYY-MM-DD)")
):
    """
    Análisis de ventas de productos terminados (PTT/Retail).
    Solo facturas de cliente con productos terminados.
    
    Returns:
        - resumen: totales generales
        - por_categoria: PTT, Retail, Subproducto
        - por_tipo: desglose por tipo de fruta
        - top_clientes: principales clientes
        - tendencia_precios: evolución mensual de precios
        - detalle: líneas individuales
    """
    try:
        odoo = OdooClient(username=username, password=password)
        service = AnalisisVentasService(odoo=odoo)
        return service.get_analisis_ventas(fecha_desde, fecha_hasta)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analisis-produccion")
async def get_analisis_produccion(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_desde: str = Query(..., description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: str = Query(..., description="Fecha hasta (YYYY-MM-DD)")
):
    """
    Análisis de rendimientos de producción (PSP → PTT).
    Usa órdenes de fabricación y movimientos de stock.
    
    Returns:
        - resumen: totales de consumo, producción, merma
        - rendimientos_por_tipo: % rendimiento por tipo de fruta
        - detalle_ordenes: detalle de órdenes de producción
    """
    try:
        odoo = OdooClient(username=username, password=password)
        service = AnalisisProduccionService(odoo=odoo)
        return service.get_analisis_produccion(fecha_desde, fecha_hasta)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analisis-inventario")
async def get_analisis_inventario(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_desde: str = Query(..., description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: str = Query(..., description="Fecha hasta (YYYY-MM-DD)")
):
    """
    Análisis de inventario y rotación de stock.
    Calcula stock actual, valorización, rotación, días de inventario.
    
    Returns:
        - resumen: stock total, valorización
        - por_producto: detalle por producto con rotación
        - por_ubicacion: stock por ubicación
        - alertas: productos con stock bajo o sin movimiento
    """
    try:
        odoo = OdooClient(username=username, password=password)
        service = AnalisisInventarioService(odoo=odoo)
        return service.get_analisis_inventario(fecha_desde, fecha_hasta)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock-teorico-rango")
async def get_stock_teorico_rango(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    fecha_desde: str = Query(..., description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: str = Query(..., description="Fecha fin YYYY-MM-DD")
):
    """
    Análisis de stock teórico para un rango de fechas específico.
    Calcula: Compras - Ventas - Merma proyectada = Stock Teórico
    
    Args:
        fecha_desde: Fecha inicio en formato YYYY-MM-DD
        fecha_hasta: Fecha fin en formato YYYY-MM-DD
    
    Returns:
        - resumen: totales consolidados del período
        - datos: desglose detallado por tipo de fruta y manejo con:
            * compras_kg, compras_monto, precio_promedio_compra
            * ventas_kg, ventas_monto, precio_promedio_venta
            * merma_kg, merma_pct
            * stock_teorico_kg, stock_teorico_valor
        - merma_historica_pct: % de merma calculado para el período
    """
    try:
        odoo = OdooClient(username=username, password=password)
        service = AnalisisStockTeoricoService(odoo)
        
        resultado = service.get_analisis_rango(fecha_desde, fecha_hasta)
        
        return resultado
    
    except Exception as e:
        return {"error": str(e)}


@router.get("/stock-teorico-anual")
async def get_stock_teorico_anual(
    username: str = Query(..., description="Usuario Odoo"),
    password: str = Query(..., description="API Key Odoo"),
    anios: str = Query(..., description="Años separados por coma (ej: 2024,2025,2026)"),
    fecha_corte: str = Query("10-31", description="Fecha de corte MM-DD (default: 10-31)")
):
    """
    Análisis de stock teórico anual por tipo de fruta y manejo.
    Calcula: Compras - Ventas - Merma proyectada = Stock Teórico
    
    Args:
        anios: Años a analizar separados por coma (ej: "2024,2025,2026")
        fecha_corte: Mes-Día de corte para cada año (default: "10-31" = 31 octubre)
    
    Returns:
        - resumen_general: totales consolidados de todos los años
        - por_anio: desglose detallado año por año con:
            * compras_kg, compras_monto, precio_promedio_compra
            * ventas_kg, ventas_monto, precio_promedio_venta
            * merma_kg, merma_pct
            * stock_teorico_kg, stock_teorico_valor
        - merma_historica_pct: % de merma calculado histórico
    """
    try:
        # Convertir string de años a lista de enteros
        anios_list = [int(a.strip()) for a in anios.split(",")]
        
        odoo = OdooClient(username=username, password=password)
        service = AnalisisStockTeoricoService(odoo=odoo)
        return service.get_analisis_multi_anual(anios_list, fecha_corte)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Formato de años inválido: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

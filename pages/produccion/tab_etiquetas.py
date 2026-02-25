"""
Tab de Etiquetas (Pallets y Cajas)
Permite buscar órdenes de producción y generar etiquetas para cada pallet o caja
Cliente se obtiene automáticamente desde x_studio_clientes de la orden
"""
import streamlit as st
import httpx
import re
import time
from typing import List, Dict
from .shared import API_URL


def _throttle_rerun(key: str = "etiq", min_interval: float = 1.0) -> bool:
    """Limita la frecuencia de reruns. Retorna True si se puede hacer rerun."""
    now = time.time()
    last_key = f"_throttle_last_{key}"
    last_time = st.session_state.get(last_key, 0)
    if now - last_time < min_interval:
        return False
    st.session_state[last_key] = now
    return True


def extraer_codigo_descripcion(nombre_producto: str) -> tuple:
    """
    Extrae el código y descripción del nombre del producto.
    Ejemplo: "[402122000] FB MK Conv. IQF A 10 kg en Caja" -> ("402122000", "FB MK Conv. IQF A 10 kg en Caja")
    """
    match = re.match(r'\[(\d+)\]\s*(.+)', nombre_producto)
    if match:
        return match.group(1), match.group(2)
    return '', nombre_producto


def extraer_peso_de_descripcion(descripcion: str) -> str:
    """
    Extrae el peso en kg de la descripción del producto.
    Ejemplo: "FB MK Conv. IQF A 10 kg en Caja" -> "10"
    Ejemplo: "AR HB Org. S/C PSP 13,61 kg en Caja" -> "13,61"
    """
    match = re.search(r'(\d+[.,]\d+)\s*kg', descripcion, re.IGNORECASE)
    if match:
        return match.group(1)  # Devuelve con coma/punto tal cual
    match = re.search(r'(\d+)\s*kg', descripcion, re.IGNORECASE)
    if match:
        return match.group(1)
    return "10"  # Por defecto


def calcular_fecha_vencimiento(fecha_elaboracion: str, años: int = 2) -> str:
    """
    Calcula la fecha de vencimiento sumando años a la fecha de elaboración.
    Formato entrada/salida: DD.MM.YYYY
    """
    from datetime import datetime, timedelta
    try:
        # Intentar varios formatos
        for fmt in ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d']:
            try:
                fecha = datetime.strptime(fecha_elaboracion, fmt)
                # Sumar años
                fecha_venc = fecha.replace(year=fecha.year + años)
                return fecha_venc.strftime('%d.%m.%Y')
            except ValueError:
                continue
        return fecha_elaboracion  # Si no se puede parsear, devolver la misma
    except Exception:
        return fecha_elaboracion


def _fecha_elaboracion_pallet(pallet: Dict) -> str:
    """
    Determina la fecha de elaboración para la etiqueta de un pallet.
    - Usa la fecha de inicio de la orden (fecha_inicio_fmt) por defecto.
    - Si el pallet se usó en un proceso anterior (fecha_elaboracion_fmt es más antigua),
      usa esa fecha para respetar cuándo se creó realmente el pallet.
    """
    fecha_orden = pallet.get('fecha_inicio_fmt', '')
    fecha_pallet = pallet.get('fecha_elaboracion_fmt', '')
    
    if not fecha_orden:
        return fecha_pallet
    if not fecha_pallet:
        return fecha_orden
    
    # Comparar ambas fechas (formato DD.MM.YYYY)
    try:
        from datetime import datetime
        for fmt in ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d']:
            try:
                dt_orden = datetime.strptime(fecha_orden, fmt)
                break
            except ValueError:
                continue
        else:
            return fecha_orden
        
        for fmt in ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d']:
            try:
                dt_pallet = datetime.strptime(fecha_pallet, fmt)
                break
            except ValueError:
                continue
        else:
            return fecha_orden
        
        # Si el pallet se inició antes que esta orden, usar la fecha del pallet
        if dt_pallet < dt_orden:
            return fecha_pallet
        return fecha_orden
    except Exception:
        return fecha_orden


def imprimir_etiqueta(html_etiqueta: str, height: int = 300):
    """
    Renderiza la etiqueta en un iframe con botón de imprimir.
    Usa window.print() directamente en el iframe (no window.open que los
    navegadores bloquean como popup).
    """
    import base64
    b64 = base64.b64encode(html_etiqueta.encode('utf-8')).decode()
    wrapper = f"""
    <html><head><style>
        body {{ margin:0; font-family:Arial,sans-serif; }}
        .btn-print {{
            display:block; width:100%; padding:8px; margin-bottom:6px;
            background:#2563eb; color:#fff; border:none; border-radius:6px;
            font-size:14px; font-weight:600; cursor:pointer;
        }}
        .btn-print:hover {{ background:#1d4ed8; }}
        iframe {{ border:1px solid #ddd; border-radius:4px; }}
    </style></head><body>
    <button class="btn-print" onclick="printLabel()">&#128424; Imprimir etiqueta</button>
    <iframe id="labelFrame" srcdoc="" style="width:100%;height:{height - 50}px;"></iframe>
    <script>
        var html = atob("{b64}");
        document.getElementById('labelFrame').srcdoc = html;
        function printLabel() {{
            var f = document.getElementById('labelFrame');
            f.contentWindow.focus();
            f.contentWindow.print();
        }}
    </script>
    </body></html>
    """
    st.components.v1.html(wrapper, height=height, scrolling=False)


def buscar_ordenes(username: str, password: str, termino: str):
    """Busca órdenes de producción."""
    params = {
        "username": username,
        "password": password,
        "termino": termino
    }
    response = httpx.get(
        f"{API_URL}/api/v1/etiquetas/buscar_ordenes",
        params=params,
        timeout=30.0
    )
    response.raise_for_status()
    return response.json()


def obtener_pallets_orden(username: str, password: str, orden_name: str):
    """Obtiene pallets de una orden."""
    params = {
        "username": username,
        "password": password,
        "orden_name": orden_name
    }
    response = httpx.get(
        f"{API_URL}/api/v1/etiquetas/pallets_orden",
        params=params,
        timeout=60.0
    )
    response.raise_for_status()
    return response.json()


def generar_etiqueta_html(datos: Dict) -> str:
    """
    Genera HTML de etiqueta sin fondo (el color lo da la etiqueta física).
    Usa JsBarcode para generar código de barras real.
    Tamaño: 100mm x 150mm
    """
    barcode_value = datos.get('barcode', datos.get('numero_pallet', ''))
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
        <style>
            @page {{
                size: 100mm 150mm;
                margin: 0;
            }}
            @media print {{
                body {{
                    width: 100mm;
                    height: 150mm;
                    margin: 0;
                    padding: 8mm;
                }}
            }}
            body {{
                font-family: Arial, sans-serif;
                padding: 8mm;
                margin: 0;
                width: 84mm;
                height: 134mm;
            }}
            .etiqueta {{
                width: 100%;
            }}
            .titulo {{
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .campo {{
                font-size: 14px;
                font-weight: bold;
                margin: 8px 0;
            }}
            .barcode-container {{
                margin-top: 20px;
            }}
            #barcode {{
                width: 100%;
            }}
        </style>
    </head>
    <body>
        <div class="etiqueta">
            <div class="titulo">{datos.get('nombre_producto', '')}</div>
            
            <div class="campo">CODIGO PRODUCTO: {datos.get('codigo_producto', '')}</div>
            <div class="campo">PESO PALLET: {datos.get('peso_pallet_kg', 0)} KG</div>
            <div class="campo">CANTIDAD CAJAS: {datos.get('cantidad_cajas', 0)}</div>
            <div class="campo">FECHA ELABORACION: {datos.get('fecha_elaboracion', '')}</div>
            <div class="campo">FECHA VENCIMIENTO: {datos.get('fecha_vencimiento', '')}</div>
            <div class="campo">LOTE PRODUCCION: {datos.get('lote_produccion', '')}</div>
            <div class="campo">NUMERO DE PALLET: {datos.get('numero_pallet', '')}</div>
            
            <div class="barcode-container">
                <svg id="barcode"></svg>
            </div>
        </div>
        <script>
            JsBarcode("#barcode", "{barcode_value}", {{
                format: "CODE128",
                width: 2,
                height: 60,
                displayValue: true,
                fontSize: 14,
                margin: 10,
                background: "transparent"
            }});
        </script>
    </body>
    </html>
    """
    return html


def _generar_etiqueta_100x50(datos: Dict, mostrar_md: bool = False, md_checked: bool = False) -> str:
    """
    Genera HTML de etiqueta de producto 100mm x 50mm.
    Layout común para etiquetas genéricas de pallet y etiquetas de caja por cliente.
    """
    nombre = datos.get('nombre_producto', '')
    # Para etiquetas 100x50 usar x_studio_fecha_inicio; fallback a fecha_elaboracion
    fecha_elab = datos.get('fecha_inicio', '') or datos.get('fecha_elaboracion', '')
    fecha_venc = calcular_fecha_vencimiento(fecha_elab, años=2) if fecha_elab else ''
    lote = datos.get('lote_produccion', '')
    pallet = datos.get('numero_pallet', '')
    peso = datos.get('peso_caja_kg', extraer_peso_de_descripcion(nombre))

    md_html = ''
    if mostrar_md:
        check_inner = '<span class="tick"></span>' if md_checked else ''
        md_html = f'''
        <div class="md-box">
            <span>MD</span>
            <div class="checkbox">{check_inner}</div>
        </div>
        '''

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: 100mm 50mm;
                margin: 0;
            }}
            @media print {{
                body {{
                    width: 100mm;
                    height: 50mm;
                    margin: 0;
                    padding: 2mm 3mm;
                }}
            }}
            body {{
                font-family: Arial, sans-serif;
                padding: 2mm 3mm;
                margin: 0;
                width: 94mm;
                height: 46mm;
                font-size: 10px;
                line-height: 1.4;
            }}
            .titulo {{
                font-size: 13px;
                font-weight: bold;
                text-align: center;
                margin-bottom: 4px;
                text-transform: uppercase;
                line-height: 1.2;
                padding-bottom: 3px;
            }}
            .contenido {{
                padding: 2px 0;
            }}
            .linea {{
                margin: 1px 0;
            }}
            .md-box {{
                margin-top: 4px;
                display: flex;
                align-items: center;
                gap: 5px;
            }}
            .checkbox {{
                width: 16px;
                height: 16px;
                border: 1px solid black;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                position: relative;
            }}
            .checkbox .tick {{
                display: inline-block;
                width: 4px;
                height: 9px;
                border: solid black;
                border-width: 0 2px 2px 0;
                transform: rotate(45deg);
                margin-bottom: 2px;
            }}
        </style>
    </head>
    <body>
        <div class="titulo">{nombre}</div>

        <div class="contenido">
            <div class="linea">Fecha de elaboraci&oacute;n: {fecha_elab} / Fecha de vencimiento: {fecha_venc}</div>
            <div class="linea">Lote: {lote} / Pallet: {pallet}</div>
            <div class="linea">Peso Neto: {peso} kg</div>
            <div class="linea">PRODUCTO CONGELADO</div>
            <div class="linea">Planta: Rio Futuro Procesos Spa</div>
            <div class="linea">Camino Contra Coronel Lote 4, Cocule, Rio Bueno, Chile</div>
            <div class="linea">Res Servicio Salud Valdivia Dpto. del Ambiente</div>
            <div class="linea">XIV Regi&oacute;n, N&deg; 2214585504 del 30-11-2022</div>
            <div class="linea">C&oacute;digo SAG Planta: 105721</div>
        </div>

        {md_html}
    </body>
    </html>
    """
    return html


def generar_etiqueta_pallet_generica(datos: Dict) -> str:
    """
    Genera etiqueta genérica de pallet en 100x50mm.
    Mismo diseño que la estándar (campos + código de barras) pero más compacto.
    Usa x_studio_fecha_inicio como fecha de elaboración.
    """
    barcode_value = datos.get('barcode', datos.get('numero_pallet', ''))
    fecha_elab = datos.get('fecha_inicio', '') or datos.get('fecha_elaboracion', '')
    fecha_venc = calcular_fecha_vencimiento(fecha_elab, años=2) if fecha_elab else ''

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
        <style>
            @page {{
                size: 100mm 50mm;
                margin: 0;
            }}
            @media print {{
                body {{
                    width: 100mm;
                    height: 50mm;
                    margin: 0;
                    padding: 2mm 3mm;
                }}
            }}
            body {{
                font-family: Arial, sans-serif;
                padding: 2mm 3mm;
                margin: 0;
                width: 94mm;
                height: 46mm;
            }}
            .etiqueta {{
                width: 100%;
            }}
            .titulo {{
                font-size: 10px;
                font-weight: bold;
                margin-bottom: 3px;
            }}
            .campo {{
                font-size: 9px;
                font-weight: bold;
                margin: 2px 0;
            }}
            .barcode-container {{
                margin-top: 4px;
            }}
            #barcode {{
                width: 100%;
            }}
        </style>
    </head>
    <body>
        <div class="etiqueta">
            <div class="titulo">{datos.get('nombre_producto', '')}</div>

            <div class="campo">CODIGO PRODUCTO: {datos.get('codigo_producto', '')}</div>
            <div class="campo">PESO PALLET: {datos.get('peso_pallet_kg', 0)} KG</div>
            <div class="campo">CANTIDAD CAJAS: {datos.get('cantidad_cajas', 0)}</div>
            <div class="campo">FECHA ELABORACION: {fecha_elab}</div>
            <div class="campo">FECHA VENCIMIENTO: {fecha_venc}</div>
            <div class="campo">LOTE PRODUCCION: {datos.get('lote_produccion', '')}</div>
            <div class="campo">NUMERO DE PALLET: {datos.get('numero_pallet', '')}</div>

            <div class="barcode-container">
                <svg id="barcode"></svg>
            </div>
        </div>
        <script>
            JsBarcode("#barcode", "{barcode_value}", {{
                format: "CODE128",
                width: 1.5,
                height: 30,
                displayValue: true,
                fontSize: 10,
                margin: 4,
                background: "transparent"
            }});
        </script>
    </body>
    </html>
    """
    return html


def render(username: str, password: str):
    """Renderiza el tab de etiquetas (tarjas pallet y etiquetas caja)."""
    
    st.header("🏷️ Generación de Etiquetas")
    
    # ==================== ESTADO COMPARTIDO ====================
    if "etiq_orden_seleccionada" not in st.session_state:
        st.session_state.etiq_orden_seleccionada = None
    if "etiq_pallets_cargados" not in st.session_state:
        st.session_state.etiq_pallets_cargados = []
    if "etiq_ordenes_encontradas" not in st.session_state:
        st.session_state.etiq_ordenes_encontradas = []
    if "etiq_pallets_carga_intentada" not in st.session_state:
        st.session_state.etiq_pallets_carga_intentada = False
    
    # ==================== PASO 1: BUSCAR ORDEN (COMPARTIDO) ====================
    st.subheader("1️⃣ Buscar Orden de Producción")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        termino_busqueda = st.text_input(
            "Buscar orden",
            placeholder="Ej: WH/MO/12345",
            help="Ingresa el nombre o referencia de la orden",
            key="etiq_termino_busqueda"
        )
    with col2:
        btn_buscar = st.button("🔍 Buscar", type="primary", use_container_width=True, key="etiq_btn_buscar")
    
    if btn_buscar and termino_busqueda:
        with st.spinner("Buscando órdenes..."):
            try:
                ordenes = buscar_ordenes(username, password, termino_busqueda)
                st.session_state.etiq_ordenes_encontradas = ordenes
                if ordenes:
                    st.success(f"✅ Se encontraron {len(ordenes)} órdenes")
                else:
                    st.warning("⚠️ No se encontraron órdenes")
            except Exception as e:
                st.error(f"❌ Error al buscar órdenes: {e}")
                st.session_state.etiq_ordenes_encontradas = []
    
    # Mostrar órdenes encontradas
    if st.session_state.etiq_ordenes_encontradas:
        st.write("**Órdenes encontradas:**")
        for orden in st.session_state.etiq_ordenes_encontradas:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{orden.get('name', '')}**")
                product_name = orden.get('product_id', ['', ''])[1] if isinstance(orden.get('product_id'), list) else orden.get('product_name', '')
                st.caption(f"Producto: {product_name}")
            with col2:
                st.write(f"Estado: {orden.get('state', '')}")
                cliente_auto = orden.get('cliente_nombre', '')
                if cliente_auto:
                    st.caption(f"👤 Cliente: {cliente_auto}")
            with col3:
                if st.button("Seleccionar", key=f"etiq_sel_{orden.get('id')}", use_container_width=True):
                    st.session_state.etiq_orden_seleccionada = orden
                    st.session_state.etiq_pallets_cargados = []
                    st.session_state.etiq_pallets_carga_intentada = False
                    # Auto-cargar pallets
                    try:
                        pallets = obtener_pallets_orden(username, password, orden.get('name'))
                        st.session_state.etiq_pallets_cargados = pallets
                        st.session_state.etiq_pallets_carga_intentada = True
                    except Exception:
                        st.session_state.etiq_pallets_carga_intentada = True
                    if _throttle_rerun("etiq_select"):
                        st.rerun()
    
    # ==================== PASO 2: ORDEN SELECCIONADA (COMPARTIDO) ====================
    if st.session_state.etiq_orden_seleccionada:
        orden = st.session_state.etiq_orden_seleccionada
        product_name = orden.get('product_id', ['', ''])[1] if isinstance(orden.get('product_id'), list) else orden.get('product_name', '')
        cliente_nombre = orden.get('cliente_nombre', '')
        
        st.divider()
        st.subheader("2️⃣ Orden Seleccionada")
        st.info(f"📦 **{orden.get('name')}** — {product_name}")
        if cliente_nombre:
            st.success(f"👤 Cliente: **{cliente_nombre}**")
        
        pallets = st.session_state.etiq_pallets_cargados
        if pallets:
            st.write(f"✅ **{len(pallets)} pallets cargados**")
        elif st.session_state.etiq_pallets_carga_intentada:
            # Ya se intentó cargar y no hay pallets
            st.warning("⚠️ No se encontraron pallets para esta orden")
        else:
            # Auto-cargar pallets si aún no se intentó
            with st.spinner("Cargando pallets..."):
                try:
                    pallets = obtener_pallets_orden(username, password, orden.get('name'))
                    st.session_state.etiq_pallets_cargados = pallets
                    st.session_state.etiq_pallets_carga_intentada = True
                    if pallets and _throttle_rerun("etiq_load"):
                        st.rerun()
                    elif not pallets:
                        st.warning("⚠️ No se encontraron pallets para esta orden")
                except Exception as e:
                    st.session_state.etiq_pallets_carga_intentada = True
                    st.error(f"❌ Error al cargar pallets: {e}")
        
        if st.button("❌ Cambiar Orden", use_container_width=False, key="etiq_btn_cambiar"):
            st.session_state.etiq_orden_seleccionada = None
            st.session_state.etiq_pallets_cargados = []
            st.session_state.etiq_ordenes_encontradas = []
            st.session_state.etiq_pallets_carga_intentada = False
            if _throttle_rerun("etiq_cambiar"):
                st.rerun()
        
        # ==================== PASO 3: SECCIONES DE ETIQUETAS ====================
        if st.session_state.etiq_pallets_cargados:
            st.divider()
            
            # ---------- Tarja por Pallet o Etiquetas por Caja ----------
            tipo_etiqueta = st.radio(
                "Tipo de etiqueta",
                ["📦 Tarja por Pallet", "🏷️ Etiquetas por Caja"],
                horizontal=True,
                key="etiq_tipo"
            )
            
            st.divider()
            
            if tipo_etiqueta == "📦 Tarja por Pallet":
                render_etiquetas_pallet(username, password)
            else:
                # ---------- ETIQUETAS POR CAJA ----------
                # Todos los pallets usan etiqueta genérica con los datos del producto
                # exactamente como está registrado en Odoo (subproductos de la orden)
                all_pallets = st.session_state.etiq_pallets_cargados
                if all_pallets:
                    render_seccion_subproductos(username, password, all_pallets, titulo="📋 ETIQUETAS POR CAJA")
                else:
                    st.warning("No se encontraron pallets para generar etiquetas.")


# ==================== DISEÑOS DE ETIQUETAS POR CLIENTE ====================

def generar_etiqueta_caja_retail(datos: Dict) -> str:
    """
    Genera HTML de etiqueta de caja para productos IQF Retail.
    Tamaño: 100mm x 100mm — con checkbox MD.
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: 100mm 100mm;
                margin: 0;
            }}
            @media print {{
                body {{
                    width: 100mm;
                    height: 100mm;
                    margin: 0;
                    padding: 0;
                }}
            }}
            body {{
                font-family: Arial, sans-serif;
                padding: 0;
                margin: 0;
                width: 100mm;
                height: 100mm;
            }}
            .recuadro {{
                padding: 4mm 5mm;
                margin: 2mm;
                height: calc(100mm - 6mm);
                box-sizing: border-box;
                font-size: 12px;
                line-height: 1.5;
            }}
            .titulo {{
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                margin-bottom: 4px;
                padding-bottom: 4px;
                line-height: 1.2;
            }}
            .linea {{
                margin: 1px 0;
            }}
            .md-box {{
                margin-top: 8px;
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 14px;
                font-weight: bold;
            }}
            .checkbox {{
                width: 22px;
                height: 22px;
                border: 2px solid #333;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                position: relative;
            }}
            .checkbox .tick {{
                display: inline-block;
                width: 6px;
                height: 12px;
                border: solid #333;
                border-width: 0 2.5px 2.5px 0;
                transform: rotate(45deg);
                margin-bottom: 2px;
            }}
        </style>
    </head>
    <body>
        <div class="recuadro">
            <div class="titulo">{datos.get('nombre_producto', '')}</div>
            <div class="linea">Fecha de elaboraci&oacute;n: {datos.get('fecha_elaboracion', '')} / Fecha de vencimiento: {datos.get('fecha_vencimiento', '')}</div>
            <div class="linea">Lote: {datos.get('lote_produccion', '')} / Pallet: {datos.get('numero_pallet', '')}</div>
            <div class="linea">Peso Neto: {datos.get('peso_caja_kg', 10)} kg</div>
            <div class="linea">PRODUCTO CONGELADO</div>
            <div class="linea">Planta: Rio Futuro Procesos Spa</div>
            <div class="linea">Camino Contra Coronel Lote 4, Cocule, Rio Bueno, Chile</div>
            <div class="linea">Res Servicio Salud Valdivia Dpto. del Ambiente</div>
            <div class="linea">XIV Regi&oacute;n, N&deg; 2214585504 del 30-11-2022</div>
            <div class="linea">C&oacute;digo SAG Planta: 105721</div>
            
            <div class="md-box">
                <span>MD</span>
                <div class="checkbox"><span class="tick"></span></div>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def generar_etiqueta_caja_lanna(datos: Dict) -> str:
    """
    Genera HTML de etiqueta(s) de caja para IQF A — estilo LACO.
    Genera N etiquetas (una por caja/cart&oacute;n) con CARTON NO enumerado.
    MATERIAL CODE y PRODUCT NAME fijos. Solo fecha, lote y pallet vienen de Odoo.
    """
    fecha_elab = datos.get('fecha_elaboracion', '').replace('.', '-')
    fecha_venc = datos.get('fecha_vencimiento', '').replace('.', '-')
    lote = datos.get('lote_produccion', '')
    pallet = datos.get('numero_pallet', '')

    # Obtener el número inicial de cartón
    carton_no_inicio = datos.get('carton_no_inicio', 1)

    # Calcular cantidad de cajas (cartones)
    cantidad_cajas = datos.get('cantidad_cajas', 0)
    if not cantidad_cajas:
        peso_pallet = datos.get('peso_pallet_kg', 0)
        cantidad_cajas = max(int(peso_pallet / 10), 1) if peso_pallet else 1

    # Generar una etiqueta por cada cartón
    labels_html = ""
    for i in range(carton_no_inicio, carton_no_inicio + cantidad_cajas):
        labels_html += f"""
        <div class="etiqueta">
            <div class="campo"><span class="label">MATERIAL CODE: </span><span class="valor">RIRASPBERRY</span></div>
            <div class="campo"><span class="label">PRODUCT NAME: </span><span class="valor">Frozen Raspberry 12-24 mm</span></div>
            <div class="campo"><span class="label">NET WEIGHT: </span><span class="valor">10KG</span></div>
            <div class="campo"><span class="label">PRODUCTION DATE: </span><span class="valor">{fecha_elab}</span></div>
            <div class="campo"><span class="label">BEST BEFORE: </span><span class="valor">{fecha_venc}</span></div>
            <div class="campo"><span class="label">BATCH NO.: </span><span class="valor">{lote} / {pallet}</span></div>
            <div class="campo"><span class="label">STORAGE TEMPERATURE: </span><span class="valor">-18&deg;C</span></div>
            <div class="campo"><span class="label">ORIGIN: </span><span class="valor">CHILE</span></div>
            <div class="campo"><span class="label">CARTON NO.: </span><span class="valor">{i}</span></div>
            <div class="campo"><span class="label">PRODUCT FOR </span><span class="valor">LACO</span></div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: 100mm 100mm;
                margin: 0;
            }}
            * {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            html, body {{
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
                width: 100mm;
            }}
            .etiqueta {{
                width: 100mm;
                height: 100mm;
                padding: 3mm 4mm;
                box-sizing: border-box;
                page-break-after: always;
                page-break-inside: avoid;
            }}
            .etiqueta:last-child {{
                page-break-after: auto;
            }}
            .campo {{
                font-size: 11px;
                margin: 1px 0;
                line-height: 1.4;
            }}
            .campo .label {{
                font-weight: normal;
            }}
            .campo .valor {{
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        {labels_html}
    </body>
    </html>
    """
    return html


# Diseños por tipo de producto (no por cliente)
DISEÑOS_ETIQUETAS_CAJA = {
    "RETAIL": generar_etiqueta_caja_retail,    # IQF Retail -> con MD
    "LACO": generar_etiqueta_caja_lanna,        # IQF A -> estilo LACO
}


def generar_etiqueta_caja_generica(datos: Dict) -> str:
    """
    Genera HTML de etiqueta gen&eacute;rica (subproductos).
    Tama&ntilde;o: 100mm x 100mm, sin MD.
    """
    nombre = datos.get('nombre_producto', '')
    fecha_elab = datos.get('fecha_elaboracion', '')
    fecha_venc = datos.get('fecha_vencimiento', '')
    lote = datos.get('lote_produccion', '')
    pallet = datos.get('numero_pallet', '')
    peso = datos.get('peso_neto_kg', '10')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: 100mm 100mm;
                margin: 0;
            }}
            @media print {{
                body {{
                    width: 100mm;
                    height: 100mm;
                    margin: 0;
                    padding: 0;
                }}
            }}
            body {{
                font-family: Arial, sans-serif;
                padding: 0;
                margin: 0;
                width: 100mm;
                height: 100mm;
            }}
            .recuadro {{
                padding: 4mm 5mm;
                margin: 2mm;
                height: calc(100mm - 6mm);
                box-sizing: border-box;
                font-size: 13px;
                line-height: 1.55;
            }}
            .titulo {{
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                margin-bottom: 4px;
                padding-bottom: 4px;
                line-height: 1.2;
            }}
            .linea {{
                margin: 1px 0;
            }}
        </style>
    </head>
    <body>
        <div class="recuadro">
            <div class="titulo">{nombre}</div>
            <div class="linea">Fecha de elaboraci&oacute;n: {fecha_elab} &nbsp; / &nbsp; Fecha de vencimiento: {fecha_venc}</div>
            <div class="linea">Lote: {lote}/ Pallet: {pallet}</div>
            <div class="linea">Peso Neto: {peso} kg</div>
            <div class="linea">PRODUCTO CONGELADO</div>
            <div class="linea">Planta: Rio Futuro Procesos Spa</div>
            <div class="linea">Camino Contra Coronel Lote 4, Cocule, Rio Bueno, Chile</div>
            <div class="linea">Res Servicio Salud Valdivia Dpto. del Ambiente</div>
            <div class="linea">XIV Regi&oacute;n, N&deg; 2214585504 del 30-11-2022</div>
            <div class="linea">C&oacute;digo SAG Planta: 105721</div>
        </div>
    </body>
    </html>
    """
    return html


def _get_lot_name(pallet: Dict) -> str:
    """Extrae nombre de lote del pallet."""
    lot_name = pallet.get('lot_name', '') or pallet.get('lote_produccion', '') or ''
    if not lot_name:
        lot_id = pallet.get('lot_id')
        lot_name = lot_id[1] if isinstance(lot_id, (list, tuple)) and lot_id else ''
    return lot_name


def _agrupar_pallets_por_producto(pallets: List[Dict]) -> Dict:
    """Agrupa pallets por product_id, devuelve dict {product_key: {descripcion, codigo, pallets}}."""
    grupos = {}
    for p in pallets:
        pid = p.get('product_id')
        if not pid:
            continue
        pkey = pid[0] if isinstance(pid, list) else pid
        pname = pid[1] if isinstance(pid, list) else str(pid)
        codigo, desc = extraer_codigo_descripcion(pname)
        if pkey not in grupos:
            grupos[pkey] = {'codigo': codigo, 'descripcion': desc, 'pallets': []}
        grupos[pkey]['pallets'].append(p)
    return grupos


def render_seccion_iqf(username: str, password: str, pallets_iqf: List[Dict]):
    """Sección ETIQUETAS IQF — clasifica por tipo de producto (Retail vs IQF A)."""
    
    orden = st.session_state.etiq_orden_seleccionada
    cliente_nombre = orden.get('cliente_nombre', '')
    
    st.subheader("📋 ETIQUETAS IQF")
    
    grupos = _agrupar_pallets_por_producto(pallets_iqf)
    
    for pkey, grupo in grupos.items():
        desc = grupo['descripcion']
        codigo = grupo['codigo']
        pallets = grupo['pallets']
        
        # Determinar diseño por nombre del producto
        desc_upper = desc.upper()
        if 'RETAIL' in desc_upper:
            funcion_diseño = generar_etiqueta_caja_retail
            tipo_label = "Retail (MD)"
        else:
            funcion_diseño = generar_etiqueta_caja_lanna
            tipo_label = "LACO"
        
        titulo_producto = f"[{codigo}] {desc}" if codigo else desc
        st.markdown(f"#### 📦 {titulo_producto}")
        st.caption(f"{len(pallets)} pallets — Etiqueta: {tipo_label}")
        
        for pallet in pallets:
            with st.expander(f"{pallet.get('package_name', '')} — {pallet.get('cantidad_cajas', 0)} cajas"):
                lot_name = _get_lot_name(pallet)
                # Fecha de la orden, o del pallet si se inició en un proceso anterior
                fecha_elab = _fecha_elaboracion_pallet(pallet)
                fecha_venc = calcular_fecha_vencimiento(fecha_elab, años=2)
                
                datos_etiqueta = {
                    'nombre_producto': desc,
                    'codigo_producto': codigo,
                    'peso_caja_kg': extraer_peso_de_descripcion(desc),
                    'peso_neto_kg': extraer_peso_de_descripcion(desc),
                    'fecha_elaboracion': fecha_elab,
                    'fecha_vencimiento': fecha_venc,
                    'lote_produccion': lot_name,
                    'numero_pallet': pallet.get('package_name', ''),
                    'cantidad_cajas': int(pallet.get('cantidad_cajas', 0)),
                    'peso_pallet_kg': int(pallet.get('peso_pallet_kg', 0)),
                }
                
                if st.button("🖨️ Imprimir / Vista", key=f"etiq_iqf_{pallet.get('package_id')}", use_container_width=True):
                    # Usar la fecha de inicio de la orden seleccionada
                    orden = st.session_state.etiq_orden_seleccionada
                    fecha_inicio_proceso = orden.get('fecha_inicio_fmt', '') or orden.get('fecha_elaboracion_fmt', '')
                    package_id = pallet.get('package_id')
                    params = {
                        "username": username,
                        "password": password,
                        "fecha_inicio_proceso": fecha_inicio_proceso
                    }
                    url = f"{API_URL}/api/v1/etiquetas/info_etiqueta/{package_id}"
                    try:
                        response = httpx.get(url, params=params, timeout=30.0)
                        response.raise_for_status()
                        datos_backend = response.json()
                        datos_etiqueta.update({
                            'carton_no_inicio': datos_backend.get('carton_no_inicio', 1),
                            'cantidad_cajas': datos_backend.get('cantidad_cajas', datos_etiqueta['cantidad_cajas'])
                        })
                    except Exception as e:
                        st.error(f"No se pudo obtener correlativo de cartón: {e}")
                    html_print = funcion_diseño(datos_etiqueta)
                    imprimir_etiqueta(html_print, height=420)
    
    st.divider()


def render_seccion_subproductos(username: str, password: str, pallets_sub: List[Dict], titulo: str = "📋 ETIQUETAS SUBPRODUCTOS"):
    """Sección ETIQUETAS — detecta tipo de producto y usa el diseño correcto."""
    
    st.subheader(titulo)
    
    grupos = _agrupar_pallets_por_producto(pallets_sub)
    
    for pkey, grupo in grupos.items():
        desc = grupo['descripcion']
        codigo = grupo['codigo']
        peso_neto = extraer_peso_de_descripcion(desc)
        pallets = grupo['pallets']
        
        # Detectar tipo de producto → diseño correcto
        desc_upper = desc.upper()
        if 'RETAIL' in desc_upper:
            tipo_diseño = 'RETAIL'
            tipo_label = "Retail 100×100mm (MD)"
        elif 'IQF A' in desc_upper:
            tipo_diseño = 'LACO'
            tipo_label = "LACO 100×100mm"
        else:
            tipo_diseño = 'GENERICA'
            tipo_label = "Genérica 100×50mm"
        
        titulo_producto = f"[{codigo}] {desc}" if codigo else desc
        st.markdown(f"#### 📦 {titulo_producto}")
        st.caption(f"{len(pallets)} pallets — Etiqueta: {tipo_label}")
        
        for pallet in pallets:
            with st.expander(f"{pallet.get('package_name', '')} — {pallet.get('cantidad_cajas', 0)} cajas"):
                lot_name = _get_lot_name(pallet)
                # Fecha de la orden, o del pallet si se inició en un proceso anterior
                fecha_elab = _fecha_elaboracion_pallet(pallet)
                fecha_venc = calcular_fecha_vencimiento(fecha_elab, años=2)
                
                datos_etiqueta = {
                    'nombre_producto': desc,
                    'codigo_producto': codigo,
                    'peso_caja_kg': peso_neto,
                    'peso_neto_kg': peso_neto,
                    'fecha_elaboracion': fecha_elab,
                    'fecha_vencimiento': fecha_venc,
                    'lote_produccion': lot_name,
                    'numero_pallet': pallet.get('package_name', ''),
                    'cantidad_cajas': int(pallet.get('cantidad_cajas', 0)),
                    'peso_pallet_kg': int(pallet.get('peso_pallet_kg', 0)),
                }
                
                if st.button("🖨️ Imprimir / Vista", key=f"etiq_sub_{pallet.get('package_id')}", use_container_width=True):
                    if tipo_diseño == 'RETAIL':
                        html_print = generar_etiqueta_caja_retail(datos_etiqueta)
                    elif tipo_diseño == 'LACO':
                        html_print = generar_etiqueta_caja_lanna(datos_etiqueta)
                    else:
                        html_print = generar_etiqueta_caja_generica(datos_etiqueta)
                    imprimir_etiqueta(html_print, height=420)
    
    st.divider()


def render_etiquetas_pallet(username: str, password: str):
    """Renderiza etiquetas por pallet — usa estado compartido."""
    
    st.write(f"**Total de pallets:** {len(st.session_state.etiq_pallets_cargados)}")
    
    vista_opcion = st.radio(
        "Mostrar:",
        ["🆕 Solo último pallet", "📋 Todos los pallets"],
        horizontal=True,
        key="etiq_vista_opcion"
    )
    
    st.divider()
    
    # Agrupar pallets por producto
    pallets_por_producto = {}
    for pallet in st.session_state.etiq_pallets_cargados:
        product_id = pallet.get('product_id')
        if product_id:
            product_key = product_id[0] if isinstance(product_id, list) else product_id
            product_name = product_id[1] if isinstance(product_id, list) else str(product_id)
            
            codigo, descripcion = extraer_codigo_descripcion(product_name)
            
            if product_key not in pallets_por_producto:
                pallets_por_producto[product_key] = {
                    'nombre': product_name,
                    'codigo': codigo,
                    'descripcion': descripcion,
                    'pallets': []
                }
            pallets_por_producto[product_key]['pallets'].append(pallet)
    
    if vista_opcion == "🆕 Solo último pallet":
        for product_key in pallets_por_producto:
            pallets_por_producto[product_key]['pallets'] = [pallets_por_producto[product_key]['pallets'][-1]]
    
    for product_key, producto_data in pallets_por_producto.items():
        st.markdown(f"### 📦 {producto_data['descripcion']}")
        cantidad_mostrados = len(producto_data['pallets'])
        if vista_opcion == "🆕 Solo último pallet":
            st.caption("Último pallet ingresado")
        else:
            st.caption(f"{cantidad_mostrados} pallets")
        
        for pallet in producto_data['pallets']:
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"**{pallet.get('package_name', 'Sin nombre')}**")
            
            product_id = pallet.get('product_id')
            product_name = product_id[1] if isinstance(product_id, (list, tuple)) else 'Producto desconocido'
            
            codigo_prod, descripcion_prod = extraer_codigo_descripcion(product_name)
            
            lot_id = pallet.get('lot_id')
            lot_name = lot_id[1] if isinstance(lot_id, (list, tuple)) and lot_id else 'Sin lote'
            
            barcode_odoo = pallet.get('barcode', pallet.get('package_name', ''))
            cliente_pallet = pallet.get('cliente_nombre', '')
            
            # Fecha de la orden, o del pallet si se inició en un proceso anterior
            fecha_elab_pallet = _fecha_elaboracion_pallet(pallet)
            datos_etiqueta = {
                'cliente': cliente_pallet,
                'nombre_producto': descripcion_prod,
                'codigo_producto': codigo_prod,
                'peso_pallet_kg': int(pallet.get('peso_pallet_kg', 0)),
                'cantidad_cajas': int(pallet.get('cantidad_cajas', 0)),
                'fecha_elaboracion': fecha_elab_pallet,
                'fecha_vencimiento': pallet.get('fecha_vencimiento', ''),
                'lote_produccion': lot_name,
                'numero_pallet': pallet.get('package_name', ''),
                'barcode': barcode_odoo
            }
            
            with col2:
                if st.button("🖨️ Imprimir / Vista", key=f"etiq_print_{pallet.get('package_id')}", use_container_width=True):
                    html_print = generar_etiqueta_html(datos_etiqueta)
                    imprimir_etiqueta(html_print, height=550)
        
        st.divider()


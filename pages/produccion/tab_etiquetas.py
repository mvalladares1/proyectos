"""
Tab de Etiquetas (Pallets y Cajas)
Permite buscar órdenes de producción y generar etiquetas para cada pallet o caja
Cliente se obtiene automáticamente desde x_studio_clientes de la orden
"""
import streamlit as st
import httpx
import re
from typing import List, Dict
from produccion.shared import API_URL


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
                    # Auto-cargar pallets
                    try:
                        pallets = obtener_pallets_orden(username, password, orden.get('name'))
                        st.session_state.etiq_pallets_cargados = pallets
                    except Exception:
                        pass
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
        else:
            # Auto-cargar pallets si aún no se cargaron
            with st.spinner("Cargando pallets..."):
                try:
                    pallets = obtener_pallets_orden(username, password, orden.get('name'))
                    st.session_state.etiq_pallets_cargados = pallets
                    if pallets:
                        st.rerun()
                    else:
                        st.warning("⚠️ No se encontraron pallets para esta orden")
                except Exception as e:
                    st.error(f"❌ Error al cargar pallets: {e}")
        
        if st.button("❌ Cambiar Orden", use_container_width=False, key="etiq_btn_cambiar"):
            st.session_state.etiq_orden_seleccionada = None
            st.session_state.etiq_pallets_cargados = []
            st.session_state.etiq_ordenes_encontradas = []
            st.rerun()
        
        # ==================== PASO 3: TIPO DE ETIQUETA ====================
        if st.session_state.etiq_pallets_cargados:
            st.divider()
            
            tipo_etiqueta = st.radio(
                "Tipo de etiqueta",
                ["📦 Tarja por Pallet", "🎁 Etiqueta por Caja"],
                horizontal=True,
                key="etiq_tipo"
            )
            
            st.divider()
            
            if tipo_etiqueta == "📦 Tarja por Pallet":
                render_etiquetas_pallet(username, password)
            else:
                render_etiquetas_caja(username, password)


# ==================== DISEÑOS DE ETIQUETAS POR CLIENTE ====================

def generar_etiqueta_caja_tronador(datos: Dict) -> str:
    """
    Genera HTML de etiqueta de caja para cliente TRONADOR SAC.
    Tamaño: 100mm x 100mm
    Solo para productos IQF A
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
                    padding: 3mm;
                }}
            }}
            body {{
                font-family: Arial, sans-serif;
                padding: 3mm;
                margin: 0;
                width: 94mm;
                height: 94mm;
                font-size: 11px;
            }}
            .titulo {{
                font-size: 15px;
                font-weight: bold;
                text-align: center;
                margin-bottom: 5px;
                text-transform: uppercase;
                line-height: 1.2;
            }}
            .recuadro {{
                padding: 5px 0px;
                margin-top: 3px;
            }}
            .linea {{
                margin: 2px 0;
            }}
            .md-box {{
                margin-top: 5px;
                display: flex;
                align-items: center;
                gap: 5px;
            }}
            .checkbox {{
                width: 20px;
                height: 20px;
                border: 1px solid black;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="titulo">{datos.get('nombre_producto', '')}</div>
        
        <div class="recuadro">
            <div class="linea">Fecha de elaboración: {datos.get('fecha_elaboracion', '')}</div>
            <div class="linea">Fecha de vencimiento: {datos.get('fecha_vencimiento', '')}</div>
            <div class="linea">Lote: {datos.get('lote_produccion', '')}</div>
            <div class="linea">Pallet: {datos.get('numero_pallet', '')}</div>
            <div class="linea">Peso Neto: {datos.get('peso_caja_kg', 10)} kg</div>
            <div class="linea">PRODUCTO CONGELADO</div>
            <div class="linea">Planta Cocule: Rio Futuro Procesos Spa</div>
            <div class="linea">Camino Contra Coronel Lote 4, Cocule, Rio Bueno, Chile</div>
            <div class="linea">Res Servicio Salud Valdivia Dpto. del Ambiente</div>
            <div class="linea">XIV Región, N° 2214585504 del 30-11-2022</div>
            <div class="linea">Código SAG Planta: 105721</div>
        </div>
        
        <div class="md-box">
            <span>MD</span>
            <div class="checkbox">✓</div>
        </div>
    </body>
    </html>
    """
    return html


def generar_etiqueta_caja_lanna(datos: Dict) -> str:
    """
    Genera HTML de etiqueta(s) de caja para cliente LANNA AGRO INDUSTRY.
    Tamaño: 100mm x 100mm — estilo LACO.
    Genera N etiquetas (una por caja/cartón) con CARTON NO enumerado.
    NET WEIGHT fijo 10KG. Solo fecha, lote y pallet vienen de Odoo.
    """
    codigo = datos.get('codigo_producto', '')
    nombre = datos.get('nombre_producto', '')
    fecha_elab = datos.get('fecha_elaboracion', '').replace('.', '-')
    fecha_venc = datos.get('fecha_vencimiento', '').replace('.', '-')
    lote = datos.get('lote_produccion', '')
    pallet = datos.get('numero_pallet', '')

    # Calcular cantidad de cajas (cartones)
    cantidad_cajas = datos.get('cantidad_cajas', 0)
    if not cantidad_cajas:
        peso_pallet = datos.get('peso_pallet_kg', 0)
        cantidad_cajas = max(int(peso_pallet / 10), 1) if peso_pallet else 1

    # Generar una etiqueta por cada cartón
    labels_html = ""
    for i in range(1, cantidad_cajas + 1):
        labels_html += f"""
        <div class="etiqueta">
            <div class="campo"><span class="label">MATERIAL CODE: </span><span class="valor">{codigo}</span></div>
            <div class="campo"><span class="label">PRODUCT NAME: </span><span class="valor">{nombre}</span></div>
            <div class="campo"><span class="label">NET WEIGHT: </span><span class="valor">10KG</span></div>
            <div class="campo"><span class="label">PRODUCTION DATE: </span><span class="valor">{fecha_elab}</span></div>
            <div class="campo"><span class="label">BEST BEFORE: </span><span class="valor">{fecha_venc}</span></div>
            <div class="campo"><span class="label">BATCH NO.: </span><span class="valor">{lote} / {pallet}</span></div>
            <div class="campo"><span class="label">STORAGE TEMPERATURE: </span><span class="valor">-18°C</span></div>
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
            }}
            .etiqueta {{
                width: 100mm;
                height: 100mm;
                padding: 5mm;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                justify-content: center;
                page-break-after: always;
                page-break-inside: avoid;
            }}
            .etiqueta:last-child {{
                page-break-after: auto;
            }}
            .campo {{
                font-size: 12px;
                margin: 2px 0;
                line-height: 1.5;
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


DISEÑOS_ETIQUETAS_CAJA = {
    "TRONADOR": generar_etiqueta_caja_tronador,
    "TRONADOR SAC": generar_etiqueta_caja_tronador,
    "LANNA": generar_etiqueta_caja_lanna,
    "LANNA AGRO": generar_etiqueta_caja_lanna,
    "LANNA AGRO INDUSTRY": generar_etiqueta_caja_lanna,
    "LACO": generar_etiqueta_caja_lanna,
}


def render_etiquetas_caja(username: str, password: str):
    """Renderiza etiquetas por caja — usa estado compartido."""
    
    pallets = st.session_state.etiq_pallets_cargados
    orden = st.session_state.etiq_orden_seleccionada
    cliente_nombre = orden.get('cliente_nombre', '')
    
    # Buscar diseño del cliente
    cliente_key = None
    for key in DISEÑOS_ETIQUETAS_CAJA.keys():
        if key.upper() in cliente_nombre.upper():
            cliente_key = key
            break
    
    if not cliente_key:
        st.error(f"❌ No hay diseño de etiqueta configurado para el cliente: {cliente_nombre}")
        st.info("Clientes con diseño disponible: " + ", ".join(DISEÑOS_ETIQUETAS_CAJA.keys()))
        return
    
    funcion_diseño = DISEÑOS_ETIQUETAS_CAJA[cliente_key]
    
    st.write(f"**{len(pallets)} pallets disponibles** — Diseño: {cliente_key}")
    
    for pallet in pallets:
        with st.expander(f"📦 {pallet.get('package_name', '')} - {pallet.get('cantidad_cajas', 0)} cajas"):
            codigo_prod, desc_prod = extraer_codigo_descripcion(pallet.get('producto_nombre', ''))
            lot_name = pallet.get('lot_name', '') or pallet.get('lote_produccion', '') or ''
            
            peso_caja = extraer_peso_de_descripcion(desc_prod)
            
            fecha_elab = pallet.get('fecha_elaboracion_fmt', '')
            fecha_venc = calcular_fecha_vencimiento(fecha_elab, años=2)
            
            datos_etiqueta = {
                'nombre_producto': desc_prod,
                'codigo_producto': codigo_prod,
                'peso_caja_kg': peso_caja,
                'fecha_elaboracion': fecha_elab,
                'fecha_vencimiento': fecha_venc,
                'lote_produccion': lot_name,
                'numero_pallet': pallet.get('package_name', ''),
                'cliente_nombre': cliente_nombre,
                'cantidad_cajas': int(pallet.get('cantidad_cajas', 0)),
                'peso_pallet_kg': int(pallet.get('peso_pallet_kg', 0)),
            }
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button("🖨️ Imprimir", key=f"etiq_caja_print_{pallet.get('package_id')}", use_container_width=True):
                    html_print = funcion_diseño(datos_etiqueta)
                    # Abrir en ventana nueva para que window.print() funcione fuera del iframe
                    import base64
                    html_bytes = html_print.encode('utf-8')
                    b64 = base64.b64encode(html_bytes).decode()
                    print_script = f'''
                    <script>
                        var win = window.open('', '_blank');
                        if (win) {{
                            win.document.write(atob("{b64}"));
                            win.document.close();
                            win.onload = function() {{
                                setTimeout(function() {{
                                    win.print();
                                }}, 500);
                            }};
                        }} else {{
                            alert("Permite ventanas emergentes para imprimir");
                        }}
                    </script>
                    '''
                    st.components.v1.html(print_script, height=0)
            
            with col2:
                if st.button("👁️ Vista", key=f"etiq_caja_preview_{pallet.get('package_id')}", use_container_width=True):
                    html_etiqueta = funcion_diseño(datos_etiqueta)
                    st.components.v1.html(html_etiqueta, height=450, scrolling=True)




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
            
            datos_etiqueta = {
                'cliente': cliente_pallet,
                'nombre_producto': descripcion_prod,
                'codigo_producto': codigo_prod,
                'peso_pallet_kg': int(pallet.get('peso_pallet_kg', 0)),
                'cantidad_cajas': int(pallet.get('cantidad_cajas', 0)),
                'fecha_elaboracion': pallet.get('fecha_elaboracion_fmt', ''),
                'fecha_vencimiento': pallet.get('fecha_vencimiento', ''),
                'lote_produccion': lot_name,
                'numero_pallet': pallet.get('package_name', ''),
                'barcode': barcode_odoo
            }
            
            with col2:
                if st.button("🖨️ Imprimir", key=f"etiq_print_{pallet.get('package_id')}", use_container_width=True):
                    html_print = generar_etiqueta_html(datos_etiqueta)
                    import base64
                    html_bytes = html_print.encode('utf-8')
                    b64 = base64.b64encode(html_bytes).decode()
                    print_script = f'''
                    <script>
                        var win = window.open('', '_blank');
                        if (win) {{
                            win.document.write(atob("{b64}"));
                            win.document.close();
                            win.onload = function() {{
                                setTimeout(function() {{
                                    win.print();
                                }}, 500);
                            }};
                        }} else {{
                            alert("Permite ventanas emergentes para imprimir");
                        }}
                    </script>
                    '''
                    st.components.v1.html(print_script, height=0)
            
            with col3:
                if st.button("👁️ Vista", key=f"etiq_preview_{pallet.get('package_id')}", use_container_width=True):
                    html_etiqueta = generar_etiqueta_html(datos_etiqueta)
                    st.components.v1.html(html_etiqueta, height=600, scrolling=True)
        
        st.divider()


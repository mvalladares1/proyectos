"""
Tab de Etiquetas de Pallets
Permite buscar órdenes de producción y generar etiquetas para cada pallet
"""
import streamlit as st
import httpx
from typing import List, Dict
from produccion.shared import API_URL


def obtener_clientes(username: str, password: str):
    """Obtiene lista de clientes desde Odoo."""
    params = {
        "username": username,
        "password": password
    }
    response = httpx.get(
        f"{API_URL}/api/v1/etiquetas/clientes",
        params=params,
        timeout=30.0
    )
    response.raise_for_status()
    return response.json()


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
    Genera HTML de etiqueta con el formato especificado.
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: 10cm 15cm;
                margin: 0.5cm;
            }}
            body {{
                font-family: Arial, sans-serif;
                padding: 10px;
                margin: 0;
            }}
            .etiqueta {{
                border: 2px solid black;
                padding: 15px;
                width: 9cm;
                min-height: 13cm;
            }}
            .titulo {{
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 15px;
                text-align: center;
            }}
            .campo {{
                font-size: 14px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .barcode-container {{
                text-align: center;
                margin-top: 20px;
            }}
            .barcode {{
                font-family: 'Libre Barcode 128', cursive;
                font-size: 48px;
                margin: 10px 0;
            }}
            .barcode-text {{
                font-size: 12px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="etiqueta">
            <div class="titulo">{datos.get('cliente', '')}</div>
            <div class="titulo">{datos.get('nombre_producto', '')}</div>
            
            <div class="campo">CODIGO PRODUCTO: {datos.get('codigo_producto', '')}</div>
            <div class="campo">PESO PALLET: {datos.get('peso_pallet_kg', 0)} KG</div>
            <div class="campo">CANTIDAD CAJAS: {datos.get('cantidad_cajas', 0)}</div>
            <div class="campo">FECHA ELABORACION: {datos.get('fecha_elaboracion', '')}</div>
            <div class="campo">FECHA VENCIMIENTO: {datos.get('fecha_vencimiento', '')}</div>
            <div class="campo">LOTE PRODUCCION: {datos.get('lote_produccion', '')}</div>
            <div class="campo">NUMERO DE PALLET: {datos.get('numero_pallet', '')}</div>
            
            <div class="barcode-container">
                <div class="barcode">*{datos.get('numero_pallet', '')}*</div>
                <div class="barcode-text">{datos.get('numero_pallet', '')}</div>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def render(username: str, password: str):
    """Renderiza el tab de etiquetas de pallets."""
    
    st.header("🏷️ Generación de Etiquetas de Pallets")
    
    # Inicializar estado
    if "etiq_orden_seleccionada" not in st.session_state:
        st.session_state.etiq_orden_seleccionada = None
    if "etiq_pallets_cargados" not in st.session_state:
        st.session_state.etiq_pallets_cargados = []
    if "etiq_cliente_nombre" not in st.session_state:
        st.session_state.etiq_cliente_nombre = ""
    if "etiq_ordenes_encontradas" not in st.session_state:
        st.session_state.etiq_ordenes_encontradas = []
    
    # ==================== PASO 1: SELECCIONAR CLIENTE ====================
    st.subheader("1️⃣ Cliente")
    
    # Cargar clientes
    if "etiq_clientes_list" not in st.session_state:
        with st.spinner("Cargando clientes..."):
            try:
                clientes = obtener_clientes(username, password)
                st.session_state.etiq_clientes_list = clientes
            except Exception as e:
                st.error(f"Error cargando clientes: {e}")
                st.session_state.etiq_clientes_list = []
    
    clientes_options = [""] + [c.get('name', '') for c in st.session_state.etiq_clientes_list]
    
    cliente_seleccionado = st.selectbox(
        "Seleccionar Cliente",
        options=clientes_options,
        index=0,
        help="Selecciona el cliente para las etiquetas",
        key="etiq_cliente_selectbox"
    )
    
    if cliente_seleccionado:
        st.session_state.etiq_cliente_nombre = cliente_seleccionado
    
    # ==================== PASO 2: BUSCAR ORDEN ====================
    st.subheader("2️⃣ Buscar Orden de Producción")
    
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
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**{orden.get('name')}**")
                st.caption(f"Producto: {orden.get('product_id', ['', ''])[1] if isinstance(orden.get('product_id'), list) else ''}")
            
            with col2:
                st.write(f"Estado: {orden.get('state', '')}")
                if orden.get('origin'):
                    st.caption(f"Origen: {orden.get('origin')}")
            
            with col3:
                if st.button("Seleccionar", key=f"etiq_sel_{orden.get('id')}", use_container_width=True):
                    st.session_state.etiq_orden_seleccionada = orden
                    # Auto-cargar pallets al seleccionar
                    with st.spinner("Cargando pallets..."):
                        try:
                            pallets = obtener_pallets_orden(username, password, orden.get('name'))
                            st.session_state.etiq_pallets_cargados = pallets
                            if pallets:
                                st.success(f"✅ Se cargaron {len(pallets)} pallets")
                            else:
                                st.warning("⚠️ No se encontraron pallets")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
                    st.rerun()
    
    # ==================== PASO 3: ORDEN SELECCIONADA ====================
    if st.session_state.etiq_orden_seleccionada:
        orden = st.session_state.etiq_orden_seleccionada
        
        st.divider()
        st.subheader("3️⃣ Orden Seleccionada")
        st.info(f"📦 **{orden.get('name')}** - {orden.get('product_id', ['', ''])[1] if isinstance(orden.get('product_id'), list) else ''}")
        
        if st.button("❌ Cambiar Orden", use_container_width=False, key="etiq_btn_cambiar"):
            st.session_state.etiq_orden_seleccionada = None
            st.session_state.etiq_pallets_cargados = []
            st.session_state.etiq_ordenes_encontradas = []
            st.rerun()
    
    # ==================== PASO 4: MOSTRAR PALLETS Y GENERAR ETIQUETAS ====================
    if st.session_state.etiq_pallets_cargados:
        st.subheader("4️⃣ Etiquetas Disponibles")
        
        if not st.session_state.etiq_cliente_nombre:
            st.warning("⚠️ Por favor ingresa el nombre del cliente arriba")
        
        st.write(f"**Total de pallets:** {len(st.session_state.etiq_pallets_cargados)}")
        
        # Botón para generar todas las etiquetas
        if st.button("📥 Descargar Todas las Etiquetas (PDF)", type="primary", key="etiq_btn_descargar_todas"):
            st.info("🚧 Generación de PDF múltiple - Próximamente")
        
        st.divider()
        
        # Mostrar cada pallet
        for idx, pallet in enumerate(st.session_state.etiq_pallets_cargados, 1):
            with st.expander(f"**Pallet {idx}: {pallet.get('package_name', 'Sin nombre')}**", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Número Pallet:** {pallet.get('package_name', '')}")
                    product_id = pallet.get('product_id')
                    if product_id:
                        product_name = product_id[1] if isinstance(product_id, list) else str(product_id)
                        st.write(f"**Producto:** {product_name}")
                
                with col2:
                    st.write(f"**Peso Total:** {pallet.get('peso_pallet_kg', 0)} KG")
                    st.write(f"**Cantidad Cajas:** {pallet.get('cantidad_cajas', 0)}")
                
                with col3:
                    lot_id = pallet.get('lot_id')
                    if lot_id:
                        lot_name = lot_id[1] if isinstance(lot_id, list) else str(lot_id)
                        st.write(f"**Lote:** {lot_name}")
                    st.write(f"**Fecha:** {pallet.get('fecha_elaboracion_fmt', '')}")
                
                # Botón para vista previa de etiqueta individual
                if st.button(f"👁️ Vista Previa Etiqueta", key=f"etiq_prev_{idx}"):
                    # Preparar datos para la etiqueta
                    product_id = pallet.get('product_id')
                    product_name = product_id[1] if isinstance(product_id, (list, tuple)) else 'Producto desconocido'
                    
                    lot_id = pallet.get('lot_id')
                    lot_name = lot_id[1] if isinstance(lot_id, (list, tuple)) and lot_id else 'Sin lote'
                    
                    datos_etiqueta = {
                        'cliente': st.session_state.etiq_cliente_nombre,
                        'nombre_producto': product_name,
                        'codigo_producto': '',  # TODO: Obtener desde product_id
                        'peso_pallet_kg': int(pallet.get('peso_pallet_kg', 0)),
                        'cantidad_cajas': int(pallet.get('cantidad_cajas', 0)),
                        'fecha_elaboracion': pallet.get('fecha_elaboracion_fmt', ''),
                        'fecha_vencimiento': pallet.get('fecha_vencimiento', ''),
                        'lote_produccion': lot_name,
                        'numero_pallet': pallet.get('package_name', '')
                    }
                    
                    # Generar HTML
                    html_etiqueta = generar_etiqueta_html(datos_etiqueta)
                    
                    # Mostrar vista previa
                    st.components.v1.html(html_etiqueta, height=600, scrolling=True)
    
    else:
        if st.session_state.etiq_orden_seleccionada:
            st.info("👆 Haz clic en 'Cargar Pallets' para ver los pallets de esta orden")

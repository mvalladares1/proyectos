"""
Tab de Etiquetas (Pallets y Cajas) - ZPL para impresoras Zebra 203 dpi
Permite buscar ordenes de produccion y generar etiquetas ZPL para cada pallet o caja.
Cliente se obtiene automaticamente desde x_studio_clientes de la orden.
Resolucion: 203 dpi (8 dots/mm). Conexion: USB.
"""
import streamlit as st
import httpx
import re
import time
from typing import List, Dict
from .shared import API_URL


# ==================== HELPERS ====================

def _throttle_rerun(key: str = "etiq", min_interval: float = 1.0) -> bool:
    now = time.time()
    last_key = f"_throttle_last_{key}"
    last_time = st.session_state.get(last_key, 0)
    if now - last_time < min_interval:
        return False
    st.session_state[last_key] = now
    return True


def _zpl_safe(text) -> str:
    """Limpia texto para ZPL (ASCII sin acentos ni caracteres especiales)."""
    if not text:
        return ''
    text = str(text)
    repl = {
        '\u00e1': 'a', '\u00e9': 'e', '\u00ed': 'i', '\u00f3': 'o', '\u00fa': 'u',
        '\u00c1': 'A', '\u00c9': 'E', '\u00cd': 'I', '\u00d3': 'O', '\u00da': 'U',
        '\u00f1': 'n', '\u00d1': 'N', '\u00b0': 'o', '\u2013': '-', '\u2014': '-',
        '^': '', '~': '-',
    }
    for k, v in repl.items():
        text = text.replace(k, v)
    return text


def extraer_codigo_descripcion(nombre_producto: str) -> tuple:
    """Extrae codigo y descripcion: '[402122000] FB MK Conv...' -> ('402122000', 'FB MK Conv...')"""
    match = re.match(r'\[(\d+)\]\s*(.+)', nombre_producto)
    if match:
        return match.group(1), match.group(2)
    return '', nombre_producto


def extraer_peso_de_descripcion(descripcion: str) -> str:
    """Extrae peso en kg de la descripcion del producto."""
    match = re.search(r'(\d+[.,]\d+)\s*kg', descripcion, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r'(\d+)\s*kg', descripcion, re.IGNORECASE)
    if match:
        return match.group(1)
    return "10"


def calcular_fecha_vencimiento(fecha_elaboracion: str, years: int = 2) -> str:
    """Calcula fecha vencimiento sumando anios. Formato: DD.MM.YYYY"""
    from datetime import datetime
    try:
        for fmt in ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d']:
            try:
                fecha = datetime.strptime(fecha_elaboracion, fmt)
                return fecha.replace(year=fecha.year + years).strftime('%d.%m.%Y')
            except ValueError:
                continue
        return fecha_elaboracion
    except Exception:
        return fecha_elaboracion


def _get_lot_name(pallet: Dict) -> str:
    """Extrae nombre de lote del pallet."""
    lot_name = pallet.get('lot_name', '') or pallet.get('lote_produccion', '') or ''
    if not lot_name:
        lot_id = pallet.get('lot_id')
        lot_name = lot_id[1] if isinstance(lot_id, (list, tuple)) and lot_id else ''
    return lot_name


def _agrupar_pallets_por_producto(pallets: List[Dict]) -> Dict:
    """Agrupa pallets por product_id."""
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


# ==================== API ====================

def buscar_ordenes(username: str, password: str, termino: str):
    """Busca ordenes de produccion."""
    params = {"username": username, "password": password, "termino": termino}
    response = httpx.get(
        f"{API_URL}/api/v1/etiquetas/buscar_ordenes",
        params=params, timeout=30.0
    )
    response.raise_for_status()
    return response.json()


def obtener_pallets_orden(username: str, password: str, orden_name: str):
    """Obtiene pallets de una orden."""
    params = {"username": username, "password": password, "orden_name": orden_name}
    response = httpx.get(
        f"{API_URL}/api/v1/etiquetas/pallets_orden",
        params=params, timeout=60.0
    )
    response.raise_for_status()
    return response.json()


# ==================== ZPL GENERATORS (203 dpi = 8 dots/mm) ====================
# Tamanos: 100x150mm (800x1200), 100x100mm (800x800), 100x50mm (800x400)

def generar_tarja_zpl(datos: Dict) -> str:
    """
    Tarja por Pallet 100x150mm con codigo de barras CODE128.
    Campos: producto, codigo, peso, cajas, fechas, lote, pallet, barcode.
    """
    nombre = _zpl_safe(datos.get('nombre_producto', ''))
    codigo = _zpl_safe(datos.get('codigo_producto', ''))
    peso = datos.get('peso_pallet_kg', 0)
    cajas = datos.get('cantidad_cajas', 0)
    fecha_elab = _zpl_safe(datos.get('fecha_elaboracion', ''))
    fecha_venc = _zpl_safe(datos.get('fecha_vencimiento', ''))
    lote = _zpl_safe(datos.get('lote_produccion', ''))
    pallet = _zpl_safe(datos.get('numero_pallet', ''))
    barcode = _zpl_safe(datos.get('barcode', pallet))

    return (
        "^XA\n"
        "^PW800\n"
        "^LL1200\n"
        f"^FO30,30^A0N,40,32^FB740,2,0,C^FD{nombre}^FS\n"
        "^FO30,110^GB740,3,3^FS\n"
        f"^FO30,140^A0N,28,24^FDCODIGO PRODUCTO:^FS\n"
        f"^FO400,140^A0N,28,24^FD{codigo}^FS\n"
        f"^FO30,190^A0N,28,24^FDPESO PALLET:^FS\n"
        f"^FO400,190^A0N,28,24^FD{peso} KG^FS\n"
        f"^FO30,240^A0N,28,24^FDCANTIDAD CAJAS:^FS\n"
        f"^FO400,240^A0N,28,24^FD{cajas}^FS\n"
        f"^FO30,290^A0N,28,24^FDFECHA ELABORACION:^FS\n"
        f"^FO400,290^A0N,28,24^FD{fecha_elab}^FS\n"
        f"^FO30,340^A0N,28,24^FDFECHA VENCIMIENTO:^FS\n"
        f"^FO400,340^A0N,28,24^FD{fecha_venc}^FS\n"
        f"^FO30,390^A0N,28,24^FDLOTE PRODUCCION:^FS\n"
        f"^FO400,390^A0N,28,24^FD{lote}^FS\n"
        f"^FO30,440^A0N,28,24^FDNUMERO DE PALLET:^FS\n"
        f"^FO400,440^A0N,28,24^FD{pallet}^FS\n"
        "^FO30,500^GB740,3,3^FS\n"
        f"^FO100,540^BY3,2,120^BCN,,Y,N^FD{barcode}^FS\n"
        "^XZ\n"
    )


def generar_etiqueta_generica_zpl(datos: Dict) -> str:
    """
    Etiqueta generica subproductos 100x50mm.
    PSP, Whole, Broken, W&B, Desecho, Jugo.
    Info planta + SAG.
    """
    nombre = _zpl_safe(datos.get('nombre_producto', ''))
    fecha_elab = _zpl_safe(datos.get('fecha_elaboracion', ''))
    fecha_venc = _zpl_safe(datos.get('fecha_vencimiento', ''))
    lote = _zpl_safe(datos.get('lote_produccion', ''))
    pallet = _zpl_safe(datos.get('numero_pallet', ''))
    peso = _zpl_safe(str(datos.get('peso_neto_kg', '10')))

    return (
        "^XA\n"
        "^PW800\n"
        "^LL400\n"
        f"^FO20,10^A0N,26,22^FB760,2,0,C^FD{nombre}^FS\n"
        "^FO20,55^GB760,2,2^FS\n"
        f"^FO20,65^A0N,18,16^FDFecha elab: {fecha_elab} / Venc: {fecha_venc}^FS\n"
        f"^FO20,90^A0N,18,16^FDLote: {lote} / Pallet: {pallet}^FS\n"
        f"^FO20,115^A0N,18,16^FDPeso Neto: {peso} kg^FS\n"
        "^FO20,145^A0N,18,16^FDPRODUCTO CONGELADO^FS\n"
        "^FO20,175^A0N,16,14^FDPlanta: Rio Futuro Procesos Spa^FS\n"
        "^FO20,197^A0N,16,14^FDCamino Contra Coronel Lote 4, Cocule, Rio Bueno, Chile^FS\n"
        "^FO20,219^A0N,16,14^FDRes Servicio Salud Valdivia Dpto. del Ambiente^FS\n"
        "^FO20,241^A0N,16,14^FDXIV Region, No 2214585504 del 30-11-2022^FS\n"
        "^FO20,263^A0N,16,14^FDCodigo SAG Planta: 105721^FS\n"
        "^XZ\n"
    )


def generar_etiqueta_tronador_zpl(datos: Dict) -> str:
    """
    Etiqueta caja TRONADOR SAC 100x100mm.
    Info completa + checkbox MD marcado.
    """
    nombre = _zpl_safe(datos.get('nombre_producto', ''))
    fecha_elab = _zpl_safe(datos.get('fecha_elaboracion', ''))
    fecha_venc = _zpl_safe(datos.get('fecha_vencimiento', ''))
    lote = _zpl_safe(datos.get('lote_produccion', ''))
    pallet = _zpl_safe(datos.get('numero_pallet', ''))
    peso = _zpl_safe(str(datos.get('peso_caja_kg', 10)))

    return (
        "^XA\n"
        "^PW800\n"
        "^LL800\n"
        f"^FO30,20^A0N,34,28^FB740,2,0,C^FD{nombre}^FS\n"
        "^FO30,85^GB740,2,2^FS\n"
        f"^FO30,100^A0N,24,20^FDFecha de elaboracion: {fecha_elab}^FS\n"
        f"^FO30,132^A0N,24,20^FDFecha de vencimiento: {fecha_venc}^FS\n"
        f"^FO30,164^A0N,24,20^FDLote: {lote}^FS\n"
        f"^FO30,196^A0N,24,20^FDPallet: {pallet}^FS\n"
        f"^FO30,228^A0N,24,20^FDPeso Neto: {peso} kg^FS\n"
        "^FO30,268^A0N,24,20^FDPRODUCTO CONGELADO^FS\n"
        "^FO30,306^A0N,20,18^FDPlanta Cocule: Rio Futuro Procesos Spa^FS\n"
        "^FO30,332^A0N,20,18^FDCamino Contra Coronel Lote 4, Cocule, Rio Bueno, Chile^FS\n"
        "^FO30,358^A0N,20,18^FDRes Servicio Salud Valdivia Dpto. del Ambiente^FS\n"
        "^FO30,384^A0N,20,18^FDXIV Region, No 2214585504 del 30-11-2022^FS\n"
        "^FO30,410^A0N,20,18^FDCodigo SAG Planta: 105721^FS\n"
        "^FO30,455^A0N,26,22^FDMD^FS\n"
        "^FO80,450^GB32,32,2^FS\n"
        "^FO87,455^A0N,22,18^FDX^FS\n"
        "^XZ\n"
    )


def generar_etiqueta_lanna_zpl(datos: Dict) -> str:
    """
    Etiqueta caja LANNA AGRO / LACO 100x100mm.
    Genera N etiquetas (una por carton) con CARTON NO enumerado.
    """
    codigo = _zpl_safe(datos.get('codigo_producto', ''))
    nombre = _zpl_safe(datos.get('nombre_producto', ''))
    fecha_elab = _zpl_safe(datos.get('fecha_elaboracion', '').replace('.', '-'))
    fecha_venc = _zpl_safe(datos.get('fecha_vencimiento', '').replace('.', '-'))
    lote = _zpl_safe(datos.get('lote_produccion', ''))
    pallet = _zpl_safe(datos.get('numero_pallet', ''))

    cantidad = datos.get('cantidad_cajas', 0)
    if not cantidad:
        peso_pallet = datos.get('peso_pallet_kg', 0)
        cantidad = max(int(peso_pallet / 10), 1) if peso_pallet else 1

    labels = []
    for i in range(1, cantidad + 1):
        labels.append(
            "^XA\n"
            "^PW800\n"
            "^LL800\n"
            f"^FO30,40^A0N,24,20^FDMATERIAL CODE:^FS\n"
            f"^FO300,40^A0N,24,22^FD{codigo}^FS\n"
            f"^FO30,80^A0N,24,20^FDPRODUCT NAME:^FS\n"
            f"^FO300,80^A0N,24,22^FD{nombre}^FS\n"
            f"^FO30,120^A0N,24,20^FDNET WEIGHT:^FS\n"
            f"^FO300,120^A0N,24,22^FD10KG^FS\n"
            f"^FO30,160^A0N,24,20^FDPRODUCTION DATE:^FS\n"
            f"^FO300,160^A0N,24,22^FD{fecha_elab}^FS\n"
            f"^FO30,200^A0N,24,20^FDBEST BEFORE:^FS\n"
            f"^FO300,200^A0N,24,22^FD{fecha_venc}^FS\n"
            f"^FO30,240^A0N,24,20^FDBATCH NO.:^FS\n"
            f"^FO300,240^A0N,24,22^FD{lote} / {pallet}^FS\n"
            f"^FO30,280^A0N,24,20^FDSTORAGE TEMPERATURE:^FS\n"
            f"^FO300,280^A0N,24,22^FD-18C^FS\n"
            f"^FO30,320^A0N,24,20^FDORIGIN:^FS\n"
            f"^FO300,320^A0N,24,22^FDCHILE^FS\n"
            f"^FO30,370^A0N,28,24^FDCARTON NO.:^FS\n"
            f"^FO300,370^A0N,28,24^FD{i}^FS\n"
            f"^FO30,420^A0N,28,24^FDPRODUCT FOR LACO^FS\n"
            "^XZ\n"
        )

    return "\n".join(labels)


# Mapa de cliente -> funcion generadora ZPL
DISENOS_ETIQUETAS_CAJA = {
    "TRONADOR": generar_etiqueta_tronador_zpl,
    "TRONADOR SAC": generar_etiqueta_tronador_zpl,
    "LANNA": generar_etiqueta_lanna_zpl,
    "LANNA AGRO": generar_etiqueta_lanna_zpl,
    "LANNA AGRO INDUSTRY": generar_etiqueta_lanna_zpl,
    "LACO": generar_etiqueta_lanna_zpl,
}


# ==================== UI: PREVIEW + DOWNLOAD ZPL ====================

def mostrar_etiqueta_zpl(zpl_code: str, label_size: str = "4x6",
                         filename: str = "etiqueta.zpl", unique_key: str = ""):
    """
    Muestra preview de la etiqueta (via Labelary API), boton de descarga .zpl
    y codigo raw en un expander.
    label_size: 'WxH' en pulgadas para Labelary (4x6, 4x4, 4x2).
    """
    col_prev, col_dl = st.columns([2, 1])

    with col_prev:
        try:
            # Solo previsualizar el primer label (^XA...^XZ)
            first_label = zpl_code
            idx = zpl_code.find("^XZ")
            if idx > 0:
                first_label = zpl_code[:idx + 3]

            url = f"https://api.labelary.com/v1/printers/8dpmm/labels/{label_size}/0/"
            resp = httpx.post(
                url,
                content=first_label.encode('utf-8'),
                headers={"Accept": "image/png"},
                timeout=15,
            )
            if resp.status_code == 200:
                st.image(resp.content, caption="Vista previa ZPL", use_container_width=True)
            else:
                st.warning("No se pudo generar vista previa")
                st.code(first_label[:400], language=None)
        except Exception:
            st.info("Sin conexion a Labelary para preview")
            st.code(zpl_code[:400], language=None)

    with col_dl:
        st.download_button(
            label="\u2b07\ufe0f Descargar .ZPL",
            data=zpl_code,
            file_name=filename,
            mime="application/octet-stream",
            key=f"dl_{unique_key}",
            use_container_width=True,
        )

        # Contar etiquetas en el archivo
        n_labels = zpl_code.count("^XZ")
        if n_labels > 1:
            st.caption(f"\U0001f4c4 {n_labels} etiquetas en el archivo")

        st.markdown("---")
        st.caption("**Enviar a Zebra (USB):**")
        st.code(f'copy /b "{filename}" \\\\%COMPUTERNAME%\\Zebra', language="bat")

    with st.expander("\U0001f4cb Ver codigo ZPL"):
        st.code(zpl_code, language=None)


# ==================== RENDER FUNCTIONS ====================

def render(username: str, password: str):
    """Renderiza el tab de etiquetas."""

    st.header("\U0001f3f7\ufe0f Generacion de Etiquetas")
    st.caption("Formato ZPL para impresoras Zebra (203 dpi)")

    # Estado compartido
    for key, default in [
        ("etiq_orden_seleccionada", None),
        ("etiq_pallets_cargados", []),
        ("etiq_ordenes_encontradas", []),
        ("etiq_pallets_carga_intentada", False),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # ==================== PASO 1: BUSCAR ORDEN ====================
    st.subheader("1\ufe0f\u20e3 Buscar Orden de Produccion")

    col1, col2 = st.columns([3, 1])
    with col1:
        termino_busqueda = st.text_input(
            "Buscar orden",
            placeholder="Ej: WH/MO/12345",
            help="Ingresa el nombre o referencia de la orden",
            key="etiq_termino_busqueda",
        )
    with col2:
        btn_buscar = st.button(
            "\U0001f50d Buscar", type="primary",
            use_container_width=True, key="etiq_btn_buscar",
        )

    if btn_buscar and termino_busqueda:
        with st.spinner("Buscando ordenes..."):
            try:
                ordenes = buscar_ordenes(username, password, termino_busqueda)
                st.session_state.etiq_ordenes_encontradas = ordenes
                if ordenes:
                    st.success(f"\u2705 {len(ordenes)} ordenes encontradas")
                else:
                    st.warning("\u26a0\ufe0f No se encontraron ordenes")
            except Exception as e:
                st.error(f"\u274c Error: {e}")
                st.session_state.etiq_ordenes_encontradas = []

    # Mostrar ordenes encontradas
    if st.session_state.etiq_ordenes_encontradas:
        st.write("**Ordenes encontradas:**")
        for orden in st.session_state.etiq_ordenes_encontradas:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{orden.get('name', '')}**")
                pname = (
                    orden.get('product_id', ['', ''])[1]
                    if isinstance(orden.get('product_id'), list)
                    else orden.get('product_name', '')
                )
                st.caption(f"Producto: {pname}")
            with col2:
                st.write(f"Estado: {orden.get('state', '')}")
                cli = orden.get('cliente_nombre', '')
                if cli:
                    st.caption(f"\U0001f464 Cliente: {cli}")
            with col3:
                if st.button("Seleccionar", key=f"etiq_sel_{orden.get('id')}",
                             use_container_width=True):
                    st.session_state.etiq_orden_seleccionada = orden
                    st.session_state.etiq_pallets_cargados = []
                    st.session_state.etiq_pallets_carga_intentada = False
                    try:
                        pallets = obtener_pallets_orden(
                            username, password, orden.get('name')
                        )
                        st.session_state.etiq_pallets_cargados = pallets
                        st.session_state.etiq_pallets_carga_intentada = True
                    except Exception:
                        st.session_state.etiq_pallets_carga_intentada = True
                    if _throttle_rerun("etiq_select"):
                        st.rerun()

    # ==================== PASO 2: ORDEN SELECCIONADA ====================
    if st.session_state.etiq_orden_seleccionada:
        orden = st.session_state.etiq_orden_seleccionada
        product_name = (
            orden.get('product_id', ['', ''])[1]
            if isinstance(orden.get('product_id'), list)
            else orden.get('product_name', '')
        )
        cliente_nombre = orden.get('cliente_nombre', '')

        st.divider()
        st.subheader("2\ufe0f\u20e3 Orden Seleccionada")
        st.info(f"\U0001f4e6 **{orden.get('name')}** \u2014 {product_name}")
        if cliente_nombre:
            st.success(f"\U0001f464 Cliente: **{cliente_nombre}**")

        pallets = st.session_state.etiq_pallets_cargados
        if pallets:
            st.write(f"\u2705 **{len(pallets)} pallets cargados**")
        elif st.session_state.etiq_pallets_carga_intentada:
            st.warning("\u26a0\ufe0f No se encontraron pallets para esta orden")
        else:
            with st.spinner("Cargando pallets..."):
                try:
                    pallets = obtener_pallets_orden(
                        username, password, orden.get('name')
                    )
                    st.session_state.etiq_pallets_cargados = pallets
                    st.session_state.etiq_pallets_carga_intentada = True
                    if pallets and _throttle_rerun("etiq_load"):
                        st.rerun()
                    elif not pallets:
                        st.warning("\u26a0\ufe0f No se encontraron pallets")
                except Exception as e:
                    st.session_state.etiq_pallets_carga_intentada = True
                    st.error(f"\u274c Error al cargar pallets: {e}")

        if st.button("\u274c Cambiar Orden", use_container_width=False,
                     key="etiq_btn_cambiar"):
            st.session_state.etiq_orden_seleccionada = None
            st.session_state.etiq_pallets_cargados = []
            st.session_state.etiq_ordenes_encontradas = []
            st.session_state.etiq_pallets_carga_intentada = False
            if _throttle_rerun("etiq_cambiar"):
                st.rerun()

        # ==================== PASO 3: ETIQUETAS ====================
        if st.session_state.etiq_pallets_cargados:
            st.divider()

            _SUBPRODUCTO_KEYWORDS = [
                'PSP', 'Whole', 'Broken', 'W&B', 'Desecho', 'Jugo',
            ]
            pallets_iqf, pallets_sub = [], []
            for p in st.session_state.etiq_pallets_cargados:
                pid = p.get('product_id')
                pname = pid[1] if isinstance(pid, list) else str(pid or '')
                _, desc = extraer_codigo_descripcion(pname)
                if any(kw.upper() in desc.upper() for kw in _SUBPRODUCTO_KEYWORDS):
                    pallets_sub.append(p)
                else:
                    pallets_iqf.append(p)

            tipo_etiqueta = st.radio(
                "Tipo de etiqueta",
                ["\U0001f4e6 Tarja por Pallet", "\U0001f3f7\ufe0f Etiquetas por Caja"],
                horizontal=True,
                key="etiq_tipo",
            )
            st.divider()

            if tipo_etiqueta == "\U0001f4e6 Tarja por Pallet":
                render_etiquetas_pallet(username, password)
            else:
                if pallets_iqf:
                    render_seccion_iqf(username, password, pallets_iqf)
                if pallets_sub:
                    render_seccion_subproductos(username, password, pallets_sub)
                if not pallets_iqf and not pallets_sub:
                    st.warning("No se encontraron pallets para generar etiquetas.")


def render_seccion_iqf(username: str, password: str, pallets_iqf: List[Dict]):
    """Seccion ETIQUETAS CLIENTES (IQF) - etiquetas por caja con diseno de cliente."""

    orden = st.session_state.etiq_orden_seleccionada
    cliente_nombre = orden.get('cliente_nombre', '')

    st.subheader("\U0001f4cb ETIQUETAS CLIENTES (IQF)")

    # Buscar diseno del cliente
    cliente_key = None
    for key in DISENOS_ETIQUETAS_CAJA:
        if key.upper() in cliente_nombre.upper():
            cliente_key = key
            break

    if not cliente_key:
        st.warning(
            f"\u26a0\ufe0f No hay diseno para: **{cliente_nombre or '(sin cliente)'}**"
        )
        st.info(
            "Clientes disponibles: "
            + ", ".join(sorted(set(DISENOS_ETIQUETAS_CAJA.keys())))
        )
        render_seccion_subproductos(
            username, password, pallets_iqf,
            titulo="\U0001f4cb IQF (Etiqueta Generica)",
        )
        return

    funcion_diseno = DISENOS_ETIQUETAS_CAJA[cliente_key]
    grupos = _agrupar_pallets_por_producto(pallets_iqf)

    for pkey, grupo in grupos.items():
        desc = grupo['descripcion']
        pallets = grupo['pallets']
        st.markdown(f"#### \U0001f4e6 {desc}")
        st.caption(f"{len(pallets)} pallets \u2014 Diseno: {cliente_key}")

        for pallet in pallets:
            pkg_name = pallet.get('package_name', '')
            n_cajas = pallet.get('cantidad_cajas', 0)
            with st.expander(f"{pkg_name} \u2014 {n_cajas} cajas"):
                lot_name = _get_lot_name(pallet)
                fecha_elab = pallet.get('fecha_elaboracion_fmt', '')
                fecha_venc = calcular_fecha_vencimiento(fecha_elab, years=2)

                datos = {
                    'nombre_producto': desc,
                    'codigo_producto': grupo['codigo'],
                    'peso_caja_kg': extraer_peso_de_descripcion(desc),
                    'fecha_elaboracion': fecha_elab,
                    'fecha_vencimiento': fecha_venc,
                    'lote_produccion': lot_name,
                    'numero_pallet': pkg_name,
                    'cliente_nombre': cliente_nombre,
                    'cantidad_cajas': int(n_cajas),
                    'peso_pallet_kg': int(pallet.get('peso_pallet_kg', 0)),
                }
                zpl = funcion_diseno(datos)
                mostrar_etiqueta_zpl(
                    zpl, "4x4",
                    f"{pkg_name}_caja.zpl",
                    f"iqf_{pallet.get('package_id')}",
                )
    st.divider()


def render_seccion_subproductos(username: str, password: str,
                                 pallets_sub: List[Dict],
                                 titulo: str = "\U0001f4cb ETIQUETAS SUBPRODUCTOS"):
    """Seccion subproductos - etiqueta generica 100x50mm."""

    st.subheader(titulo)
    grupos = _agrupar_pallets_por_producto(pallets_sub)

    for pkey, grupo in grupos.items():
        desc = grupo['descripcion']
        peso_neto = extraer_peso_de_descripcion(desc)
        pallets = grupo['pallets']

        st.markdown(f"#### \U0001f4e6 {desc}")
        st.caption(f"{len(pallets)} pallets \u2014 Etiqueta generica 100\u00d750mm")

        for pallet in pallets:
            pkg_name = pallet.get('package_name', '')
            n_cajas = pallet.get('cantidad_cajas', 0)
            with st.expander(f"{pkg_name} \u2014 {n_cajas} cajas"):
                lot_name = _get_lot_name(pallet)
                fecha_elab = pallet.get('fecha_elaboracion_fmt', '')
                fecha_venc = calcular_fecha_vencimiento(fecha_elab, years=2)

                datos = {
                    'nombre_producto': desc,
                    'peso_neto_kg': peso_neto,
                    'fecha_elaboracion': fecha_elab,
                    'fecha_vencimiento': fecha_venc,
                    'lote_produccion': lot_name,
                    'numero_pallet': pkg_name,
                }
                zpl = generar_etiqueta_generica_zpl(datos)
                mostrar_etiqueta_zpl(
                    zpl, "4x2",
                    f"{pkg_name}_sub.zpl",
                    f"sub_{pallet.get('package_id')}",
                )
    st.divider()


def render_etiquetas_pallet(username: str, password: str):
    """Tarjas por pallet - etiqueta grande 100x150mm con codigo de barras."""

    st.write(
        f"**Total de pallets:** {len(st.session_state.etiq_pallets_cargados)}"
    )
    vista_opcion = st.radio(
        "Mostrar:",
        ["\U0001f195 Solo ultimo pallet", "\U0001f4cb Todos los pallets"],
        horizontal=True,
        key="etiq_vista_opcion",
    )
    st.divider()

    # Agrupar por producto
    pallets_por_producto = {}
    for pallet in st.session_state.etiq_pallets_cargados:
        product_id = pallet.get('product_id')
        if product_id:
            pkey = product_id[0] if isinstance(product_id, list) else product_id
            pname = product_id[1] if isinstance(product_id, list) else str(product_id)
            codigo, descripcion = extraer_codigo_descripcion(pname)
            if pkey not in pallets_por_producto:
                pallets_por_producto[pkey] = {
                    'nombre': pname,
                    'codigo': codigo,
                    'descripcion': descripcion,
                    'pallets': [],
                }
            pallets_por_producto[pkey]['pallets'].append(pallet)

    if vista_opcion == "\U0001f195 Solo ultimo pallet":
        for pk in pallets_por_producto:
            pallets_por_producto[pk]['pallets'] = [
                pallets_por_producto[pk]['pallets'][-1]
            ]

    for product_key, prod_data in pallets_por_producto.items():
        st.markdown(f"### \U0001f4e6 {prod_data['descripcion']}")
        n = len(prod_data['pallets'])
        st.caption(
            "Ultimo pallet"
            if vista_opcion == "\U0001f195 Solo ultimo pallet"
            else f"{n} pallets"
        )

        for pallet in prod_data['pallets']:
            pkg_name = pallet.get('package_name', 'Sin nombre')
            with st.expander(f"\U0001f3f7\ufe0f {pkg_name}"):
                product_id = pallet.get('product_id')
                product_name = (
                    product_id[1]
                    if isinstance(product_id, (list, tuple))
                    else 'Producto desconocido'
                )
                codigo_prod, descripcion_prod = extraer_codigo_descripcion(
                    product_name
                )
                lot_id = pallet.get('lot_id')
                lot_name = (
                    lot_id[1]
                    if isinstance(lot_id, (list, tuple)) and lot_id
                    else 'Sin lote'
                )
                barcode_odoo = pallet.get('barcode', pkg_name)

                datos = {
                    'nombre_producto': descripcion_prod,
                    'codigo_producto': codigo_prod,
                    'peso_pallet_kg': int(pallet.get('peso_pallet_kg', 0)),
                    'cantidad_cajas': int(pallet.get('cantidad_cajas', 0)),
                    'fecha_elaboracion': pallet.get('fecha_elaboracion_fmt', ''),
                    'fecha_vencimiento': pallet.get('fecha_vencimiento', ''),
                    'lote_produccion': lot_name,
                    'numero_pallet': pkg_name,
                    'barcode': barcode_odoo,
                }
                zpl = generar_tarja_zpl(datos)
                mostrar_etiqueta_zpl(
                    zpl, "4x6",
                    f"{pkg_name}_tarja.zpl",
                    f"tarja_{pallet.get('package_id')}",
                )
        st.divider()


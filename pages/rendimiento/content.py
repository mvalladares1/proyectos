"""
Contenido principal del dashboard de Trazabilidad.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared.auth import tiene_acceso_pagina

from .shared import (
    fmt_numero,
    get_trazabilidad_inversa,
    get_sankey_data,
    get_reactflow_data,
    get_traceability_raw,
    get_traceability_by_identifier,
    get_container_partners,
    get_sankey_producers
)

# Importar componente Timeline Flow
try:
    from components.timeline_flow import render_timeline_flow, render_simple_flow
    from components.timeline_flow.component import FLOW_AVAILABLE
    TIMELINE_FLOW_AVAILABLE = FLOW_AVAILABLE
except ImportError:
    TIMELINE_FLOW_AVAILABLE = False
    render_timeline_flow = None
    render_simple_flow = None

# Importar componente vis.js Network
try:
    from components.visjs_network import (
        render_visjs_network,
        render_visjs_timeline,
        render_combined_view,
        PYVIS_AVAILABLE,
    )
    VISJS_AVAILABLE = PYVIS_AVAILABLE
except ImportError:
    VISJS_AVAILABLE = False
    render_visjs_network = None
    render_visjs_timeline = None
    render_combined_view = None

# Importar componente Nivo Sankey
try:
    from components.nivo_sankey import render_nivo_sankey, NIVO_AVAILABLE
except ImportError:
    NIVO_AVAILABLE = False
    render_nivo_sankey = None


def render(username: str, password: str):
    """Renderiza el contenido principal del dashboard."""
    
    # Pre-calcular permisos
    _perm_trazabilidad = tiene_acceso_pagina("rendimiento", "trazabilidad_pallets")
    _perm_sankey = tiene_acceso_pagina("rendimiento", "diagrama_sankey")
    _perm_inventario = tiene_acceso_pagina("rendimiento", "trazabilidad_inventario")
    
    # Debug permisos
    print(f"[DEBUG] Permisos - Trazabilidad: {_perm_trazabilidad}, Sankey: {_perm_sankey}, Inventario: {_perm_inventario}")
    
    # Tabs con nombres actualizados
    tab_names = []
    tab_funcs = []
    
    if _perm_trazabilidad:
        tab_names.append("📦 Producción")
        tab_funcs.append(('trazabilidad', _render_trazabilidad))
    
    if _perm_sankey:
        tab_names.append("🔗 Contenedores")
        tab_funcs.append(('sankey', _render_sankey))
    
    if _perm_inventario:
        tab_names.append("📊 Stock Teórico Anual")
        tab_funcs.append(('inventario', _render_analisis_completo))
    
    if not tab_names:
        st.error("🚫 **Acceso Restringido** - No tienes permisos para ver ninguna sección de Trazabilidad.")
        return
    
    tabs_ui = st.tabs(tab_names)
    
    for idx, (tab_type, render_func) in enumerate(tab_funcs):
        with tabs_ui[idx]:
            render_func(username, password)


def _render_trazabilidad(username: str, password: str):
    """Renderiza el tab de trazabilidad inversa por pallets (Producción)."""
    st.subheader("📦 Trazabilidad de Producción: Pallet → Productor")
    st.markdown("Rastrea uno o varios pallets desde el producto terminado hasta el productor original.")
    
    # Sección de búsqueda
    st.markdown("### 🔍 Buscar Pallets")
    
    # Opciones de entrada
    modo = st.radio(
        "Modo de entrada:",
        ["📝 Ingresar uno por uno", "📋 Pegar lista (separada por comas o líneas)"],
        horizontal=True
    )
    
    pallets = []
    
    if modo == "📝 Ingresar uno por uno":
        col1, col2 = st.columns([3, 1])
        with col1:
            pallet_input = st.text_input(
                "Nombre del Pallet",
                placeholder="Ej: PALLET-RF-2024-0156",
                key="pallet_single"
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Agregar", use_container_width=True):
                if pallet_input and pallet_input not in st.session_state.get('pallets_list', []):
                    if 'pallets_list' not in st.session_state:
                        st.session_state.pallets_list = []
                    st.session_state.pallets_list.append(pallet_input.strip())
                    st.rerun()
        
        # Mostrar pallets agregados
        if 'pallets_list' in st.session_state and st.session_state.pallets_list:
            st.markdown("**Pallets agregados:**")
            cols = st.columns([4, 1])
            for idx, p in enumerate(st.session_state.pallets_list):
                with cols[0]:
                    st.write(f"{idx + 1}. {p}")
                with cols[1]:
                    if st.button(f"🗑️", key=f"del_{idx}"):
                        st.session_state.pallets_list.remove(p)
                        st.rerun()
            pallets = st.session_state.pallets_list
    else:
        pallets_text = st.text_area(
            "Lista de Pallets",
            placeholder="PALLET-001\nPALLET-002, PALLET-003\nPALLET-004",
            height=150,
            help="Separa los pallets por comas o líneas nuevas"
        )
        if pallets_text:
            # Separar por comas o líneas
            import re
            pallets = [p.strip() for p in re.split(r'[,\n]+', pallets_text) if p.strip()]
            st.info(f"🔢 {len(pallets)} pallet(s) detectado(s)")
    
    # Botón de búsqueda
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔍 Rastrear Trazabilidad", type="primary", use_container_width=True):
            if not pallets:
                st.warning("⚠️ Ingresa al menos un pallet")
                return
            
            with st.spinner(f"🔎 Rastreando {len(pallets)} pallet(s)..."):
                from .shared import get_trazabilidad_pallets
                resultado = get_trazabilidad_pallets(username, password, pallets)
                
                if resultado.get('error'):
                    st.error(f"❌ {resultado['error']}")
                    return
                
                # Guardar en session state
                st.session_state.trazabilidad_resultado = resultado
                st.rerun()
    
    # Botón para limpiar
    if 'pallets_list' in st.session_state and st.session_state.pallets_list:
        with col3:
            if st.button("🧹 Limpiar", use_container_width=True):
                st.session_state.pallets_list = []
                st.rerun()
    
    # Mostrar resultados
    if 'trazabilidad_resultado' in st.session_state:
        resultado = st.session_state.trazabilidad_resultado
        
        st.markdown("---")
        st.markdown(f"## 📊 Resultados ({resultado['pallets_rastreados']} pallet(s))")
        
        # Mostrar cada pallet
        for pallet_data in resultado['pallets']:
            _render_pallet_trazabilidad(pallet_data)


def _render_pallet_trazabilidad(pallet_data: dict):
    """Renderiza la trazabilidad de un pallet individual."""
    
    pallet_name = pallet_data.get('pallet', 'N/A')
    
    # Verificar si hay error
    if pallet_data.get('error'):
        with st.expander(f"❌ {pallet_name}", expanded=False):
            st.error(f"Error: {pallet_data['error']}")
        return
    
    # Pallet exitoso
    resumen = pallet_data.get('resumen', {})
    cadena = pallet_data.get('cadena', [])
    
    # Título del pallet
    with st.expander(f"✅ {pallet_name} - {pallet_data.get('producto_pt', 'N/A')}", expanded=True):
        
        # KPIs del pallet
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Kg PT", fmt_numero(pallet_data.get('kg_pt', 0), 2))
        with col2:
            st.metric("Kg MP Total", fmt_numero(resumen.get('kg_mp_total', 0), 2))
        with col3:
            rendimiento = resumen.get('rendimiento_total', 0)
            st.metric("Rendimiento", f"{rendimiento}%")
        with col4:
            merma = resumen.get('merma_kg', 0)
            st.metric("Merma", f"{fmt_numero(merma, 2)} kg")
        
        st.markdown("---")
        
        # Información del lote PT
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**📦 Lote PT:** {pallet_data.get('lote_pt', 'N/A')}")
        with col2:
            st.markdown(f"**🏭 Total Procesos:** {resumen.get('total_procesos', 0)}")
        
        # Productores origen
        if resumen.get('productores'):
            st.markdown("**👨‍🌾 Productores Origen:**")
            for prod in resumen['productores']:
                st.markdown(f"- {prod}")
        
        st.markdown("---")
        st.markdown("### 🔗 Cadena de Trazabilidad")
        
        # Organizar cadena por niveles
        niveles = {}
        for registro in cadena:
            nivel = registro.get('nivel', 0)
            if nivel not in niveles:
                niveles[nivel] = []
            niveles[nivel].append(registro)
        
        # Mostrar por niveles (de 0 a N)
        for nivel in sorted(niveles.keys()):
            registros = niveles[nivel]
            
            for registro in registros:
                tipo = registro.get('tipo', '')
                
                if tipo == 'PROCESO':
                    _render_proceso(registro, nivel)
                elif tipo == 'MATERIA_PRIMA':
                    _render_materia_prima(registro, nivel)


def _render_proceso(registro: dict, nivel: int):
    """Renderiza un registro de proceso."""
    indent = "  " * nivel
    
    # Cabecera del proceso
    sala = registro.get('sala', 'N/A')
    mo_name = registro.get('mo_name', 'N/A')
    fecha = registro.get('fecha_mo', 'N/A')
    
    st.markdown(f"{indent}**🏭 PROCESO - Nivel {nivel}**")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"{indent}- **Sala:** {sala}")
        st.markdown(f"{indent}- **MO:** {mo_name}")
        st.markdown(f"{indent}- **Lote:** {registro.get('lot_name', 'N/A')}")
    with col2:
        st.markdown(f"{indent}- **Fecha:** {fecha}")
        kg_consumido = registro.get('total_kg_consumido', 0)
        st.markdown(f"{indent}- **Total consumido:** {fmt_numero(kg_consumido, 2)} kg")
    
    # Consumos del proceso
    consumos = registro.get('consumos', [])
    if consumos:
        st.markdown(f"{indent}  **📥 Consumió:**")
        for c in consumos:
            st.markdown(
                f"{indent}    - {c['lot_name']}: {fmt_numero(c['qty_done'], 2)} kg ({c['product_name'][:60]}...)"
            )
    
    st.markdown("")  # Espacio


def _render_materia_prima(registro: dict, nivel: int):
    """Renderiza un registro de materia prima."""
    indent = "  " * nivel
    
    st.markdown(f"{indent}**🌾 MATERIA PRIMA - Nivel {nivel} (ORIGEN)**")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"{indent}- **Lote MP:** {registro.get('lot_name', 'N/A')}")
        st.markdown(f"{indent}- **Producto:** {registro.get('product_name', 'N/A')[:60]}")
        st.markdown(f"{indent}- **👨‍🌾 Productor:** {registro.get('productor', 'N/A')}")
    with col2:
        st.markdown(f"{indent}- **Fecha recepción:** {registro.get('fecha_recepcion', 'N/A')}")
    
    st.markdown("")  # Espacio



def _render_sankey(username: str, password: str):
    """Renderiza el tab del diagrama de trazabilidad."""
    st.subheader("🔗 Diagrama de Trazabilidad")
    
    # Selector de tipo de diagrama
    st.markdown("### 📊 Tipo de Visualización")
    
    diagram_types = ["📈 Sankey (Plotly)"]
    
    # Agregar Nivo Sankey si está disponible
    if NIVO_AVAILABLE:
        diagram_types.append("📊 Sankey (D3)")
    
    # Agregar vis.js si está disponible
    if VISJS_AVAILABLE:
        diagram_types.append("🕸️ vis.js Network")
    
    # Agregar tabla al final
    diagram_types.append("📋 Tabla de Conexiones")
    
    diagram_type = st.radio(
        "Selecciona el tipo de diagrama:",
        diagram_types,
        horizontal=True,
        key="diagram_type_selector"
    )
    
    st.markdown("---")
    st.markdown("### 🔍 Modo de Búsqueda")
    
    search_mode = st.radio(
        "Selecciona el modo:",
        ["📅 Por rango de fechas", "🔖 Por venta o paquete", "📥 Por guía de despacho", "🏭 Por proveedor"],
        horizontal=True,
        key="search_mode_selector"
    )
    
    if search_mode == "📅 Por rango de fechas":
        st.markdown("### 📅 Período para Diagrama")
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input(
                "Desde",
                datetime(2025, 12, 1),
                format="DD/MM/YYYY",
                key="sankey_fecha_inicio",
            )
        with col2:
            fecha_fin = st.date_input(
                "Hasta",
                datetime.now(),
                format="DD/MM/YYYY",
                key="sankey_fecha_fin",
            )
        identifier = None
        delivery_guide = None
    elif search_mode == "📥 Por guía de despacho":
        st.markdown("### 📥 Buscar por Guía de Despacho")
        
        col_guide, col_btn = st.columns([3, 1])
        with col_guide:
            guide_pattern = st.text_input(
                "Número de guía",
                placeholder="Ej: 503",
                key="delivery_guide_pattern",
                help="Ingresa el número base de guía (ej: 503 para buscar 503, 503., 503a, etc.)"
            )
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            search_btn = st.button("🔍 Buscar", use_container_width=True, key="search_guide_btn")
        
        # Buscar recepciones cuando se presiona el botón
        if search_btn and guide_pattern:
            from .shared import search_recepciones_by_guide_pattern
            with st.spinner(f"Buscando recepciones con guía {guide_pattern}..."):
                result = search_recepciones_by_guide_pattern(username, password, guide_pattern)
                
                if result and result.get('recepciones'):
                    st.session_state.found_recepciones = result['recepciones']
                    st.session_state.guide_pattern_searched = guide_pattern
                else:
                    st.warning(f"No se encontraron recepciones con guía {guide_pattern}")
                    st.session_state.found_recepciones = []
        
        # Mostrar recepciones encontradas
        selected_picking_id = None
        if 'found_recepciones' in st.session_state and st.session_state.found_recepciones:
            st.markdown(f"#### 📋 Recepciones encontradas ({len(st.session_state.found_recepciones)})")
            
            # Crear opciones para el selectbox
            opciones = [
                f"{r['guia_despacho']} | {r['productor']} | {r['albaran']} | {r['fecha'][:10] if r['fecha'] else 'Sin fecha'}"
                for r in st.session_state.found_recepciones
            ]
            
            seleccion_idx = st.selectbox(
                "Selecciona una recepción:",
                options=range(len(opciones)),
                format_func=lambda i: opciones[i],
                key="select_recepcion_guide"
            )
            
            if seleccion_idx is not None:
                selected_picking_id = st.session_state.found_recepciones[seleccion_idx]['picking_id']
                selected_info = st.session_state.found_recepciones[seleccion_idx]
                st.info(f"✅ Seleccionado: **{selected_info['guia_despacho']}** - {selected_info['productor']}")
        
        # Modo de conexión
        connection_mode = st.selectbox(
            "Modo de conexión",
            ["🔗 Conexión directa", "🌐 Todos (con hermanos)"],
            key="connection_mode_guide",
            help="'Conexión directa' muestra solo la cadena conectada. 'Todos' incluye pallets hermanos del mismo proceso."
        )
        include_siblings = connection_mode == "🌐 Todos (con hermanos)"
        
        st.caption("💡 Ingresa el número base de guía (ej: 503), busca las recepciones y selecciona una para ver su trazabilidad")
        fecha_inicio = None
        fecha_fin = None
        identifier = None
        delivery_guide = None
        supplier_id = None
    elif search_mode == "🏭 Por proveedor":
        st.markdown("### 🏭 Buscar por Proveedor")
        
        # Obtener lista de proveedores
        from .shared import get_suppliers_list
        suppliers = get_suppliers_list(username, password)
        
        if suppliers:
            # Crear opciones para el selectbox
            supplier_options = {f"{s['name']} (ID: {s['id']})": s['id'] for s in suppliers}
            
            selected_supplier = st.selectbox(
                "Selecciona un proveedor:",
                options=list(supplier_options.keys()),
                key="select_supplier"
            )
            supplier_id = supplier_options[selected_supplier]
            
            # Rango de fechas con default últimos 7 días
            st.markdown("#### 📅 Rango de fechas")
            col1, col2 = st.columns(2)
            
            default_end = datetime.now().date()
            default_start = default_end - timedelta(days=7)
            
            with col1:
                fecha_inicio_supplier = st.date_input(
                    "Desde",
                    value=default_start,
                    format="DD/MM/YYYY",
                    key="supplier_fecha_inicio",
                )
            with col2:
                fecha_fin_supplier = st.date_input(
                    "Hasta",
                    value=default_end,
                    format="DD/MM/YYYY",
                    key="supplier_fecha_fin",
                )
            
            # Modo de conexión
            connection_mode = st.selectbox(
                "Modo de conexión",
                ["🔗 Conexión directa", "🌐 Todos (con hermanos)"],
                key="connection_mode_supplier",
                help="'Conexión directa' muestra solo la cadena conectada. 'Todos' incluye pallets hermanos del mismo proceso."
            )
            include_siblings = connection_mode == "🌐 Todos (con hermanos)"
            
            st.caption("💡 Selecciona un proveedor y un rango de fechas para ver la trazabilidad de todas sus recepciones")
            fecha_inicio = fecha_inicio_supplier
            fecha_fin = fecha_fin_supplier
            identifier = None
            delivery_guide = None
        else:
            st.warning("No se encontraron proveedores con recepciones")
            supplier_id = None
            fecha_inicio = None
            fecha_fin = None
            identifier = None
            delivery_guide = None
    else:
        st.markdown("### 🔖 Buscar por Identificador")
        col_id, col_mode = st.columns([3, 2])
        with col_id:
            identifier = st.text_input(
                "Ingresa el código",
                placeholder="Ej: S00574 (venta) o nombre de paquete",
                key="identifier_input",
                help="Si empieza con 'S' + números, buscará la venta. Si no, buscará el paquete específico."
            )
        with col_mode:
            connection_mode = st.selectbox(
                "Modo de conexión",
                ["🔗 Conexión directa", "🌐 Todos (con hermanos)"],
                key="connection_mode",
                help="'Conexión directa' muestra solo la cadena conectada. 'Todos' incluye pallets hermanos del mismo proceso."
            )
        include_siblings = connection_mode == "🌐 Todos (con hermanos)"
        st.caption("💡 **Ejemplos:** `S00574` (busca venta) | `PALLET-001` (busca paquete)")
        fecha_inicio = None
        fecha_fin = None
        delivery_guide = None

    # Filtro de productor (deshabilitado temporalmente)
    # TODO: Implementar filtro por productor buscando pallet por pallet
    st.caption("🔒 Filtro de productor disponible próximamente")
    
    # Inicializar session_state para datos de diagrama
    if "diagram_data" not in st.session_state:
        st.session_state.diagram_data = None
    if "diagram_data_type" not in st.session_state:
        st.session_state.diagram_data_type = None
    if "search_identifier" not in st.session_state:
        st.session_state.search_identifier = None
    
    # Validar entrada según modo
    can_generate = False
    if search_mode == "📅 Por rango de fechas":
        can_generate = True
    elif search_mode == "📥 Por guía de despacho":
        can_generate = selected_picking_id is not None
    elif search_mode == "🏭 Por proveedor":
        can_generate = supplier_id is not None
    else:  # Por identificador
        can_generate = identifier and identifier.strip()
    
    if st.button("🔄 Generar Diagrama", type="primary", disabled=not can_generate):
        spinner_msg = "Obteniendo datos de trazabilidad..."
        
        with st.spinner(spinner_msg):
            # Obtener datos según el modo de búsqueda
            if search_mode == "🏭 Por proveedor":
                # Limpiar identificador en búsqueda por proveedor
                st.session_state.search_identifier = None
                
                from .shared import get_traceability_by_supplier
                fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
                fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")
                
                raw_data = get_traceability_by_supplier(
                    username,
                    password,
                    supplier_id,
                    fecha_inicio_str,
                    fecha_fin_str,
                    include_siblings=include_siblings
                )
                
                if not raw_data or raw_data.get('error') or not raw_data.get('pallets'):
                    error_msg = raw_data.get('error', f"No se encontraron datos para el proveedor seleccionado")
                    st.warning(error_msg)
                    st.session_state.diagram_data = None
                    return
                
                # Mostrar metadata
                metadata = raw_data.get('search_metadata', {})
                if metadata:
                    st.info(f"✅ Encontradas {metadata.get('total_recepciones', 0)} recepciones con {metadata.get('total_pallets', 0)} pallets")
                
                # Transformar según el tipo de diagrama
                if diagram_type == "📈 Sankey (Plotly)":
                    from backend.services.traceability import transform_to_sankey
                    data = transform_to_sankey(raw_data)
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "sankey"
                    
                elif diagram_type == "📊 Sankey (D3)" and NIVO_AVAILABLE:
                    from backend.services.traceability import transform_to_sankey
                    data = transform_to_sankey(raw_data)
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "nivo_sankey"
                    
                elif diagram_type == "🕸️ vis.js Network" and VISJS_AVAILABLE:
                    from backend.services.traceability import transform_to_visjs
                    data = transform_to_visjs(raw_data)
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "visjs"
                    
                else:  # Tabla
                    st.session_state.diagram_data = raw_data
                    st.session_state.diagram_data_type = "table"
                
                st.success(f"✅ Diagrama generado para {selected_supplier}")
                st.rerun()
            
            elif search_mode == "📥 Por guía de despacho":
                # Limpiar identificador en búsqueda por guía
                st.session_state.search_identifier = None
                
                from .shared import get_traceability_by_picking_id
                raw_data = get_traceability_by_picking_id(
                    username, 
                    password, 
                    selected_picking_id, 
                    include_siblings=include_siblings
                )
                
                if not raw_data or not raw_data.get('pallets'):
                    st.warning(f"No se encontraron datos para la recepción seleccionada")
                    st.session_state.diagram_data = None
                    return
                
                # Transformar según el tipo de diagrama
                if diagram_type == "📈 Sankey (Plotly)":
                    from backend.services.traceability import transform_to_sankey
                    data = transform_to_sankey(raw_data)
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "sankey"
                    
                elif diagram_type == "📊 Sankey (D3)" and NIVO_AVAILABLE:
                    from backend.services.traceability import transform_to_sankey
                    data = transform_to_sankey(raw_data)
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "nivo_sankey"
                    
                elif diagram_type == "🕸️ vis.js Network" and VISJS_AVAILABLE:
                    from backend.services.traceability import transform_to_visjs
                    data = transform_to_visjs(raw_data)
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "visjs"
                    
                else:  # Tabla
                    st.session_state.diagram_data = raw_data
                    st.session_state.diagram_data_type = "table"
                
                selected_info = st.session_state.found_recepciones[seleccion_idx]
                st.success(f"✅ Diagrama generado para guía {selected_info['guia_despacho']} - {selected_info['productor']}")
                st.rerun()
            
            elif search_mode == "📅 Por rango de fechas":
                # Limpiar identificador en búsqueda por fechas
                st.session_state.search_identifier = None
                
                fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
                fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")
                
                # Obtener datos según el tipo de diagrama
                if diagram_type == "📈 Sankey (Plotly)":
                    data = get_sankey_data(username, password, fecha_inicio_str, fecha_fin_str)
                    if not data or not data.get('nodes'):
                        st.warning("No hay datos suficientes para generar el diagrama en el período seleccionado.")
                        st.session_state.diagram_data = None
                        return
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "sankey"
                
                elif diagram_type == "📊 Sankey (D3)" and NIVO_AVAILABLE:
                    data = get_sankey_data(username, password, fecha_inicio_str, fecha_fin_str)
                    if not data or not data.get('nodes'):
                        st.warning("No hay datos suficientes para generar el diagrama en el período seleccionado.")
                        st.session_state.diagram_data = None
                        return
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "nivo_sankey"
                
                elif diagram_type == "🕸️ vis.js Network" and VISJS_AVAILABLE:
                    # Obtener datos crudos y transformar a vis.js
                    raw_data = get_traceability_raw(username, password, fecha_inicio_str, fecha_fin_str)
                    if not raw_data or not raw_data.get('pallets'):
                        st.warning("No hay datos suficientes para generar el diagrama en el período seleccionado.")
                        st.session_state.diagram_data = None
                        return
                    # Transformar a formato vis.js
                    from backend.services.traceability import transform_to_visjs
                    data = transform_to_visjs(raw_data)
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "visjs"
                    
                elif diagram_type == "📋 Tabla de Conexiones":
                    data = get_traceability_raw(username, password, fecha_inicio_str, fecha_fin_str)
                    if not data or not data.get('pallets'):
                        st.warning("No hay datos suficientes para mostrar en el período seleccionado.")
                        st.session_state.diagram_data = None
                        return
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "table"
            
            else:  # Por identificador
                # Guardar el identificador para resaltado
                st.session_state.search_identifier = identifier.strip()
                
                # Determinar el formato de salida según el tipo de diagrama
                if diagram_type == "📈 Sankey (Plotly)":
                    data = get_traceability_by_identifier(username, password, identifier.strip(), output_format="sankey", include_siblings=include_siblings)
                    if not data or not data.get('nodes'):
                        st.warning(f"No se encontraron datos para: {identifier}")
                        st.session_state.diagram_data = None
                        return
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "sankey"
                
                elif diagram_type == "📊 Sankey (D3)" and NIVO_AVAILABLE:
                    data = get_traceability_by_identifier(username, password, identifier.strip(), output_format="sankey", include_siblings=include_siblings)
                    if not data or not data.get('nodes'):
                        st.warning(f"No se encontraron datos para: {identifier}")
                        st.session_state.diagram_data = None
                        return
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "nivo_sankey"
                
                elif diagram_type == "🕸️ vis.js Network" and VISJS_AVAILABLE:
                    data = get_traceability_by_identifier(username, password, identifier.strip(), output_format="visjs", include_siblings=include_siblings)
                    if not data or not data.get('nodes'):
                        st.warning(f"No se encontraron datos para: {identifier}")
                        st.session_state.diagram_data = None
                        return
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "visjs"
                    
                elif diagram_type == "📋 Tabla de Conexiones":
                    # Para tabla, usar raw data del endpoint base
                    try:
                        params = {
                            "username": username,
                            "password": password,
                            "identifier": identifier.strip(),
                            "include_siblings": str(include_siblings).lower(),
                        }
                        import requests, os
                        API_URL = os.getenv("API_URL", "http://127.0.0.1:8002")
                        resp = requests.get(
                            f"{API_URL}/api/v1/containers/traceability/by-identifier",
                            params=params,
                            timeout=120
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                        else:
                            data = None
                    except:
                        data = None
                    
                    if not data or not data.get('pallets'):
                        st.warning(f"No se encontraron datos para: {identifier}")
                        st.session_state.diagram_data = None
                        return
                    st.session_state.diagram_data = data
                    st.session_state.diagram_data_type = "table"
    
    # Renderizar el diagrama si hay datos en session_state
    if st.session_state.diagram_data:
        data = st.session_state.diagram_data
        data_type = st.session_state.diagram_data_type
        
        if data_type == "sankey":
            _render_sankey_plotly(data)
            _render_sankey_stats(data)
        elif data_type == "nivo_sankey" and NIVO_AVAILABLE:
            _render_nivo_sankey(data)
            _render_sankey_stats(data)
        elif data_type == "reactflow" and TIMELINE_FLOW_AVAILABLE:
            _render_reactflow_diagram(data)
        elif data_type == "visjs" and VISJS_AVAILABLE:
            _render_visjs_diagram(data)
        elif data_type == "table":
            _render_connections_table(data)
    else:
        st.info("👆 Ajusta filtros y haz clic en **Generar Diagrama**")


def _render_sankey_plotly(sankey_data: dict):
    """Renderiza el diagrama Sankey con Plotly con controles de zoom y pan."""
    # Calcular altura dinámica basada en cantidad de nodos
    num_nodes = len(sankey_data.get("nodes", []))
    min_height = 800
    max_height = 2000
    # Aumentar altura si hay muchos nodos
    dynamic_height = min(max_height, max(min_height, num_nodes * 15))
    
    # Crear figura Sankey con layout automático de Plotly
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=[n["label"] for n in sankey_data["nodes"]],
            color=[n["color"] for n in sankey_data["nodes"]],
            customdata=[str(n.get("detail", "")) for n in sankey_data["nodes"]],
            hovertemplate="%{label}<br>%{customdata}<extra></extra>"
        ),
        link=dict(
            source=[l["source"] for l in sankey_data["links"]],
            target=[l["target"] for l in sankey_data["links"]],
            value=[l["value"] for l in sankey_data["links"]],
            color=[l.get("color", "rgba(200,200,200,0.35)") for l in sankey_data["links"]],
        )
    )])
    
    # Configurar layout con controles de zoom y pan
    fig.update_layout(
        title="Trazabilidad Completa de Paquetes",
        height=dynamic_height,
        font=dict(size=10),
        dragmode="pan",  # Habilitar pan (arrastre)
        hovermode="closest",
        # Configurar modebar con herramientas
        modebar=dict(
            orientation="v",
            bgcolor="rgba(255,255,255,0.7)",
        )
    )
    
    # Configurar opciones del gráfico para mejor interactividad
    config = {
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToAdd": ["drawopenpath", "eraseshape"],
        "modeBarButtonsToRemove": [],
        "toImageButtonOptions": {
            "format": "png",
            "filename": "trazabilidad_sankey",
            "height": dynamic_height,
            "width": 1400,
            "scale": 2
        },
        "scrollZoom": True,  # Habilitar zoom con scroll
    }
    
    st.markdown("### 📊 Diagrama Sankey")
    st.caption("🖱️ Arrastra para mover | 🔍 Scroll para zoom | 📷 Botones superiores para más opciones")
    
    st.plotly_chart(fig, use_container_width=True, config=config)


def _render_nivo_sankey(sankey_data: dict):
    """Renderiza el diagrama Sankey con D3 en orientación vertical."""
    if not NIVO_AVAILABLE:
        st.error("❌ Componente Nivo no está disponible")
        return
    
    # Calcular altura dinámica basada en cantidad de nodos
    num_nodes = len(sankey_data.get("nodes", []))
    min_height = 800
    max_height = 2000
    dynamic_height = min(max_height, max(min_height, num_nodes * 20))
    
    st.markdown("### 📊 Diagrama Sankey (D3)")
    st.caption("🖱️ Hover sobre nodos para ver detalles | 📊 Orientación vertical para mejor flujo temporal")
    
    # Obtener identificador buscado para resaltar (si existe)
    highlight_package = st.session_state.get("search_identifier", None)
    
    render_nivo_sankey(sankey_data, height=dynamic_height, highlight_package=highlight_package)


def _render_visjs_diagram(visjs_data: dict):
    """Renderiza el diagrama con vis.js Network usando pyvis."""
    if not VISJS_AVAILABLE:
        st.error("❌ pyvis no está instalado. Ejecuta: pip install pyvis")
        return
    
    # Opción para mostrar timeline
    show_timeline = st.checkbox("📅 Mostrar Línea de Tiempo", value=True)
    
    if show_timeline and visjs_data.get("timeline_data"):
        # Vista combinada: timeline arriba, red abajo
        render_combined_view(
            visjs_data,
            network_height="500px",
            timeline_height="750px"
        )
    else:
        # Solo red
        render_visjs_network(visjs_data, height="700px")


def _render_connections_table(traceability_data: dict):
    """Renderiza una tabla de conexiones desde datos crudos de trazabilidad."""
    st.markdown("### 📋 Tabla de Conexiones")
    
    pallets = traceability_data.get("pallets", {})
    processes = traceability_data.get("processes", {})
    suppliers = traceability_data.get("suppliers", {})
    customers = traceability_data.get("customers", {})
    links = traceability_data.get("links", [])
    
    # Mostrar estadísticas
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🏭 Proveedores", len(suppliers))
    with col2:
        pallets_in = len([p for p in pallets.values() if p.get("direction") == "IN"])
        st.metric("🟠 Pallets IN", pallets_in)
    with col3:
        procs = len([p for p in processes.values() if not p.get("is_reception")])
        st.metric("🔴 Procesos", procs)
    with col4:
        pallets_out = len([p for p in pallets.values() if p.get("direction") == "OUT"])
        st.metric("🟢 Pallets OUT", pallets_out)
    with col5:
        st.metric("🔵 Clientes", len(customers))
    
    st.markdown("---")
    
    # Crear tabla de conexiones
    connections = []
    for link in links:
        source_type, source_id, target_type, target_id, qty = link
        
        # Resolver nombres
        source_name = "?"
        target_name = "?"
        
        if source_type == "RECV":
            source_name = f"📥 {source_id}"
        elif source_type == "PALLET":
            pinfo = pallets.get(source_id, {})
            source_name = f"📦 {pinfo.get('name', source_id)}"
        elif source_type == "PROCESS":
            source_name = f"🔴 {source_id}"
        
        if target_type == "PALLET":
            pinfo = pallets.get(target_id, {})
            target_name = f"📦 {pinfo.get('name', target_id)}"
        elif target_type == "PROCESS":
            target_name = f"🔴 {target_id}"
        elif target_type == "CUSTOMER":
            cname = customers.get(target_id, "Cliente")
            target_name = f"🔵 {cname}"
        
        connections.append({
            "Origen": source_name,
            "Tipo": source_type,
            "Destino": target_name,
            "Tipo Destino": target_type,
            "Cantidad (kg)": f"{qty:,.0f}",
        })
    
    if connections:
        df = pd.DataFrame(connections)
        st.dataframe(df, use_container_width=True, hide_index=True, height=500)
    else:
        st.info("No hay conexiones para mostrar")


def _render_reactflow_diagram(reactflow_data: dict):
    """Renderiza el diagrama con React Flow usando streamlit-flow-component."""
    if not TIMELINE_FLOW_AVAILABLE:
        st.error("❌ streamlit-flow-component no está disponible")
        return
    
    # Importar aquí para evitar errores si no está instalado
    try:
        from streamlit_flow import streamlit_flow
        from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
        from streamlit_flow.state import StreamlitFlowState
        from streamlit_flow.layouts import LayeredLayout, TreeLayout, RadialLayout
    except ImportError:
        st.error("❌ Error al importar streamlit-flow-component")
        return
    
    nodes_data = reactflow_data.get("nodes", [])
    edges_data = reactflow_data.get("edges", [])
    timeline_dates = reactflow_data.get("timeline_dates", [])
    stats = reactflow_data.get("stats", {})
    
    if not nodes_data:
        st.warning("No hay nodos para mostrar")
        return
    
    # Mostrar estadísticas
    st.markdown("### 📊 Resumen")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🏭 Proveedores", stats.get("suppliers", 0))
    with col2:
        st.metric("🟠 Pallets IN", stats.get("pallets_in", 0))
    with col3:
        st.metric("🔴 Procesos", stats.get("processes", 0))
    with col4:
        st.metric("🟢 Pallets OUT", stats.get("pallets_out", 0))
    with col5:
        st.metric("🔵 Clientes", stats.get("customers", 0))
    
    # Mostrar línea de tiempo si hay fechas
    if timeline_dates:
        with st.expander(f"📅 Línea de Tiempo ({len(timeline_dates)} fechas)", expanded=False):
            st.write(", ".join(timeline_dates[:20]))
    
    st.markdown("---")
    
    # Usar session_state para mantener el estado del flow
    flow_state_key = "reactflow_state"
    
    # Solo crear nodos/edges si no existen en session_state o si los datos cambiaron
    if flow_state_key not in st.session_state or st.session_state.get("reactflow_data_hash") != hash(str(nodes_data)):
        nodes = []
        for node in nodes_data:
            nodes.append(StreamlitFlowNode(
                id=node["id"],
                pos=(node["position"]["x"], node["position"]["y"]),
                data=node["data"],
                node_type=node.get("type", "default"),
                source_position=node.get("source_position", "right"),
                target_position=node.get("target_position", "left"),
                style=node.get("style", {})
            ))
        
        edges = []
        for edge in edges_data:
            edges.append(StreamlitFlowEdge(
                id=edge["id"],
                source=edge["source"],
                target=edge["target"],
                label=edge.get("label", ""),
                animated=edge.get("animated", False),
                edge_type=edge.get("edge_type", "smoothstep"),
                style=edge.get("style", {}),
                label_style=edge.get("label_style", {})
            ))
        
        st.session_state[flow_state_key] = StreamlitFlowState(nodes=nodes, edges=edges)
        st.session_state["reactflow_data_hash"] = hash(str(nodes_data))
    
    # Layout fijo (Layered horizontal)
    layout = LayeredLayout(direction="right", node_node_spacing=50, node_layer_spacing=200)
    
    # Renderizar con estado persistente
    updated_state = streamlit_flow(
        key="traceability_flow",
        state=st.session_state[flow_state_key],
        layout=layout,
        fit_view=True,
        height=700,
        show_minimap=True,
        show_controls=True,
        hide_watermark=True,
        allow_new_edges=False,
        pan_on_drag=True,
        allow_zoom=True,
        min_zoom=0.1,
        get_node_on_click=True,
    )
    
    # Actualizar estado si cambió
    if updated_state:
        st.session_state[flow_state_key] = updated_state
        if updated_state.selected_id:
            st.info(f"📍 Nodo seleccionado: **{updated_state.selected_id}**")


def _render_sankey_stats(sankey_data: dict):
    """Renderiza las estadísticas del diagrama."""
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🏭 Proveedores", len([n for n in sankey_data["nodes"] if n["color"] == "#9b59b6"]))
    with col2:
        st.metric("📥 Recepciones", len([n for n in sankey_data["nodes"] if n["color"] == "#1abc9c"]))
    with col3:
        st.metric("🔴 Procesos", len([n for n in sankey_data["nodes"] if n["color"] == "#e74c3c"]))
    with col4:
        st.metric("🟢 Pallets OUT", len([n for n in sankey_data["nodes"] if n["color"] == "#2ecc71"]))
    with col5:
        st.metric("🔵 Clientes", len([n for n in sankey_data["nodes"] if n["color"] == "#3498db"]))
    
    # Leyenda
    st.markdown("##### Leyenda de Nodos:")
    st.markdown("""
    - 🏭 **Proveedor** (morado): Origen de la mercadería
    - 📥 **Recepción** (turquesa): Entrada desde proveedor
    - 🔴 **Proceso** (rojo): Operación/transformación
    - 🟠 **Pallet IN** (naranja): Pallet que entra
    - 🟢 **Pallet OUT** (verde): Pallet que sale
    - 🔵 **Cliente** (azul): Destino de venta
    """)
    st.markdown("##### Conexiones:")
    st.markdown("""
    - 🟣 **Continuidad** (morado): Pallet OUT → mismo Pallet IN en otro proceso
    """)


def _render_inventario(username: str, password: str):
    """DEPRECATED: Renderiza el tab viejo de inventario."""
    from .tab_inventario import render as render_inventario
    render_inventario(username, password)


def _render_analisis_completo(username: str, password: str):
    """Renderiza el nuevo tab de análisis completo (4 en 1)."""
    from .tab_analisis_completo import render as render_analisis_completo
    render_analisis_completo(username, password)


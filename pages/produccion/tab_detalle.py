"""
Tab: Detalle de OF
Búsqueda y detalle de órdenes de fabricación individuales.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

from .shared import (
    STATE_OPTIONS, fmt_numero, clean_name, get_state_label,
    format_fecha, format_num, build_pie_chart, build_horizontal_bar,
    fetch_ordenes, fetch_of_detail, fetch_kpis, render_component_tab, render_metrics_row,
    detectar_planta
)


@st.fragment
def render(username: str, password: str):
    """Renderiza el contenido del tab Detalle de OF."""
    st.subheader("📋 Detalle de Órdenes de Fabricación")
    
    # KPIs rápidos
    with st.spinner("Cargando indicadores..."):
        try:
            kpis = fetch_kpis(username, password)
        except Exception as exc:
            st.warning(f"No fue posible cargar los KPIs: {exc}")
            kpis = {}

    if kpis:
        cols = st.columns(5)
        metrics = [
            ("Total órdenes", kpis.get("total_ordenes", 0), ""),
            ("En progreso", kpis.get("ordenes_progress", 0), ""),
            ("Confirmadas", kpis.get("ordenes_confirmed", 0), ""),
            ("Completadas", kpis.get("ordenes_done", 0), ""),
            ("Por cerrar", kpis.get("ordenes_to_close", 0), ""),
        ]
        render_metrics_row(cols, metrics)

    st.markdown("---")

    # Estado de sesión
    if "production_ofs" not in st.session_state:
        st.session_state["production_ofs"] = []
    if "production_current_of" not in st.session_state:
        st.session_state["production_current_of"] = None
    if "prod_error" not in st.session_state:
        st.session_state["prod_error"] = None

    if st.session_state["prod_error"]:
        st.error(st.session_state["prod_error"])

    # Filtros de búsqueda
    with st.expander("🔍 Filtros de búsqueda", expanded=True):
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        start_date = col1.date_input("Desde", value=date.today() - timedelta(days=90), key="prod_filter_start", format="DD/MM/YYYY")
        end_date = col2.date_input("Hasta", value=date.today(), key="prod_filter_end", format="DD/MM/YYYY")
        planta_sel = col3.selectbox("Planta", options=["Todas", "RIO FUTURO", "VILKUN"], index=0, key="prod_filter_planta")
        state_label = col4.selectbox("Estado", options=list(STATE_OPTIONS.keys()), index=0, key="prod_filter_state")
        state_filter = STATE_OPTIONS[state_label]

        btn_col1, btn_col2 = st.columns(2)
        if btn_col1.button("Buscar órdenes", type="primary", key="btn_buscar_ordenes"):
            st.session_state["prod_error"] = None  # Limpiar error
            # SKELETON LOADER
            skeleton = st.empty()
            with skeleton.container():
                st.markdown("""
                <div style="animation: pulse 1.5s infinite;">
                    <div style="height: 40px; background-color: #f0f2f6; border-radius: 8px; margin-bottom: 10px;"></div>
                    <div style="height: 40px; background-color: #f0f2f6; border-radius: 8px; margin-bottom: 10px;"></div>
                    <div style="height: 40px; background-color: #f0f2f6; border-radius: 8px; margin-bottom: 10px;"></div>
                </div>
                <style>@keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 0.3; } 100% { opacity: 0.6; } }</style>
                """, unsafe_allow_html=True)
            
            # with st.spinner("Consultando órdenes..."):
                try:
                    results = fetch_ordenes(
                        username, password,
                        start_date.isoformat(), end_date.isoformat(),
                        state_filter
                    )
                    st.session_state["production_ofs"] = results
                    if results:
                        st.success(f"{len(results)} órdenes encontradas")
                    else:
                        st.info("No se encontraron órdenes en el rango solicitado")
                except Exception as error:
                    st.session_state["prod_error"] = f"Error al buscar órdenes: {error}"
                    st.error(st.session_state["prod_error"])
                finally:
                    skeleton.empty()
        
        if btn_col2.button("Limpiar resultados", type="secondary", key="btn_limpiar_ordenes"):
            st.session_state["production_ofs"] = []
            st.session_state["production_current_of"] = None
            st.cache_data.clear()

    # PLACEHOLDER PARA CONTENIDO - evita que se muestre debajo del skeleton
    content_placeholder = st.container()

    with content_placeholder:
        # Tabla de órdenes
        if st.session_state["production_ofs"]:
            df_full = pd.DataFrame(st.session_state["production_ofs"])
            
            # --- PROCESAMIENTO ---
            df_full['Planta'] = df_full['name'].apply(detectar_planta)
            if planta_sel != "Todas":
                df_full = df_full[df_full['Planta'] == planta_sel].copy()
            
            if df_full.empty:
                st.warning(f"No hay órdenes para la planta {planta_sel}")
                return

            def get_tipo_sala(row):
                sala = str(row.get('x_studio_sala_de_proceso', '')).lower()
                prod = clean_name(row.get('product_id')).lower()
                if any(s in sala for s in ['sala 1', 'sala 2', 'sala 3', 'sala 4', 'sala 5', 'sala 6', 'linea retail', 'granel', 'proceso']):
                    return "Sala"
                if 'congel' in sala or 'tunel' in sala or 'túnel' in sala:
                    return "Congelado"
                if 'iqf' in sala or 'iqf' in prod:
                    return "Sala"
                return "Congelado"

            df_full['Tipo'] = df_full.apply(get_tipo_sala, axis=1)
            df_full['Pendiente'] = (df_full['product_qty'] - df_full['qty_produced']).clip(lower=0)
            df_full['% Avance'] = (df_full['qty_produced'] / df_full['product_qty'] * 100).fillna(0).clip(upper=100)
            df_full['PSP'] = df_full['product_id'].apply(lambda x: "✅" if "PSP" in clean_name(x).upper() or clean_name(x).startswith(('[2.', '[2,')) else "")
            df_full['Estado_Label'] = df_full['state'].apply(lambda x: "Abierta" if x in ['confirmed', 'progress', 'planned', 'to_close'] else "Cerrada")
            df_full['Sala_Clean'] = df_full['x_studio_sala_de_proceso'].apply(lambda x: x if x and x is not False else "Sin Sala")

            # Selector de Vista
            view_mode = st.radio("Modo de Visualización", ["📍 Seguimiento por Sala", "📋 Tabla Detallada"], horizontal=True, key="prod_view_mode")
            
            st.markdown("---")

            if view_mode == "📍 Seguimiento por Sala":
                _render_grouped_view(df_full)
            else:
                _render_table_view(df_full)

            st.markdown("---")
            # Selector para detalle individual
            ofs_for_selector = df_full.to_dict('records')
            
            options = {
                f"{of.get('name', 'OF')} — {clean_name(of.get('product_id'))}": of["id"]
                for of in ofs_for_selector
            }
            selected_label = st.selectbox("Seleccionar orden para detalle", options=list(options.keys()), key="prod_selector")
            selected_id = options[selected_label]
            
            if st.button("Cargar detalle", type="primary", key="btn_cargar_detalle", disabled=st.session_state.prod_detalle_loading):
                st.session_state.prod_detalle_loading = True
                try:
                    # Progress bar personalizado
                    progress_placeholder = st.empty()
                    
                    with progress_placeholder.container():
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        status_text.text("🔗 Conectando con Odoo...")
                        progress_bar.progress(25)
                        
                        status_text.text("📋 Consultando detalle de OF...")
                        progress_bar.progress(50)
                        
                        detail = fetch_of_detail(selected_id, username, password)
                        
                        status_text.text("⚙️ Procesando componentes...")
                        progress_bar.progress(75)
                        
                        st.session_state["production_current_of"] = detail
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Detalle cargado")
                    
                    progress_placeholder.empty()
                    st.toast("✅ Detalle cargado correctamente", icon="✅")
                except Exception as error:
                    progress_placeholder.empty()
                    st.error(f"No se pudo cargar la orden: {error}")
                    st.toast(f"❌ Error: {str(error)[:100]}", icon="❌")
                finally:
                    st.session_state.prod_detalle_loading = False
        else:
            st.info("Busca una orden para comenzar")

    # =============================================================================
# HELPER RENDERS PARA TAB DETALLE
# =============================================================================

def _render_grouped_view(df):
    """Renderiza las órdenes agrupadas por Estado, Planta y Sala."""
    tabs_estado = st.tabs(["🔄 Órdenes Abiertas", "✅ Órdenes Cerradas"])
    
    with tabs_estado[0]: # ABIERTAS
        _render_status_group(df[df['Estado_Label'] == "Abierta"])
        
    with tabs_estado[1]: # CERRADAS
        _render_status_group(df[df['Estado_Label'] == "Cerrada"])

def _render_status_group(df_status):
    if df_status.empty:
        st.info("No hay órdenes en este estado.")
        return
    
    # KPIs rápidos del grupo
    k1, k2, k3 = st.columns(3)
    k1.metric("Órdenes", len(df_status))
    k2.metric("Pendiente", f"{df_status['Pendiente'].sum():,.0f} kg")
    k3.metric("Hecho", f"{df_status['qty_produced'].sum():,.0f} kg")

    # Separar por Tipo (Sala vs Congelado)
    df_sala = df_status[df_status['Tipo'] == "Sala"]
    df_congelado = df_status[df_status['Tipo'] == "Congelado"]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🏭 Procesos en Sala")
        if df_sala.empty: st.caption("No hay órdenes de sala")
        else:
            for sala, group in df_sala.groupby("Sala_Clean"):
                with st.expander(f"📍 {sala} ({len(group)} OFs)"):
                    for _, row in group.iterrows():
                        _render_of_card(row)

    with c2:
        st.markdown("#### ❄️ Congelado / Túneles")
        if df_congelado.empty: st.caption("No hay órdenes de congelado")
        else:
            for sala, group in df_congelado.groupby("Sala_Clean"):
                with st.expander(f"📍 {sala} ({len(group)} OFs)"):
                    for _, row in group.iterrows():
                        _render_of_card(row)

def _render_of_card(row):
    """Renderiza una card visual para una OF en la vista agrupada."""
    with st.container():
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 10px; border-left: 4px solid {'#00cc66' if row['Estado_Label'] == 'Cerrada' else '#3498db'}; margin-bottom: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <b style="font-size: 1.1em; color: #ffffff;">{row['name']} {row['PSP']}</b>
                <span style="font-size: 0.85em; color: #8892b0;">{row['Planta']}</span>
            </div>
            <div style="font-size: 0.9em; color: #8892b0; margin: 4px 0;">{clean_name(row['product_id'])}</div>
            <div style="display: flex; justify-content: space-between; font-size: 0.85em; margin-bottom: 4px;">
                <span>Progreso: {row['qty_produced']:,.0f} / {row['product_qty']:,.0f} kg</span>
                <b style="color: {'#e74c3c' if row['Pendiente'] > 0 else '#00cc66'};">{row['Pendiente']:,.0f} kg pendientes</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(row['% Avance']/100)

def _render_table_view(df):
    """Vista de tabla tradicional mejorada."""
    display_cols = [
        "name", "Estado_Label", "Planta", "Sala_Clean", "Tipo", "producto",
        "product_qty", "qty_produced", "Pendiente", "PSP", "Fecha Planif."
    ]
    st.dataframe(
        df[display_cols].rename(columns={
            "name": "Orden", "Estado_Label": "Estado", "Sala_Clean": "Sala",
            "product_qty": "Planificado", "qty_produced": "Producido"
        }),
        use_container_width=True,
        height=500,
        column_config={
            "Planificado": st.column_config.NumberColumn(format="%d"),
            "Producido": st.column_config.NumberColumn(format="%d"),
            "Pendiente": st.column_config.NumberColumn(format="%d"),
        },
        hide_index=True
    )

def _render_detalle_of(data_of):
    """Renderiza el detalle completo de una orden de fabricación."""
    st.markdown("---")
    of = data_of.get("of", {})
    componentes = data_of.get("componentes", [])
    subproductos = data_of.get("subproductos", [])
    detenciones = data_of.get("detenciones", [])
    consumo = data_of.get("consumo", [])

    # Filtrar componentes y subproductos
    componentes_fruta = [item for item in componentes if str(item.get('product_category_name', '')).upper().startswith('PRODUCTOS')]
    subproductos_filtrados = [item for item in subproductos if not str(item.get('product_category_name', '')).upper().startswith('PROCESOS')]
    subproductos_sin_merma = [item for item in subproductos_filtrados if 'merma' not in str(item.get('product_category_name', '')).lower()]

    # Calcular KG in y out
    kg_in = sum([item.get('qty_done', 0) or 0 for item in componentes_fruta])
    kg_out = sum([item.get('qty_done', 0) or 0 for item in subproductos_sin_merma])
    merma = sum([item.get('qty_done', 0) or 0 for item in subproductos_filtrados if 'merma' in str(item.get('product_category_name', '')).lower()])

    # Calcular PxQ
    total_pxq_comp = sum([(item.get('x_studio_precio_unitario', 0) or 0) * (item.get('qty_done', 0) or 0) for item in componentes])
    total_pxq_sub = sum([(item.get('x_studio_precio_unitario', 0) or 0) * (item.get('qty_done', 0) or 0) for item in subproductos_filtrados])

    rendimiento_val = (kg_out / kg_in * 100) if kg_in > 0 else 0

    # Header de la OF
    st.markdown(f"### 🏭 Detalle de la Orden: {of.get('name')} {('✅ PSP' if 'PSP' in clean_name(of.get('product_id')).upper() else '')}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="info-card">
            <h4>📌 Información General</h4>
            <div class="info-row"><span class="info-label">Producto</span><span class="info-value">{clean_name(of.get('product_id'))}</span></div>
            <div class="info-row"><span class="info-label">Cliente</span><span class="info-value">{clean_name(of.get('x_studio_clientes')) if clean_name(of.get('x_studio_clientes')) != 'False' else 'N/A'}</span></div>
            <div class="info-row"><span class="info-label">Planta</span><span class="info-value">{detectar_planta(of.get('name'))}</span></div>
            <div class="info-row"><span class="info-label">Sala</span><span class="info-value">{clean_name(of.get('x_studio_sala_de_proceso'))}</span></div>
            <div class="info-row"><span class="info-label">Responsable</span><span class="info-value">{clean_name(of.get('user_id'))}</span></div>
            <div class="info-row"><span class="info-label">Estado</span><span class="info-value">{get_state_label(of.get('state'))}</span></div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="info-card">
            <h4>⏱️ Tiempos y Dotación</h4>
            <div class="info-row"><span class="info-label">Inicio Proceso</span><span class="info-value">{format_fecha(of.get('x_studio_inicio_de_proceso'))}</span></div>
            <div class="info-row"><span class="info-label">Término Proceso</span><span class="info-value">{format_fecha(of.get('x_studio_termino_de_proceso'))}</span></div>
            <div class="info-row"><span class="info-label">Horas Detención</span><span class="info-value">{format_num(of.get('x_studio_horas_detencion_totales'))} hrs</span></div>
            <div class="info-row"><span class="info-label">Dotación</span><span class="info-value">{format_num(of.get('x_studio_dotacin'))} personas</span></div>
            <div class="info-row"><span class="info-label">Total HH</span><span class="info-value">{format_num(of.get('x_studio_hh'))} hrs</span></div>
        </div>
        """, unsafe_allow_html=True)

    # Eficiencia y PO en filas compactas
    ec1, ec2 = st.columns(2)
    with ec1:
        st.markdown(f"""
        <div class="info-card">
            <h4>📈 Eficiencia Operativa</h4>
            <div class="info-row"><span class="info-label">HH Efectiva</span><span class="info-value">{format_num(of.get('x_studio_hh_efectiva'))} hrs</span></div>
            <div class="info-row"><span class="info-label">KG / HH Efectiva</span><span class="info-value">{format_num(of.get('x_studio_kghh_efectiva'))} kg/hr</span></div>
        </div>
        """, unsafe_allow_html=True)
    with ec2:
        po_asociada = clean_name(of.get('x_studio_po_asociada'))
        st.markdown(f"""
        <div class="info-card">
            <h4>📦 Referencia PO</h4>
            <div class="info-row"><span class="info-label">PO Asociada</span><span class="info-value">{po_asociada if po_asociada not in ['-', 'False'] else 'N/A'}</span></div>
            <div class="info-row"><span class="info-label">KG Disponibles PO</span><span class="info-value">{format_num(of.get('x_studio_kg_disponibles_po', 0))} kg</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # KPIs de Producción
    st.markdown("### 📊 Balance de Masa y Rendimiento")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    kpi_col1.metric("KG Entrada (Materia Prima)", f"{kg_in:,.0f} kg")
    kpi_col2.metric("KG Salida (Terminado)", f"{kg_out:,.0f} kg")
    kpi_col3.metric("Merma Proceso", f"{merma:,.0f} kg", delta=f"{merma/(kg_in if kg_in>0 else 1)*100:.1f}%", delta_color="inverse")
    kpi_col4.metric("Rendimiento Final", f"{rendimiento_val:.2f}%")

    # Gráfico de Rendimiento (Gauge)
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rendimiento_val,
        number={"suffix": "%", "valueformat": ".2f", "font": {"color": "#ffffff"}},
        gauge={
            "axis": {"range": [0, 120], "tickcolor": "#ffffff"},
            "bar": {"color": "#00cc66"},
            "bgcolor": "rgba(0,0,0,0)",
            "steps": [
                {"range": [0, 80], "color": "#ff444433"},
                {"range": [80, 100], "color": "#00cc6633"},
            ],
        }
    ))
    fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(t=0, b=0))
    st.plotly_chart(fig_gauge, use_container_width=True)

    st.markdown("---")

    # Tabs de Información Detallada
    tab_comp, tab_sub, tab_det, tab_consumo = st.tabs([
        "🌳 Componentes (MP / Insumos)", 
        "📦 Subproductos (Pallets Producidos)", 
        "⏱️ Detenciones", 
        "⚖️ Trazabilidad de Consumo"
    ])

    with tab_comp:
        st.markdown("#### Detalle de Materiales Consumidos")
        if componentes:
            df_c = pd.DataFrame([{
                "Producto": clean_name(c.get("product_id")),
                "Lote": clean_name(c.get("lot_id")),
                "Pallet Origen": clean_name(c.get("package_id")),
                "Cantidad": c.get("qty_done", 0),
                "UoM": clean_name(c.get("product_uom_id")),
                "Categoría": clean_name(c.get("product_category_name"))
            } for c in componentes])
            st.dataframe(df_c, use_container_width=True, hide_index=True)
        else:
            st.info("No hay componentes registrados.")

    with tab_sub:
        st.markdown("#### Detalle de Pallets y Productos Resultantes")
        if subproductos:
            df_s = pd.DataFrame([{
                "Producto": clean_name(s.get("product_id")),
                "Lote": clean_name(s.get("lot_id")),
                "Pallet Destino": clean_name(s.get("result_package_id")),
                "Cantidad": s.get("qty_done", 0),
                "UoM": clean_name(s.get("product_uom_id")),
                "Categoría": clean_name(s.get("product_category_name"))
            } for s in subproductos])
            st.dataframe(df_s, use_container_width=True, hide_index=True)
        else:
            st.info("No hay subproductos registrados.")

    with tab_det:
        st.markdown("#### Registro de Tiempos Muertos")
        if detenciones:
            df_det = pd.DataFrame([{
                "Motivo": clean_name(det.get("x_motivodetencion")),
                "Responsable": clean_name(det.get("x_studio_responsable")),
                "Inicio": format_fecha(det.get("x_horainiciodetencion")),
                "Fin": format_fecha(det.get("x_horafindetencion")),
                "Duración (hrs)": format_num(det.get("x_studio_horas_de_detencin", 0)),
            } for det in detenciones])
            st.dataframe(df_det, use_container_width=True, hide_index=True)
        else:
            st.info("No se registraron detenciones para esta orden.")

    with tab_consumo:
        st.markdown("#### Historial Cronológico de Consumo de Pallets")
        if consumo:
            df_cons = pd.DataFrame([{
                "Pallet": item.get("x_name", "N/A"),
                "Producto": item.get("producto", "Desconocido"),
                "Lote": item.get("lote", ""),
                "Tipo": item.get("type", "Desconocido"),
                "Hora Inicio": format_fecha(item.get("x_studio_hora_inicio")),
                "Hora Fin": format_fecha(item.get("x_studio_hora_fin")),
            } for item in consumo])
            st.dataframe(df_cons, use_container_width=True, hide_index=True)
        else:
            st.info("No hay registros detallados de cronología de consumo.")

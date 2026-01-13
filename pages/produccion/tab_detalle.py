"""
Tab: Detalle de OF
Búsqueda y detalle de órdenes de fabricación individuales.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

from .shared import (
    STATE_OPTIONS, CSS_GLOBAL, fmt_numero, clean_name, get_state_label,
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
        start_date = col1.date_input("Desde", value=date.today() - timedelta(days=30), key="prod_filter_start", format="DD/MM/YYYY")
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
            df = pd.DataFrame(st.session_state["production_ofs"])
            st.subheader("📋 Tabla de órdenes encontradas")
            
            if not df.empty:
                # --- PROCESAMIENTO ADICIONAL ---
                df['Planta'] = df['name'].apply(detectar_planta)
                
                # Filtrar por planta seleccionada en el UI
                if planta_sel != "Todas":
                    df = df[df['Planta'] == planta_sel].copy()
                
                if df.empty:
                    st.warning(f"No hay órdenes para la planta {planta_sel}")
                else:
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

                    df['Tipo'] = df.apply(get_tipo_sala, axis=1)
                    df['Pendiente'] = (df['product_qty'] - df['qty_produced']).clip(lower=0)
                    df['PSP'] = df['product_id'].apply(lambda x: "✅" if "PSP" in clean_name(x).upper() or clean_name(x).startswith(('[2.', '[2,')) else "")
                    
                    # KPIs de los resultados filtrados
                    st.markdown("##### 📊 Resumen de Búsqueda")
                    rkpi1, rkpi2, rkpi3, rkpi4 = st.columns(4)
                    rkpi1.metric("Cant. Órdenes", len(df))
                    rkpi2.metric("Total Pendiente", f"{df['Pendiente'].sum():,.0f} kg")
                    rkpi3.metric("Total Producido", f"{df['qty_produced'].sum():,.0f} kg")
                    rkpi4.metric("Órdenes PSP", len(df[df['PSP'] == "✅"]))

                    display_cols = [col for col in [
                        "name", "state", "Planta", "x_studio_sala_de_proceso", "Tipo", "product_id",
                        "product_qty", "qty_produced", "Pendiente", "PSP", "date_planned_start"
                    ] if col in df.columns]
                    
                    df_display = df[display_cols].copy()
                    
                    if "product_id" in df_display.columns:
                        df_display["producto"] = df_display["product_id"].apply(clean_name)
                        df_display.drop(columns=["product_id"], inplace=True)
                    
                    if "date_planned_start" in df_display.columns:
                        df_display["Fecha Planif."] = df_display["date_planned_start"].apply(lambda x: pd.to_datetime(x).strftime("%d/%m/%Y") if pd.notna(x) and x else "")
                        df_display.drop(columns=["date_planned_start"], inplace=True)

                    df_display = df_display.rename(columns={
                        "name": "Orden",
                        "state": "Estado",
                        "x_studio_sala_de_proceso": "Sala",
                        "product_qty": "Planificado",
                        "qty_produced": "Producido",
                    })
                    
                    # Mostrar tabla
                    st.dataframe(
                        df_display, 
                        use_container_width=True, 
                        height=400,
                        column_config={
                            "Planificado": st.column_config.NumberColumn(format="%d"),
                            "Producido": st.column_config.NumberColumn(format="%d"),
                            "Pendiente": st.column_config.NumberColumn(format="%d"),
                        },
                        hide_index=True
                    )
                    
                    csv = df_display.to_csv(index=False)
                    st.download_button("📥 Descargar Tabla (CSV)", csv, "ordenes_produccion.csv", "text/csv")

            st.markdown("---")
            # Re-filtrar para el selector por si se aplicó filtro de planta
            ofs_for_selector = df.to_dict('records')
            
            options = {
                f"{of.get('name', 'OF')} — {clean_name(of.get('product_id'))} ({of.get('Planta', '-')})": of["id"]
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

    # Detalle de OF seleccionada
    if st.session_state["production_current_of"]:
        _render_detalle_of(st.session_state["production_current_of"])


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

    # Detalle de la orden
    st.markdown("### 📋 Detalle de la Orden")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="info-card">
            <h4>📌 Información General</h4>
            <div class="info-row">
                <span class="info-label">Responsable</span>
                <span class="info-value">{clean_name(of.get('user_id'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Cliente</span>
                <span class="info-value">{clean_name(of.get('x_studio_clientes')) if clean_name(of.get('x_studio_clientes')) != 'False' else 'N/A'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Producto</span>
                <span class="info-value">{clean_name(of.get('product_id'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Estado</span>
                <span class="info-value">{get_state_label(of.get('state'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Sala</span>
                <span class="info-value">{clean_name(of.get('x_studio_sala_de_proceso'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Tipo Proceso</span>
                <span class="info-value">{"Sala" if any(s in str(of.get('x_studio_sala_de_proceso','')).lower() for s in ['sala 1', 'sala 2', 'sala 3', 'sala 4', 'sala 5', 'sala 6', 'linea retail', 'granel', 'proceso']) else "Congelado"}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Planta</span>
                <span class="info-value">{detectar_planta(of.get('name'))}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="info-card">
            <h4>⏱️ Tiempos y Dotación</h4>
            <div class="info-row">
                <span class="info-label">Hora inicio</span>
                <span class="info-value">{format_fecha(of.get('x_studio_inicio_de_proceso'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Hora término</span>
                <span class="info-value">{format_fecha(of.get('x_studio_termino_de_proceso'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Horas detención</span>
                <span class="info-value">{format_num(of.get('x_studio_horas_detencion_totales'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Dotación</span>
                <span class="info-value">{format_num(of.get('x_studio_dotacin'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Horas hombre</span>
                <span class="info-value">{format_num(of.get('x_studio_hh'))}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown(f"""
        <div class="info-card">
            <h4>📈 Eficiencia</h4>
            <div class="info-row">
                <span class="info-label">HH efectiva</span>
                <span class="info-value">{format_num(of.get('x_studio_hh_efectiva'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">KG/hora efectiva</span>
                <span class="info-value">{format_num(of.get('x_studio_kghora_efectiva'))}</span>
            </div>
            <div class="info-row">
                <span class="info-label">KG/HH efectiva</span>
                <span class="info-value">{format_num(of.get('x_studio_kghh_efectiva'))}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        po_asociada = clean_name(of.get('x_studio_po_asociada'))
        po_asociada_display = po_asociada if po_asociada not in ['-', 'False'] else 'N/A'
        st.markdown(f"""
        <div class="info-card">
            <h4>📦 PO Asociada</h4>
            <div class="info-row">
                <span class="info-label">Para PO</span>
                <span class="info-value">{'Sí' if of.get('x_studio_odf_es_para_una_po_en_particular') else 'No'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">PO asociada</span>
                <span class="info-value">{po_asociada_display}</span>
            </div>
            <div class="info-row">
                <span class="info-label">KG totales PO</span>
                <span class="info-value">{format_num(of.get('x_studio_kg_totales_po', 0))} kg</span>
            </div>
            <div class="info-row">
                <span class="info-label">KG consumidos</span>
                <span class="info-value">{format_num(of.get('x_studio_kg_consumidos_po', 0))} kg</span>
            </div>
            <div class="info-row">
                <span class="info-label">KG disponibles</span>
                <span class="info-value">{format_num(of.get('x_studio_kg_disponibles_po', 0))} kg</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # KPIs de Producción
    st.markdown("### 📊 KPIs de Producción")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
    kpi_col1.metric("KG Entrada (Fruta)", f"{kg_in:,.0f} kg")
    kpi_col2.metric("KG Salida (Producto)", f"{kg_out:,.0f} kg")
    kpi_col3.metric("Merma", f"{merma:,.0f} kg")
    kpi_col4.metric("Rendimiento", f"{rendimiento_val:.2f}%")
    kpi_col5.metric("Total PxQ", f"${total_pxq_comp + total_pxq_sub:,.2f}")

    # Gauge y resumen PxQ
    col_gauge, col_pxq = st.columns([2, 1])
    with col_gauge:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=rendimiento_val,
            number={"suffix": "%", "valueformat": ".2f"},
            gauge={
                "axis": {"range": [0, 120]},
                "bar": {"color": "#00cc66"},
                "steps": [
                    {"range": [0, 50], "color": "#ff4444"},
                    {"range": [50, 80], "color": "#ffb347"},
                    {"range": [80, 100], "color": "#00cc66"},
                    {"range": [100, 120], "color": "#00ff88"},
                ],
            }
        ))
        fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=280)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_pxq:
        st.markdown(f"""
        <div style='background:#1e1e1e;padding:20px;border-radius:12px;height:260px'>
            <h4 style='margin:0 0 16px 0;color:#00cc66'>Resumen PxQ</h4>
            <p style='margin:8px 0;font-size:1.1em'><span style='color:#888'>Componentes:</span> <b>${total_pxq_comp:,.2f}</b></p>
            <p style='margin:8px 0;font-size:1.1em'><span style='color:#888'>Subproductos:</span> <b>${total_pxq_sub:,.2f}</b></p>
            <hr style='border-color:#333;margin:16px 0'>
            <p style='margin:8px 0;font-size:1.3em'><span style='color:#888'>Total:</span> <b style='color:#00cc66'>${total_pxq_comp + total_pxq_sub:,.2f}</b></p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Tabs de componentes/subproductos/detenciones/consumo
    tab_comp, tab_sub, tab_det, tab_consumo = st.tabs([
        "Componentes", "Subproductos", "Detenciones", "Consumo"
    ])

    with tab_comp:
        render_component_tab(componentes, "componentes")

    with tab_sub:
        render_component_tab(subproductos_filtrados, "subproductos")

    with tab_det:
        if detenciones:
            df_det = pd.DataFrame([{
                "Responsable": clean_name(det.get("x_studio_responsable")),
                "Motivo": clean_name(det.get("x_motivodetencion")),
                "Hora inicio": format_fecha(det.get("x_horainiciodetencion")),
                "Hora fin": format_fecha(det.get("x_horafindetencion")),
                "Horas detención": format_num(det.get("x_studio_horas_de_detencin", 0) or 0),
            } for det in detenciones])
            st.dataframe(df_det, use_container_width=True, height=320)
        else:
            st.info("No hay detenciones registradas")

    with tab_consumo:
        if consumo:
            df_consumo = pd.DataFrame([{
                "Pallet": item.get("x_name", "N/A"),
                "Producto": item.get("producto", "Desconocido"),
                "Lote": item.get("lote", ""),
                "Tipo": item.get("type", "Desconocido"),
                "Hora inicio": format_fecha(item.get("x_studio_hora_inicio")),
                "Hora fin": format_fecha(item.get("x_studio_hora_fin")),
            } for item in consumo])
            st.dataframe(df_consumo, use_container_width=True, height=360)
        else:
            st.info("No hay registros de consumo")

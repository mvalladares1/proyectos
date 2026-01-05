"""
Tab: Gestión de Recepciones
Monitoreo de estados de validación y control de calidad.
"""
import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta
from .shared import fmt_numero, fmt_dinero, fmt_fecha, API_URL, get_validation_icon, get_qc_icon, fetch_gestion_data, fetch_gestion_overview


@st.fragment
def render(username: str, password: str):
    """
    Renderiza el contenido del tab Gestión de Recepciones.
    Fragment independiente para evitar re-renders al cambiar de tab.
    Mantiene button blocking para evitar múltiples consultas.
    """
    st.subheader("📋 Gestión de Recepciones MP")
    st.caption("Monitoreo de estados de validación y control de calidad")

    # Filtros en una sola fila
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
    with col1:
        fecha_inicio_g = st.date_input("Desde", datetime.now() - timedelta(days=7), format="DD/MM/YYYY", key="gestion_desde")
    with col2:
        fecha_fin_g = st.date_input("Hasta", datetime.now(), format="DD/MM/YYYY", key="gestion_hasta")
    with col3:
        status_filter = st.selectbox("Estado", ["Todos", "Validada", "Lista para validar", "Confirmada", "En espera", "Borrador"], key="gestion_status")
    with col4:
        qc_filter = st.selectbox("Control Calidad", ["Todos", "Con QC Aprobado", "Con QC Pendiente", "Sin QC", "QC Fallido"], key="gestion_qc")
    with col5:
        # Inicializar debounce state
        if 'gestion_search_debounce' not in st.session_state:
            st.session_state.gestion_search_debounce = ""
        
        search_text = st.text_input(
            "Buscar Albarán", 
            placeholder="Ej: WH/IN/00123", 
            key="gestion_search",
            help="🕒 Presiona Enter o haz clic en Consultar para buscar"
        )

    # Botones de acción
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn2:
        if st.button("🗑️ Limpiar caché", key="btn_clear_cache"):
            fetch_gestion_data.clear()
            fetch_gestion_overview.clear()
            st.toast("✅ Caché limpiado")
            st.rerun()

    # Cargar datos usando caché
    fecha_inicio_str = fecha_inicio_g.strftime("%Y-%m-%d")
    fecha_fin_str = fecha_fin_g.strftime("%Y-%m-%d")

    # SIEMPRE CARGAR (Auto-refresh)
    # Controlar si es carga inicial o refresco
    if True:
        st.session_state.gestion_loaded = True
        st.session_state.recep_gestion_loading = True
        
        try:
            # SKELETON LOADER
            skeleton = st.empty()
            with skeleton.container():
                st.markdown("""
                <div style="animation: pulse 1.5s infinite;">
                    <div style="display: flex; gap: 20px; margin-bottom: 20px;">
                        <div style="flex: 1; height: 100px; background-color: #f0f2f6; border-radius: 12px;"></div>
                        <div style="flex: 1; height: 100px; background-color: #f0f2f6; border-radius: 12px;"></div>
                        <div style="flex: 1; height: 100px; background-color: #f0f2f6; border-radius: 12px;"></div>
                        <div style="flex: 1; height: 100px; background-color: #f0f2f6; border-radius: 12px;"></div>
                    </div>
                     <div style="height: 400px; background-color: #f0f2f6; border-radius: 12px;"></div>
                </div>
                <style>@keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 0.3; } 100% { opacity: 0.6; } }</style>
                """, unsafe_allow_html=True)
            
            # with st.spinner("Cargando datos..."):
                # Usar funciones con caché (automáticamente devuelve caché si existe)
                overview = fetch_gestion_overview(username, password, fecha_inicio_str, fecha_fin_str)
                data_gestion = fetch_gestion_data(username, password, fecha_inicio_str, fecha_fin_str, 
                                                  status_filter, qc_filter, search_text if search_text else None)

                st.session_state.gestion_overview = overview
                st.session_state.gestion_data = data_gestion
                
                if not st.session_state.get('gestion_loaded_initial'):
                    st.session_state.gestion_loaded_initial = True
                    # st.toast("✅ Datos actualizados") 
        finally:
            skeleton.empty()
            st.session_state.recep_gestion_loading = False

    overview = st.session_state.gestion_overview
    data_gestion = st.session_state.gestion_data

    if overview:
        # KPIs
        st.markdown("### 📊 Resumen")
        kpi_cols = st.columns(6)
        with kpi_cols[0]:
            st.metric("Total Recepciones", overview['total_recepciones'])
        with kpi_cols[1]:
            st.metric("Validadas ✅", overview['validadas'])
        with kpi_cols[2]:
            st.metric("Listas para validar 🟡", overview['listas_validar'])
        with kpi_cols[3]:
            # Otras = Total - Validadas - Listas validar
            otras = overview['total_recepciones'] - (overview['validadas'] + overview['listas_validar'])
            st.metric("Confirmadas/Otras 🔵", otras)
        with kpi_cols[4]:
            st.metric("Con QC Aprobado ✅", overview['con_qc_aprobado'])
        with kpi_cols[5]:
            # Pendiente/Sin QC/Fallido = Total - Aprobado
            pend_otros = overview['total_recepciones'] - overview['con_qc_aprobado']
            st.metric("QC Pendientes/Resto 🟡", pend_otros)

        st.markdown("---")

    if data_gestion:
        st.subheader(f"📋 Recepciones ({len(data_gestion)})")

        df_g = pd.DataFrame(data_gestion)

        # Filtros de tabla
        with st.expander("🔍 Filtros de tabla", expanded=True):
            fc1, fc2, fc3, fc4 = st.columns(4)
            with fc1:
                productores = sorted(df_g['partner'].dropna().unique())
                prod_filter = st.multiselect("Productor", productores, default=[], placeholder="Todos", key="gestion_prod")
            with fc2:
                valid_opts = ["Todos"] + list(df_g['validation_status'].unique())
                valid_filter = st.selectbox("Estado Validación", valid_opts, key="tbl_valid")
            with fc3:
                qc_opts = ["Todos"] + list(df_g['qc_status'].unique())
                qc_tbl_filter = st.selectbox("Estado QC", qc_opts, key="tbl_qc")
            with fc4:
                pend_filter = st.selectbox("Con Pendientes", ["Todos", "Sí", "No"], key="tbl_pend_g")

            # Segunda fila de filtros
            fc5, fc6 = st.columns([1, 3])
            with fc5:
                guia_filter = st.text_input(
                    "🚚 Guía de Despacho", 
                    placeholder="Buscar por N° guía...",
                    key="gestion_guia_despacho"
                )

        # Leyenda
        st.caption("**Leyenda:** ✅ Completo | 🟡 Pendiente | 🔵 Confirmada | ⏳ En espera | ⚪ Sin datos | ❌ Cancelada/Fallido")

        # Aplicar filtros
        df_filtered = df_g.copy()
        if prod_filter:
            df_filtered = df_filtered[df_filtered['partner'].isin(prod_filter)]
        if valid_filter != "Todos":
            df_filtered = df_filtered[df_filtered['validation_status'] == valid_filter]
        if qc_tbl_filter != "Todos":
            df_filtered = df_filtered[df_filtered['qc_status'] == qc_tbl_filter]
        if pend_filter == "Sí":
            df_filtered = df_filtered[df_filtered['pending_users'].str.len() > 0]
        elif pend_filter == "No":
            df_filtered = df_filtered[df_filtered['pending_users'].str.len() == 0]

        # Filtro por Guía de Despacho
        if guia_filter:
            guia_col = 'guia_despacho' if 'guia_despacho' in df_filtered.columns else 'x_studio_gua_de_despacho'
            if guia_col in df_filtered.columns:
                df_filtered = df_filtered[df_filtered[guia_col].fillna('').astype(str).str.contains(guia_filter, case=False, na=False)]

        st.caption(f"Mostrando {len(df_filtered)} de {len(df_g)} recepciones")

        # Inicializar estado de página si no existe
        if 'gestion_page' not in st.session_state:
            st.session_state.gestion_page = 1

        # Vista (sin causar rerun)
        vista = st.radio("Vista", ["📊 Tabla compacta", "📋 Detalle con expanders"], horizontal=True, label_visibility="collapsed", key="vista_gestion")

        if vista == "📊 Tabla compacta":
            # Tabla compacta
            df_display = df_filtered[['name', 'date', 'partner', 'tipo_fruta', 'validation_status', 'qc_status', 'pending_users']].copy()

            df_display['Validación'] = df_display['validation_status'].apply(get_validation_icon)
            df_display['QC'] = df_display['qc_status'].apply(get_qc_icon)
            df_display['Pendientes'] = df_display['pending_users'].apply(lambda x: '⏳' if x else '✓')
            df_display['Fecha'] = df_display['date'].apply(fmt_fecha)

            df_final = df_display[['name', 'Fecha', 'partner', 'tipo_fruta', 'Validación', 'QC', 'Pendientes']].copy()
            df_final.columns = ['Albarán', 'Fecha', 'Productor', 'Tipo Fruta', 'Validación', 'QC', 'Pend.']

            st.dataframe(
                df_final, 
                use_container_width=True, 
                hide_index=True, 
                height=450,
                column_config={
                    "Albarán": st.column_config.TextColumn(width="medium"),
                    "Fecha": st.column_config.TextColumn(width="small"),
                    "Productor": st.column_config.TextColumn(width="large"),
                    "Tipo Fruta": st.column_config.TextColumn(width="small"),
                    "Validación": st.column_config.TextColumn(width="small"),
                    "QC": st.column_config.TextColumn(width="small"),
                    "Pend.": st.column_config.TextColumn(width="small"),
                }
            )
        else:
            # Vista con expanders y paginación
            ITEMS_PER_PAGE = 15
            total_items = len(df_filtered)
            total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

            # Inicializar estado de página
            if 'gestion_page' not in st.session_state:
                st.session_state.gestion_page = 1

            # Asegurar que la página esté en rango válido
            if st.session_state.gestion_page > total_pages:
                st.session_state.gestion_page = 1

            # Navegación de páginas con selectbox (más estable que number_input)
            col_nav1, col_nav2 = st.columns([3, 1])
            with col_nav1:
                st.markdown(f"**{total_items} recepciones** en {total_pages} páginas")
            with col_nav2:
                page_options = list(range(1, total_pages + 1))
                current_idx = st.session_state.gestion_page - 1
                selected_page = st.selectbox(
                    "Página", page_options, 
                    index=min(current_idx, len(page_options) - 1),
                    key="gestion_page_select",
                    label_visibility="collapsed"
                )
                st.session_state.gestion_page = selected_page

            start_idx = (st.session_state.gestion_page - 1) * ITEMS_PER_PAGE
            end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)

            for idx, row in df_filtered.iloc[start_idx:end_idx].iterrows():
                valid_icon = get_validation_icon(row['validation_status'])
                qc_icon = get_qc_icon(row['qc_status'])
                pend_icon = "⏳" if row.get('pending_users', '') else "✓"

                fecha_rec = fmt_fecha(row.get('date', ''))
                header = f"{valid_icon}{qc_icon}{pend_icon} **{row['name']}** | {fecha_rec} | {row['partner'][:30]} | {row.get('tipo_fruta', '-')}"

                with st.expander(header, expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**Fecha:** {fmt_fecha(row['date'])}")
                        st.markdown(f"**Productor:** {row['partner']}")
                        st.markdown(f"**Guía Despacho:** {row.get('guia_despacho', '-')}")
                    with col2:
                        st.markdown(f"**Estado:** {valid_icon} {row['validation_status']}")
                        st.markdown(f"**Tipo Fruta:** {row.get('tipo_fruta', '-')}")
                    with col3:
                        st.markdown(f"**Control Calidad:** {qc_icon} {row['qc_status']}")
                        if row.get('calific_final'):
                            st.markdown(f"**Calificación:** {row['calific_final']}")
                        if row.get('jefe_calidad'):
                            st.markdown(f"**Jefe Calidad:** {row['jefe_calidad']}")

                    st.markdown("---")

                    # Detalle de pendientes/validaciones
                    c1, c2 = st.columns(2)
                    with c1:
                        validated = row.get('validated_by', '')
                        if validated:
                            st.success(f"✅ **Validado por:** {validated}")
                        else:
                            if row['validation_status'] == 'Validada':
                                st.success("✅ Recepción validada")
                            else:
                                st.info("Pendiente de validación")
                    with c2:
                        pending = row.get('pending_users', '')
                        if pending:
                            st.warning(f"⏳ **Pendiente de:** {pending}")
                        else:
                            st.success("✓ Sin pendientes de aprobación")

                    # Link a Odoo
                    picking_id = row.get('picking_id', '')
                    if picking_id:
                        odoo_url = f"https://riofuturo.server98c6e.oerpondemand.net/web#id={picking_id}&menu_id=350&cids=1&action=540&active_id=164&model=stock.picking&view_type=form"
                        st.markdown(f"🔗 [Abrir en Odoo]({odoo_url})")

        # Export
        st.markdown("---")
        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_g.to_excel(writer, sheet_name='Gestión Recepciones', index=False)
            st.download_button("📥 Descargar Excel", buffer.getvalue(), "gestion_recepciones.xlsx", 
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except:
            st.download_button("📥 Descargar CSV", df_g.to_csv(index=False).encode('utf-8'), "gestion_recepciones.csv", "text/csv")
    else:
        st.info("Haz clic en **Consultar Gestión** para cargar los datos.")

        with st.expander("ℹ️ ¿Cómo funciona?"):
            st.markdown("""
            ### Gestión de Recepciones MP

            Este módulo te permite monitorear el estado de las recepciones de materia prima:

            | Estado | Descripción |
            |--------|-------------|
            | ✅ **Validada** | Recepción completada y validada en Odoo |
            | 🟡 **Lista para validar** | Productos asignados, lista para validar |
            | 🔵 **Confirmada** | Confirmada, esperando disponibilidad |
            | ⏳ **En espera** | Esperando otra operación |
            | ⚪ **Borrador** | En estado borrador |

            ### Control de Calidad

            | Estado | Descripción |
            |--------|-------------|
            | ✅ **Con QC Aprobado** | Tiene control de calidad completado |
            | 🟡 **Con QC Pendiente** | Tiene QC pero está pendiente |
            | 🔴 **QC Fallido** | El control de calidad falló |
            | ⚪ **Sin QC** | No tiene control de calidad asociado |
            """)

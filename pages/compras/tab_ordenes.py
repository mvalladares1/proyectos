"""
Tab: Órdenes de Compra
Gestión de órdenes de compra con filtros, KPIs y exportación.
"""
import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta

from .shared import API_URL, fmt_numero, fmt_moneda, fmt_fecha, get_approval_color, get_receive_color
from .shared import fetch_compras_overview, fetch_compras_ordenes


def render(username: str, password: str):
    """Renderiza el contenido del tab Órdenes de Compra."""
    st.subheader("Gestión de Órdenes de Compra")
    
    # Filtros
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
    with col1:
        fecha_inicio = st.date_input("Desde", datetime.now() - timedelta(days=7), format="DD/MM/YYYY", key="po_desde")
    with col2:
        fecha_fin = st.date_input("Hasta", datetime.now(), format="DD/MM/YYYY", key="po_hasta")
    with col3:
        status_filter = st.selectbox("Aprobación", ["Todos", "Aprobada", "Parcialmente aprobada", "En revisión", "Rechazada"])
    with col4:
        receive_filter = st.selectbox("Recepción", ["Todos", "No recepcionada", "Recepción parcial", "Recepcionada totalmente", "No se recepciona"])
    with col5:
        search_text = st.text_input("Buscar PO", placeholder="Ej: OC08123")
    
    if st.button("🔄 Consultar POs", type="primary", disabled=st.session_state.compras_loading):
        st.session_state.compras_loading = True
        try:
            # Progress bar personalizado
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("⏳ Fase 1/4: Conectando con Odoo...")
            progress_bar.progress(25)
            
            # Llamadas cacheadas
            st.session_state.compras_data = fetch_compras_overview(username, password)
            
            status_text.text("⏳ Fase 2/4: Consultando órdenes...")
            progress_bar.progress(50)
            
            # Parámetros para órdenes
            state = None if status_filter == "Todos" else status_filter
            date_from = fecha_inicio.strftime("%Y-%m-%d")
            date_to = fecha_fin.strftime("%Y-%m-%d")
            
            status_text.text("⏳ Fase 3/4: Procesando datos...")
            progress_bar.progress(75)
            
            st.session_state.compras_ordenes = fetch_compras_ordenes(
                username, password, 
                state=state,
                date_from=date_from,
                date_to=date_to
            )
            
            status_text.text("✅ Fase 4/4: Completado")
            progress_bar.progress(100)
            st.toast("✅ Datos cargados correctamente", icon="✅")
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"Error: {e}")
            st.toast(f"❌ Error al cargar datos: {str(e)[:100]}", icon="❌")
        finally:
            st.session_state.compras_loading = False
            st.rerun()
    
    data = st.session_state.get('compras_data')
    ordenes = st.session_state.get('compras_ordenes')
    
    if data:
        # KPIs
        kpi_cols = st.columns(5)
        with kpi_cols[0]:
            st.metric("Total POs", data['total_pos'])
        with kpi_cols[1]:
            st.metric("Monto Total", fmt_moneda(data['monto_total']))
        with kpi_cols[2]:
            st.metric("Monto Aprobado", fmt_moneda(data['monto_aprobado']))
        with kpi_cols[3]:
            st.metric("Monto Pendiente", fmt_moneda(data['monto_pendiente']))
        with kpi_cols[4]:
            st.metric("% Aprobadas", f"{data['pct_aprobadas']:.1f}%")
        
        st.markdown("---")
        
        if ordenes:
            st.subheader(f"📋 Órdenes de Compra ({len(ordenes)})")
            
            df = pd.DataFrame(ordenes)
            
            # === FILTROS DE COLUMNA ===
            with st.expander("🔍 Filtros de tabla", expanded=True):
                fc1, fc2, fc3, fc4, fc5 = st.columns(5)
                with fc1:
                    proveedores = sorted(df['partner'].unique())
                    prov_filter = st.multiselect("Proveedor", proveedores, default=[], placeholder="Todos")
                with fc2:
                    creadores = sorted([c for c in df['created_by'].unique() if c])
                    creador_filter = st.multiselect("Creado por", creadores, default=[], placeholder="Todos", key="creador_filter")
                with fc3:
                    aprob_opts = ["Todos"] + list(df['approval_status'].unique())
                    aprob_filter = st.selectbox("Estado Aprobación", aprob_opts, key="tbl_aprob")
                with fc4:
                    recep_opts = ["Todos"] + list(df['receive_status'].unique())
                    recep_filter = st.selectbox("Estado Recepción", recep_opts, key="tbl_recep")
                with fc5:
                    pend_filter = st.selectbox("Con Pendientes", ["Todos", "Sí", "No"], key="tbl_pend")
            
            # Leyenda
            st.caption("**Leyenda:** ✅ Completo | 🟡 Parcial | ⏳ Pendiente | 🔴 Sin recepción | ➖ N/A | ✓ Sin pendientes")
            
            # Aplicar filtros
            df_filtered = df.copy()
            if prov_filter:
                df_filtered = df_filtered[df_filtered['partner'].isin(prov_filter)]
            if creador_filter:
                df_filtered = df_filtered[df_filtered['created_by'].isin(creador_filter)]
            if aprob_filter != "Todos":
                df_filtered = df_filtered[df_filtered['approval_status'] == aprob_filter]
            if recep_filter != "Todos":
                df_filtered = df_filtered[df_filtered['receive_status'] == recep_filter]
            if pend_filter == "Sí":
                df_filtered = df_filtered[df_filtered['pending_users'].str.len() > 0]
            elif pend_filter == "No":
                df_filtered = df_filtered[df_filtered['pending_users'].str.len() == 0]
            
            st.caption(f"Mostrando {len(df_filtered)} de {len(df)} órdenes")
            
            # Opción de vista
            vista = st.radio("Vista", ["📊 Tabla compacta", "📋 Detalle con expanders"], horizontal=True, label_visibility="collapsed")
            
            if vista == "📊 Tabla compacta":
                _render_tabla_compacta(df_filtered)
            else:
                _render_vista_expanders(df_filtered)
            
            # Export
            st.markdown("---")
            try:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='Compras', index=False)
                st.download_button("📥 Descargar Excel", buffer.getvalue(), "ordenes_compra.xlsx", 
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except:
                st.download_button("📥 Descargar CSV", df.to_csv(index=False).encode('utf-8'), "ordenes_compra.csv", "text/csv")
    else:
        st.info("Haz clic en **Consultar POs** para cargar los datos.")


def _render_tabla_compacta(df_filtered):
    """Renderiza tabla compacta de órdenes con paginación."""
    ITEMS_PER_PAGE = 50
    total_items = len(df_filtered)
    total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    
    # Inicializar página
    if 'ordenes_page' not in st.session_state:
        st.session_state.ordenes_page = 1
    if st.session_state.ordenes_page > total_pages:
        st.session_state.ordenes_page = 1
    
    # Navegación
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav2:
        st.session_state.ordenes_page = st.number_input(
            "Página",
            min_value=1,
            max_value=total_pages,
            value=st.session_state.ordenes_page,
            key="ordenes_page_input"
        )
    
    st.caption(f"Mostrando {total_items} órdenes | Página {st.session_state.ordenes_page} de {total_pages}")
    
    # Paginar datos
    start_idx = (st.session_state.ordenes_page - 1) * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
    df_page = df_filtered.iloc[start_idx:end_idx]
    
    df_display = df_page[['name', 'date_order', 'partner', 'created_by', 'amount_total', 'approval_status', 'receive_status', 'pending_users']].copy()
    
    df_display['Aprobación'] = df_display['approval_status'].apply(lambda x: {
        'Aprobada': '✅', 'Parcialmente aprobada': '🟡', 'En revisión': '⏳', 'Rechazada': '❌'
    }.get(x, '⚪'))
    df_display['Recepción'] = df_display['receive_status'].apply(lambda x: {
        'Recepcionada totalmente': '✅', 'Recepción parcial': '🟡', 'No recepcionada': '🔴', 'No se recepciona': '➖'
    }.get(x, '⚪'))
    df_display['Pendientes'] = df_display['pending_users'].apply(lambda x: '⏳' if x else '✓')
    
    df_final = df_display[['name', 'date_order', 'partner', 'created_by', 'amount_total', 'Aprobación', 'Recepción', 'Pendientes']].copy()
    df_final.columns = ['PO', 'Fecha', 'Proveedor', 'Creado por', 'Monto', 'Aprobación', 'Recepción', 'Pend.']
    df_final['Monto'] = df_final['Monto'].apply(fmt_moneda)
    df_final['Fecha'] = df_final['Fecha'].apply(fmt_fecha)
    
    st.dataframe(
        df_final, 
        use_container_width=True, 
        hide_index=True, 
        height=450,
        column_config={
            "PO": st.column_config.TextColumn(width="small"),
            "Fecha": st.column_config.TextColumn(width="small"),
            "Proveedor": st.column_config.TextColumn(width="medium"),
            "Creado por": st.column_config.TextColumn(width="medium"),
            "Monto": st.column_config.TextColumn(width="small"),
            "Aprobación": st.column_config.TextColumn(width="small"),
            "Recepción": st.column_config.TextColumn(width="small"),
            "Pend.": st.column_config.TextColumn(width="small"),
        }
    )


def _render_vista_expanders(df_filtered):
    """Renderiza vista con expanders y paginación."""
    ITEMS_PER_PAGE = 15
    total_items = len(df_filtered)
    total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    
    if 'po_page' not in st.session_state:
        st.session_state.po_page = 1
    
    if st.session_state.po_page > total_pages:
        st.session_state.po_page = 1
    
    col_nav1, col_nav2 = st.columns([3, 1])
    with col_nav1:
        st.markdown(f"**{total_items} órdenes** en {total_pages} páginas")
    with col_nav2:
        page_options = list(range(1, total_pages + 1))
        current_idx = st.session_state.po_page - 1
        selected_page = st.selectbox(
            "Página", page_options,
            index=min(current_idx, len(page_options) - 1),
            key="po_page_select",
            label_visibility="collapsed"
        )
        st.session_state.po_page = selected_page
    
    start_idx = (st.session_state.po_page - 1) * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
    
    for idx, row in df_filtered.iloc[start_idx:end_idx].iterrows():
        aprob_icon = get_approval_color(row['approval_status'])
        recep_icon = get_receive_color(row['receive_status'])
        pend_icon = "⏳" if row.get('pending_users', '') else "✓"
        
        fecha_oc = fmt_fecha(row.get('date_order', ''))
        header = f"{aprob_icon}{recep_icon}{pend_icon} **{row['name']}** | {fecha_oc} | {row['partner'][:30]} | {fmt_moneda(row['amount_total'])}"
        
        with st.expander(header, expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Fecha:** {fmt_fecha(row['date_order'])}")
                st.markdown(f"**Monto:** {fmt_moneda(row['amount_total'])}")
                if row.get('currency_original') == 'USD' and row.get('amount_original'):
                    st.caption(f"💱 Original: USD$ {fmt_numero(row['amount_original'], 2)} × {fmt_numero(row['exchange_rate'], 2)}")
            with col2:
                st.markdown(f"**Aprobación:** {aprob_icon} {row['approval_status']}")
                st.markdown(f"**Recepción:** {recep_icon} {row['receive_status']}")
            with col3:
                st.markdown(f"**Creado por:** {row.get('created_by', '-')}")
                st.markdown(f"**Estado PO:** {row['po_state']}")
            
            st.markdown("---")
            
            aprobado = row.get('approved_by', '')
            pendiente = row.get('pending_users', '')
            
            c1, c2 = st.columns(2)
            with c1:
                if aprobado:
                    st.success(f"✅ **Aprobado por:** {aprobado}")
                else:
                    st.info("Sin aprobaciones aún")
            with c2:
                if pendiente:
                    st.warning(f"⏳ **Pendiente de:** {pendiente}")
                else:
                    st.success("✓ Sin pendientes")
            
            po_id = row.get('po_id', '')
            if po_id:
                odoo_url = f"https://riofuturo.server98c6e.oerpondemand.net/web#id={po_id}&menu_id=411&cids=1&action=627&model=purchase.order&view_type=form"
                st.markdown(f"🔗 [Abrir en Odoo]({odoo_url})")
            
            lineas = row.get('lineas', [])
            if lineas:
                st.markdown("---")
                st.markdown("**📦 Productos de la OC:**")
                df_lineas = pd.DataFrame(lineas)
                df_lineas['Subtotal'] = df_lineas['subtotal'].apply(fmt_moneda)
                df_lineas['P. Unit'] = df_lineas['price_unit'].apply(fmt_moneda)
                df_display = df_lineas[['producto', 'cantidad', 'P. Unit', 'Subtotal']].rename(columns={
                    'producto': 'Producto', 'cantidad': 'Cant.'
                })
                st.dataframe(df_display, use_container_width=True, hide_index=True, height=150)

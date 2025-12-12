"""
Compras: Dashboard de Órdenes de Compra (PO) y Líneas de Crédito
Estados de aprobación, recepción y monitoreo de crédito.
"""
import streamlit as st
import pandas as pd
import requests
import altair as alt
from datetime import datetime, timedelta
import sys
import os
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.auth import proteger_pagina, get_credenciales


# --- Funciones de formateo chileno ---
def fmt_numero(valor, decimales=0):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "0"
    try:
        if decimales > 0:
            formatted = f"{valor:,.{decimales}f}"
        else:
            formatted = f"{valor:,.0f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except:
        return str(valor)


def fmt_moneda(valor):
    return f"${fmt_numero(valor, 0)}"


def fmt_fecha(fecha_str):
    """Convierte YYYY-MM-DD a DD/MM/YYYY"""
    if not fecha_str:
        return ""
    try:
        if isinstance(fecha_str, str) and len(fecha_str) >= 10:
            # Tomar solo los primeros 10 caracteres (YYYY-MM-DD)
            fecha_str = fecha_str[:10]
            parts = fecha_str.split("-")
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return fecha_str
    except:
        return str(fecha_str)


def get_approval_color(status):
    return {'Aprobada': '🟢', 'Parcialmente aprobada': '🟡', 'En revisión': '⚪', 'Rechazada': '🔴'}.get(status, '⚪')


def get_receive_color(status):
    return {'Recepcionada totalmente': '🟢', 'Recepción parcial': '🟡', 'No recepcionada': '🔴', 'No se recepciona': '⚪'}.get(status, '⚪')


# Configuración de página
st.set_page_config(page_title="Compras", page_icon="🛒", layout="wide")

if not proteger_pagina():
    st.stop()

username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales.")
    st.stop()

st.title("🛒 Compras y Líneas de Crédito")

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# --- Estado de sesión ---
for key in ['compras_data', 'compras_ordenes', 'lineas_credito', 'lineas_resumen']:
    if key not in st.session_state:
        st.session_state[key] = None

# --- TABS PRINCIPALES ---
tab_po, tab_credito = st.tabs(["📋 Órdenes de Compra", "💳 Líneas de Crédito"])

# =====================================================
#                  TAB 1: ÓRDENES DE COMPRA
# =====================================================
with tab_po:
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
    
    if st.button("🔄 Consultar POs", type="primary"):
        params = {
            "username": username, "password": password,
            "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
            "fecha_fin": fecha_fin.strftime("%Y-%m-%d")
        }
        if status_filter != "Todos":
            params["status_filter"] = status_filter
        if receive_filter != "Todos":
            params["receive_filter"] = receive_filter
        if search_text:
            params["search_text"] = search_text
        
        with st.spinner("Cargando..."):
            try:
                resp = requests.get(f"{API_URL}/api/v1/compras/overview", params={
                    "username": username, "password": password,
                    "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
                    "fecha_fin": fecha_fin.strftime("%Y-%m-%d")
                }, timeout=120)
                if resp.status_code == 200:
                    st.session_state.compras_data = resp.json()
                
                resp = requests.get(f"{API_URL}/api/v1/compras/ordenes", params=params, timeout=120)
                if resp.status_code == 200:
                    st.session_state.compras_ordenes = resp.json()
            except Exception as e:
                st.error(f"Error: {e}")
    
    data = st.session_state.compras_data
    ordenes = st.session_state.compras_ordenes
    
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
                fc1, fc2, fc3, fc4 = st.columns(4)
                with fc1:
                    proveedores = sorted(df['partner'].unique())
                    prov_filter = st.multiselect("Proveedor", proveedores, default=[], placeholder="Todos")
                with fc2:
                    aprob_opts = ["Todos"] + list(df['approval_status'].unique())
                    aprob_filter = st.selectbox("Estado Aprobación", aprob_opts, key="tbl_aprob")
                with fc3:
                    recep_opts = ["Todos"] + list(df['receive_status'].unique())
                    recep_filter = st.selectbox("Estado Recepción", recep_opts, key="tbl_recep")
                with fc4:
                    pend_filter = st.selectbox("Con Pendientes", ["Todos", "Sí", "No"], key="tbl_pend")
            
            # Leyenda (debajo de filtros)
            st.caption("**Leyenda:** ✅ Completo | 🟡 Parcial | ⏳ Pendiente | 🔴 Sin recepción | ➖ N/A | ✓ Sin pendientes")
            
            # Aplicar filtros
            df_filtered = df.copy()
            if prov_filter:
                df_filtered = df_filtered[df_filtered['partner'].isin(prov_filter)]
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
                # Tabla compacta con columnas esenciales
                df_display = df_filtered[['name', 'date_order', 'partner', 'amount_total', 'approval_status', 'receive_status', 'pending_users']].copy()
                
                # Columnas de estado con emoji compacto
                df_display['Aprobación'] = df_display['approval_status'].apply(lambda x: {
                    'Aprobada': '✅', 'Parcialmente aprobada': '🟡', 'En revisión': '⏳', 'Rechazada': '❌'
                }.get(x, '⚪'))
                df_display['Recepción'] = df_display['receive_status'].apply(lambda x: {
                    'Recepcionada totalmente': '✅', 'Recepción parcial': '🟡', 'No recepcionada': '🔴', 'No se recepciona': '➖'
                }.get(x, '⚪'))
                df_display['Pendientes'] = df_display['pending_users'].apply(lambda x: '⏳' if x else '✓')
                
                # Solo columnas esenciales
                df_final = df_display[['name', 'date_order', 'partner', 'amount_total', 'Aprobación', 'Recepción', 'Pendientes']].copy()
                df_final.columns = ['PO', 'Fecha', 'Proveedor', 'Monto', 'Aprobación', 'Recepción', 'Pendientes']
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
                        "Proveedor": st.column_config.TextColumn(width="large"),
                        "Monto": st.column_config.TextColumn(width="medium"),
                        "Aprobación": st.column_config.TextColumn(width="small"),
                        "Recepción": st.column_config.TextColumn(width="small"),
                        "Pendientes": st.column_config.TextColumn(width="small"),
                    }
                )
            
            else:
                # Vista con expanders - con paginación
                ITEMS_PER_PAGE = 10
                total_items = len(df_filtered)
                total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
                
                # Control de página en session state
                if 'po_page' not in st.session_state:
                    st.session_state.po_page = 1
                
                # Navegación de páginas
                col_prev, col_info, col_next = st.columns([1, 2, 1])
                with col_prev:
                    if st.button("⬅️ Anterior", disabled=st.session_state.po_page <= 1):
                        st.session_state.po_page -= 1
                        st.rerun()
                with col_info:
                    st.markdown(f"**Página {st.session_state.po_page} de {total_pages}** ({total_items} órdenes)")
                with col_next:
                    if st.button("Siguiente ➡️", disabled=st.session_state.po_page >= total_pages):
                        st.session_state.po_page += 1
                        st.rerun()
                
                # Calcular rango de items
                start_idx = (st.session_state.po_page - 1) * ITEMS_PER_PAGE
                end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
                
                # Mostrar solo los items de la página actual
                for idx, row in df_filtered.iloc[start_idx:end_idx].iterrows():
                    aprob_icon = get_approval_color(row['approval_status'])
                    recep_icon = get_receive_color(row['receive_status'])
                    pend_icon = "⏳" if row.get('pending_users', '') else "✓"
                    
                    # Header con fecha formateada DD/MM/YYYY
                    fecha_oc = fmt_fecha(row.get('date_order', ''))
                    header = f"{aprob_icon}{recep_icon}{pend_icon} **{row['name']}** | {fecha_oc} | {row['partner'][:30]} | {fmt_moneda(row['amount_total'])}"
                    
                    with st.expander(header, expanded=False):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown(f"**Fecha:** {fmt_fecha(row['date_order'])}")
                            st.markdown(f"**Monto:** {fmt_moneda(row['amount_total'])}")
                        with col2:
                            st.markdown(f"**Aprobación:** {aprob_icon} {row['approval_status']}")
                            st.markdown(f"**Recepción:** {recep_icon} {row['receive_status']}")
                        with col3:
                            st.markdown(f"**Estado PO:** {row['po_state']}")
                        
                        st.markdown("---")
                        
                        # Detalle de aprobaciones
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
                        
                        # Detalle de productos (si viene precargado)
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

# =====================================================
#                  TAB 2: LÍNEAS DE CRÉDITO
# =====================================================
with tab_credito:
    st.subheader("💳 Monitoreo de Líneas de Crédito")
    st.caption("Proveedores con línea de crédito activa y uso actual")
    
    # Filtro de fecha para nueva temporada
    col_fecha, col_btn = st.columns([2, 1])
    with col_fecha:
        from datetime import datetime, timedelta
        # Default: inicio de temporada (20 de noviembre 2025)
        fecha_default = datetime(2025, 11, 20).date()
        fecha_desde_lc = st.date_input(
            "📅 Calcular uso desde", 
            value=fecha_default,
            help="Solo considera facturas y OCs desde esta fecha para calcular el uso de línea"
        )
    with col_btn:
        st.write("")  # Spacer
        cargar_lineas = st.button("🔄 Cargar Líneas de Crédito", type="primary", use_container_width=True)
    
    if cargar_lineas:
        with st.spinner("Cargando líneas de crédito..."):
            try:
                params = {
                    "username": username, 
                    "password": password,
                    "fecha_desde": fecha_desde_lc.isoformat()
                }
                
                resp = requests.get(f"{API_URL}/api/v1/compras/lineas-credito/resumen", params=params, timeout=120)
                if resp.status_code == 200:
                    st.session_state.lineas_resumen = resp.json()
                
                resp = requests.get(f"{API_URL}/api/v1/compras/lineas-credito", params=params, timeout=120)
                if resp.status_code == 200:
                    st.session_state.lineas_credito = resp.json()
            except Exception as e:
                st.error(f"Error: {e}")
    
    resumen = st.session_state.lineas_resumen
    lineas = st.session_state.lineas_credito
    
    if resumen:
        # KPIs de líneas de crédito
        kpi_cols = st.columns(5)
        with kpi_cols[0]:
            st.metric("Proveedores", resumen['total_proveedores'])
        with kpi_cols[1]:
            st.metric("Línea Total", fmt_moneda(resumen['total_linea']))
        with kpi_cols[2]:
            st.metric("Usado", fmt_moneda(resumen['total_usado']))
        with kpi_cols[3]:
            st.metric("Disponible", fmt_moneda(resumen['total_disponible']))
        with kpi_cols[4]:
            pct = resumen['pct_uso_global']
            color = "🔴" if pct >= 80 else "🟡" if pct >= 60 else "🟢"
            st.metric(f"Uso Global {color}", f"{pct:.1f}%")
        
        # Estados
        st.markdown("---")
        status_cols = st.columns(3)
        with status_cols[0]:
            st.metric("🔴 Sin Cupo", resumen['sin_cupo'])
        with status_cols[1]:
            st.metric("🟡 Cupo Bajo", resumen['cupo_bajo'])
        with status_cols[2]:
            st.metric("🟢 Disponibles", resumen['disponibles'])
        
        st.markdown("---")
    
    if lineas:
        st.markdown("### Detalle por Proveedor")
        
        # === FILTROS ===
        with st.expander("🔍 Filtros", expanded=True):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                estado_opts = ["Todos", "🔴 Sin cupo", "🟡 Cupo bajo", "🟢 Disponible"]
                estado_filter = st.selectbox("Estado", estado_opts, key="lc_estado")
            with fc2:
                proveedores = sorted([l['partner_name'] for l in lineas])
                prov_filter = st.multiselect("Proveedor", proveedores, default=[], placeholder="Todos", key="lc_prov")
            with fc3:
                buscar = st.text_input("Buscar proveedor", placeholder="Nombre...", key="lc_buscar")
        
        # Aplicar filtros
        lineas_filtradas = lineas.copy()
        
        if estado_filter != "Todos":
            estado_map = {"🔴 Sin cupo": "Sin cupo", "🟡 Cupo bajo": "Cupo bajo", "🟢 Disponible": "Disponible"}
            lineas_filtradas = [l for l in lineas_filtradas if l['estado'] == estado_map.get(estado_filter)]
        
        if prov_filter:
            lineas_filtradas = [l for l in lineas_filtradas if l['partner_name'] in prov_filter]
        
        if buscar:
            lineas_filtradas = [l for l in lineas_filtradas if buscar.lower() in l['partner_name'].lower()]
        
        st.caption(f"Mostrando {len(lineas_filtradas)} de {len(lineas)} proveedores")
        
        for prov in lineas_filtradas:
            alerta = prov['alerta']
            pct = prov['pct_uso']
            pct_disp = max(100 - pct, 0)
            
            # Header simple: solo nombre + % usado + % disponible
            nombre = prov['partner_name']
            header = alerta + " " + nombre + " - Usado: " + str(int(pct)) + "% - Disponible: " + str(int(pct_disp)) + "%"
            
            with st.expander(header):
                # Barra de progreso con estado
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.progress(min(pct / 100, 1.0))
                with col2:
                    if prov['estado'] == 'Sin cupo':
                        st.error(prov['estado'])
                    elif prov['estado'] == 'Cupo bajo':
                        st.warning(prov['estado'])
                    else:
                        st.success(prov['estado'])
                
                # KPIs en cards visuales
                st.markdown("---")
                kp_cols = st.columns(5)
                with kp_cols[0]:
                    st.metric("Linea Total", fmt_moneda(prov['linea_total']))
                with kp_cols[1]:
                    st.metric("Facturas", fmt_moneda(prov.get('monto_facturas', 0)), 
                             delta=str(prov.get('num_facturas', 0)) + " pend.", delta_color="off")
                with kp_cols[2]:
                    st.metric("OCs Sin Fact.", fmt_moneda(prov.get('monto_ocs', 0)),
                             delta=str(prov.get('num_ocs', 0)) + " OCs", delta_color="off")
                with kp_cols[3]:
                    st.metric("Total Usado", fmt_moneda(prov['monto_usado']),
                             delta=str(int(pct)) + "%", delta_color="inverse")
                with kp_cols[4]:
                    st.metric("Disponible", fmt_moneda(max(prov['disponible'], 0)),
                             delta=str(int(pct_disp)) + "%", delta_color="normal")
                
                st.markdown("---")
                
                # Detalle unificado (facturas + OCs)
                detalle = prov.get('detalle', [])
                if detalle:
                    st.markdown("##### 📋 Detalle de compromisos")
                    df_det = pd.DataFrame(detalle)
                    df_display = df_det[['tipo', 'numero', 'monto', 'fecha', 'estado']].copy()
                    df_display.columns = ['Tipo', 'Documento', 'Monto', 'Fecha', 'Estado']
                    df_display['Monto'] = df_display['Monto'].apply(fmt_moneda)
                    df_display['Fecha'] = df_display['Fecha'].apply(fmt_fecha)
                    
                    st.dataframe(df_display, use_container_width=True, hide_index=True,
                                column_config={
                                    "Tipo": st.column_config.TextColumn(width="small"),
                                    "Documento": st.column_config.TextColumn(width="medium"),
                                    "Monto": st.column_config.TextColumn(width="medium"),
                                    "Fecha": st.column_config.TextColumn(width="small"),
                                    "Estado": st.column_config.TextColumn(width="medium"),
                                })
                else:
                    st.success("✅ Sin compromisos pendientes")
        
        # Gráfico resumen
        st.markdown("---")
        st.markdown("### Uso de Líneas de Crédito (%)")
        
        df_lineas = pd.DataFrame([{
            'Proveedor': l['partner_name'][:25],
            'Uso (%)': min(l['pct_uso'], 200),  # Limitar a 200% para visualización
            'Linea': l['linea_total'],
            'Usado': l['monto_usado'],
            'Color': '#dc3545' if l['pct_uso'] >= 80 else ('#ffc107' if l['pct_uso'] >= 60 else '#28a745')
        } for l in lineas])
        
        # Ordenar por % uso descendente
        df_lineas = df_lineas.sort_values('Uso (%)', ascending=False)
        
        bars = alt.Chart(df_lineas).mark_bar().encode(
            x=alt.X('Proveedor:N', sort=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('Uso (%):Q', title='% Uso', scale=alt.Scale(domain=[0, max(df_lineas['Uso (%)'].max() + 10, 100)])),
            color=alt.Color('Color:N', scale=None),
            tooltip=['Proveedor', 'Uso (%)', 'Linea', 'Usado']
        ).properties(height=350)
        
        # Línea de referencia al 100%
        line_100 = alt.Chart(pd.DataFrame({'y': [100]})).mark_rule(
            color='white', strokeDash=[5, 5], strokeWidth=2
        ).encode(y='y:Q')
        
        st.altair_chart(bars + line_100, use_container_width=True)
    else:
        if not resumen:
            st.info("Haz clic en **Cargar Líneas de Crédito** para ver los datos.")
            
            with st.expander("ℹ️ ¿Cómo funciona?"):
                st.markdown("""
                ### Líneas de Crédito
                
                Este módulo monitorea proveedores con el campo `x_studio_linea_credito_activa = True`.
                
                | Concepto | Descripción |
                |----------|-------------|
                | **Línea Total** | Campo `x_studio_linea_credito_monto` del proveedor |
                | **Usado** | Suma de facturas con `amount_residual > 0` |
                | **Disponible** | Línea Total - Usado |
                
                ### Alertas
                
                - 🔴 **Sin cupo**: Disponible ≤ 0
                - 🟡 **Cupo bajo**: Uso ≥ 80%
                - 🟢 **Disponible**: Uso < 80%
                
                ### Objetivo
                
                Identificar qué facturas pagar primero para liberar cupo de crédito.
                """)

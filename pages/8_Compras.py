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
                df_display['Aprob'] = df_display['approval_status'].apply(lambda x: {
                    'Aprobada': '✅', 'Parcialmente aprobada': '🟡', 'En revisión': '⏳', 'Rechazada': '❌'
                }.get(x, '⚪'))
                df_display['Recep'] = df_display['receive_status'].apply(lambda x: {
                    'Recepcionada totalmente': '✅', 'Recepción parcial': '🟡', 'No recepcionada': '🔴', 'No se recepciona': '➖'
                }.get(x, '⚪'))
                df_display['Pend'] = df_display['pending_users'].apply(lambda x: '⏳' if x else '✓')
                
                # Solo columnas esenciales
                df_final = df_display[['name', 'date_order', 'partner', 'amount_total', 'Aprob', 'Recep', 'Pend']].copy()
                df_final.columns = ['PO', 'Fecha', 'Proveedor', 'Monto', '✓', '📦', '⏳']
                df_final['Monto'] = df_final['Monto'].apply(fmt_moneda)
                
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
                        "✓": st.column_config.TextColumn("Aprob", width="small"),
                        "📦": st.column_config.TextColumn("Recep", width="small"),
                        "⏳": st.column_config.TextColumn("Pend", width="small"),
                    }
                )
                
                # Leyenda
                st.caption("**Leyenda:** ✅ Completo | 🟡 Parcial | ⏳ Pendiente | 🔴 Sin recepción | ➖ N/A | ✓ Sin pendientes")
            
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
                    
                    header = f"{aprob_icon}{recep_icon}{pend_icon} **{row['name']}** | {row['partner'][:35]} | {fmt_moneda(row['amount_total'])}"
                    
                    with st.expander(header, expanded=False):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown(f"**Fecha:** {row['date_order']}")
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
    
    if st.button("🔄 Cargar Líneas de Crédito", type="primary"):
        with st.spinner("Cargando líneas de crédito..."):
            try:
                params = {"username": username, "password": password}
                
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
        
        for prov in lineas:
            alerta = prov['alerta']
            pct = prov['pct_uso']
            
            with st.expander(f"{alerta} **{prov['partner_name']}** | Línea: {fmt_moneda(prov['linea_total'])} | Usado: {fmt_moneda(prov['monto_usado'])} ({pct:.0f}%) | Disponible: {fmt_moneda(prov['disponible'])}"):
                # Gráfico de barra de progreso visual
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.progress(min(pct / 100, 1.0))
                with col2:
                    st.markdown(f"**{prov['estado']}**")
                
                # KPIs del proveedor
                kp_cols = st.columns(4)
                with kp_cols[0]:
                    st.metric("Línea Total", fmt_moneda(prov['linea_total']))
                with kp_cols[1]:
                    st.metric("Monto Usado", fmt_moneda(prov['monto_usado']))
                with kp_cols[2]:
                    st.metric("Disponible", fmt_moneda(prov['disponible']))
                with kp_cols[3]:
                    st.metric("Facturas Pendientes", prov['num_facturas'])
                
                # Detalle de facturas
                if prov['facturas']:
                    st.markdown("**📄 Facturas Pendientes de Pago:**")
                    df_fact = pd.DataFrame(prov['facturas'])
                    df_display = df_fact[['numero', 'monto_pendiente', 'fecha_vencimiento', 'origen']].copy()
                    df_display.columns = ['Factura', 'Pendiente', 'Vencimiento', 'Origen OC']
                    df_display['Pendiente'] = df_display['Pendiente'].apply(fmt_moneda)
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                else:
                    st.info("Sin facturas pendientes")
        
        # Gráfico resumen
        st.markdown("---")
        st.markdown("### Uso de Líneas de Crédito")
        
        df_lineas = pd.DataFrame([{
            'Proveedor': l['partner_name'][:30],
            'Usado': l['monto_usado'],
            'Disponible': max(l['disponible'], 0),
            '% Uso': l['pct_uso']
        } for l in lineas])
        
        chart = alt.Chart(df_lineas).mark_bar().encode(
            x=alt.X('Proveedor:N', sort='-y'),
            y=alt.Y('Usado:Q', title='Monto'),
            color=alt.condition(
                alt.datum['% Uso'] >= 80,
                alt.value('#dc3545'),
                alt.condition(alt.datum['% Uso'] >= 60, alt.value('#ffc107'), alt.value('#28a745'))
            ),
            tooltip=['Proveedor', 'Usado', 'Disponible', '% Uso']
        ).properties(height=300)
        
        st.altair_chart(chart, use_container_width=True)
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

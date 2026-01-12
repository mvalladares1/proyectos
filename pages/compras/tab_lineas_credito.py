"""
Tab: Líneas de Crédito
Monitoreo de líneas de crédito activas y uso por proveedor.
"""
import streamlit as st
import pandas as pd
import requests
import altair as alt
from datetime import datetime

from .shared import API_URL, fmt_numero, fmt_moneda, fmt_fecha
from .shared import fetch_lineas_credito_resumen, fetch_lineas_credito


@st.fragment
def render(username: str, password: str):
    """Renderiza el contenido del tab Líneas de Crédito."""
    st.subheader("💳 Monitoreo de Líneas de Crédito")
    st.caption("Proveedores con línea de crédito activa y uso actual")
    
    # Filtro de fecha para nueva temporada
    col_fecha, col_btn = st.columns([2, 1])
    with col_fecha:
        fecha_default = datetime(2025, 11, 20).date()
        fecha_desde_lc = st.date_input(
            "📅 Calcular uso desde", 
            value=fecha_default,
            format="DD/MM/YYYY",
            help="Solo considera facturas y OCs desde esta fecha para calcular el uso de línea"
        )
    with col_btn:
        st.write("")
        cargar_lineas = st.button("🔄 Cargar Líneas de Crédito", type="primary", use_container_width=True, disabled=st.session_state.lineas_loading)
    
    if cargar_lineas:
        st.session_state.lineas_loading = True
        try:
            # Progress bar personalizado
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("⏳ Fase 1/4: Conectando con Odoo...")
            progress_bar.progress(25)
            
            status_text.text("⏳ Fase 2/4: Consultando líneas de crédito...")
            progress_bar.progress(50)
            
            # Llamadas cacheadas
            st.session_state.lineas_resumen = fetch_lineas_credito_resumen(username, password)
            
            status_text.text("⏳ Fase 3/4: Procesando datos...")
            progress_bar.progress(75)
            
            st.session_state.lineas_credito = fetch_lineas_credito(username, password)
            
            status_text.text("✅ Fase 4/4: Completado")
            progress_bar.progress(100)
            st.toast("✅ Líneas de crédito cargadas", icon="✅")
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"Error: {e}")
            st.toast(f"❌ Error al cargar líneas: {str(e)[:100]}", icon="❌")
        finally:
            st.session_state.lineas_loading = False
    
    resumen = st.session_state.get('lineas_resumen')
    lineas = st.session_state.get('lineas_credito')
    
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
            _render_proveedor_card(prov)
        
        # Gráfico resumen
        _render_grafico_uso(lineas)
    else:
        if not resumen:
            st.info("Haz clic en **Cargar Líneas de Crédito** para ver los datos.")
            _render_info_ayuda()


def _render_proveedor_card(prov):
    """Renderiza tarjeta de proveedor."""
    alerta = prov['alerta']
    pct = prov['pct_uso']
    pct_disp = max(100 - pct, 0)
    
    nombre = prov['partner_name']
    header = alerta + " " + nombre + " - Usado: " + str(int(pct)) + "% - Disponible: " + str(int(pct_disp)) + "%"
    
    with st.expander(header):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.progress(min(pct / 100, 1.0))
        with col2:
            estado_texto = f"{prov['estado']} ({int(pct)}%)"
            if prov['estado'] == 'Sin cupo':
                st.error(estado_texto)
            elif prov['estado'] == 'Cupo bajo':
                st.warning(estado_texto)
            else:
                st.success(estado_texto)
        
        st.markdown("---")
        kp_cols = st.columns(6)
        with kp_cols[0]:
            st.metric("Linea Total", fmt_moneda(prov['linea_total']))
        with kp_cols[1]:
            st.metric("Facturas", fmt_moneda(prov.get('monto_facturas', 0)), 
                     delta=str(prov.get('num_facturas', 0)) + " pend.", delta_color="off")
        with kp_cols[2]:
            monto_recep_total = prov.get('monto_recepciones', 0) + prov.get('monto_preparadas', 0)
            num_recep_total = prov.get('num_recepciones', 0) + prov.get('num_preparadas', 0)
            st.metric("Recepciones", fmt_moneda(monto_recep_total),
                     delta=str(num_recep_total) + " recep.", delta_color="off")
        with kp_cols[3]:
            st.metric("OCs Tentativas", fmt_moneda(prov.get('monto_ocs', 0)),
                     delta=str(prov.get('num_ocs', 0)) + " OCs", delta_color="off")
        with kp_cols[4]:
            st.metric("Total Usado", fmt_moneda(prov['monto_usado']),
                     delta=str(int(pct)) + "%", delta_color="inverse")
        with kp_cols[5]:
            st.metric("Disponible", fmt_moneda(max(prov['disponible'], 0)),
                     delta=str(int(pct_disp)) + "%", delta_color="normal")
        
        st.markdown("---")
        
        detalle = prov.get('detalle', [])
        if detalle:
            _render_detalle_compromisos(detalle)
        else:
            st.success("✅ Sin compromisos pendientes")


def _render_detalle_compromisos(detalle):
    """Renderiza tabla de compromisos (facturas + OCs)."""
    st.markdown("##### 📋 Detalle de compromisos")
    df_det = pd.DataFrame(detalle)
    
    def format_monto_con_conversion(row):
        monto_str = fmt_moneda(row['monto'])
        if row.get('moneda_original') == 'USD' and row.get('monto_original'):
            return f"{monto_str} (USD$ {fmt_numero(row['monto_original'], 2)})"
        return monto_str
    
    ODOO_BASE = "https://riofuturo.server98c6e.oerpondemand.net/web#"
    def get_odoo_link(row):
        if row.get('picking_id'):
            return f"{ODOO_BASE}id={row['picking_id']}&menu_id=350&cids=1&action=540&model=stock.picking&view_type=form"
        elif row.get('oc_id'):
            return f"{ODOO_BASE}id={row['oc_id']}&menu_id=411&cids=1&action=627&model=purchase.order&view_type=form"
        return None
    
    df_det['odoo_link'] = df_det.apply(get_odoo_link, axis=1)
    
    df_display = df_det[['tipo', 'numero', 'monto', 'fecha', 'estado', 'odoo_link']].copy()
    df_display.columns = ['Tipo', 'Documento', 'Monto', 'Fecha', 'Estado', 'Odoo']
    
    df_display['Monto'] = df_det.apply(format_monto_con_conversion, axis=1)
    df_display['Fecha'] = df_display['Fecha'].apply(fmt_fecha)
    
    has_usd = any(d.get('moneda_original') == 'USD' for d in detalle)
    if has_usd:
        tipo_cambio = next((d.get('tipo_cambio') for d in detalle if d.get('tipo_cambio')), None)
        if tipo_cambio:
            st.caption(f"💱 Tipo de cambio: 1 USD = ${fmt_numero(tipo_cambio, 2)} CLP")
    
    st.dataframe(df_display, use_container_width=True, hide_index=True,
                column_config={
                    "Tipo": st.column_config.TextColumn(width="small"),
                    "Documento": st.column_config.TextColumn(width="medium"),
                    "Monto": st.column_config.TextColumn(width="large"),
                    "Fecha": st.column_config.TextColumn(width="small"),
                    "Estado": st.column_config.TextColumn(width="medium"),
                    "Odoo": st.column_config.LinkColumn(width="small", display_text="🔗 Abrir"),
                })


def _render_grafico_uso(lineas):
    """Renderiza gráfico de uso de líneas de crédito."""
    st.markdown("---")
    st.markdown("### Uso de Líneas de Crédito (%)")
    
    df_lineas = pd.DataFrame([{
        'Proveedor': l['partner_name'][:25],
        'Uso (%)': min(l['pct_uso'], 200),
        'Linea': l['linea_total'],
        'Usado': l['monto_usado'],
        'Color': '#dc3545' if l['pct_uso'] >= 80 else ('#ffc107' if l['pct_uso'] >= 60 else '#28a745')
    } for l in lineas])
    
    df_lineas = df_lineas.sort_values('Uso (%)', ascending=False)
    
    bars = alt.Chart(df_lineas).mark_bar().encode(
        x=alt.X('Proveedor:N', sort=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Uso (%):Q', title='% Uso', scale=alt.Scale(domain=[0, max(df_lineas['Uso (%)'].max() + 10, 100)])),
        color=alt.Color('Color:N', scale=None),
        tooltip=['Proveedor', 'Uso (%)', 'Linea', 'Usado']
    ).properties(height=350)
    
    line_100 = alt.Chart(pd.DataFrame({'y': [100]})).mark_rule(
        color='white', strokeDash=[5, 5], strokeWidth=2
    ).encode(y='y:Q')
    
    st.altair_chart(bars + line_100, use_container_width=True)


def _render_info_ayuda():
    """Renderiza información de ayuda."""
    with st.expander("ℹ️ ¿Cómo funciona?"):
        st.markdown("""
        ### Líneas de Crédito
        
        Este módulo monitorea proveedores con el campo `x_studio_linea_credito_activa = True`.
        
        | Concepto | Descripción |
        |----------|-------------|
        | **Línea Total** | Campo `x_studio_linea_credito_monto` del proveedor |
        | **Facturas** | Facturas con `amount_residual > 0` (pendientes pago) |
        | **Recep. Sin Fact.** | Recepciones reales (stock.move done) sin facturar |
        | **OCs Tentativas** | OCs confirmadas sin factura (solo informativo) |
        | **Usado** | Facturas + Recepciones reales (**no incluye OCs tentativas**) |
        | **Disponible** | Línea Total - Usado |
        
        ### Alertas
        
        - 🔴 **Sin cupo**: Disponible ≤ 0
        - 🟡 **Cupo bajo**: Uso ≥ 80%
        - 🟢 **Disponible**: Uso < 80%
        
        ### Objetivo
        
        Identificar qué facturas pagar primero para liberar cupo de crédito.
        """)

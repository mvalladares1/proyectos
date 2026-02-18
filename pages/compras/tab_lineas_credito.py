"""
Tab: Líneas de Crédito
Monitoreo de líneas de crédito activas y uso por proveedor.

Calcula el uso real de la línea basado en:
- Facturas pendientes de pago
- Recepciones sin facturar (material recibido)
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
            help="Filtra facturas y recepciones desde esta fecha para el cálculo de uso de línea"
        )
    with col_btn:
        st.write("")
        cargar_lineas = st.button("🔄 Cargar Líneas de Crédito", type="primary", use_container_width=True, disabled=st.session_state.lineas_loading)
    
    if cargar_lineas:
        st.session_state.lineas_loading = True
        st.session_state.lineas_fecha_desde = fecha_desde_lc.strftime("%Y-%m-%d")
        try:
            # Progress bar personalizado
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("⏳ Fase 1/4: Conectando con Odoo...")
            progress_bar.progress(25)
            
            status_text.text("⏳ Fase 2/4: Consultando líneas de crédito...")
            progress_bar.progress(50)
            
            fecha_str = fecha_desde_lc.strftime("%Y-%m-%d")
            
            # Llamadas cacheadas con fecha
            st.session_state.lineas_resumen = fetch_lineas_credito_resumen(username, password, fecha_str)
            
            status_text.text("⏳ Fase 3/4: Procesando datos...")
            progress_bar.progress(75)
            
            st.session_state.lineas_credito = fetch_lineas_credito(username, password, fecha_str)
            
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
    fecha_filtrada = st.session_state.get('lineas_fecha_desde')
    
    if resumen:
        # Mostrar fecha del filtro aplicado
        if fecha_filtrada:
            st.info(f"📅 Datos filtrados desde: **{fecha_filtrada}** (facturas y recepciones)")
        
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
        kp_cols = st.columns(5)
        with kp_cols[0]:
            st.metric("Línea Total", fmt_moneda(prov['linea_total']))
        with kp_cols[1]:
            st.metric("💰 Facturas", fmt_moneda(prov.get('monto_facturas', 0)), 
                     delta=str(prov.get('num_facturas', 0)) + " pend.", delta_color="off",
                     help="Facturas pendientes de pago")
        with kp_cols[2]:
            st.metric("📦 Recepciones", fmt_moneda(prov.get('monto_recepciones', 0)),
                     delta=str(prov.get('num_recepciones', 0)) + " OCs", delta_color="off",
                     help="Material recibido pendiente de facturar")
        with kp_cols[3]:
            st.metric("🔴 Total Usado", fmt_moneda(prov['monto_usado']),
                     delta=str(int(pct)) + "%", delta_color="inverse",
                     help="Facturas + Recepciones sin facturar")
        with kp_cols[4]:
            st.metric("🟢 Disponible", fmt_moneda(max(prov['disponible'], 0)),
                     delta=str(int(pct_disp)) + "%", delta_color="normal",
                     help="Cupo disponible para nuevas compras")
        
        st.markdown("---")
        
        detalle = prov.get('detalle', [])
        if detalle:
            tab_detalle, tab_ocs = st.tabs(["📋 Detalle de Compromisos", "📦 Vista por OC"])
            with tab_detalle:
                _render_detalle_compromisos(detalle)
            with tab_ocs:
                _render_vista_por_oc(detalle)
        else:
            st.success("✅ Sin compromisos pendientes")


def _render_detalle_compromisos(detalle):
    """Renderiza tabla de compromisos (facturas + recepciones + OCs tentativas)."""
    st.markdown("##### 📋 Detalle de compromisos")
    st.caption("💰 Facturas pendientes + 📦 Recepciones sin facturar + 📄 OCs tentativas (informativas)")
    df_det = pd.DataFrame(detalle)
    
    def format_monto_con_conversion(row):
        monto_str = fmt_moneda(row['monto'])
        if row.get('moneda_original') == 'USD' and row.get('monto_original'):
            return f"{monto_str} (USD$ {fmt_numero(row['monto_original'], 2)})"
        return monto_str
    
    ODOO_BASE = "https://riofuturo.server98c6e.oerpondemand.net/web#"
    def get_odoo_link(row):
        # Solo OCs tienen link (las recepciones se referencian por OC)
        if row.get('oc_id'):
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


def _render_vista_por_oc(detalle):
    """Renderiza vista agrupada por OC mostrando pagado vs pendiente."""
    st.markdown("##### 📦 Desglose por Orden de Compra")
    st.caption("Agrupación de compromisos por OC: recibido, facturado y pendiente")
    
    ODOO_BASE = "https://riofuturo.server98c6e.oerpondemand.net/web#"
    
    # Agrupar datos por OC
    ocs_data = {}
    facturas_sin_oc = []
    
    for item in detalle:
        tipo = item.get('tipo', '')
        numero = item.get('numero', '')
        monto = float(item.get('monto', 0))
        fecha = item.get('fecha', '')
        origen = item.get('origen', '')  # Para facturas, puede contener nombre de OC
        oc_id = item.get('oc_id')
        
        if tipo == 'Factura':
            # Intentar asociar factura a OC vía origen
            # El origen puede ser múltiple "OC1, OC2", tomar el primero
            oc_ref = None
            if origen and origen.strip():
                oc_ref = origen.split(',')[0].strip()
            
            if oc_ref:
                if oc_ref not in ocs_data:
                    ocs_data[oc_ref] = {
                        'oc_name': oc_ref,
                        'oc_id': oc_id,  # Usar el oc_id que ahora viene del backend
                        'monto_recibido': 0,
                        'monto_facturado': monto,
                        'monto_tentativo': 0,
                        'facturas': [numero],
                        'fecha_min': fecha,
                    }
                else:
                    ocs_data[oc_ref]['monto_facturado'] += monto
                    ocs_data[oc_ref]['facturas'].append(numero)
                    # Actualizar oc_id si no lo teníamos
                    if oc_id and not ocs_data[oc_ref]['oc_id']:
                        ocs_data[oc_ref]['oc_id'] = oc_id
            else:
                facturas_sin_oc.append({'numero': numero, 'monto': monto, 'fecha': fecha})
                
        elif tipo == 'Recepción':
            oc_name = numero  # El número de recepción ES el nombre de la OC
            if oc_name not in ocs_data:
                ocs_data[oc_name] = {
                    'oc_name': oc_name,
                    'oc_id': oc_id,
                    'monto_recibido': monto,
                    'monto_facturado': 0,
                    'monto_tentativo': 0,
                    'facturas': [],
                    'fecha_min': fecha,
                }
            else:
                ocs_data[oc_name]['monto_recibido'] += monto
                ocs_data[oc_name]['oc_id'] = ocs_data[oc_name]['oc_id'] or oc_id
                
        elif tipo == 'OC Tentativa':
            oc_name = numero
            if oc_name not in ocs_data:
                ocs_data[oc_name] = {
                    'oc_name': oc_name,
                    'oc_id': oc_id,
                    'monto_recibido': 0,
                    'monto_facturado': 0,
                    'monto_tentativo': monto,
                    'facturas': [],
                    'fecha_min': fecha,
                }
            else:
                ocs_data[oc_name]['monto_tentativo'] += monto
                ocs_data[oc_name]['oc_id'] = ocs_data[oc_name]['oc_id'] or oc_id
    
    if not ocs_data and not facturas_sin_oc:
        st.info("No hay datos de OC para mostrar")
        return
    
    # Crear DataFrame para mostrar
    rows = []
    for oc_name, data in ocs_data.items():
        monto_pendiente = data['monto_recibido']  # Lo recibido sin facturar
        
        odoo_link = None
        if data['oc_id']:
            odoo_link = f"{ODOO_BASE}id={data['oc_id']}&menu_id=411&cids=1&action=627&model=purchase.order&view_type=form"
        
        rows.append({
            'OC': oc_name,
            'Recibido sin Fact.': data['monto_recibido'],
            'Facturado Pend. Pago': data['monto_facturado'],
            'OC Tentativa': data['monto_tentativo'],
            'Total Compromiso': data['monto_recibido'] + data['monto_facturado'] + data['monto_tentativo'],
            'Facturas': ', '.join(data['facturas']) if data['facturas'] else '-',
            'Fecha': data['fecha_min'],
            'odoo_link': odoo_link,
        })
    
    # Agregar facturas sin OC asociada
    for f in facturas_sin_oc:
        rows.append({
            'OC': '(Sin OC)',
            'Recibido sin Fact.': 0,
            'Facturado Pend. Pago': f['monto'],
            'OC Tentativa': 0,
            'Total Compromiso': f['monto'],
            'Facturas': f['numero'],
            'Fecha': f['fecha'],
            'odoo_link': None,
        })
    
    df_ocs = pd.DataFrame(rows)
    df_ocs = df_ocs.sort_values('Total Compromiso', ascending=False)
    
    # Formatear montos
    df_display = df_ocs.copy()
    df_display['Recibido sin Fact.'] = df_ocs['Recibido sin Fact.'].apply(lambda x: fmt_moneda(x) if x > 0 else '-')
    df_display['Facturado Pend. Pago'] = df_ocs['Facturado Pend. Pago'].apply(lambda x: fmt_moneda(x) if x > 0 else '-')
    df_display['OC Tentativa'] = df_ocs['OC Tentativa'].apply(lambda x: fmt_moneda(x) if x > 0 else '-')
    df_display['Total Compromiso'] = df_ocs['Total Compromiso'].apply(fmt_moneda)
    df_display['Fecha'] = df_ocs['Fecha'].apply(fmt_fecha)
    
    st.dataframe(df_display, use_container_width=True, hide_index=True,
                column_config={
                    "OC": st.column_config.TextColumn(width="medium"),
                    "Recibido sin Fact.": st.column_config.TextColumn(width="medium", help="Material recibido pendiente de facturar"),
                    "Facturado Pend. Pago": st.column_config.TextColumn(width="medium", help="Facturas emitidas pendientes de pago"),
                    "OC Tentativa": st.column_config.TextColumn(width="medium", help="OC sin recepciones (informativo)"),
                    "Total Compromiso": st.column_config.TextColumn(width="medium"),
                    "Facturas": st.column_config.TextColumn(width="large"),
                    "Fecha": st.column_config.TextColumn(width="small"),
                    "odoo_link": st.column_config.LinkColumn(width="small", display_text="🔗 Ver OC"),
                })
    
    # Resumen rápido
    total_recibido = sum(r['Recibido sin Fact.'] for r in rows if isinstance(r['Recibido sin Fact.'], (int, float)))
    total_recibido = sum(d['monto_recibido'] for d in ocs_data.values())
    total_facturado = sum(d['monto_facturado'] for d in ocs_data.values())
    total_facturado += sum(f['monto'] for f in facturas_sin_oc)
    total_tentativo = sum(d['monto_tentativo'] for d in ocs_data.values())
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📦 Total Recibido sin Facturar", fmt_moneda(total_recibido))
    with col2:
        st.metric("💰 Total Facturado Pend. Pago", fmt_moneda(total_facturado))
    with col3:
        st.metric("📄 Total OCs Tentativas", fmt_moneda(total_tentativo), help="Solo informativo, no afecta el cupo")


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
        ### 📊 Líneas de Crédito
        
        Este módulo monitorea proveedores con línea de crédito activa en Odoo.
        
        | Concepto | Descripción |
        |----------|-------------|
        | **Línea Total** | Monto máximo de crédito otorgado al proveedor |
        | **💰 Facturas** | Facturas pendientes de pago (`amount_residual > 0`) |
        | **📦 Recepciones** | Material recibido pendiente de facturar (de líneas de OC) |
        | **📄 OCs Tentativas** | OCs sin recepción ni factura (solo informativo en detalle) |
        | **🔴 Usado** | Facturas + Recepciones (**compromiso real**) |
        | **🟢 Disponible** | Línea Total - Usado |
        
        ### 🚦 Alertas de Estado
        
        - 🔴 **Sin cupo**: Disponible ≤ 0 (no se puede comprar más)
        - 🟡 **Cupo bajo**: Uso ≥ 80% (próximo a agotar crédito)
        - 🟢 **Disponible**: Uso < 80% (crédito saludable)
        
        ### 💡 ¿Qué incluye "Recepciones sin facturar"?
        
        Se calcula desde las líneas de órdenes de compra:
        - `qty_received`: Cantidad física recibida en bodega
        - `qty_invoiced`: Cantidad ya facturada
        - `Pendiente`: (qty_received - qty_invoiced) × precio_unitario
        
        Esto ya incluye TODAS las recepciones físicas realizadas, sin importar el estado del picking.
        
        ### 🎯 Objetivo
        
        Identificar proveedores críticos y qué facturas pagar para liberar cupo de crédito.
        """)

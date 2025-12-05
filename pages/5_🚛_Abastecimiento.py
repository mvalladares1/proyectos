"""
Control de Gestión - Programa de Abastecimiento
Integrado en la estructura modular del proyecto (usa `shared.odoo_client` y `backend.services`).
"""
import streamlit as st
import pandas as pd
from shared.odoo_client import get_odoo_client
from backend.services import abastecimiento_data_service as data_service
from backend.services import abastecimiento_recepcion_service as recepcion_service

st.set_page_config(page_title="Control de Gestión, Programa de Abastecimiento", layout="wide")

st.title("🚛 Control de Gestión, Programa de Abastecimiento")


@st.cache_resource
def get_connector():
    return get_odoo_client()


client = get_connector()


if not client:
    st.error("No se pudo conectar a Odoo. Verificar variables en .env")
    st.stop()


with st.spinner("Cargando datos..."):
    # Fetch raw purchase orders from Odoo via service
    po_data = data_service.get_purchase_orders(client)

    uploaded_budget = st.sidebar.file_uploader("📂 1. Presupuesto Actual (Excel)", type=["xlsx"] )
    uploaded_dates = st.sidebar.file_uploader("📅 2. Archivo de Fechas (FecHAS.xlsx)", type=["xlsx"] )
    uploaded_future = st.sidebar.file_uploader("📈 3. Presupuesto Futuro (Ej: PPTO's 2026.xlsx)", type=["xlsx"] )

    if uploaded_budget and uploaded_dates and uploaded_future:
        try:
            budget_data = data_service.load_budget_data(uploaded_budget)
            dates_data = data_service.load_dates_data(uploaded_dates)
            future_budget_data = data_service.load_budget_2026_data(uploaded_future)
            st.sidebar.success("✅ Archivos cargados correctamente.")
        except ValueError as e:
            st.error(str(e))
            st.stop()
    else:
        st.warning("⚠️ Por favor, cargue TODOS los archivos requeridos (Presupuesto, Fechas, Futuro) para visualizar los datos.")
        st.stop()

    pricing_data = pd.DataFrame()
    static_data = pd.DataFrame()
    central_bank_data = data_service.get_central_bank_data()


# --- Filters (portado del original) ---
with st.container():
    col1, col2, col3 = st.columns(3)
    with col1:
        estados = ["Todas"]
        selected_estado = st.selectbox("🏷️ Estado", estados)
    with col2:
        manejos = ["Todas"]
        selected_manejo = st.selectbox("🌱 Manejo", manejos)
    with col3:
        with st.form(key="date_filter_form"):
            today = pd.Timestamp.now().date()
            start_default = pd.Timestamp(2022,1,1).date()
            end_default = pd.Timestamp(today.year,12,31).date()
            date_range = st.date_input("🗓️ Rango de Fechas", [start_default, end_default])
            submit_button = st.form_submit_button("Aplicar Fechas", use_container_width=True)
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Actualizar Datos", use_container_width=True):
        st.rerun()


# Apply basic filters to po_data (placeholders until static data mapping is available)
filtered_po = po_data.copy()
filtered_budget = budget_data.copy()
filtered_pricing = pricing_data.copy()

if selected_estado != "Todas":
    filtered_po = filtered_po[filtered_po.get('condition','') == selected_estado]

if selected_manejo != "Todas":
    filtered_po = filtered_po[filtered_po.get('labeling','') == selected_manejo]

# Product filter
col_prod, col_var = st.columns(2)
with col_prod:
    lista_productos = ["Todas"]
    selected_producto = st.selectbox("🍇 Producto", lista_productos)
with col_var:
    lista_variedades = ["Todas"]
    selected_variedad = st.selectbox("🧬 Variedad", lista_variedades)

if len(date_range) == 2:
    start_date, end_date = date_range
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    if not filtered_po.empty and 'date_planned' in filtered_po.columns:
        filtered_po['date_planned'] = pd.to_datetime(filtered_po['date_planned'])
        filtered_po = filtered_po[(filtered_po['date_planned'] >= start_date) & (filtered_po['date_planned'] <= end_date)]

# Tabs
tab_diario, tab_semanal = st.tabs(["📊 Diario", "📈 Semanal"]) 

with tab_diario:
    control_df = recepcion_service.get_control_presupuestario_data(filtered_po, filtered_budget)
    col_gauge, col_pmp = st.columns(2)
    with col_gauge:
        st.subheader("Avance Programa")
        if not control_df.empty and ('Total','Recepción') in control_df.columns:
            total_rec = filtered_po['qty_received'].sum() if not filtered_po.empty else 0
            try:
                total_ppto = control_df.loc[('Total',''), ('Total','PPTO 3')]
            except Exception:
                total_ppto = 0
            import plotly.graph_objects as go
            fig_gauge = go.Figure(go.Indicator(mode = "gauge+number", value = total_rec, domain = {'x':[0,1],'y':[0,1]}, title = {'text': "Avance Programa Abastecimiento"}, number = {'valueformat': ",.0f"}, gauge = {'axis': {'range': [None, total_ppto * 1.1 if total_ppto>0 else 100]}, 'bar': {'color': "#0091EA"}}))
            fig_gauge.update_layout(height=250, margin=dict(l=20,r=20,t=50,b=20))
            st.plotly_chart(fig_gauge, use_container_width=True)
    with col_pmp:
        if not filtered_po.empty:
            pmp_val, _ = recepcion_service.calculate_raw_pmp(filtered_po)
            formatted_pmp = f"{pmp_val:,.2f}".replace(",","X").replace(".",",").replace("X",".")
            st.markdown(f"<div style='padding:15px;border:1px solid #d0d0d0;border-radius:5px;text-align:center;background:white;'><div style='font-size:16px;'>Precio Medio Ponderado</div><div style='font-size:48px;font-weight:bold'>{formatted_pmp}</div></div>", unsafe_allow_html=True)

    st.subheader("Control Presupuestario")
    if not control_df.empty:
        format_dict = {}
        for col in control_df.columns:
            manejo, metric = col
            if metric == '%':
                format_dict[col] = "{:.0f}%"
            else:
                format_dict[col] = lambda x: "{:,.0f}".format(x).replace(",", ".")
        height = (len(control_df) + 1) * 35 + 3
        st.dataframe(control_df.style.format(format_dict), width="stretch", height=height)
    else:
        st.info("No hay datos para mostrar.")

    st.subheader("Precios contra presupuesto")
    price_comparison_df = recepcion_service.get_price_comparison_pivot(filtered_po, filtered_budget, central_bank_data=central_bank_data)
    if not price_comparison_df.empty:
        st.dataframe(price_comparison_df.style.format("${:,.2f}"), width="stretch")
    else:
        st.info("No hay datos de precios.")

    st.subheader("Curvas Diarias de Recepción")
    evolution_data = recepcion_service.get_stacked_evolution_data(filtered_po, filtered_budget, granularity='Diario') if hasattr(recepcion_service, 'get_stacked_evolution_data') else {}
    real_stacked = evolution_data.get('real_stacked', pd.DataFrame()) if isinstance(evolution_data, dict) else pd.DataFrame()
    ppto_stacked = evolution_data.get('ppto_stacked', pd.DataFrame()) if isinstance(evolution_data, dict) else pd.DataFrame()
    ppto_total = evolution_data.get('ppto_total', pd.DataFrame()) if isinstance(evolution_data, dict) else pd.DataFrame()
    if not real_stacked.empty or not ppto_total.empty:
        import plotly.graph_objects as go
        st.plotly_chart(go.Figure(), use_container_width=True)
    else:
        st.info("No hay datos de evolución.")

with tab_semanal:
    st.subheader("Evolución Semanal")
    evolution_df = recepcion_service.get_evolution_data(filtered_po, filtered_budget)
    if not evolution_df.empty:
        import plotly.graph_objects as go
        fig_evo = go.Figure()
        fig_evo.add_trace(go.Scatter(x=evolution_df['Date'], y=evolution_df['Real'], mode='lines', fill='tozeroy', name='Recepción Real', line=dict(color='#0091EA')))
        fig_evo.add_trace(go.Scatter(x=evolution_df['Date'], y=evolution_df['PPTO Original'], mode='lines', name='PPTO Original', line=dict(color='#1A237E', width=3)))
        fig_evo.add_trace(go.Scatter(x=evolution_df['Date'], y=evolution_df['v.2'], mode='lines', name='v.2', line=dict(color='#FF6D00', width=3)))
        fig_evo.update_layout(title='Curvas semanal de recepción', xaxis_title='Semana', yaxis_title='Kilos', height=400)
        st.plotly_chart(fig_evo, use_container_width=True)
    else:
        st.info('No hay datos de evolución.')

st.markdown('---')
if st.button('🔄 Actualizar Datos Odoo', use_container_width=True):
    st.rerun()

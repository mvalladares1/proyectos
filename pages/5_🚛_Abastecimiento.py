"""
Control de Gestión - Programa de Abastecimiento
Integrado en la estructura modular del proyecto (usa `shared.odoo_client` y `backend.services`).
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from shared.odoo_client import get_odoo_client
from shared.auth import proteger_pagina, get_credenciales
from backend.services import abastecimiento_data_service as data_service
from backend.services import abastecimiento_recepcion_service as recepcion_service

st.set_page_config(page_title="Control de Gestión, Programa de Abastecimiento", layout="wide")

# --- Custom CSS ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .stDataFrame {
        font-size: 0.8rem;
    }
    [data-testid="stFileUploader"] {
        padding-top: 0px;
        padding-bottom: 10px;
    }
    [data-testid="stFileUploader"] section {
        padding: 10px;
        min-height: 0px;
    }
</style>
""", unsafe_allow_html=True)

# Proteger la página (requiere login desde Home)
if not proteger_pagina():
    st.stop()

st.title("🚛 Control de Gestión, Programa de Abastecimiento")

# Obtener credenciales de la sesión
username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales. Por favor inicia sesión en Home.")
    st.stop()

# Conectar a Odoo con las credenciales de sesión
try:
    client = get_odoo_client(username=username, password=password)
except Exception as e:
    st.error(f"Error al conectar con Odoo: {e}")
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


# Cargar datos de precios estáticos
pricing_data = data_service.get_pricing_data()

# --- Filters (dinámicos desde po_data) ---
with st.container():
    col1, col2, col3 = st.columns(3)
    with col1:
        # Estado (Condition) - dinámico desde po_data
        if not po_data.empty and 'condition' in po_data.columns:
            unique_estados = sorted(po_data['condition'].dropna().unique().tolist())
        else:
            unique_estados = []
        estados = ["Todas"] + unique_estados
        selected_estado = st.selectbox("🏷️ Estado", estados, key='filter_estado')
        
    with col2:
        # Manejo (Labeling) - dinámico desde po_data
        if not po_data.empty and 'labeling' in po_data.columns:
            unique_manejos = sorted(po_data['labeling'].dropna().unique().tolist())
        else:
            unique_manejos = []
        manejos = ["Todas"] + unique_manejos
        selected_manejo = st.selectbox("🌱 Manejo", manejos, key='filter_manejo')
        
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

# Apply filters
filtered_po = po_data.copy()
filtered_budget = budget_data.copy()
filtered_pricing = pricing_data.copy()

if selected_estado != "Todas":
    filtered_po = filtered_po[filtered_po['condition'] == selected_estado]
    if 'ESTADO' in filtered_budget.columns:
        filtered_budget = filtered_budget[filtered_budget['ESTADO'] == selected_estado]
    if 'ESTADO' in filtered_pricing.columns:
        filtered_pricing = filtered_pricing[filtered_pricing['ESTADO'] == selected_estado]

if selected_manejo != "Todas":
    filtered_po = filtered_po[filtered_po['labeling'] == selected_manejo]
    if 'MANEJO' in filtered_budget.columns:
        filtered_budget = filtered_budget[filtered_budget['MANEJO'] == selected_manejo]
    if 'MANEJO' in filtered_pricing.columns:
        filtered_pricing = filtered_pricing[filtered_pricing['MANEJO'] == selected_manejo]

# Product filter - dinámico
col_prod, col_var = st.columns(2)
with col_prod:
    if not po_data.empty and 'product' in po_data.columns:
        unique_products = sorted(po_data['product'].dropna().unique().tolist())
    else:
        unique_products = []
    lista_productos = ["Todas"] + unique_products
    selected_producto = st.selectbox("🍇 Producto", lista_productos, key='filter_producto')
    
with col_var:
    if not po_data.empty and 'variety' in po_data.columns:
        unique_varieties = sorted(po_data['variety'].dropna().unique().tolist())
    else:
        unique_varieties = []
    lista_variedades = ["Todas"] + unique_varieties
    selected_variedad = st.selectbox("🧬 Variedad", lista_variedades, key='filter_variedad')

if selected_producto != "Todas":
    filtered_po = filtered_po[filtered_po['product'] == selected_producto]
    if 'PRODUCTO' in filtered_budget.columns:
        filtered_budget = filtered_budget[filtered_budget['PRODUCTO'] == selected_producto]
    if 'FRUTA' in filtered_pricing.columns:
        filtered_pricing = filtered_pricing[filtered_pricing['FRUTA'] == selected_producto]

if selected_variedad != "Todas":
    filtered_po = filtered_po[filtered_po['variety'] == selected_variedad]
    if 'VARIEDAD' in filtered_budget.columns:
        filtered_budget = filtered_budget[filtered_budget['VARIEDAD'] == selected_variedad]

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
            # Filtrar solo CONVENCIONAL y ORGANICO para PMP  
            pmp_df = filtered_po.copy()
            pmp_df = pmp_df[pmp_df['labeling'].isin(['CONVENCIONAL', 'ORGANICO'])]
            
            # Use Raw PMP (matches DAX formula without currency conversion)
            pmp_val, _ = recepcion_service.calculate_raw_pmp(pmp_df)
            
            # Format with comma as decimal separator
            formatted_pmp = f"{pmp_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            st.markdown(f"""
            <div style="
                border: 1px solid rgba(128, 128, 128, 0.3); 
                border-radius: 5px; 
                padding: 15px; 
                text-align: center; 
                background-color: rgba(128, 128, 128, 0.1);
                margin-top: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <div style="font-size: 16px; font-weight: 500; margin-bottom: 10px;">Precio Medio Ponderado</div>
                <div style="font-size: 48px; font-weight: bold; line-height: 1.2;">{formatted_pmp}</div>
                <div style="font-size: 14px; margin-top: 5px;">PMP</div>
            </div>
            """, unsafe_allow_html=True)

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

        fig_evo = go.Figure()

        # Define Colors for Fruits
        fruit_colors = {
            'ARANDANO': '#1A237E',
            'FRAMBUESA': '#F48FB1',
            'MORA': '#8E24AA',
            'FRUTILLA': '#D32F2F',
            'CEREZA': '#FBC02D',
            'OTRO': '#757575'
        }

        # Get all unique fruits and dates
        all_fruits = sorted(list(set(real_stacked['FRUTA'].unique()) | set(ppto_stacked['FRUTA'].unique()))) if not real_stacked.empty or not ppto_stacked.empty else []
        all_dates = sorted(list(set(real_stacked['Date'].unique()) | set(ppto_total['Date'].unique()))) if not real_stacked.empty or not ppto_total.empty else []

        # Pivot Data for easier access
        real_pivot = real_stacked.pivot(index='Date', columns='FRUTA', values='Real').fillna(0) if not real_stacked.empty else pd.DataFrame()
        if not real_pivot.empty:
            real_pivot = real_pivot.reindex(index=all_dates, columns=all_fruits, fill_value=0)

        ppto_stacked_pivot = ppto_stacked.pivot(index='Date', columns='FRUTA', values='v.2').fillna(0) if not ppto_stacked.empty else pd.DataFrame()
        if not ppto_stacked_pivot.empty:
            ppto_stacked_pivot = ppto_stacked_pivot.reindex(index=all_dates, columns=all_fruits, fill_value=0)

        ppto_total_pivot = ppto_total.set_index('Date')['PPTO Original'].reindex(all_dates, fill_value=0) if not ppto_total.empty else pd.Series([], dtype=float)

        # Initialize bases for stacking
        real_stacked_base = pd.Series(0.0, index=all_dates)
        ppto_stacked_base = pd.Series(0.0, index=all_dates)

        # Iterate through fruits to add stacked traces for both Real and v.2
        for fruit in all_fruits:
            color = fruit_colors.get(fruit, '#757575')

            # 1. Real Stacked (Group 0)
            if not real_pivot.empty and fruit in real_pivot.columns:
                y_real = real_pivot[fruit]
                if y_real.sum() > 0:
                    fig_evo.add_trace(go.Bar(
                        name=f"{fruit}",
                        x=all_dates,
                        y=y_real,
                        base=real_stacked_base.tolist(),
                        marker_color=color,
                        offsetgroup='0',
                        legendgroup=fruit,
                        showlegend=True,
                        text=[f"{val:,.0f}" if val > 0 else '' for val in y_real],
                        textposition='inside',
                        hovertemplate=f"<b>{fruit} (Real)</b><br>%{{y:,.0f}}<extra></extra>"
                    ))
                    real_stacked_base += y_real

            # 2. v.2 Stacked (Group 2)
            if not ppto_stacked_pivot.empty and fruit in ppto_stacked_pivot.columns:
                y_ppto = ppto_stacked_pivot[fruit]
                if y_ppto.sum() > 0:
                    fig_evo.add_trace(go.Bar(
                        name=f"{fruit}",
                        x=all_dates,
                        y=y_ppto,
                        base=ppto_stacked_base.tolist(),
                        marker_color=color,
                        offsetgroup='2',
                        legendgroup=fruit,
                        showlegend=False,
                        opacity=0.6,
                        text=[f"{val:,.0f}" if val > 0 else '' for val in y_ppto],
                        textposition='inside',
                        hovertemplate=f"<b>{fruit} (v.2)</b><br>%{{y:,.0f}}<extra></extra>"
                    ))
                    ppto_stacked_base += y_ppto

        # 3. PPTO Original (Group 1) - Single Bar (Middle)
        fig_evo.add_trace(go.Bar(
            name='PPTO Original',
            x=all_dates,
            y=ppto_total_pivot,
            marker_color='#4CAF50',
            offsetgroup='1',
            text=[f"{val:,.0f}" if val > 100 else '' for val in ppto_total_pivot],
            textposition='outside',
            hovertemplate="<b>PPTO Original</b><br>%{y:,.0f}<extra></extra>"
        ))

        # 4. Total Labels
        fig_evo.add_trace(go.Scatter(
            name='Total Real',
            x=all_dates,
            y=real_stacked_base,
            mode='text',
            text=[f"{val:,.0f}" if val > 0 else '' for val in real_stacked_base],
            textposition='top center',
            textfont=dict(color='#333', size=12),
            offsetgroup='0',
            showlegend=False,
            hovertemplate="<b>Total Real</b><br>%{y:,.0f}<extra></extra>"
        ))

        fig_evo.add_trace(go.Scatter(
            name='v.2',
            x=all_dates,
            y=ppto_stacked_base,
            mode='text',
            text=[f"{val:,.0f}" if val > 0 else '' for val in ppto_stacked_base],
            textposition='top center',
            textfont=dict(color='#FF6D00', size=12),
            offsetgroup='2',
            showlegend=False,
            hovertemplate="<b>Total v.2</b><br>%{y:,.0f}<extra></extra>"
        ))

        # Dynamic height
        chart_height = 600

        fig_evo.update_layout(
            xaxis_title="Día",
            yaxis_title="Kilos",
            height=chart_height,
            margin=dict(l=20, r=20, t=50, b=100),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            barmode='group',
            bargap=0.15,
            xaxis=dict(
                type='category',
                tickangle=-45,
            )
        )

        st.plotly_chart(fig_evo, use_container_width=True)
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

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
    # usa variables en .env a través de shared.odoo_client
    return get_odoo_client()

client = get_connector()

if not client:
    st.error("No se pudo obtener cliente Odoo. Verificar configuración en .env.")
    st.stop()

with st.spinner("Cargando datos..."):
    po_data = pd.DataFrame()
    budget_data = pd.DataFrame()
    pricing_data = pd.DataFrame()
    static_data = pd.DataFrame()
    central_bank_data = pd.DataFrame()
    try:
        # fetches through backend services if needed; keep lightweight on page load
        po_data = data_service.get_purchase_report_data(client) if hasattr(data_service, 'get_purchase_report_data') else pd.DataFrame()
    except Exception:
        po_data = pd.DataFrame()

    uploaded_budget = st.sidebar.file_uploader("📂 1. Presupuesto Actual (Excel)", type=["xlsx"])
    uploaded_dates = st.sidebar.file_uploader("📅 2. Archivo de Fechas (FecHAS.xlsx)", type=["xlsx"])
    uploaded_future = st.sidebar.file_uploader("📈 3. Presupuesto Futuro (Ej: PPTO's 2026.xlsx)", type=["xlsx"])

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

    try:
        pricing_data = pd.DataFrame()  # placeholder
        static_data = pd.read_excel  # placeholder to avoid immediate failures
        central_bank_data = data_service.get_central_bank_data()
    except Exception:
        central_bank_data = pd.DataFrame()

# (Se pueden adaptar los filtros y la UI completa usando la lógica original)
st.info("Página integrada: adapta la UI interna según tus necesidades. Los servicios están en `backend/services/abastecimiento_*`.")

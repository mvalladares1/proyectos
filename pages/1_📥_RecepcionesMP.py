"""
Dashboard Recepciones MP - Integrado a central de dashboards
"""
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.auth import proteger_pagina

st.set_page_config(page_title="Recepciones MP", page_icon="📥", layout="wide")

# Autenticación central
if not proteger_pagina():
    st.stop()

st.title("📥 Recepciones de Materia Prima (MP)")
st.caption("Monitorea la fruta recepcionada en planta, con KPIs de calidad asociados")

# --- Estado persistente ---
if 'df' not in st.session_state:
    st.session_state.df = None
if 'idx' not in st.session_state:
    st.session_state.idx = None

# Filtros
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Fecha inicio", datetime.now() - timedelta(days=7))
with col2:
    fecha_fin = st.date_input("Fecha fin", datetime.now())

if st.button("Consultar Recepciones"):
    params = {
        "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
        "fecha_fin": fecha_fin.strftime("%Y-%m-%d")
    }
    api_url = "http://localhost:8001/api/v1/recepciones-mp/"  # Cambia si tu API está en otro host
    resp = requests.get(api_url, params=params)
    if resp.status_code == 200:
        data = resp.json()
        df = pd.DataFrame(data)
        if not df.empty:
            st.session_state.df = df
            st.session_state.idx = None
        else:
            st.session_state.df = None
            st.session_state.idx = None
            st.warning("No se encontraron recepciones en el rango de fechas seleccionado.")
    else:
        st.error(f"Error: {resp.status_code} - {resp.text}")
        st.session_state.df = None
        st.session_state.idx = None

# Mostrar tabla y detalle si hay datos
df = st.session_state.df
if df is not None:
    # ...existing code...
    st.subheader("📊 KPIs de Calidad")
    total_costo = 0
    for _, row in df.iterrows():
        if 'productos' in row and isinstance(row['productos'], list):
            for p in row['productos']:
                total_costo += p.get('Costo Total', 0) or 0
    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    with col_a:
        total_kg = df['kg_recepcionados'].sum()
        st.metric("Total Kg Recepcionados", f"{total_kg:,.2f}")
    with col_b:
        st.metric("Costo Total", f"${total_costo:,.0f}")
    with col_c:
        prom_iqf = df['total_iqf'].mean()
        st.metric("Promedio % IQF", f"{prom_iqf:.2f}%")
    with col_d:
        prom_block = df['total_block'].mean()
        st.metric("Promedio % Block", f"{prom_block:.2f}%")
    with col_e:
        clasif = df['calific_final'].value_counts().idxmax() if not df['calific_final'].isnull().all() and not df['calific_final'].eq('').all() else "-"
        st.metric("Clasificación más frecuente", clasif)
    # ...existing code...
    # (El resto del código se mantiene igual que en el dashboard original de recepcion/pages/1_📥_RecepcionesMP.py)

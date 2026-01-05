"""
Módulo compartido para Rendimiento/Trazabilidad.
Contiene funciones API y de formateo.
"""
import streamlit as st
import requests
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


# --------------------- Funciones de formateo ---------------------

def fmt_numero(valor, decimales=0):
    """Formatea número con punto como miles y coma como decimal (formato chileno)."""
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


# --------------------- Funciones API ---------------------

def get_trazabilidad_inversa(username: str, password: str, lote_pt: str):
    """Obtiene trazabilidad inversa desde PT hacia MP."""
    try:
        params = {"username": username, "password": password}
        resp = requests.get(
            f"{API_URL}/api/v1/rendimiento/trazabilidad-inversa/{lote_pt}",
            params=params,
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"Error HTTP: {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def get_sankey_data(username: str, password: str, fecha_inicio: str, fecha_fin: str, limit: int = 30):
    """Obtiene datos para diagrama Sankey."""
    try:
        params = {
            "username": username,
            "password": password,
            "start_date": fecha_inicio,
            "end_date": fecha_fin,
            "limit": limit
        }
        resp = requests.get(
            f"{API_URL}/api/v1/containers/sankey",
            params=params,
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

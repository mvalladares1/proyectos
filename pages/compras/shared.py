"""
Módulo compartido para Compras.
Contiene funciones de utilidad, formateo y configuración.
"""
import streamlit as st
import pandas as pd
import os

# Determinar API_URL basado en ENV
ENV = os.getenv("ENV", "production")
if ENV == "development":
    API_URL = "http://127.0.0.1:8002"  # Puerto DEV
else:
    API_URL = "http://127.0.0.1:8000"  # Puerto PROD


# --------------------- Funciones de formateo ---------------------

def fmt_numero(valor, decimales=0):
    """Formatea número con punto de miles y coma decimal (chileno)."""
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
    """Formatea valor monetario con símbolo $."""
    return f"${fmt_numero(valor, 0)}"


def fmt_fecha(fecha_str):
    """Convierte YYYY-MM-DD a DD/MM/YYYY."""
    if not fecha_str:
        return ""
    try:
        if isinstance(fecha_str, str) and len(fecha_str) >= 10:
            fecha_str = fecha_str[:10]
            parts = fecha_str.split("-")
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return fecha_str
    except:
        return str(fecha_str)


# --------------------- Funciones de estado ---------------------

def get_approval_color(status):
    """Retorna emoji según estado de aprobación."""
    return {
        'Aprobada': '🟢', 
        'Parcialmente aprobada': '🟡', 
        'En revisión': '⚪', 
        'Rechazada': '🔴'
    }.get(status, '⚪')


def get_receive_color(status):
    """Retorna emoji según estado de recepción."""
    return {
        'Recepcionada totalmente': '🟢', 
        'Recepción parcial': '🟡', 
        'No recepcionada': '🔴', 
        'No se recepciona': '⚪'
    }.get(status, '⚪')


# --------------------- Funciones fetch con caché ---------------------

@st.cache_data(ttl=300, show_spinner=False)
def fetch_compras_overview(_username, _password, fecha_inicio, fecha_fin):
    """Obtiene overview de compras (KPIs)."""
    try:
        import requests
        resp = requests.get(
            f"{API_URL}/api/v1/compras/overview",
            params={
                "username": _username, 
                "password": _password,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin
            },
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()
        return {}
    except Exception as e:
        st.error(f"Error al obtener overview: {str(e)}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_compras_ordenes(_username, _password, status_filter=None, fecha_inicio=None, fecha_fin=None):
    """Obtiene órdenes de compra."""
    try:
        import requests
        params = {"username": _username, "password": _password}
        if status_filter:
            params["status_filter"] = status_filter
        if fecha_inicio:
            params["fecha_inicio"] = fecha_inicio
        if fecha_fin:
            params["fecha_fin"] = fecha_fin
        
        resp = requests.get(
            f"{API_URL}/api/v1/compras/ordenes",
            params=params,
            timeout=120
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Error al obtener órdenes: {str(e)}")
        return []


@st.cache_data(ttl=300, show_spinner=False)
def fetch_lineas_credito_resumen(_username, _password, fecha_desde: str = None):
    """Obtiene resumen de líneas de crédito."""
    try:
        import requests
        params = {"username": _username, "password": _password}
        if fecha_desde:
            params["fecha_desde"] = fecha_desde
        resp = requests.get(
            f"{API_URL}/api/v1/compras/lineas-credito/resumen",
            params=params,
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json()
        return {}
    except Exception as e:
        st.error(f"Error al obtener resumen: {str(e)}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_lineas_credito(_username, _password, fecha_desde: str = None):
    """Obtiene líneas de crédito detalladas."""
    try:
        import requests
        params = {"username": _username, "password": _password}
        if fecha_desde:
            params["fecha_desde"] = fecha_desde
        resp = requests.get(
            f"{API_URL}/api/v1/compras/lineas-credito",
            params=params,
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception as e:
        st.error(f"Error al obtener líneas: {str(e)}")
        return []


# --------------------- Inicialización de Session State ---------------------

def init_session_state():
    """Inicializa variables de session_state para el módulo Compras."""
    defaults = {
        'compras_data': None,
        'compras_ordenes': None,
        'lineas_credito': None,
        'lineas_resumen': None,
        'po_page': 1,
        'compras_loading': False,
        'lineas_loading': False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

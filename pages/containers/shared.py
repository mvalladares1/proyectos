"""
Módulo compartido para Containers.
Contiene funciones API y utilidades.
"""
import streamlit as st
import httpx
from typing import Dict, List

API_URL = st.secrets.get("API_URL", "http://localhost:8000")


# --------------------- Funciones API ---------------------

@st.cache_data(ttl=300, show_spinner=False)
def fetch_containers(_username: str, _password: str, start_date: str = None, end_date: str = None,
                     partner_id: int = None, state: str = None) -> List[Dict]:
    """Obtiene containers desde la API."""
    try:
        params = {
            "username": _username,
            "password": _password
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if partner_id:
            params["partner_id"] = partner_id
        if state:
            params["state"] = state
        
        response = httpx.get(
            f"{API_URL}/api/v1/containers/",
            params=params,
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener containers: {str(e)}")
        return []


@st.cache_data(ttl=300, show_spinner=False)
def fetch_container_detail(_username: str, _password: str, sale_id: int) -> Dict:
    """Obtiene detalle de un container."""
    try:
        response = httpx.get(
            f"{API_URL}/api/v1/containers/{sale_id}",
            params={
                "username": _username,
                "password": _password
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener detalle: {str(e)}")
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_summary(_username: str, _password: str) -> Dict:
    """Obtiene resumen de containers."""
    try:
        response = httpx.get(
            f"{API_URL}/api/v1/containers/summary",
            params={
                "username": _username,
                "password": _password
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener resumen: {str(e)}")
        return {}


# --------------------- Funciones auxiliares ---------------------

def get_state_color(avance_pct: float) -> str:
    """Retorna color según el avance."""
    if avance_pct >= 100:
        return "#00ff88"
    elif avance_pct >= 75:
        return "#00cc66"
    elif avance_pct >= 50:
        return "#ffaa00"
    elif avance_pct >= 25:
        return "#ff8800"
    else:
        return "#ff4444"


def get_sale_state_display(state: str) -> str:
    """Convierte el estado de venta a texto legible."""
    state_map = {
        "draft": "Borrador",
        "sent": "Enviado",
        "sale": "Confirmado",
        "done": "Completado",
        "cancel": "Cancelado"
    }
    return state_map.get(state, state)


# Opciones de filtro de estado
STATE_OPTIONS = {
    "Todos": None,
    "Borrador": "draft",
    "Confirmado": "sale",
    "Completado": "done"
}


def init_session_state():
    """Inicializa variables de session_state para el módulo Containers."""
    if "containers_loading" not in st.session_state:
        st.session_state.containers_loading = False

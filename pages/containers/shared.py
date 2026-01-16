"""
Módulo compartido para Pedidos de Venta.
Contiene funciones API y utilidades.
"""
import streamlit as st
import httpx
import os
from typing import Dict, List
from datetime import datetime, timedelta

API_URL = os.getenv("API_URL", "http://localhost:8000")
ODOO_BASE_URL = "https://riofuturo.server98c6e.oerpondemand.net/web"

print(f"[SHARED.PY] API_URL cargada: {API_URL}")
print(f"[SHARED.PY] os.getenv('API_URL'): {os.getenv('API_URL')}")


# --------------------- Funciones API ---------------------

# @st.cache_data(ttl=300, show_spinner=False)  # DESHABILITADO TEMPORALMENTE PARA DEBUG
def fetch_containers(_username: str, _password: str, start_date: str = None, end_date: str = None,
                     partner_id: int = None, state: str = None) -> List[Dict]:
    """Obtiene containers desde la API."""
    import time
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
        
        url = f"{API_URL}/api/v1/containers/"
        params["_t"] = int(time.time())  # Timestamp para evitar cache
        print(f"[DEBUG] API_URL global variable: {API_URL}")
        print(f"[DEBUG] URL completa: {url}")
        print(f"[DEBUG] os.getenv('API_URL'): {os.getenv('API_URL')}")
        print(f"[DEBUG] Llamando a: {url}")
        print(f"[DEBUG] Variables recibidas: start_date={start_date}, end_date={end_date}, state={state}")
        print(f"[DEBUG] Params que se enviarán en HTTP: {params}")
        print(f"[DEBUG] Username: {_username[:10]}... Password: {'*' * 10}{_password[-4:] if _password else 'EMPTY'}")
        
        response = httpx.get(
            url,
            params=params,
            timeout=60.0
        )
        
        print(f"[DEBUG] Status code: {response.status_code}")
        
        response.raise_for_status()
        data = response.json()
        
        print(f"[DEBUG] Containers recibidos: {len(data)}")
        if data:
            print(f"[DEBUG] Primer container: {data[0].get('name')}")
        else:
            print(f"[DEBUG] Response body: {response.text[:300]}")
        
        return data
    except httpx.HTTPStatusError as e:
        error_msg = f"❌ Error {e.response.status_code}: {e.response.text[:500]}"
        print(f"[DEBUG ERROR] {error_msg}")
        st.error(error_msg)
        return []
    except Exception as e:
        error_msg = f"❌ Error al obtener containers: {str(e)}"
        print(f"[DEBUG ERROR] {error_msg}")
        st.error(error_msg)
        import traceback
        traceback.print_exc()
        st.error(traceback.format_exc())
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


def get_date_urgency_color(date_str: str) -> tuple:
    """
    Retorna color y emoji según la urgencia de la fecha.
    Returns: (color_hex, emoji, days_remaining)
    """
    if not date_str:
        return "#888888", "⚪", None
    
    try:
        # Parsear fecha
        if 'T' in str(date_str):
            fecha = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        else:
            fecha = datetime.strptime(str(date_str)[:10], '%Y-%m-%d')
        
        # Si tiene timezone, convertir a naive
        if fecha.tzinfo:
            fecha = fecha.replace(tzinfo=None)
        
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        dias = (fecha - hoy).days
        
        if dias < 0:
            return "#ff4444", "🔴", dias  # Vencido
        elif dias <= 3:
            return "#ff4444", "🔴", dias  # Crítico (0-3 días)
        elif dias <= 7:
            return "#ff8800", "🟠", dias  # Urgente (4-7 días)
        elif dias <= 14:
            return "#ffaa00", "🟡", dias  # Próximo (8-14 días)
        else:
            return "#00cc66", "🟢", dias  # Holgado (>14 días)
    except:
        return "#888888", "⚪", None


def get_odoo_link(model: str, record_id: int) -> str:
    """Genera link a Odoo para un registro."""
    if model == "sale.order":
        return f"{ODOO_BASE_URL}#id={record_id}&menu_id=451&cids=1&action=676&model=sale.order&view_type=form"
    elif model == "mrp.production":
        return f"{ODOO_BASE_URL}#id={record_id}&menu_id=390&cids=1&action=604&model=mrp.production&view_type=form"
    return f"{ODOO_BASE_URL}#id={record_id}&model={model}&view_type=form"


def format_date_with_urgency(date_str: str) -> str:
    """Formatea fecha con indicador de urgencia."""
    color, emoji, dias = get_date_urgency_color(date_str)
    
    if not date_str:
        return "—"
    
    try:
        if 'T' in str(date_str):
            fecha = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        else:
            fecha = datetime.strptime(str(date_str)[:10], '%Y-%m-%d')
        
        fecha_fmt = fecha.strftime('%d/%m/%Y')
        
        if dias is not None:
            if dias < 0:
                return f"{emoji} {fecha_fmt} (vencido hace {abs(dias)}d)"
            elif dias == 0:
                return f"{emoji} {fecha_fmt} (HOY)"
            else:
                return f"{emoji} {fecha_fmt} ({dias}d)"
        return fecha_fmt
    except:
        return str(date_str)[:10] if date_str else "—"

"""
Módulo compartido para Recepciones.
Contiene funciones de utilidad, formateo y llamadas a API.
"""
import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime

# Determinar API_URL basado en ENV
ENV = os.getenv("ENV", "production")
if ENV == "development":
    # Usar nombre del contenedor en Docker, localhost fuera de Docker
    API_URL = os.getenv("API_URL", "http://rio-api-dev:8000")
else:
    API_URL = os.getenv("API_URL", "http://rio-api-prod:8000")


# --------------------- Funciones de formateo ---------------------

def fmt_fecha(fecha_str):
    """Convierte fecha ISO a formato DD/MM/AAAA"""
    if not fecha_str:
        return ""
    try:
        if isinstance(fecha_str, str):
            # Manejar formato con hora
            if " " in fecha_str:
                fecha_str = fecha_str.split(" ")[0]
            elif "T" in fecha_str:
                fecha_str = fecha_str.split("T")[0]
            dt = datetime.strptime(fecha_str, "%Y-%m-%d")
        else:
            dt = fecha_str
        return dt.strftime("%d/%m/%Y")
    except:
        return str(fecha_str)


def fmt_numero(valor, decimales=0):
    """Formatea número con punto como miles y coma como decimal (formato chileno)."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "0"
    try:
        if decimales > 0:
            formatted = f"{valor:,.{decimales}f}"
        else:
            formatted = f"{valor:,.0f}"
        # Intercambiar: coma -> temporal, punto -> coma, temporal -> punto
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except:
        return str(valor)


def fmt_dinero(valor, decimales=0):
    """Formatea valor monetario con símbolo $"""
    return f"${fmt_numero(valor, decimales)}"


# --------------------- Funciones de estado ---------------------

def get_validation_icon(status):
    """Retorna icono según estado de validación."""
    return {
        'Validada': '✅',
        'Lista para validar': '🟡',
        'Confirmada': '🔵',
        'En espera': '⏳',
        'Borrador': '⚪',
        'Cancelada': '❌'
    }.get(status, '⚪')


def get_qc_icon(status):
    """Retorna icono según estado de QC."""
    return {
        'Con QC Aprobado': '✅',
        'Con QC Pendiente': '🟡',
        'QC Fallido': '🔴',
        'Sin QC': '⚪'
    }.get(status, '⚪')


# --------------------- Llamadas API con caché ---------------------

@st.cache_data(ttl=120, show_spinner=False)
def fetch_gestion_data(_username, _password, fecha_inicio, fecha_fin, status_filter=None, qc_filter=None, search_text=None, origen=None):
    """
    Obtiene datos de gestión con caché de 2 minutos.
    
    Parámetros:
        origen: Lista de orígenes a filtrar (RFP, VILKUN, SAN JOSE)
    """
    params = {
        "username": _username, "password": _password,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin
    }
    if status_filter and status_filter != "Todos":
        params["status_filter"] = status_filter
    if qc_filter and qc_filter != "Todos":
        params["qc_filter"] = qc_filter
    if search_text:
        params["search_text"] = search_text
    
    # Construir URL con múltiples orígenes
    url = f"{API_URL}/api/v1/recepciones-mp/gestion"
    if origen and len(origen) > 0:
        from urllib.parse import urlencode
        query_string = urlencode(params)
        for orig in origen:
            query_string += f"&origen={orig}"
        url = f"{url}?{query_string}"
        params = None  # Ya están en la URL
    
    try:
        if params:
            resp = requests.get(url, params=params, timeout=120)
        else:
            resp = requests.get(url, timeout=120)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error fetching gestion data: {e}")
    return None



@st.cache_data(ttl=120, show_spinner=False)
def fetch_gestion_overview(_username, _password, fecha_inicio, fecha_fin):
    """Obtiene overview con caché de 2 minutos."""
    try:
        resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/gestion/overview", params={
            "username": _username, "password": _password,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        }, timeout=60)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


@st.cache_data(ttl=120, show_spinner=False)
def fetch_pallets_data(_username, _password, fecha_inicio, fecha_fin, manejo=None, tipo_fruta=None, origen=None, variedad=None):
    """Obtiene datos de pallets por recepción."""
    params = {
        "username": _username, "password": _password,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin
    }
    if manejo:
        params["manejo"] = manejo
    if tipo_fruta:
        params["tipo_fruta"] = tipo_fruta
    if variedad:
        params["variedad"] = variedad
    if origen:
        params["origen"] = origen
    
    try:
        resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/pallets", params=params, timeout=120)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error fetching pallets data: {e}")
    return None


def fetch_pallets_excel(username, password, fecha_inicio, fecha_fin, manejo=None, tipo_fruta=None, origen=None, variedad=None):
    """Obtiene el archivo Excel de detalle de pallets."""
    params = {
        "username": username, "password": password,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin
    }
    if manejo:
        params["manejo"] = manejo
    if tipo_fruta:
        params["tipo_fruta"] = tipo_fruta
    if variedad:
        params["variedad"] = variedad
    if origen:
        params["origen"] = origen
    
    try:
        resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/pallets/report.xlsx", params=params, timeout=120)
        if resp.status_code == 200:
            return resp.content
    except Exception as e:
        print(f"Error fetching pallets excel: {e}")
    return None


# --------------------- Gestión de Caché ---------------------

def clear_backend_cache():
    """Limpia el caché del backend."""
    try:
        resp = requests.post(f"{API_URL}/api/v1/recepciones-mp/clear-cache", timeout=10)
        if resp.status_code == 200:
            return True, "✅ Caché del backend limpiado"
        else:
            return False, f"❌ Error {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, f"❌ Error al limpiar caché: {str(e)}"


def clear_all_caches():
    """Limpia todos los cachés (frontend + backend)."""
    # Limpiar cachés de Streamlit
    st.cache_data.clear()
    
    # Limpiar caché del backend
    success, msg = clear_backend_cache()
    
    return success, msg


# --------------------- Inicialización de Session State ---------------------

def init_session_state():
    """Inicializa variables de session_state para el módulo Recepciones."""
    defaults = {
        'df_recepcion': None,
        'idx_recepcion': None,
        'gestion_data': None,
        'gestion_overview': None,
        'gestion_loaded': False,
        'curva_proyecciones_raw': None,
        'curva_recepciones_raw': None,
        'curva_plantas_usadas': [],
        'aprob_data': [],
        'aprob_ppto': {},
        'aprob_ppto_detalle': {},
        'origen_filtro_usado': [],
        'recep_gestion_loading': False,
        'recep_curva_loading': False,
        'recep_aprob_cargar_loading': False,
        'recep_aprob_aprobar_loading': False,
        'recep_aprob_ productores_loading': False,
        'pallets_data': None,
        'pallets_loaded': False,
        'pallets_loading': False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# --------------------- Normalización de especies ---------------------

def normalizar_especie_manejo(tipo_fruta: str, manejo: str = "") -> str:
    """
    Normaliza tipo_fruta + manejo a formato 'Especie Manejo'.
    Ejemplo: 'ARANDANO ORGANICO' -> 'Arándano Orgánico'
    """
    tf = str(tipo_fruta or '').upper().strip()
    man = str(manejo or '').upper().strip()
    
    # Detectar manejo
    if 'ORGAN' in tf or 'ORGAN' in man:
        manejo_norm = 'Orgánico'
    else:
        manejo_norm = 'Convencional'
    
    # Detectar especie
    if 'ARANDANO' in tf or 'ARÁNDANO' in tf or 'BLUEBERRY' in tf:
        especie = 'Arándano'
    elif 'FRAM' in tf or 'MEEKER' in tf or 'HERITAGE' in tf or 'WAKEFIELD' in tf or 'RASPBERRY' in tf:
        especie = 'Frambuesa'
    elif 'FRUTILLA' in tf or 'FRESA' in tf or 'STRAWBERRY' in tf:
        especie = 'Frutilla'
    elif 'MORA' in tf or 'BLACKBERRY' in tf:
        especie = 'Mora'
    elif 'CEREZA' in tf or 'CHERRY' in tf:
        especie = 'Cereza'
    else:
        especie = 'Otro'
    
    return f"{especie} {manejo_norm}"


# --------------------- Carga de exclusiones ---------------------

@st.cache_data(ttl=60, show_spinner=False)
def get_exclusiones():
    """Carga lista de IDs/albaranes de recepciones excluidas de valorización desde la API (DB)."""
    try:
        # Usar API de permisos que lee de la base de datos
        resp = requests.get(f"{API_URL}/api/v1/permissions/exclusiones", timeout=5.0)
        if resp.status_code == 200:
            return resp.json().get("exclusiones", [])
    except Exception:
        pass
    # Fallback: intentar leer JSON local si la API falla
    try:
        import json as _json
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        path = os.path.join(project_root, "shared", "exclusiones.json")
        if os.path.exists(path):
            with open(path, 'r') as f:
                return _json.load(f).get("recepciones", [])
    except Exception:
        pass
    return []


@st.cache_data(ttl=60, show_spinner=False)
def get_precio_override():
    """Carga mapa albaran -> precio_unitario desde la API (DB)."""
    try:
        resp = requests.get(f"{API_URL}/api/v1/permissions/precio-override", timeout=5.0)
        if resp.status_code == 200:
            return resp.json().get("precio_override", {})
    except Exception:
        pass
    return {}


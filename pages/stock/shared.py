"""
Módulo compartido para Stock.
Contiene funciones de utilidad, formateo, llamadas a API y configuración de cámaras.
"""
import streamlit as st
import httpx
from datetime import datetime
from typing import Dict, List
import os

API_URL = os.getenv("API_URL", st.secrets.get("API_URL", "http://localhost:8000"))


# --------------------- Funciones de formateo ---------------------

def fmt_fecha(fecha):
    """Formatea fecha a DD/MM/AAAA"""
    if not fecha:
        return ""
    if isinstance(fecha, str):
        try:
            fecha = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
        except:
            return fecha
    return fecha.strftime("%d/%m/%Y")


def fmt_numero(valor, decimales=0):
    """Formatea número con punto de miles y coma decimal (chileno)"""
    try:
        v = float(valor)
        if decimales == 0 and v == int(v):
            return f"{int(v):,}".replace(",", ".")
        return f"{v:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)


# --------------------- Configuración de cámaras ---------------------

CAMARAS_CONFIG = {
    "RF/Stock/Camara 0°C REAL": {"capacidad": 200, "patron": ["Camara 0°C REAL"], "id": 5452},
    "VLK/Camara 0°": {"capacidad": 200, "patron": ["VLK/Camara 0", "VLK", "Camara 0°"], "id": 8528},
    "RF/Stock/Inventario Real": {"capacidad": 500, "patron": ["Inventario Real"], "id": 8474},
    "VLK/Stock": {"capacidad": 500, "patron": ["VLK/Stock"], "id": 8497},
}


def get_capacidades_default():
    """Retorna capacidades por defecto."""
    return {
        "RF/Stock/Camara 0°C REAL": 200,
        "VLK/Camara 0°": 200,
        "RF/Stock/Inventario Real": 500,
        "VLK/Stock": 500
    }


def filtrar_camaras_principales(camaras_data):
    """Filtra solo las ubicaciones específicas configuradas."""
    camaras_filtradas = []
    usados = set()
    
    # Obtener capacidades del session_state o usar por defecto
    capacidades = st.session_state.get("capacidades_config", get_capacidades_default())
    
    for camara in camaras_data:
        camara_id = camara.get("id")
        nombre = camara.get("name", "")
        full_name = camara.get("full_name", "")
        
        for config_name, config in CAMARAS_CONFIG.items():
            if config_name in usados:
                continue
            
            # Primero intentar match por ID (más preciso)
            if config.get("id") and camara_id == config["id"]:
                camara_copy = camara.copy()
                camara_copy["capacity_pallets"] = capacidades.get(config_name, config["capacidad"])
                camara_copy["config_name"] = config_name
                camaras_filtradas.append(camara_copy)
                usados.add(config_name)
                break
            
            # Si no hay match por ID, usar patrones
            patrones = config.get("patron", [])
            coincide = any(
                p.lower() in nombre.lower() or p.lower() in full_name.lower() 
                for p in patrones
            )
            
            if coincide:
                camara_copy = camara.copy()
                camara_copy["capacity_pallets"] = capacidades.get(config_name, config["capacidad"])
                camara_copy["config_name"] = config_name
                camaras_filtradas.append(camara_copy)
                usados.add(config_name)
                break
    
    return camaras_filtradas


# --------------------- Llamadas API ---------------------

@st.cache_data(ttl=300, show_spinner=False)
def fetch_camaras(_username: str, _password: str, fecha_desde=None, fecha_hasta=None) -> List[Dict]:
    """Obtiene datos de cámaras desde la API, opcionalmente filtrado por fecha de ingreso."""
    try:
        params = {
            "username": _username,
            "password": _password
        }
        if fecha_desde:
            params["fecha_desde"] = fecha_desde.strftime("%Y-%m-%d")
        if fecha_hasta:
            params["fecha_hasta"] = fecha_hasta.strftime("%Y-%m-%d")
            
        response = httpx.get(
            f"{API_URL}/api/v1/stock/camaras",
            params=params,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener datos de cámaras: {str(e)}")
        return []


@st.cache_data(ttl=300, show_spinner=False)
def fetch_pallets(_username: str, _password: str, location_id: int, category: str = None) -> List[Dict]:
    """Obtiene pallets de una ubicación."""
    try:
        params = {
            "username": _username,
            "password": _password,
            "location_id": location_id
        }
        if category:
            params["category"] = category
            
        response = httpx.get(
            f"{API_URL}/api/v1/stock/pallets",
            params=params,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener pallets: {str(e)}")
        return []


@st.cache_data(ttl=300, show_spinner=False)
def fetch_lotes(_username: str, _password: str, category: str, location_ids: List[int] = None) -> List[Dict]:
    """Obtiene lotes por categoría."""
    try:
        params = {
            "username": _username,
            "password": _password,
            "category": category
        }
        if location_ids:
            params["location_ids"] = ",".join(map(str, location_ids))
            
        response = httpx.get(
            f"{API_URL}/api/v1/stock/lotes",
            params=params,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener lotes: {str(e)}")
        return []


# --------------------- Inicialización de Session State ---------------------

def init_session_state():
    """Inicializa variables de session_state para el módulo Stock."""
    defaults = {
        'mostrar_todas_camaras': False,
        'capacidades_config': get_capacidades_default(),
        'stock_pallets_loading': False,
        'stock_lotes_loading': False,
        'stock_data_loaded': False,
        'stock_loading': False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

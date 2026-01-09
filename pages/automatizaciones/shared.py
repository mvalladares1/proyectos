"""
Módulo compartido para Automatizaciones.
Contiene CSS, constantes y funciones reutilizables.
"""
import streamlit as st
import requests
import os
from datetime import datetime
import urllib3

# Deshabilitar warnings de SSL para certificados autofirmados
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Forzar lectura de API_URL desde environment
API_URL = os.environ.get("API_URL") or os.getenv("API_URL", "http://127.0.0.1:8000")
st.write(f"🔍 API_URL configurada: {API_URL}")  # Debug temporal

# --------------------- CSS Global ---------------------

CSS_GLOBAL = """
<style>
    /* Botones grandes para mobile */
    .stButton > button {
        width: 100%;
        min-height: 48px;
        font-size: 16px;
        font-weight: 600;
        border-radius: 8px;
    }
    
    /* Input más grande */
    .stTextInput > div > div > input {
        font-size: 16px;
        min-height: 48px;
    }
    
    /* Radio buttons más grandes */
    .stRadio > div {
        gap: 12px;
    }
    
    .stRadio > div > label {
        min-height: 48px;
        font-size: 16px;
        padding: 8px 12px;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        cursor: pointer;
    }
    
    /* Cards de pallets (dark mode compatible) */
    .pallet-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border-left: 4px solid #22c55e;
        padding: 16px;
        margin: 8px 0;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    
    .pallet-card strong {
        color: #ffffff;
        font-size: 1.05em;
    }
    
    .pallet-card small {
        color: #94a3b8;
    }
    
    /* Cards de órdenes (dark mode compatible) */
    .orden-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border: 1px solid #475569;
        padding: 16px;
        margin: 12px 0;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    
    .orden-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    
    /* Estados */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .badge-draft { background: #78350f; color: #fde68a; }
    .badge-progress { background: #1e3a8a; color: #93c5fd; }
    .badge-done { background: #14532d; color: #86efac; }
    .badge-cancel { background: #7f1d1d; color: #fca5a5; }
</style>
"""


# --------------------- Funciones API ---------------------

@st.cache_data(ttl=3600)
def get_tuneles(_username, _password):
    """Obtiene la lista de túneles disponibles."""
    try:
        response = requests.get(
            f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/procesos",
            params={"username": _username, "password": _password},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []


def validar_pallets(username, password, codigos, buscar_ubicacion_auto=False):
    """Valida una lista de códigos de pallet."""
    try:
        response = requests.post(
            f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/validar-pallets",
            params={"username": username, "password": password},
            json={
                "pallets": codigos,
                "buscar_ubicacion": buscar_ubicacion_auto
            },
            timeout=15
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error validando pallets: {e}")
        return None


def crear_orden(username, password, tunel, pallets_payload, buscar_ubicacion_auto=False):
    """Crea una orden de fabricación en túneles estáticos."""
    try:
        response = requests.post(
            f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/crear",
            params={"username": username, "password": password},
            json={
                "tunel": tunel,
                "pallets": pallets_payload,
                "buscar_ubicacion_auto": buscar_ubicacion_auto
            },
            timeout=60
        )
        return response
    except Exception as e:
        st.error(f"Error creando orden: {e}")
        return None


def get_ordenes(username, password, tunel=None, estado=None, limit=50):
    """Obtiene órdenes de túneles estáticos."""
    try:
        params = {
            "username": username,
            "password": password,
            "limit": limit
        }
        if tunel and tunel != 'Todos':
            params['tunel'] = tunel
        
        if estado == 'stock_pendiente':
            params['solo_pendientes'] = True
        elif estado and estado != 'Todos':
            params['estado'] = estado
        
        response = requests.get(
            f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/ordenes",
            params=params
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error obteniendo órdenes: {e}")
        return []


def get_pendientes_orden(username, password, orden_id):
    """Obtiene los pendientes de una orden específica."""
    try:
        url = f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/ordenes/{orden_id}/pendientes"
        resp = requests.get(
            url,
            params={"username": username, "password": password},
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
            timeout=10,
            verify=False  # Ignorar verificación SSL para certificados autofirmados
        )
        if resp.status_code == 200:
            data = resp.json()
            # Debug: mostrar resumen
            if data.get('success'):
                resumen = data.get('resumen', {})
                st.info(f"📊 Datos del servidor - Agregados: {resumen.get('agregados')}, Disponibles: {resumen.get('disponibles')}, Pendientes: {resumen.get('pendientes')}")
            return data
        else:
            st.error(f"Error HTTP {resp.status_code}: {resp.text[:200]}")
            return {'success': False, 'error': f"HTTP {resp.status_code}"}
    except requests.exceptions.SSLError as e:
        st.error(f"❌ Error SSL: {str(e)[:200]}")
        return {'success': False, 'error': f"SSL Error: {str(e)}"}
    except requests.exceptions.ConnectionError as e:
        st.error(f"❌ Error de conexión a {API_URL}: {str(e)[:200]}")
        return {'success': False, 'error': f"Connection error: {str(e)}"}
    except requests.exceptions.Timeout:
        st.error(f"❌ Timeout conectando a {API_URL}")
        return {'success': False, 'error': "Timeout"}
    except Exception as e:
        st.error(f"❌ Error inesperado: {type(e).__name__} - {str(e)[:200]}")
        return {'success': False, 'error': str(e)}


def agregar_disponibles(username, password, orden_id):
    """Agrega pallets disponibles a una orden."""
    try:
        resp = requests.post(
            f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/ordenes/{orden_id}/agregar-disponibles",
            params={"username": username, "password": password},
            verify=False
        )
        return resp
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def completar_pendientes(username, password, orden_id):
    """Completa los pendientes de una orden."""
    try:
        resp = requests.post(
            f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/ordenes/{orden_id}/completar-pendientes",
            params={"username": username, "password": password},
            verify=False
        )
        return resp
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def reset_estado_pendientes(username, password, orden_id):
    """SOLO DEBUG: Resetea el estado de pendientes para forzar re-validación."""
    try:
        url = f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/ordenes/{orden_id}/reset-pendientes"
        st.write(f"🔍 DEBUG: Llamando a {url}")
        st.write(f"🔍 DEBUG: Usuario: {username[:20]}...")
        
        resp = requests.post(
            url,
            params={"username": username, "password": password},
            verify=False,
            timeout=10
        )
        
        st.write(f"🔍 DEBUG: Status code: {resp.status_code}")
        st.write(f"🔍 DEBUG: Response: {resp.text[:200]}")
        
        return resp
    except requests.exceptions.SSLError as e:
        st.error(f"❌ Error SSL en reset: {str(e)[:200]}")
        return None
    except requests.exceptions.ConnectionError as e:
        st.error(f"❌ Error de conexión en reset: {str(e)[:200]}")
        return None
    except requests.exceptions.Timeout:
        st.error(f"❌ Timeout en reset")
        return None
    except Exception as e:
        st.error(f"❌ Error inesperado en reset: {type(e).__name__} - {str(e)[:200]}")
        return None


# --------------------- Funciones de formato ---------------------

def format_fecha(fecha_str):
    """Formatea fecha a DD/MM/YYYY HH:MM."""
    if not fecha_str or fecha_str == 'N/A':
        return 'N/A'
    try:
        fecha_dt = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
        return fecha_dt.strftime('%d/%m/%Y %H:%M')
    except:
        return fecha_str[:16] if len(fecha_str) > 16 else fecha_str


def get_estado_visual(estado, tiene_pendientes=False):
    """Retorna configuración visual según estado."""
    if tiene_pendientes:
        return {
            'borde': '#f59e0b',
            'badge_bg': '#78350f',
            'badge_text': '#fcd34d',
            'label': '🟠 PENDIENTE STOCK'
        }
    
    estados = {
        'draft': {'borde': '#fbbf24', 'badge_bg': '#78350f', 'badge_text': '#fde68a', 'label': '📝 BORRADOR'},
        'confirmed': {'borde': '#3b82f6', 'badge_bg': '#1e3a8a', 'badge_text': '#93c5fd', 'label': '✅ CONFIRMADO'},
        'progress': {'borde': '#f97316', 'badge_bg': '#7c2d12', 'badge_text': '#fed7aa', 'label': '🔄 EN PROCESO'},
        'done': {'borde': '#22c55e', 'badge_bg': '#14532d', 'badge_text': '#86efac', 'label': '✔️ TERMINADO'},
        'cancel': {'borde': '#ef4444', 'badge_bg': '#7f1d1d', 'badge_text': '#fca5a5', 'label': '❌ CANCELADO'}
    }
    return estados.get(estado, estados['draft'])


# --------------------- Inicialización de Session State ---------------------

def init_session_state():
    """Inicializa variables de session_state para el módulo."""
    defaults = {
        'pallets_list': [],
        'creando_orden': False,
        'last_order_result': None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

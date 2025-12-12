"""
Módulo de autenticación compartido para todos los dashboards.
Maneja sesiones con tokens, cookies y expiración automática.
"""
import streamlit as st
import httpx
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# Clave para el token en session_state y cookies
TOKEN_KEY = "session_token"


def _get_token_from_query_params() -> Optional[str]:
    """Obtiene el token de los query params (recuperado de localStorage)."""
    try:
        params = st.query_params
        return params.get("session")
    except:
        return None


def _get_stored_token() -> Optional[str]:
    """
    Obtiene el token almacenado.
    Primero intenta session_state, luego query params (para recuperación de localStorage).
    """
    # 1. Intentar session_state
    token = st.session_state.get(TOKEN_KEY)
    if token:
        return token
    
    # 2. Intentar query params (recuperación de cookie/localStorage)
    token = _get_token_from_query_params()
    if token:
        # Almacenar en session_state para futuras consultas
        st.session_state[TOKEN_KEY] = token
        return token
    
    return None


def _store_token(token: str):
    """Almacena el token en session_state."""
    st.session_state[TOKEN_KEY] = token


def _clear_token():
    """Limpia el token del storage."""
    if TOKEN_KEY in st.session_state:
        del st.session_state[TOKEN_KEY]



def validar_token_backend(token: str) -> Optional[Dict[str, Any]]:
    """Valida el token contra el backend y retorna datos de sesión."""
    try:
        response = httpx.post(
            f"{API_URL}/api/v1/auth/validate",
            json={"token": token},
            timeout=10.0
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("valid"):
                return data
    except:
        pass
    return None


def refrescar_actividad(token: str) -> bool:
    """Refresca la actividad de la sesión para evitar timeout."""
    try:
        response = httpx.post(
            f"{API_URL}/api/v1/auth/refresh",
            json={"token": token},
            timeout=5.0
        )
        return response.status_code == 200
    except:
        return False


def obtener_credenciales_backend(token: str) -> Optional[tuple]:
    """Obtiene las credenciales de Odoo desde el backend."""
    try:
        response = httpx.get(
            f"{API_URL}/api/v1/auth/credentials",
            params={"token": token},
            timeout=10.0
        )
        if response.status_code == 200:
            data = response.json()
            return (data["username"], data["password"])
    except:
        pass
    return None


def verificar_autenticacion() -> bool:
    """
    Verifica si el usuario está autenticado.
    Valida el token contra el backend si existe.
    """
    token = _get_stored_token()
    if not token:
        return False
    
    # Si ya validamos recientemente, no revalidar
    last_check = st.session_state.get("_last_token_check", 0)
    now = datetime.now().timestamp()
    
    # Revalidar cada 60 segundos
    if now - last_check < 60:
        return st.session_state.get('authenticated', False)
    
    # Validar contra backend
    session_data = validar_token_backend(token)
    if session_data:
        st.session_state['authenticated'] = True
        st.session_state['username'] = session_data.get('username')
        st.session_state['uid'] = session_data.get('uid')
        st.session_state['session_info'] = session_data
        st.session_state['_last_token_check'] = now
        
        # Refrescar actividad
        refrescar_actividad(token)
        return True
    else:
        # Token inválido o expirado
        cerrar_sesion()
        return False


def get_credenciales() -> tuple[Optional[str], Optional[str]]:
    """
    Obtiene las credenciales del usuario autenticado desde el backend.
    Retorna (username, password) o (None, None) si no hay sesión.
    """
    token = _get_stored_token()
    if not token:
        return None, None
    
    creds = obtener_credenciales_backend(token)
    if creds:
        return creds
    return None, None


def get_user_data() -> Optional[Dict[str, Any]]:
    """
    Obtiene los datos del usuario autenticado.
    """
    if verificar_autenticacion():
        return st.session_state.get('session_info')
    return None


def iniciar_sesion(token: str, username: str, uid: int):
    """Inicia sesión con un token válido."""
    _store_token(token)
    st.session_state['authenticated'] = True
    st.session_state['username'] = username
    st.session_state['uid'] = uid
    st.session_state['_last_token_check'] = datetime.now().timestamp()


def cerrar_sesion():
    """
    Cierra la sesión del usuario, limpiando el estado.
    También invalida el token en el backend.
    """
    token = _get_stored_token()
    
    # Invalidar en backend
    if token:
        try:
            httpx.post(
                f"{API_URL}/api/v1/auth/logout",
                json={"token": token},
                timeout=5.0
            )
        except:
            pass
    
    # Limpiar session_state
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def mostrar_login_requerido():
    """
    Muestra un mensaje indicando que se requiere login y detiene la ejecución.
    """
    st.warning("⚠️ Debes iniciar sesión para acceder a este dashboard.")
    st.info("👈 Ve a la página principal (Home) para iniciar sesión.")
    st.stop()


def proteger_pagina():
    """
    Decorador/función para proteger una página.
    Si no hay autenticación, muestra mensaje y detiene.
    """
    if not verificar_autenticacion():
        mostrar_login_requerido()
        return False
    return True


def guardar_permisos_state(restricted: Dict[str, List[str]], allowed: List[str], is_admin: bool):
    """Guarda los permisos en la sesión de Streamlit."""
    st.session_state['restricted_dashboards'] = restricted
    st.session_state['allowed_dashboards'] = allowed
    st.session_state['is_admin'] = is_admin


def obtener_dashboards_restringidos() -> Dict[str, List[str]]:
    return st.session_state.get('restricted_dashboards', {})


def obtener_dashboards_permitidos() -> List[str]:
    return st.session_state.get('allowed_dashboards', [])


def es_admin() -> bool:
    return st.session_state.get('is_admin', False)


def tiene_acceso_dashboard(clave: str) -> bool:
    restricted = obtener_dashboards_restringidos()
    if clave not in restricted:
        return True
    return clave in obtener_dashboards_permitidos()


def obtener_info_sesion() -> Optional[Dict[str, Any]]:
    """Obtiene información de la sesión incluyendo tiempo restante."""
    token = _get_stored_token()
    if not token:
        return None
    
    try:
        response = httpx.get(
            f"{API_URL}/api/v1/auth/session-info",
            params={"token": token},
            timeout=5.0
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

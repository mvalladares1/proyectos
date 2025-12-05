"""
Módulo de autenticación compartido para todos los dashboards.
Maneja el estado de sesión de Streamlit de forma centralizada.
"""
import streamlit as st
from typing import Optional, Dict, Any, List


def verificar_autenticacion() -> bool:
    """
    Verifica si el usuario está autenticado.
    Retorna True si hay sesión activa, False en caso contrario.
    """
    return st.session_state.get('authenticated', False)


def get_credenciales() -> tuple[Optional[str], Optional[str]]:
    """
    Obtiene las credenciales del usuario autenticado.
    Retorna (username, password) o (None, None) si no hay sesión.
    """
    if verificar_autenticacion():
        return (
            st.session_state.get('username'),
            st.session_state.get('password')
        )
    return None, None


def get_user_data() -> Optional[Dict[str, Any]]:
    """
    Obtiene los datos del usuario autenticado.
    """
    if verificar_autenticacion():
        return st.session_state.get('user_data')
    return None


def cerrar_sesion():
    """
    Cierra la sesión del usuario, limpiando el estado.
    """
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

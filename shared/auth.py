"""
Módulo de autenticación compartido para todos los dashboards.
Maneja el estado de sesión de Streamlit de forma centralizada.
"""
import streamlit as st
from typing import Optional, Dict, Any


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

"""
Módulo de manejo de cookies y persistencia de sesión para Streamlit.
Enfoque simplificado: Query Params + Cookies (sin JavaScript/iframes).
"""
import streamlit as st
from typing import Optional

# Importar CookieManager de extra-streamlit-components
try:
    import extra_streamlit_components as stx
    COOKIES_AVAILABLE = True
except ImportError:
    COOKIES_AVAILABLE = False
    stx = None

COOKIE_NAME = "rf_session"


# ============ COOKIE MANAGER ============

def get_cookie_manager():
    """Obtiene o crea el CookieManager singleton."""
    if not COOKIES_AVAILABLE:
        return None
    
    # Usar un key único para evitar recreación
    return stx.CookieManager(key="rf_cookies")


# ============ QUERY PARAMS ============

def get_token_from_query_params() -> Optional[str]:
    """Obtiene el token de los query params."""
    try:
        return st.query_params.get("session")
    except:
        return None


def save_token_to_query_params(token: str):
    """Guarda el token en query params."""
    try:
        st.query_params["session"] = token
    except:
        pass


def clear_token_from_query_params():
    """Limpia el token de query params."""
    try:
        if "session" in st.query_params:
            del st.query_params["session"]
    except:
        pass


# ============ COOKIES ============

def get_token_from_browser_cookies() -> Optional[str]:
    """Obtiene el token de las cookies del navegador."""
    if COOKIES_AVAILABLE:
        try:
            manager = get_cookie_manager()
            if manager:
                all_cookies = manager.get_all()
                if all_cookies and COOKIE_NAME in all_cookies:
                    return all_cookies[COOKIE_NAME]
        except:
            pass
    return None


def save_token_to_browser_cookies(token: str):
    """Guarda el token en cookies del navegador."""
    if COOKIES_AVAILABLE:
        try:
            manager = get_cookie_manager()
            if manager:
                manager.set(COOKIE_NAME, token, max_age=int(8 * 60 * 60))  # 8 horas
        except:
            pass


def clear_token_from_browser_cookies():
    """Limpia el token de cookies del navegador."""
    if COOKIES_AVAILABLE:
        try:
            manager = get_cookie_manager()
            if manager:
                manager.delete(COOKIE_NAME)
        except:
            pass


# ============ FUNCIONES PRINCIPALES ============

def get_token_from_cookies() -> Optional[str]:
    """
    Obtiene el token intentando múltiples fuentes en orden de prioridad:
    1. Query Params (más confiable en Streamlit)
    2. Cookies del navegador (fallback)
    """
    # 1. Query Params
    token = get_token_from_query_params()
    if token:
        return token
    
    # 2. Cookies del navegador
    token = get_token_from_browser_cookies()
    if token:
        # Si lo recuperamos de cookies, guardarlo en query params
        save_token_to_query_params(token)
        return token
    
    return None


def save_session_multi_method(token: str):
    """
    Guarda sesión en Query Params y Cookies.
    """
    # 1. Query Params
    save_token_to_query_params(token)
    
    # 2. Cookies
    save_token_to_browser_cookies(token)


def clear_session_multi_method():
    """
    Limpia sesión de todos los métodos de almacenamiento.
    """
    # Query params
    clear_token_from_query_params()
    
    # Cookies
    clear_token_from_browser_cookies()


# ============ NO-OP para LocalStorage (removido) ============

def inject_localstorage_recovery():
    """No-op - LocalStorage removido por conflictos con iframes."""
    pass


def save_token_to_localstorage(token: str):
    """No-op - LocalStorage removido."""
    pass


def clear_token_from_localstorage():
    """No-op - LocalStorage removido."""
    pass


# ============ ALIAS DE COMPATIBILIDAD ============

def save_token_to_cookies(token: str):
    """Alias para guardar token (compatibilidad)."""
    save_session_multi_method(token)


def clear_token_from_cookies():
    """Alias para limpiar (compatibilidad)."""
    clear_session_multi_method()


def get_token_from_url() -> Optional[str]:
    """Alias para compatibilidad."""
    return get_token_from_cookies()


def save_token_to_url(token: str):
    """Alias para compatibilidad."""
    save_session_multi_method(token)


def clear_token_from_url():
    """Alias para compatibilidad."""
    clear_session_multi_method()


def inject_session_recovery_script(cookie_name: str = "session_token"):
    """No-op - mantener compatibilidad."""
    pass


def save_session_to_storage(token: str, cookie_name: str = "session_token"):
    """Guarda el token en todos los métodos."""
    save_session_multi_method(token)


def clear_session_from_storage(cookie_name: str = "session_token"):
    """Limpia el token de todos los métodos."""
    clear_session_multi_method()

"""
Módulo de manejo de cookies para Streamlit.
Usa extra-streamlit-components para cookies reales del navegador.
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
COOKIE_EXPIRY_DAYS = 0.33  # 8 horas = 0.33 días


def get_cookie_manager():
    """Obtiene o crea el CookieManager singleton."""
    if not COOKIES_AVAILABLE:
        return None
    
    # Usar un key único para evitar recreación
    if 'cookie_manager' not in st.session_state:
        st.session_state['cookie_manager'] = stx.CookieManager(key="rf_cookies")
    return st.session_state['cookie_manager']


def get_token_from_cookies() -> Optional[str]:
    """Obtiene el token de la cookie del navegador."""
    if not COOKIES_AVAILABLE:
        # Fallback a query params si no hay librería
        try:
            return st.query_params.get("session")
        except:
            return None
    
    manager = get_cookie_manager()
    if manager:
        try:
            return manager.get(COOKIE_NAME)
        except:
            pass
    return None


def save_token_to_cookies(token: str):
    """Guarda el token en una cookie del navegador."""
    if not COOKIES_AVAILABLE:
        # Fallback a query params
        try:
            st.query_params["session"] = token
        except:
            pass
        return
    
    manager = get_cookie_manager()
    if manager:
        try:
            manager.set(COOKIE_NAME, token, expires_at=None, max_age=int(8 * 60 * 60))  # 8 horas
        except:
            pass


def clear_token_from_cookies():
    """Elimina el token de las cookies."""
    if not COOKIES_AVAILABLE:
        # Fallback a query params
        try:
            if "session" in st.query_params:
                del st.query_params["session"]
        except:
            pass
        return
    
    manager = get_cookie_manager()
    if manager:
        try:
            manager.delete(COOKIE_NAME)
        except:
            pass


# Funciones de compatibilidad con el código existente
def get_token_from_url() -> Optional[str]:
    """Alias para compatibilidad."""
    return get_token_from_cookies()


def save_token_to_url(token: str):
    """Alias para compatibilidad."""
    save_token_to_cookies(token)


def clear_token_from_url():
    """Alias para compatibilidad."""
    clear_token_from_cookies()


def inject_session_recovery_script(cookie_name: str = "session_token"):
    """No-op - las cookies se leen automáticamente."""
    pass


def save_session_to_storage(token: str, cookie_name: str = "session_token"):
    """Guarda el token en cookie."""
    save_token_to_cookies(token)


def clear_session_from_storage(cookie_name: str = "session_token"):
    """Limpia el token de cookies."""
    clear_token_from_cookies()

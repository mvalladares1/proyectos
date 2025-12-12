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


def get_cookie_manager():
    """Obtiene o crea el CookieManager singleton."""
    if not COOKIES_AVAILABLE:
        return None
    
    # Usar un key único para evitar recreación
    return stx.CookieManager(key="rf_cookies")


def get_token_from_cookies() -> Optional[str]:
    """Obtiene el token de la cookie del navegador."""
    # Primero intentar query params (es síncrono y confiable)
    try:
        token = st.query_params.get("session")
        if token:
            return token
    except:
        pass
    
    # Luego intentar cookies
    if COOKIES_AVAILABLE:
        try:
            manager = get_cookie_manager()
            if manager:
                # get_all() es más confiable que get()
                all_cookies = manager.get_all()
                if all_cookies and COOKIE_NAME in all_cookies:
                    return all_cookies[COOKIE_NAME]
        except:
            pass
    
    return None


def save_token_to_cookies(token: str):
    """Guarda el token en una cookie del navegador Y en query params."""
    # Guardar en query params (es más confiable para persistencia)
    try:
        st.query_params["session"] = token
    except:
        pass
    
    # También guardar en cookies si está disponible
    if COOKIES_AVAILABLE:
        try:
            manager = get_cookie_manager()
            if manager:
                manager.set(COOKIE_NAME, token, max_age=int(8 * 60 * 60))  # 8 horas
        except:
            pass


def clear_token_from_cookies():
    """Elimina el token de las cookies y query params."""
    # Limpiar query params
    try:
        if "session" in st.query_params:
            del st.query_params["session"]
    except:
        pass
    
    # Limpiar cookies
    if COOKIES_AVAILABLE:
        try:
            manager = get_cookie_manager()
            if manager:
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
    """Guarda el token en cookie y query params."""
    save_token_to_cookies(token)


def clear_session_from_storage(cookie_name: str = "session_token"):
    """Limpia el token de cookies y query params."""
    clear_token_from_cookies()

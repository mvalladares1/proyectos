"""
Módulo de manejo de cookies y persistencia de sesión para Streamlit.
Sistema multi-capa: Query Params → LocalStorage → Cookies

Usa st.components.v1.html para ejecutar JavaScript (funciona correctamente).
"""
import streamlit as st
import streamlit.components.v1 as components
from typing import Optional

# Importar CookieManager de extra-streamlit-components
try:
    import extra_streamlit_components as stx
    COOKIES_AVAILABLE = True
except ImportError:
    COOKIES_AVAILABLE = False
    stx = None

COOKIE_NAME = "rf_session"
LOCALSTORAGE_KEY = "rf_session_token"


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


# ============ LOCALSTORAGE (JavaScript via components.html) ============

def inject_localstorage_recovery():
    """
    Inyecta script para recuperar token de LocalStorage.
    Si el token existe en LocalStorage pero no en URL, lo añade y recarga.
    
    Usa st.components.v1.html que SÍ ejecuta JavaScript correctamente.
    """
    # Solo inyectar si no hay session en query params
    if get_token_from_query_params():
        return  # Ya hay token en URL, no hacer nada
    
    # Script que recupera de LocalStorage y redirige si encuentra token
    js_code = f"""
    <script>
        (function() {{
            const token = localStorage.getItem('{LOCALSTORAGE_KEY}');
            if (token) {{
                const urlParams = new URLSearchParams(window.location.search);
                if (!urlParams.has('session')) {{
                    urlParams.set('session', token);
                    const newUrl = window.location.pathname + '?' + urlParams.toString();
                    window.location.replace(newUrl);
                }}
            }}
        }})();
    </script>
    """
    # height=0 para que sea invisible
    components.html(js_code, height=0)


def save_token_to_localstorage(token: str):
    """Guarda token en LocalStorage vía JavaScript."""
    js_code = f"""
    <script>
        localStorage.setItem('{LOCALSTORAGE_KEY}', '{token}');
    </script>
    """
    components.html(js_code, height=0)


def clear_token_from_localstorage():
    """Limpia token de LocalStorage."""
    js_code = f"""
    <script>
        localStorage.removeItem('{LOCALSTORAGE_KEY}');
    </script>
    """
    components.html(js_code, height=0)


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


# ============ FUNCIONES MULTI-MÉTODO ============

def get_token_from_cookies() -> Optional[str]:
    """
    Obtiene el token intentando múltiples fuentes en orden de prioridad:
    1. Query Params (más confiable en Streamlit)
    2. Cookies del navegador (fallback)
    
    Nota: LocalStorage se maneja via JavaScript que añade a query params.
    """
    # 1. Query Params
    token = get_token_from_query_params()
    if token:
        return token
    
    # 2. Cookies
    token = get_token_from_browser_cookies()
    if token:
        # Si lo recuperamos de cookies, guardarlo en query params también
        save_token_to_query_params(token)
        return token
    
    return None


def save_session_multi_method(token: str):
    """
    Guarda sesión en todos los métodos disponibles para máxima persistencia.
    """
    # 1. Query Params (prioritario - Streamlit lo lee síncronamente)
    save_token_to_query_params(token)
    
    # 2. LocalStorage (persiste entre pestañas y recargas)
    save_token_to_localstorage(token)
    
    # 3. Cookies
    save_token_to_browser_cookies(token)


def clear_session_multi_method():
    """
    Limpia sesión de todos los métodos de almacenamiento.
    """
    # Query params
    clear_token_from_query_params()
    
    # LocalStorage
    clear_token_from_localstorage()
    
    # Cookies
    clear_token_from_browser_cookies()


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
    """Inyecta script de recuperación de LocalStorage."""
    inject_localstorage_recovery()


def save_session_to_storage(token: str, cookie_name: str = "session_token"):
    """Guarda el token en todos los métodos."""
    save_session_multi_method(token)


def clear_session_from_storage(cookie_name: str = "session_token"):
    """Limpia el token de todos los métodos."""
    clear_session_multi_method()

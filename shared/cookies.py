"""
Módulo de manejo de cookies para Streamlit.
Usa JavaScript injection para leer/escribir cookies del navegador.
"""
import streamlit as st
import streamlit.components.v1 as components
from typing import Optional
import time


def _inject_cookie_script():
    """Inyecta el script de manejo de cookies en la página."""
    script = """
    <script>
    // Funciones de cookies
    function setCookie(name, value, hours) {
        const expires = new Date(Date.now() + hours * 60 * 60 * 1000).toUTCString();
        document.cookie = name + '=' + encodeURIComponent(value) + ';expires=' + expires + ';path=/;SameSite=Lax';
    }
    
    function getCookie(name) {
        const nameEQ = name + '=';
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            let c = cookies[i].trim();
            if (c.indexOf(nameEQ) === 0) {
                return decodeURIComponent(c.substring(nameEQ.length));
            }
        }
        return null;
    }
    
    function deleteCookie(name) {
        document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
    }
    
    // Exponer al parent frame si es necesario
    window.cookieManager = {
        set: setCookie,
        get: getCookie,
        delete: deleteCookie
    };
    </script>
    """
    components.html(script, height=0, width=0)


def get_cookie_via_js(cookie_name: str) -> Optional[str]:
    """ 
    Obtiene una cookie usando query params como bridge.
    El usuario debe incluir ?token=xxx en la URL al recargar.
    """
    # Intentar obtener de query params primero
    params = st.query_params
    token = params.get("token")
    if token:
        return token
    return None


def set_cookie_instruction(cookie_name: str, value: str, hours: int = 8):
    """
    Genera instrucciones JavaScript para establecer una cookie.
    Se muestra como un script que el navegador ejecuta.
    """
    script = f"""
    <script>
    const expires = new Date(Date.now() + {hours} * 60 * 60 * 1000).toUTCString();
    document.cookie = '{cookie_name}=' + encodeURIComponent('{value}') + ';expires=' + expires + ';path=/;SameSite=Lax';
    
    // Almacenar también en localStorage como backup
    localStorage.setItem('{cookie_name}', '{value}');
    </script>
    """
    components.html(script, height=0, width=0)


def get_cookie_from_storage(cookie_name: str) -> Optional[str]:
    """
    Trata de obtener el token de localStorage vía query params.
    Requiere que el JavaScript previo haya almacenado el valor.
    """
    # Este método usa un enfoque de dos pasos:
    # 1. JavaScript lee localStorage y redirige con el token en query params
    # 2. Python lee el query param
    
    params = st.query_params
    token = params.get("session")
    if token:
        return token
    return None


def inject_session_recovery_script(cookie_name: str = "session_token"):
    """
    Inyecta un script que intenta recuperar la sesión de localStorage
    y la pasa a Streamlit vía query params si no está ya presente.
    """
    script = f"""
    <script>
    (function() {{
        // Solo ejecutar si no hay sesión en la URL
        const urlParams = new URLSearchParams(window.location.search);
        if (!urlParams.get('session')) {{
            const savedToken = localStorage.getItem('{cookie_name}');
            if (savedToken && savedToken !== 'null' && savedToken !== 'undefined') {{
                // Redirigir con el token
                urlParams.set('session', savedToken);
                window.location.search = urlParams.toString();
            }}
        }}
    }})();
    </script>
    """
    components.html(script, height=0, width=0)


def save_session_to_storage(token: str, cookie_name: str = "session_token"):
    """
    Guarda el token en localStorage y cookie del navegador.
    """
    script = f"""
    <script>
    localStorage.setItem('{cookie_name}', '{token}');
    
    // También como cookie (8 horas)
    const expires = new Date(Date.now() + 8 * 60 * 60 * 1000).toUTCString();
    document.cookie = '{cookie_name}=' + encodeURIComponent('{token}') + ';expires=' + expires + ';path=/;SameSite=Lax';
    </script>
    """
    components.html(script, height=0, width=0)


def clear_session_from_storage(cookie_name: str = "session_token"):
    """
    Limpia el token de localStorage y cookies.
    """
    script = f"""
    <script>
    localStorage.removeItem('{cookie_name}');
    document.cookie = '{cookie_name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
    
    // Limpiar query params
    const url = new URL(window.location);
    url.searchParams.delete('session');
    window.history.replaceState({{}}, '', url);
    </script>
    """
    components.html(script, height=0, width=0)

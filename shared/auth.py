"""
Módulo de autenticación compartido para todos los dashboards.
Maneja sesiones con tokens, cookies y expiración automática.
"""
import streamlit as st
import httpx
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

# Determinar API_URL basado en ENV
ENV = os.getenv("ENV", "production")
if ENV == "development":
    API_URL = os.getenv("API_URL", "http://rio-api-dev:8000")
else:
    API_URL = os.getenv("API_URL", "http://rio-api-prod:8000")

# Clave para el token en session_state y cookies
TOKEN_KEY = "session_token"

# Bloqueo temporal de la central de dashboards
CENTRAL_DASHBOARDS_DISABLED = True
CENTRAL_DASHBOARDS_DISABLED_TITLE = "¡CENTRAL DE DASHBOARDS ESTA DADA DE BAJA HASTA NUEVO AVISO!"
CENTRAL_DASHBOARDS_DISABLED_MESSAGE = (
    "Por decisiones de la empresa, como departamento de informática ya no es prioridad seguir "
    "manteniendo la central de dashboards activa hasta que sea un requerimiento de la empresa."
)
CENTRAL_DASHBOARDS_DISABLED_SIGNATURE = "Atte: Jefe de Sistemas"


def _get_token_from_cookies() -> Optional[str]:
    """Obtiene el token de las cookies del navegador."""
    try:
        from shared.cookies import get_token_from_browser_cookies
        return get_token_from_browser_cookies()
    except:
        return None


def _get_stored_token() -> Optional[str]:
    """
    Obtiene el token almacenado.
    Primero intenta session_state, luego query params, luego cookies.
    Si encuentra token en cookies pero no en query params, restaura los query params.
    """
    # 1. Intentar session_state (más rápido)
    token = st.session_state.get(TOKEN_KEY)
    if token:
        # Asegurar que query params tiene el token
        if not st.query_params.get("session"):
            try:
                st.query_params["session"] = token
            except:
                pass
        return token
    
    # 2. Intentar query params
    try:
        token = st.query_params.get("session")
        if token:
            st.session_state[TOKEN_KEY] = token
            return token
    except:
        pass
    
    # 3. Intentar cookies del navegador (para recuperación al recargar)
    token = _get_token_from_cookies()
    if token:
        # Almacenar en session_state
        st.session_state[TOKEN_KEY] = token
        # Restaurar query params
        try:
            st.query_params["session"] = token
        except:
            pass
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
    
    # Limpiar query params de la URL (session_key, etc.)
    try:
        st.query_params.clear()
    except:
        pass  # Fallback para versiones antiguas de Streamlit


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
    También muestra el banner de mantenimiento si está activo.
    """
    if central_dashboards_dada_de_baja():
        invalidar_sesion_por_bloqueo_central()
        mostrar_bloqueo_central()
        st.stop()

    if not verificar_autenticacion():
        mostrar_login_requerido()
        return False
    
    # Mostrar banner de mantenimiento si está activo
    mostrar_banner_mantenimiento()
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


def cargar_permisos_usuario():
    """
    Carga los permisos del usuario desde el backend.
    Almacena en session_state para uso posterior.
    Incluye permisos de páginas dentro de cada módulo.
    """
    token = _get_stored_token()
    if not token:
        return
    
    # Evitar recargar si ya se cargaron recientemente
    cache_key = "_permisos_cache_time"
    now = datetime.now().timestamp()
    last_load = st.session_state.get(cache_key, 0)
    
    if now - last_load < 60:  # Cache de 60 segundos
        return
    
    try:
        response = httpx.get(
            f"{API_URL}/api/v1/auth/user-permissions",
            params={"token": token},
            timeout=10.0
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state['allowed_dashboards'] = data.get('allowed_dashboards', [])
            st.session_state['allowed_pages'] = data.get('allowed_pages', {})
            st.session_state['module_structure'] = data.get('module_structure', {})
            st.session_state['restricted_modules'] = data.get('restricted_modules', {})
            st.session_state['is_admin'] = data.get('is_admin', False)
            st.session_state[cache_key] = now
    except:
        pass


def tiene_acceso_pagina(modulo: str, pagina: str) -> bool:
    """
    Verifica si el usuario tiene acceso a una página específica dentro de un módulo.
    
    Args:
        modulo: Clave del módulo (recepciones, produccion, etc.)
        pagina: Clave de la página/tab (curva_abastecimiento, kpis_calidad, etc.)
    
    Returns:
        True si tiene acceso, False si no
        
    Lógica:
    - Admins: acceso total
    - Si el módulo no está en allowed_pages: acceso denegado (usuario no tiene módulo asignado)
    - Si el módulo está pero module_pages está vacío: acceso total al módulo (sin restricciones de páginas)
    - Si el módulo está y module_pages tiene contenido: solo permite las páginas listadas
    """
    # Admins tienen acceso a todo
    if st.session_state.get('is_admin', False):
        return True
    
    # Cargar permisos si no están cargados
    if 'allowed_pages' not in st.session_state:
        cargar_permisos_usuario()
    
    # Verificar acceso
    allowed_pages = st.session_state.get('allowed_pages', {})
    
    # Si allowed_pages está completamente vacío, permitir (problema de carga)
    if not allowed_pages:
        return True
    
    # Si el módulo no está en allowed_pages, denegar (usuario no tiene módulo)
    if modulo not in allowed_pages:
        return False
    
    module_pages = allowed_pages.get(modulo, [])
    
    # Si module_pages está vacío, significa sin restricciones → permitir todo
    if not module_pages:
        return True
    
    # Si tiene páginas, verificar que la página esté en la lista
    return pagina in module_pages


def filtrar_tabs_permitidos(modulo: str, tabs_config: List[Dict[str, str]]) -> tuple:
    """
    Filtra los tabs de un módulo según los permisos del usuario.
    
    Args:
        modulo: Clave del módulo (recepciones, produccion, etc.)
        tabs_config: Lista de dicts con 'slug' y 'label'
                     Ejemplo: [{"slug": "kpis", "label": "📊 KPIs"}, ...]
        
    Returns:
        tuple: (list de labels permitidos, list de slugs permitidos)
    """
    # Cargar permisos si no están cargados
    if 'allowed_pages' not in st.session_state:
        cargar_permisos_usuario()
    
    # Admins ven todo
    if st.session_state.get('is_admin', False):
        labels = [t['label'] for t in tabs_config]
        slugs = [t['slug'] for t in tabs_config]
        return (labels, slugs)
    
    # Obtener páginas permitidas para este módulo
    allowed_pages = st.session_state.get('allowed_pages', {}).get(modulo, [])
    
    # Si lista vacía, significa que no hay restricciones (módulo público)
    if not allowed_pages:
        labels = [t['label'] for t in tabs_config]
        slugs = [t['slug'] for t in tabs_config]
        return (labels, slugs)
    
    # Filtrar solo los tabs permitidos
    tabs_filtrados = [t for t in tabs_config if t['slug'] in allowed_pages]
    labels = [t['label'] for t in tabs_filtrados]
    slugs = [t['slug'] for t in tabs_filtrados]
    
    return (labels, slugs)


def verificar_acceso_tab(modulo: str, pagina: str, nombre_pagina: str = None) -> bool:
    """
    Verifica si el usuario tiene acceso a un tab/página.
    Si no tiene acceso, muestra mensaje de error Y DETIENE la ejecución del tab.
    
    Uso dentro de un tab:
        with tab_kpis:
            if not verificar_acceso_tab("recepciones", "kpis_calidad", "KPIs y Calidad"):
                pass  # El código después de esto NO se ejecutará
            # resto del contenido del tab se ejecuta solo si tiene acceso
    
    Args:
        modulo: Clave del módulo (recepciones, produccion, etc.)
        pagina: Slug de la página/tab
        nombre_pagina: Nombre amigable para mostrar en el mensaje
        
    Returns:
        True si tiene acceso, False si no (y muestra mensaje + st.stop())
    """
    if tiene_acceso_pagina(modulo, pagina):
        return True
    
    # Mostrar mensaje de acceso denegado
    nombre = nombre_pagina or pagina.replace("_", " ").title()
    st.error(f"🚫 **Acceso Restringido** - No tienes permisos para ver '{nombre}'.")
    st.info("💡 Contacta al administrador para solicitar acceso a esta sección.")
    # NO llamamos st.stop() aquí porque detendría toda la página, no solo el tab
    return False


def proteger_tab(modulo: str, pagina: str, nombre_pagina: str = None) -> bool:
    """
    Protege un tab específico. Si no tiene acceso, muestra error y retorna False.
    El código que llama DEBE verificar el retorno y no continuar si es False.
    
    Uso recomendado:
        with tab_kpis:
            if not proteger_tab("recepciones", "kpis_calidad", "KPIs y Calidad"):
                st.stop()  # Detiene solo este tab
            # Contenido del tab aquí
    
    Args:
        modulo: Clave del módulo
        pagina: Slug de la página/tab
        nombre_pagina: Nombre amigable para mostrar
        
    Returns:
        True si tiene acceso, False si no (y muestra mensaje)
    """
    if tiene_acceso_pagina(modulo, pagina):
        return True
    
    nombre = nombre_pagina or pagina.replace("_", " ").title()
    st.error(f"🚫 **Acceso Restringido** - No tienes permisos para ver '{nombre}'.")
    st.info("💡 Contacta al administrador para solicitar acceso a esta sección.")
    return False


def proteger_modulo(modulo_key: str) -> bool:
    """
    Protege un módulo específico verificando autenticación y permisos.
    
    Args:
        modulo_key: Clave del módulo (recepciones, produccion, stock, etc.)
    
    Returns:
        True si el usuario tiene acceso, False si no (y detiene la página)
    """
    if central_dashboards_dada_de_baja():
        invalidar_sesion_por_bloqueo_central()
        mostrar_bloqueo_central()
        st.stop()

    # 1. Verificar autenticación
    if not verificar_autenticacion():
        mostrar_login_requerido()
        return False
    
    # 2. Mostrar banner de mantenimiento si aplica
    mostrar_banner_mantenimiento()
    
    # 3. Cargar permisos si no están cargados
    if 'allowed_dashboards' not in st.session_state or 'restricted_modules' not in st.session_state:
        cargar_permisos_usuario()
    
    # 4. Admins tienen acceso a todo
    if st.session_state.get('is_admin', False):
        return True
    
    # 5. Verificar si el módulo tiene restricciones
    restricted_modules = st.session_state.get('restricted_modules', {})
    
    # Si el módulo NO está restringido (lista vacía o no existe), es público
    if modulo_key not in restricted_modules or not restricted_modules.get(modulo_key):
        return True  # Módulo público, permitir acceso
    
    # 6. Si está restringido, verificar si el usuario está en la lista
    allowed = st.session_state.get('allowed_dashboards', [])
    if modulo_key in allowed:
        return True
    
    # No tiene acceso - mostrar mensaje y detener
    st.error(f"🚫 No tienes acceso al módulo **{modulo_key.title()}**")
    st.info("💡 Contacta al administrador para solicitar acceso a este módulo.")
    st.stop()
    return False


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


# ============ BANNER DE MANTENIMIENTO ============

def central_dashboards_dada_de_baja() -> bool:
    """Indica si la central de dashboards está deshabilitada temporalmente."""
    return CENTRAL_DASHBOARDS_DISABLED


def invalidar_sesion_por_bloqueo_central():
    """Limpia storage y sesión cuando la central está deshabilitada."""
    try:
        from shared.cookies import clear_session_multi_method
        clear_session_multi_method()
    except Exception:
        pass

    token = _get_stored_token()
    if token or st.session_state:
        cerrar_sesion()


def mostrar_bloqueo_central():
    """Renderiza el aviso institucional de baja de la central."""
    st.markdown(
        """
        <style>
            .central-shutdown-banner {
                border: 2px solid #9f1239;
                background: linear-gradient(135deg, #7f1d1d 0%, #3f0d12 100%);
                color: #fff7ed;
                border-radius: 16px;
                padding: 1.5rem;
                margin: 1rem 0 1.5rem 0;
                box-shadow: 0 12px 30px rgba(127, 29, 29, 0.28);
            }
            .central-shutdown-banner h2 {
                margin: 0 0 0.75rem 0;
                font-size: 1.65rem;
                line-height: 1.2;
            }
            .central-shutdown-banner p {
                margin: 0;
                font-size: 1rem;
                line-height: 1.55;
            }
            .central-shutdown-banner .signature {
                margin-top: 1rem;
                font-weight: 700;
                color: #fecaca;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="central-shutdown-banner">
            <h2>{CENTRAL_DASHBOARDS_DISABLED_TITLE}</h2>
            <p>{CENTRAL_DASHBOARDS_DISABLED_MESSAGE}</p>
            <p class="signature">{CENTRAL_DASHBOARDS_DISABLED_SIGNATURE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def obtener_estado_mantenimiento() -> Dict[str, Any]:
    """Obtiene el estado del banner de mantenimiento desde el backend."""
    try:
        response = httpx.get(
            f"{API_URL}/api/v1/permissions/maintenance/status",
            timeout=5.0
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"enabled": False, "message": ""}


def mostrar_banner_mantenimiento():
    """Muestra el banner de mantenimiento si está activo."""
    # Cachear el estado brevemente para evitar muchas llamadas
    cache_key = "_maintenance_cache"
    cache_time_key = "_maintenance_cache_time"
    
    now = datetime.now().timestamp()
    last_check = st.session_state.get(cache_time_key, 0)
    
    # Revalidar cada 30 segundos
    if now - last_check > 30:
        config = obtener_estado_mantenimiento()
        st.session_state[cache_key] = config
        st.session_state[cache_time_key] = now
    else:
        config = st.session_state.get(cache_key, {"enabled": False, "message": ""})
    
    if config.get("enabled", False):
        message = config.get("message", "El sistema está siendo ajustado en este momento.")
        st.warning(f"⚠️ **AVISO:** {message}")


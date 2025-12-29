"""
Panel de administración: gestiona qué usuarios pueden acceder a cada dashboard y página del sistema.
Rediseñado para ser más usable y dinámico.
"""
import os
from typing import Dict, List

import httpx
import pandas as pd
import streamlit as st

from shared.auth import es_admin, proteger_modulo, get_credenciales

st.set_page_config(
    page_title="Permisos",
    page_icon="⚙️",
    layout="wide"
)

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

if not proteger_modulo("permisos"):
    st.stop()

if not es_admin():
    st.error("Solo administradores pueden acceder a este panel.")
    st.stop()

# Obtener credenciales del backend
username, password = get_credenciales()

if not username or not password:
    st.warning("Inicia sesión con credenciales válidas para administrar los permisos.")
    st.stop()

# ============ ESTILOS CSS ============
st.markdown("""
<style>
.permission-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 10px;
    padding: 15px;
    margin: 10px 0;
    border: 1px solid #3498db33;
}
.module-header {
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 10px;
}
.page-item {
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
    padding: 10px 15px;
    margin: 5px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.public-badge {
    background: #27ae60;
    color: white;
    padding: 3px 10px;
    border-radius: 15px;
    font-size: 12px;
}
.restricted-badge {
    background: #e74c3c;
    color: white;
    padding: 3px 10px;
    border-radius: 15px;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

# ============ FUNCIONES API ============

@st.cache_data(ttl=30)
def fetch_full_permissions():
    """Obtiene todos los permisos (módulos y páginas)"""
    try:
        resp = httpx.get(
            f"{API_URL}/api/v1/permissions/all",
            params={"admin_username": username, "admin_password": password},
            timeout=10.0
        )
        resp.raise_for_status()
        return resp.json()
    except:
        return {"dashboards": {}, "pages": {}}

@st.cache_data(ttl=60)
def fetch_module_structure():
    """Obtiene la estructura de módulos y páginas"""
    try:
        resp = httpx.get(f"{API_URL}/api/v1/permissions/pages/structure", timeout=10.0)
        resp.raise_for_status()
        return resp.json().get("modules", {})
    except:
        return {}

def update_module_permission(action: str, dashboard: str, email: str):
    """Asigna o revoca permiso a un módulo"""
    resp = httpx.post(
        f"{API_URL}/api/v1/permissions/{action}",
        json={
            "dashboard": dashboard,
            "email": email,
            "admin_username": username,
            "admin_password": password
        },
        timeout=10.0
    )
    resp.raise_for_status()
    st.cache_data.clear()
    return resp.json()

def update_page_permission(action: str, module: str, page: str, email: str):
    """Asigna o revoca permiso a una página"""
    resp = httpx.post(
        f"{API_URL}/api/v1/permissions/pages/{action}",
        json={
            "module": module,
            "page": page,
            "email": email,
            "admin_username": username,
            "admin_password": password
        },
        timeout=10.0
    )
    resp.raise_for_status()
    st.cache_data.clear()
    return resp.json()

# ============ MAPEO DE NOMBRES ============
MODULE_NAMES = {
    "recepciones": "📥 Recepciones",
    "produccion": "🏭 Producción",
    "bandejas": "📊 Bandejas",
    "stock": "📦 Stock",
    "containers": "🚢 Containers",
    "rendimiento": "📈 Rendimiento",
    "finanzas": "💰 Finanzas",
    "compras": "🛒 Compras",
    "permisos": "⚙️ Permisos",
}

# ============ UI PRINCIPAL ============
st.title("🛠️ Panel de Permisos")
st.caption("Configura quién puede ver cada módulo y página del sistema")

# Cargar datos
permisos = fetch_full_permissions()
estructura = fetch_module_structure()
modulos_perms = permisos.get("dashboards", {})
paginas_perms = permisos.get("pages", {})

# ============ TABS PRINCIPALES ============
tab_modulos, tab_paginas, tab_usuarios, tab_config = st.tabs([
    "📁 Módulos", 
    "📄 Páginas",
    "👤 Por Usuario",
    "⚙️ Configuración"
])

# ============ TAB: MÓDULOS ============
with tab_modulos:
    st.subheader("Permisos por Módulo")
    st.info("💡 **Lista vacía** = Módulo público. **Con emails** = Solo esos usuarios pueden acceder.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Mostrar módulos con sus permisos
        for modulo, emails in modulos_perms.items():
            with st.container():
                nombre = MODULE_NAMES.get(modulo, modulo.title())
                es_publico = len(emails) == 0
                
                col_nombre, col_estado, col_accion = st.columns([3, 1, 2])
                
                with col_nombre:
                    st.markdown(f"**{nombre}**")
                    if emails:
                        st.caption(f"Acceso: {', '.join(emails[:3])}{'...' if len(emails) > 3 else ''}")
                    else:
                        st.caption("Acceso: Todos los usuarios")
                
                with col_estado:
                    if es_publico:
                        st.success("Público")
                    else:
                        st.error(f"Restringido ({len(emails)})")
                
                with col_accion:
                    if st.button("Gestionar", key=f"manage_{modulo}", use_container_width=True):
                        st.session_state['selected_module'] = modulo
                
                st.divider()
    
    with col2:
        st.markdown("### Asignar Acceso")
        
        selected = st.session_state.get('selected_module', list(modulos_perms.keys())[0] if modulos_perms else '')
        
        modulo_sel = st.selectbox(
            "Módulo",
            options=list(modulos_perms.keys()),
            format_func=lambda x: MODULE_NAMES.get(x, x.title()),
            index=list(modulos_perms.keys()).index(selected) if selected in modulos_perms else 0,
            key="modulo_select"
        )
        
        nuevo_email = st.text_input("Email del usuario", placeholder="usuario@empresa.cl", key="nuevo_email_modulo")
        
        col_asignar, col_revocar = st.columns(2)
        
        with col_asignar:
            if st.button("➕ Asignar", type="primary", use_container_width=True):
                if nuevo_email:
                    try:
                        update_module_permission("assign", modulo_sel, nuevo_email)
                        st.success(f"✅ Acceso asignado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Ingresa un email")
        
        with col_revocar:
            if st.button("➖ Revocar", use_container_width=True):
                if nuevo_email:
                    try:
                        update_module_permission("remove", modulo_sel, nuevo_email)
                        st.success(f"✅ Acceso revocado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Ingresa un email")
        
        # Mostrar emails actuales del módulo seleccionado
        st.markdown("---")
        st.markdown(f"**Usuarios con acceso a {MODULE_NAMES.get(modulo_sel, modulo_sel)}:**")
        emails_modulo = modulos_perms.get(modulo_sel, [])
        if emails_modulo:
            for email in emails_modulo:
                col_email, col_del = st.columns([4, 1])
                with col_email:
                    st.text(email)
                with col_del:
                    if st.button("🗑️", key=f"del_{modulo_sel}_{email}"):
                        try:
                            update_module_permission("remove", modulo_sel, email)
                            st.rerun()
                        except:
                            pass
        else:
            st.caption("Sin restricciones (público)")

# ============ TAB: PÁGINAS ============
with tab_paginas:
    st.subheader("Permisos por Página/Tab")
    st.info("💡 Control granular: restringe acceso a tabs específicos dentro de cada módulo.")
    
    # Selector de módulo
    modulo_paginas = st.selectbox(
        "Selecciona un módulo para ver sus páginas",
        options=list(estructura.keys()),
        format_func=lambda x: MODULE_NAMES.get(x, x.title()),
        key="modulo_paginas_select"
    )
    
    if modulo_paginas and modulo_paginas in estructura:
        paginas = estructura[modulo_paginas]
        
        st.markdown(f"### Páginas de {MODULE_NAMES.get(modulo_paginas, modulo_paginas)}")
        
        for pagina in paginas:
            page_slug = pagina["slug"]
            page_name = pagina["name"]
            page_key = f"{modulo_paginas}.{page_slug}"
            emails_pagina = paginas_perms.get(page_key, [])
            es_publico = len(emails_pagina) == 0
            
            with st.expander(f"📄 {page_name} {'🌐 Público' if es_publico else f'🔒 Restringido ({len(emails_pagina)})'}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    if emails_pagina:
                        st.markdown("**Usuarios con acceso:**")
                        for email in emails_pagina:
                            col_e, col_d = st.columns([5, 1])
                            with col_e:
                                st.text(f"  • {email}")
                            with col_d:
                                if st.button("❌", key=f"del_page_{page_key}_{email}"):
                                    try:
                                        update_page_permission("remove", modulo_paginas, page_slug, email)
                                        st.rerun()
                                    except:
                                        pass
                    else:
                        st.success("✅ Esta página es pública para todos los usuarios con acceso al módulo.")
                
                with col2:
                    st.markdown("**Agregar acceso:**")
                    nuevo_email_pg = st.text_input("Email", placeholder="usuario@empresa.cl", key=f"email_{page_key}")
                    if st.button("Asignar", key=f"assign_{page_key}", type="primary"):
                        if nuevo_email_pg:
                            try:
                                update_page_permission("assign", modulo_paginas, page_slug, nuevo_email_pg)
                                st.success("✅ Acceso asignado")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

# ============ TAB: POR USUARIO ============
with tab_usuarios:
    st.subheader("Ver Permisos de un Usuario")
    st.info("💡 Consulta a qué módulos y páginas tiene acceso un usuario específico.")
    
    email_consulta = st.text_input("Email del usuario a consultar", placeholder="usuario@empresa.cl", key="email_consulta")
    
    if st.button("🔍 Consultar permisos", type="primary") and email_consulta:
        try:
            resp = httpx.get(
                f"{API_URL}/api/v1/permissions/user",
                params={"username": email_consulta},
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                allowed = data.get("allowed", [])
                is_admin = data.get("is_admin", False)
                
                if is_admin:
                    st.success(f"🔑 **{email_consulta}** es ADMINISTRADOR - Tiene acceso a todo el sistema")
                else:
                    st.markdown(f"### Módulos permitidos para **{email_consulta}**:")
                    
                    col1, col2, col3 = st.columns(3)
                    for i, modulo in enumerate(allowed):
                        with [col1, col2, col3][i % 3]:
                            st.success(f"✅ {MODULE_NAMES.get(modulo, modulo)}")
                    
                    # Módulos sin acceso
                    no_access = [m for m in modulos_perms.keys() if m not in allowed]
                    if no_access:
                        st.markdown("### Módulos sin acceso:")
                        for modulo in no_access:
                            st.error(f"🚫 {MODULE_NAMES.get(modulo, modulo)}")
            else:
                st.error("Error al consultar permisos")
        except Exception as e:
            st.error(f"Error: {e}")

# ============ TAB: CONFIGURACIÓN ============
with tab_config:
    st.subheader("⚠️ Banner de Mantenimiento")
    st.caption("Activa este banner para mostrar un aviso en todas las páginas del sistema.")
    
    # Obtener estado actual del banner
    try:
        maint_resp = httpx.get(f"{API_URL}/api/v1/permissions/maintenance/status", timeout=5.0)
        maint_config = maint_resp.json() if maint_resp.status_code == 200 else {"enabled": False, "message": ""}
    except:
        maint_config = {"enabled": False, "message": "El sistema está siendo ajustado en este momento."}
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        banner_enabled = st.toggle(
            "Banner activo",
            value=maint_config.get("enabled", False),
            key="banner_toggle"
        )
    
    with col2:
        banner_message = st.text_input(
            "Mensaje del banner",
            value=maint_config.get("message", "El sistema está siendo ajustado en este momento."),
            key="banner_message",
            placeholder="El sistema está siendo ajustado..."
        )
    
    if st.button("💾 Guardar configuración de banner", type="primary"):
        try:
            resp = httpx.post(
                f"{API_URL}/api/v1/permissions/maintenance",
                json={
                    "enabled": banner_enabled,
                    "message": banner_message,
                    "admin_username": username,
                    "admin_password": password
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                st.success("✅ Configuración de banner guardada.")
                st.rerun()
            else:
                st.error(f"Error: {resp.text}")
        except Exception as e:
            st.error(f"Error al guardar: {e}")
    
    if banner_enabled:
        st.warning(f"⚠️ **AVISO (Vista previa):** {banner_message}")
    
    st.divider()
    
    # Sección de administradores
    st.subheader("👑 Administradores")
    st.caption("Los administradores tienen acceso completo a todo el sistema.")
    
    admins = permisos.get("admins", [])
    for admin_email in admins:
        st.markdown(f"• **{admin_email}**")
    
    st.divider()
    
    # ============ EXCLUSIONES DE RECEPCIONES ============
    st.subheader("🚫 Exclusiones de Valorización")
    st.caption("Recepciones que se contabilizan en Kg pero se excluyen del cálculo de costos. Útil para corregir malos ingresos.")
    
    # Archivo de configuración para exclusiones
    import json
    EXCLUSIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shared", "exclusiones.json")
    
    # Cargar exclusiones existentes
    exclusiones = {"recepciones": []}
    try:
        if os.path.exists(EXCLUSIONS_FILE):
            with open(EXCLUSIONS_FILE, 'r') as f:
                exclusiones = json.load(f)
    except:
        pass
    
    # Mostrar exclusiones actuales
    col_excl1, col_excl2 = st.columns([2, 1])
    
    with col_excl1:
        st.markdown("**Recepciones excluidas de valorización:**")
        if exclusiones.get("recepciones"):
            for recep_id in exclusiones["recepciones"]:
                col_id, col_del = st.columns([5, 1])
                with col_id:
                    st.text(f"📋 Recepción ID: {recep_id}")
                with col_del:
                    if st.button("🗑️", key=f"del_excl_{recep_id}"):
                        exclusiones["recepciones"].remove(recep_id)
                        with open(EXCLUSIONS_FILE, 'w') as f:
                            json.dump(exclusiones, f, indent=2)
                        st.success(f"Recepción {recep_id} eliminada de exclusiones")
                        st.rerun()
        else:
            st.info("No hay recepciones excluidas actualmente.")
    
    with col_excl2:
        st.markdown("**Agregar exclusión:**")
        st.caption("Ingresa el ID de la recepción (ej: 123456 o RF/REC/00123)")
        nueva_exclusion = st.text_input("ID de recepción", placeholder="12345 o RF/REC/00123", key="nueva_exclusion")
        
        if st.button("➕ Excluir recepción", type="primary", key="btn_add_exclusion"):
            if nueva_exclusion and nueva_exclusion.strip():
                excl_val = nueva_exclusion.strip()
                # Intentar convertir a int si es solo números
                try:
                    excl_val = int(excl_val)
                except:
                    pass  # Mantener como string si tiene letras
                    
                if excl_val not in exclusiones["recepciones"]:
                    exclusiones["recepciones"].append(excl_val)
                    # Guardar en archivo
                    os.makedirs(os.path.dirname(EXCLUSIONS_FILE), exist_ok=True)
                    with open(EXCLUSIONS_FILE, 'w') as f:
                        json.dump(exclusiones, f, indent=2)
                    st.success(f"✅ Recepción {excl_val} agregada a exclusiones")
                    st.rerun()
                else:
                    st.warning("Esta recepción ya está excluida")
            else:
                st.warning("Ingresa un ID de recepción válido")
    
    st.info("💡 Las recepciones excluidas se contarán en los Kg totales pero su costo NO se sumará a la valorización.")

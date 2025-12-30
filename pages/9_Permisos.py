"""
Panel de administración: gestiona qué usuarios pueden acceder a cada dashboard y página del sistema.
Rediseñado para ser más usable y dinámico mediante fragments.
"""
import os
import json
from typing import Dict, List
from datetime import datetime, timedelta

import httpx
import pandas as pd
import streamlit as st

from shared.auth import es_admin, proteger_modulo, get_credenciales

# Configuración de página
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

# ============ ESTADOS Y PERSISTENCIA ============
if "perms_version" not in st.session_state:
    st.session_state.perms_version = 0

def refresh_perms():
    st.session_state.perms_version += 1
    st.cache_data.clear()

# ============ ESTILOS CSS ============
st.markdown("""
<style>
.permission-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
    border: 1px solid #3498db44;
    transition: all 0.3s ease;
}
.permission-card:hover {
    border-color: #3498db88;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
.module-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    border-bottom: 1px solid #ffffff11;
}
.module-row:last-child {
    border-bottom: none;
}
.badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}
.badge-public { background: #2ecc71; color: white; }
.badge-restricted { background: #e74c3c; color: white; }
</style>
""", unsafe_allow_html=True)

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

# ============ FUNCIONES API (CON CALLBACKS) ============

@st.cache_data(ttl=30)
def fetch_full_permissions(version=0):
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
        return {"dashboards": {}, "pages": {}, "admins": []}

@st.cache_data(ttl=60)
def fetch_module_structure():
    """Obtiene la estructura de módulos y páginas"""
    try:
        resp = httpx.get(f"{API_URL}/api/v1/permissions/pages/structure", timeout=10.0)
        resp.raise_for_status()
        return resp.json().get("modules", {})
    except:
        return {}

def cb_update_module(action: str, dashboard: str, email: str = None):
    """Callback para asignar o revocar permiso a un módulo"""
    # Si viene de un form_submit sin email directo, lo sacamos del session_state
    if email is None:
        email = st.session_state.get(f"new_email_{dashboard}", "").strip()
    
    if not email:
        st.error("Email requerido")
        return

    try:
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
        refresh_perms()
    except Exception as e:
        st.error(f"Error: {e}")

def cb_update_page(action: str, module: str, page: str, email: str = None):
    """Callback para asignar o revocar permiso a una página"""
    if email is None:
        email = st.session_state.get(f"new_email_{module}_{page}", "").strip()
        
    if not email:
        st.error("Email requerido")
        return

    try:
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
        refresh_perms()
    except Exception as e:
        st.error(f"Error: {e}")

# ============ UI PRINCIPAL ============
st.title("🛠️ Panel de Permisos")
st.caption("Configura quién puede ver cada módulo y página del sistema")

# ============ FRAGMENTS ============

@st.fragment
def fragment_modulos():
    st.subheader("Permisos por Módulo")
    st.info("💡 **Sin emails** = Público. **Con emails** = Restringido.")
    
    permisos = fetch_full_permissions(st.session_state.perms_version)
    modulos_perms = permisos.get("dashboards", {})
    
    col_list, col_manage = st.columns([2, 1])
    
    with col_list:
        for modulo, emails in modulos_perms.items():
            nombre = MODULE_NAMES.get(modulo, modulo.title())
            es_publico = len(emails) == 0
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"#### {nombre}")
                if es_publico:
                    c2.markdown('<span class="badge badge-public">Público</span>', unsafe_allow_html=True)
                else:
                    c2.markdown(f'<span class="badge badge-restricted">Restringido ({len(emails)})</span>', unsafe_allow_html=True)
                
                # Al hacer clic, guardamos en session_state. Esto NO dispara rerun global si está en fragment.
                if c3.button("Gestionar", key=f"btn_m_{modulo}", use_container_width=True):
                    st.session_state.selected_module_id = modulo
    
    with col_manage:
        active_mod = st.session_state.get('selected_module_id', list(modulos_perms.keys())[0] if modulos_perms else None)
        if active_mod:
            st.markdown(f"### Gestionar {MODULE_NAMES.get(active_mod, active_mod)}")
            
            # Usamos on_click para que se procese ANTES de que el fragment se redibuje
            st.text_input("Agregar email:", placeholder="ejemplo@riofuturo.cl", key=f"new_email_{active_mod}")
            if st.button("➕ Asignar", use_container_width=True, key=f"btn_assign_{active_mod}"):
                cb_update_module("assign", active_mod)
            
            st.divider()
            st.markdown("**Usuarios con acceso:**")
            emails_mod = modulos_perms.get(active_mod, [])
            if emails_mod:
                for email in emails_mod:
                    ce, cd = st.columns([4, 1])
                    ce.text(email)
                    cd.button("🗑️", key=f"del_m_{active_mod}_{email}", 
                              on_click=cb_update_module, 
                              args=("remove", active_mod, email))
            else:
                st.caption("Cualquier usuario logueado puede entrar.")

@st.fragment
def fragment_paginas():
    st.subheader("Permisos por Página/Tab")
    st.info("💡 Control granular: restringe acceso a pestañas internas de cada módulo.")
    
    estructura = fetch_module_structure()
    permisos = fetch_full_permissions(st.session_state.perms_version)
    paginas_perms = permisos.get("pages", {})
    
    mod_selected = st.selectbox(
        "Módulo",
        options=list(estructura.keys()),
        format_func=lambda x: MODULE_NAMES.get(x, x.title()),
        key="frag_paginas_mod_sel"
    )
    
    if mod_selected and mod_selected in estructura:
        paginas = estructura[mod_selected]
        for pg in paginas:
            slug, name = pg["slug"], pg["name"]
            key = f"{mod_selected}.{slug}"
            emails_pg = paginas_perms.get(key, [])
            es_publico = len(emails_pg) == 0
            
            with st.expander(f"📄 {name} | {'🌐 Público' if es_publico else f'🔒 Restringido ({len(emails_pg)})'}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    if emails_pg:
                        for e in emails_pg:
                            ce, cd = st.columns([5, 1])
                            ce.text(f"• {e}")
                            cd.button("🗑️", key=f"del_p_{key}_{e}", 
                                      on_click=cb_update_page, 
                                      args=("remove", mod_selected, slug, e))
                    else:
                        st.success("Acceso público (si tiene acceso al módulo)")
                
                with c2:
                    st.text_input("Nuevo acceso:", key=f"new_email_{mod_selected}_{slug}")
                    st.button("Asignar", key=f"btn_p_{key}", type="primary",
                              on_click=cb_update_page,
                              args=("assign", mod_selected, slug))

@st.fragment
def fragment_usuarios():
    st.subheader("Control por Usuario")
    q_email = st.text_input("Buscar email:", placeholder="usuario@riofuturo.cl")
    if q_email or st.button("🔍 Consultar"):
        try:
            resp = httpx.get(f"{API_URL}/api/v1/permissions/user", params={"username": q_email})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("is_admin"):
                    st.success(f"👑 **{q_email}** es ADMINISTRADOR")
                else:
                    allowed = data.get("allowed", [])
                    st.markdown(f"**Módulos para {q_email}:**")
                    for m in allowed:
                        st.markdown(f"- {MODULE_NAMES.get(m, m)}")
            else:
                st.error("No se encontró el usuario o error en API")
        except:
            st.error("Error de conexión")

@st.fragment
def fragment_config():
    st.subheader("Configuración Global")
    
    # 1. Mantenimiento
    with st.container(border=True):
        st.markdown("### ⚠️ Modo Mantenimiento")
        try:
            m_resp = httpx.get(f"{API_URL}/api/v1/permissions/maintenance/status")
            m_cfg = m_resp.json() if m_resp.status_code == 200 else {"enabled": False, "message": ""}
        except:
            m_cfg = {"enabled": False, "message": ""}
            
        c1, c2 = st.columns([1, 3])
        m_enabled = c1.toggle("Activar Banner", value=m_cfg["enabled"], key="cfg_maint_enabled")
        m_msg = c2.text_input("Mensaje", value=m_cfg["message"], key="cfg_maint_msg")
        
        def cb_save_maint():
            try:
                httpx.post(f"{API_URL}/api/v1/permissions/maintenance", json={
                    "enabled": st.session_state.cfg_maint_enabled, 
                    "message": st.session_state.cfg_maint_msg,
                    "admin_username": username, "admin_password": password
                })
                st.toast("✅ Configuración de mantenimiento guardada")
            except: 
                st.error("Error al guardar mantenimiento")

        st.button("Guardar Mantenimiento", type="primary", on_click=cb_save_maint)

    # 2. Exclusiones
    st.divider()
    st.markdown("### 🚫 Exclusiones de Valorización")
    EXCLUSIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shared", "exclusiones.json")
    
    try:
        with open(EXCLUSIONS_FILE, 'r') as f: exclusiones = json.load(f)
    except: exclusiones = {"recepciones": []}
    
    tabL, tabA = st.tabs(["📋 Actuales", "➕ Agregar"])
    
    with tabL:
        if exclusiones["recepciones"]:
            for rid in exclusiones["recepciones"]:
                cl, cd = st.columns([5, 1])
                cl.text(rid)
                
                def cb_del_excl(target_id=rid):
                    exclusiones["recepciones"].remove(target_id)
                    with open(EXCLUSIONS_FILE, 'w') as f: json.dump(exclusiones, f)
                    st.toast(f"Recepción {target_id} eliminada de exclusiones")

                cd.button("🗑️", key=f"excl_del_{rid}", on_click=cb_del_excl)
        else: st.caption("No hay exclusiones")
        
    with tabA:
        c1, c2 = st.columns(2)
        f1 = c1.date_input("Desde", datetime.now()-timedelta(days=7), key="excl_date_from")
        f2 = c2.date_input("Hasta", datetime.now(), key="excl_date_to")
        
        def cb_search_receps():
            try:
                resp = httpx.get(f"{API_URL}/api/v1/recepciones-mp/", params={
                    "username": username, "password": password,
                    "fecha_inicio": st.session_state.excl_date_from.isoformat(), 
                    "fecha_fin": st.session_state.excl_date_to.isoformat()
                })
                if resp.status_code == 200:
                    st.session_state.r_list_excl = resp.json()
            except:
                st.error("Error al buscar recepciones")

        st.button("🔍 Buscar Recepciones", on_click=cb_search_receps)
                
        if "r_list_excl" in st.session_state:
            r_list = st.session_state.r_list_excl
            opts = [f"{r['albaran']} | {r['productor']} ({r['kg_recepcionados']:.0f}Kg)" for r in r_list]
            sels = st.multiselect("Seleccionar para excluir:", opts, key="excl_multiselect")
            
            def cb_confirm_excl():
                current_excl = exclusiones["recepciones"]
                for s in st.session_state.excl_multiselect:
                    alb = s.split("|")[0].strip()
                    if alb not in current_excl: 
                        current_excl.append(alb)
                with open(EXCLUSIONS_FILE, 'w') as f: json.dump(exclusiones, f)
                st.toast("✅ Exclusiones guardadas")
                if "r_list_excl" in st.session_state:
                    del st.session_state.r_list_excl

            if sels:
                st.button("✅ Confirmar Exclusión", type="primary", on_click=cb_confirm_excl)

# ============ TABS PRINCIPALES ============
tab1, tab2, tab3, tab4 = st.tabs(["📁 Módulos", "📄 Páginas", "👤 Usuarios", "⚙️ Configuración"])

with tab1: fragment_modulos()
with tab2: fragment_paginas()
with tab3: fragment_usuarios()
with tab4: fragment_config()

"""
Contenido principal del panel de Permisos.
Fragments para cada tab.
"""
import os
import json
from datetime import datetime, timedelta

import httpx
import streamlit as st

from .shared import (
    API_URL, MODULE_NAMES,
    fetch_full_permissions, fetch_module_structure,
    update_module_permission, update_page_permission,
    get_user_permissions, get_maintenance_config, save_maintenance_config,
    refresh_perms
)


def render(username: str, password: str):
    """Renderiza el contenido principal del panel."""
    st.title("🛠️ Panel de Permisos")
    st.caption("Configura quién puede ver cada módulo y página del sistema")
    
    # Tabs principales
    tab1, tab2, tab3, tab4 = st.tabs(["📁 Módulos", "📄 Páginas", "👤 Usuarios", "⚙️ Configuración"])
    
    with tab1:
        _fragment_modulos(username, password)
    with tab2:
        _fragment_paginas(username, password)
    with tab3:
        _fragment_usuarios()
    with tab4:
        _fragment_config(username, password)


@st.fragment
def _fragment_modulos(username: str, password: str):
    """Fragment para gestión de módulos."""
    st.subheader("Permisos por Módulo")
    st.info("💡 **Sin emails** = Público. **Con emails** = Restringido.")
    
    permisos = fetch_full_permissions(username, password, st.session_state.perms_version)
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
                
                if c3.button("Gestionar", key=f"btn_m_{modulo}", use_container_width=True):
                    st.session_state.selected_module_id = modulo
    
    with col_manage:
        active_mod = st.session_state.get('selected_module_id', list(modulos_perms.keys())[0] if modulos_perms else None)
        if active_mod:
            st.markdown(f"### Gestionar {MODULE_NAMES.get(active_mod, active_mod)}")
            
            with st.form(key=f"form_mod_{active_mod}", clear_on_submit=True):
                new_email = st.text_input("Agregar email:", placeholder="ejemplo@riofuturo.cl")
                if st.form_submit_button("➕ Asignar", use_container_width=True):
                    if update_module_permission("assign", active_mod, new_email, username, password):
                        refresh_perms()
            
            st.divider()
            st.markdown("**Usuarios con acceso:**")
            emails_mod = modulos_perms.get(active_mod, [])
            if emails_mod:
                for email in emails_mod:
                    ce, cd = st.columns([4, 1])
                    ce.text(email)
                    if cd.button("🗑️", key=f"del_m_{active_mod}_{email}"):
                        if update_module_permission("remove", active_mod, email, username, password):
                            refresh_perms()
                            st.rerun()
            else:
                st.caption("Cualquier usuario logueado puede entrar.")


@st.fragment
def _fragment_paginas(username: str, password: str):
    """Fragment para gestión de páginas/tabs."""
    st.subheader("Permisos por Página/Tab")
    st.info("💡 Control granular: restringe acceso a pestañas internas de cada módulo.")
    
    estructura = fetch_module_structure()
    permisos = fetch_full_permissions(username, password, st.session_state.perms_version)
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
                            if cd.button("🗑️", key=f"del_p_{key}_{e}"):
                                if update_page_permission("remove", mod_selected, slug, e, username, password):
                                    refresh_perms()
                                    st.rerun()
                    else:
                        st.success("Acceso público (si tiene acceso al módulo)")
                
                with c2:
                    with st.form(key=f"form_p_{key}", clear_on_submit=True):
                        new_email_p = st.text_input("Nuevo acceso:", key=f"in_p_{key}")
                        if st.form_submit_button("Asignar", type="primary"):
                            if update_page_permission("assign", mod_selected, slug, new_email_p, username, password):
                                refresh_perms()


@st.fragment
def _fragment_usuarios():
    """Fragment para consulta de usuarios."""
    st.subheader("Control por Usuario")
    
    # Inicializar debounce state
    if 'permisos_email_debounce' not in st.session_state:
        st.session_state.permisos_email_debounce = ""
    
    q_email = st.text_input(
        "Buscar email:", 
        placeholder="usuario@riofuturo.cl",
        help="🕒 Presiona Enter o haz clic en Consultar para buscar"
    )
    if q_email or st.button("🔍 Consultar", disabled=st.session_state.permisos_consultar_loading):
        try:
            st.session_state.permisos_consultar_loading = True
            data = get_user_permissions(q_email)
            if data:
                if data.get("is_admin"):
                    st.success(f"👑 **{q_email}** es ADMINISTRADOR")
                else:
                    allowed = data.get("allowed", [])
                    st.markdown(f"**Módulos para {q_email}:**")
                    for m in allowed:
                        st.markdown(f"- {MODULE_NAMES.get(m, m)}")
            else:
                st.error("No se encontró el usuario o error en API")
        finally:
            st.session_state.permisos_consultar_loading = False
            st.rerun()


@st.fragment
def _fragment_config(username: str, password: str):
    """Fragment para configuración global."""
    st.subheader("Configuración Global")
    
    # Mantenimiento
    with st.container(border=True):
        st.markdown("### ⚠️ Modo Mantenimiento")
        m_cfg = get_maintenance_config()
        
        c1, c2 = st.columns([1, 3])
        m_enabled = c1.toggle("Activar Banner", value=m_cfg["enabled"], key="cfg_maint_enabled")
        m_msg = c2.text_input("Mensaje", value=m_cfg["message"], key="cfg_maint_msg")
        
        if st.button("Guardar Mantenimiento", type="primary", disabled=st.session_state.permisos_config_loading):
            try:
                st.session_state.permisos_config_loading = True
                if save_maintenance_config(
                    st.session_state.cfg_maint_enabled,
                    st.session_state.cfg_maint_msg,
                    username, password
                ):
                    st.toast("✅ Configuración de mantenimiento guardada")
                else:
                    st.error("Error al guardar mantenimiento")
            finally:
                st.session_state.permisos_config_loading = False
                st.rerun()
    
    # Exclusiones
    st.divider()
    st.markdown("### 🚫 Exclusiones de Valorización")
    
    exclusions_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "shared", "exclusiones.json")
    
    try:
        with open(exclusions_file, 'r') as f:
            exclusiones = json.load(f)
    except:
        exclusiones = {"recepciones": []}
    
    tabL, tabA = st.tabs(["📋 Actuales", "➕ Agregar"])
    
    with tabL:
        if exclusiones["recepciones"]:
            for rid in exclusiones["recepciones"]:
                cl, cd = st.columns([5, 1])
                cl.text(rid)
                if cd.button("🗑️", key=f"excl_del_{rid}"):
                    exclusiones["recepciones"].remove(rid)
                    with open(exclusions_file, 'w') as f:
                        json.dump(exclusiones, f)
                    st.toast(f"Recepción {rid} eliminada de exclusiones")
                    st.rerun()
        else:
            st.caption("No hay exclusiones")
    
    with tabA:, disabled=st.session_state.permisos_buscar_loading):
            try:
                st.session_state.permisos_buscar_loading = True
                resp = httpx.get(f"{API_URL}/api/v1/recepciones-mp/", params={
                    "username": username, "password": password,
                    "fecha_inicio": st.session_state.excl_date_from.isoformat(),
                    "fecha_fin": st.session_state.excl_date_to.isoformat()
                })
                if resp.status_code == 200:
                    st.session_state.r_list_excl = resp.json()
                    st.toast("✅ Recepciones cargadas")
                else:
                    st.error("Error al buscar recepciones")
            except Exception as e:
                st.error(f"Error al buscar recepciones: {str(e)}")
            finally:
                st.session_state.permisos_buscar_loading = False
                st.rerun(_date_to.isoformat()
                })
                if resp.status_code == 200:
                    st.session_state.r_list_excl = resp.json()
            except:
                st.error("Error al buscar recepciones"), disabled=st.session_state.permisos_excluir_loading):
                try:
                    st.session_state.permisos_excluir_loading = True
                    current_excl = exclusiones["recepciones"]
                    for s in st.session_state.excl_multiselect:
                        alb = s.split("|")[0].strip()
                        if alb not in current_excl:
                            current_excl.append(alb)
                    with open(exclusions_file, 'w') as f:
                        json.dump(exclusiones, f)
                    st.toast("✅ Exclusiones guardadas")
                    if "r_list_excl" in st.session_state:
                        del st.session_state.r_list_excl
                finally:
                    st.session_state.permisos_excluir_loading = False
                        if alb not in current_excl:
                        current_excl.append(alb)
                with open(exclusions_file, 'w') as f:
                    json.dump(exclusiones, f)
                st.toast("✅ Exclusiones guardadas")
                if "r_list_excl" in st.session_state:
                    del st.session_state.r_list_excl
                st.rerun()

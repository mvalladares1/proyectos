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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📁 Módulos",
        "📄 Páginas",
        "👤 Usuarios",
        "📦 Override Origen",
        "⚙️ Configuración",
        "🏪 Portal Proveedores",
    ])
    
    with tab1:
        _fragment_modulos(username, password)
    with tab2:
        _fragment_paginas(username, password)
    with tab3:
        _fragment_usuarios()
    with tab4:
        _fragment_override_origen(username, password)
    with tab5:
        _fragment_config(username, password)
    with tab6:
        _fragment_provider_portal(username, password)


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
def _fragment_override_origen(username: str, password: str):
    """Fragment para gestionar overrides de origen de recepciones."""
    st.subheader("📦 Reclasificación de Origen de Recepciones")
    st.info("💡 Corrige recepciones que fueron ingresadas con el origen incorrecto en Odoo (ej: RFP → VILKUN)")
    
    # Cargar overrides desde API
    try:
        resp_overrides = httpx.get(
            f"{API_URL}/api/v1/permissions/overrides/origen/list",
            params={"admin_username": username, "admin_password": password},
            timeout=10.0
        )
        if resp_overrides.status_code == 200:
            overrides_list = resp_overrides.json().get("overrides", [])
        else:
            overrides_list = []
    except:
        overrides_list = []
    
    # También cargar el mapa legacy para mostrar todos
    from backend.services.recepcion_service import _LEGACY_OVERRIDE_ORIGEN_PICKING
    
    tabL, tabA = st.tabs(["📋 Overrides Actuales", "➕ Agregar Override"])
    
    with tabL:
        st.markdown("### Recepciones Reclasificadas")
        
        # Mostrar overrides de DB (editables)
        if overrides_list:
            st.markdown("**🗄️ En Base de Datos (editables):**")
            for ov in overrides_list:
                cl, co, cd = st.columns([4, 2, 1])
                cl.text(ov["picking_name"])
                co.markdown(f"🏢 **{ov['origen']}**")
                if cd.button("🗑️", key=f"ov_del_{ov['picking_name']}"):
                    try:
                        resp = httpx.post(
                            f"{API_URL}/api/v1/permissions/overrides/origen/remove",
                            params={
                                "picking_name": ov["picking_name"],
                                "admin_username": username,
                                "admin_password": password
                            },
                            timeout=10.0
                        )
                        if resp.status_code == 200:
                            st.toast(f"✅ Override eliminado")
                            st.rerun()
                        else:
                            st.error("Error al eliminar")
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        # Mostrar overrides legacy (solo lectura)
        if _LEGACY_OVERRIDE_ORIGEN_PICKING:
            st.markdown("**📜 Legacy (fijos en código):**")
            for albaran, origen in _LEGACY_OVERRIDE_ORIGEN_PICKING.items():
                cl, co, cd = st.columns([4, 2, 1])
                cl.text(albaran)
                co.markdown(f"🏢 **{origen}**")
                cd.caption("📌 Fijo")
        
        total = len(overrides_list) + len(_LEGACY_OVERRIDE_ORIGEN_PICKING)
        st.caption(f"Total: {total} overrides ({len(overrides_list)} en DB, {len(_LEGACY_OVERRIDE_ORIGEN_PICKING)} legacy)")
    
    with tabA:
        st.markdown("### Buscar Recepciones para Reclasificar")
        
        # Inicializar fechas
        if "override_date_from" not in st.session_state:
            st.session_state.override_date_from = datetime.now().date() - timedelta(days=30)
        if "override_date_to" not in st.session_state:
            st.session_state.override_date_to = datetime.now().date()
        
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        with c1:
            st.session_state.override_date_from = st.date_input("Desde", st.session_state.override_date_from, key="ov_from")
        with c2:
            st.session_state.override_date_to = st.date_input("Hasta", st.session_state.override_date_to, key="ov_to")
        with c3:
            origen_filtro = st.selectbox("Origen actual", ["Todos", "RFP", "VILKUN", "SAN JOSE"], key="ov_origen_filtro")
        with c4:
            st.write("")
            if st.button("🔍 Buscar Recepciones", key="btn_buscar_override"):
                try:
                    origen_param = None if origen_filtro == "Todos" else [origen_filtro]
                    
                    resp = httpx.get(f"{API_URL}/api/v1/recepciones-mp/", params={
                        "username": username, "password": password,
                        "fecha_inicio": st.session_state.override_date_from.isoformat(),
                        "fecha_fin": st.session_state.override_date_to.isoformat(),
                        "origen": origen_param[0] if origen_param else None
                    }, timeout=60.0)
                    if resp.status_code == 200:
                        st.session_state.r_list_override = resp.json()
                        st.toast(f"✅ {len(st.session_state.r_list_override)} recepciones cargadas")
                    else:
                        st.error(f"Error {resp.status_code} al buscar recepciones")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                st.rerun()
        
        # Mostrar tabla si hay recepciones
        if "r_list_override" in st.session_state and st.session_state.r_list_override:
            recepciones = st.session_state.r_list_override
            
            # Obtener set de todos los overrides existentes
            existing_overrides = set(ov["picking_name"] for ov in overrides_list)
            existing_overrides.update(_LEGACY_OVERRIDE_ORIGEN_PICKING.keys())
            
            recepciones_sin_override = [r for r in recepciones if r.get('albaran') not in existing_overrides]
            
            st.markdown(f"**{len(recepciones_sin_override)} recepciones disponibles** (excluidas las que ya tienen override)")
            
            if recepciones_sin_override:
                options = [f"{r['albaran']} | {r.get('productor', 'N/A')[:30]} | {r.get('origen', '?')}" for r in recepciones_sin_override]
                selected = st.multiselect("Seleccionar recepciones a reclasificar", options, key="override_multiselect")
                
                if selected:
                    nuevo_origen = st.selectbox("Nuevo origen:", ["VILKUN", "RFP", "SAN JOSE"], key="nuevo_origen_select")
                    
                    st.warning(f"⚠️ Esto cambiará {len(selected)} recepciones a **{nuevo_origen}**")
                    
                    if st.button("✅ Confirmar Reclasificación", type="primary"):
                        success_count = 0
                        for s in selected:
                            alb = s.split("|")[0].strip()
                            try:
                                resp = httpx.post(
                                    f"{API_URL}/api/v1/permissions/overrides/origen/add",
                                    json={
                                        "picking_name": alb,
                                        "origen": nuevo_origen,
                                        "admin_username": username,
                                        "admin_password": password
                                    },
                                    timeout=10.0
                                )
                                if resp.status_code == 200:
                                    success_count += 1
                            except:
                                pass
                        
                        st.toast(f"✅ {success_count} overrides guardados en la base de datos")
                        if "r_list_override" in st.session_state:
                            del st.session_state.r_list_override
                        st.rerun()
            else:
                st.info("👍 Todas las recepciones en este rango ya tienen su origen correcto o ya están en overrides")


@st.fragment
def _fragment_config(username: str, password: str):
    """Fragment para configuración global."""
    st.subheader("Configuración Global")
    
    # Administradores
    with st.container(border=True):
        st.markdown("### 👑 Super Usuarios (Administradores)")
        st.caption("Los administradores tienen acceso total a todos los módulos y páginas")
        
        try:
            resp_admins = httpx.get(f"{API_URL}/api/v1/permissions/admins", timeout=10.0)
            if resp_admins.status_code == 200:
                admins_list = resp_admins.json().get("admins", [])
            else:
                admins_list = []
        except:
            admins_list = []
        
        col_list, col_add = st.columns([2, 1])
        
        with col_list:
            st.markdown("**Administradores actuales:**")
            if admins_list:
                for admin_email in admins_list:
                    ce, cd = st.columns([4, 1])
                    ce.text(admin_email)
                    if cd.button("🗑️", key=f"admin_del_{admin_email}"):
                        try:
                            resp = httpx.post(
                                f"{API_URL}/api/v1/permissions/admins/remove",
                                params={
                                    "email": admin_email,
                                    "admin_username": username,
                                    "admin_password": password
                                },
                                timeout=10.0
                            )
                            if resp.status_code == 200:
                                st.toast(f"✅ {admin_email} removido como admin")
                                st.rerun()
                            else:
                                st.error("Error al remover admin")
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.caption("No hay administradores configurados")
        
        with col_add:
            st.markdown("**Agregar Admin:**")
            with st.form(key="form_add_admin", clear_on_submit=True):
                new_admin_email = st.text_input("Email:", placeholder="admin@riofuturo.cl")
                if st.form_submit_button("➕ Agregar", use_container_width=True):
                    if new_admin_email:
                        try:
                            resp = httpx.post(
                                f"{API_URL}/api/v1/permissions/admins/assign",
                                params={
                                    "email": new_admin_email,
                                    "admin_username": username,
                                    "admin_password": password
                                },
                                timeout=10.0
                            )
                            if resp.status_code == 200:
                                st.toast(f"✅ {new_admin_email} agregado como admin")
                                st.rerun()
                            else:
                                st.error("Error al agregar admin")
                        except Exception as e:
                            st.error(f"Error: {e}")
    
    st.divider()
    
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
    
    # Cargar exclusiones desde API
    try:
        resp_excl = httpx.get(
            f"{API_URL}/api/v1/permissions/exclusiones/list",
            params={"admin_username": username, "admin_password": password},
            timeout=10.0
        )
        if resp_excl.status_code == 200:
            exclusiones_list = resp_excl.json().get("exclusiones", [])
        else:
            exclusiones_list = []
    except:
        exclusiones_list = []
    
    tabL, tabA = st.tabs(["📋 Actuales", "➕ Agregar"])
    
    with tabL:
        if exclusiones_list:
            for excl in exclusiones_list:
                cl, cm, cd = st.columns([4, 2, 1])
                cl.text(excl["albaran"])
                cm.caption(excl.get("motivo", ""))
                if cd.button("🗑️", key=f"excl_del_{excl['albaran']}"):
                    try:
                        resp = httpx.post(
                            f"{API_URL}/api/v1/permissions/exclusiones/remove",
                            params={
                                "albaran": excl["albaran"],
                                "admin_username": username,
                                "admin_password": password
                            },
                            timeout=10.0
                        )
                        if resp.status_code == 200:
                            st.toast(f"✅ {excl['albaran']} eliminada de exclusiones")
                            st.rerun()
                        else:
                            st.error("Error al eliminar exclusión")
                    except Exception as e:
                        st.error(f"Error: {e}")
            st.caption(f"Total: {len(exclusiones_list)} exclusiones")
        else:
            st.caption("No hay exclusiones")
    
    with tabA:
        st.markdown("#### Buscar Recepciones")
        
        # Inicializar fechas
        if "excl_date_from" not in st.session_state:
            st.session_state.excl_date_from = datetime.now().date() - timedelta(days=7)
        if "excl_date_to" not in st.session_state:
            st.session_state.excl_date_to = datetime.now().date()
        
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            st.session_state.excl_date_from = st.date_input("Desde", st.session_state.excl_date_from)
        with c2:
            st.session_state.excl_date_to = st.date_input("Hasta", st.session_state.excl_date_to)
        with c3:
            st.write("")
            if st.button("🔍 Buscar Recepciones", disabled=st.session_state.permisos_buscar_loading):
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
                    st.rerun()
        
        # Mostrar multiselect si hay recepciones
        if "r_list_excl" in st.session_state and st.session_state.r_list_excl:
            options = [f"{r['name']} | {r.get('partner_name', 'N/A')}" for r in st.session_state.r_list_excl]
            selected = st.multiselect("Seleccionar recepciones a excluir", options, key="excl_multiselect")
            
            if selected:
                motivo = st.text_input("Motivo (opcional):", placeholder="Ej: Recepción duplicada", key="excl_motivo")
                
                if st.button("✅ Confirmar Exclusión", type="primary", disabled=st.session_state.permisos_excluir_loading):
                    try:
                        st.session_state.permisos_excluir_loading = True
                        success_count = 0
                        for s in selected:
                            alb = s.split("|")[0].strip()
                            try:
                                resp = httpx.post(
                                    f"{API_URL}/api/v1/permissions/exclusiones/add",
                                    json={
                                        "albaran": alb,
                                        "motivo": motivo or "Agregado desde panel",
                                        "admin_username": username,
                                        "admin_password": password
                                    },
                                    timeout=10.0
                                )
                                if resp.status_code == 200:
                                    success_count += 1
                            except:
                                pass
                        
                        st.toast(f"✅ {success_count} exclusiones guardadas")
                        if "r_list_excl" in st.session_state:
                            del st.session_state.r_list_excl
                    finally:
                        st.session_state.permisos_excluir_loading = False
                        st.rerun()

    # Override de Precio para Valorización
    st.divider()
    st.markdown("### 💰 Override de Precio Unitario")
    st.caption("Incluir recepciones en valorización con precio personalizado ($/kg)")
    
    # Cargar overrides de precio desde API
    try:
        resp_precio = httpx.get(
            f"{API_URL}/api/v1/permissions/precio-override/list",
            params={"admin_username": username, "admin_password": password},
            timeout=10.0
        )
        if resp_precio.status_code == 200:
            precio_override_list = resp_precio.json().get("precio_override", [])
        else:
            precio_override_list = []
    except:
        precio_override_list = []
    
    tabPO_L, tabPO_A = st.tabs(["📋 Actuales", "➕ Agregar"])
    
    with tabPO_L:
        if precio_override_list:
            for po in precio_override_list:
                cl, cp, cm, cd = st.columns([3, 1.5, 2, 0.5])
                cl.text(po["albaran"])
                cp.text(f"${po['precio_unitario']:,.0f}/kg")
                cm.caption(po.get("motivo", ""))
                if cd.button("🗑️", key=f"po_del_{po['albaran']}"):
                    try:
                        resp = httpx.post(
                            f"{API_URL}/api/v1/permissions/precio-override/remove",
                            params={
                                "albaran": po["albaran"],
                                "admin_username": username,
                                "admin_password": password
                            },
                            timeout=10.0
                        )
                        if resp.status_code == 200:
                            st.toast(f"✅ Override de {po['albaran']} eliminado")
                            st.rerun()
                        else:
                            st.error("Error al eliminar override")
                    except Exception as e:
                        st.error(f"Error: {e}")
            st.caption(f"Total: {len(precio_override_list)} overrides")
        else:
            st.caption("No hay overrides de precio configurados")
    
    with tabPO_A:
        st.markdown("#### Buscar Recepciones Excluidas")
        st.info("💡 Busca entre las recepciones **excluidas** para moverlas a precio override")
        
        # Mostrar exclusiones actuales para mover a precio override
        if exclusiones_list:
            po_options = [e["albaran"] for e in exclusiones_list]
            po_selected = st.selectbox("Seleccionar recepción excluida:", options=[""] + po_options, key="po_select_albaran")
            
            if po_selected:
                c1, c2 = st.columns([1, 2])
                with c1:
                    precio_nuevo = st.number_input("Precio $/kg:", min_value=0.0, value=500.0, step=50.0, key="po_precio")
                with c2:
                    po_motivo = st.text_input("Motivo (opcional):", placeholder="Ej: Precio negociado", key="po_motivo")
                
                if st.button("✅ Agregar Override y Remover de Exclusiones", type="primary"):
                    try:
                        # 1. Agregar override de precio
                        resp_add = httpx.post(
                            f"{API_URL}/api/v1/permissions/precio-override/add",
                            json={
                                "albaran": po_selected,
                                "precio_unitario": precio_nuevo,
                                "motivo": po_motivo or "Agregado desde panel",
                                "admin_username": username,
                                "admin_password": password
                            },
                            timeout=10.0
                        )
                        if resp_add.status_code == 200:
                            # 2. Remover de exclusiones
                            resp_rem = httpx.post(
                                f"{API_URL}/api/v1/permissions/exclusiones/remove",
                                params={
                                    "albaran": po_selected,
                                    "admin_username": username,
                                    "admin_password": password
                                },
                                timeout=10.0
                            )
                            st.toast(f"✅ Override para {po_selected} guardado a ${precio_nuevo:,.0f}/kg")
                            st.rerun()
                        else:
                            st.error("Error al agregar override")
                    except Exception as e:
                        st.error(f"Error: {e}")


        else:
            st.caption("No hay exclusiones disponibles para convertir en override")
        
        st.divider()
        st.markdown("#### Agregar Override Manual")
        with st.form(key="form_add_precio_override", clear_on_submit=True):
            albaran_manual = st.text_input("Albarán:", placeholder="RF/RFP/IN/00123")
            cm1, cm2 = st.columns(2)
            with cm1:
                precio_manual = st.number_input("Precio $/kg:", min_value=0.0, value=500.0, step=50.0)
            with cm2:
                motivo_manual = st.text_input("Motivo:", placeholder="Ej: Ajuste de precio")
            
            if st.form_submit_button("➕ Agregar Override", use_container_width=True):
                if albaran_manual:
                    try:
                        resp = httpx.post(
                            f"{API_URL}/api/v1/permissions/precio-override/add",
                            json={
                                "albaran": albaran_manual,
                                "precio_unitario": precio_manual,
                                "motivo": motivo_manual or "Agregado manualmente",
                                "admin_username": username,
                                "admin_password": password
                            },
                            timeout=10.0
                        )
                        if resp.status_code == 200:
                            st.toast(f"✅ Override para {albaran_manual} guardado")
                            st.rerun()
                        else:
                            st.error("Error al agregar override")
                    except Exception as e:
                        st.error(f"Error: {e}")


@st.fragment
def _fragment_provider_portal(username: str, password: str):
    """Fragment para administración del portal de proveedores."""
    st.subheader("Portal de Proveedores")
    st.caption("Sincroniza proveedores MP y configura accesos del portal sin usar scripts locales")

    col_sync, col_info = st.columns([1, 2])
    with col_sync:
        if st.button("🔄 Sincronizar proveedores MP", use_container_width=True, key="pp_sync"):
            try:
                resp = httpx.post(
                    f"{API_URL}/api/v1/permissions/provider-portal/sync",
                    params={"admin_username": username, "admin_password": password},
                    timeout=120.0,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    st.success(
                        f"Sincronización completada: {result.get('created', 0)} creados, "
                        f"{result.get('updated', 0)} actualizados, {result.get('total', 0)} total"
                    )
                else:
                    st.error(resp.text)
            except Exception as e:
                st.error(f"Error sincronizando: {e}")
    with col_info:
        st.info("La sincronización toma los proveedores con recepciones MP hechas y los deja disponibles para activar en el portal.")

    with st.form("provider_portal_set_password"):
        st.markdown("### Activar o resetear clave")
        c1, c2, c3 = st.columns([1.2, 1, 0.8])
        with c1:
            rut = st.text_input("RUT proveedor", placeholder="12.345.678-9")
        with c2:
            portal_password = st.text_input("Nueva clave", type="password")
        with c3:
            activate = st.checkbox("Activar usuario", value=True)
        submitted = st.form_submit_button("Guardar clave", use_container_width=True, type="primary")
        if submitted:
            try:
                resp = httpx.post(
                    f"{API_URL}/api/v1/permissions/provider-portal/set-password",
                    json={
                        "rut": rut,
                        "password": portal_password,
                        "activate": activate,
                        "admin_username": username,
                        "admin_password": password,
                    },
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.success(f"Clave actualizada para {data.get('display_name', rut)}")
                else:
                    st.error(resp.text)
            except Exception as e:
                st.error(f"Error guardando clave: {e}")

    st.markdown("### Usuarios portal")
    filtro = st.text_input("Buscar por nombre, RUT o email", key="provider_portal_filter")
    try:
        resp = httpx.get(
            f"{API_URL}/api/v1/permissions/provider-portal/users",
            params={"admin_username": username, "admin_password": password},
            timeout=60.0,
        )
        if resp.status_code == 200:
            users = resp.json().get("users", [])
        else:
            users = []
            st.error(resp.text)
    except Exception as e:
        users = []
        st.error(f"Error cargando usuarios del portal: {e}")

    if filtro:
        filtro_lower = filtro.strip().lower()
        users = [
            user for user in users
            if filtro_lower in (user.get("display_name", "").lower())
            or filtro_lower in (user.get("rut", "").lower())
            or filtro_lower in (user.get("email", "").lower())
        ]

    if users:
        st.dataframe(
            users,
            use_container_width=True,
            hide_index=True,
            column_config={
                "partner_id": st.column_config.NumberColumn("Partner ID"),
                "display_name": st.column_config.TextColumn("Proveedor", width="large"),
                "rut": st.column_config.TextColumn("RUT"),
                "email": st.column_config.TextColumn("Email", width="medium"),
                "phone": st.column_config.TextColumn("Teléfono"),
                "city": st.column_config.TextColumn("Ciudad"),
                "active": st.column_config.CheckboxColumn("Activo"),
                "has_password": st.column_config.CheckboxColumn("Clave"),
                "created_at": st.column_config.TextColumn("Creado"),
                "updated_at": st.column_config.TextColumn("Actualizado"),
            },
        )
    else:
        st.info("No hay usuarios portal para mostrar.")

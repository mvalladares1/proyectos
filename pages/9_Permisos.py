"""
Panel de administración: gestiona qué usuarios pueden acceder a cada dashboard del sistema.
"""
import os
from typing import Dict, List

import httpx
import pandas as pd
import streamlit as st

from shared.auth import es_admin, proteger_pagina

st.set_page_config(
    page_title="Permisos",
    page_icon="⚙️",
    layout="wide"
)

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

if not proteger_pagina():
    st.stop()

if not es_admin():
    st.error("Solo administradores pueden acceder a este panel.")
    st.stop()

username = st.session_state.get("username")
password = st.session_state.get("password")

if not username or not password:
    st.warning("Inicia sesión con credenciales válidas para administrar los permisos.")
    st.stop()


def fetch_permissions() -> Dict[str, List[str]]:
    resp = httpx.get(
        f"{API_URL}/api/v1/permissions/all",
        params={"admin_username": username, "admin_password": password},
        timeout=10.0
    )
    resp.raise_for_status()
    return resp.json().get("dashboards", {})


def update_permission(action: str, dashboard: str, email: str) -> Dict[str, List[str]]:
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
    return resp.json().get("dashboards", {})


def render_table(perms: Dict[str, List[str]]) -> None:
    if not perms:
        st.info("Aún no hay dashboards restringidos.")
        return
    rows = []
    for slug, emails in perms.items():
        rows.append({"Dashboard": slug, "Correos": ", ".join(emails) if emails else "-"})
    st.table(pd.DataFrame(rows))


st.title("🛠️ Panel de Permisos")
st.markdown("Control centralizado de quién ve cada dashboard.")

try:
    permisos = fetch_permissions()
except httpx.HTTPError as exc:
    st.error(f"No se pudo cargar permisos: {exc}")
    st.stop()

st.subheader("Permisos actuales")
render_table(permisos)

dashboards = sorted(permisos.keys())

with st.expander("Asignar permiso"):
    with st.form("assign_form"):
        slug_input = st.text_input(
            "Slug del dashboard",
            value=dashboards[0] if dashboards else "",
            placeholder="ej: estado_resultado",
            help="Usa el slug en minúsculas que identifica a cada página."
        )
        correo = st.text_input("Correo autorizado")
        if dashboards:
            st.caption(f"Dashboards registrados: {', '.join(dashboards)}")
        submitted = st.form_submit_button("Asignar")
        if submitted:
            if not slug_input or not correo:
                st.warning("Ingresa slug y correo para continuar.")
            else:
                try:
                    update_permission("assign", slug_input, correo)
                    st.success(f"{correo} ahora puede ver {slug_input}.")
                    st.rerun()
                except httpx.HTTPError as exc:
                    st.error(f"Error al asignar permiso: {exc}")

with st.expander("Revocar permiso"):
    with st.form("remove_form"):
        slug_input = st.text_input(
            "Slug del dashboard",
            value=dashboards[0] if dashboards else "",
            placeholder="ej: estado_resultado",
            key="remove_slug",
            help="Escribe el mismo slug que se usó para asignar el permiso."
        )
        correo = st.text_input("Correo a revocar", key="remove_email")
        submitted = st.form_submit_button("Revocar")
        if submitted:
            if not slug_input or not correo:
                st.warning("Ingresa slug y correo para continuar.")
            else:
                try:
                    update_permission("remove", slug_input, correo)
                    st.success(f"Se revocó {correo} de {slug_input}.")
                    st.rerun()
                except httpx.HTTPError as exc:
                    st.error(f"Error al revocar permiso: {exc}")

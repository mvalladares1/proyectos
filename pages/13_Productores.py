"""Módulo PRODUCTORES dentro del dashboard principal."""
import os
from datetime import date, timedelta
from typing import Any, Dict

import httpx
import pandas as pd
import streamlit as st

from shared.auth import proteger_modulo


ENV = os.getenv("ENV", "production")
if ENV == "development":
    API_URL = os.getenv("API_URL", "http://127.0.0.1:8002")
else:
    API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


st.set_page_config(
    layout="wide",
    page_title="Productores",
    page_icon="🌱",
    initial_sidebar_state="expanded",
)


if not proteger_modulo("productores"):
    st.stop()


def _provider_headers() -> Dict[str, str]:
    token = st.session_state.get("prod_provider_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _provider_get(path: str, **params) -> Dict[str, Any]:
    response = httpx.get(
        f"{API_URL}{path}",
        params=params,
        headers=_provider_headers(),
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()


def _provider_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = httpx.post(
        f"{API_URL}{path}",
        json=payload,
        headers=_provider_headers(),
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()


def _provider_dev_auto_login(rut: str = "", partner_id: int = 0) -> None:
    internal_session_token = st.session_state.get("session_token", "")
    params: Dict[str, Any] = {"internal_session_token": internal_session_token}
    if partner_id:
        params["partner_id"] = partner_id
    elif rut:
        params["rut"] = rut
    response = httpx.post(
        f"{API_URL}/api/v1/provider-portal/login/dev-auto",
        params=params,
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()
    st.session_state["prod_provider_token"] = data["token"]


@st.cache_data(ttl=300)
def _load_dev_providers() -> list:
    try:
        r = httpx.get(f"{API_URL}/api/v1/provider-portal/dev-providers", timeout=30.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def _provider_download(attachment_id: int) -> tuple[bytes, str, str]:
    token = st.session_state.get("prod_provider_token")
    response = httpx.get(
        f"{API_URL}/api/v1/provider-portal/attachments/{attachment_id}",
        params={"token": token},
        timeout=120.0,
    )
    response.raise_for_status()
    disposition = response.headers.get("Content-Disposition", "")
    filename = disposition.split("filename=", 1)[1] if "filename=" in disposition else f"attachment_{attachment_id}"
    return response.content, filename.strip('"'), response.headers.get("Content-Type", "application/octet-stream")


def _provider_logout() -> None:
    token = st.session_state.get("prod_provider_token")
    if token:
        try:
            httpx.post(f"{API_URL}/api/v1/provider-portal/logout", params={"token": token}, timeout=10.0)
        except Exception:
            pass
    st.session_state.pop("prod_provider_token", None)
    st.rerun()


def _render_provider_login() -> None:
    st.markdown("### 🔐 Acceso Proveedor")
    with st.form("prod_provider_login_form"):
        rut = st.text_input("RUT", placeholder="12.345.678-9")
        password = st.text_input("Clave", type="password")
        submitted = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
    if submitted:
        try:
            data = _provider_post(
                "/api/v1/provider-portal/login",
                {"rut": rut, "password": password},
            )
            st.session_state["prod_provider_token"] = data["token"]
            st.success("Ingreso correcto")
            st.rerun()
        except Exception as exc:
            st.error(f"No se pudo iniciar sesión: {exc}")


def _render_summary(summary: Dict[str, Any]) -> None:
    cols = st.columns(6)
    cards = [
        ("Recepciones", f"{summary.get('recepciones', 0):,}"),
        ("KG Recepcionados", f"{summary.get('kg_recepcionados', 0):,.0f}"),
        ("Guías", f"{summary.get('guias', 0):,}"),
        ("Fotos", f"{summary.get('fotos', 0):,}"),
        ("Proformas", f"{summary.get('proformas', 0):,}"),
        ("Facturas", f"{summary.get('facturas', 0):,}"),
    ]
    for col, (label, value) in zip(cols, cards):
        with col:
            st.metric(label, value)


def _render_recepciones_table(recepciones):
    rows = []
    for item in recepciones:
        rows.append(
            {
                "Fecha": item.get("fecha", ""),
                "Guía": item.get("guia_despacho", ""),
                "Albarán": item.get("albaran", ""),
                "Origen": item.get("origen", ""),
                "OC": item.get("oc_asociada", ""),
                "KG": round(item.get("kg_recepcionados", 0) or 0, 2),
                "Calidad Final": item.get("calific_final", ""),
                "Estado QC": item.get("quality_state", ""),
                "IQF %": item.get("total_iqf", 0),
                "Block %": item.get("total_block", 0),
                "Fotos": item.get("cantidad_fotos", 0),
                "Docs": item.get("cantidad_documentos", 0),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_documentos(fin_docs):
    for section_name, docs in (("Proformas", fin_docs.get("proformas", [])), ("Facturas", fin_docs.get("facturas", []))):
        st.markdown(f"#### {section_name}")
        if not docs:
            st.caption(f"Sin {section_name.lower()} disponibles")
            continue
        rows = []
        for doc in docs:
            rows.append(
                {
                    "Documento": doc.get("name", ""),
                    "Fecha": doc.get("invoice_date", ""),
                    "Referencia": doc.get("ref", ""),
                    "OC/Origen": doc.get("invoice_origin", ""),
                    "Monto": f"{doc.get('amount_total', 0):,.0f} {doc.get('currency', 'CLP')}",
                    "Estado": doc.get("state", ""),
                    "Pago": doc.get("payment_state", ""),
                    "Adjuntos": len(doc.get("attachments", [])),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        for doc in docs:
            attachments = doc.get("attachments", [])
            if not attachments:
                continue
            with st.expander(f"Adjuntos {doc.get('name', '')}"):
                for attachment in attachments:
                    try:
                        content, filename, mime = _provider_download(attachment["id"])
                        st.download_button(
                            label=f"Descargar {filename}",
                            data=content,
                            file_name=filename,
                            mime=mime,
                            key=f"prod_doc_{attachment['id']}",
                        )
                    except Exception as exc:
                        st.warning(f"No se pudo descargar {attachment.get('name', 'adjunto')}: {exc}")


st.markdown("## 🌱 PRODUCTORES")
st.caption("Portal integrado para consulta de recepciones, calidad, fotos, proformas y facturas por proveedor")

if "prod_provider_token" not in st.session_state:
    if ENV == "development":
        try:
            _provider_dev_auto_login(st.session_state.get("prod_selected_rut", ""))
            st.rerun()
        except Exception as exc:
            st.error(f"No se pudo iniciar sesión automática en dev: {exc}")
            st.stop()
    _render_provider_login()
    st.stop()

try:
    me = _provider_get("/api/v1/provider-portal/me")
except Exception:
    st.warning("La sesión de proveedor expiró o no es válida")
    _provider_logout()
    st.stop()

partner = me.get("partner", {})
st.sidebar.markdown(f"### {partner.get('name', 'Proveedor')}")
st.sidebar.caption(partner.get("rut", ""))

if ENV == "development":
    st.sidebar.markdown("---")
    st.sidebar.caption("🔧 Selector dev")
    providers = _load_dev_providers()
    if providers:
        options_map = {f"{p['name']} ({p['rut']})": p for p in providers}
        current_pid = st.session_state.get("prod_selected_partner_id", 0)
        current_label = next(
            (k for k, v in options_map.items() if v.get("partner_id") == current_pid),
            None,
        )
        labels = list(options_map.keys())
        default_idx = labels.index(current_label) if current_label in labels else 0
        selected_label = st.sidebar.selectbox(
            "Proveedor",
            labels,
            index=default_idx,
            key="prod_dev_selector",
        )
        if st.sidebar.button("Cambiar proveedor", use_container_width=True):
            p = options_map[selected_label]
            try:
                st.session_state["prod_selected_partner_id"] = p["partner_id"]
                _provider_dev_auto_login(partner_id=int(p["partner_id"]))
                st.rerun()
            except Exception as exc:
                st.sidebar.error(f"Error: {exc}")
    else:
        dev_rut = st.sidebar.text_input(
            "Filtrar por RUT (dev)",
            value=st.session_state.get("prod_selected_rut", ""),
        )
        if st.sidebar.button("Aplicar RUT", use_container_width=True):
            try:
                st.session_state["prod_selected_rut"] = dev_rut.strip()
                _provider_dev_auto_login(rut=dev_rut.strip())
                st.rerun()
            except Exception as exc:
                st.sidebar.error(f"No se pudo aplicar RUT: {exc}")

if st.sidebar.button("Cerrar sesión proveedor", use_container_width=True):
    _provider_logout()

today = date.today()
start = st.date_input("Desde", value=today - timedelta(days=30), key="prod_fecha_inicio")
end = st.date_input("Hasta", value=today, key="prod_fecha_fin")
if start > end:
    st.error("La fecha inicio no puede ser mayor que la fecha fin")
    st.stop()

try:
    dashboard = _provider_get(
        "/api/v1/provider-portal/dashboard",
        fecha_inicio=start.isoformat(),
        fecha_fin=end.isoformat(),
    )
except Exception as exc:
    st.error(f"No se pudo cargar la data de productores: {exc}")
    st.stop()

_render_summary(dashboard.get("summary", {}))
tab1, tab2, tab3 = st.tabs(["Recepciones", "Calidad/Fotos", "Proformas y Facturas"])

with tab1:
    recepciones = dashboard.get("recepciones", [])
    if recepciones:
        _render_recepciones_table(recepciones)
    else:
        st.info("Sin recepciones para el período seleccionado")

with tab2:
    recepciones = dashboard.get("recepciones", [])
    if not recepciones:
        st.info("Sin recepciones con calidad para el período")
    else:
        options = {
            f"{item.get('fecha', '')} · Guía {item.get('guia_despacho', 'S/G')} · {item.get('kg_recepcionados', 0):,.0f} kg": item
            for item in recepciones
        }
        selected = st.selectbox("Selecciona una recepción", list(options.keys()))
        item = options[selected]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Calidad Final", item.get("calific_final", "-"))
        c2.metric("IQF %", f"{item.get('total_iqf', 0):.1f}")
        c3.metric("Block %", f"{item.get('total_block', 0):.1f}")
        c4.metric("Gramos Muestra", f"{item.get('gramos_muestra', 0):,.0f}")

        defectos = pd.DataFrame(
            [
                ("Daño Mecánico", item.get("dano_mecanico", 0)),
                ("Hongos", item.get("hongos", 0)),
                ("Inmadura", item.get("inmadura", 0)),
                ("Sobremadura", item.get("sobremadura", 0)),
                ("Daño Insecto", item.get("dano_insecto", 0)),
                ("Fruta Verde", item.get("fruta_verde", 0)),
                ("Deshidratado", item.get("deshidratado", 0)),
                ("Herida Partida", item.get("herida_partida", 0)),
                ("Crumble", item.get("crumble", 0)),
            ],
            columns=["Defecto", "Valor"],
        )
        st.dataframe(defectos, use_container_width=True, hide_index=True)

        fotos = item.get("fotos", [])
        st.markdown("#### Fotos")
        if not fotos:
            st.caption("Sin fotos para esta recepción")
        else:
            cols = st.columns(3)
            for idx, foto in enumerate(fotos[:12]):
                with cols[idx % 3]:
                    try:
                        content, filename, _ = _provider_download(foto["id"])
                        st.image(content, caption=filename, use_container_width=True)
                    except Exception as exc:
                        st.warning(f"No se pudo cargar foto: {exc}")

with tab3:
    _render_documentos(dashboard)

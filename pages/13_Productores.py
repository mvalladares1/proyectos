"""Módulo PRODUCTORES dentro del dashboard principal."""
import os
from datetime import date, timedelta
from typing import Any, Dict, List

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


st.markdown(
    """
    <style>
    .prod-hero {
        padding: 0.9rem 1.1rem;
        border: 1px solid rgba(120, 130, 160, 0.25);
        border-radius: 12px;
        background: linear-gradient(135deg, rgba(28, 31, 46, 0.8), rgba(18, 26, 38, 0.9));
        margin-bottom: 0.8rem;
    }
    .prod-hero h3 {
        margin: 0;
        font-size: 1.25rem;
        letter-spacing: 0.2px;
    }
    .prod-hero p {
        margin: 0.35rem 0 0 0;
        opacity: 0.9;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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


def _provider_download_qc_photo(qc_id: int, field_name: str) -> tuple[bytes, str, str]:
    token = st.session_state.get("prod_provider_token")
    response = httpx.get(
        f"{API_URL}/api/v1/provider-portal/qc-photo/{qc_id}/{field_name}",
        params={"token": token},
        timeout=120.0,
    )
    response.raise_for_status()
    disposition = response.headers.get("Content-Disposition", "")
    filename = disposition.split("filename=", 1)[1] if "filename=" in disposition else f"qc_{qc_id}_{field_name}.jpg"
    return response.content, filename.strip('"'), response.headers.get("Content-Type", "image/jpeg")


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
        ("KG Netos", f"{summary.get('kg_recepcionados', 0):,.0f}"),
        ("Guías", f"{summary.get('guias', 0):,}"),
        ("Fotos QC", f"{summary.get('fotos', 0):,}"),
        ("Proformas", f"{summary.get('proformas', 0):,}"),
        ("Facturas", f"{summary.get('facturas', 0):,}"),
    ]
    for col, (label, value) in zip(cols, cards):
        with col:
            st.metric(label, value)


def _render_recepciones_table(recepciones: List[Dict[str, Any]]) -> None:
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
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by=["Fecha", "Albarán"], ascending=[False, False])
    st.dataframe(df, use_container_width=True, hide_index=True)


def _filter_recepciones(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return []
    c1, c2 = st.columns([2, 1])
    with c1:
        q = st.text_input("Buscar por guía, albarán u OC", value="", key="prod_busqueda_recepcion")
    with c2:
        estado = st.selectbox("Estado QC", ["Todos", "pass", "fail", "none"], key="prod_estado_qc")

    q_norm = q.strip().upper()
    result = []
    for item in rows:
        haystack = " ".join(
            [
                str(item.get("guia_despacho", "")),
                str(item.get("albaran", "")),
                str(item.get("oc_asociada", "")),
            ]
        ).upper()
        if q_norm and q_norm not in haystack:
            continue
        if estado != "Todos" and str(item.get("quality_state", "")) != estado:
            continue
        result.append(item)
    return result


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
            links = doc.get("linked_recepciones", [])
            if links:
                with st.expander(f"Recepciones vinculadas {doc.get('name', '')} ({len(links)})"):
                    st.dataframe(pd.DataFrame(links), use_container_width=True, hide_index=True)
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


st.markdown(
        """
        <div class='prod-hero'>
            <h3>🌱 PRODUCTORES</h3>
            <p>Vista integrada por proveedor: recepciones, control de calidad, fotos y documentos comerciales vinculados.</p>
        </div>
        """,
        unsafe_allow_html=True,
)

if "prod_provider_token" not in st.session_state:
    if ENV == "development":
        try:
            initial_partner_id = int(st.session_state.get("prod_selected_partner_id", 0) or 0)
            if initial_partner_id:
                _provider_dev_auto_login(partner_id=initial_partner_id)
            else:
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
        current_pid = int(st.session_state.get("prod_selected_partner_id", 0) or 0)
        if not current_pid:
            current_pid = int(partner.get("partner_id", 0) or 0)
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
        selected_partner_id = int(options_map[selected_label]["partner_id"])
        last_applied_pid = int(st.session_state.get("prod_last_applied_partner_id", 0) or 0)
        if selected_partner_id != last_applied_pid:
            try:
                st.session_state["prod_selected_partner_id"] = selected_partner_id
                st.session_state["prod_last_applied_partner_id"] = selected_partner_id
                _provider_dev_auto_login(partner_id=selected_partner_id)
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
c_from, c_to = st.columns(2)
with c_from:
    start = st.date_input("Desde", value=today - timedelta(days=30), key="prod_fecha_inicio")
with c_to:
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
    recepciones_filtradas = _filter_recepciones(recepciones)
    st.caption(f"{len(recepciones_filtradas)} recepciones en pantalla")
    if recepciones_filtradas:
        _render_recepciones_table(recepciones_filtradas)
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

        c_left, c_right = st.columns([1.2, 1])
        with c_left:
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

            lineas = item.get("lineas_analisis", [])
            st.markdown("#### Control de Calidad (líneas)")
            if lineas:
                st.dataframe(pd.DataFrame(lineas), use_container_width=True, hide_index=True)
            else:
                st.caption("Sin líneas detalladas de control de calidad")

        with c_right:
            fotos = item.get("fotos", [])
            st.markdown("#### Fotos")
            if not fotos:
                st.caption("Sin fotos para esta recepción")
            else:
                cols = st.columns(2)
                for idx, foto in enumerate(fotos[:12]):
                    with cols[idx % 2]:
                        try:
                            if foto.get("source") == "quality_check_binary":
                                content, filename, _ = _provider_download_qc_photo(int(foto["qc_id"]), str(foto["field"]))
                            else:
                                content, filename, _ = _provider_download(foto["id"])
                            st.image(content, caption=filename, use_container_width=True)
                        except Exception as exc:
                            st.warning(f"No se pudo cargar foto: {exc}")

with tab3:
    _render_documentos(dashboard)

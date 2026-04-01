"""Portal de proveedores Rio Futuro."""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd
import streamlit as st


ENV = os.getenv("ENV", "production")
if ENV == "development":
    API_URL = os.getenv("API_URL", "http://127.0.0.1:8002")
else:
    API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


st.set_page_config(
    page_title="Portal de Proveedores",
    page_icon="📦",
    layout="wide",
)


def _api_headers() -> Dict[str, str]:
    token = st.session_state.get("provider_portal_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _api_get(path: str, **params) -> Dict[str, Any]:
    response = httpx.get(f"{API_URL}{path}", params=params, headers=_api_headers(), timeout=120.0)
    response.raise_for_status()
    return response.json()


def _api_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = httpx.post(f"{API_URL}{path}", json=payload, headers=_api_headers(), timeout=30.0)
    response.raise_for_status()
    return response.json()


def _download_attachment(attachment_id: int) -> tuple[bytes, str, str]:
    token = st.session_state.get("provider_portal_token")
    response = httpx.get(
        f"{API_URL}/api/v1/provider-portal/attachments/{attachment_id}",
        params={"token": token},
        timeout=120.0,
    )
    response.raise_for_status()
    disposition = response.headers.get("Content-Disposition", "")
    filename = disposition.split("filename=", 1)[1] if "filename=" in disposition else f"attachment_{attachment_id}"
    return response.content, filename.strip('"'), response.headers.get("Content-Type", "application/octet-stream")


def _logout() -> None:
    token = st.session_state.get("provider_portal_token")
    if token:
        try:
            httpx.post(
                f"{API_URL}/api/v1/provider-portal/logout",
                params={"token": token},
                timeout=10.0,
            )
        except Exception:
            pass
    st.session_state.clear()
    st.rerun()


def _render_login() -> None:
    st.markdown(
        """
        <div style="background:linear-gradient(135deg,#0d3b66,#1d5f91);padding:28px;border-radius:18px;margin-bottom:24px;">
            <h1 style="margin:0;color:#fff;">Portal de Proveedores</h1>
            <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);font-size:16px;">
                Consulta tus recepciones, calidad, fotos y documentos desde Odoo.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("### Ingreso Proveedor")
        with st.form("provider_login_form"):
            rut = st.text_input("RUT")
            password = st.text_input("Clave", type="password")
            submitted = st.form_submit_button("Ingresar", use_container_width=True, type="primary")
        if submitted:
            try:
                result = _api_post(
                    "/api/v1/provider-portal/login",
                    {"rut": rut, "password": password},
                )
                st.session_state["provider_portal_token"] = result["token"]
                st.rerun()
            except Exception as exc:
                st.error(f"No se pudo iniciar sesion: {exc}")


def _render_summary(summary: Dict[str, Any]) -> None:
    cols = st.columns(6)
    metrics = [
        ("Recepciones", f"{summary.get('recepciones', 0):,}"),
        ("KG Recepcionados", f"{summary.get('kg_recepcionados', 0):,.0f}"),
        ("Guias", f"{summary.get('guias', 0):,}"),
        ("Fotos", f"{summary.get('fotos', 0):,}"),
        ("Proformas", f"{summary.get('proformas', 0):,}"),
        ("Facturas", f"{summary.get('facturas', 0):,}"),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.metric(label, value)


def _render_recepciones(recepciones: List[Dict[str, Any]]) -> None:
    st.subheader("Recepciones")
    if not recepciones:
        st.info("No hay recepciones en el rango seleccionado.")
        return
    rows = []
    for item in recepciones:
        rows.append(
            {
                "Fecha": item.get("fecha", ""),
                "Guia": item.get("guia_despacho", ""),
                "Albaran": item.get("albaran", ""),
                "Origen": item.get("origen", ""),
                "KG": round(item.get("kg_recepcionados", 0) or 0, 2),
                "Calidad Final": item.get("calific_final", ""),
                "Estado QC": item.get("quality_state", ""),
                "IQF %": item.get("total_iqf", 0),
                "Block %": item.get("total_block", 0),
                "Fotos": item.get("cantidad_fotos", 0),
                "Docs": item.get("cantidad_documentos", 0),
                "OC": item.get("oc_asociada", ""),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_calidad_fotos(recepciones: List[Dict[str, Any]]) -> None:
    st.subheader("Calidad y Fotos")
    if not recepciones:
        st.info("No hay recepciones para mostrar.")
        return
    options = {
        f"{item.get('fecha', '')} · Guia {item.get('guia_despacho', 'S/G')} · {item.get('kg_recepcionados', 0):,.0f} kg": item
        for item in recepciones
    }
    selected_label = st.selectbox("Selecciona una recepcion", list(options.keys()))
    item = options[selected_label]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Calidad Final", item.get("calific_final", "-"))
    with col2:
        st.metric("IQF %", f"{item.get('total_iqf', 0):.1f}")
    with col3:
        st.metric("Block %", f"{item.get('total_block', 0):.1f}")
    with col4:
        st.metric("Gramos Muestra", f"{item.get('gramos_muestra', 0):,.0f}")

    quality_rows = [
        ("Dano Mecanico", item.get("dano_mecanico", 0)),
        ("Hongos", item.get("hongos", 0)),
        ("Inmadura", item.get("inmadura", 0)),
        ("Sobremadura", item.get("sobremadura", 0)),
        ("Dano Insecto", item.get("dano_insecto", 0)),
        ("Fruta Verde", item.get("fruta_verde", 0)),
        ("Deshidratado", item.get("deshidratado", 0)),
        ("Herida Partida", item.get("herida_partida", 0)),
        ("Crumble", item.get("crumble", 0)),
    ]
    quality_df = pd.DataFrame(quality_rows, columns=["Defecto", "Valor"])
    st.dataframe(quality_df, use_container_width=True, hide_index=True)

    st.markdown("#### Fotos")
    fotos = item.get("fotos", [])
    if not fotos:
        st.info("No hay fotos asociadas a esta recepcion.")
        return
    cols = st.columns(3)
    for idx, foto in enumerate(fotos[:12]):
        try:
            content, filename, mime = _download_attachment(foto["id"])
            with cols[idx % 3]:
                st.image(content, caption=filename, use_container_width=True)
        except Exception as exc:
            with cols[idx % 3]:
                st.warning(f"No se pudo cargar {foto.get('name', 'foto')}: {exc}")


def _render_documents(title: str, documentos: List[Dict[str, Any]]) -> None:
    st.markdown(f"#### {title}")
    if not documentos:
        st.info(f"No hay {title.lower()} disponibles.")
        return
    rows = []
    for doc in documentos:
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
    for doc in documentos:
        attachments = doc.get("attachments", [])
        if not attachments:
            continue
        with st.expander(f"Adjuntos {doc.get('name', '')}"):
            for attachment in attachments:
                try:
                    content, filename, mime = _download_attachment(attachment["id"])
                    st.download_button(
                        label=f"Descargar {filename}",
                        data=content,
                        file_name=filename,
                        mime=mime,
                        key=f"download_{attachment['id']}",
                    )
                except Exception as exc:
                    st.warning(f"No se pudo descargar {attachment.get('name', 'adjunto')}: {exc}")


def _render_app() -> None:
    try:
        me = _api_get("/api/v1/provider-portal/me")
    except Exception:
        _logout()
        return

    partner = me.get("partner", {})
    st.sidebar.markdown(f"### {partner.get('name', 'Proveedor')}")
    st.sidebar.caption(partner.get("rut", ""))
    if partner.get("email"):
        st.sidebar.write(partner["email"])
    if partner.get("phone"):
        st.sidebar.write(partner["phone"])
    st.sidebar.button("Cerrar sesion", on_click=_logout, use_container_width=True)

    st.markdown(
        """
        <div style="background:linear-gradient(135deg,#0d3b66,#1d5f91);padding:24px;border-radius:18px;margin-bottom:20px;">
            <h1 style="margin:0;color:#fff;">Mi Portal de Recepciones</h1>
            <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);font-size:15px;">
                Informacion de recepciones, calidad, fotos y documentos del proveedor.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    today = date.today()
    default_start = today - timedelta(days=30)
    c1, c2 = st.columns(2)
    with c1:
        fecha_inicio = st.date_input("Desde", value=default_start, key="portal_fecha_inicio")
    with c2:
        fecha_fin = st.date_input("Hasta", value=today, key="portal_fecha_fin")

    if fecha_inicio > fecha_fin:
        st.error("La fecha inicio no puede ser mayor que la fecha fin.")
        return

    try:
        dashboard = _api_get(
            "/api/v1/provider-portal/dashboard",
            fecha_inicio=fecha_inicio.isoformat(),
            fecha_fin=fecha_fin.isoformat(),
        )
    except Exception as exc:
        st.error(f"No se pudo cargar la informacion del portal: {exc}")
        return

    _render_summary(dashboard.get("summary", {}))
    tab1, tab2, tab3 = st.tabs(["Recepciones", "Calidad y Fotos", "Proformas y Facturas"])
    with tab1:
        _render_recepciones(dashboard.get("recepciones", []))
    with tab2:
        _render_calidad_fotos(dashboard.get("recepciones", []))
    with tab3:
        _render_documents("Proformas", dashboard.get("proformas", []))
        _render_documents("Facturas", dashboard.get("facturas", []))


if "provider_portal_token" not in st.session_state:
    _render_login()
else:
    _render_app()

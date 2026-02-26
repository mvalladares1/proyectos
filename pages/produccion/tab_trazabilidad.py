"""
Tab Trazabilidad de Pallets - formato tabla con cadenas de composicion.
"""
import streamlit as st
import pandas as pd
import io
from datetime import datetime
from typing import Dict, List
import httpx
from .shared import API_URL


def render(username: str, password: str):
    st.subheader("\U0001f50d Trazabilidad de Pallets")
    st.caption(
        "Ingresa un pallet y rastrea su cadena productiva hasta la recepcion "
        "de materia prima (guia de despacho y productor)."
    )

    col_in, col_btn = st.columns([3, 1])
    with col_in:
        pallet_name = st.text_input(
            "Nombre del pallet", placeholder="Ej: PACK0012345",
            key="traz_in",
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        buscar = st.button("\U0001f50d Trazar", type="primary", key="traz_btn")

    if not buscar and "traz_res" not in st.session_state:
        st.info("Ingresa un pallet y presiona **Trazar**.")
        return

    if buscar:
        if not pallet_name or not pallet_name.strip():
            st.warning("Ingresa un nombre de pallet.")
            return
        pallet_name = pallet_name.strip().upper()
        with st.spinner(f"Trazando **{pallet_name}** ..."):
            try:
                r = httpx.get(
                    f"{API_URL}/api/v1/produccion/trazabilidad",
                    params={
                        "pallet_name": pallet_name,
                        "username": username,
                        "password": password,
                    },
                    timeout=120.0,
                )
                r.raise_for_status()
                st.session_state["traz_res"] = r.json()
            except httpx.TimeoutException:
                st.error("Timeout.")
                return
            except httpx.HTTPStatusError as e:
                st.error(f"Error {e.response.status_code}: {e.response.text[:300]}")
                return
            except Exception as e:
                st.error(f"Error: {e}")
                return

    res = st.session_state.get("traz_res")
    if not res:
        return
    if res.get("error"):
        st.error(f"{res['error']}")
        return

    pack = res.get("pack", "")
    consumidos = res.get("pallets_consumidos", "")
    cadenas = res.get("cadenas", [])

    # --- Header info ---
    st.markdown(f"**Pack:** {pack}")
    st.markdown(f"**Pallets Consumidos:** {consumidos}")
    st.divider()

    # --- Tabla principal ---
    if cadenas:
        rows = []
        for c in cadenas:
            rows.append({
                "Pallet Origen": c.get("pallet_origen", ""),
                "Cadena de Trazabilidad": c.get("cadena", ""),
                "Guia Despacho": c.get("guia_despacho", ""),
                "Productor": c.get("productor", ""),
            })
        df = pd.DataFrame(rows)

        def _highlight(row):
            if row["Cadena de Trazabilidad"] == "NO TIENE TRAZABILIDAD":
                return ["color: red; font-style: italic"] * len(row)
            return [""] * len(row)

        styled = df.style.apply(_highlight, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.warning("No se encontraron cadenas de trazabilidad.")

    st.divider()

    # --- Excel ---
    st.markdown("### Exportar")
    excel = _generar_excel(res)
    fname = f"Trazabilidad_{pack}_{datetime.now():%Y%m%d_%H%M}.xlsx"
    st.download_button(
        "Descargar Excel",
        data=excel,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


def _generar_excel(res: Dict) -> bytes:
    """Genera Excel con formato identico al screenshot del usuario."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pack = res.get("pack", "")
        consumidos = res.get("pallets_consumidos", "")
        cadenas = res.get("cadenas", [])

        rows = []
        for c in cadenas:
            rows.append({
                "Pack": pack,
                "Pallets Consumidos": consumidos,
                "Pallet Origen": c.get("pallet_origen", ""),
                "Cadena de Trazabilidad": c.get("cadena", ""),
                "Guia Despacho": c.get("guia_despacho", ""),
                "Productor": c.get("productor", ""),
            })

        df = pd.DataFrame(rows) if rows else pd.DataFrame({"Info": ["Sin datos"]})
        df.to_excel(writer, sheet_name="Trazabilidad", index=False)

        # Auto-width
        ws = writer.sheets["Trazabilidad"]
        for col in ws.columns:
            letter = col[0].column_letter
            max_len = max((len(str(c.value or "")) for c in col), default=10)
            ws.column_dimensions[letter].width = min(max_len + 4, 70)

    output.seek(0)
    return output.getvalue()

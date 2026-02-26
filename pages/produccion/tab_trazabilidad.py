"""
Tab Trazabilidad de Pallets - formato jerarquico.
"""
import streamlit as st
import pandas as pd
import io
from datetime import datetime
from typing import Dict
import httpx
from .shared import API_URL


def render(username: str, password: str):
    st.subheader("\ud83d\udd0d Trazabilidad de Pallets")
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
        buscar = st.button("\ud83d\udd0d Trazar", type="primary", key="traz_btn")

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
    filas = res.get("filas", [])

    st.markdown(f"### Trazabilidad de **{pack}**")
    st.divider()

    if filas:
        for f in filas:
            nivel = f.get("nivel", 0)
            pallet = f.get("pallet", "")
            conforma = f.get("se_conforma_por", "")
            producto = f.get("producto", "")
            guia = f.get("guia_despacho", "")
            productor = f.get("productor", "")
            fecha = f.get("fecha_recepcion", "")
            indent = "\u2003" * nivel
            arrow = "\u2192"
            if conforma == "(RECEPCION)":
                st.markdown(
                    f"{indent}**{pallet}** {arrow} :green[RECEPCION] "
                    f"{producto} "
                    f"Guia: **{guia}** "
                    f"Productor: **{productor}** "
                    f"Fecha: {fecha}"
                )
            elif conforma == "(SIN CONSUMIDOS)":
                st.markdown(f"{indent}**{pallet}**  {arrow} :red[SIN CONSUMIDOS]")
            else:
                st.markdown(
                    f"{indent}**{pallet}** se conforma por: {conforma} "
                    f"{producto}"
                )
    else:
        st.warning("No se encontraron datos.")

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
    """Genera Excel con formato jerarquico."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pack = res.get("pack", "")
        filas = res.get("filas", [])

        rows = []
        for f in filas:
            rows.append({
                "Pack": pack,
                "Nivel": f.get("nivel", 0),
                "Pallet": ("  " * f.get("nivel", 0)) + f.get("pallet", ""),
                "Se Conforma Por": f.get("se_conforma_por", ""),
                "Producto": f.get("producto", ""),
                "Guia Despacho": f.get("guia_despacho", ""),
                "Productor": f.get("productor", ""),
                "Fecha Recepcion": f.get("fecha_recepcion", ""),
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

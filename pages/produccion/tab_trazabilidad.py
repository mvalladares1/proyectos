"""
Tab Trazabilidad de Pallets – multi-pallet.
Permite trazar varios pallets a la vez.
Excel con 2 hojas:
  1) Trazabilidad Completa  (cadena detallada)
  2) Guías y Productores    (resumen único guía + productor)
"""
import streamlit as st
import pandas as pd
import io
from datetime import datetime
from typing import Dict, List
import httpx
from .shared import API_URL


# ═════════════════════════════════════════════════════════════
# Render principal
# ═════════════════════════════════════════════════════════════

def render(username: str, password: str):
    st.subheader("\U0001F50D Trazabilidad de Pallets")
    st.caption(
        "Ingresa uno o más pallets (separados por coma, espacio o salto de línea) "
        "y genera un Excel con toda la trazabilidad."
    )

    pallet_text = st.text_area(
        "Pallets a trazar",
        placeholder="PACK0012345, PACK0012346\nPACK0012347",
        height=100,
        key="traz_input",
        help="Puedes pegar varios pallets. Se aceptan separados por coma, espacio o línea.",
    )

    buscar = st.button("\U0001F50D Trazar Todos", type="primary", key="traz_btn")

    if not buscar and "traz_multi" not in st.session_state:
        st.info("Ingresa uno o más pallets y presiona **Trazar Todos**.")
        return

    # ── Llamar API por cada pallet ───────────────────────────
    if buscar:
        nombres = _parsear_pallets(pallet_text)
        if not nombres:
            st.warning("Ingresa al menos un nombre de pallet.")
            return

        resultados: List[Dict] = []
        errores: List[str] = []
        progress = st.progress(0, text="Iniciando...")

        for i, nombre in enumerate(nombres):
            progress.progress(
                (i) / len(nombres),
                text=f"Trazando **{nombre}** ({i+1}/{len(nombres)})...",
            )
            try:
                r = httpx.get(
                    f"{API_URL}/api/v1/produccion/trazabilidad",
                    params={
                        "pallet_name": nombre,
                        "username": username,
                        "password": password,
                    },
                    timeout=180.0,
                )
                r.raise_for_status()
                data = r.json()
                if data.get("error"):
                    errores.append(f"{nombre}: {data['error']}")
                else:
                    resultados.append(data)
            except Exception as e:
                errores.append(f"{nombre}: {e}")

        progress.progress(1.0, text="Listo.")
        st.session_state["traz_multi"] = resultados
        st.session_state["traz_errores"] = errores

    resultados = st.session_state.get("traz_multi", [])
    errores = st.session_state.get("traz_errores", [])

    if errores:
        for err in errores:
            st.warning(err)

    if not resultados:
        st.error("No se obtuvo trazabilidad de ningún pallet.")
        return

    # ── Métricas globales ────────────────────────────────────
    total_filas = sum(len(r.get("filas", [])) for r in resultados)
    total_guias = set()
    total_productores = set()
    for r in resultados:
        for f in r.get("filas", []):
            g = f.get("guia_despacho", "")
            p = f.get("productor", "")
            if g:
                total_guias.add(g)
            if p:
                total_productores.add(p)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pallets Trazados", len(resultados))
    c2.metric("Filas Totales", total_filas)
    c3.metric("Guías Únicas", len(total_guias))
    c4.metric("Productores Únicos", len(total_productores))

    st.divider()

    # ── Mostrar tabla por cada pack ──────────────────────────
    for res in resultados:
        pack = res.get("pack", "")
        pallets_consumidos = res.get("pallets_consumidos", "")
        filas = res.get("filas", [])

        with st.expander(f"**{pack}** — {len(filas)} filas — Consumidos: {pallets_consumidos}", expanded=len(resultados) == 1):
            if filas:
                rows = []
                for f in filas:
                    rows.append({
                        "Pallet Origen": f.get("pallet_origen", ""),
                        "Cadena de Trazabilidad": f.get("cadena", ""),
                        "Guía Despacho": f.get("guia_despacho", ""),
                        "Productor": f.get("productor", ""),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("Sin datos.")

    st.divider()

    # ── Descarga Excel ───────────────────────────────────────
    st.markdown("### \U0001F4E5 Exportar Excel")
    excel = _generar_excel_multi(resultados)
    packs_str = "_".join(r.get("pack", "X") for r in resultados[:3])
    if len(resultados) > 3:
        packs_str += f"_y_{len(resultados)-3}_mas"
    fname = f"Trazabilidad_{packs_str}_{datetime.now():%Y%m%d_%H%M}.xlsx"
    st.download_button(
        "\u2B07\uFE0F Descargar Excel (2 hojas)",
        data=excel,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


# ═════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════

def _parsear_pallets(text: str) -> List[str]:
    """Extrae nombres de pallets de texto libre."""
    import re
    if not text:
        return []
    # Reemplazar separadores comunes por espacio
    cleaned = re.sub(r'[,;\n\r\t]+', ' ', text)
    nombres = [n.strip().upper() for n in cleaned.split() if n.strip()]
    # Deduplicar preservando orden
    seen = set()
    result = []
    for n in nombres:
        if n not in seen:
            seen.add(n)
            result.append(n)
    return result


# ═════════════════════════════════════════════════════════════
# Generación Excel – 2 hojas
# ═════════════════════════════════════════════════════════════

def _generar_excel_multi(resultados: List[Dict]) -> bytes:
    """
    Genera Excel con 2 hojas:
      1) Trazabilidad Completa – toda la info por pack
      2) Guías y Productores  – resumen único de guías
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()

    # ── Estilos compartidos ──────────────────────────────────
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hdr_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    hdr_font = Font(color="FFFFFF", bold=True, size=11)
    hdr2_fill = PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid")
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_al = Alignment(vertical="center", wrap_text=True)
    red_font = Font(color="CC0000", bold=True, italic=True)
    green_font = Font(color="006100", bold=True)
    pack_font = Font(bold=True, size=11)
    sep_fill = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")

    def write_header(ws, headers, fill=None):
        f = fill or hdr_fill
        for c, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.fill = f
            cell.font = hdr_font
            cell.alignment = center
            cell.border = border

    def set_widths(ws, widths):
        for c, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(c)].width = w

    # ══════════════════════════════════════════════════════════
    # HOJA 1 – Trazabilidad Completa
    # ══════════════════════════════════════════════════════════
    ws1 = wb.active
    ws1.title = "Trazabilidad Completa"

    h1 = ["Pack", "Pallets Consumidos", "Pallet Origen",
          "Cadena de Trazabilidad", "Guía Despacho", "Productor"]
    write_header(ws1, h1)
    set_widths(ws1, [20, 50, 16, 60, 18, 42])

    row_idx = 2
    for res in resultados:
        pack = res.get("pack", "")
        consumidos = res.get("pallets_consumidos", "")
        filas = res.get("filas", [])

        if not filas:
            continue

        start_row = row_idx
        for f in filas:
            ws1.cell(row=row_idx, column=1, value=pack).font = pack_font
            ws1.cell(row=row_idx, column=2, value=consumidos)
            ws1.cell(row=row_idx, column=3, value=f.get("pallet_origen", ""))
            ws1.cell(row=row_idx, column=4, value=f.get("cadena", ""))
            ws1.cell(row=row_idx, column=5, value=f.get("guia_despacho", ""))
            ws1.cell(row=row_idx, column=6, value=f.get("productor", ""))

            # Formato y bordes
            for c in range(1, 7):
                cell = ws1.cell(row=row_idx, column=c)
                cell.border = border
                cell.alignment = center if c <= 3 else left_al

            # Colores condicionales
            cadena_cell = ws1.cell(row=row_idx, column=4)
            if "NO TIENE" in str(cadena_cell.value):
                cadena_cell.font = red_font
            guia_cell = ws1.cell(row=row_idx, column=5)
            if guia_cell.value:
                guia_cell.font = green_font

            row_idx += 1

        end_row = row_idx - 1

        # Merge Pack y Pallets Consumidos para este bloque
        if end_row > start_row:
            ws1.merge_cells(start_row=start_row, start_column=1, end_row=end_row, end_column=1)
            ws1.merge_cells(start_row=start_row, start_column=2, end_row=end_row, end_column=2)
        ws1.cell(row=start_row, column=1).alignment = center
        ws1.cell(row=start_row, column=2).alignment = center

        # Fila separadora entre packs
        if res != resultados[-1]:
            for c in range(1, 7):
                cell = ws1.cell(row=row_idx, column=c)
                cell.fill = sep_fill
                cell.border = border
            row_idx += 1

    ws1.freeze_panes = "A2"

    # ══════════════════════════════════════════════════════════
    # HOJA 2 – Guías y Productores
    # ══════════════════════════════════════════════════════════
    ws2 = wb.create_sheet("Guías y Productores")

    h2 = ["Pack", "Guía Despacho", "Productor"]
    write_header(ws2, h2, fill=hdr2_fill)
    set_widths(ws2, [20, 22, 48])

    # Recolectar guías únicas por pack
    guias_por_pack: Dict[str, List] = {}
    for res in resultados:
        pack = res.get("pack", "")
        seen_guias: set = set()
        entries: List = []
        for f in res.get("filas", []):
            guia = f.get("guia_despacho", "")
            prod = f.get("productor", "")
            key = (guia, prod)
            if key not in seen_guias and (guia or prod):
                seen_guias.add(key)
                entries.append({"guia": guia, "prod": prod})
        if entries:
            guias_por_pack[pack] = entries

    row2 = 2
    for pack, entries in guias_por_pack.items():
        start2 = row2
        for entry in entries:
            ws2.cell(row=row2, column=1, value=pack).font = pack_font
            g_cell = ws2.cell(row=row2, column=2, value=entry["guia"])
            g_cell.font = green_font if entry["guia"] else Font()
            ws2.cell(row=row2, column=3, value=entry["prod"])

            for c in range(1, 4):
                cell = ws2.cell(row=row2, column=c)
                cell.border = border
                cell.alignment = center if c <= 2 else left_al

            row2 += 1

        end2 = row2 - 1
        # Merge Pack
        if end2 > start2:
            ws2.merge_cells(start_row=start2, start_column=1, end_row=end2, end_column=1)
        ws2.cell(row=start2, column=1).alignment = center

        # Separador
        if pack != list(guias_por_pack.keys())[-1]:
            for c in range(1, 4):
                cell = ws2.cell(row=row2, column=c)
                cell.fill = sep_fill
                cell.border = border
            row2 += 1

    ws2.freeze_panes = "A2"

    # ── Guardar ──────────────────────────────────────────────
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()

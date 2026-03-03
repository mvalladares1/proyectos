"""
Tab Trazabilidad de Pallets - trazado automatico completo.

Flujo simplificado:
  1) El usuario ingresa un pallet
  2) Un clic -> el sistema traza TODO automaticamente hasta las recepciones
  3) Muestra un arbol visual claro
  4) Genera Excel limpio con la trazabilidad completa
"""
import streamlit as st
import io
from datetime import datetime
from typing import Dict, List, Optional
import httpx
from .shared import API_URL

TREE_KEY = "traz_tree_v2"


# =============================================================
# API
# =============================================================

def _full_trace(package_name: str, username: str, password: str) -> Dict:
    """Llama al endpoint que traza todo el arbol en un solo request."""
    r = httpx.get(
        f"{API_URL}/api/v1/etiquetas/full_trace",
        params={
            "package_name": package_name,
            "username": username,
            "password": password,
            "max_levels": 12,
        },
        timeout=120.0,
    )
    r.raise_for_status()
    return r.json()


# =============================================================
# Helpers
# =============================================================

def _short(name: str) -> str:
    """PACK0048229 -> 048229"""
    if not name:
        return ""
    n = name.strip()
    if n.upper().startswith("PACK"):
        return n[4:].strip() or n
    return n


def _build_children_map(nodes: List[Dict]) -> Dict[int, List[Dict]]:
    """Agrupa nodos por parent_node_id -> hijos."""
    children: Dict[int, List[Dict]] = {}
    for n in nodes:
        pid = n.get("parent_node_id")
        if pid is not None:
            children.setdefault(pid, []).append(n)
    return children


def _build_chain(node: Dict, idx: Dict[int, Dict]) -> List[str]:
    """Construye cadena de nombres desde root hasta el nodo."""
    chain = [_short(node["pkg_name"])]
    cur = node
    while cur.get("parent_node_id") and cur["parent_node_id"] in idx:
        cur = idx[cur["parent_node_id"]]
        chain.append(_short(cur["pkg_name"]))
    chain.reverse()
    return chain


# =============================================================
# Render principal
# =============================================================

def render(username: str, password: str):
    st.subheader("\U0001f50d Trazabilidad de Pallets")
    st.caption(
        "Ingresa un pallet y el sistema traza automaticamente toda la cadena "
        "hasta las recepciones con guia de despacho y productor."
    )

    # Estado
    if TREE_KEY not in st.session_state:
        st.session_state[TREE_KEY] = None

    # Limpiar estado antiguo (v1)
    for old_key in ["traz_tree", "traz_acumulado"]:
        if old_key in st.session_state:
            del st.session_state[old_key]

    data = st.session_state[TREE_KEY]

    # Input
    col_in, col_btn, col_rst = st.columns([3, 1.2, 0.8])
    with col_in:
        pallet_name = st.text_input(
            "Pallet",
            placeholder="Ej: PACK0012345",
            key="traz_input_v2",
            label_visibility="collapsed",
        )
    with col_btn:
        trazar = st.button("\U0001f680 Trazar", type="primary", use_container_width=True)
    with col_rst:
        if data and st.button("\U0001f504 Limpiar", use_container_width=True):
            st.session_state[TREE_KEY] = None
            st.rerun()

    # Trazar
    if trazar:
        if not pallet_name or not pallet_name.strip():
            st.warning("Ingresa un nombre de pallet.")
            return

        nombre = pallet_name.strip().upper()
        try:
            with st.spinner(f"Trazando **{nombre}** \u2014 buscando toda la cadena hasta recepcion..."):
                result = _full_trace(nombre, username, password)
            st.session_state[TREE_KEY] = result
            data = result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                st.error(f"No se encontro el pallet **{nombre}** en Odoo.")
            else:
                st.error(f"Error del servidor: {e.response.text}")
            return
        except Exception as e:
            st.error(f"Error de conexion: {e}")
            return

    if data is None:
        st.info(
            "Ingresa un pallet y presiona **Trazar** para ver la cadena completa "
            "de trazabilidad hasta las recepciones."
        )
        return

    # Resultado
    _render_result(data)


# =============================================================
# Render resultado
# =============================================================

def _render_result(data: Dict):
    """Muestra el resultado del trazado completo."""
    nodes = data.get("nodes", [])
    root_name = data.get("root_name", "?")
    num_levels = data.get("levels", 0)
    leaf_count = data.get("leaf_count", 0)
    rec_count = data.get("reception_count", 0)

    if not nodes:
        st.warning("No se encontraron datos para este pallet.")
        return

    st.divider()

    # Metricas
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pallet", root_name)
    c2.metric("Niveles", num_levels)
    c3.metric("Recepciones", rec_count)
    c4.metric("Total pallets", len(nodes))

    if rec_count > 0 and rec_count == leaf_count:
        st.success("\u2705 Trazabilidad completa \u2014 todos los caminos llegan a recepcion.")
    elif rec_count > 0:
        st.info(f"\u2139\ufe0f {rec_count} de {leaf_count} hojas son recepciones.")

    # Arbol visual
    st.markdown("### \U0001f333 Arbol de Trazabilidad")

    idx = {n["node_id"]: n for n in nodes}
    children_map = _build_children_map(nodes)
    root = next((n for n in nodes if n.get("parent_node_id") is None), None)

    if root:
        _render_tree_node(root, idx, children_map, depth=0)

    # Tabla de recepciones
    receptions = [n for n in nodes if n.get("reception_info")]
    if receptions:
        st.markdown("### \U0001f4cb Recepciones Encontradas")
        rows = []
        for n in receptions:
            rec = n["reception_info"]
            chain = _build_chain(n, idx)
            rows.append({
                "Pallet Origen": n["pkg_name"],
                "Cadena": " \u2192 ".join(chain),
                "Guia Despacho": rec.get("guia_despacho", "") or "\u2014",
                "Productor": rec.get("proveedor", "") or "\u2014",
                "Picking": rec.get("picking_name", "") or "\u2014",
                "Fecha": rec.get("fecha", "") or "\u2014",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    # Excel
    st.divider()
    excel = _generar_excel(data)
    fname = f"Trazabilidad_{root_name}_{datetime.now():%Y%m%d_%H%M}.xlsx"
    st.download_button(
        "\u2b07\ufe0f Descargar Excel",
        data=excel,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


# =============================================================
# Arbol visual recursivo
# =============================================================

def _render_tree_node(node: Dict, idx: Dict, children_map: Dict, depth: int):
    """Renderiza un nodo y sus hijos recursivamente como arbol con indentacion."""
    pad = "&nbsp;&nbsp;&nbsp;&nbsp;" * depth
    nid = node["node_id"]
    name = node["pkg_name"]
    rec = node.get("reception_info")
    mo = node.get("mo_name")
    kids = children_map.get(nid, [])

    if depth == 0:
        # Raiz
        st.markdown(f"\U0001f4e6 **`{name}`** (destino final)")
    elif rec:
        # Recepcion (hoja verde)
        guia = rec.get("guia_despacho", "") or "\u2014"
        prov = rec.get("proveedor", "") or "\u2014"
        fecha = rec.get("fecha", "") or ""
        st.markdown(
            f"{pad}\U0001f7e2 **`{name}`** \u2014 Guia: **{guia}** \u00b7 Productor: **{prov}** \u00b7 {fecha}"
        )
    elif node.get("is_leaf"):
        # Hoja sin recepcion
        st.markdown(f"{pad}\U0001f7e1 `{name}` \u2014 sin origen conocido")
    else:
        # Nodo intermedio
        mo_label = f" *(OP: {mo})*" if mo else ""
        st.markdown(f"{pad}\U0001f539 **`{name}`**{mo_label}")

    # Hijos
    for child in kids:
        _render_tree_node(child, idx, children_map, depth + 1)


# =============================================================
# Excel - 2 hojas limpias
# =============================================================

def _generar_excel(data: Dict) -> bytes:
    """
    Excel con 2 hojas:
      1) Trazabilidad - una fila por recepcion con cadena completa
      2) Arbol Completo - todos los nodos del arbol
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    nodes = data.get("nodes", [])
    root_name = data.get("root_name", "?")
    idx = {n["node_id"]: n for n in nodes}

    wb = Workbook()

    # Estilos
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hdr_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    hdr_font = Font(color="FFFFFF", bold=True, size=11)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_al = Alignment(vertical="center", wrap_text=True)
    rec_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    root_fill = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
    hdr2_fill = PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid")

    def _write_header(ws, headers, fill=None):
        for c, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.fill = fill or hdr_fill
            cell.font = hdr_font
            cell.alignment = center
            cell.border = border

    def _set_widths(ws, widths):
        for c, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(c)].width = w

    # ===========================================================
    # HOJA 1 - Trazabilidad (una fila por recepcion)
    # ===========================================================
    ws1 = wb.active
    ws1.title = "Trazabilidad"

    headers1 = [
        "Pack (Destino)", "Pallet Origen (Recepcion)",
        "Cadena Completa", "Guia Despacho", "Productor",
        "Picking", "Fecha Recepcion",
    ]
    _write_header(ws1, headers1)
    _set_widths(ws1, [20, 20, 55, 20, 35, 20, 14])

    receptions = [n for n in nodes if n.get("reception_info")]
    row = 2
    for n in receptions:
        rec = n["reception_info"]
        chain = _build_chain(n, idx)
        chain_str = " \u2192 ".join(chain)

        ws1.cell(row=row, column=1, value=root_name)
        ws1.cell(row=row, column=2, value=n["pkg_name"])
        ws1.cell(row=row, column=3, value=chain_str)
        ws1.cell(row=row, column=4, value=rec.get("guia_despacho", ""))
        ws1.cell(row=row, column=5, value=rec.get("proveedor", ""))
        ws1.cell(row=row, column=6, value=rec.get("picking_name", ""))
        ws1.cell(row=row, column=7, value=rec.get("fecha", ""))

        for c in range(1, 8):
            cell = ws1.cell(row=row, column=c)
            cell.border = border
            cell.alignment = left_al
            cell.fill = rec_fill
        row += 1

    if not receptions:
        ws1.cell(row=2, column=1, value=root_name)
        ws1.cell(row=2, column=2, value="(sin recepciones encontradas)")
        for c in range(1, 8):
            ws1.cell(row=2, column=c).border = border

    ws1.freeze_panes = "A2"

    # ===========================================================
    # HOJA 2 - Arbol Completo
    # ===========================================================
    ws2 = wb.create_sheet("Arbol Completo")

    headers2 = [
        "Nivel", "Pallet", "Padre", "OP",
        "Producto", "Cantidad (kg)", "Lote", "Tipo",
        "Guia Despacho", "Productor", "Picking", "Fecha",
    ]
    _write_header(ws2, headers2, fill=hdr2_fill)
    _set_widths(ws2, [8, 20, 20, 22, 45, 14, 20, 14, 20, 35, 20, 14])

    sorted_nodes = sorted(nodes, key=lambda n: (n.get("level", 0), n.get("pkg_name", "")))

    row2 = 2
    for n in sorted_nodes:
        level = n.get("level", 0)
        rec = n.get("reception_info")
        is_leaf = n.get("is_leaf", False)

        if level == 0:
            tipo = "Destino"
        elif rec:
            tipo = "Recepcion"
        elif is_leaf:
            tipo = "Hoja"
        else:
            tipo = "Intermedio"

        parent = idx.get(n.get("parent_node_id"))
        parent_name = parent["pkg_name"] if parent else ""

        ws2.cell(row=row2, column=1, value=level)
        ws2.cell(row=row2, column=2, value=n.get("pkg_name", "")).font = Font(bold=True)
        ws2.cell(row=row2, column=3, value=parent_name)
        ws2.cell(row=row2, column=4, value=n.get("mo_name", "") or "")
        ws2.cell(row=row2, column=5, value=n.get("product_name", "") or "")
        qty = n.get("qty")
        ws2.cell(row=row2, column=6, value=f"{qty:.1f}" if qty else "")
        ws2.cell(row=row2, column=7, value=n.get("lot_name", "") or "")
        ws2.cell(row=row2, column=8, value=tipo)
        ws2.cell(row=row2, column=9, value=rec.get("guia_despacho", "") if rec else "")
        ws2.cell(row=row2, column=10, value=rec.get("proveedor", "") if rec else "")
        ws2.cell(row=row2, column=11, value=rec.get("picking_name", "") if rec else "")
        ws2.cell(row=row2, column=12, value=rec.get("fecha", "") if rec else "")

        for c in range(1, 13):
            cell = ws2.cell(row=row2, column=c)
            cell.border = border
            cell.alignment = center if c in (1, 6, 8) else left_al

        if level == 0:
            for c in range(1, 13):
                ws2.cell(row=row2, column=c).fill = root_fill
        elif rec:
            for c in range(1, 13):
                ws2.cell(row=row2, column=c).fill = rec_fill

        row2 += 1

    ws2.freeze_panes = "A2"

    # Guardar
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()

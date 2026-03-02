"""
Tab Trazabilidad Interactiva de Pallets – paso a paso.

Flujo:
  1) El usuario ingresa un pallet destino final
  2) El sistema busca los paquetes origen que lo conformaron (candidatos)
  3) El usuario selecciona cuáles seguir trazando hacia atrás
  4) Se repite hasta llegar a paquetes de recepción (sin orígenes)
  5) Se genera Excel con la cadena completa de trazabilidad

Cada paquete destino se compone de paquetes origen.
Esos paquetes origen, en un proceso anterior, fueron paquetes destino
compuestos por otros paquetes origen, y así sucesivamente hasta
llegar a la recepción.
"""
import streamlit as st
import pandas as pd
import io
from datetime import datetime
from typing import Dict, List, Optional
import httpx
from .shared import API_URL

TREE_KEY = "traz_tree"
OLD_SESSION_KEY = "traz_acumulado"  # clave antigua, limpiar si existe


# ═════════════════════════════════════════════════════════════
# Helpers API
# ═════════════════════════════════════════════════════════════

def _api_get(url: str, params: dict, timeout: float = 60.0):
    """GET al backend con timeout."""
    r = httpx.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _find_package(name: str, username: str, password: str) -> Optional[Dict]:
    """Busca un package por nombre exacto/similar. Devuelve {id, name} o None."""
    try:
        res = _api_get(
            f"{API_URL}/api/v1/etiquetas/find_package",
            {"package_name": name, "username": username, "password": password},
        )
        if not res:
            return None
        # preferir match exacto
        for r in res:
            if (r.get("name") or "").upper() == name.upper():
                return r
        return res[0]
    except Exception:
        return None


def _get_candidates(pkg_id: int, username: str, password: str,
                    product_name=None, manejo=None, variedad=None) -> List[Dict]:
    """Obtiene candidatos previos (paquetes origen) para un paquete destino."""
    params: dict = {"package_id": pkg_id, "username": username, "password": password}
    if product_name:
        params["product_name"] = product_name
    if manejo:
        params["manejo"] = manejo
    if variedad:
        params["variedad"] = variedad
    try:
        return _api_get(f"{API_URL}/api/v1/etiquetas/prev_candidates", params) or []
    except Exception:
        return []


def _get_package_info(pkg_id: int, username: str, password: str) -> Dict:
    """Obtiene info de etiqueta (producto, manejo, variedad, etc.)."""
    try:
        return _api_get(
            f"{API_URL}/api/v1/etiquetas/info_etiqueta/{pkg_id}",
            {"username": username, "password": password},
            timeout=30.0,
        ) or {}
    except Exception:
        return {}


def _new_node(pkg_id: int, pkg_name: str, **extra) -> Dict:
    """Crea un nodo de paquete en el árbol de trazabilidad."""
    node = {
        "pkg_id": pkg_id,
        "pkg_name": pkg_name,
        "candidates": None,  # None = no cargado, [] = sin orígenes
        "is_leaf": False,
    }
    node.update(extra)
    return node


def _all_known_pkg_ids(tree: Dict) -> set:
    """Devuelve el set de todos los pkg_id ya presentes en el árbol (para evitar ciclos)."""
    ids = set()
    for lvl in tree.get("levels", []):
        for p in lvl:
            ids.add(p["pkg_id"])
    return ids


# ═════════════════════════════════════════════════════════════
# Render principal
# ═════════════════════════════════════════════════════════════

def render(username: str, password: str):
    st.subheader("\U0001F50D Trazabilidad Interactiva de Pallets")
    st.caption(
        "Traza pallets paso a paso hacia atrás. En cada nivel el sistema "
        "muestra los paquetes origen y tú eliges cuáles seguir trazando."
    )

    # limpiar estado antiguo
    if OLD_SESSION_KEY in st.session_state:
        del st.session_state[OLD_SESSION_KEY]

    # Inicializar árbol
    if TREE_KEY not in st.session_state:
        st.session_state[TREE_KEY] = None

    tree = st.session_state[TREE_KEY]

    # ── Fase 1: Ingresar pallet raíz ────────────────────────
    if tree is None:
        _render_input_root(username, password)
        return

    # ── Header ───────────────────────────────────────────────
    filters = tree.get("filters", {})
    col_hdr, col_reset = st.columns([4, 1])
    with col_hdr:
        st.markdown(f"**Pallet raíz:** `{tree['root_name']}`")
        parts = []
        if filters.get("product_name"):
            parts.append(f"**Producto:** {filters['product_name']}")
        if filters.get("manejo"):
            parts.append(f"**Manejo:** {filters['manejo']}")
        if filters.get("variedad"):
            parts.append(f"**Variedad:** {filters['variedad']}")
        if parts:
            st.caption(" · ".join(parts))
    with col_reset:
        if st.button("\U0001F504 Nueva", key="traz_reset"):
            st.session_state[TREE_KEY] = None
            st.rerun()

    st.divider()

    # ── Fase 2: Navegar niveles del árbol ────────────────────
    levels = tree["levels"]
    for level_idx, level_pkgs in enumerate(levels):
        is_frontier = level_idx == len(levels) - 1
        _render_level(level_idx, level_pkgs, is_frontier, tree, username, password)

    # ── Fase 3: Resumen y exportar Excel ─────────────────────
    st.divider()
    _render_summary_and_export(tree)


# ═════════════════════════════════════════════════════════════
# Fase 1 – Input pallet raíz
# ═════════════════════════════════════════════════════════════

def _render_input_root(username: str, password: str):
    """Muestra input para el pallet destino raíz."""
    col_in, col_btn = st.columns([3, 1])
    with col_in:
        pallet_name = st.text_input(
            "Pallet destino inicial",
            placeholder="Ej: PACK0012345",
            key="traz_root_input",
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        iniciar = st.button("\U0001F680 Iniciar Trazabilidad", type="primary")

    if not iniciar:
        st.info(
            "Ingresa un pallet destino para iniciar la trazabilidad paso a paso.\n\n"
            "El sistema buscará los paquetes origen que lo conformaron. "
            "En cada nivel podrás elegir cuáles seguir trazando hasta llegar "
            "a la recepción."
        )
        return

    if not pallet_name or not pallet_name.strip():
        st.warning("Ingresa un nombre de pallet.")
        return

    nombre = pallet_name.strip().upper()

    with st.spinner(f"Buscando **{nombre}** en Odoo..."):
        pkg = _find_package(nombre, username, password)

    if not pkg:
        st.error(f"No se encontró el paquete **{nombre}** en Odoo.")
        return

    with st.spinner("Obteniendo información del producto..."):
        info = _get_package_info(pkg["id"], username, password)

    tree = {
        "root_name": nombre,
        "root_id": pkg["id"],
        "filters": {
            "product_name": info.get("product_name") or info.get("nombre_producto"),
            "manejo": info.get("manejo"),
            "variedad": info.get("variedad"),
        },
        "levels": [
            [_new_node(pkg["id"], nombre)]
        ],
    }
    st.session_state[TREE_KEY] = tree
    st.rerun()


# ═════════════════════════════════════════════════════════════
# Fase 2 – Renderizar un nivel del árbol
# ═════════════════════════════════════════════════════════════

def _render_level(level_idx: int, level_pkgs: List[Dict], is_frontier: bool,
                  tree: Dict, username: str, password: str):
    """Renderiza un nivel del árbol de paquetes."""
    filters = tree.get("filters", {})
    levels = tree["levels"]
    n_pkgs = len(level_pkgs)

    # ── Título del nivel ─────────────────────────────────────
    if level_idx == 0:
        label = "\U0001F3AF **Nivel 0** — Pallet Destino"
    else:
        label = f"\U0001F4E6 **Nivel {level_idx}** — {n_pkgs} paquete(s)"
    st.markdown(label)

    # ── Si NO es frontera → resumen compacto ─────────────────
    if not is_frontier:
        names = ", ".join(f"`{p['pkg_name']}`" for p in level_pkgs)
        st.markdown(f"&nbsp;&nbsp;&nbsp; {names}")
        return

    # ── FRONTERA: cargar candidatos y seleccionar ────────────
    any_unloaded = any(
        p.get("candidates") is None and not p.get("is_leaf")
        for p in level_pkgs
    )
    all_leaves = all(
        p.get("is_leaf") or (isinstance(p.get("candidates"), list) and len(p["candidates"]) == 0)
        for p in level_pkgs
    )

    # Si todos son hojas → trazabilidad completa en este nivel
    if all_leaves:
        for p in level_pkgs:
            st.markdown(f"&nbsp;&nbsp;&nbsp; \U0001F7E2 `{p['pkg_name']}` — sin orígenes (recepción/inicio)")
        return

    # ── Botón para cargar candidatos de todos los paquetes ───
    if any_unloaded:
        unloaded_names = [
            p["pkg_name"] for p in level_pkgs
            if p.get("candidates") is None and not p.get("is_leaf")
        ]
        btn_label = f"\U0001F50D Buscar orígenes ({len(unloaded_names)} paquetes pendientes)"
        if st.button(btn_label, key=f"load_all_{level_idx}", type="primary"):
            known_ids = _all_known_pkg_ids(tree)
            with st.spinner("Buscando orígenes en Odoo..."):
                for p in level_pkgs:
                    if p.get("candidates") is None and not p.get("is_leaf"):
                        cands = _get_candidates(
                            p["pkg_id"], username, password,
                            product_name=filters.get("product_name"),
                            manejo=filters.get("manejo"),
                            variedad=filters.get("variedad"),
                        )
                        # Filtrar candidatos que ya están en el árbol (evitar ciclos)
                        cands = [c for c in cands if c.get("package_id") not in known_ids]
                        p["candidates"] = cands
                        if not cands:
                            p["is_leaf"] = True
            st.session_state[TREE_KEY] = tree
            st.rerun()

        # Mostrar estado de cada paquete
        for p in level_pkgs:
            if p.get("candidates") is None and not p.get("is_leaf"):
                st.markdown(f"&nbsp;&nbsp;&nbsp; \U0001F535 `{p['pkg_name']}` — pendiente de buscar")
            elif p.get("is_leaf"):
                st.markdown(f"&nbsp;&nbsp;&nbsp; \U0001F7E2 `{p['pkg_name']}` — sin orígenes (recepción)")
        return

    # ── Candidatos ya cargados → mostrar para selección ──────
    # Re-check all_leaves
    all_leaves = all(
        p.get("is_leaf") or (isinstance(p.get("candidates"), list) and len(p["candidates"]) == 0)
        for p in level_pkgs
    )
    if all_leaves:
        for p in level_pkgs:
            p["is_leaf"] = True
        st.session_state[TREE_KEY] = tree
        for p in level_pkgs:
            st.markdown(f"&nbsp;&nbsp;&nbsp; \U0001F7E2 `{p['pkg_name']}` — sin orígenes (recepción)")
        return

    # ── Mostrar candidatos agrupados por paquete fuente ──────
    all_selected: List[Dict] = []
    seen_pkg_ids: set = set()

    for p_idx, p in enumerate(level_pkgs):
        if p.get("is_leaf") or not p.get("candidates"):
            if p.get("is_leaf"):
                st.markdown(f"&nbsp;&nbsp;&nbsp; \U0001F7E2 `{p['pkg_name']}` — sin orígenes (recepción)")
            continue

        cands = p["candidates"]
        st.markdown(f"&nbsp;&nbsp;&nbsp; **Orígenes de `{p['pkg_name']}`** — {len(cands)} candidato(s):")

        for c_idx, c in enumerate(cands):
            c_name = c.get("package_name") or str(c.get("package_id"))
            c_id = c.get("package_id")
            c_qty = c.get("qty_total", 0)
            c_prod = c.get("product_name", "")
            c_lot = c.get("lot_name", "")
            c_manejo = c.get("x_manejo") or ""
            c_variedad = c.get("x_variedad") or ""

            cols = st.columns([0.4, 2, 2.5, 1, 1, 1])
            with cols[0]:
                key = f"chk_{level_idx}_{p['pkg_id']}_{c_idx}"
                checked = st.checkbox("", key=key, value=True, label_visibility="collapsed")
            with cols[1]:
                st.markdown(f"**{c_name}**")
            with cols[2]:
                st.caption(c_prod[:50] if c_prod else "—")
            with cols[3]:
                st.caption(f"{c_qty:.1f} kg")
            with cols[4]:
                st.caption(c_manejo or "—")
            with cols[5]:
                st.caption(c_lot or "—")

            if checked and c_id and c_id not in seen_pkg_ids:
                all_selected.append(c)
                seen_pkg_ids.add(c_id)

    # ── Botón confirmar selección ────────────────────────────
    st.markdown("---")
    if not all_selected:
        st.warning("Selecciona al menos un paquete origen para continuar la trazabilidad.")
    else:
        if st.button(
            f"\u2705 Confirmar y avanzar ({len(all_selected)} paquetes seleccionados)",
            key=f"confirm_{level_idx}",
            type="primary",
        ):
            new_level = []
            for s in all_selected:
                s_name = s.get("package_name") or str(s.get("package_id"))
                s_id = s.get("package_id")
                new_level.append(_new_node(
                    s_id, s_name,
                    qty=s.get("qty_total", 0),
                    product_name=s.get("product_name", ""),
                    lot_name=s.get("lot_name", ""),
                ))
            levels.append(new_level)
            st.session_state[TREE_KEY] = tree
            st.rerun()


# ═════════════════════════════════════════════════════════════
# Fase 3 – Resumen y exportar Excel
# ═════════════════════════════════════════════════════════════

def _render_summary_and_export(tree: Dict):
    """Métricas de resumen y botón de descarga Excel."""
    levels = tree["levels"]
    total_pkgs = sum(len(lvl) for lvl in levels)
    leaf_count = sum(
        1 for lvl in levels for p in lvl
        if p.get("is_leaf") or (isinstance(p.get("candidates"), list) and len(p.get("candidates", [])) == 0)
    )
    pending = sum(
        1 for lvl in levels for p in lvl
        if p.get("candidates") is None and not p.get("is_leaf")
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Niveles", len(levels))
    c2.metric("Paquetes", total_pkgs)
    c3.metric("Recepciones", leaf_count)
    c4.metric("Pendientes", pending)

    if pending == 0 and leaf_count > 0:
        st.success("\u2705 Trazabilidad completa — todos los caminos llegan a recepción.")

    # Excel siempre disponible (puede estar parcial)
    excel = _generar_excel_arbol(tree)
    fname = f"Trazabilidad_{tree['root_name']}_{datetime.now():%Y%m%d_%H%M}.xlsx"
    st.download_button(
        "\u2B07\uFE0F Descargar Excel de Trazabilidad",
        data=excel,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


# ═════════════════════════════════════════════════════════════
# Generación Excel – 2 hojas
# ═════════════════════════════════════════════════════════════

def _generar_excel_arbol(tree: Dict) -> bytes:
    """
    Genera Excel con 2 hojas:
      1) Cadena de Trazabilidad – todos los paquetes nivel por nivel
      2) Detalle Candidatos     – candidatos por nivel con marca de selección
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()

    # ── Estilos ──────────────────────────────────────────────
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hdr_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    hdr_font = Font(color="FFFFFF", bold=True, size=11)
    hdr2_fill = PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid")
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_al = Alignment(vertical="center", wrap_text=True)
    root_fill = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
    leaf_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    sel_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

    def _write_header(ws, headers, fill=None):
        f = fill or hdr_fill
        for c, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.fill = f
            cell.font = hdr_font
            cell.alignment = center
            cell.border = border

    def _set_widths(ws, widths):
        for c, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(c)].width = w

    levels = tree.get("levels", [])
    filters = tree.get("filters", {})

    # ══════════════════════════════════════════════════════════
    # HOJA 1 – Cadena de Trazabilidad
    # ══════════════════════════════════════════════════════════
    ws1 = wb.active
    ws1.title = "Cadena de Trazabilidad"

    headers1 = ["Nivel", "Paquete", "Producto", "Cantidad (kg)", "Lote", "Tipo"]
    _write_header(ws1, headers1)
    _set_widths(ws1, [8, 22, 45, 14, 22, 16])

    row = 2
    for level_idx, level_pkgs in enumerate(levels):
        for p in level_pkgs:
            is_leaf = p.get("is_leaf") or (
                isinstance(p.get("candidates"), list) and len(p.get("candidates", [])) == 0
            )
            if level_idx == 0:
                tipo = "Destino"
            elif is_leaf:
                tipo = "Recepción"
            else:
                tipo = "Intermedio"

            ws1.cell(row=row, column=1, value=level_idx)
            ws1.cell(row=row, column=2, value=p.get("pkg_name", "")).font = Font(bold=True)
            prod_name = p.get("product_name", "") or (filters.get("product_name") if level_idx == 0 else "")
            ws1.cell(row=row, column=3, value=prod_name or "")
            qty = p.get("qty")
            ws1.cell(row=row, column=4, value=f"{qty:.1f}" if qty else "")
            ws1.cell(row=row, column=5, value=p.get("lot_name", ""))
            ws1.cell(row=row, column=6, value=tipo)

            for c in range(1, 7):
                cell = ws1.cell(row=row, column=c)
                cell.border = border
                cell.alignment = center if c in (1, 4, 6) else left_al

            # Color por tipo
            if level_idx == 0:
                for c in range(1, 7):
                    ws1.cell(row=row, column=c).fill = root_fill
            elif is_leaf:
                for c in range(1, 7):
                    ws1.cell(row=row, column=c).fill = leaf_fill

            row += 1

    ws1.freeze_panes = "A2"

    # ══════════════════════════════════════════════════════════
    # HOJA 2 – Detalle Candidatos
    # ══════════════════════════════════════════════════════════
    ws2 = wb.create_sheet("Detalle Candidatos")

    headers2 = ["Nivel", "Paquete Destino", "Candidato Origen", "Producto",
                 "Cantidad (kg)", "Lote", "Seleccionado"]
    _write_header(ws2, headers2, fill=hdr2_fill)
    _set_widths(ws2, [8, 22, 22, 45, 14, 22, 14])

    row2 = 2
    for level_idx, level_pkgs in enumerate(levels):
        # Nombres del nivel siguiente para saber cuáles se seleccionaron
        next_names: set = set()
        if level_idx + 1 < len(levels):
            next_names = {p["pkg_name"] for p in levels[level_idx + 1]}

        for p in level_pkgs:
            cands = p.get("candidates") or []
            for c in cands:
                c_name = c.get("package_name") or str(c.get("package_id"))
                selected = "Sí" if c_name in next_names else "No"

                ws2.cell(row=row2, column=1, value=level_idx)
                ws2.cell(row=row2, column=2, value=p.get("pkg_name", ""))
                ws2.cell(row=row2, column=3, value=c_name)
                ws2.cell(row=row2, column=4, value=c.get("product_name", ""))
                qty = c.get("qty_total", 0)
                ws2.cell(row=row2, column=5, value=f"{qty:.1f}" if qty else "")
                ws2.cell(row=row2, column=6, value=c.get("lot_name", ""))
                ws2.cell(row=row2, column=7, value=selected)

                for col in range(1, 8):
                    cell = ws2.cell(row=row2, column=col)
                    cell.border = border
                    cell.alignment = center if col in (1, 5, 7) else left_al

                if selected == "Sí":
                    for col in range(1, 8):
                        ws2.cell(row=row2, column=col).fill = sel_fill

                row2 += 1

    ws2.freeze_panes = "A2"

    # ── Guardar ──────────────────────────────────────────────
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()

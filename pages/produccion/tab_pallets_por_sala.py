"""
Tab: Pallets por Sala
Muestra una vista detallada de pallets de producto terminado filtrados por sala de proceso,
producto, fecha, manejo y tipo de fruta. Solo temporada 2025 y 2026.
Incluye enlace con datos de Control de Calidad desde Excel.
"""
import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .shared import API_URL, fmt_numero


# --- Constantes del módulo ---
SALA_MAP_INTERNAL = {
    "Sala 1 - Línea Retail": "Sala 1 - Linea Retail",
    "Sala 2 - Línea Granel": "Sala 2 - Linea Granel",
    "Sala 3 - Línea Granel": "Sala 3 - Linea Granel",
    "Sala 3 - Línea Retail": "Sala 3 - Linea Retail",
    "Sala 4 - Línea Retail": "Sala 4 - Linea Retail",
    "Sala 4 - Línea Chocolate": "Sala 4 - Linea Chocolate",
    "Sala - Vilkun": "Sala - Vilkun"
}

GRADO_NOMBRES = {
    '1': 'IQF AA', '2': 'IQF A', '3': 'PSP', '4': 'W&B',
    '5': 'Block', '6': 'Jugo', '7': 'IQF Retail'
}

GRADO_COLORES = {
    'IQF AA': '#FFB302', 'IQF A': '#2196F3', 'PSP': '#9C27B0',
    'W&B': '#795548', 'Block': '#00BCD4', 'Jugo': '#FF5722', 'IQF Retail': '#4CAF50'
}

TEMPORADAS_VALIDAS = ["2025", "2026"]

# Columnas de calidad del Excel (fila 2 = headers, mapeadas en orden)
QUALITY_COLS = [
    'fecha_qc', 'semana', 'turno', 'sala_qc', 'codigo_qc', 'descripcion_producto',
    'familia_calidad', 'n_pallet', 'n_lote', 'muestra', 'hora_monitoreo',
    'peso_bolsa', 'peso_caja', 'temperatura', 'sellado_bolsa', 'sellado_caja',
    'pct_iqf', 'inmadura', 'pct_inmadura', 'partidas', 'pct_partidas',
    'dano_insecto', 'pct_dano_insecto', 'sobremadura', 'pct_sobremadura',
    'deforme', 'pct_deforme', 'desc_extra_1', 'valor_extra_1', 'pct_extra_1',
    'desc_extra_2', 'valor_extra_2', 'pct_extra_2',
    'hongos', 'pct_hongos', 'block', 'pct_block',
    'caliz_und', 'larvas_und',
    'fuera_calibre_menor', 'pct_fuera_calibre_menor',
    'calibre_menor_25', 'pct_menor_25', 'calibre_mayor_12', 'pct_mayor_12',
    'calibre_menor_14', 'pct_menor_14', 'calibre_mayor_14', 'pct_mayor_14',
    'calibre_menor_10', 'pct_menor_10', 'calibre_mayor_13', 'pct_mayor_13',
    'hoja_un', 'pedicelo_caja', 'larvas_caja', 'vidrios', 'madera', 'plastico',
    'brix', 'sabor', 'olor', 'defectos_totales', 'pct_defectos',
    'observaciones', 'pct_iqf2', 'analista',
    'mat_extr_endo', 'mat_extr_exo', 'filtro_producto', 'filtro_lote', 'filtro_pallet'
]

# Columnas principales para tabla interactiva de QC
QUALITY_DISPLAY_COLS = {
    'hora_monitoreo': 'Hora',
    'peso_caja': 'Peso Caja',
    'temperatura': 'Temp',
    'sellado_bolsa': 'Sell.B',
    'sellado_caja': 'Sell.C',
    'pct_iqf': '% IQF',
    'pct_inmadura': '% Inmad.',
    'pct_partidas': '% Partid.',
    'pct_dano_insecto': '% D.Insecto',
    'pct_sobremadura': '% Sobrem.',
    'pct_deforme': '% Deforme',
    'pct_hongos': '% Hongos',
    'pct_defectos': '% Defectos',
    'brix': 'Brix',
    'observaciones': 'Obs.',
}


def _normalize(text: str) -> str:
    """Normaliza texto removiendo acentos para comparaciones."""
    if not text:
        return ""
    text = text.lower()
    for old, new in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]:
        text = text.replace(old, new)
    return text


def _extraer_numero_pallet(pallet_name: str) -> str:
    """Extrae el número puro del nombre de pallet. PACK0013712 -> 13712"""
    if not pallet_name:
        return ""
    num = re.sub(r'^PACK0*', '', str(pallet_name), flags=re.IGNORECASE)
    return num.strip()


def _fmt_pct(val):
    """Formatea un valor de porcentaje del Excel."""
    if val is None or val == '' or val == 0:
        return ''
    try:
        v = float(val)
        return round(v * 100, 2) if v <= 1 else round(v, 2)
    except (ValueError, TypeError):
        return val


def _parsear_excel_calidad(uploaded_file) -> Dict[str, List[Dict]]:
    """
    Parsea un Excel de control de calidad.
    Retorna: { "13712": [registro1, ...], "13713": [...] }
    Lee hojas con "base de datos" o "b.d." en el nombre.
    Headers en fila 2, datos desde fila 3.
    """
    import openpyxl

    calidad_por_pallet: Dict[str, List[Dict]] = {}

    try:
        wb = openpyxl.load_workbook(uploaded_file, data_only=True)
    except Exception as e:
        st.error(f"Error al leer Excel de calidad: {e}")
        return {}

    hojas_calidad = [
        n for n in wb.sheetnames
        if 'base de datos' in n.lower() or 'b.d.' in n.lower()
    ]

    for nombre_hoja in hojas_calidad:
        ws = wb[nombre_hoja]
        planta_origen = "RIO FUTURO" if "r.f." in nombre_hoja.lower() else "VILKUN"

        for row_idx in range(3, ws.max_row + 1):
            pallet_val = ws.cell(row=row_idx, column=8).value
            if not pallet_val:
                continue

            pallet_num = str(int(pallet_val)) if isinstance(pallet_val, (int, float)) else str(pallet_val).strip()
            if not pallet_num or pallet_num == '0':
                continue

            registro = {'planta_qc': planta_origen, 'hoja_origen': nombre_hoja}
            for col_idx in range(1, min(ws.max_column + 1, len(QUALITY_COLS) + 1)):
                col_name = QUALITY_COLS[col_idx - 1] if col_idx - 1 < len(QUALITY_COLS) else f'col_{col_idx}'
                registro[col_name] = ws.cell(row=row_idx, column=col_idx).value

            calidad_por_pallet.setdefault(pallet_num, []).append(registro)

    return calidad_por_pallet


def _render_calidad_pallet(registros_calidad: List[Dict], pallet_name: str):
    """Renderiza los datos de calidad de un pallet de forma visual e interactiva."""
    n = len(registros_calidad)

    # Calcular promedios
    pcts_iqf = [float(r.get('pct_iqf', 0) or 0) for r in registros_calidad if r.get('pct_iqf')]
    pcts_defectos = [float(r.get('pct_defectos', 0) or 0) for r in registros_calidad if r.get('pct_defectos')]
    temps = []
    for r in registros_calidad:
        t = r.get('temperatura')
        if t and str(t).strip() not in ('', 'N/A'):
            try:
                temps.append(float(t))
            except (ValueError, TypeError):
                pass

    avg_iqf = sum(pcts_iqf) / len(pcts_iqf) * 100 if pcts_iqf else None
    avg_defectos = sum(pcts_defectos) / len(pcts_defectos) * 100 if pcts_defectos else None
    avg_temp = sum(temps) / len(temps) if temps else None

    # Determinar estado de calidad
    if avg_defectos is not None:
        if avg_defectos <= 4:
            estado_color, estado_icon, estado_text = "#22c55e", "✅", "APROBADO"
        elif avg_defectos <= 7:
            estado_color, estado_icon, estado_text = "#f59e0b", "⚠️", "OBSERVADO"
        else:
            estado_color, estado_icon, estado_text = "#ef4444", "❌", "RECHAZADO"
    else:
        estado_color, estado_icon, estado_text = "#64748b", "❓", "SIN EVALUAR"

    # Header con estado
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{estado_color}22 0%,{estado_color}11 100%);
        border-left:4px solid {estado_color}; border-radius:8px; padding:0.8rem 1rem; margin-bottom:0.8rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-weight:700; color:{estado_color}; font-size:1rem;">
                {estado_icon} Control de Calidad — {estado_text}
            </span>
            <span style="color:#94a3b8; font-size:0.8rem;">{n} monitoreo{'s' if n > 1 else ''}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KPIs de calidad
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        iqf_val = f"{avg_iqf:.1f}%" if avg_iqf is not None else "—"
        iqf_color = "#22c55e" if avg_iqf and avg_iqf >= 90 else ("#f59e0b" if avg_iqf and avg_iqf >= 80 else "#ef4444")
        st.markdown(f"""<div style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:0.6rem; text-align:center;">
            <div style="font-size:0.65rem; color:#94a3b8; text-transform:uppercase;">% IQF Prom.</div>
            <div style="font-size:1.2rem; font-weight:800; color:{iqf_color};">{iqf_val}</div>
        </div>""", unsafe_allow_html=True)
    with kpi_cols[1]:
        def_val = f"{avg_defectos:.1f}%" if avg_defectos is not None else "—"
        def_color = "#22c55e" if avg_defectos is not None and avg_defectos <= 4 else ("#f59e0b" if avg_defectos is not None and avg_defectos <= 7 else "#ef4444")
        st.markdown(f"""<div style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:0.6rem; text-align:center;">
            <div style="font-size:0.65rem; color:#94a3b8; text-transform:uppercase;">% Defectos Prom.</div>
            <div style="font-size:1.2rem; font-weight:800; color:{def_color};">{def_val}</div>
        </div>""", unsafe_allow_html=True)
    with kpi_cols[2]:
        temp_val = f"{avg_temp:.1f}&deg;C" if avg_temp is not None else "—"
        temp_color = "#22c55e" if avg_temp is not None and avg_temp <= -5 else ("#f59e0b" if avg_temp is not None and avg_temp <= 0 else "#ef4444")
        st.markdown(f"""<div style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:0.6rem; text-align:center;">
            <div style="font-size:0.65rem; color:#94a3b8; text-transform:uppercase;">Temp. Prom.</div>
            <div style="font-size:1.2rem; font-weight:800; color:{temp_color};">{temp_val}</div>
        </div>""", unsafe_allow_html=True)
    with kpi_cols[3]:
        sellados_b = [str(r.get('sellado_bolsa', '')).upper() for r in registros_calidad if r.get('sellado_bolsa')]
        sellados_c = [str(r.get('sellado_caja', '')).upper() for r in registros_calidad if r.get('sellado_caja')]
        todo_ok = all(s == 'C' for s in sellados_b + sellados_c) if (sellados_b or sellados_c) else None
        sell_icon = "✅" if todo_ok else ("❌" if todo_ok is not None else "—")
        sell_color = "#22c55e" if todo_ok else ("#ef4444" if todo_ok is not None else "#64748b")
        st.markdown(f"""<div style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:0.6rem; text-align:center;">
            <div style="font-size:0.65rem; color:#94a3b8; text-transform:uppercase;">Sellado</div>
            <div style="font-size:1.2rem; font-weight:800; color:{sell_color};">{sell_icon}</div>
        </div>""", unsafe_allow_html=True)

    # Tabla de detalle por monitoreo
    rows = []
    for r in registros_calidad:
        row = {}
        for col_key, col_label in QUALITY_DISPLAY_COLS.items():
            val = r.get(col_key, '')
            if val is None:
                val = ''
            if col_key.startswith('pct_') and val != '':
                try:
                    val = f"{float(val) * 100:.1f}%" if float(val) <= 1 else f"{float(val):.1f}%"
                except (ValueError, TypeError):
                    pass
            elif col_key == 'temperatura' and val != '':
                try:
                    val = f"{float(val):.1f}"
                except (ValueError, TypeError):
                    pass
            elif col_key == 'hora_monitoreo':
                val = str(val)[:8] if val else ''
            row[col_label] = val
        rows.append(row)

    df_qc = pd.DataFrame(rows)
    st.dataframe(df_qc, use_container_width=True, hide_index=True, height=min(200, 35 * len(rows) + 38))

    # Desglose de defectos (barras visuales)
    defectos = {}
    defecto_keys = [
        ('pct_inmadura', 'Inmadura'), ('pct_partidas', 'Partidas'),
        ('pct_dano_insecto', 'D. Insecto'), ('pct_sobremadura', 'Sobremadura'),
        ('pct_deforme', 'Deforme'), ('pct_hongos', 'Hongos'), ('pct_block', 'Block'),
    ]
    for key, label in defecto_keys:
        vals = [float(r.get(key, 0) or 0) for r in registros_calidad if r.get(key)]
        if vals:
            avg = sum(vals) / len(vals) * 100
            if avg > 0:
                defectos[label] = round(avg, 2)

    if defectos:
        max_val = max(defectos.values()) if defectos else 1
        bars_html = ""
        for label, val in sorted(defectos.items(), key=lambda x: x[1], reverse=True):
            width_pct = min(val / max_val * 100, 100) if max_val > 0 else 0
            bar_color = "#ef4444" if val > 4 else ("#f59e0b" if val > 2 else "#22c55e")
            bars_html += (
                '<div style="display:flex;align-items:center;margin:3px 0;gap:8px;">'
                f'<span style="width:100px;font-size:0.75rem;color:#94a3b8;text-align:right;">{label}</span>'
                '<div style="flex:1;background:#1e293b;border-radius:4px;height:18px;overflow:hidden;">'
                f'<div style="width:{width_pct}%;background:{bar_color};height:100%;border-radius:4px;min-width:2px;"></div>'
                '</div>'
                f'<span style="width:50px;font-size:0.75rem;color:#e2e8f0;font-weight:600;">{val:.1f}%</span>'
                '</div>'
            )

        html_block = (
            '<div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:0.8rem;margin-top:0.5rem;">'
            '<div style="font-size:0.7rem;color:#64748b;margin-bottom:6px;text-transform:uppercase;font-weight:600;">Desglose de Defectos (Promedio)</div>'
            f'{bars_html}'
            '</div>'
        )
        st.markdown(html_block, unsafe_allow_html=True)


def _generar_excel_con_calidad(df_display, calidad_dict):
    """Genera un Excel con 3 hojas: Pallets, Calidad (detalle QC), Resumen QC."""
    import io
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # --- HOJA 1: PALLETS ---
        df_display.to_excel(writer, index=False, sheet_name='Pallets')

        # --- HOJA 2: CALIDAD (registros QC enlazados) ---
        qc_rows = []
        for _, row in df_display.iterrows():
            pallet_name = row.get('Pallet', '')
            pallet_num = _extraer_numero_pallet(pallet_name)
            registros = calidad_dict.get(pallet_num, [])
            for r in registros:
                qc_rows.append({
                    'Pallet': pallet_name,
                    'Producto': row.get('Producto', ''),
                    'Grado': row.get('Grado', ''),
                    'Kilos': row.get('Kilos', 0),
                    'OF': row.get('OF', ''),
                    'Sala': row.get('Sala', ''),
                    'Fecha QC': str(r.get('fecha_qc', ''))[:10] if r.get('fecha_qc') else '',
                    'Hora': str(r.get('hora_monitoreo', ''))[:8] if r.get('hora_monitoreo') else '',
                    'Turno': r.get('turno', ''),
                    'Peso Caja': r.get('peso_caja', ''),
                    'Temperatura': r.get('temperatura', ''),
                    'Sellado Bolsa': r.get('sellado_bolsa', ''),
                    'Sellado Caja': r.get('sellado_caja', ''),
                    '% IQF': _fmt_pct(r.get('pct_iqf')),
                    '% Inmadura': _fmt_pct(r.get('pct_inmadura')),
                    '% Partidas': _fmt_pct(r.get('pct_partidas')),
                    '% D. Insecto': _fmt_pct(r.get('pct_dano_insecto')),
                    '% Sobremadura': _fmt_pct(r.get('pct_sobremadura')),
                    '% Deforme': _fmt_pct(r.get('pct_deforme')),
                    '% Hongos': _fmt_pct(r.get('pct_hongos')),
                    '% Block': _fmt_pct(r.get('pct_block')),
                    'Defectos Tot.': r.get('defectos_totales', ''),
                    '% Defectos': _fmt_pct(r.get('pct_defectos')),
                    'Brix': r.get('brix', ''),
                    'Observaciones': r.get('observaciones', ''),
                    'Analista': r.get('analista', ''),
                })

        if qc_rows:
            pd.DataFrame(qc_rows).to_excel(writer, index=False, sheet_name='Calidad')

        # --- HOJA 3: RESUMEN QC POR PALLET ---
        resumen_rows = []
        for _, row in df_display.iterrows():
            pallet_name = row.get('Pallet', '')
            pallet_num = _extraer_numero_pallet(pallet_name)
            registros = calidad_dict.get(pallet_num, [])
            base = {
                'Pallet': pallet_name,
                'Producto': row.get('Producto', ''),
                'Grado': row.get('Grado', ''),
                'Kilos': row.get('Kilos', 0),
                'Sala': row.get('Sala', ''),
            }
            if registros:
                pi = [float(r.get('pct_iqf', 0) or 0) for r in registros if r.get('pct_iqf')]
                pd2 = [float(r.get('pct_defectos', 0) or 0) for r in registros if r.get('pct_defectos')]
                tl = []
                for r in registros:
                    t = r.get('temperatura')
                    if t and str(t).strip() not in ('', 'N/A'):
                        try:
                            tl.append(float(t))
                        except (ValueError, TypeError):
                            pass
                ai = sum(pi) / len(pi) * 100 if pi else None
                ad = sum(pd2) / len(pd2) * 100 if pd2 else None
                at = sum(tl) / len(tl) if tl else None
                estado = "APROBADO" if ad is not None and ad <= 4 else ("OBSERVADO" if ad is not None and ad <= 7 else ("RECHAZADO" if ad is not None else "SIN EVALUAR"))
                base.update({
                    'N Monitoreos': len(registros),
                    '% IQF Prom.': round(ai, 1) if ai is not None else '',
                    '% Defectos Prom.': round(ad, 1) if ad is not None else '',
                    'Temp. Prom.': round(at, 1) if at is not None else '',
                    'Estado': estado,
                })
            else:
                base.update({'N Monitoreos': 0, '% IQF Prom.': '', '% Defectos Prom.': '', 'Temp. Prom.': '', 'Estado': 'SIN DATOS QC'})
            resumen_rows.append(base)

        pd.DataFrame(resumen_rows).to_excel(writer, index=False, sheet_name='Resumen QC')

        # --- ESTILOS ---
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style='thin', color='D0D0D0'), right=Side(style='thin', color='D0D0D0'),
            top=Side(style='thin', color='D0D0D0'), bottom=Side(style='thin', color='D0D0D0'),
        )
        fills = {
            'Pallets': PatternFill(start_color="1F3A5F", end_color="1F3A5F", fill_type="solid"),
            'Calidad': PatternFill(start_color="1a5f3a", end_color="1a5f3a", fill_type="solid"),
            'Resumen QC': PatternFill(start_color="5f1a3a", end_color="5f1a3a", fill_type="solid"),
        }

        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            fill = fills.get(sheet_name, fills['Pallets'])
            ws.auto_filter.ref = ws.dimensions
            ws.freeze_panes = "A2"
            for ci in range(1, ws.max_column + 1):
                cell = ws.cell(row=1, column=ci)
                cell.font = header_font
                cell.fill = fill
                cell.alignment = header_align
                cell.border = thin_border
            for ri in range(2, ws.max_row + 1):
                for ci in range(1, ws.max_column + 1):
                    ws.cell(row=ri, column=ci).border = thin_border
            for ci in range(1, ws.max_column + 1):
                cl = get_column_letter(ci)
                mx = len(str(ws.cell(row=1, column=ci).value or ""))
                for ri in range(2, min(ws.max_row + 1, 200)):
                    v = ws.cell(row=ri, column=ci).value
                    if v:
                        mx = max(mx, len(str(v)))
                ws.column_dimensions[cl].width = min(mx + 3, 45)

        # Colorear estados en Resumen QC
        if 'Resumen QC' in writer.sheets:
            ws_r = writer.sheets['Resumen QC']
            estado_col = None
            for ci in range(1, ws_r.max_column + 1):
                if ws_r.cell(row=1, column=ci).value == 'Estado':
                    estado_col = ci
                    break
            if estado_col:
                state_fills = {
                    'APROBADO': (PatternFill(start_color="C6EFCE", fill_type="solid"), Font(bold=True, color="006100")),
                    'OBSERVADO': (PatternFill(start_color="FFEB9C", fill_type="solid"), Font(bold=True, color="9C6500")),
                    'RECHAZADO': (PatternFill(start_color="FFC7CE", fill_type="solid"), Font(bold=True, color="9C0006")),
                }
                gray = (PatternFill(start_color="D9D9D9", fill_type="solid"), Font(bold=False, color="333333"))
                for ri in range(2, ws_r.max_row + 1):
                    cell = ws_r.cell(row=ri, column=estado_col)
                    val = str(cell.value or '').upper()
                    f, fo = gray
                    for key, (sf, sfo) in state_fills.items():
                        if key in val:
                            f, fo = sf, sfo
                            break
                    cell.fill = f
                    cell.font = fo

    return buffer.getvalue()


def _filtrar_detalle(detalle_raw, filtros):
    """Aplica filtros dinámicos sobre la lista de detalle en memoria."""
    resultado = list(detalle_raw)

    # Filtrar por Planta
    if filtros.get("planta") and filtros["planta"] != "Todas":
        planta_val = filtros["planta"].upper()
        resultado = [d for d in resultado if d.get('planta', '').upper() == planta_val]

    # Filtrar por Fruta (usando primeros 2 dígitos del código de producto)
    if filtros.get("tipo_fruta") and filtros["tipo_fruta"] != "Todas":
        fruta_lower = _normalize(filtros["tipo_fruta"])
        FRUTA_CODE_MAP = {
            'arandano': ['31', '41'],
            'frambuesa': ['32', '42'],
            'frutilla': ['33', '43'],
            'mora': ['34', '44'],
        }
        codes_esperados = FRUTA_CODE_MAP.get(fruta_lower, [])
        filtered = []
        for d in resultado:
            code = d.get('codigo_producto', '')
            if codes_esperados and len(code) >= 2 and code[:2] in codes_esperados:
                filtered.append(d)
            elif fruta_lower in _normalize(d.get('producto', '')):
                filtered.append(d)
        resultado = filtered

    # Filtrar por Sala de Proceso (normalizado, tolerante a acentos y variaciones)
    if filtros.get("sala") and filtros["sala"] != "Todas":
        target_key = SALA_MAP_INTERNAL.get(filtros["sala"], filtros["sala"])
        target_norm = _normalize(target_key)
        # Extraer solo la parte clave para matching parcial: "sala 1", "sala 2", etc.
        target_parts = target_norm.split(" - ")
        filtered = []
        for d in resultado:
            sala_dato = _normalize(d.get('sala', ''))
            if not sala_dato:
                continue
            # Match exacto normalizado
            if sala_dato == target_norm:
                filtered.append(d)
            # Match parcial: ambas partes del target deben estar presentes
            elif all(part.strip() in sala_dato for part in target_parts):
                filtered.append(d)
            # Match solo por sala base (ej: "sala 1")
            elif target_parts[0].strip() in sala_dato and (len(target_parts) < 2 or target_parts[1].strip() in sala_dato):
                filtered.append(d)
        resultado = filtered

    # Filtrar por Manejo (usando dígito 4 del código de producto)
    if filtros.get("tipo_manejo") and filtros["tipo_manejo"] != "Todos":
        manejo = filtros["tipo_manejo"]
        filtered = []
        for d in resultado:
            code = d.get('codigo_producto', '')
            if len(code) >= 4:
                m_digit = code[3]
                if manejo == "Orgánico" and m_digit == '2':
                    filtered.append(d)
                elif manejo == "Convencional" and m_digit == '1':
                    filtered.append(d)
        resultado = filtered

    # Filtrar por productos seleccionados (multiselect)
    if filtros.get("productos_seleccionados"):
        # Extraer códigos de las opciones seleccionadas (formato "código — nombre")
        codigos_sel = set()
        for opt in filtros["productos_seleccionados"]:
            code = opt.split(" — ")[0].strip() if " — " in opt else opt.strip()
            codigos_sel.add(code)
        resultado = [d for d in resultado if d.get('codigo_producto', '') in codigos_sel]

    # Filtrar por texto libre (pallet, OF, lote, producto, código)
    if filtros.get("producto_texto"):
        texto = _normalize(filtros["producto_texto"].strip())
        resultado = [
            d for d in resultado
            if texto in _normalize(d.get('producto', ''))
            or texto in d.get('codigo_producto', '').lower()
            or texto in _normalize(d.get('pallet', ''))
            or texto in _normalize(d.get('orden_fabricacion', ''))
            or texto in _normalize(d.get('lote', ''))
        ]

    # Filtrar por Temporada 2025/2026 basado en fecha
    resultado_temp = []
    for d in resultado:
        fecha = d.get('fecha', '')
        if fecha:
            # Extraer año: soporta "2025-01-15", "2025-01-15 10:00:00", etc.
            year = str(fecha)[:4]
            if year in TEMPORADAS_VALIDAS:
                resultado_temp.append(d)
        else:
            # Si no tiene fecha, incluirlo (no descartar datos válidos)
            resultado_temp.append(d)
    resultado = resultado_temp

    return resultado


@st.fragment
def render(username: str, password: str):
    """Renderiza el tab de Pallets por Sala."""

    st.markdown("### 🏢 PALLETS POR SALA DE PROCESO")
    st.caption("Detalle de pallets de producto terminado por sala, producto y grado — Temporada 2025 / 2026")

    # === UPLOAD DE CALIDAD ===
    with st.expander("📊 **Cargar Excel de Control de Calidad** (opcional)", expanded=False):
        st.caption("Sube el Excel de calidad para enlazar análisis a cada pallet. "
                   "Se aceptan archivos con hojas 'Base de Datos (R.F.)' y/o 'B.D.(Frío Food)'.")
        uploaded_file = st.file_uploader(
            "Seleccionar Excel de Calidad",
            type=['xlsx', 'xls'],
            key="ps_calidad_upload",
            label_visibility="collapsed"
        )
        if uploaded_file:
            with st.spinner("📊 Procesando datos de calidad..."):
                calidad_dict = _parsear_excel_calidad(uploaded_file)
                st.session_state.ps_calidad_dict = calidad_dict
                total_pallets_qc = len(calidad_dict)
                total_registros_qc = sum(len(v) for v in calidad_dict.values())
                st.success(f"✅ Se cargaron **{total_registros_qc}** monitoreos para **{total_pallets_qc}** pallets")

        if st.session_state.get('ps_calidad_dict'):
            cd = st.session_state.ps_calidad_dict
            st.info(f"📋 Datos de calidad activos: {sum(len(v) for v in cd.values())} monitoreos / {len(cd)} pallets")

    calidad_dict = st.session_state.get('ps_calidad_dict', {})

    # === FILTROS ===
    with st.container():
        col1, col2 = st.columns(2)

        with col1:
            fecha_inicio = st.date_input(
                "Fecha Inicio",
                value=datetime(2025, 1, 1),
                key="ps_fecha_inicio"
            )

            tipo_fruta_opciones = ["Todas", "Arándano", "Frambuesa", "Frutilla", "Mora"]
            tipo_fruta = st.selectbox(
                "Tipo de Fruta",
                options=tipo_fruta_opciones,
                index=0,
                key="ps_tipo_fruta"
            )

        with col2:
            fecha_fin = st.date_input(
                "Fecha Fin",
                value=datetime.now(),
                key="ps_fecha_fin"
            )

            tipo_manejo_opciones = ["Todos", "Orgánico", "Convencional"]
            tipo_manejo = st.selectbox(
                "Tipo de Manejo",
                options=tipo_manejo_opciones,
                index=0,
                key="ps_tipo_manejo"
            )

        col3, col4 = st.columns(2)

        with col3:
            sala_opciones = ["Todas"] + list(SALA_MAP_INTERNAL.keys())
            sala_seleccionada = st.selectbox(
                "🏢 Sala de Proceso",
                options=sala_opciones,
                index=0,
                key="ps_sala",
                help="Sala donde se procesó el pallet"
            )

        with col4:
            planta_opciones = ["Todas", "VILKUN", "RIO FUTURO"]
            planta_seleccionada = st.selectbox(
                "🏭 Planta / Operación",
                options=planta_opciones,
                index=0,
                key="ps_planta"
            )

        # Filtro de productos (multiselect dinámico)
        cached_data = st.session_state.get("ps_pallets_data")
        if cached_data and cached_data.get('detalle'):
            # Extraer productos únicos del cache: "código — nombre"
            productos_unicos = {}
            for d in cached_data['detalle']:
                code = d.get('codigo_producto', '')
                name = d.get('producto', '')
                if code and code not in productos_unicos:
                    productos_unicos[code] = f"{code} — {name}"
            opciones_productos = sorted(productos_unicos.values())
        else:
            opciones_productos = []

        productos_seleccionados = st.multiselect(
            "📦 Filtrar por Producto (escribí código o nombre)",
            options=opciones_productos,
            default=[],
            key="ps_productos_sel",
            placeholder="Buscar producto... (podés seleccionar varios)",
        )

        # Búsqueda libre adicional (pallet, OF, lote)
        producto_texto = st.text_input(
            "🔎 Buscar pallet, OF o lote",
            value="",
            key="ps_producto_texto",
            placeholder="Ej: PACK0013713, WPF/00123..."
        )

        consultar = st.button("🔍 Consultar Pallets", use_container_width=True, type="primary", key="ps_btn_consultar")

    # === CSS ===
    st.markdown("""
    <style>
        .kpi-mini {
            background: #1e293b;
            padding: 0.8rem;
            border-radius: 10px;
            text-align: center;
            border: 1px solid #334155;
        }
        .kpi-mini .value { font-size: 1.3rem; font-weight: 800; color: #ffffff; }
        .kpi-mini .label { font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

    # === CONSULTA ===
    if consultar or st.session_state.get("ps_pallets_data"):
        if consultar:
            fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
            fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")

            # Todos los filtros de fruta, manejo y sala se aplican en memoria
            # para evitar problemas de acentos/encoding con Odoo ilike

            with st.spinner("⏳ Consultando pallets por sala..."):
                try:
                    params = {
                        "username": username,
                        "password": password,
                        "fecha_inicio": fecha_inicio_str,
                        "fecha_fin": fecha_fin_str,
                        "tipo_operacion": planta_seleccionada
                    }

                    response = requests.get(
                        f"{API_URL}/api/v1/produccion/clasificacion",
                        params=params,
                        timeout=120
                    )

                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.ps_pallets_data = data
                        count = len(data.get('detalle', []))
                        if count > 0:
                            st.success(f"✅ Se cargaron {count} pallets correctamente")
                        else:
                            st.info("ℹ️ No se encontraron pallets para los filtros seleccionados.")
                    else:
                        st.error(f"❌ Error al obtener datos: {response.status_code}")
                        return

                except Exception as e:
                    st.error(f"❌ Error en la consulta: {str(e)}")
                    return

        # --- Procesar datos ---
        data = st.session_state.get("ps_pallets_data")
        if not data:
            st.info("👆 Consulta los datos primero.")
            return

        detalle_raw = data.get('detalle', [])

        # Aplicar filtros en memoria
        filtros = {
            "planta": planta_seleccionada,
            "tipo_fruta": tipo_fruta,
            "sala": sala_seleccionada,
            "tipo_manejo": tipo_manejo,
            "productos_seleccionados": productos_seleccionados,
            "producto_texto": producto_texto,
        }
        detalle_filtrado = _filtrar_detalle(detalle_raw, filtros)

        if not detalle_filtrado:
            st.warning("⚠️ No hay pallets con los filtros seleccionados (solo temporada 2025/2026, producto terminado).")
            return

        # Convertir a DataFrame
        df = pd.DataFrame(detalle_filtrado)

        # --- KPIs GENERALES ---
        total_pallets = df['pallet'].nunique()
        total_kg = df['kg'].sum()
        total_productos = df['producto'].nunique()
        salas_activas = df['sala'].nunique()

        # Contar pallets con calidad
        pallets_con_qc = 0
        if calidad_dict:
            for pname in df['pallet'].unique():
                if _extraer_numero_pallet(pname) in calidad_dict:
                    pallets_con_qc += 1

        st.markdown("---")
        n_kpi = 5 if calidad_dict else 4
        kpi_cols = st.columns(n_kpi)
        with kpi_cols[0]:
            st.markdown(f"""
            <div class="kpi-mini">
                <div class="label">📦 Pallets Únicos</div>
                <div class="value">{fmt_numero(total_pallets)}</div>
            </div>""", unsafe_allow_html=True)
        with kpi_cols[1]:
            st.markdown(f"""
            <div class="kpi-mini">
                <div class="label">⚖️ Total Kilogramos</div>
                <div class="value">{fmt_numero(total_kg)}</div>
            </div>""", unsafe_allow_html=True)
        with kpi_cols[2]:
            st.markdown(f"""
            <div class="kpi-mini">
                <div class="label">🍇 Productos</div>
                <div class="value">{fmt_numero(total_productos)}</div>
            </div>""", unsafe_allow_html=True)
        with kpi_cols[3]:
            st.markdown(f"""
            <div class="kpi-mini">
                <div class="label">🏢 Salas Activas</div>
                <div class="value">{fmt_numero(salas_activas)}</div>
            </div>""", unsafe_allow_html=True)
        if calidad_dict:
            pct_qc = round(pallets_con_qc / total_pallets * 100) if total_pallets > 0 else 0
            qc_color = "#22c55e" if pct_qc >= 80 else ("#f59e0b" if pct_qc >= 50 else "#ef4444")
            with kpi_cols[4]:
                st.markdown(f"""
                <div class="kpi-mini" style="border-color:{qc_color};">
                    <div class="label">🔬 Con Calidad</div>
                    <div class="value" style="color:{qc_color};">{pallets_con_qc}/{total_pallets}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # --- RESUMEN POR SALA ---
        st.markdown("#### 🏢 Resumen por Sala de Proceso")

        # Agrupar pallets por sala
        salas_unicas = sorted(df['sala'].unique(), key=lambda x: x if x else "ZZZ")

        for sala in salas_unicas:
            sala_label = sala if sala else "Sin Sala"
            df_sala = df[df['sala'] == sala]

            kg_sala = df_sala['kg'].sum()
            pallets_sala = df_sala['pallet'].nunique()
            productos_sala = df_sala['producto'].nunique()

            # Contar QC en esta sala
            qc_badge = ""
            if calidad_dict:
                sala_con_qc = sum(1 for p in df_sala['pallet'].unique() if _extraer_numero_pallet(p) in calidad_dict)
                if sala_con_qc > 0:
                    qc_badge = f" | 🔬 {sala_con_qc} con QC"

            # Desglose por grado
            grado_resumen = df_sala.groupby('grado')['kg'].sum().sort_values(ascending=False)

            with st.expander(f"🏢 **{sala_label}** — {fmt_numero(kg_sala)} kg | {pallets_sala} pallets | {productos_sala} productos{qc_badge}", expanded=False):

                # Mini KPIs de la sala
                gcols = st.columns(min(len(grado_resumen), 7))
                for i, (grado, kg_g) in enumerate(grado_resumen.items()):
                    if i >= 7:
                        break
                    color = GRADO_COLORES.get(grado, '#64748b')
                    with gcols[i]:
                        st.markdown(f"""
                        <div style="background:{color}; padding:0.5rem; border-radius:8px; text-align:center;">
                            <div style="font-size:0.7rem; color:rgba(255,255,255,0.9); font-weight:600;">{grado}</div>
                            <div style="font-size:1.1rem; font-weight:800; color:#fff;">{fmt_numero(kg_g)}</div>
                            <div style="font-size:0.6rem; color:rgba(255,255,255,0.8);">kg</div>
                        </div>""", unsafe_allow_html=True)

                st.markdown("")

                # Resumen por producto
                resumen_producto = (
                    df_sala.groupby(['producto', 'codigo_producto', 'grado'])
                    .agg(kg_total=('kg', 'sum'), pallets=('pallet', 'nunique'))
                    .reset_index()
                    .sort_values('kg_total', ascending=False)
                )
                resumen_producto.columns = ['Producto', 'Código', 'Grado', 'Kilos', 'Pallets']
                resumen_producto['Kilos'] = resumen_producto['Kilos'].apply(lambda x: round(x, 2))

                st.caption("📊 Resumen por producto")
                st.dataframe(
                    resumen_producto,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Kilos": st.column_config.NumberColumn(format="%.2f"),
                        "Pallets": st.column_config.NumberColumn(format="%d"),
                    }
                )

                # Detalle pallet por pallet
                df_sala_detail = df_sala[['pallet', 'producto', 'codigo_producto', 'grado', 'kg', 'orden_fabricacion', 'fecha']].copy()
                df_sala_detail['kg'] = df_sala_detail['kg'].apply(lambda x: round(x, 2))
                df_sala_detail.columns = ['Pallet', 'Producto', 'Código', 'Grado', 'Kilos', 'OF', 'Inicio Proceso']
                df_sala_detail = df_sala_detail.sort_values(['Producto', 'Grado', 'Pallet'], ascending=[True, True, True])

                # Agregar indicador QC a la tabla de detalle
                if calidad_dict:
                    df_sala_detail['QC'] = df_sala_detail['Pallet'].apply(
                        lambda p: f"🔬 {len(calidad_dict.get(_extraer_numero_pallet(p), []))}" if _extraer_numero_pallet(p) in calidad_dict else "—"
                    )

                st.caption(f"📋 Detalle: {len(df_sala_detail)} pallets")
                st.dataframe(
                    df_sala_detail,
                    use_container_width=True,
                    hide_index=True,
                    height=min(400, 35 * len(df_sala_detail) + 38),
                    column_config={
                        "Kilos": st.column_config.NumberColumn(format="%.2f"),
                    }
                )

                # === QC INLINE: expander por cada pallet con datos de calidad ===
                if calidad_dict:
                    pallets_con_datos = [
                        p for p in df_sala_detail['Pallet'].unique()
                        if _extraer_numero_pallet(p) in calidad_dict
                    ]
                    for pallet_name in pallets_con_datos:
                        pallet_num = _extraer_numero_pallet(pallet_name)
                        registros = calidad_dict.get(pallet_num, [])
                        if not registros:
                            continue
                        # Resumen rápido para el título del expander
                        pi = [float(r.get('pct_iqf', 0) or 0) for r in registros if r.get('pct_iqf')]
                        pd2 = [float(r.get('pct_defectos', 0) or 0) for r in registros if r.get('pct_defectos')]
                        avg_i = sum(pi) / len(pi) * 100 if pi else 0
                        avg_d = sum(pd2) / len(pd2) * 100 if pd2 else 0
                        icon = "✅" if avg_d <= 4 else ("⚠️" if avg_d <= 7 else "❌")
                        iqf_str = f"IQF {avg_i:.0f}%" if pi else ""
                        def_str = f"Def {avg_d:.1f}%" if pd2 else ""
                        resumen = " | ".join(filter(None, [iqf_str, def_str]))
                        with st.expander(f"🔬 **{pallet_name}** — {icon} {resumen}", expanded=False):
                            _render_calidad_pallet(registros, pallet_name)

        # --- TABLA DETALLADA COMPLETA ---
        st.markdown("---")
        st.markdown("#### 📋 Detalle Completo de Pallets")

        # Preparar DataFrame de display
        SALA_REVERSE = {v: k for k, v in SALA_MAP_INTERNAL.items()}

        df_display = df[[
            'pallet', 'producto', 'codigo_producto', 'grado', 'kg',
            'orden_fabricacion', 'planta', 'sala', 'fecha'
        ]].copy()
        df_display['sala'] = df_display['sala'].map(lambda x: SALA_REVERSE.get(x, x))
        df_display['kg'] = df_display['kg'].apply(lambda x: round(x, 2))
        df_display.columns = [
            'Pallet', 'Producto', 'Código', 'Grado', 'Kilos',
            'OF', 'Planta', 'Sala', 'Inicio Proceso'
        ]
        df_display = df_display.sort_values(['Sala', 'Producto', 'Grado'], ascending=[True, True, True])

        # Agregar columna QC a la tabla general
        if calidad_dict:
            df_display['QC'] = df_display['Pallet'].apply(
                lambda p: f"🔬 {len(calidad_dict.get(_extraer_numero_pallet(p), []))}" if _extraer_numero_pallet(p) in calidad_dict else "—"
            )

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=600,
            column_config={
                "Kilos": st.column_config.NumberColumn(format="%.2f"),
            }
        )

        # --- EXPORTAR ---
        st.markdown("---")
        col_exp1, col_exp2 = st.columns(2)

        with col_exp1:
            csv_data = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv_data,
                file_name=f"pallets_por_sala_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col_exp2:
            try:
                excel_bytes = _generar_excel_con_calidad(df_display, calidad_dict)
                label_excel = "📊 Descargar Excel + Calidad" if calidad_dict else "📊 Descargar Excel"
                st.download_button(
                    label=label_excel,
                    data=excel_bytes,
                    file_name=f"pallets_sala_calidad_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error al preparar Excel: {e}")
    else:
        st.info("👆 Selecciona los filtros y haz clic en **Consultar Pallets** para ver los datos")

"""
Tab: Pallets por Sala
Muestra una vista detallada de pallets de producto terminado filtrados por sala de proceso,
producto, fecha, manejo y tipo de fruta. Solo temporada 2025 y 2026.
"""
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

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


def _normalize(text: str) -> str:
    """Normaliza texto removiendo acentos para comparaciones."""
    if not text:
        return ""
    text = text.lower()
    for old, new in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]:
        text = text.replace(old, new)
    return text


def _filtrar_detalle(detalle_raw, filtros):
    """Aplica filtros dinámicos sobre la lista de detalle en memoria."""
    resultado = list(detalle_raw)

    # Filtrar por Planta
    if filtros.get("planta") and filtros["planta"] != "Todas":
        resultado = [d for d in resultado if d.get('planta') == filtros["planta"]]

    # Filtrar por Fruta (usando código de producto, más robusto que nombre)
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

    # Filtrar por Sala de Proceso
    if filtros.get("sala") and filtros["sala"] != "Todas":
        target_key = SALA_MAP_INTERNAL.get(filtros["sala"])
        target_norm = _normalize(target_key or filtros["sala"])
        resultado = [
            d for d in resultado
            if _normalize(d.get('sala')) == target_norm or target_norm in _normalize(d.get('sala'))
        ]

    # Filtrar por Manejo
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

    # Filtrar por Producto (texto libre)
    if filtros.get("producto_texto"):
        texto = filtros["producto_texto"].lower().strip()
        resultado = [d for d in resultado if texto in d.get('producto', '').lower() or texto in d.get('codigo_producto', '').lower()]

    # Filtrar por Temporada 2025/2026 basado en fecha
    resultado_temp = []
    for d in resultado:
        fecha = d.get('fecha', '')
        if fecha:
            year = str(fecha)[:4]
            if year in TEMPORADAS_VALIDAS:
                resultado_temp.append(d)
    resultado = resultado_temp

    return resultado


@st.fragment
def render(username: str, password: str):
    """Renderiza el tab de Pallets por Sala."""

    st.markdown("### 🏢 PALLETS POR SALA DE PROCESO")
    st.caption("Detalle de pallets de producto terminado por sala, producto y grado — Temporada 2025 / 2026")

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

        # Filtro de búsqueda de producto
        producto_texto = st.text_input(
            "🔎 Buscar Producto (nombre o código)",
            value="",
            key="ps_producto_texto",
            placeholder="Ej: Arándano IQF, 3111..."
        )

        consultar = st.button("🔍 Consultar Pallets", use_container_width=True, type="primary", key="ps_btn_consultar")

    # === CSS ===
    st.markdown("""
    <style>
        .sala-header {
            background: linear-gradient(135deg, #1e3a5f 0%, #1e293b 100%);
            padding: 1rem 1.2rem;
            border-radius: 12px;
            border-left: 5px solid #3b82f6;
            margin-bottom: 1rem;
        }
        .sala-header h4 { margin: 0; color: #ffffff; }
        .sala-header span { color: #94a3b8; font-size: 0.85rem; }
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

            tipo_fruta_param = None if tipo_fruta == "Todas" else tipo_fruta
            tipo_manejo_param = None if tipo_manejo == "Todos" else tipo_manejo
            sala_key = SALA_MAP_INTERNAL.get(sala_seleccionada)
            sala_param = sala_key if sala_key else None

            with st.spinner("⏳ Consultando pallets por sala..."):
                try:
                    params = {
                        "username": username,
                        "password": password,
                        "fecha_inicio": fecha_inicio_str,
                        "fecha_fin": fecha_fin_str,
                        "tipo_operacion": planta_seleccionada
                    }
                    if tipo_fruta_param:
                        params["tipo_fruta"] = tipo_fruta_param
                    if tipo_manejo_param:
                        params["tipo_manejo"] = tipo_manejo_param
                    if sala_param:
                        params["sala_proceso"] = sala_param

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

        st.markdown("---")
        kpi_cols = st.columns(4)
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

            # Desglose por grado
            grado_resumen = df_sala.groupby('grado')['kg'].sum().sort_values(ascending=False)

            with st.expander(f"🏢 **{sala_label}** — {fmt_numero(kg_sala)} kg | {pallets_sala} pallets | {productos_sala} productos", expanded=False):

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
                import io
                from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                from openpyxl.utils import get_column_letter

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_display.to_excel(writer, index=False, sheet_name='Pallets_por_Sala')
                    ws = writer.sheets['Pallets_por_Sala']

                    # Autofiltro en todo el rango
                    ws.auto_filter.ref = ws.dimensions

                    # Estilos
                    header_font = Font(bold=True, color="FFFFFF", size=11)
                    header_fill = PatternFill(start_color="1F3A5F", end_color="1F3A5F", fill_type="solid")
                    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
                    thin_border = Border(
                        left=Side(style='thin', color='D0D0D0'),
                        right=Side(style='thin', color='D0D0D0'),
                        top=Side(style='thin', color='D0D0D0'),
                        bottom=Side(style='thin', color='D0D0D0')
                    )

                    # Formatear encabezados
                    for col_idx in range(1, ws.max_column + 1):
                        cell = ws.cell(row=1, column=col_idx)
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = header_align
                        cell.border = thin_border

                    # Bordes en todas las celdas de datos
                    for row in range(2, ws.max_row + 1):
                        for col_idx in range(1, ws.max_column + 1):
                            ws.cell(row=row, column=col_idx).border = thin_border

                    # Ajustar ancho de columnas al contenido
                    for col_idx in range(1, ws.max_column + 1):
                        col_letter = get_column_letter(col_idx)
                        max_len = len(str(ws.cell(row=1, column=col_idx).value or ""))
                        for row in range(2, min(ws.max_row + 1, 200)):
                            val = ws.cell(row=row, column=col_idx).value
                            if val:
                                max_len = max(max_len, len(str(val)))
                        ws.column_dimensions[col_letter].width = min(max_len + 3, 50)

                    # Congelar primera fila (encabezados siempre visibles)
                    ws.freeze_panes = "A2"

                st.download_button(
                    label="📊 Descargar Excel",
                    data=buffer.getvalue(),
                    file_name=f"pallets_por_sala_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception:
                st.error("Error al preparar Excel.")
    else:
        st.info("👆 Selecciona los filtros y haz clic en **Consultar Pallets** para ver los datos")

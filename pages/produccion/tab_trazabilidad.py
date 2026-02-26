"""
Tab de Trazabilidad de Pallets
Permite ingresar un nombre de pallet y trazar hacia atrás toda la cadena
productiva hasta llegar a materia prima (recepciones).
Genera un Excel descargable con toda la trazabilidad.
"""
import streamlit as st
import pandas as pd
import io
from datetime import datetime
from typing import Dict, List
import httpx
from .shared import API_URL


def render(username: str, password: str):
    """Renderiza el tab de Trazabilidad de Pallets."""

    st.subheader("🔍 Trazabilidad de Pallets")
    st.caption(
        "Ingresa un pallet (PACK) y rastrea su cadena productiva hacia atrás "
        "hasta la materia prima recepcionada (guía de despacho y proveedor)."
    )

    col_input, col_btn = st.columns([3, 1])
    with col_input:
        pallet_name = st.text_input(
            "Nombre del pallet",
            placeholder="Ej: PACK0012345",
            key="traz_pallet_input",
            help="Ingresa el nombre exacto del pallet tal como aparece en Odoo"
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        buscar = st.button("🔍 Trazar", type="primary", key="traz_buscar")

    if not buscar and 'traz_resultado' not in st.session_state:
        st.info("💡 Ingresa un nombre de pallet y presiona **Trazar** para ver la cadena completa.")
        return

    if buscar:
        if not pallet_name or not pallet_name.strip():
            st.warning("⚠️ Debes ingresar un nombre de pallet.")
            return

        pallet_name = pallet_name.strip().upper()

        with st.spinner(f"🔎 Trazando pallet **{pallet_name}** hacia atrás..."):
            try:
                resp = httpx.get(
                    f"{API_URL}/api/v1/produccion/trazabilidad",
                    params={
                        "pallet_name": pallet_name,
                        "username": username,
                        "password": password,
                    },
                    timeout=120.0,
                )
                resp.raise_for_status()
                resultado = resp.json()
                st.session_state['traz_resultado'] = resultado
            except httpx.TimeoutException:
                st.error("⏱️ La consulta tardó demasiado. Intenta nuevamente.")
                return
            except httpx.HTTPStatusError as e:
                st.error(f"❌ Error del servidor: {e.response.status_code} – {e.response.text[:300]}")
                return
            except Exception as e:
                st.error(f"❌ Error de conexión: {e}")
                return

    resultado = st.session_state.get('traz_resultado')
    if not resultado:
        return

    if resultado.get('error'):
        st.error(f"⚠️ {resultado['error']}")
        return

    arbol = resultado.get('arbol', [])
    mp_list = resultado.get('materia_prima', [])
    niveles = resultado.get('niveles', 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pallet Origen", resultado.get('pallet_origen', ''))
    c2.metric("Niveles de Trazabilidad", niveles)
    c3.metric("Nodos en Cadena", len(arbol))
    c4.metric("Pallets MP Encontrados", len(mp_list))

    st.divider()

    if arbol:
        st.markdown("### 🌳 Cadena de Trazabilidad")
        _render_arbol(arbol)

    st.divider()

    if mp_list:
        st.markdown("### 📦 Materia Prima (Recepciones)")
        df_mp = pd.DataFrame(mp_list)
        cols_rename = {
            'pallet': 'Pallet',
            'producto': 'Producto',
            'lote': 'Lote',
            'kg': 'Kg',
            'recepcion': 'Recepción',
            'guia_despacho': 'Guía Despacho',
            'proveedor': 'Proveedor',
            'fecha_recepcion': 'Fecha Recepción',
        }
        df_display = df_mp.rename(columns=cols_rename)
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.warning("No se encontraron pallets de materia prima en la cadena.")

    st.divider()

    st.markdown("### 📥 Exportar a Excel")
    excel_bytes = _generar_excel(resultado)
    pallet_origen = resultado.get('pallet_origen', 'PALLET')
    fecha_str = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"Trazabilidad_{pallet_origen}_{fecha_str}.xlsx"

    st.download_button(
        label="⬇️ Descargar Excel de Trazabilidad",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


def _render_arbol(arbol: List[Dict]):
    """Renderiza el árbol de trazabilidad de forma visual."""
    niveles = {}
    for nodo in arbol:
        nivel = nodo.get('nivel', 0)
        if nivel not in niveles:
            niveles[nivel] = []
        niveles[nivel].append(nodo)

    for nivel_num in sorted(niveles.keys()):
        nodos = niveles[nivel_num]
        tipo_label = "PT (Producto Terminado)" if nivel_num == 0 else "MP (Materia Prima)" if nodos[0].get('es_mp') else "Semi-elaborado"

        with st.expander(f"{'↳ ' * nivel_num}Nivel {nivel_num} — {tipo_label} ({len(nodos)} pallets)", expanded=(nivel_num <= 1)):
            rows = []
            for n in nodos:
                rows.append({
                    'Pallet': n.get('pallet', ''),
                    'Producto': n.get('producto', ''),
                    'Lote': n.get('lote', ''),
                    'Kg': n.get('kg', 0),
                    'Orden': n.get('orden', ''),
                    'Tipo': n.get('tipo_orden', ''),
                    'Fecha': n.get('fecha', ''),
                    'MP': '✅' if n.get('es_mp') else '',
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)


def _generar_excel(resultado: Dict) -> bytes:
    """Genera un archivo Excel con toda la trazabilidad."""
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pallet_origen = resultado.get('pallet_origen', '')

        resumen = {
            'Campo': ['Pallet Consultado', 'Niveles de Trazabilidad', 'Total Nodos en Cadena', 'Pallets MP Encontrados', 'Fecha de Consulta'],
            'Valor': [pallet_origen, resultado.get('niveles', 0), len(resultado.get('arbol', [])), len(resultado.get('materia_prima', [])), datetime.now().strftime('%d/%m/%Y %H:%M')],
        }
        pd.DataFrame(resumen).to_excel(writer, sheet_name='Resumen', index=False)

        arbol = resultado.get('arbol', [])
        if arbol:
            rows_arbol = []
            for n in arbol:
                rows_arbol.append({
                    'Nivel': n.get('nivel', 0),
                    'Pallet': n.get('pallet', ''),
                    'Producto': n.get('producto', ''),
                    'Lote': n.get('lote', ''),
                    'Kg': n.get('kg', 0),
                    'Orden': n.get('orden', ''),
                    'Tipo Orden': n.get('tipo_orden', ''),
                    'Fecha': n.get('fecha', ''),
                    'Es MP': 'Sí' if n.get('es_mp') else 'No',
                })
            pd.DataFrame(rows_arbol).to_excel(writer, sheet_name='Cadena Completa', index=False)

        mp_list = resultado.get('materia_prima', [])
        if mp_list:
            df_mp = pd.DataFrame(mp_list)
            df_mp.columns = ['Pallet', 'Producto', 'Lote', 'Kg', 'Recepción', 'Guía Despacho', 'Proveedor', 'Fecha Recepción']
            df_mp.to_excel(writer, sheet_name='Materia Prima', index=False)

        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    try:
                        cell_len = len(str(cell.value or ''))
                        if cell_len > max_len:
                            max_len = cell_len
                    except:
                        pass
                ws.column_dimensions[col_letter].width = min(max_len + 4, 50)

    output.seek(0)
    return output.getvalue()

"""
Mini-app Streamlit: Generador de Reporte Diario de Producción.
Ejecutar: streamlit run scripts/app_reporte_diario.py
"""
import sys
from pathlib import Path

# Setup path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from datetime import date, datetime

st.set_page_config(
    page_title="Reporte Diario Producción",
    page_icon="📊",
    layout="centered"
)

# Estilos
st.markdown("""
<style>
    .stButton>button {
        background: linear-gradient(135deg, #1F4E79, #2E75B6);
        color: white;
        font-size: 18px;
        font-weight: bold;
        padding: 15px 40px;
        border-radius: 12px;
        border: none;
        width: 100%;
        cursor: pointer;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #163a5c, #1F5F99);
    }
    .stDownloadButton>button {
        background: linear-gradient(135deg, #2E7D32, #43A047);
        color: white;
        font-size: 16px;
        font-weight: bold;
        padding: 12px 30px;
        border-radius: 12px;
        border: none;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align: center; padding: 20px 0;">
    <h1 style="color: #1F4E79;">📊 Reporte Diario de Producción</h1>
    <p style="color: #666; font-size: 16px;">
        Genera un Excel con la producción del día, agrupado por Sala y Turno
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Fecha
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    fecha = st.date_input("📅 Fecha del reporte", value=date.today(), format="YYYY-MM-DD")
    fecha_str = fecha.strftime('%Y-%m-%d')

st.markdown("")

# Botón principal
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    generar = st.button("📋 GENERAR EXCEL DIARIO", use_container_width=True)

if generar:
    from scripts.reporte_diario_produccion import (
        get_odoo, fetch_mos, fetch_kg_pt, fetch_quality_approval,
        process_data, write_excel
    )

    progress = st.progress(0, text="Conectando a Odoo...")

    try:
        # 1. Conectar
        odoo = get_odoo()
        progress.progress(15, text="✅ Conectado. Buscando MOs...")

        # 2. MOs
        mos = fetch_mos(odoo, fecha_str, fecha_str)
        if not mos:
            progress.empty()
            st.warning(f"⚠️ No se encontraron MOs para el {fecha_str}")
            st.stop()

        progress.progress(35, text=f"📦 {len(mos)} MOs encontradas. Calculando KG...")

        # 3. KG PT
        kg_pt_map = fetch_kg_pt(odoo, mos)
        progress.progress(60, text="⚖️ KG calculados. Verificando calidad...")

        # 4. Quality
        mo_ids = [mo['id'] for mo in mos]
        quality_map = fetch_quality_approval(odoo, mo_ids)
        progress.progress(80, text="✅ Calidad Ok. Generando Excel...")

        # 5. Procesar
        rows = process_data(mos, kg_pt_map, quality_map)

        # 6. Excel
        excel_bytes = write_excel(rows, fecha_str, fecha_str, save_to_file=True)
        progress.progress(100, text="✅ ¡Excel generado!")

        # Resumen
        st.markdown("---")

        # KPIs
        total_kg = sum(r['kg_pt'] for r in rows)
        salas = set(r['sala'] for r in rows)
        turnos = set(r['turno'] for r in rows)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 MOs", len(rows))
        c2.metric("⚖️ KG Totales", f"{total_kg:,.0f}")
        c3.metric("🏭 Salas", len(salas))
        c4.metric("⏰ Turnos", ", ".join(sorted(turnos)))

        st.markdown("")

        # Tabla resumen por sala
        st.markdown("### 📋 Resumen por Sala")
        from collections import defaultdict
        resumen = defaultdict(lambda: {"mos": 0, "kg": 0, "hh": 0, "det": 0})
        for r in rows:
            key = r['sala']
            resumen[key]["mos"] += 1
            resumen[key]["kg"] += r['kg_pt']
            resumen[key]["hh"] += r['hh']
            resumen[key]["det"] += r['detenciones']

        tabla = []
        for sala in sorted(resumen.keys()):
            d = resumen[sala]
            tabla.append({
                "Sala": sala,
                "OFs": d["mos"],
                "KG PT": f"{d['kg']:,.0f}",
                "HH Total": f"{d['hh']:,.1f}",
                "KG/HH": f"{d['kg']/d['hh']:,.1f}" if d['hh'] > 0 else "-",
                "Detenciones": f"{d['det']:,.1f}h"
            })
        st.dataframe(tabla, use_container_width=True, hide_index=True)

        # Botón de descarga
        st.markdown("")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.download_button(
                label=f"⬇️ Descargar Excel - {fecha_str}",
                data=excel_bytes,
                file_name=f"reporte_produccion_{fecha_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    except Exception as e:
        progress.empty()
        st.error(f"❌ Error: {e}")
        st.exception(e)

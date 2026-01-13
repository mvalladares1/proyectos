"""
Tab: Seguimiento de Órdenes de Fabricación
Muestra las órdenes abiertas y cerradas, separadas por planta y tipo de proceso (Sala vs Congelado).
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from .shared import API_URL, fmt_numero, detectar_planta, format_fecha

def render(username: str, password: str):
    st.markdown("### 📋 Seguimiento de Órdenes de Fabricación")
    st.caption("Visualiza el estado real de la producción: Pendientes vs Hechos")

    # === FILTROS ===
    with st.container():
        col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
        with col_f1:
            fecha_inicio = st.date_input("Desde", datetime.now() - timedelta(days=30), key="of_fecha_inicio")
        with col_f2:
            fecha_fin = st.date_input("Hasta", datetime.now(), key="of_fecha_fin")
        with col_f3:
            planta_filtro = st.selectbox("Planta", ["Todas", "RIO FUTURO", "VILKUN"], index=0, key="of_planta")

    # Botón Consultar
    if st.button("🔍 Consultar Órdenes", use_container_width=True, type="primary"):
        with st.spinner("Cargando órdenes..."):
            try:
                import requests
                params = {
                    "username": username,
                    "password": password,
                    "fecha_desde": fecha_inicio.strftime('%Y-%m-%d'),
                    "fecha_hasta": fecha_fin.strftime('%Y-%m-%d'),
                    "limit": 500
                }
                resp = requests.get(f"{API_URL}/api/v1/produccion/ordenes", params=params, timeout=60)
                if resp.status_code == 200:
                    st.session_state.of_data_list = resp.json()
                else:
                    st.error(f"Error al obtener datos: {resp.status_code}")
            except Exception as e:
                st.error(f"Error de conexión: {e}")

    # Recuperar datos de session state
    if "of_data_list" not in st.session_state:
        st.info("👆 Selecciona el rango de fechas y haz clic en **Consultar Órdenes**")
        return

    all_mos = st.session_state.of_data_list
    if not all_mos:
        st.warning("No se encontraron órdenes para el periodo seleccionado.")
        return

    # --- PROCESAMIENTO Y CLASIFICACIÓN ---
    processed_data = []
    for mo in all_mos:
        mo_name = mo.get('name', '')
        planta = detectar_planta(mo_name)
        
        # Filtrar por planta
        if planta_filtro != "Todas" and planta != planta_filtro:
            continue
            
        def get_label(val):
            if not val: return ""
            if isinstance(val, dict): return val.get('name', '')
            if isinstance(val, (list, tuple)) and len(val) > 1: return val[1]
            return str(val)

        prod_name = get_label(mo.get('product_id'))
        sala_raw = get_label(mo.get('x_studio_sala_de_proceso'))
        
        # Clasificación Sala vs Congelado
        sala_lower = sala_raw.lower()
        prod_lower = prod_name.lower()
        
        if any(s in sala_lower for s in ['sala 1', 'sala 2', 'sala 3', 'sala 4', 'sala 5', 'sala 6', 'linea retail', 'granel', 'proceso']):
            tipo_mo = "Proceso en Sala"
        elif 'congel' in sala_lower or 'tunel' in sala_lower or 'túnel' in sala_lower:
            tipo_mo = "Congelado"
        elif 'iqf' in sala_lower or 'iqf' in prod_lower:
            tipo_mo = "Proceso en Sala"
        elif 'sala' in sala_lower and any(c.isdigit() for c in sala_lower):
            tipo_mo = "Proceso en Sala"
        else:
            tipo_mo = "Congelado" # Fallback

        # PSP
        is_psp = "PSP" in prod_name.upper() or prod_name.startswith('[2.') or prod_name.startswith('[2,')

        # Estado
        state = mo.get('state', '')
        es_abierta = state in ['confirmed', 'progress', 'planned', 'to_close']
        
        qty_total = mo.get('product_qty', 0) or 0
        qty_done = mo.get('qty_produced', 0) or 0
        qty_pending = max(0, qty_total - qty_done)

        processed_data.append({
            "OF": mo_name,
            "Producto": prod_name,
            "Planta": planta,
            "Sala": sala_raw or "Sin Sala",
            "Tipo": tipo_mo,
            "Estado": "Abierta" if es_abierta else "Cerrada",
            "Kg Total": qty_total,
            "Kg Hechos": qty_done,
            "Kg Pendientes": qty_pending,
            "PSP": "✅" if is_psp else "",
            "Fecha": mo.get('date_planned_start', ''),
            "RawState": state
        })

    if not processed_data:
        st.info("No hay órdenes que coincidan con la planta seleccionada.")
        return

    df = pd.DataFrame(processed_data)

    # === KPIs SUPERIORES ===
    st.markdown("---")
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        total_pend = df[df['Estado'] == 'Abierta']['Kg Pendientes'].sum()
        st.metric("📦 Kg Pendientes (Abiertas)", fmt_numero(total_pend))
    with kpi_cols[1]:
        total_hechos = df['Kg Hechos'].sum()
        st.metric("✅ Kg Hechos (Total)", fmt_numero(total_hechos))
    with kpi_cols[2]:
        ofs_abier = len(df[df['Estado'] == 'Abierta'])
        st.metric("🔄 OFs Abiertas", ofs_abier)
    with kpi_cols[3]:
        ofs_psp = len(df[df['PSP'] == "✅"])
        st.metric("🟣 OFs PSP", ofs_psp)

    # === TABS DE ESTADO ===
    tab_abiertas, tab_cerradas = st.tabs(["🔄 Órdenes Abiertas", "✅ Órdenes Cerradas"])

    def render_grouped_ofs(df_filtered):
        if df_filtered.empty:
            st.info("No hay órdenes en este estado.")
            return

        # Separar Congelado de Sala
        df_sala = df_filtered[df_filtered['Tipo'] == "Proceso en Sala"]
        df_congelado = df_filtered[df_filtered['Tipo'] == "Congelado"]

        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("#### 🏭 Proceso en Sala")
            if df_sala.empty:
                st.caption("Sin órdenes de proceso")
            else:
                for sala, group in df_sala.groupby("Sala"):
                    with st.expander(f"📍 {sala} ({len(group)} OFs)"):
                        st.dataframe(
                            group[["OF", "Producto", "Kg Total", "Kg Hechos", "Kg Pendientes", "PSP"]], 
                            use_container_width=True, hide_index=True
                        )

        with col_right:
            st.markdown("#### ❄️ Congelado (Túneles)")
            if df_congelado.empty:
                st.caption("Sin órdenes de congelado")
            else:
                for sala, group in df_congelado.groupby("Sala"):
                    with st.expander(f"📍 {sala} ({len(group)} OFs)"):
                        st.dataframe(
                            group[["OF", "Producto", "Kg Total", "Kg Hechos", "Kg Pendientes", "PSP"]], 
                            use_container_width=True, hide_index=True
                        )

    with tab_abiertas:
        render_grouped_ofs(df[df['Estado'] == 'Abierta'])

    with tab_cerradas:
        render_grouped_ofs(df[df['Estado'] == 'Cerrada'])

    # === TABLA COMPLETA CON FILTRO DINÁMICO ===
    st.markdown("---")
    st.markdown("#### 🔍 Explorador Detallado")
    search = st.text_input("Buscar por OF o Producto", "")
    if search:
        df_search = df[df['OF'].str.contains(search, case=False) | df['Producto'].str.contains(search, case=False)]
    else:
        df_search = df

    st.dataframe(
        df_search.drop(columns=["RawState", "Tipo"]), 
        use_container_width=True,
        column_config={
            "Kg Total": st.column_config.NumberColumn(format="%d"),
            "Kg Hechos": st.column_config.NumberColumn(format="%d"),
            "Kg Pendientes": st.column_config.NumberColumn(format="%d"),
        }
    )

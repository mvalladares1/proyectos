"""
Recepciones de Materia Prima: KPIs de Kg, costos, % IQF/Block y análisis de calidad por productor.
"""
import streamlit as st
import pandas as pd
import requests
import altair as alt
from datetime import datetime, timedelta
import sys
import os
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.auth import proteger_pagina, get_credenciales

st.set_page_config(page_title="Recepciones MP", page_icon="📥", layout="wide")

# Autenticación central
if not proteger_pagina():
    st.stop()

# Obtener credenciales del usuario autenticado
username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales. Por favor inicie sesión nuevamente.")
    st.stop()

st.title("📥 Recepciones de Materia Prima (MP)")
st.caption("Monitorea la fruta recepcionada en planta, con KPIs de calidad asociados")

# API URL del backend central
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# --- Estado persistente ---
if 'df_recepcion' not in st.session_state:
    st.session_state.df_recepcion = None
if 'idx_recepcion' not in st.session_state:
    st.session_state.idx_recepcion = None

# Filtros
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Fecha inicio", datetime.now() - timedelta(days=7), key="fecha_inicio_recepcion")
with col2:
    fecha_fin = st.date_input("Fecha fin", datetime.now(), key="fecha_fin_recepcion")

if st.button("Consultar Recepciones", key="btn_consultar_recepcion"):
    params = {
        "username": username,
        "password": password,
        "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
        "fecha_fin": fecha_fin.strftime("%Y-%m-%d")
    }
    api_url = f"{API_URL}/api/v1/recepciones-mp/"
    try:
        resp = requests.get(api_url, params=params, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            df = pd.DataFrame(data)
            if not df.empty:
                st.session_state.df_recepcion = df
                st.session_state.idx_recepcion = None
            else:
                st.session_state.df_recepcion = None
                st.session_state.idx_recepcion = None
                st.warning("No se encontraron recepciones en el rango de fechas seleccionado.")
        else:
            st.error(f"Error: {resp.status_code} - {resp.text}")
            st.session_state.df_recepcion = None
            st.session_state.idx_recepcion = None
    except requests.exceptions.ConnectionError:
        st.error("No se puede conectar al servidor API. Verificar que el backend esté corriendo.")
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Mostrar tabla y detalle si hay datos
df = st.session_state.df_recepcion
if df is not None:
    # --- KPIs Consolidados ---
    st.subheader("📊 KPIs Consolidados")
    # Calcular Totales separando por categoría de producto (BANDEJAS)
    total_kg_mp = 0.0
    total_costo_mp = 0.0
    total_bandejas = 0.0
    # recorrer todas las recepciones y sus productos
    for _, row in df.iterrows():
        # Asegurarnos que solo consideramos recepciones que sean fruta
        tipo_fruta_row = (row.get('tipo_fruta') or "").strip()
        if not tipo_fruta_row:
            continue
        if 'productos' in row and isinstance(row['productos'], list):
            for p in row['productos']:
                kg = p.get('Kg Hechos', 0) or 0
                costo = p.get('Costo Total', 0) or 0
                categoria = (p.get('Categoria') or "").strip().upper()
                # detectar variantes que contengan 'BANDEJ' (Bandeja/Bandejas)
                if 'BANDEJ' in categoria:
                    total_bandejas += kg
                else:
                    total_kg_mp += kg
                    total_costo_mp += costo

    # Calcular métricas y promedios existentes
    # Nota: eliminamos 'Total Kg Recepcionados (global)'.
    # El "Costo Total (global)" se mostrará en base a Total Kg Recepcionados MP (total_costo_mp).
    prom_iqf = df['total_iqf'].mean()
    prom_block = df['total_block'].mean()
    clasif = df['calific_final'].value_counts().idxmax() if not df['calific_final'].isnull().all() and not df['calific_final'].eq('').all() else "-"

    # Mostrar en dos filas compactas
    top_cols = st.columns([1,1,1])
    with top_cols[0]:
        st.metric("Total Kg Recepcionados MP", f"{total_kg_mp:,.2f}")
    with top_cols[1]:
        st.metric("Costo Total MP", f"${total_costo_mp:,.0f}")
    with top_cols[2]:
        st.metric("Bandejas recepcionadas", f"{total_bandejas:,.2f}")

    bot_cols = st.columns([1,1,1])
    with bot_cols[0]:
        st.metric("Costo Total (global)", f"${total_costo_mp:,.0f}")
    with bot_cols[1]:
        st.metric("Promedio % IQF", f"{prom_iqf:.2f}%")
    with bot_cols[2]:
        st.metric("Promedio % Block", f"{prom_block:.2f}%")
    st.markdown(f"**Clasificación más frecuente:** {clasif}")

    # Filtros adicionales
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        tipos_fruta = df['tipo_fruta'].dropna().unique().tolist()
        tipos_fruta = sorted([t for t in tipos_fruta if t])
        tipo_fruta_filtro = st.multiselect("Filtrar por Tipo de Fruta", tipos_fruta, key="tipo_fruta_filtro")
    with col_f2:
        clasifs = df['calific_final'].dropna().unique().tolist()
        clasifs = sorted([c for c in clasifs if c])
        clasif_filtro = st.multiselect("Filtrar por Clasificación", clasifs, key="clasif_filtro")

    productor_filtro = None
    productores = df['productor'].dropna().unique().tolist()
    productores = sorted([p for p in productores if p])
    if productores:
        productor_filtro = st.multiselect("Filtrar por Productor", productores, key="productor_filtro")

    df_filtrada = df.copy()
    if productor_filtro:
        df_filtrada = df_filtrada[df_filtrada['productor'].isin(productor_filtro)]
    if tipo_fruta_filtro:
        df_filtrada = df_filtrada[df_filtrada['tipo_fruta'].isin(tipo_fruta_filtro)]
    if clasif_filtro:
        df_filtrada = df_filtrada[df_filtrada['calific_final'].isin(clasif_filtro)]

    # Tabla de recepciones (filtrar recepciones sin tipo de fruta)
    st.subheader("📋 Detalle de Recepciones")
    df_filtrada = df_filtrada[df_filtrada['tipo_fruta'].notna() & (df_filtrada['tipo_fruta'] != '')]
    # Calcular bandejas por recepción (sumar Kg Hechos de productos cuya Categoria contenga 'BANDEJ')
    bandejas_vals = []
    for _, row in df_filtrada.iterrows():
        b = 0.0
        prods = row.get('productos', []) or []
        if isinstance(prods, list):
            for p in prods:
                categoria = (p.get('Categoria') or '').strip().upper()
                if 'BANDEJ' in categoria:
                    b += p.get('Kg Hechos', 0) or 0
        bandejas_vals.append(b)
    df_filtrada = df_filtrada.copy()
    df_filtrada['bandejas'] = bandejas_vals
    df_filtrada['sin_calidad'] = df_filtrada['calific_final'].isnull() | (df_filtrada['calific_final'] == '')
    cols_mostrar = [
        "albaran", "fecha", "productor", "tipo_fruta", "guia_despacho",
        "bandejas", "kg_recepcionados", "calific_final", "total_iqf", "total_block", "sin_calidad"
    ]
    df_mostrar = df_filtrada[cols_mostrar].copy()
    df_mostrar.columns = [
        "Albarán", "Fecha", "Productor", "Tipo Fruta", "Guía Despacho",
        "Bandejas", "Kg Recepcionados", "Clasificación", "% IQF", "% Block", "Sin Calidad"
    ]
    # Ajustar Kg Recepcionados para excluir las Bandejas (mostramos Kg fruta)
    # Convertir a numérico, restar bandejas y formatear
    df_mostrar["Bandejas"] = pd.to_numeric(df_mostrar["Bandejas"], errors='coerce').fillna(0.0)
    df_mostrar["Kg Recepcionados"] = pd.to_numeric(df_mostrar["Kg Recepcionados"], errors='coerce').fillna(0.0) - df_mostrar["Bandejas"]
    df_mostrar["Kg Recepcionados"] = df_mostrar["Kg Recepcionados"].apply(lambda x: f"{x:.2f}")
    df_mostrar["Bandejas"] = df_mostrar["Bandejas"].apply(lambda x: f"{x:.2f}")
    df_mostrar["% IQF"] = df_mostrar["% IQF"].apply(lambda x: f"{x:.2f}")
    df_mostrar["% Block"] = df_mostrar["% Block"].apply(lambda x: f"{x:.2f}")
    df_mostrar["Sin Calidad"] = df_mostrar["Sin Calidad"].apply(lambda x: "❌" if x else "✅")

    # Botón para exportar a Excel/CSV
    col_exp1, col_exp2 = st.columns([1,1])
    with col_exp1:
        csv = df_mostrar.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar CSV", csv, "recepciones.csv", "text/csv", key="download_csv")
    with col_exp2:
        excel_buffer = io.BytesIO()
        if hasattr(df_mostrar, 'to_excel'):
            df_mostrar.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)
            st.download_button(
                "Descargar Excel",
                excel_buffer,
                "recepciones.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel"
            )

    st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

    # Gráficos generales
    st.subheader("📈 Kg recepcionados por día (por Tipo de Fruta)")
    df_filtrada['fecha_dt'] = pd.to_datetime(df_filtrada['fecha']).dt.strftime('%Y-%m-%d')
    kg_por_dia_fruta = df_filtrada.groupby(['fecha_dt', 'tipo_fruta'])['kg_recepcionados'].sum().reset_index()
    chart_kg = alt.Chart(kg_por_dia_fruta).mark_bar().encode(
        x=alt.X('fecha_dt:N', title='Fecha', sort=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('kg_recepcionados:Q', title='Kg Recepcionados'),
        color=alt.Color('tipo_fruta:N', title='Tipo Fruta')
    ).properties(width=700, height=350)
    st.altair_chart(chart_kg, use_container_width=True)

    st.subheader("🏆 Ranking de productores por Kg")
    ranking = df_filtrada.groupby('productor')['kg_recepcionados'].sum().sort_values(ascending=False).reset_index()
    chart_rank = alt.Chart(ranking).mark_bar().encode(
        x=alt.X('productor:N', sort='-y', title='Productor', axis=alt.Axis(labelAngle=-90, labelLimit=200)),
        y=alt.Y('kg_recepcionados:Q', title='Kg Recepcionados')
    ).properties(width=700, height=400)
    st.altair_chart(chart_rank, use_container_width=True)

    # Detalle de defectos
    st.subheader("🔬 Detalle de Defectos (promedios)")
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        st.metric("Daño Mecánico", f"{df_filtrada['dano_mecanico'].mean():.2f}")
        st.metric("Hongos", f"{df_filtrada['hongos'].mean():.2f}")
    with col_d2:
        st.metric("Inmadura", f"{df_filtrada['inmadura'].mean():.2f}")
        st.metric("Sobremadura", f"{df_filtrada['sobremadura'].mean():.2f}")
    with col_d3:
        st.metric("Daño Insecto", f"{df_filtrada['dano_insecto'].mean():.2f}")
        st.metric("Defecto Frutilla", f"{df_filtrada['defecto_frutilla'].mean():.4f}")

    # --- Detalle de recepción específica (abajo) ---
    opciones_idx = df_filtrada.index.tolist()
    if opciones_idx:
        default_idx = 0
        if st.session_state.idx_recepcion is not None and st.session_state.idx_recepcion in opciones_idx:
            default_idx = opciones_idx.index(st.session_state.idx_recepcion)
        
        idx = st.selectbox(
            "Selecciona una recepción para ver el detalle:",
            options=opciones_idx,
            index=default_idx,
            format_func=lambda i: f"{df_filtrada.loc[i, 'albaran']} - {df_filtrada.loc[i, 'productor']} - {df_filtrada.loc[i, 'fecha']}",
            key="selectbox_recepcion"
        )
        st.session_state.idx_recepcion = idx
        rec = df_filtrada.loc[idx]
        st.markdown("---")
        st.markdown("### 📝 Detalle de Recepción")
        detalle_cols = st.columns(3)
        with detalle_cols[0]:
            st.write(f"**Albarán:** {rec['albaran']}")
            st.write(f"**Fecha:** {rec['fecha']}")
            st.write(f"**Productor:** {rec['productor']}")
            st.write(f"**Tipo Fruta:** {rec['tipo_fruta']}")
            st.write(f"**Guía Despacho:** {rec['guia_despacho']}")
        with detalle_cols[1]:
            st.write(f"**Kg Recepcionados:** {rec['kg_recepcionados']:.2f}")
            st.write(f"**Clasificación:** {rec['calific_final']}")
            st.write(f"**% IQF:** {rec['total_iqf']:.2f}")
            st.write(f"**% Block:** {rec['total_block']:.2f}")
        with detalle_cols[2]:
            st.write(f"**Daño Mecánico:** {rec['dano_mecanico']:.2f}")
            st.write(f"**Hongos:** {rec['hongos']:.2f}")
            st.write(f"**Inmadura:** {rec['inmadura']:.2f}")
            st.write(f"**Sobremadura:** {rec['sobremadura']:.2f}")
            st.write(f"**Daño Insecto:** {rec['dano_insecto']:.2f}")
            st.write(f"**Defecto Frutilla:** {rec['defecto_frutilla']:.2f}")

        st.markdown("#### 📦 Productos de la Recepción")
        if 'productos' in rec and isinstance(rec['productos'], list) and rec['productos']:
            prod_df = pd.DataFrame(rec['productos'])
            prod_df = prod_df[prod_df['Kg Hechos'] > 0]
            if not prod_df.empty:
                prod_df['Kg Hechos'] = prod_df['Kg Hechos'].apply(lambda x: f"{x:.2f}")
                prod_df['Costo Total'] = prod_df['Costo Total'].apply(lambda x: f"${x:,.0f}")
                prod_df['Costo Unitario'] = prod_df['Costo Unitario'].apply(lambda x: f"${x:,.0f}")
                st.dataframe(prod_df, use_container_width=True, hide_index=True)
            else:
                st.info("No hay productos con Kg > 0 para esta recepción.")
        else:
            st.info("No hay información de productos para esta recepción.")

        # Líneas de análisis de calidad
        st.markdown("#### 🔬 Análisis de Calidad (Líneas individuales)")
        lineas = rec.get('lineas_analisis', [])
        tipo_fruta = rec.get('tipo_fruta', '') or ''
        
        tipo_fruta_lower = tipo_fruta.lower()
        es_frutilla = 'frutilla' in tipo_fruta_lower
        es_arandano = 'ar' in tipo_fruta_lower and 'ndano' in tipo_fruta_lower
        es_frambuesa = 'frambuesa' in tipo_fruta_lower
        es_mora = 'mora' in tipo_fruta_lower
        
        if lineas:
            lineas_df = pd.DataFrame(lineas)
            
            if 'fecha_hora' in lineas_df.columns:
                lineas_df['fecha_hora'] = pd.to_datetime(lineas_df['fecha_hora'], errors='coerce').dt.strftime('%d/%m/%Y %H:%M')
            
            if es_frutilla:
                col_rename = {
                    'fecha_hora': 'Fecha/Hora', 'calificacion': 'Calif.', 'total_defectos_pct': '% Def.',
                    'n_palet': 'Palet', 'dano_mecanico': 'D.Mec(g)', 'hongos': 'Hongos(g)',
                    'inmadura': 'Inmad(g)', 'sobremadura': 'Sobrem(g)', 'dano_insecto': 'D.Ins(g)',
                    'deformes': 'Defor(g)', 'temperatura': 'Temp°C'
                }
                cols_show = ['Fecha/Hora', 'Palet', 'Calif.', '% Def.', 'D.Mec(g)', 'Hongos(g)', 'Inmad(g)', 'Sobrem(g)', 'D.Ins(g)', 'Temp°C']
            elif es_arandano:
                col_rename = {
                    'fecha_hora': 'Fecha/Hora', 'calificacion': 'Calif.', 'total_defectos_pct': '% Def.',
                    'n_palet': 'Palet', 'fruta_verde': 'F.Verde(g)', 'hongos': 'Hongos(g)',
                    'inmadura': 'Inmad(g)', 'sobremadura': 'Sobrem(g)', 'dano_insecto': 'D.Ins(g)',
                    'deshidratado': 'Deshid(g)', 'herida_partida': 'Herida(g)', 'temperatura': 'Temp°C'
                }
                cols_show = ['Fecha/Hora', 'Palet', 'Calif.', '% Def.', 'F.Verde(g)', 'Deshid(g)', 'Hongos(g)', 'Inmad(g)', 'Sobrem(g)', 'Herida(g)', 'Temp°C']
            elif es_frambuesa or es_mora:
                col_rename = {
                    'fecha_hora': 'Fecha/Hora', 'calificacion': 'Calif.', 'total_defectos_pct': '% Def.',
                    'n_palet': 'Palet', 'hongos': 'Hongos(g)', 'inmadura': 'Inmad(g)',
                    'sobremadura': 'Sobrem(g)', 'deshidratado': 'Deshid(g)', 'crumble': 'Crumble(g)', 'temperatura': 'Temp°C'
                }
                cols_show = ['Fecha/Hora', 'Palet', 'Calif.', '% Def.', 'Hongos(g)', 'Inmad(g)', 'Sobrem(g)', 'Deshid(g)', 'Crumble(g)', 'Temp°C']
            else:
                col_rename = {
                    'fecha_hora': 'Fecha/Hora', 'calificacion': 'Calif.', 'total_defectos_pct': '% Def.',
                    'n_palet': 'Palet', 'hongos': 'Hongos(g)', 'inmadura': 'Inmad(g)',
                    'sobremadura': 'Sobrem(g)', 'deshidratado': 'Deshid(g)', 'temperatura': 'Temp°C'
                }
                cols_show = ['Fecha/Hora', 'Palet', 'Calif.', '% Def.', 'Hongos(g)', 'Inmad(g)', 'Sobrem(g)', 'Temp°C']
            
            lineas_df = lineas_df.rename(columns=col_rename)
            lineas_df = lineas_df[[c for c in cols_show if c in lineas_df.columns]]
            
            for col in lineas_df.columns:
                if col not in ['Fecha/Hora', 'Palet', 'Calif.']:
                    lineas_df[col] = lineas_df[col].apply(lambda x: f"{float(x):.2f}" if pd.notna(x) else "0.00")
            
            st.dataframe(lineas_df, use_container_width=True, hide_index=True)
            
            # Gráfico de defectos
            st.markdown("#### 📊 Total de Defectos por Tipo (suma de todas las líneas)")
            lineas_orig = pd.DataFrame(rec.get('lineas_analisis', []))
            
            defectos = []
            if es_frutilla:
                defectos = [
                    {"Defecto": "Daño Mecánico", "Gramos": float(lineas_orig.get('dano_mecanico', pd.Series([0])).sum())},
                    {"Defecto": "Hongos", "Gramos": float(lineas_orig.get('hongos', pd.Series([0])).sum())},
                    {"Defecto": "Inmadura", "Gramos": float(lineas_orig.get('inmadura', pd.Series([0])).sum())},
                    {"Defecto": "Sobremadura", "Gramos": float(lineas_orig.get('sobremadura', pd.Series([0])).sum())},
                    {"Defecto": "Daño Insecto", "Gramos": float(lineas_orig.get('dano_insecto', pd.Series([0])).sum())},
                    {"Defecto": "Deformes", "Gramos": float(lineas_orig.get('deformes', pd.Series([0])).sum())}
                ]
            elif es_arandano:
                defectos = [
                    {"Defecto": "Fruta Verde", "Gramos": float(lineas_orig.get('fruta_verde', pd.Series([0])).sum())},
                    {"Defecto": "Deshidratado", "Gramos": float(lineas_orig.get('deshidratado', pd.Series([0])).sum())},
                    {"Defecto": "Inmadura", "Gramos": float(lineas_orig.get('inmadura', pd.Series([0])).sum())},
                    {"Defecto": "Sobremadura", "Gramos": float(lineas_orig.get('sobremadura', pd.Series([0])).sum())},
                    {"Defecto": "Hongos", "Gramos": float(lineas_orig.get('hongos', pd.Series([0])).sum())},
                    {"Defecto": "Herida/Partida", "Gramos": float(lineas_orig.get('herida_partida', pd.Series([0])).sum())},
                    {"Defecto": "Daño Insecto", "Gramos": float(lineas_orig.get('dano_insecto', pd.Series([0])).sum())}
                ]
            elif es_frambuesa or es_mora:
                defectos = [
                    {"Defecto": "Hongos", "Gramos": float(lineas_orig.get('hongos', pd.Series([0])).sum())},
                    {"Defecto": "Inmadura", "Gramos": float(lineas_orig.get('inmadura', pd.Series([0])).sum())},
                    {"Defecto": "Sobremadura", "Gramos": float(lineas_orig.get('sobremadura', pd.Series([0])).sum())},
                    {"Defecto": "Deshidratado", "Gramos": float(lineas_orig.get('deshidratado', pd.Series([0])).sum())},
                    {"Defecto": "Crumble", "Gramos": float(lineas_orig.get('crumble', pd.Series([0])).sum())}
                ]
            else:
                defectos = [
                    {"Defecto": "Hongos", "Gramos": float(lineas_orig.get('hongos', pd.Series([0])).sum())},
                    {"Defecto": "Inmadura", "Gramos": float(lineas_orig.get('inmadura', pd.Series([0])).sum())},
                    {"Defecto": "Sobremadura", "Gramos": float(lineas_orig.get('sobremadura', pd.Series([0])).sum())},
                    {"Defecto": "Deshidratado", "Gramos": float(lineas_orig.get('deshidratado', pd.Series([0])).sum())}
                ]
            
            defectos = [d for d in defectos if d["Gramos"] > 0]
            
            if defectos:
                df_defectos = pd.DataFrame(defectos)
                chart_def = alt.Chart(df_defectos).mark_bar().encode(
                    x=alt.X('Defecto:N', sort=None, axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y('Gramos:Q', title='Gramos')
                ).properties(width=700, height=350)
                st.altair_chart(chart_def, use_container_width=True)
            else:
                st.info("No hay defectos registrados para esta recepción.")
        else:
            st.info("No hay líneas de análisis de calidad para esta recepción.")
    else:
        st.info("No hay recepciones disponibles con los filtros seleccionados.")

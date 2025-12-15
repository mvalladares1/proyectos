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

# --- Funciones de formateo chileno ---
def fmt_fecha(fecha_str):
    """Convierte fecha ISO a formato DD/MM/AAAA"""
    if not fecha_str:
        return ""
    try:
        if isinstance(fecha_str, str):
            # Manejar formato con hora
            if " " in fecha_str:
                fecha_str = fecha_str.split(" ")[0]
            elif "T" in fecha_str:
                fecha_str = fecha_str.split("T")[0]
            dt = datetime.strptime(fecha_str, "%Y-%m-%d")
        else:
            dt = fecha_str
        return dt.strftime("%d/%m/%Y")
    except:
        return str(fecha_str)

def fmt_numero(valor, decimales=0):
    """Formatea número con punto como miles y coma como decimal"""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "0"
    try:
        if decimales > 0:
            # Con decimales: 1.234,56
            formatted = f"{valor:,.{decimales}f}"
        else:
            # Sin decimales: 1.234
            formatted = f"{valor:,.0f}"
        # Intercambiar: coma -> temporal, punto -> coma, temporal -> punto
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except:
        return str(valor)

def fmt_dinero(valor, decimales=0):
    """Formatea valor monetario con símbolo $"""
    return f"${fmt_numero(valor, decimales)}"

st.set_page_config(page_title="Recepciones", page_icon="📥", layout="wide")

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
# Estados para pestaña de gestión
if 'gestion_data' not in st.session_state:
    st.session_state.gestion_data = None
if 'gestion_overview' not in st.session_state:
    st.session_state.gestion_overview = None

# --- Funciones auxiliares para gestión ---
def get_validation_icon(status):
    """Retorna icono según estado de validación."""
    return {
        'Validada': '✅',
        'Lista para validar': '🟡',
        'Confirmada': '🔵',
        'En espera': '⏳',
        'Borrador': '⚪',
        'Cancelada': '❌'
    }.get(status, '⚪')

def get_qc_icon(status):
    """Retorna icono según estado de QC."""
    return {
        'Con QC Aprobado': '✅',
        'Con QC Pendiente': '🟡',
        'QC Fallido': '🔴',
        'Sin QC': '⚪'
    }.get(status, '⚪')

# === TABS PRINCIPALES ===
tab_kpis, tab_gestion = st.tabs(["📊 KPIs y Calidad", "📋 Gestión de Recepciones"])

# =====================================================
#           TAB 1: KPIs Y CALIDAD (Código existente)
# =====================================================
with tab_kpis:
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", datetime.now() - timedelta(days=7), key="fecha_inicio_recepcion", format="DD/MM/YYYY")
    with col2:
        fecha_fin = st.date_input("Fecha fin", datetime.now(), key="fecha_fin_recepcion", format="DD/MM/YYYY")

    # Checkbox para filtrar solo recepciones en estado "hecho"
    solo_hechas = st.checkbox("Solo recepciones hechas", value=True, key="solo_hechas_recepcion", 
                              help="Activa para ver solo recepciones completadas/validadas. Desactiva para ver todas las recepciones (en proceso, borrador, etc.)")

    if st.button("Consultar Recepciones", key="btn_consultar_recepcion"):
        params = {
            "username": username,
            "password": password,
            "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
            "fecha_fin": fecha_fin.strftime("%Y-%m-%d"),
            "solo_hechas": solo_hechas
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
        st.metric("Total Kg Recepcionados MP", fmt_numero(total_kg_mp, 2))
    with top_cols[1]:
        st.metric("Costo Total MP", fmt_dinero(total_costo_mp))
    with top_cols[2]:
        st.metric("Bandejas recepcionadas", fmt_numero(total_bandejas, 2))

    bot_cols = st.columns([1,1])
    with bot_cols[0]:
        st.metric("Promedio % IQF", f"{fmt_numero(prom_iqf, 2)}%")
    with bot_cols[1]:
        st.metric("Promedio % Block", f"{fmt_numero(prom_block, 2)}%")
    st.markdown(f"**Clasificación más frecuente:** {clasif}")

    # --- Tabla Resumen por Tipo Fruta / Manejo ---
    st.markdown("---")
    st.subheader("📊 Resumen por Tipo de Fruta y Manejo")
    
    # Agrupar por Tipo Fruta → Manejo
    def _normalize_cat(c):
        if not c:
            return ''
        cu = c.strip().upper()
        return 'BANDEJAS' if 'BANDEJ' in cu else cu
    
    # Colores por tipo de fruta
    colores_fruta = {
        'Arándano': '#4A90D9',
        'Frambuesa': '#E74C3C', 
        'Frutilla': '#E91E63',
        'Mora': '#9B59B6',
        'Cereza': '#C0392B',
        'Grosella': '#8E44AD'
    }
    
    agrup = {}
    for _, row in df.iterrows():
        tipo = (row.get('tipo_fruta') or '').strip()
        if not tipo:
            continue
        
        if tipo not in agrup:
            agrup[tipo] = {}
        
        iqf_val = row.get('total_iqf', 0) or 0
        block_val = row.get('total_block', 0) or 0
        manejos_en_rec = set()
        
        for p in row.get('productos', []) or []:
            cat = _normalize_cat(p.get('Categoria', ''))
            if cat == 'BANDEJAS':
                continue
            
            manejo = (p.get('Manejo') or '').strip()
            if not manejo:
                manejo = 'Sin Manejo'
            
            manejos_en_rec.add(manejo)
            
            if manejo not in agrup[tipo]:
                agrup[tipo][manejo] = {'kg': 0.0, 'costo': 0.0, 'iqf_vals': [], 'block_vals': []}
            
            agrup[tipo][manejo]['kg'] += p.get('Kg Hechos', 0) or 0
            agrup[tipo][manejo]['costo'] += p.get('Costo Total', 0) or 0
        
        for manejo in manejos_en_rec:
            if manejo in agrup[tipo]:
                agrup[tipo][manejo]['iqf_vals'].append(iqf_val)
                agrup[tipo][manejo]['block_vals'].append(block_val)
    
    # Construir tabla con columnas de Streamlit para mejor visualización
    if agrup:
        # Construir los datos de la tabla
        tabla_rows = []
        total_kg_tabla = 0
        total_costo_tabla = 0
        
        for tipo in sorted(agrup.keys(), key=lambda t: sum(m['kg'] for m in agrup[t].values()), reverse=True):
            tipo_kg = sum(m['kg'] for m in agrup[tipo].values())
            tipo_costo = sum(m['costo'] for m in agrup[tipo].values())
            tipo_costo_prom = tipo_costo / tipo_kg if tipo_kg > 0 else 0
            total_kg_tabla += tipo_kg
            total_costo_tabla += tipo_costo
            
            # Emoji por tipo de fruta
            emoji_fruta = {'Arándano': '🫐', 'Frambuesa': '🍒', 'Frutilla': '🍓', 'Mora': '🫐', 'Cereza': '🍒'}.get(tipo, '🍇')
            
            # Fila de Tipo Fruta (totalizador)
            tabla_rows.append({
                'tipo': 'fruta',
                'Descripción': tipo,
                'Kg': tipo_kg,
                'Costo Total': tipo_costo,
                'Costo/Kg': tipo_costo_prom,
                '% IQF': None,
                '% Block': None
            })
            
            # Filas de Manejo
            for manejo in sorted(agrup[tipo].keys(), key=lambda m: agrup[tipo][m]['kg'], reverse=True):
                v = agrup[tipo][manejo]
                kg = v['kg']
                costo = v['costo']
                costo_prom = costo / kg if kg > 0 else 0
                prom_iqf = sum(v['iqf_vals']) / len(v['iqf_vals']) if v['iqf_vals'] else 0
                prom_block = sum(v['block_vals']) / len(v['block_vals']) if v['block_vals'] else 0
                
                if 'orgánico' in manejo.lower() or 'organico' in manejo.lower():
                    icono = '🌱'
                elif 'convencional' in manejo.lower():
                    icono = '🏭'
                else:
                    icono = '📋'
                
                tabla_rows.append({
                    'tipo': 'manejo',
                    'Descripción': f"    → {manejo}",
                    'Kg': kg,
                    'Costo Total': costo,
                    'Costo/Kg': costo_prom,
                    '% IQF': prom_iqf,
                    '% Block': prom_block
                })
        
        # Fila total
        tabla_rows.append({
            'tipo': 'total',
            'Descripción': 'TOTAL GENERAL',
            'Kg': total_kg_tabla,
            'Costo Total': total_costo_tabla,
            'Costo/Kg': None,
            '% IQF': None,
            '% Block': None
        })
        
        # Crear DataFrame
        df_resumen = pd.DataFrame(tabla_rows)
        
        # Formatear para mostrar (formato chileno: punto miles, coma decimal)
        df_display = df_resumen.copy()
        df_display['Kg'] = df_display['Kg'].apply(lambda x: fmt_numero(x, 0) if pd.notna(x) else "—")
        df_display['Costo Total'] = df_display['Costo Total'].apply(lambda x: fmt_dinero(x) if pd.notna(x) else "—")
        df_display['Costo/Kg'] = df_display['Costo/Kg'].apply(lambda x: fmt_dinero(x) if pd.notna(x) and x > 0 else "—")
        df_display['% IQF'] = df_display['% IQF'].apply(lambda x: f"{fmt_numero(x, 1)}%" if pd.notna(x) and x > 0 else "—")
        df_display['% Block'] = df_display['% Block'].apply(lambda x: f"{fmt_numero(x, 1)}%" if pd.notna(x) and x > 0 else "—")
        
        # Mostrar usando columnas estilizadas
        df_show = df_display[['Descripción', 'Kg', 'Costo Total', 'Costo/Kg', '% IQF', '% Block']]
        
        # Usar st.dataframe con column_config para mejor visualización
        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Descripción': st.column_config.TextColumn('Tipo / Manejo', width='large'),
                'Kg': st.column_config.TextColumn('Kg', width='small'),
                'Costo Total': st.column_config.TextColumn('Costo Total', width='medium'),
                'Costo/Kg': st.column_config.TextColumn('$/Kg', width='small'),
                '% IQF': st.column_config.TextColumn('% IQF', width='small'),
                '% Block': st.column_config.TextColumn('% Block', width='small'),
            }
        )

    # --- Botones de descarga de informe PDF ---
    st.markdown("---")
    st.subheader("📥 Descargar Informe de Recepciones")
    informe_cols = st.columns([1,1,1])
    params = {
        'username': username,
        'password': password,
        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
        'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
        'solo_hechas': solo_hechas
    }
    # Botón 1: semana seleccionada
    with informe_cols[0]:
        if st.button("Descargar informe (Semana seleccionada)"):
            try:
                with st.spinner("Generando informe PDF..."):
                    resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/report", params={**params, 'include_prev_week': False, 'include_month_accum': False}, timeout=120)
                if resp.status_code == 200:
                    pdf_bytes = resp.content
                    # sanitizar filename
                    fname = f"informe_{params['fecha_inicio']}_a_{params['fecha_fin']}.pdf".replace('/', '-')
                    st.download_button("Descargar PDF (Semana)", data=pdf_bytes, file_name=fname, mime='application/pdf')
                else:
                    st.error(f"Error al generar informe: {resp.status_code} - {resp.text}")
            except Exception as e:
                st.error(f"Error al solicitar informe: {e}")

    # Botón 2: semana + resumen anterior + acumulado parcial mes
    with informe_cols[1]:
        if st.button("Descargar informe (Semana + resumen)"):
            try:
                with st.spinner("Generando informe PDF con resumen..."):
                    resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/report", params={**params, 'include_prev_week': True, 'include_month_accum': True}, timeout=180)
                if resp.status_code == 200:
                    pdf_bytes = resp.content
                    fname = f"informe_{params['fecha_inicio']}_a_{params['fecha_fin']}_resumen.pdf".replace('/', '-')
                    st.download_button("Descargar PDF (Semana+Resumen)", data=pdf_bytes, file_name=fname, mime='application/pdf')
                else:
                    st.error(f"Error al generar informe: {resp.status_code} - {resp.text}")
            except Exception as e:
                st.error(f"Error al solicitar informe: {e}")

    # Botón 3: Resumen del período completo seleccionado
    with informe_cols[2]:
        if st.button("Descargar informe (Período completo)"):
            try:
                with st.spinner("Generando informe PDF del período..."):
                    resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/report", params={**params, 'include_prev_week': False, 'include_month_accum': False}, timeout=120)
                if resp.status_code == 200:
                    pdf_bytes = resp.content
                    fname = f"informe_periodo_{params['fecha_inicio']}_a_{params['fecha_fin']}.pdf".replace('/', '-')
                    st.download_button("Descargar PDF (Período)", data=pdf_bytes, file_name=fname, mime='application/pdf')
                else:
                    st.error(f"Error al generar informe: {resp.status_code} - {resp.text}")
            except Exception as e:
                st.error(f"Error al solicitar informe: {e}")

    # Descripción de opciones
    st.caption("**Opciones:** Semana = rango seleccionado | Semana+Resumen = incluye semana anterior y acumulado mensual | Período = resumen del rango sin comparativos")

    # Filtros adicionales
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        tipos_fruta = df['tipo_fruta'].dropna().unique().tolist()
        tipos_fruta = sorted([t for t in tipos_fruta if t])
        tipo_fruta_filtro = st.multiselect("Filtrar por Tipo de Fruta", tipos_fruta, key="tipo_fruta_filtro")
    with col_f2:
        clasifs = df['calific_final'].dropna().unique().tolist()
        clasifs = sorted([c for c in clasifs if c])
        clasif_filtro = st.multiselect("Filtrar por Clasificación", clasifs, key="clasif_filtro")
    with col_f3:
        # Extraer valores únicos de Manejo de todos los productos
        manejos_set = set()
        for _, row in df.iterrows():
            if 'productos' in row and isinstance(row['productos'], list):
                for p in row['productos']:
                    manejo = (p.get('Manejo') or '').strip()
                    if manejo:
                        manejos_set.add(manejo)
        manejos = sorted(list(manejos_set))
        manejo_filtro = st.multiselect("Filtrar por Manejo", manejos, key="manejo_filtro")

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
    
    # Filtrar por Manejo (si el producto tiene el manejo seleccionado)
    if manejo_filtro:
        def tiene_manejo(row):
            if 'productos' in row and isinstance(row['productos'], list):
                for p in row['productos']:
                    manejo = (p.get('Manejo') or '').strip()
                    if manejo in manejo_filtro:
                        return True
            return False
        df_filtrada = df_filtrada[df_filtrada.apply(tiene_manejo, axis=1)]

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
    df_filtrada['tiene_calidad'] = df_filtrada['calific_final'].notna() & (df_filtrada['calific_final'] != '')
    cols_mostrar = [
        "albaran", "fecha", "productor", "tipo_fruta", "guia_despacho",
        "bandejas", "kg_recepcionados", "calific_final", "total_iqf", "total_block", "tiene_calidad"
    ]
    df_mostrar = df_filtrada[cols_mostrar].copy()
    df_mostrar.columns = [
        "Albarán", "Fecha", "Productor", "Tipo Fruta", "Guía Despacho",
        "Bandejas", "Kg Recepcionados", "Clasificación", "% IQF", "% Block", "Calidad"
    ]
    # Ajustar Kg Recepcionados para excluir las Bandejas (mostramos Kg fruta)
    # Convertir a numérico, restar bandejas y formatear
    df_mostrar["Bandejas"] = pd.to_numeric(df_mostrar["Bandejas"], errors='coerce').fillna(0.0)
    df_mostrar["Kg Recepcionados"] = pd.to_numeric(df_mostrar["Kg Recepcionados"], errors='coerce').fillna(0.0) - df_mostrar["Bandejas"]
    # Formatear fecha a DD/MM/AAAA
    df_mostrar["Fecha"] = df_mostrar["Fecha"].apply(fmt_fecha)
    # Formatear números con formato chileno
    df_mostrar["Kg Recepcionados"] = df_mostrar["Kg Recepcionados"].apply(lambda x: fmt_numero(x, 2))
    df_mostrar["Bandejas"] = df_mostrar["Bandejas"].apply(lambda x: fmt_numero(x, 2))
    df_mostrar["% IQF"] = df_mostrar["% IQF"].apply(lambda x: fmt_numero(x, 2))
    df_mostrar["% Block"] = df_mostrar["% Block"].apply(lambda x: fmt_numero(x, 2))
    df_mostrar["Calidad"] = df_mostrar["Calidad"].apply(lambda x: "✅" if x else "❌")

    # Botones para exportar a CSV y Excel
    col_exp1, col_exp2 = st.columns([1,1])
    with col_exp1:
        csv = df_mostrar.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar CSV", csv, "recepciones.csv", "text/csv", key="download_csv")
    with col_exp2:
        # Botón 1: Excel rápido (resumen por recepción, local)
        excel_buffer = io.BytesIO()
        if hasattr(df_mostrar, 'to_excel'):
            df_mostrar.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)
            st.download_button(
                "Descargar Excel (Resumen)",
                excel_buffer,
                "recepciones_resumen.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_resumen"
            )

    # Botón extra: descargar Excel DETALLADO (una fila por producto) desde el backend
    det_col1, det_col2 = st.columns([1,3])
    with det_col1:
        if st.button("Descargar Excel Detallado (Por Producto)"):
            try:
                with st.spinner("Generando Excel detallado en el servidor..."):
                    resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/report.xlsx", params={**params, 'include_prev_week': False, 'include_month_accum': False}, timeout=180)
                if resp.status_code == 200:
                    xlsx_bytes = resp.content
                    fname = f"recepciones_detalle_{params['fecha_inicio']}_a_{params['fecha_fin']}.xlsx".replace('/', '-')
                    st.download_button("Descargar Excel (Detallado)", xlsx_bytes, file_name=fname, mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                else:
                    st.error(f"Error al generar Excel detallado: {resp.status_code} - {resp.text}")
            except Exception as e:
                st.error(f"Error al solicitar Excel detallado: {e}")

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
        st.metric("Daño Mecánico", fmt_numero(df_filtrada['dano_mecanico'].mean(), 2))
        st.metric("Hongos", fmt_numero(df_filtrada['hongos'].mean(), 2))
    with col_d2:
        st.metric("Inmadura", fmt_numero(df_filtrada['inmadura'].mean(), 2))
        st.metric("Sobremadura", fmt_numero(df_filtrada['sobremadura'].mean(), 2))
    with col_d3:
        st.metric("Daño Insecto", fmt_numero(df_filtrada['dano_insecto'].mean(), 2))
        st.metric("Defecto Frutilla", fmt_numero(df_filtrada['defecto_frutilla'].mean(), 4))

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
            format_func=lambda i: f"{df_filtrada.loc[i, 'albaran']} - {df_filtrada.loc[i, 'productor']} - {fmt_fecha(df_filtrada.loc[i, 'fecha'])}",
            key="selectbox_recepcion"
        )
        st.session_state.idx_recepcion = idx
        rec = df_filtrada.loc[idx]
        st.markdown("---")
        st.markdown("### 📝 Detalle de Recepción")
        detalle_cols = st.columns(2)
        with detalle_cols[0]:
            st.write(f"**Albarán:** {rec['albaran']}")
            st.write(f"**Fecha:** {fmt_fecha(rec['fecha'])}")
            st.write(f"**Productor:** {rec['productor']}")
            st.write(f"**Tipo Fruta:** {rec['tipo_fruta']}")
            st.write(f"**Guía Despacho:** {rec['guia_despacho']}")
        with detalle_cols[1]:
            st.write(f"**Kg Recepcionados:** {fmt_numero(rec['kg_recepcionados'], 2)}")
            st.write(f"**Clasificación:** {rec['calific_final']}")
            st.write(f"**% IQF:** {fmt_numero(rec['total_iqf'], 2)}")
            st.write(f"**% Block:** {fmt_numero(rec['total_block'], 2)}")

        st.markdown("#### 📦 Productos de la Recepción")
        if 'productos' in rec and isinstance(rec['productos'], list) and rec['productos']:
            prod_df = pd.DataFrame(rec['productos'])
            prod_df = prod_df[prod_df['Kg Hechos'] > 0]
            if not prod_df.empty:
                # Quitar product_id de la vista
                if 'product_id' in prod_df.columns:
                    prod_df = prod_df.drop(columns=['product_id'])
                prod_df['Kg Hechos'] = prod_df['Kg Hechos'].apply(lambda x: fmt_numero(x, 2))
                prod_df['Costo Total'] = prod_df['Costo Total'].apply(lambda x: fmt_dinero(x))
                prod_df['Costo Unitario'] = prod_df['Costo Unitario'].apply(lambda x: fmt_dinero(x))
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
                    lineas_df[col] = lineas_df[col].apply(lambda x: fmt_numero(float(x), 2) if pd.notna(x) else "0,00")
            
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

# =====================================================
#           TAB 2: GESTIÓN DE RECEPCIONES
# =====================================================
with tab_gestion:
    st.subheader("📋 Gestión de Recepciones MP")
    st.caption("Monitoreo de estados de validación y control de calidad")
    
    # Filtros
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
    with col1:
        fecha_inicio_g = st.date_input("Desde", datetime.now() - timedelta(days=7), format="DD/MM/YYYY", key="gestion_desde")
    with col2:
        fecha_fin_g = st.date_input("Hasta", datetime.now(), format="DD/MM/YYYY", key="gestion_hasta")
    with col3:
        status_filter = st.selectbox("Estado", ["Todos", "Validada", "Lista para validar", "Confirmada", "En espera", "Borrador"])
    with col4:
        qc_filter = st.selectbox("Control Calidad", ["Todos", "Con QC Aprobado", "Con QC Pendiente", "Sin QC", "QC Fallido"])
    with col5:
        search_text = st.text_input("Buscar Albarán", placeholder="Ej: WH/IN/00123")
    
    if st.button("🔄 Consultar Gestión", type="primary", key="btn_gestion"):
        params = {
            "username": username, "password": password,
            "fecha_inicio": fecha_inicio_g.strftime("%Y-%m-%d"),
            "fecha_fin": fecha_fin_g.strftime("%Y-%m-%d")
        }
        if status_filter != "Todos":
            params["status_filter"] = status_filter
        if qc_filter != "Todos":
            params["qc_filter"] = qc_filter
        if search_text:
            params["search_text"] = search_text
        
        with st.spinner("Cargando datos de gestión..."):
            try:
                # Cargar overview
                resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/gestion/overview", params={
                    "username": username, "password": password,
                    "fecha_inicio": fecha_inicio_g.strftime("%Y-%m-%d"),
                    "fecha_fin": fecha_fin_g.strftime("%Y-%m-%d")
                }, timeout=120)
                if resp.status_code == 200:
                    st.session_state.gestion_overview = resp.json()
                
                # Cargar recepciones
                resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/gestion", params=params, timeout=120)
                if resp.status_code == 200:
                    st.session_state.gestion_data = resp.json()
            except Exception as e:
                st.error(f"Error: {e}")
    
    overview = st.session_state.gestion_overview
    data_gestion = st.session_state.gestion_data
    
    if overview:
        # KPIs
        st.markdown("### 📊 Resumen")
        kpi_cols = st.columns(6)
        with kpi_cols[0]:
            st.metric("Total Recepciones", overview['total_recepciones'])
        with kpi_cols[1]:
            st.metric("Validadas ✅", overview['validadas'])
        with kpi_cols[2]:
            st.metric("Listas para validar 🟡", overview['listas_validar'])
        with kpi_cols[3]:
            st.metric("Con QC Aprobado ✅", overview['con_qc_aprobado'])
        with kpi_cols[4]:
            st.metric("Con QC Pendiente 🟡", overview['con_qc_pendiente'])
        with kpi_cols[5]:
            st.metric("Sin QC ⚪", overview['sin_qc'])
        
        st.markdown("---")
    
    if data_gestion:
        st.subheader(f"📋 Recepciones ({len(data_gestion)})")
        
        df_g = pd.DataFrame(data_gestion)
        
        # Filtros de tabla
        with st.expander("🔍 Filtros de tabla", expanded=True):
            fc1, fc2, fc3, fc4 = st.columns(4)
            with fc1:
                productores = sorted(df_g['partner'].dropna().unique())
                prod_filter = st.multiselect("Productor", productores, default=[], placeholder="Todos", key="gestion_prod")
            with fc2:
                valid_opts = ["Todos"] + list(df_g['validation_status'].unique())
                valid_filter = st.selectbox("Estado Validación", valid_opts, key="tbl_valid")
            with fc3:
                qc_opts = ["Todos"] + list(df_g['qc_status'].unique())
                qc_tbl_filter = st.selectbox("Estado QC", qc_opts, key="tbl_qc")
            with fc4:
                pend_filter = st.selectbox("Con Pendientes", ["Todos", "Sí", "No"], key="tbl_pend_g")
        
        # Leyenda
        st.caption("**Leyenda:** ✅ Completo | 🟡 Pendiente | 🔵 Confirmada | ⏳ En espera | ⚪ Sin datos | ❌ Cancelada/Fallido")
        
        # Aplicar filtros
        df_filtered = df_g.copy()
        if prod_filter:
            df_filtered = df_filtered[df_filtered['partner'].isin(prod_filter)]
        if valid_filter != "Todos":
            df_filtered = df_filtered[df_filtered['validation_status'] == valid_filter]
        if qc_tbl_filter != "Todos":
            df_filtered = df_filtered[df_filtered['qc_status'] == qc_tbl_filter]
        if pend_filter == "Sí":
            df_filtered = df_filtered[df_filtered['pending_users'].str.len() > 0]
        elif pend_filter == "No":
            df_filtered = df_filtered[df_filtered['pending_users'].str.len() == 0]
        
        st.caption(f"Mostrando {len(df_filtered)} de {len(df_g)} recepciones")
        
        # Vista
        vista = st.radio("Vista", ["📊 Tabla compacta", "📋 Detalle con expanders"], horizontal=True, label_visibility="collapsed", key="vista_gestion")
        
        if vista == "📊 Tabla compacta":
            # Tabla compacta
            df_display = df_filtered[['name', 'date', 'partner', 'tipo_fruta', 'validation_status', 'qc_status', 'pending_users']].copy()
            
            df_display['Validación'] = df_display['validation_status'].apply(get_validation_icon)
            df_display['QC'] = df_display['qc_status'].apply(get_qc_icon)
            df_display['Pendientes'] = df_display['pending_users'].apply(lambda x: '⏳' if x else '✓')
            df_display['Fecha'] = df_display['date'].apply(fmt_fecha)
            
            df_final = df_display[['name', 'Fecha', 'partner', 'tipo_fruta', 'Validación', 'QC', 'Pendientes']].copy()
            df_final.columns = ['Albarán', 'Fecha', 'Productor', 'Tipo Fruta', 'Validación', 'QC', 'Pend.']
            
            st.dataframe(
                df_final, 
                use_container_width=True, 
                hide_index=True, 
                height=450,
                column_config={
                    "Albarán": st.column_config.TextColumn(width="medium"),
                    "Fecha": st.column_config.TextColumn(width="small"),
                    "Productor": st.column_config.TextColumn(width="large"),
                    "Tipo Fruta": st.column_config.TextColumn(width="small"),
                    "Validación": st.column_config.TextColumn(width="small"),
                    "QC": st.column_config.TextColumn(width="small"),
                    "Pend.": st.column_config.TextColumn(width="small"),
                }
            )
        else:
            # Vista con expanders y paginación
            ITEMS_PER_PAGE = 10
            total_items = len(df_filtered)
            total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
            
            if 'gestion_page' not in st.session_state:
                st.session_state.gestion_page = 1
            
            col_prev, col_info, col_next = st.columns([1, 2, 1])
            with col_prev:
                if st.button("⬅️ Anterior", disabled=st.session_state.gestion_page <= 1, key="prev_g"):
                    st.session_state.gestion_page -= 1
                    st.rerun()
            with col_info:
                st.markdown(f"**Página {st.session_state.gestion_page} de {total_pages}** ({total_items} recepciones)")
            with col_next:
                if st.button("Siguiente ➡️", disabled=st.session_state.gestion_page >= total_pages, key="next_g"):
                    st.session_state.gestion_page += 1
                    st.rerun()
            
            start_idx = (st.session_state.gestion_page - 1) * ITEMS_PER_PAGE
            end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
            
            for idx, row in df_filtered.iloc[start_idx:end_idx].iterrows():
                valid_icon = get_validation_icon(row['validation_status'])
                qc_icon = get_qc_icon(row['qc_status'])
                pend_icon = "⏳" if row.get('pending_users', '') else "✓"
                
                fecha_rec = fmt_fecha(row.get('date', ''))
                header = f"{valid_icon}{qc_icon}{pend_icon} **{row['name']}** | {fecha_rec} | {row['partner'][:30]} | {row.get('tipo_fruta', '-')}"
                
                with st.expander(header, expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**Fecha:** {fmt_fecha(row['date'])}")
                        st.markdown(f"**Productor:** {row['partner']}")
                        st.markdown(f"**Guía Despacho:** {row.get('guia_despacho', '-')}")
                    with col2:
                        st.markdown(f"**Estado:** {valid_icon} {row['validation_status']}")
                        st.markdown(f"**Tipo Fruta:** {row.get('tipo_fruta', '-')}")
                    with col3:
                        st.markdown(f"**Control Calidad:** {qc_icon} {row['qc_status']}")
                        if row.get('calific_final'):
                            st.markdown(f"**Calificación:** {row['calific_final']}")
                        if row.get('jefe_calidad'):
                            st.markdown(f"**Jefe Calidad:** {row['jefe_calidad']}")
                    
                    st.markdown("---")
                    
                    # Detalle de pendientes/validaciones
                    c1, c2 = st.columns(2)
                    with c1:
                        validated = row.get('validated_by', '')
                        if validated:
                            st.success(f"✅ **Validado por:** {validated}")
                        else:
                            if row['validation_status'] == 'Validada':
                                st.success("✅ Recepción validada")
                            else:
                                st.info("Pendiente de validación")
                    with c2:
                        pending = row.get('pending_users', '')
                        if pending:
                            st.warning(f"⏳ **Pendiente de:** {pending}")
                        else:
                            st.success("✓ Sin pendientes de aprobación")
        
        # Export
        st.markdown("---")
        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_g.to_excel(writer, sheet_name='Gestión Recepciones', index=False)
            st.download_button("📥 Descargar Excel", buffer.getvalue(), "gestion_recepciones.xlsx", 
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except:
            st.download_button("📥 Descargar CSV", df_g.to_csv(index=False).encode('utf-8'), "gestion_recepciones.csv", "text/csv")
    else:
        st.info("Haz clic en **Consultar Gestión** para cargar los datos.")
        
        with st.expander("ℹ️ ¿Cómo funciona?"):
            st.markdown("""
            ### Gestión de Recepciones MP
            
            Este módulo te permite monitorear el estado de las recepciones de materia prima:
            
            | Estado | Descripción |
            |--------|-------------|
            | ✅ **Validada** | Recepción completada y validada en Odoo |
            | 🟡 **Lista para validar** | Productos asignados, lista para validar |
            | 🔵 **Confirmada** | Confirmada, esperando disponibilidad |
            | ⏳ **En espera** | Esperando otra operación |
            | ⚪ **Borrador** | En estado borrador |
            
            ### Control de Calidad
            
            | Estado | Descripción |
            |--------|-------------|
            | ✅ **Con QC Aprobado** | Tiene control de calidad completado |
            | 🟡 **Con QC Pendiente** | Tiene QC pero está pendiente |
            | 🔴 **QC Fallido** | El control de calidad falló |
            | ⚪ **Sin QC** | No tiene control de calidad asociado |
            """)


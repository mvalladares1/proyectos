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
from shared.auth import proteger_modulo, get_credenciales
from backend.services.aprobaciones_service import get_aprobaciones, save_aprobaciones, remove_aprobaciones

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
if not proteger_modulo("recepciones"):
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

# --- Funciones con caché para llamadas API ---
@st.cache_data(ttl=120, show_spinner=False)
def fetch_gestion_data(_username, _password, fecha_inicio, fecha_fin, status_filter=None, qc_filter=None, search_text=None):
    """Obtiene datos de gestión con caché de 2 minutos."""
    params = {
        "username": _username, "password": _password,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin
    }
    if status_filter and status_filter != "Todos":
        params["status_filter"] = status_filter
    if qc_filter and qc_filter != "Todos":
        params["qc_filter"] = qc_filter
    if search_text:
        params["search_text"] = search_text
    
    try:
        resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/gestion", params=params, timeout=120)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

@st.cache_data(ttl=120, show_spinner=False)
def fetch_gestion_overview(_username, _password, fecha_inicio, fecha_fin):
    """Obtiene overview con caché de 2 minutos."""
    try:
        resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/gestion/overview", params={
            "username": _username, "password": _password,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        }, timeout=60)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

# === TABS PRINCIPALES ===
tab_kpis, tab_gestion, tab_curva, tab_aprobaciones = st.tabs(["📊 KPIs y Calidad", "📋 Gestión de Recepciones", "📈 Curva de Abastecimiento", "📥 Aprobaciones MP"])

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

    # Checkboxes para filtrar por origen (RFP / VILKÚN)
    st.markdown("**Origen de recepciones:**")
    col_orig1, col_orig2 = st.columns(2)
    with col_orig1:
        check_rfp = st.checkbox("🏭 RFP (Rio Futuro Procesos)", value=True, key="check_rfp",
                                help="Recepciones de la planta Rio Futuro Procesos")
    with col_orig2:
        check_vilkun = st.checkbox("🌿 VILKÚN", value=True, key="check_vilkun",
                                   help="Recepciones de la planta Vilkún")

    if st.button("Consultar Recepciones", key="btn_consultar_recepcion"):
        # Construir lista de orígenes según checkboxes
        origen_list = []
        if check_rfp:
            origen_list.append("RFP")
        if check_vilkun:
            origen_list.append("VILKUN")
        
        if not origen_list:
            st.warning("Debes seleccionar al menos un origen (RFP o VILKÚN)")
        else:
            # Guardar filtros usados en session_state
            st.session_state.origen_filtro_usado = origen_list.copy()
            
            params = {
                "username": username,
                "password": password,
                "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
                "fecha_fin": fecha_fin.strftime("%Y-%m-%d"),
                "solo_hechas": solo_hechas,
                "origen": origen_list
            }
            api_url = f"{API_URL}/api/v1/recepciones-mp/"
            
            # Debug removido - ya no mostrar mensaje de consultando origen
            
            try:
                resp = requests.get(api_url, params=params, timeout=60)
                if resp.status_code == 200:
                    data = resp.json()
                    df = pd.DataFrame(data)
                    if not df.empty:
                        st.session_state.df_recepcion = df
                        st.session_state.idx_recepcion = None
                        st.success(f"✅ Se encontraron {len(df)} recepciones para origen: {origen_list}")
                    else:
                        st.session_state.df_recepcion = None
                        st.session_state.idx_recepcion = None
                        st.warning(f"No se encontraron recepciones para origen: {origen_list} en el rango de fechas seleccionado.")
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
        # --- Cargar exclusiones de valorización ---
        import json
        exclusiones_ids = []
        try:
            exclusions_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shared", "exclusiones.json")
            if os.path.exists(exclusions_file):
                with open(exclusions_file, 'r') as f:
                    exclusiones = json.load(f)
                    exclusiones_ids = exclusiones.get("recepciones", [])
        except:
            pass
        
        # --- KPIs Consolidados ---
        st.subheader("📊 KPIs Consolidados")
        # Calcular Totales separando por categoría de producto (BANDEJAS)
        total_kg_mp = 0.0
        total_costo_mp = 0.0
        total_bandejas = 0.0
        recepciones_excluidas = 0
        
        # recorrer todas las recepciones y sus productos
        for _, row in df.iterrows():
            # Asegurarnos que solo consideramos recepciones que sean fruta
            tipo_fruta_row = (row.get('tipo_fruta') or "").strip()
            if not tipo_fruta_row:
                continue
            
            # Verificar si esta recepción está excluida de valorización
            recep_id = row.get('id') or row.get('picking_id')
            recep_name = row.get('albaran', '')
            excluir_costo = recep_id in exclusiones_ids or recep_name in exclusiones_ids
            if excluir_costo:
                recepciones_excluidas += 1
            
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
                        # Solo sumar costo si NO está excluida
                        if not excluir_costo:
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
        
        # Obtener precios proyectados del Excel de abastecimiento
        # Filtrar por planta según los checkboxes de origen seleccionados
        precios_proyectados = {}
        try:
            # Construir lista de plantas para el filtro (mismo que origen_list)
            plantas_filtro = []
            if st.session_state.get('origen_filtro_usado'):
                plantas_filtro = st.session_state.origen_filtro_usado
            
            resp_precios = requests.get(
                f"{API_URL}/api/v1/recepciones-mp/abastecimiento/precios",
                params={"planta": plantas_filtro if plantas_filtro else None, "especie": None},
                timeout=30
            )
            if resp_precios.status_code == 200:
                for item in resp_precios.json():
                    especie = item.get('especie', '')
                    precio = item.get('precio_proyectado', 0)
                    precios_proyectados[especie] = precio
        except Exception as e:
            print(f"Error obteniendo precios proyectados: {e}")
    
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
            # IQF/Block son del QC de la recepción, asociados al tipo_fruta del QC
            iqf_val = row.get('total_iqf', 0) or 0
            block_val = row.get('total_block', 0) or 0
            tipo_fruta_qc = (row.get('tipo_fruta') or '').strip()  # Tipo de fruta del control de calidad
            
            # Verificar si esta recepción está excluida de valorización
            recep_id = row.get('id') or row.get('picking_id')
            recep_name = row.get('albaran', '')
            excluir_costo = recep_id in exclusiones_ids or recep_name in exclusiones_ids
            
            manejos_por_tipo = {}  # Rastrear manejos por tipo de fruta
        
            for p in row.get('productos', []) or []:
                cat = _normalize_cat(p.get('Categoria', ''))
                if cat == 'BANDEJAS':
                    continue
                
                # Usar el TipoFruta del producto, con fallback al tipo_fruta de la recepción
                tipo = (p.get('TipoFruta') or row.get('tipo_fruta') or '').strip()
                if not tipo:
                    continue
            
                manejo = (p.get('Manejo') or '').strip()
                if not manejo:
                    manejo = 'Sin Manejo'
                
                # Rastrear qué manejos tiene cada tipo de fruta
                if tipo not in manejos_por_tipo:
                    manejos_por_tipo[tipo] = set()
                manejos_por_tipo[tipo].add(manejo)
            
                if tipo not in agrup:
                    agrup[tipo] = {}
                    
                if manejo not in agrup[tipo]:
                    agrup[tipo][manejo] = {'kg': 0.0, 'costo': 0.0, 'iqf_vals': [], 'block_vals': []}
            
                agrup[tipo][manejo]['kg'] += p.get('Kg Hechos', 0) or 0
                # Solo sumar costo si NO está excluida
                if not excluir_costo:
                    agrup[tipo][manejo]['costo'] += p.get('Costo Total', 0) or 0
        
            # Agregar IQF/Block SOLO al tipo de fruta que corresponde al QC
            # (no a todos los productos, ya que IQF/Block son mediciones del tipo_fruta del QC)
            if tipo_fruta_qc and tipo_fruta_qc in manejos_por_tipo:
                for manejo in manejos_por_tipo[tipo_fruta_qc]:
                    if tipo_fruta_qc in agrup and manejo in agrup[tipo_fruta_qc]:
                        agrup[tipo_fruta_qc][manejo]['iqf_vals'].append(iqf_val)
                        agrup[tipo_fruta_qc][manejo]['block_vals'].append(block_val)


    
        # Construir tabla con columnas de Streamlit para mejor visualización
        if agrup:
            # Construir los datos de la tabla
            tabla_rows = []
            total_kg_tabla = 0
            total_costo_tabla = 0
        
            for tipo in sorted(agrup.keys(), key=lambda t: sum(m['kg'] for m in agrup[t].values()), reverse=True):
                tipo_kg = sum(m['kg'] for m in agrup[tipo].values())
                
                # Omitir tipos de fruta sin kg recepcionados
                if tipo_kg <= 0:
                    continue
                    
                tipo_costo = sum(m['costo'] for m in agrup[tipo].values())
                tipo_costo_prom = tipo_costo / tipo_kg if tipo_kg > 0 else 0
                total_kg_tabla += tipo_kg
                total_costo_tabla += tipo_costo
            
                # Emoji por tipo de fruta
                emoji_fruta = {'Arándano': '🫐', 'Frambuesa': '🍒', 'Frutilla': '🍓', 'Mora': '🫐', 'Cereza': '🍒'}.get(tipo, '🍇')
            
                # Fila de Tipo Fruta (totalizador)
                # Buscar precio proyectado para este tipo de fruta
                precio_proy_tipo = precios_proyectados.get(tipo, 0)
                
                tabla_rows.append({
                    'tipo': 'fruta',
                    'Descripción': tipo,
                    'Kg': tipo_kg,
                    'Costo Total': tipo_costo,
                    'Costo/Kg': tipo_costo_prom,
                    'Precio Proy': precio_proy_tipo,
                    '% IQF': None,
                    '% Block': None
                })
            
                # Filas de Manejo
                for manejo in sorted(agrup[tipo].keys(), key=lambda m: agrup[tipo][m]['kg'], reverse=True):
                    v = agrup[tipo][manejo]
                    kg = v['kg']
                    
                    # Omitir manejos con 0 kg
                    if kg <= 0:
                        continue
                        
                    costo = v['costo']
                    costo_prom = costo / kg if kg > 0 else 0
                    prom_iqf = sum(v['iqf_vals']) / len(v['iqf_vals']) if v['iqf_vals'] else 0
                    prom_block = sum(v['block_vals']) / len(v['block_vals']) if v['block_vals'] else 0
                    
                    # Buscar precio proyectado para la combinación tipo + manejo
                    # Formato del Excel: "Arándano Orgánico" o "Frambuesa Convencional"
                    manejo_norm = 'Orgánico' if 'org' in manejo.lower() else 'Convencional'
                    especie_manejo = f"{tipo} {manejo_norm}"
                    precio_proy_manejo = precios_proyectados.get(especie_manejo, precios_proyectados.get(tipo, 0))
                
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
                        'Precio Proy': precio_proy_manejo,
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
                'Precio Proy': None,
                '% IQF': None,
                '% Block': None
            })
        
            # Crear DataFrame
            df_resumen = pd.DataFrame(tabla_rows)
            
            # Calcular desviación de precio: (Costo/Kg - Precio Proy) / Precio Proy * 100
            def calcular_desviacion(row):
                costo_kg = row.get('Costo/Kg', 0) or 0
                precio_proy = row.get('Precio Proy', 0) or 0
                if precio_proy > 0 and costo_kg > 0:
                    desv = ((costo_kg - precio_proy) / precio_proy) * 100
                    return round(desv, 1)
                return None
            
            df_resumen['Desv_Num'] = df_resumen.apply(calcular_desviacion, axis=1)
            
            # Formatear desviación con colores (emoji + texto)
            def formatear_desviacion(desv):
                if desv is None or pd.isna(desv):
                    return "—"
                if desv <= 0:
                    # Pagando MENOS que lo proyectado = Favorable
                    return f"✓ {abs(desv):.1f}%"
                elif desv <= 3:
                    # 1-3%: Verde
                    return f"🟢 +{desv:.1f}%"
                elif desv <= 8:
                    # 3-8%: Amarillo
                    return f"🟡 +{desv:.1f}%"
                else:
                    # >8%: Rojo
                    return f"🔴 +{desv:.1f}%"
        
            # Formatear para mostrar (formato chileno: punto miles, coma decimal)
            df_display = df_resumen.copy()
            df_display['Kg'] = df_display['Kg'].apply(lambda x: fmt_numero(x, 0) if pd.notna(x) else "—")
            df_display['Costo Total'] = df_display['Costo Total'].apply(lambda x: fmt_dinero(x) if pd.notna(x) else "—")
            df_display['Costo/Kg'] = df_display['Costo/Kg'].apply(lambda x: fmt_dinero(x) if pd.notna(x) and x > 0 else "—")
            df_display['Precio Proy'] = df_display['Precio Proy'].apply(lambda x: fmt_dinero(x) if pd.notna(x) and x > 0 else "—")
            df_display['% Desv'] = df_display['Desv_Num'].apply(formatear_desviacion)
            df_display['% IQF'] = df_display['% IQF'].apply(lambda x: f"{fmt_numero(x, 1)}%" if pd.notna(x) and x > 0 else "—")
            df_display['% Block'] = df_display['% Block'].apply(lambda x: f"{fmt_numero(x, 1)}%" if pd.notna(x) and x > 0 else "—")
        
            # Mostrar usando columnas estilizadas
            df_show = df_display[['Descripción', 'Kg', 'Costo Total', 'Costo/Kg', 'Precio Proy', '% Desv', '% IQF', '% Block']]
        
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
                    'Precio Proy': st.column_config.TextColumn('PPTO', width='small'),
                    '% Desv': st.column_config.TextColumn('Desviación', width='small'),
                    '% IQF': st.column_config.TextColumn('% IQF', width='small'),
                    '% Block': st.column_config.TextColumn('% Block', width='small'),
                }
            )
            
            # Leyenda de colores para desviación de precio
            st.caption(
                "**Leyenda Desviación:** "
                "✓ Favorable (pagando menos) · "
                "🟢 +1% a +3% · "
                "🟡 +3% a +8% · "
                "🔴 >+8% sobre precio proyectado"
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

        # Aplicar filtros
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
        
        # Verificar si existe columna 'origen' (datos antiguos pueden no tenerla)
        if 'origen' not in df_filtrada.columns:
            df_filtrada['origen'] = 'RFP'  # Default para datos antiguos
        
        cols_mostrar = [
            "albaran", "fecha", "productor", "tipo_fruta", "origen", "guia_despacho",
            "bandejas", "kg_recepcionados", "calific_final", "total_iqf", "total_block", "tiene_calidad"
        ]
        df_mostrar = df_filtrada[cols_mostrar].copy()
        df_mostrar.columns = [
            "Albarán", "Fecha", "Productor", "Tipo Fruta", "Origen", "Guía Despacho",
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
                        # Construir parámetros pasando las listas de filtros
                        params_excel = {**params, 'include_prev_week': False, 'include_month_accum': False}
                        
                        # Pasar filtros como listas
                        if tipo_fruta_filtro:
                            params_excel['tipo_fruta'] = tipo_fruta_filtro
                        if clasif_filtro:
                            params_excel['clasificacion'] = clasif_filtro
                        if manejo_filtro:
                            params_excel['manejo'] = manejo_filtro
                        if productor_filtro:
                            params_excel['productor'] = productor_filtro
                        
                        resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/report.xlsx", params=params_excel, timeout=180)
                        
                    if resp.status_code == 200:
                        xlsx_bytes = resp.content
                        fname = f"recepciones_detalle_{params['fecha_inicio']}_a_{params['fecha_fin']}.xlsx".replace('/', '-')
                        st.download_button("Descargar Excel (Detallado)", xlsx_bytes, file_name=fname, mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    else:
                        st.error(f"Error al generar Excel detallado: {resp.status_code} - {resp.text}")
                except Exception as e:
                    st.error(f"Error al solicitar Excel detallado: {e}")

        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)


        # Gráficos por Planta - Kg recepcionados por día (por Tipo de Fruta)
        df_filtrada['fecha_dt'] = pd.to_datetime(df_filtrada['fecha']).dt.strftime('%Y-%m-%d')
        origen_filtro_usado = st.session_state.get('origen_filtro_usado', [])
        
        # Función para crear gráfico de una planta
        def crear_grafico_planta(df_planta, nombre_planta, color_titulo):
            kg_por_dia_fruta = df_planta.groupby(['fecha_dt', 'tipo_fruta'])['kg_recepcionados'].sum().reset_index()
            chart = alt.Chart(kg_por_dia_fruta).mark_bar().encode(
                x=alt.X('fecha_dt:N', title='Fecha', sort=None, axis=alt.Axis(labelAngle=-45)),
                y=alt.Y('kg_recepcionados:Q', title='Kg Recepcionados'),
                color=alt.Color('tipo_fruta:N', title='Tipo Fruta')
            ).properties(width=700, height=350)
            return chart
        
        # Si ambas plantas están seleccionadas, mostrar un gráfico por cada una
        if len(origen_filtro_usado) == 2 and 'origen' in df_filtrada.columns:
            # Gráfico para RFP
            st.subheader("🏭 RFP - Kg recepcionados por día (por Tipo de Fruta)")
            df_rfp = df_filtrada[df_filtrada['origen'] == 'RFP']
            if not df_rfp.empty:
                chart_rfp = crear_grafico_planta(df_rfp, 'RFP', '#3498db')
                st.altair_chart(chart_rfp, use_container_width=True)
                # Calcular total excluyendo bandejas
                total_rfp = 0.0
                for _, row in df_rfp.iterrows():
                    for p in row.get('productos', []) or []:
                        cat = (p.get('Categoria') or '').strip().upper()
                        if 'BANDEJ' not in cat:
                            total_rfp += p.get('Kg Hechos', 0) or 0
                st.caption(f"**Total RFP:** {fmt_numero(total_rfp, 0)} Kg")
            else:
                st.info("No hay datos de RFP en el período seleccionado")
            
            st.markdown("---")
            
            # Gráfico para VILKÚN
            st.subheader("🌿 VILKÚN - Kg recepcionados por día (por Tipo de Fruta)")
            df_vilkun = df_filtrada[df_filtrada['origen'] == 'VILKUN']
            if not df_vilkun.empty:
                chart_vilkun = crear_grafico_planta(df_vilkun, 'VILKUN', '#27ae60')
                st.altair_chart(chart_vilkun, use_container_width=True)
                # Calcular total excluyendo bandejas
                total_vilkun = 0.0
                for _, row in df_vilkun.iterrows():
                    for p in row.get('productos', []) or []:
                        cat = (p.get('Categoria') or '').strip().upper()
                        if 'BANDEJ' not in cat:
                            total_vilkun += p.get('Kg Hechos', 0) or 0
                st.caption(f"**Total VILKÚN:** {fmt_numero(total_vilkun, 0)} Kg")
            else:
                st.info("No hay datos de VILKÚN en el período seleccionado")
            
            # Resumen comparativo
            st.markdown("---")
            st.markdown("**📊 Resumen Comparativo:**")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                # Calcular total RFP excluyendo bandejas
                total_rfp = 0.0
                df_rfp_comp = df_filtrada[df_filtrada['origen'] == 'RFP'] if 'origen' in df_filtrada.columns else df_filtrada.head(0)
                for _, row in df_rfp_comp.iterrows():
                    for p in row.get('productos', []) or []:
                        cat = (p.get('Categoria') or '').strip().upper()
                        if 'BANDEJ' not in cat:
                            total_rfp += p.get('Kg Hechos', 0) or 0
                st.metric("🏭 RFP", f"{fmt_numero(total_rfp, 0)} Kg")
            with col_p2:
                # Calcular total VILKÚN excluyendo bandejas
                total_vilkun = 0.0
                df_vilkun_comp = df_filtrada[df_filtrada['origen'] == 'VILKUN'] if 'origen' in df_filtrada.columns else df_filtrada.head(0)
                for _, row in df_vilkun_comp.iterrows():
                    for p in row.get('productos', []) or []:
                        cat = (p.get('Categoria') or '').strip().upper()
                        if 'BANDEJ' not in cat:
                            total_vilkun += p.get('Kg Hechos', 0) or 0
                st.metric("🌿 VILKÚN", f"{fmt_numero(total_vilkun, 0)} Kg")
        else:
            # Solo una planta seleccionada - mostrar gráfico normal
            planta_actual = origen_filtro_usado[0] if origen_filtro_usado else "Planta"
            emoji = "🏭" if planta_actual == "RFP" else "🌿"
            st.subheader(f"{emoji} {planta_actual} - Kg recepcionados por día (por Tipo de Fruta)")
            chart_kg = crear_grafico_planta(df_filtrada, planta_actual, '#3498db')
            st.altair_chart(chart_kg, use_container_width=True)
            # Calcular total excluyendo bandejas
            total_kg = 0.0
            for _, row in df_filtrada.iterrows():
                for p in row.get('productos', []) or []:
                    cat = (p.get('Categoria') or '').strip().upper()
                    if 'BANDEJ' not in cat:
                        total_kg += p.get('Kg Hechos', 0) or 0
            st.caption(f"**Total {planta_actual}:** {fmt_numero(total_kg, 0)} Kg")

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
    
    # Filtros en una sola fila
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
    with col1:
        fecha_inicio_g = st.date_input("Desde", datetime.now() - timedelta(days=7), format="DD/MM/YYYY", key="gestion_desde")
    with col2:
        fecha_fin_g = st.date_input("Hasta", datetime.now(), format="DD/MM/YYYY", key="gestion_hasta")
    with col3:
        status_filter = st.selectbox("Estado", ["Todos", "Validada", "Lista para validar", "Confirmada", "En espera", "Borrador"], key="gestion_status")
    with col4:
        qc_filter = st.selectbox("Control Calidad", ["Todos", "Con QC Aprobado", "Con QC Pendiente", "Sin QC", "QC Fallido"], key="gestion_qc")
    with col5:
        search_text = st.text_input("Buscar Albarán", placeholder="Ej: WH/IN/00123", key="gestion_search")
    
    # Botón de consulta con limpiar caché
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        consultar = st.button("🔄 Consultar", type="primary", key="btn_gestion")
    with col_btn2:
        if st.button("🗑️ Limpiar caché", key="btn_clear_cache"):
            fetch_gestion_data.clear()
            fetch_gestion_overview.clear()
            st.success("Caché limpiado")
    
    # Cargar datos usando caché
    fecha_inicio_str = fecha_inicio_g.strftime("%Y-%m-%d")
    fecha_fin_str = fecha_fin_g.strftime("%Y-%m-%d")
    
    if consultar or st.session_state.get('gestion_loaded'):
        st.session_state.gestion_loaded = True
        
        with st.spinner("Cargando datos..."):
            # Usar funciones con caché (automáticamente devuelve caché si existe)
            overview = fetch_gestion_overview(username, password, fecha_inicio_str, fecha_fin_str)
            data_gestion = fetch_gestion_data(username, password, fecha_inicio_str, fecha_fin_str, 
                                              status_filter, qc_filter, search_text if search_text else None)
            
            st.session_state.gestion_overview = overview
            st.session_state.gestion_data = data_gestion
    
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
            
            # Segunda fila de filtros
            fc5, fc6 = st.columns([1, 3])
            with fc5:
                guia_filter = st.text_input(
                    "🚚 Guía de Despacho", 
                    placeholder="Buscar por N° guía...",
                    key="gestion_guia_despacho"
                )
        
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
        
        # Filtro por Guía de Despacho
        if guia_filter:
            guia_col = 'guia_despacho' if 'guia_despacho' in df_filtered.columns else 'x_studio_gua_de_despacho'
            if guia_col in df_filtered.columns:
                df_filtered = df_filtered[df_filtered[guia_col].fillna('').astype(str).str.contains(guia_filter, case=False, na=False)]
        
        st.caption(f"Mostrando {len(df_filtered)} de {len(df_g)} recepciones")
        
        # Inicializar estado de página si no existe
        if 'gestion_page' not in st.session_state:
            st.session_state.gestion_page = 1
        
        # Vista (sin causar rerun)
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
            ITEMS_PER_PAGE = 15
            total_items = len(df_filtered)
            total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
            
            # Inicializar estado de página
            if 'gestion_page' not in st.session_state:
                st.session_state.gestion_page = 1
            
            # Asegurar que la página esté en rango válido
            if st.session_state.gestion_page > total_pages:
                st.session_state.gestion_page = 1
            
            # Navegación de páginas con selectbox (más estable que number_input)
            col_nav1, col_nav2 = st.columns([3, 1])
            with col_nav1:
                st.markdown(f"**{total_items} recepciones** en {total_pages} páginas")
            with col_nav2:
                page_options = list(range(1, total_pages + 1))
                current_idx = st.session_state.gestion_page - 1
                selected_page = st.selectbox(
                    "Página", page_options, 
                    index=min(current_idx, len(page_options) - 1),
                    key="gestion_page_select",
                    label_visibility="collapsed"
                )
                st.session_state.gestion_page = selected_page
            
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
                    
                    # Link a Odoo
                    picking_id = row.get('picking_id', '')
                    if picking_id:
                        odoo_url = f"https://riofuturo.server98c6e.oerpondemand.net/web#id={picking_id}&menu_id=350&cids=1&action=540&active_id=164&model=stock.picking&view_type=form"
                        st.markdown(f"🔗 [Abrir en Odoo]({odoo_url})")
        
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

# =====================================================
#           TAB 3: CURVA DE ABASTECIMIENTO
# =====================================================
with tab_curva:
    st.subheader("📈 Curva de Abastecimiento")
    st.caption("Comparación entre kilogramos proyectados (Excel) vs recepcionados (Sistema)")
    
    # --- Filtros organizados ---
    st.markdown("### 🔍 Filtros")
    
    # Fila 1: Plantas y Solo hechas
    col_row1_1, col_row1_2, col_row1_3 = st.columns([1, 1, 1])
    
    with col_row1_1:
        st.markdown("**Origen/Planta:**")
        col_pl1, col_pl2 = st.columns(2)
        with col_pl1:
            curva_rfp = st.checkbox("🏭 RFP", value=True, key="curva_rfp")
        with col_pl2:
            curva_vilkun = st.checkbox("🌿 VILKÚN", value=True, key="curva_vilkun")
    
    with col_row1_2:
        st.markdown("**Estado recepciones:**")
        curva_solo_hechas = st.checkbox(
            "Solo recepciones hechas", 
            value=True, 
            key="curva_solo_hechas",
            help="Activa para ver solo recepciones completadas/validadas"
        )
    
    with col_row1_3:
        st.markdown("**Período:**")
        curva_fecha_inicio = st.date_input("Desde", datetime(2025, 11, 24), format="DD/MM/YYYY", key="curva_desde")
        curva_fecha_fin = datetime.now()
        st.caption(f"Hasta: {curva_fecha_fin.strftime('%d/%m/%Y')} (hoy)")
    
    # Fila 2: Especies
    # Obtener especies disponibles desde el backend
    especies_disponibles = []
    try:
        resp_esp = requests.get(f"{API_URL}/api/v1/recepciones-mp/abastecimiento/especies", timeout=30)
        if resp_esp.status_code == 200:
            especies_disponibles = resp_esp.json()
    except:
        pass
    
    st.markdown("**Filtrar por especie:**")
    especies_filtro = st.multiselect(
        "Especies", 
        especies_disponibles, 
        default=[],
        placeholder="Seleccionar especies (dejar vacío = todas)",
        key="curva_especie",
        label_visibility="collapsed"
    )
    
    # Filtro de rango de semanas
    st.markdown("**Rango de semanas a visualizar:**")
    # Semanas de temporada: 47-52 del año anterior, 1-17 del año actual
    semanas_temporada = list(range(47, 53)) + list(range(1, 18))
    semana_labels = [f"S{s}" for s in semanas_temporada]
    
    col_sem1, col_sem2 = st.columns(2)
    with col_sem1:
        semana_desde_idx = st.selectbox(
            "Desde semana",
            options=range(len(semanas_temporada)),
            format_func=lambda i: semana_labels[i],
            index=0,
            key="semana_desde"
        )
    with col_sem2:
        semana_hasta_idx = st.selectbox(
            "Hasta semana",
            options=range(len(semanas_temporada)),
            format_func=lambda i: semana_labels[i],
            index=len(semanas_temporada) - 1,
            key="semana_hasta"
        )
    
    # Obtener semanas seleccionadas
    semana_desde = semanas_temporada[semana_desde_idx]
    semana_hasta = semanas_temporada[semana_hasta_idx]
    
    st.markdown("---")
    
    # Botón para cargar curva (carga TODOS los datos, sin filtro de especie)
    if st.button("📊 Cargar Curva de Abastecimiento", key="btn_curva", type="primary"):
        # Construir lista de plantas
        plantas_list = []
        if curva_rfp:
            plantas_list.append("RFP")
        if curva_vilkun:
            plantas_list.append("VILKUN")
        
        if not plantas_list:
            st.warning("Debes seleccionar al menos una planta (RFP o VILKÚN)")
        else:
            st.session_state.curva_plantas_usadas = plantas_list.copy()
            
            with st.spinner("Cargando datos proyectados y del sistema..."):
                # 1. Obtener TODAS las proyecciones del Excel (sin filtro de especie)
                params_proy = {"planta": plantas_list}
                # NO agregamos filtro de especie aquí - se aplica dinámicamente después
                
                try:
                    resp_proy = requests.get(f"{API_URL}/api/v1/recepciones-mp/abastecimiento/proyectado", 
                                            params=params_proy, timeout=60)
                    if resp_proy.status_code == 200:
                        proyecciones = resp_proy.json()
                        st.session_state.curva_proyecciones_raw = proyecciones
                        st.success(f"✅ Datos cargados: {len(proyecciones)} semanas de proyección")
                    else:
                        st.error(f"Error al cargar proyecciones: {resp_proy.status_code}")
                        st.session_state.curva_proyecciones_raw = None
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
                    st.session_state.curva_proyecciones_raw = None
                
                # 2. Obtener TODAS las recepciones del sistema (sin filtro de especie)
                params_sist = {
                    "username": username,
                    "password": password,
                    "fecha_inicio": curva_fecha_inicio.strftime("%Y-%m-%d"),
                    "fecha_fin": curva_fecha_fin.strftime("%Y-%m-%d"),
                    "solo_hechas": curva_solo_hechas,
                    "origen": plantas_list
                }
                try:
                    resp_sist = requests.get(f"{API_URL}/api/v1/recepciones-mp/", 
                                            params=params_sist, timeout=120)
                    if resp_sist.status_code == 200:
                        recepciones_sist = resp_sist.json()
                        st.session_state.curva_sistema_raw = recepciones_sist
                    else:
                        st.error(f"Error al cargar recepciones del sistema: {resp_sist.status_code}")
                        st.session_state.curva_sistema_raw = None
                except Exception as e:
                    st.error(f"Error de conexión al sistema: {e}")
                    st.session_state.curva_sistema_raw = None
    
    # ============ MOSTRAR CURVA CON FILTRO DINÁMICO ============
    # Cargar proyecciones dinámicamente basado en filtro de especies actual
    if 'curva_plantas_usadas' in st.session_state and st.session_state.curva_plantas_usadas:
        plantas_usadas = st.session_state.curva_plantas_usadas
        
        # Cargar proyecciones dinámicamente según filtro actual de especies
        params_proy = {"planta": plantas_usadas}
        if especies_filtro:
            params_proy["especie"] = especies_filtro
        
        try:
            resp_proy = requests.get(f"{API_URL}/api/v1/recepciones-mp/abastecimiento/proyectado", 
                                    params=params_proy, timeout=30)
            if resp_proy.status_code == 200:
                proyecciones = resp_proy.json()
            else:
                proyecciones = []
        except:
            proyecciones = []
        
        if proyecciones:
            df_proy_all = pd.DataFrame(proyecciones)
            
            # Agregar columna de semana label y sort_key
            df_proy_all['semana_label'] = 'S' + df_proy_all['semana'].astype(str)
            df_proy_all['sort_key'] = df_proy_all['semana'].apply(lambda x: x if x >= 47 else x + 100)
            df_proy = df_proy_all.sort_values('sort_key')
            
            # Función para normalizar tipo_fruta del sistema al mismo formato que proyecciones
            def normalizar_tipo_fruta(tipo_fruta):
                if not tipo_fruta or pd.isna(tipo_fruta):
                    return 'Otro Convencional'
                
                tf = str(tipo_fruta).upper().strip()
                
                # Detectar manejo
                if 'ORGAN' in tf:
                    manejo = 'Orgánico'
                else:
                    manejo = 'Convencional'
                
                # Detectar especie base
                if 'ARANDANO' in tf or 'ARÁNDANO' in tf or 'BLUEBERRY' in tf:
                    especie_base = 'Arándano'
                elif 'FRAM' in tf or 'FRAMBUESA' in tf or 'MEEKER' in tf or 'HERITAGE' in tf or 'WAKEFIELD' in tf or 'RASPBERRY' in tf:
                    especie_base = 'Frambuesa'
                elif 'FRUTILLA' in tf or 'FRESA' in tf or 'STRAWBERRY' in tf:
                    especie_base = 'Frutilla'
                elif 'MORA' in tf or 'BLACKBERRY' in tf:
                    especie_base = 'Mora'
                elif 'CEREZA' in tf or 'CHERRY' in tf:
                    especie_base = 'Cereza'
                else:
                    especie_base = 'Otro'
                
                return f"{especie_base} {manejo}"
            
            # Si hay datos del sistema, procesarlos por semana
            df_sistema_semana = None
            if 'curva_sistema_raw' in st.session_state and st.session_state.curva_sistema_raw:
                recepciones = st.session_state.curva_sistema_raw
                
                # Procesar recepciones igual que KPIs:
                # - Iterar sobre productos
                # - Sumar Kg Hechos por semana
                # - Filtrar por especie+manejo (normalizado)
                kg_por_semana = {}
                
                for rec in recepciones:
                    tipo_fruta = (rec.get('tipo_fruta') or '').strip()
                    if not tipo_fruta:
                        continue
                    
                    # Obtener semana de la fecha
                    fecha_str = rec.get('fecha')
                    if not fecha_str:
                        continue
                    try:
                        fecha_dt = pd.to_datetime(fecha_str)
                        semana = fecha_dt.isocalendar().week
                        año = fecha_dt.year
                    except:
                        continue
                    
                    # Procesar productos igual que KPIs
                    productos = rec.get('productos', []) or []
                    for p in productos:
                        categoria = (p.get('Categoria') or '').strip().upper()
                        # Excluir BANDEJAS igual que KPIs
                        if 'BANDEJ' in categoria:
                            continue
                        
                        kg_hechos = p.get('Kg Hechos', 0) or 0
                        if kg_hechos <= 0:
                            continue
                        
                        # Obtener manejo del producto
                        manejo = (p.get('Manejo') or '').strip()
                        if not manejo:
                            manejo = 'Sin Manejo'
                        
                        # Normalizar especie base
                        tf = tipo_fruta.upper()
                        if 'ARANDANO' in tf or 'ARÁNDANO' in tf or 'BLUEBERRY' in tf:
                            especie_base = 'Arándano'
                        elif 'FRAM' in tf or 'FRAMBUESA' in tf or 'MEEKER' in tf or 'HERITAGE' in tf or 'WAKEFIELD' in tf or 'RASPBERRY' in tf:
                            especie_base = 'Frambuesa'
                        elif 'FRUTILLA' in tf or 'FRESA' in tf or 'STRAWBERRY' in tf:
                            especie_base = 'Frutilla'
                        elif 'MORA' in tf or 'BLACKBERRY' in tf:
                            especie_base = 'Mora'
                        elif 'CEREZA' in tf or 'CHERRY' in tf:
                            especie_base = 'Cereza'
                        else:
                            especie_base = 'Otro'
                        
                        # Determinar manejo normalizado (Convencional / Orgánico)
                        manejo_upper = manejo.upper()
                        if 'ORGAN' in manejo_upper:
                            manejo_norm = 'Orgánico'
                        elif 'CONVENCIONAL' in manejo_upper:
                            manejo_norm = 'Convencional'
                        else:
                            manejo_norm = 'Convencional'  # Por defecto
                        
                        especie_manejo = f"{especie_base} {manejo_norm}"
                        
                        # Filtrar por especie si hay filtro activo
                        if especies_filtro and especie_manejo not in especies_filtro:
                            continue
                        
                        # Acumular kg por semana
                        if semana not in kg_por_semana:
                            kg_por_semana[semana] = {'kg': 0, 'año': año}
                        kg_por_semana[semana]['kg'] += kg_hechos
                
                # Convertir a DataFrame
                if kg_por_semana:
                    data_semanas = [{'semana': s, 'kg_sistema': v['kg'], 'año': v['año']} 
                                    for s, v in kg_por_semana.items()]
                    df_sistema_semana = pd.DataFrame(data_semanas)
                    df_sistema_semana['semana_label'] = 'S' + df_sistema_semana['semana'].astype(str)
                    df_sistema_semana['sort_key'] = df_sistema_semana.apply(
                        lambda x: x['semana'] if x['año'] == 2024 else x['semana'] + 100, axis=1
                    )
            
            # Mostrar info de filtro activo
            if especies_filtro:
                st.info(f"🔍 Filtro activo: {', '.join(especies_filtro)}")
            
            st.markdown("---")
            st.markdown("### 📊 Comparativa Semanal")
            
            # Combinar datos de proyección y sistema
            df_chart = df_proy[['semana', 'semana_label', 'kg_proyectados']].copy()
            if df_sistema_semana is not None and not df_sistema_semana.empty:
                df_chart = df_chart.merge(
                    df_sistema_semana[['semana', 'kg_sistema']], 
                    on='semana', 
                    how='left'
                )
                df_chart['kg_sistema'] = df_chart['kg_sistema'].fillna(0)
            else:
                df_chart['kg_sistema'] = 0
            
            # ============ OBTENER DATOS DEL AÑO ANTERIOR ============
            # Calcular fechas del año anterior DINÁMICAMENTE basado en las semanas de la proyección
            # IMPORTANTE: Esta consulta es INDEPENDIENTE de los filtros superiores
            kg_anterior_por_semana = {}
            try:
                # Obtener las semanas que tiene la proyección
                semanas_proyeccion = df_proy['semana'].unique().tolist()
                
                # Calcular fechas del año anterior correspondientes a esas semanas
                # Usamos un rango amplio para cubrir la temporada anterior (2023-2024)
                # Las semanas 47-52 corresponden a Nov-Dic 2023
                # Las semanas 1-17 corresponden a Ene-Abr 2024
                from datetime import timedelta
                
                # Fecha inicio: primera semana de la temporada anterior
                # Si hay semanas >= 47, el inicio es en noviembre del año anterior
                min_semana = min(semanas_proyeccion)
                max_semana = max(semanas_proyeccion)
                
                # Para temporada 2024-2025, el año anterior es 2023-2024
                if any(s >= 47 for s in semanas_proyeccion):
                    fecha_inicio_anterior = datetime(2023, 11, 1)  # Noviembre 2023
                else:
                    fecha_inicio_anterior = datetime(2024, 1, 1)  # Enero 2024
                
                if any(s <= 20 for s in semanas_proyeccion):
                    fecha_fin_anterior = datetime(2024, 5, 31)  # Mayo 2024
                else:
                    fecha_fin_anterior = datetime(2023, 12, 31)  # Diciembre 2023
                
                # Llamar a la API para obtener datos del año anterior SIN filtros de planta
                # IMPORTANTE: Incluir username y password que son requeridos por el endpoint
                params_anterior = {
                    "username": username,
                    "password": password,
                    "fecha_inicio": fecha_inicio_anterior.strftime("%Y-%m-%d"),
                    "fecha_fin": fecha_fin_anterior.strftime("%Y-%m-%d"),
                    "solo_hechas": True
                    # NO usar filtro de origen para que traiga todos los datos
                }
                print(f"DEBUG: Consultando año anterior desde {fecha_inicio_anterior} hasta {fecha_fin_anterior}")
                resp_anterior = requests.get(
                    f"{API_URL}/api/v1/recepciones-mp/",
                    params=params_anterior,
                    timeout=60
                )
                
                if resp_anterior.status_code == 200:
                    recepciones_anterior = resp_anterior.json()
                    print(f"DEBUG: Recepciones año anterior: {len(recepciones_anterior)} registros")
                    
                    for rec in recepciones_anterior:
                        fecha_str = rec.get('fecha')
                        if not fecha_str:
                            continue
                        try:
                            fecha_dt = pd.to_datetime(fecha_str)
                            semana = fecha_dt.isocalendar().week
                        except:
                            continue
                        
                        # Procesar productos
                        productos = rec.get('productos', []) or []
                        for p in productos:
                            categoria = (p.get('Categoria') or '').strip().upper()
                            if 'BANDEJ' in categoria:
                                continue
                            
                            kg_hechos = p.get('Kg Hechos', 0) or 0
                            if kg_hechos <= 0:
                                continue
                            
                            # Acumular por semana
                            if semana not in kg_anterior_por_semana:
                                kg_anterior_por_semana[semana] = 0
                            kg_anterior_por_semana[semana] += kg_hechos
                    
                    print(f"DEBUG: Semanas con datos del año anterior: {list(kg_anterior_por_semana.keys())}")
                    print(f"DEBUG: Total kg año anterior: {sum(kg_anterior_por_semana.values())}")
                else:
                    print(f"DEBUG: Error en API año anterior: {resp_anterior.status_code}")
            except Exception as e:
                print(f"Error obteniendo datos del año anterior: {e}")
            
            # Agregar columna de año anterior al df_chart
            df_chart['kg_anterior'] = df_chart['semana'].apply(
                lambda s: kg_anterior_por_semana.get(s, 0)
            )
            
            # Ordenar por semana
            df_chart['sort_key'] = df_chart['semana'].apply(lambda x: x if x >= 47 else x + 100)
            df_chart = df_chart.sort_values('sort_key')
            
            # Aplicar filtro de semanas
            semana_desde_sk = semana_desde if semana_desde >= 47 else semana_desde + 100
            semana_hasta_sk = semana_hasta if semana_hasta >= 47 else semana_hasta + 100
            df_chart = df_chart[(df_chart['sort_key'] >= semana_desde_sk) & (df_chart['sort_key'] <= semana_hasta_sk)]
            
            if df_chart.empty:
                st.warning("No hay datos en el rango de semanas seleccionado.")
            
            if not df_chart.empty:
                # Melt para formato largo (ahora con 3 tipos)
                df_melt = df_chart.melt(
                    id_vars=['semana', 'semana_label', 'sort_key'],
                    value_vars=['kg_anterior', 'kg_proyectados', 'kg_sistema'],
                    var_name='Tipo',
                    value_name='Kg'
                )
                df_melt['Tipo'] = df_melt['Tipo'].replace({
                    'kg_anterior': 'Año Anterior',
                    'kg_proyectados': 'Proyectado',
                    'kg_sistema': 'Recepcionado'
                })
                
                # Orden específico para las barras: Año Anterior (naranjo) | Proyectado (azul) | Recepcionado (verde)
                chart = alt.Chart(df_melt).mark_bar(opacity=0.85, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                    x=alt.X('semana_label:N', title='Semana', sort=alt.SortField('sort_key')),
                    y=alt.Y('Kg:Q', title='Kilogramos', axis=alt.Axis(format=',.0f')),
                    color=alt.Color('Tipo:N', 
                        scale=alt.Scale(
                            domain=['Año Anterior', 'Proyectado', 'Recepcionado'],
                            range=['#e67e22', '#3498db', '#2ecc71']  # Naranjo, Azul, Verde
                        ),
                        legend=alt.Legend(title="Tipo", orient="top")
                    ),
                    xOffset=alt.XOffset('Tipo:N', sort=['Año Anterior', 'Proyectado', 'Recepcionado']),
                    tooltip=[
                        alt.Tooltip('semana_label:N', title='Semana'),
                        alt.Tooltip('Tipo:N', title='Tipo'),
                        alt.Tooltip('Kg:Q', title='Kilogramos', format=',.0f')
                    ]
                ).properties(
                    height=350,
                    title=alt.TitleParams(
                        text='Kg Proyectados vs Recepcionados por Semana (incluye Año Anterior)',
                        fontSize=16,
                        anchor='start'
                    )
                ).configure_axis(
                    labelFontSize=11,
                    titleFontSize=12
                ).configure_legend(
                    labelFontSize=12,
                    titleFontSize=12
                )
                
                st.altair_chart(chart, use_container_width=True)
                
                # Sumatoria del gráfico de volumen (ahora con 5 métricas)
                total_kg_anterior = df_chart['kg_anterior'].sum()
                total_kg_proy_vol = df_chart['kg_proyectados'].sum()
                total_kg_recep_vol = df_chart['kg_sistema'].sum()
                diff_kg = total_kg_proy_vol - total_kg_recep_vol
                cumplimiento_kg = (total_kg_recep_vol / total_kg_proy_vol * 100) if total_kg_proy_vol > 0 else 0
                
                vol_cols = st.columns(5)
                with vol_cols[0]:
                    st.metric("🟠 Año Anterior", fmt_numero(total_kg_anterior, 0))
                with vol_cols[1]:
                    st.metric("📦 Total Kg Proyectados", fmt_numero(total_kg_proy_vol, 0))
                with vol_cols[2]:
                    st.metric("✅ Total Kg Recepcionados", fmt_numero(total_kg_recep_vol, 0))
                with vol_cols[3]:
                    delta_color = "normal" if diff_kg >= 0 else "inverse"
                    st.metric("📊 Diferencia", fmt_numero(abs(diff_kg), 0), delta=f"{'Falta' if diff_kg > 0 else 'Exceso'}", delta_color=delta_color)
                with vol_cols[4]:
                    st.metric("📈 Cumplimiento", f"{fmt_numero(cumplimiento_kg, 1)}%")
            
            # ============ GRÁFICO DE PRECIOS POR SEMANA ============
            st.markdown("---")
            st.markdown("### 💰 Comparativa de Precios y Gastos por Semana")
            
            try:
                # Calcular datos de precio y gasto recepcionado por semana desde datos del sistema
                precios_por_semana = {}
                
                # Cargar exclusiones para ignorar costos
                import json as json_curva
                exclusiones_ids_curva = []
                try:
                    exclusions_file_curva = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shared", "exclusiones.json")
                    if os.path.exists(exclusions_file_curva):
                        with open(exclusions_file_curva, 'r') as f:
                            exclusiones_curva = json_curva.load(f)
                            exclusiones_ids_curva = exclusiones_curva.get("recepciones", [])
                except:
                    pass
                
                if 'curva_sistema_raw' in st.session_state and st.session_state.curva_sistema_raw:
                    for rec in st.session_state.curva_sistema_raw:
                        fecha_str = rec.get('fecha')
                        if not fecha_str:
                            continue
                        
                        # Verificar si esta recepción está excluida de valorización
                        recep_id_curva = rec.get('id') or rec.get('picking_id')
                        recep_name_curva = rec.get('albaran', '')
                        excluir_costo_curva = recep_id_curva in exclusiones_ids_curva or recep_name_curva in exclusiones_ids_curva
                        
                        try:
                            fecha = pd.to_datetime(fecha_str)
                            semana = fecha.isocalendar()[1]
                            año = fecha.year
                        except:
                            continue
                        
                        productos = rec.get('productos', []) or []
                        for p in productos:
                            categoria = (p.get('Categoria') or '').strip().upper()
                            if 'BANDEJ' in categoria:
                                continue
                            
                            kg = p.get('Kg Hechos', 0) or 0
                            precio = p.get('Costo Unitario', 0) or p.get('precio', 0) or 0
                            
                            if kg <= 0:
                                continue
                            
                            # Aplicar filtro de especie si existe
                            if especies_filtro:
                                tipo_fruta = (rec.get('tipo_fruta') or '').upper()
                                manejo = (p.get('Manejo') or '').upper()
                                if 'ORGAN' in manejo or 'ORGAN' in tipo_fruta:
                                    manejo_norm = 'Orgánico'
                                else:
                                    manejo_norm = 'Convencional'
                                
                                if 'ARANDANO' in tipo_fruta or 'ARÁNDANO' in tipo_fruta:
                                    especie_base = 'Arándano'
                                elif 'FRAM' in tipo_fruta or 'MEEKER' in tipo_fruta or 'HERITAGE' in tipo_fruta:
                                    especie_base = 'Frambuesa'
                                elif 'FRUTILLA' in tipo_fruta:
                                    especie_base = 'Frutilla'
                                elif 'MORA' in tipo_fruta:
                                    especie_base = 'Mora'
                                elif 'CEREZA' in tipo_fruta:
                                    especie_base = 'Cereza'
                                else:
                                    especie_base = 'Otro'
                                
                                especie_manejo = f"{especie_base} {manejo_norm}"
                                if especie_manejo not in especies_filtro:
                                    continue
                            
                            if semana not in precios_por_semana:
                                precios_por_semana[semana] = {'total_kg': 0, 'total_valor': 0, 'año': año}
                            precios_por_semana[semana]['total_kg'] += kg
                            # Solo sumar valor si NO está excluida
                            if not excluir_costo_curva:
                                precios_por_semana[semana]['total_valor'] += kg * precio if precio > 0 else 0
                
                # Construir DataFrame para gráficos de precios y gastos
                precios_data = []
                for semana, data in precios_por_semana.items():
                    sort_key = semana if semana >= 47 else semana + 100
                    
                    # Aplicar filtro de semanas
                    if sort_key < semana_desde_sk or sort_key > semana_hasta_sk:
                        continue
                    
                    precio_recep = data['total_valor'] / data['total_kg'] if data['total_kg'] > 0 else 0
                    
                    precios_data.append({
                        'semana': semana,
                        'semana_label': f'S{semana}',
                        'sort_key': sort_key,
                        'kg_recepcionado': data['total_kg'],
                        'gasto_total': data['total_valor'],
                        'precio_recepcionado': round(precio_recep, 0)
                    })
                
                if precios_data:
                    df_precios = pd.DataFrame(precios_data)
                    df_precios = df_precios.sort_values('sort_key')
                    
                    # Combinar con proyecciones para tener volumen proyectado
                    df_precios_full = df_precios.merge(
                        df_chart[['semana', 'kg_proyectados']], 
                        on='semana', 
                        how='left'
                    )
                    df_precios_full['kg_proyectados'] = df_precios_full['kg_proyectados'].fillna(0)
                    
                    # ============ GRÁFICO DE GASTO PROYECTADO VS RECEPCIONADO ============
                    st.markdown("#### 💵 Gasto Proyectado vs Recepcionado por Semana")
                    
                    # Combinar con gasto proyectado del Excel
                    df_proy_gasto = df_proy[['semana', 'kg_proyectados']].copy()
                    
                    # Obtener gasto proyectado desde las proyecciones (si está disponible)
                    # Verificar si las proyecciones tienen gasto_proyectado
                    if 'gasto_proyectado' in df_proy.columns if isinstance(df_proy, pd.DataFrame) and not df_proy.empty else False:
                        df_proy_gasto = df_proy[['semana', 'gasto_proyectado']].copy()
                    else:
                        # Calcular gasto proyectado desde proyecciones raw si existe
                        # Intentar obtener proyecciones con gasto del backend
                        try:
                            params_gasto = {"planta": plantas_usadas}
                            if especies_filtro:
                                params_gasto["especie"] = especies_filtro
                            resp_gasto = requests.get(f"{API_URL}/api/v1/recepciones-mp/abastecimiento/proyectado", 
                                                    params=params_gasto, timeout=30)
                            if resp_gasto.status_code == 200:
                                proyecciones_gasto = resp_gasto.json()
                                df_proy_gasto = pd.DataFrame(proyecciones_gasto)
                                if 'gasto_proyectado' not in df_proy_gasto.columns:
                                    df_proy_gasto['gasto_proyectado'] = 0
                        except:
                            df_proy_gasto = pd.DataFrame({'semana': [], 'gasto_proyectado': []})
                    
                    # Merge con datos de precios para tener gasto proyectado
                    if not df_proy_gasto.empty and 'gasto_proyectado' in df_proy_gasto.columns:
                        df_precios_full = df_precios_full.merge(
                            df_proy_gasto[['semana', 'gasto_proyectado']].rename(columns={'gasto_proyectado': 'gasto_proy'}),
                            on='semana',
                            how='left'
                        )
                        df_precios_full['gasto_proy'] = df_precios_full['gasto_proy'].fillna(0)
                    else:
                        df_precios_full['gasto_proy'] = 0
                    
                    # Melt para formato largo
                    df_gasto_melt = df_precios_full.melt(
                        id_vars=['semana', 'semana_label', 'sort_key'],
                        value_vars=['gasto_proy', 'gasto_total'],
                        var_name='Tipo',
                        value_name='Gasto'
                    )
                    df_gasto_melt['Tipo'] = df_gasto_melt['Tipo'].replace({
                        'gasto_proy': 'Proyectado',
                        'gasto_total': 'Recepcionado'
                    })
                    
                    gasto_chart = alt.Chart(df_gasto_melt).mark_bar(opacity=0.85, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                        x=alt.X('semana_label:N', title='Semana', sort=alt.SortField('sort_key')),
                        y=alt.Y('Gasto:Q', title='Gasto ($)', axis=alt.Axis(format='$,.0f')),
                        color=alt.Color('Tipo:N', 
                            scale=alt.Scale(
                                domain=['Proyectado', 'Recepcionado'],
                                range=['#9b59b6', '#e74c3c']  # Morado para proyectado, Rojo para recepcionado
                            ),
                            legend=alt.Legend(title="Tipo", orient="top")
                        ),
                        xOffset='Tipo:N',
                        tooltip=[
                            alt.Tooltip('semana_label:N', title='Semana'),
                            alt.Tooltip('Tipo:N', title='Tipo'),
                            alt.Tooltip('Gasto:Q', title='Gasto $', format='$,.0f')
                        ]
                    ).properties(
                        height=300
                    )
                    st.altair_chart(gasto_chart, use_container_width=True)
                    
                    # Sumatoria del gráfico de gastos
                    total_gasto_proy = df_precios_full['gasto_proy'].sum() if 'gasto_proy' in df_precios_full.columns else 0
                    total_gasto_recep = df_precios_full['gasto_total'].sum()
                    diff_gasto = total_gasto_proy - total_gasto_recep
                    cumplimiento_gasto = (total_gasto_recep / total_gasto_proy * 100) if total_gasto_proy > 0 else 0
                    
                    gasto_cols = st.columns(4)
                    with gasto_cols[0]:
                        st.metric("💰 Gasto Proyectado", fmt_dinero(total_gasto_proy, 0))
                    with gasto_cols[1]:
                        st.metric("💵 Gasto Recepcionado", fmt_dinero(total_gasto_recep, 0))
                    with gasto_cols[2]:
                        delta_color = "normal" if diff_gasto >= 0 else "inverse"
                        st.metric("📊 Diferencia", fmt_dinero(abs(diff_gasto), 0), delta=f"{'Ahorro' if diff_gasto > 0 else 'Exceso'}", delta_color=delta_color)
                    with gasto_cols[3]:
                        st.metric("📈 Ejecución", f"{fmt_numero(cumplimiento_gasto, 1)}%")
                    
                    # ============ GRÁFICO DE PRECIO PROMEDIO ============
                    st.markdown("#### 📈 Precio Promedio Recepcionado por Semana")
                    
                    # Crear gráfico de líneas para precios por semana
                    precio_chart = alt.Chart(df_precios).mark_line(
                        point=alt.OverlayMarkDef(size=60),
                        strokeWidth=3,
                        color='#e67e22'
                    ).encode(
                        x=alt.X('semana_label:N', title='Semana', sort=alt.SortField('sort_key')),
                        y=alt.Y('precio_recepcionado:Q', title='Precio por Kg ($)', axis=alt.Axis(format=',.0f')),
                        tooltip=[
                            alt.Tooltip('semana_label:N', title='Semana'),
                            alt.Tooltip('precio_recepcionado:Q', title='Precio $/kg', format=',.0f')
                        ]
                    ).properties(
                        height=300
                    )
                    st.altair_chart(precio_chart, use_container_width=True)
                    
                    # ============ RESUMEN DE TOTALES ============
                    st.markdown("---")
                    st.markdown("#### 📋 Resumen de Costos del Período")
                    
                    total_kg_recep = df_precios_full['kg_recepcionado'].sum()
                    total_kg_proy = df_precios_full['kg_proyectados'].sum()
                    total_gasto_recep = df_precios_full['gasto_total'].sum()
                    total_gasto_proy = df_precios_full['gasto_proy'].sum() if 'gasto_proy' in df_precios_full.columns else 0
                    precio_prom = total_gasto_recep / total_kg_recep if total_kg_recep > 0 else 0
                    
                    res_cols = st.columns(5)
                    with res_cols[0]:
                        st.metric("Kg Proyectados", fmt_numero(total_kg_proy, 0))
                    with res_cols[1]:
                        st.metric("Kg Recepcionados", fmt_numero(total_kg_recep, 0))
                    with res_cols[2]:
                        st.metric("Gasto Proyectado", fmt_dinero(total_gasto_proy, 0))
                    with res_cols[3]:
                        st.metric("Gasto Recepcionado", fmt_dinero(total_gasto_recep, 0))
                    with res_cols[4]:
                        st.metric("Precio Prom. $/Kg", fmt_dinero(precio_prom, 0))
                    
                else:
                    st.info("No hay datos de precios recepcionados en el rango seleccionado.")
            except Exception as e:
                st.warning(f"Error al cargar precios: {e}")
            
            # ============ TOTALES DEL PERÍODO ============
            st.markdown("---")
            
            # Calcular totales
            total_proy_temporada = df_chart['kg_proyectados'].sum()  # Total proyectado toda la temporada
            total_sist = df_chart['kg_sistema'].sum()  # Total recepcionado
            # Calcular proyectado hasta el día de hoy (solo semanas pasadas)
            from datetime import datetime as dt
            semana_actual = dt.now().isocalendar()[1]
            año_actual = dt.now().year
            
            # Calcular sort_key de la semana actual
            # Temporada va de S47 de un año a S17 del siguiente
            # El sort_key debe ser consistente con cómo se calcula en df_chart
            # S47-52 → sort_key 47-52 (año base de temporada)
            # S1-17 → sort_key 101-117 (año siguiente)
            if semana_actual >= 47:
                # Estamos en S47-52, es el año base de la temporada
                sort_key_actual = semana_actual
            else:
                # Estamos en S1-17 del año siguiente
                sort_key_actual = semana_actual + 100
            
            # Filtrar solo semanas que ya pasaron (sort_key <= sort_key_actual)
            df_periodo = df_chart[df_chart['sort_key'] <= sort_key_actual]
            total_proy_periodo = df_periodo['kg_proyectados'].sum() if not df_periodo.empty else 0
            total_sist_periodo = df_periodo['kg_sistema'].sum() if not df_periodo.empty else 0
            
            # Cumplimiento del período (hasta hoy)
            cumpl_periodo = (total_sist_periodo / total_proy_periodo * 100) if total_proy_periodo > 0 else 0
            diff_periodo = abs(total_proy_periodo - total_sist_periodo)  # Siempre positivo
            
            # KPIs con mejor diseño
            st.markdown("### 🎯 Resumen de Cumplimiento")
            st.caption(f"Semana actual: S{semana_actual}")
            
            # Primera fila: Período actual (lo más importante)
            st.markdown("**📅 Período hasta hoy:**")
            kpi_cols1 = st.columns(4)
            
            with kpi_cols1[0]:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1abc9c 0%, #16a085 100%); padding: 20px; border-radius: 10px; text-align: center;">
                    <p style="margin: 0; color: #fff; font-size: 11px; opacity: 0.9;">📅 PROYECTADO AL DÍA</p>
                    <p style="margin: 5px 0 0 0; color: #fff; font-size: 22px; font-weight: bold;">{fmt_numero(total_proy_periodo, 0)} Kg</p>
                </div>
                """, unsafe_allow_html=True)
            
            with kpi_cols1[1]:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%); padding: 20px; border-radius: 10px; text-align: center;">
                    <p style="margin: 0; color: #fff; font-size: 11px; opacity: 0.9;">✅ RECEPCIONADO</p>
                    <p style="margin: 5px 0 0 0; color: #fff; font-size: 22px; font-weight: bold;">{fmt_numero(total_sist_periodo, 0)} Kg</p>
                </div>
                """, unsafe_allow_html=True)
            
            with kpi_cols1[2]:
                # Color según cumplimiento
                if cumpl_periodo >= 80:
                    color_cumpl = "#2ecc71"
                elif cumpl_periodo >= 50:
                    color_cumpl = "#f39c12"
                else:
                    color_cumpl = "#e74c3c"
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, {color_cumpl} 0%, {color_cumpl}cc 100%); padding: 20px; border-radius: 10px; text-align: center;">
                    <p style="margin: 0; color: #fff; font-size: 11px; opacity: 0.9;">📊 CUMPLIMIENTO</p>
                    <p style="margin: 5px 0 0 0; color: #fff; font-size: 22px; font-weight: bold;">{fmt_numero(cumpl_periodo, 1)}%</p>
                </div>
                """, unsafe_allow_html=True)
            
            with kpi_cols1[3]:
                # Siempre rojo porque es lo que falta
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); padding: 20px; border-radius: 10px; text-align: center;">
                    <p style="margin: 0; color: #fff; font-size: 11px; opacity: 0.9;">📉 DIFERENCIA PERÍODO</p>
                    <p style="margin: 5px 0 0 0; color: #fff; font-size: 22px; font-weight: bold;">{fmt_numero(diff_periodo, 0)} Kg</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Barra de progreso visual
            st.markdown("<br>", unsafe_allow_html=True)
            progress_val = min(cumpl_periodo / 100, 1.0)
            st.progress(progress_val, text=f"Avance de abastecimiento (hasta S{semana_actual}): {fmt_numero(cumpl_periodo, 1)}%")
            
            # Segunda fila: Total temporada (referencia)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**📆 Total Temporada (proyección completa):**")
            kpi_cols2 = st.columns(4)
            
            cumpl_temporada = (total_sist / total_proy_temporada * 100) if total_proy_temporada > 0 else 0
            diff_temporada = total_sist - total_proy_temporada
            
            with kpi_cols2[0]:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); padding: 15px; border-radius: 10px; text-align: center;">
                    <p style="margin: 0; color: #fff; font-size: 10px; opacity: 0.8;">📋 TOTAL TEMPORADA</p>
                    <p style="margin: 3px 0 0 0; color: #fff; font-size: 18px; font-weight: bold;">{fmt_numero(total_proy_temporada, 0)} Kg</p>
                </div>
                """, unsafe_allow_html=True)
            
            with kpi_cols2[1]:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%); padding: 15px; border-radius: 10px; text-align: center;">
                    <p style="margin: 0; color: #fff; font-size: 10px; opacity: 0.8;">🎯 RECEP. VS TEMPORADA</p>
                    <p style="margin: 3px 0 0 0; color: #fff; font-size: 18px; font-weight: bold;">{fmt_numero(cumpl_temporada, 1)}%</p>
                </div>
                """, unsafe_allow_html=True)
            
            with kpi_cols2[2]:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%); padding: 15px; border-radius: 10px; text-align: center;">
                    <p style="margin: 0; color: #fff; font-size: 10px; opacity: 0.8;">📊 PENDIENTE TEMPORADA</p>
                    <p style="margin: 3px 0 0 0; color: #fff; font-size: 18px; font-weight: bold;">{fmt_numero(abs(diff_temporada), 0)} Kg</p>
                </div>
                """, unsafe_allow_html=True)
            
            with kpi_cols2[3]:
                # Semanas en df_chart que aún no han pasado
                semanas_futuras = df_chart[df_chart['sort_key'] > sort_key_actual]
                semanas_restantes = len(semanas_futuras)
                
                # Si no hay semanas restantes, la temporada finalizó
                if semanas_restantes == 0:
                    texto_semanas = "Finalizada"
                else:
                    texto_semanas = str(semanas_restantes)
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%); padding: 15px; border-radius: 10px; text-align: center;">
                    <p style="margin: 0; color: #fff; font-size: 10px; opacity: 0.8;">📅 SEMANAS RESTANTES</p>
                    <p style="margin: 3px 0 0 0; color: #fff; font-size: 18px; font-weight: bold;">{texto_semanas}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # ============ TABLA RESUMEN ============
            st.markdown("---")
            st.markdown("### 📋 Detalle por Semana")
            
            df_tabla = df_chart[['semana', 'semana_label', 'kg_proyectados', 'kg_sistema']].copy()
            df_tabla['pct_cumplimiento'] = (df_tabla['kg_sistema'] / df_tabla['kg_proyectados'] * 100).fillna(0)
            df_tabla['diferencia'] = df_tabla['kg_sistema'] - df_tabla['kg_proyectados']
            
            # Aplicar formato chileno (punto como separador de miles)
            df_tabla['kg_proy_fmt'] = df_tabla['kg_proyectados'].apply(lambda x: fmt_numero(x, 0))
            df_tabla['kg_sist_fmt'] = df_tabla['kg_sistema'].apply(lambda x: fmt_numero(x, 0))
            df_tabla['diff_fmt'] = df_tabla['diferencia'].apply(lambda x: fmt_numero(x, 0))
            df_tabla['pct_fmt'] = df_tabla['pct_cumplimiento'].apply(lambda x: f"{fmt_numero(x, 1)}%")
            
            # Mostrar tabla con formato chileno
            st.dataframe(
                df_tabla[['semana_label', 'kg_proy_fmt', 'kg_sist_fmt', 'pct_cumplimiento', 'diff_fmt']],
                column_config={
                    "semana_label": st.column_config.TextColumn("Semana", width="small"),
                    "kg_proy_fmt": st.column_config.TextColumn(
                        "Kg Proyectados",
                        help="Kilogramos proyectados según planificación"
                    ),
                    "kg_sist_fmt": st.column_config.TextColumn(
                        "Kg Recepcionados",
                        help="Kilogramos recepcionados en el sistema"
                    ),
                    "pct_cumplimiento": st.column_config.ProgressColumn(
                        "Cumplimiento",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        help="Porcentaje de cumplimiento"
                    ),
                    "diff_fmt": st.column_config.TextColumn(
                        "Diferencia",
                        help="Diferencia entre recepcionado y proyectado"
                    ),
                },
                use_container_width=True,
                hide_index=True,
                height=400
            )
        
    else:
        # Estado inicial con mejor diseño
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 40px; border-radius: 15px; text-align: center; border: 1px solid #3498db33;">
            <p style="font-size: 48px; margin: 0;">📈</p>
            <h3 style="color: #fff; margin: 15px 0 10px 0;">Curva de Abastecimiento</h3>
            <p style="color: #aaa; margin: 0;">Selecciona los filtros arriba y presiona <b>Cargar Curva de Abastecimiento</b> para ver la comparativa entre lo proyectado y lo recepcionado.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.expander("ℹ️ ¿Cómo funciona?", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                **📋 Datos Proyectados**
                - Provienen del Excel de planificación
                - Organizados por semana, especie y planta
                - Representan la meta de abastecimiento
                """)
            with col2:
                st.markdown("""
                **✅ Datos del Sistema**
                - Recepciones registradas en Odoo
                - Agrupadas por semana
                - Actualizados en tiempo real
                """)

# =====================================================
#           TAB 4: APROBACIONES MP (Nuevo)
# =====================================================
with tab_aprobaciones:
    st.markdown("### 📥 Aprobaciones de Precios MP")
    st.markdown("Valida masivamente los precios de recepción comparándolos con el presupuesto.")
    
    # Leyenda de semáforos
    st.markdown("""
    <div style="background: rgba(50,50,50,0.5); padding: 10px; border-radius: 8px; margin-bottom: 15px;">
        <b>🚦 Semáforo:</b> 
        <span style="color: #2ecc71;">🟢 OK (0-3%)</span> · 
        <span style="color: #f1c40f;">🟡 Alerta (3-8%)</span> · 
        <span style="color: #e74c3c;">🔴 Crítico (>8%)</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Inicializar session_state
    if 'aprob_data' not in st.session_state:
        st.session_state.aprob_data = None
    if 'aprob_ppto' not in st.session_state:
        st.session_state.aprob_ppto = {}
    
    # --- FILTROS DE FECHA ---
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio_aprob = st.date_input("Desde", datetime.now() - timedelta(days=7), key="fecha_inicio_aprob", format="DD/MM/YYYY")
    with col2:
        fecha_fin_aprob = st.date_input("Hasta", datetime.now() + timedelta(days=1), key="fecha_fin_aprob", format="DD/MM/YYYY")
    
    estado_filtro = st.radio("Estado", ["Pendientes", "Aprobadas", "Todas"], horizontal=True, key="estado_filtro_aprob")

    # Botón de carga
    if st.button("🔄 Cargar Recepciones", type="primary", use_container_width=True):
        with st.spinner("Cargando datos..."):
            try:
                params = {
                    "username": username,
                    "password": password,
                    "fecha_inicio": fecha_inicio_aprob.strftime("%Y-%m-%d"),
                    "fecha_fin": fecha_fin_aprob.strftime("%Y-%m-%d"),
                    "origen": None 
                }
                resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/", params=params, timeout=60)
                
                if resp.status_code == 200:
                    st.session_state.aprob_data = resp.json()
                    # Cargar PPTO
                    try:
                        resp_ppto = requests.get(
                            f"{API_URL}/api/v1/recepciones-mp/abastecimiento/precios",
                            params={"planta": None, "especie": None},
                            timeout=30
                        )
                        if resp_ppto.status_code == 200:
                            st.session_state.aprob_ppto = {item.get('especie', ''): item.get('precio_proyectado', 0) for item in resp_ppto.json()}
                    except:
                        pass
                    st.success(f"✅ Cargadas {len(st.session_state.aprob_data)} recepciones")
                else:
                    st.error(f"Error: {resp.text}")
            except Exception as e:
                st.error(f"Error: {e}")
    
    # --- MOSTRAR DATOS SI EXISTEN ---
    if st.session_state.aprob_data:
        recepciones = st.session_state.aprob_data
        precios_ppto_dict = st.session_state.aprob_ppto
        aprobadas_ids = get_aprobaciones()
        
        # Procesar datos
        filas_aprobacion = []
        for rec in recepciones:
            recep_name = rec.get('albaran', '')
            fecha_recep = rec.get('fecha', '')
            productor = rec.get('productor', '')
            oc = rec.get('orden_compra', '') or rec.get('OC', '') or ''
            es_aprobada = recep_name in aprobadas_ids
            
            if estado_filtro == "Pendientes" and es_aprobada: continue
            if estado_filtro == "Aprobadas" and not es_aprobada: continue

            productos = rec.get('productos', []) or []
            for p in productos:
                cat = (p.get('Categoria') or '').strip().upper()
                if 'BANDEJ' in cat: continue
                    
                kg = p.get('Kg Hechos', 0) or 0
                if kg <= 0: continue
                    
                precio_real = float(p.get('Costo Unitario', 0) or p.get('precio', 0) or 0)
                
                # Obtener nombre del producto
                prod_name_raw = p.get('Producto') or p.get('producto') or ''
                prod_name = prod_name_raw.upper()
                
                # Usar TipoFruta del producto directamente (como hace KPIs)
                tipo_fruta = (p.get('TipoFruta') or rec.get('tipo_fruta') or '').strip()
                manejo = (p.get('Manejo') or '').strip()
                
                # Si hay TipoFruta directo, usarlo
                if tipo_fruta:
                    esp_base = tipo_fruta
                    man_norm = manejo if manejo else 'Convencional'
                else:
                    # Fallback: detectar desde nombre del producto
                    man_norm = 'Orgánico' if ('ORG' in prod_name or 'ORGAN' in manejo.upper()) else 'Convencional'
                    esp_base = 'Otro'
                    # Detectar especie desde código/nombre
                    if 'AR ' in prod_name or 'AR HB' in prod_name or 'ARAND' in prod_name or 'BLUEBERRY' in prod_name:
                        esp_base = 'Arándano'
                    elif 'FR ' in prod_name or 'FRAM' in prod_name or 'MEEKER' in prod_name or 'HERITAGE' in prod_name or 'RASPBERRY' in prod_name:
                        esp_base = 'Frambuesa'
                    elif 'FT ' in prod_name or 'FRUTI' in prod_name or 'STRAW' in prod_name:
                        esp_base = 'Frutilla'
                    elif 'MO ' in prod_name or 'MORA' in prod_name or 'BLACKBERRY' in prod_name:
                        esp_base = 'Mora'
                    elif 'CE ' in prod_name or 'CEREZA' in prod_name or 'CHERRY' in prod_name:
                        esp_base = 'Cereza'
                
                especie_manejo = f"{esp_base} {man_norm}"
                key_ppto = especie_manejo
                ppto_val = precios_ppto_dict.get(key_ppto, 0)
                
                desv = 0
                if ppto_val > 0:
                    desv = ((precio_real - ppto_val) / ppto_val)
                
                sema = "🟢"
                if desv > 0.08: sema = "🔴"
                elif desv > 0.03: sema = "🟡"
                    
                filas_aprobacion.append({
                    "Sel": es_aprobada,
                    "Recepción": recep_name,
                    "Fecha": fmt_fecha(fecha_recep),
                    "Productor": productor,
                    "OC": oc,
                    "Producto": prod_name_raw[:40] if len(prod_name_raw) > 40 else prod_name_raw,  # Truncar si muy largo
                    "Especie": especie_manejo,
                    "Kg": fmt_numero(kg, 2),
                    "$/Kg": fmt_dinero(precio_real),
                    "PPTO": fmt_dinero(ppto_val),
                    "Desv": f"{desv*100:.1f}%",
                    "🚦": sema,
                    "_id": recep_name,
                    "_kg_raw": kg
                })
        
        if filas_aprobacion:
            df_full = pd.DataFrame(filas_aprobacion)
            
            # --- FILTROS ADICIONALES ---
            with st.expander("🔍 Filtros adicionales", expanded=False):
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                with col_f1:
                    filtro_recep = st.text_input("Recepción", "", key="filtro_recep", placeholder="Buscar...")
                with col_f2:
                    filtro_prod = st.selectbox("Productor", ["Todos"] + sorted(df_full["Productor"].unique().tolist()), key="filtro_prod")
                with col_f3:
                    filtro_esp = st.selectbox("Especie", ["Todos"] + sorted(df_full["Especie"].unique().tolist()), key="filtro_esp")
                with col_f4:
                    filtro_oc = st.text_input("OC", "", key="filtro_oc", placeholder="Buscar OC...")
            
            # Aplicar filtros
            df_filtered = df_full.copy()
            if filtro_recep:
                df_filtered = df_filtered[df_filtered["Recepción"].str.contains(filtro_recep, case=False, na=False)]
            if filtro_prod != "Todos":
                df_filtered = df_filtered[df_filtered["Productor"] == filtro_prod]
            if filtro_esp != "Todos":
                df_filtered = df_filtered[df_filtered["Especie"] == filtro_esp]
            if filtro_oc:
                df_filtered = df_filtered[df_filtered["OC"].str.contains(filtro_oc, case=False, na=False)]
            
            # Mostrar tabla
            edited_df = st.data_editor(
                df_filtered,
                column_config={
                    "Sel": st.column_config.CheckboxColumn("✓", default=False, width="small"),
                    "Desv": st.column_config.TextColumn("Desv", width="small"),
                    "$/Kg": st.column_config.TextColumn("$/Kg"),
                    "PPTO": st.column_config.TextColumn("PPTO"),
                    "Kg": st.column_config.TextColumn("Kg"),
                    "🚦": st.column_config.TextColumn("🚦", width="small"),
                    "_id": None,
                    "_kg_raw": None
                },
                column_order=["Sel", "Recepción", "Fecha", "Productor", "OC", "Especie", "Kg", "$/Kg", "PPTO", "Desv", "🚦"],
                disabled=["Recepción", "Fecha", "Productor", "OC", "Especie", "Kg", "$/Kg", "PPTO", "Desv", "🚦"],
                hide_index=True,
                key="editor_aprob",
                height=500,
                use_container_width=True
            )
            
            # --- BARRA DE ESTADO ---
            seleccionados = edited_df[edited_df["Sel"] == True]
            n_sel = len(seleccionados)
            kg_sel = seleccionados["_kg_raw"].sum() if n_sel > 0 else 0
            receps_sel = seleccionados["_id"].nunique() if n_sel > 0 else 0
            
            st.markdown(f"""
            <div style="background: rgba(50,100,150,0.3); padding: 10px; border-radius: 8px; margin: 10px 0;">
                <b>📊 Selección:</b> {n_sel} líneas · {receps_sel} recepciones · {fmt_numero(kg_sel, 2)} Kg
            </div>
            """, unsafe_allow_html=True)
            
            # --- BOTONES DE ACCIÓN ---
            ADMIN_APROBADOR = "mvalladares@riofuturo.cl"
            es_admin = username == ADMIN_APROBADOR
            
            if es_admin:
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    if st.button("✅ Aprobar Seleccionadas", type="primary", use_container_width=True):
                        ids = seleccionados["_id"].unique().tolist()
                        if ids:
                            if save_aprobaciones(ids):
                                st.success(f"✅ Aprobadas {len(ids)} recepciones.")
                                st.rerun()
                        else:
                            st.warning("Selecciona al menos una línea.")
                with col_b:
                    if estado_filtro != "Pendientes":
                        if st.button("↩️ Quitar Aprobación", use_container_width=True):
                            ids_del = seleccionados["_id"].unique().tolist()
                            if ids_del:
                                if remove_aprobaciones(ids_del):
                                    st.warning(f"Se quitó aprobación a {len(ids_del)} recepciones.")
                                    st.rerun()
            else:
                st.info("👁️ Solo visualización. Contacta al administrador para aprobar.")
        else:
            st.info("No hay datos con los filtros seleccionados.")
    else:
        st.info("👆 Selecciona un rango de fechas y presiona **Cargar Recepciones**")

"""
Tab: Curva de Abastecimiento
Comparación entre kilogramos proyectados vs recepcionados.
"""
import streamlit as st
import pandas as pd
import requests
import altair as alt
from datetime import datetime, timedelta
from .shared import fmt_numero, fmt_dinero, fmt_fecha, API_URL


@st.fragment
def render(username: str, password: str):
    """
    Renderiza el contenido del tab Curva de Abastecimiento.
    Fragment independiente para evitar re-renders al cambiar de tab.
    Mantiene button blocking para evitar múltiples consultas.
    """
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
        curva_fecha_inicio = st.date_input("Desde", datetime(2025, 11, 17), format="DD/MM/YYYY", key="curva_desde")
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
    if st.button("📊 Cargar Curva de Abastecimiento", key="btn_curva", type="primary", disabled=st.session_state.recep_curva_loading):
        # Construir lista de plantas
        plantas_list = []
        if curva_rfp:
            plantas_list.append("RFP")
        if curva_vilkun:
            plantas_list.append("VILKUN")

        if not plantas_list:
            st.warning("Debes seleccionar al menos una planta (RFP o VILKÚN)")
        else:
            st.session_state.recep_curva_loading = True
            try:
                # Progress bar personalizado
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                st.session_state.curva_plantas_usadas = plantas_list.copy()

                status_text.text("⏳ Fase 1/4: Conectando con API...")
                progress_bar.progress(25)
                
                # 1. Obtener TODAS las proyecciones del Excel (sin filtro de especie)
                # Construir URL con múltiples parámetros planta
                from urllib.parse import urlencode
                params_proy = {}
                query_string_proy = urlencode(params_proy)
                for planta in plantas_list:
                    query_string_proy += f"&planta={planta}" if query_string_proy else f"planta={planta}"

                status_text.text("⏳ Fase 2/4: Consultando proyecciones...")
                progress_bar.progress(50)
                
                try:
                    url_proy = f"{API_URL}/api/v1/recepciones-mp/abastecimiento/proyectado?{query_string_proy}"
                    resp_proy = requests.get(url_proy, timeout=60)
                    if resp_proy.status_code == 200:
                        proyecciones = resp_proy.json()
                        st.session_state.curva_proyecciones_raw = proyecciones
                    else:
                        st.error(f"Error al cargar proyecciones: {resp_proy.status_code}")
                        st.session_state.curva_proyecciones_raw = None
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
                    st.session_state.curva_proyecciones_raw = None

                status_text.text("⏳ Fase 3/4: Consultando recepciones...")
                progress_bar.progress(75)
                
                # 2. Obtener TODAS las recepciones del sistema (sin filtro de especie)
                params_sist = {
                    "username": username,
                    "password": password,
                    "fecha_inicio": curva_fecha_inicio.strftime("%Y-%m-%d"),
                    "fecha_fin": curva_fecha_fin.strftime("%Y-%m-%d"),
                    "solo_hechas": curva_solo_hechas
                }
                # Construir URL con múltiples parámetros origen
                query_string_sist = urlencode(params_sist)
                for origen in plantas_list:
                    query_string_sist += f"&origen={origen}"
                
                try:
                    url_sist = f"{API_URL}/api/v1/recepciones-mp/?{query_string_sist}"
                    resp_sist = requests.get(url_sist, timeout=120)
                    if resp_sist.status_code == 200:
                        recepciones_sist = resp_sist.json()
                        st.session_state.curva_sistema_raw = recepciones_sist
                        st.toast(f"✅ {len(recepciones_sist)} recepciones cargadas del sistema")
                    else:
                        st.error(f"Error al cargar recepciones del sistema: {resp_sist.status_code} - {resp_sist.text}")
                        st.session_state.curva_sistema_raw = None
                except Exception as e:
                    st.error(f"Error de conexión al sistema: {e}")
                    st.session_state.curva_sistema_raw = None
                    st.session_state.curva_sistema_raw = None
                
                status_text.text("✅ Fase 4/4: Completado")
                progress_bar.progress(100)
                st.toast("✅ Curva de abastecimiento cargada")
            finally:
                st.session_state.recep_curva_loading = False
                st.rerun()

    # ============ MOSTRAR CURVA CON FILTRO DINÁMICO ============
    # Cargar proyecciones dinámicamente basado en filtro de especies actual
    if 'curva_plantas_usadas' in st.session_state and st.session_state.curva_plantas_usadas:
        plantas_usadas = st.session_state.curva_plantas_usadas

        # Cargar proyecciones dinámicamente según filtro actual de especies
        from urllib.parse import urlencode
        params_proy = {}
        query_string_proy = ""
        for planta in plantas_usadas:
            query_string_proy += f"&planta={planta}" if query_string_proy else f"planta={planta}"
        if especies_filtro:
            for especie in especies_filtro:
                query_string_proy += f"&especie={especie}"

        try:
            url_proy = f"{API_URL}/api/v1/recepciones-mp/abastecimiento/proyectado?{query_string_proy}"
            resp_proy = requests.get(url_proy, timeout=30)
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
                
                st.info(f"📊 Procesando {len(recepciones)} recepciones del sistema...")

                # Procesar recepciones igual que KPIs:
                # - Iterar sobre productos
                # - Sumar Kg Hechos por semana
                # - Filtrar por especie+manejo (normalizado)
                kg_por_semana = {}

                for rec in recepciones:
                    # Obtener tipo_fruta, con fallback a productos si no existe en recepción
                    tipo_fruta_row = (rec.get('tipo_fruta') or '').strip()
                    # Si no hay tipo_fruta en recepción, intentar obtener del primer producto válido
                    if not tipo_fruta_row:
                        for p_check in rec.get('productos', []) or []:
                            cat_check = (p_check.get('Categoria') or '').upper()
                            if 'BANDEJ' not in cat_check:
                                tipo_fruta_row = (p_check.get('TipoFruta') or '').strip()
                                if tipo_fruta_row:
                                    break
                    # Si sigue sin tipo_fruta, continuar de todas formas para sumar kg

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

                    # Procesar productos
                    productos = rec.get('productos', []) or []
                    for p in productos:
                        categoria = (p.get('Categoria') or '').strip().upper()
                        producto_nombre = (p.get('Producto') or '').strip().upper()

                        # Excluir solo BANDEJAS por categoría (igual que KPIs)
                        if 'BANDEJ' in categoria:
                            continue

                        kg_hechos = p.get('Kg Hechos', 0) or 0

                        # Solo aplicar filtro de especie si está activo
                        if especies_filtro:
                            tipo_fruta = (rec.get('tipo_fruta') or '').upper()
                            manejo = (p.get('Manejo') or '').upper()

                            # Determinar manejo normalizado
                            if 'ORGAN' in manejo or 'ORGAN' in tipo_fruta:
                                manejo_norm = 'Orgánico'
                            else:
                                manejo_norm = 'Convencional'

                            # Detectar especie
                            if 'ARANDANO' in tipo_fruta or 'ARÁNDANO' in tipo_fruta or 'BLUEBERRY' in tipo_fruta:
                                especie_base = 'Arándano'
                            elif 'FRAM' in tipo_fruta or 'MEEKER' in tipo_fruta or 'HERITAGE' in tipo_fruta or 'RASPBERRY' in tipo_fruta:
                                especie_base = 'Frambuesa'
                            elif 'FRUTILLA' in tipo_fruta or 'FRESA' in tipo_fruta or 'STRAWBERRY' in tipo_fruta:
                                especie_base = 'Frutilla'
                            elif 'MORA' in tipo_fruta or 'BLACKBERRY' in tipo_fruta:
                                especie_base = 'Mora'
                            elif 'CEREZA' in tipo_fruta or 'CHERRY' in tipo_fruta:
                                especie_base = 'Cereza'
                            else:
                                especie_base = 'Otro'

                            especie_manejo = f"{especie_base} {manejo_norm}"
                            if especie_manejo not in especies_filtro:
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
                    total_kg_sistema = df_sistema_semana['kg_sistema'].sum()
                    st.success(f"✅ Sistema: {fmt_numero(total_kg_sistema, 0)} kg procesados en {len(df_sistema_semana)} semanas")
                else:
                    st.warning("⚠️ No se encontraron kg en las recepciones del sistema")

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
                # Dinámico: restamos 1 año a las fechas de la proyección actual
                from datetime import timedelta

                # Obtener los años presentes en la proyección actual
                # Por ejemplo, si la proyección es 2024-2025, los años serán 2024 y 2025
                # El año anterior para comparar debe ser 2023-2024

                if any(s >= 47 for s in semanas_proyeccion):
                    # FECHAS FIJAS para Año Anterior: Temporada 2024-2025
                    # (Temporada actual es 2025-2026)
                    # Desde 01-Nov-2024 hasta 30-Abr-2025
                    fecha_inicio_anterior = datetime(2024, 11, 1)
                    fecha_fin_anterior = datetime(2025, 4, 30, 23, 59, 59)
                else:
                    # Temporada de un solo año
                    year_curr = datetime.now().year
                    fecha_inicio_anterior = datetime(year_curr - 2, 1, 1)
                    fecha_fin_anterior = datetime(year_curr - 2, 12, 31, 23, 59, 59)

                # Llamar a la API para obtener datos del año anterior SIN filtros de planta
                # IMPORTANTE: Incluir username y password que son requeridos por el endpoint
                from urllib.parse import urlencode
                params_anterior = {
                    "username": username,
                    "password": password,
                    "fecha_inicio": fecha_inicio_anterior.strftime("%Y-%m-%d"),
                    "fecha_fin": fecha_fin_anterior.strftime("%Y-%m-%d %H:%M:%S"),
                    "solo_hechas": True  # Boolean correcto, no string
                }
                query_string_ant = urlencode(params_anterior)
                url_anterior = f"{API_URL}/api/v1/recepciones-mp/?{query_string_ant}"
                
                resp_anterior = requests.get(url_anterior, timeout=60)

                if resp_anterior.status_code == 200:
                    try:
                        recepciones_anterior = resp_anterior.json()
                        
                        # VALIDACIÓN: Asegurar que es una lista
                        if not isinstance(recepciones_anterior, list):
                            st.error(f"⚠️ Formato inválido de respuesta del año anterior: se esperaba lista, se recibió {type(recepciones_anterior)}")
                            print(f"[ERROR] Respuesta año anterior no es lista: {type(recepciones_anterior)}")
                            recepciones_anterior = []
                        
                        
                    except Exception as json_error:
                        st.error(f"❌ Error al parsear JSON del año anterior: {json_error}")
                        print(f"[ERROR] JSON parse error: {json_error}")
                        print(f"[ERROR] Respuesta cruda (primeros 500 chars): {resp_anterior.text[:500]}")
                        recepciones_anterior = []

                    for rec in recepciones_anterior:
                        # VALIDACIÓN: Asegurar que cada registro es un diccionario
                        if not isinstance(rec, dict):
                            print(f"[WARNING] Registro no es diccionario, saltando: {type(rec)}")
                            continue
                            
                        # Filtrar recepciones sin tipo_fruta (igual que año actual y KPIs)
                        tipo_fruta_row = (rec.get('tipo_fruta') or '').strip()
                        # Si no hay tipo_fruta en recepción, intentar obtener del primer producto válido
                        if not tipo_fruta_row:
                            for p_check in rec.get('productos', []) or []:
                                cat_check = (p_check.get('Categoria') or '').upper()
                                if 'BANDEJ' not in cat_check:
                                    tipo_fruta_row = (p_check.get('TipoFruta') or '').strip()
                                    if tipo_fruta_row:
                                        break
                        # Si sigue sin tipo_fruta, continuar de todas formas para sumar kg

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
                            producto_nombre = (p.get('Producto') or '').strip().upper()

                            # Excluir bandejas y pallets por categoría únicamente
                            # IMPORTANTE: No filtrar por nombre de producto, ya que 'IQF en Bandeja' son productos válidos
                            if 'BANDEJ' in categoria:
                                continue
                            if 'PALLET' in categoria:
                                continue

                            kg_hechos = p.get('Kg Hechos', 0) or 0
                            if kg_hechos <= 0:
                                continue

                            # SINCRO FILTROS: Aplicar los mismos filtros que el año actual
                            # (especie y manejo) si están activos
                            if especies_filtro:
                                tipo_fruta = (rec.get('tipo_fruta') or '').upper()
                                # Obtener manejo del producto
                                manejo_prod = (p.get('Manejo') or '').strip()
                                if not manejo_prod:
                                    manejo_prod = 'Sin Manejo'

                                # Normalizar especie base (igual que en df_sistema_semana)
                                if 'ARANDANO' in tipo_fruta or 'ARÁNDANO' in tipo_fruta or 'BLUEBERRY' in tipo_fruta:
                                    esp_base = 'Arándano'
                                elif 'FRAM' in tipo_fruta or 'MEEKER' in tipo_fruta or 'HERITAGE' in tipo_fruta or 'RASPBERRY' in tipo_fruta:
                                    esp_base = 'Frambuesa'
                                elif 'FRUTILLA' in tipo_fruta or 'FRESA' in tipo_fruta or 'STRAWBERRY' in tipo_fruta:
                                    esp_base = 'Frutilla'
                                elif 'MORA' in tipo_fruta or 'BLACKBERRY' in tipo_fruta:
                                    esp_base = 'Mora'
                                elif 'CEREZA' in tipo_fruta or 'CHERRY' in tipo_fruta:
                                    esp_base = 'Cereza'
                                else:
                                    esp_base = 'Otro'

                                # Normalizar manejo (Convencional / Orgánico)
                                if 'ORGAN' in manejo_prod.upper() or 'ORGAN' in tipo_fruta:
                                    man_norm = 'Orgánico'
                                else:
                                    man_norm = 'Convencional'

                                especie_key = f"{esp_base} {man_norm}"
                                if especie_key not in especies_filtro:
                                    continue

                            # Acumular por semana
                            if semana not in kg_anterior_por_semana:
                                kg_anterior_por_semana[semana] = 0
                            kg_anterior_por_semana[semana] += kg_hechos


                else:
                    st.error(f"❌ Error al cargar año anterior: código {resp_anterior.status_code}")
                    try:
                        error_detail = resp_anterior.json()
                        st.error(f"Detalle del error: {error_detail}")
                        print(f"[ERROR] Detalle completo: {error_detail}")
                    except:
                        st.error(f"Respuesta del servidor: {resp_anterior.text[:500]}")
                        print(f"[ERROR] Respuesta cruda: {resp_anterior.text}")
            except Exception as e:
                st.error(f"❌ Error de conexión al cargar año anterior: {e}")
                print(f"[ERROR] Exception completa: {e}")
                import traceback
                print(f"[ERROR] Traceback:\n{traceback.format_exc()}")

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

                # Cargar exclusiones usando función centralizada
                from .shared import get_exclusiones
                exclusiones_ids_curva = get_exclusiones()

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
                            from urllib.parse import urlencode
                            query_string_gasto = ""
                            for planta in plantas_usadas:
                                query_string_gasto += f"&planta={planta}" if query_string_gasto else f"planta={planta}"
                            if especies_filtro:
                                for especie in especies_filtro:
                                    query_string_gasto += f"&especie={especie}"
                            url_gasto = f"{API_URL}/api/v1/recepciones-mp/abastecimiento/proyectado?{query_string_gasto}"
                            resp_gasto = requests.get(url_gasto, timeout=30)
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

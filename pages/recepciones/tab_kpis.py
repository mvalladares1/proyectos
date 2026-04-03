"""
Tab: KPIs y Calidad
KPIs de Kg, costos, % IQF/Block y análisis de calidad.
"""
import streamlit as st
import pandas as pd
import requests
import altair as alt
import io
import os
from datetime import datetime, timedelta
from .shared import fmt_numero, fmt_dinero, fmt_fecha, API_URL


@st.fragment
def render(username: str, password: str):
    """
    Renderiza el contenido del tab KPIs y Calidad.
    Fragment independiente para evitar re-renders al cambiar de tab.
    """
    
    # Filtros (Directos, sin form)
    # Checkbox para filtrar solo recepciones en estado "hecho"
    with st.expander("⚙️ Configuración de Filtros", expanded=False):
        solo_hechas = st.checkbox("Solo recepciones hechas", value=True, key="solo_hechas_recepcion", 
                                help="Activa para ver solo recepciones completadas/validadas.")
        
        # Checkboxes para filtrar por origen (RFP / VILKÚN / SAN JOSE)
        st.markdown("**Origen de recepciones:**")
        col_orig1, col_orig2, col_orig3 = st.columns([1, 1, 1])
        with col_orig1:
            check_rfp = st.checkbox("🏭 RFP", value=True, key="check_rfp")
        with col_orig2:
            check_vilkun = st.checkbox("🌿 VILKÚN", value=True, key="check_vilkun")
        with col_orig3:
            check_san_jose = st.checkbox("🏘️ SAN JOSE", value=True, key="check_san_jose")

    # Fechas (arriba para acceso rápido)
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Desde", datetime.now() - timedelta(days=7), key="fecha_inicio_recepcion", format="DD/MM/YYYY")
    with col2:
        fecha_fin = st.date_input("Hasta", datetime.now(), key="fecha_fin_recepcion", format="DD/MM/YYYY")

    # Botón manual para consultar
    if st.button("🔄 Consultar Recepciones", type="primary", key="btn_consultar_recepciones"):
        # Construir lista de orígenes según checkboxes
        origen_list = []
        if check_rfp:
            origen_list.append("RFP")
        if check_vilkun:
            origen_list.append("VILKUN")
        if check_san_jose:
            origen_list.append("SAN JOSE")

        if not origen_list:
            st.warning("Debes seleccionar al menos un origen (RFP, VILKÚN o SAN JOSE)")
        else:
            # Guardar filtros usados en session_state
            st.session_state.origen_filtro_usado = origen_list.copy()
            st.session_state.fecha_inicio_filtro = fecha_inicio
            st.session_state.fecha_fin_filtro = fecha_fin
            st.session_state.solo_hechas_filtro = solo_hechas

            params = {
                "username": username,
                "password": password,
                "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
                "fecha_fin": fecha_fin.strftime("%Y-%m-%d"),
                "solo_hechas": solo_hechas,
            }
            
            # Guardar params en session_state para usar en reportes
            st.session_state.kpis_params = params.copy()
            st.session_state.kpis_origen_list = origen_list.copy()
            
            api_url = f"{API_URL}/api/v1/recepciones-mp/"
            
            # SKELETON LOADER
            skeleton = st.empty()
            with skeleton.container():
                st.markdown("""
                <div style="animation: pulse 1.5s infinite;">
                    <div style="display: flex; gap: 20px; margin-bottom: 20px;">
                        <div style="flex: 1; height: 120px; background-color: #f0f2f6; border-radius: 12px;"></div>
                        <div style="flex: 1; height: 120px; background-color: #f0f2f6; border-radius: 12px;"></div>
                        <div style="flex: 1; height: 120px; background-color: #f0f2f6; border-radius: 12px;"></div>
                    </div>
                     <div style="display: flex; gap: 20px;">
                        <div style="flex: 2; height: 300px; background-color: #f0f2f6; border-radius: 12px;"></div>
                        <div style="flex: 1; height: 300px; background-color: #f0f2f6; border-radius: 12px;"></div>
                    </div>
                </div>
                <style>
                    @keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 0.3; } 100% { opacity: 0.6; } }
                </style>
                """, unsafe_allow_html=True)
            
            try:
                # Construir URL con múltiples parámetros origen si es necesario
                from urllib.parse import urlencode
                query_string = urlencode(params)
                # Agregar cada origen como parámetro separado
                for orig in origen_list:
                    query_string += f"&origen={orig}"
                
                full_url = f"{api_url}?{query_string}"
                resp = requests.get(full_url, timeout=60)
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
            finally:
                skeleton.empty()

    # PLACEHOLDER PARA CONTENIDO - evita que se muestre debajo del skeleton
    content_placeholder = st.container()

    # Mostrar tabla y detalle si hay datos
    with content_placeholder:
        df = st.session_state.df_recepcion
        if df is not None:
            # --- Cargar exclusiones y precio overrides usando funciones centralizadas ---
            from .shared import get_exclusiones, get_precio_override
            exclusiones_ids = get_exclusiones()
            precio_override_map = get_precio_override()  # albaran -> precio_unitario

            # --- KPIs Consolidados ---
            st.subheader("📊 KPIs Consolidados")
            # Calcular Totales separando por categoría de producto (BANDEJAS)
            total_kg_mp = 0.0
            total_costo_mp = 0.0
            total_bandejas = 0.0
            recepciones_excluidas = 0
            recepciones_con_override = 0

            # recorrer todas las recepciones y sus productos
            for _, row in df.iterrows():
                # Asegurarnos que solo consideramos recepciones que sean fruta
                tipo_fruta_row = (row.get('tipo_fruta') or "").strip()
                if not tipo_fruta_row:
                    continue

                # Verificar si esta recepción está excluida de valorización
                recep_id = row.get('id') or row.get('picking_id')
                recep_name = row.get('albaran', '')
                
                # Prioridad: 1) exclusión (no suma costo), 2) precio override, 3) costo original
                excluir_costo = recep_id in exclusiones_ids or recep_name in exclusiones_ids
                precio_override = precio_override_map.get(recep_name) or precio_override_map.get(str(recep_id))
                
                if excluir_costo:
                    recepciones_excluidas += 1
                elif precio_override:
                    recepciones_con_override += 1

                if 'productos' in row and isinstance(row['productos'], list):
                    for p in row['productos']:
                        kg = p.get('Kg Hechos', 0) or 0
                        costo_original = p.get('Costo Total', 0) or 0
                        categoria = (p.get('Categoria') or "").strip().upper()
                        # detectar variantes que contengan 'BANDEJ' (Bandeja/Bandejas)
                        if 'BANDEJ' in categoria:
                            total_bandejas += kg
                        else:
                            total_kg_mp += kg
                            # Calcular costo según prioridad
                            if excluir_costo:
                                # Excluida: no sumar costo
                                pass
                            elif precio_override:
                                # Override: usar precio_unitario * kg
                                total_costo_mp += precio_override * kg
                            else:
                                # Normal: usar costo original
                                total_costo_mp += costo_original

            # Calcular métricas y promedios existentes
            # Nota: eliminamos 'Total Kg Recepcionados (global)'.
            # El "Costo Total (global)" se mostrará en base a Total Kg Recepcionados MP (total_costo_mp).

            # Filtramos solo las que tienen calidad para el promedio de IQF/Block
            df_con_calidad = df[df['calific_final'].notna() & (df['calific_final'] != '')]
            if not df_con_calidad.empty:
                raw_iqf = df_con_calidad['total_iqf'].mean()
                raw_block = df_con_calidad['total_block'].mean()
                total_raw = raw_iqf + raw_block
                if total_raw > 0:
                    prom_iqf = (raw_iqf / total_raw) * 100
                    prom_block = (raw_block / total_raw) * 100
                else:
                    prom_iqf = 0
                    prom_block = 0
                clasif = df_con_calidad['calific_final'].value_counts().idxmax()
            else:
                prom_iqf = 0
                prom_block = 0
                clasif = "-"

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

                # Construir URL con múltiples parámetros planta
                from urllib.parse import urlencode
                url_precios = f"{API_URL}/api/v1/recepciones-mp/abastecimiento/precios"
                if plantas_filtro:
                    query_string = ""
                    for planta in plantas_filtro:
                        query_string += f"&planta={planta}" if query_string else f"planta={planta}"
                    url_precios += f"?{query_string}"
                resp_precios = requests.get(url_precios, timeout=30)
                if resp_precios.status_code == 200:
                    for item in resp_precios.json():
                        especie = item.get('especie', '')
                        precio = item.get('precio_proyectado', 0)
                        precios_proyectados[especie] = precio
            except Exception as e:
                print(f"Error obteniendo precios proyectados: {e}")

            # Obtener kg proyectados por especie_manejo desde el Excel sumando directamente las semanas
            kg_proyectados_por_especie = {}
            try:
                # Obtener fecha HASTA del filtro
                fecha_fin_filtro = st.session_state.get('fecha_fin_filtro')
            
                if fecha_fin_filtro:
                    from datetime import date
                    if isinstance(fecha_fin_filtro, date):
                        fecha_f = fecha_fin_filtro
                    else:
                        fecha_f = datetime.strptime(str(fecha_fin_filtro), '%Y-%m-%d').date()
                
                    # Calcular semana ISO de la fecha HASTA
                    semana_hasta = fecha_f.isocalendar()[1]
                    
                    # Determinar semanas a incluir
                    # Temporada: S47-S52 (2024) + S1-S17 (2025)
                    if semana_hasta >= 47:
                        # Solo parte de 2024
                        semanas_incluir = list(range(47, semana_hasta + 1))
                    else:
                        # 2024 completo + parte de 2025
                        semanas_incluir = list(range(47, 53)) + list(range(1, semana_hasta + 1))
                    
                    # Obtener proyecciones DETALLADAS desde el backend (por productor, planta, especie, semana)
                    # Este endpoint retorna datos más granulares que nos permiten sumar por especie
                    url_proy_det = f"{API_URL}/api/v1/recepciones-mp/abastecimiento/proyectado-detalle"
                    query_params = []
                    if plantas_filtro:
                        for planta in plantas_filtro:
                            query_params.append(f"planta={planta}")
                    
                    if query_params:
                        url_proy_det += f"?{'&'.join(query_params)}"
                    
                    try:
                        resp_det = requests.get(url_proy_det, timeout=30)
                        if resp_det.status_code == 200:
                            proyecciones_detalle = resp_det.json()
                            
                            # Sumar kg por especie_manejo, filtrando solo las semanas incluidas
                            for item in proyecciones_detalle:
                                semana = item.get('semana', 0)
                                if semana in semanas_incluir:
                                    especie_manejo = item.get('especie_manejo', '')
                                    kg = item.get('kg_proyectados', 0)
                                    
                                    if especie_manejo:
                                        if especie_manejo not in kg_proyectados_por_especie:
                                            kg_proyectados_por_especie[especie_manejo] = 0
                                        kg_proyectados_por_especie[especie_manejo] += kg
                        else:
                            # Fallback: Si el endpoint detallado no existe, usar el agregado con proporción
                            print(f"Endpoint detallado no disponible ({resp_det.status_code}), usando método de proporción")
                            raise Exception("Fallback a método de proporción")
                    
                    except Exception as e_det:
                        # Fallback: usar endpoint /precios con proporción de semanas
                        print(f"Error obteniendo proyecciones detalladas: {e_det}, usando fallback")
                        
                        url_kg_especie = f"{API_URL}/api/v1/recepciones-mp/abastecimiento/precios"
                        if plantas_filtro:
                            query_kg = ""
                            for planta in plantas_filtro:
                                query_kg += f"&planta={planta}" if query_kg else f"planta={planta}"
                            url_kg_especie += f"?{query_kg}"
                        
                        resp_kg = requests.get(url_kg_especie, timeout=30)
                        if resp_kg.status_code == 200:
                            especies_kg_total = resp_kg.json()
                            
                            # Calcular proporción de semanas filtradas vs total temporada
                            total_semanas = 23  # S47-S52 (6) + S1-S17 (17)
                            semanas_filtradas = len(semanas_incluir)
                            proporcion = semanas_filtradas / total_semanas if total_semanas > 0 else 0
                            
                            # Aplicar proporción a cada especie
                            for item in especies_kg_total:
                                especie = item.get('especie', '')
                                kg_total_temporada = item.get('kg_total', 0)
                                kg_hasta_fecha = kg_total_temporada * proporcion
                                kg_proyectados_por_especie[especie] = kg_hasta_fecha
            
            except Exception as e:
                print(f"Error obteniendo kg proyectados: {e}")

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
                    tipo_raw = (p.get('TipoFruta') or row.get('tipo_fruta') or '').strip()
                    if not tipo_raw:
                        continue

                    # Normalizar especie BASE (igual que en Curva)
                    tipo_fruta_upper = tipo_raw.upper()
                    manejo_raw = (p.get('Manejo') or '').strip()
                    
                    
                    # Detectar especie base
                    if 'ARANDANO' in tipo_fruta_upper or 'ARÁNDANO' in tipo_fruta_upper or 'BLUEBERRY' in tipo_fruta_upper:
                        tipo = 'Arándano'
                    elif 'FRAM' in tipo_fruta_upper or 'MEEKER' in tipo_fruta_upper or 'HERITAGE' in tipo_fruta_upper or 'RASPBERRY' in tipo_fruta_upper:
                        tipo = 'Frambuesa'
                    elif 'FRUTILLA' in tipo_fruta_upper or 'FRESA' in tipo_fruta_upper or 'STRAWBERRY' in tipo_fruta_upper:
                        tipo = 'Frutilla'
                    elif 'MORA' in tipo_fruta_upper or 'BLACKBERRY' in tipo_fruta_upper:
                        tipo = 'Mora'
                    elif 'CEREZA' in tipo_fruta_upper or 'CHERRY' in tipo_fruta_upper:
                        tipo = 'Cereza'
                    else:
                        tipo = 'Otro'
                    
                    # Normalizar manejo - detectar cualquier variante de "orgánico"
                    manejo_upper = manejo_raw.upper()
                    es_organico = (
                        'ORG' in manejo_upper or  # Org, Organic, Orgánico
                        'ORGÁN' in manejo_upper or  # Con acento
                        'ORG' in tipo_fruta_upper or
                        'ORGÁN' in tipo_fruta_upper
                    )
                    if es_organico:
                        manejo = 'Orgánico'
                    else:
                        manejo = 'Convencional'
                    

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
                
                    # Calcular kg proyectados totales para este tipo de fruta (sumando todos los manejos)
                    kg_proy_tipo = 0
                    for m in agrup[tipo].keys():
                        m_norm = 'Orgánico' if 'org' in m.lower() else 'Convencional'
                        especie_m = f"{tipo} {m_norm}"
                        kg_proy_tipo += kg_proyectados_por_especie.get(especie_m, 0)

                    tabla_rows.append({
                        'tipo': 'fruta',
                        'Descripción': tipo,
                        'Kg': tipo_kg,
                        'PPTO Kg': kg_proy_tipo,
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
                    
                        # Normalizar IQF/Block para que sumen 100%
                        total_iqf_sum = sum(v['iqf_vals']) if v['iqf_vals'] else 0
                        total_block_sum = sum(v['block_vals']) if v['block_vals'] else 0
                        total_calidad = total_iqf_sum + total_block_sum
                        if total_calidad > 0:
                            prom_iqf = (total_iqf_sum / total_calidad) * 100
                            prom_block = (total_block_sum / total_calidad) * 100
                        else:
                            prom_iqf = 0
                            prom_block = 0

                        # Buscar precio proyectado para la combinación tipo + manejo
                        # Formato del Excel: "Arándano Orgánico" o "Frambuesa Convencional"
                        manejo_norm = 'Orgánico' if 'org' in manejo.lower() else 'Convencional'
                        especie_manejo = f"{tipo} {manejo_norm}"
                        precio_proy_manejo = precios_proyectados.get(especie_manejo, precios_proyectados.get(tipo, 0))
                    
                        # Obtener kg proyectados para este especie_manejo
                        kg_proy_manejo = kg_proyectados_por_especie.get(especie_manejo, 0)

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
                            'PPTO Kg': kg_proy_manejo,
                            'Costo Total': costo,
                            'Costo/Kg': costo_prom,
                            'Precio Proy': precio_proy_manejo,
                            '% IQF': prom_iqf,
                            '% Block': prom_block
                        })

                # Fila total
                total_kg_proy = sum(kg_proyectados_por_especie.values())
                tabla_rows.append({
                    'tipo': 'total',
                    'Descripción': 'TOTAL GENERAL',
                    'Kg': total_kg_tabla,
                    'PPTO Kg': total_kg_proy,
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
                df_display['PPTO Kg'] = df_display['PPTO Kg'].apply(lambda x: fmt_numero(x, 0) if pd.notna(x) and x > 0 else "—")
            
                # Calcular % Cumplimiento (Kg / PPTO Kg * 100)
                def calcular_cumplimiento(row):
                    kg_real = row.get('Kg', 0) or 0
                    if isinstance(kg_real, str): # Check if already formatted
                        return None
                    kg_proy = row.get('PPTO Kg', 0) or 0
                    if isinstance(kg_proy, str): # Check if already formatted
                        return None
                    if kg_proy > 0:
                        return (kg_real / kg_proy) * 100
                    return None
            
                # Calcular antes del formateo de Kg
                df_resumen['% Cumpl_Num'] = df_resumen.apply(calcular_cumplimiento, axis=1)
                df_display['% Cumpl'] = df_resumen['% Cumpl_Num'].apply(lambda x: f"{fmt_numero(x, 1)}%" if pd.notna(x) and x > 0 else "—")
            
                df_display['Costo Total'] = df_display['Costo Total'].apply(lambda x: fmt_dinero(x) if pd.notna(x) else "—")
                df_display['Costo/Kg'] = df_display['Costo/Kg'].apply(lambda x: fmt_dinero(x) if pd.notna(x) and x > 0 else "—")
                df_display['Precio Proy'] = df_display['Precio Proy'].apply(lambda x: fmt_dinero(x) if pd.notna(x) and x > 0 else "—")
                df_display['% Desv'] = df_display['Desv_Num'].apply(formatear_desviacion)
                df_display['% IQF'] = df_display['% IQF'].apply(lambda x: f"{fmt_numero(x, 1)}%" if pd.notna(x) and x > 0 else "—")
                df_display['% Block'] = df_display['% Block'].apply(lambda x: f"{fmt_numero(x, 1)}%" if pd.notna(x) and x > 0 else "—")

                # Mostrar usando columnas estilizadas
                df_show = df_display[['Descripción', 'Kg', 'PPTO Kg', '% Cumpl', 'Costo Total', 'Costo/Kg', 'Precio Proy', '% Desv', '% IQF', '% Block']]

                # Usar st.dataframe con column_config para mejor visualización
                st.dataframe(
                    df_show,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'Descripción': st.column_config.TextColumn('Tipo / Manejo', width='large'),
                        'Kg': st.column_config.TextColumn('Kg', width='small'),
                        'PPTO Kg': st.column_config.TextColumn('PPTO Kg', width='small'),
                        '% Cumpl': st.column_config.TextColumn('% Cumpl', width='small'),
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
        
            # Usar params guardados si existen, sino crear params básicos
            if 'kpis_params' in st.session_state and st.session_state.kpis_params:
                params = st.session_state.kpis_params.copy()
            else:
                params = {
                    'username': username,
                    'password': password,
                    'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
                    'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
                    'solo_hechas': solo_hechas
                }
        
            informe_cols = st.columns([1,1,1])
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
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
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
            with col_f4:
                variedades_set = set()
                for _, row in df.iterrows():
                    if 'productos' in row and isinstance(row['productos'], list):
                        for p in row['productos']:
                            variedad = (p.get('Variedad') or p.get('variedad') or '').strip()
                            if variedad:
                                for part in [v.strip() for v in str(variedad).split(',') if v and v.strip()]:
                                    variedades_set.add(part)
                variedades = sorted(list(variedades_set))
                variedad_filtro = st.multiselect("Filtrar por Variedad", variedades, key="variedad_filtro")

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

            # Filtrar por Variedad (si algún producto de la recepción contiene alguna variedad seleccionada)
            if variedad_filtro:
                def tiene_variedad(row):
                    if 'productos' in row and isinstance(row['productos'], list):
                        for p in row['productos']:
                            variedad = str((p.get('Variedad') or p.get('variedad') or '')).strip()
                            if variedad and any(v in variedad for v in variedad_filtro):
                                return True
                    return False
                df_filtrada = df_filtrada[df_filtrada.apply(tiene_variedad, axis=1)]

            # Resumen de kg por manejo + variedad
            st.subheader("📊 Kg por Manejo y Variedad")
            rows_mv = []
            for _, row in df_filtrada.iterrows():
                prods = row.get('productos', []) or []
                if not isinstance(prods, list):
                    continue
                for p in prods:
                    categoria = (p.get('Categoria') or '').strip().upper()
                    if 'BANDEJ' in categoria:
                        continue
                    kg = p.get('Kg Hechos', 0) or 0
                    if kg <= 0:
                        continue
                    rows_mv.append({
                        'Tipo Fruta': (p.get('TipoFruta') or row.get('tipo_fruta') or 'N/A').strip() or 'N/A',
                        'Manejo': (p.get('Manejo') or 'N/A').strip() or 'N/A',
                        'Variedad': (p.get('Variedad') or p.get('variedad') or 'Sin Variedad').strip() or 'Sin Variedad',
                        'Kg': kg,
                    })

            if rows_mv:
                df_mv = pd.DataFrame(rows_mv)
                df_mv = (
                    df_mv.groupby(['Tipo Fruta', 'Manejo', 'Variedad'], as_index=False)['Kg']
                    .sum()
                    .sort_values(['Kg', 'Tipo Fruta', 'Manejo', 'Variedad'], ascending=[False, True, True, True])
                )
                df_mv['Kg'] = df_mv['Kg'].apply(lambda x: fmt_numero(x, 2))
                st.dataframe(df_mv, use_container_width=True, hide_index=True)
            else:
                st.info("No hay datos para mostrar en el resumen de manejo y variedad con los filtros actuales.")

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

            variedades_vals = []
            for _, row in df_filtrada.iterrows():
                variedades_row = set()
                prods = row.get('productos', []) or []
                if isinstance(prods, list):
                    for p in prods:
                        var_raw = (p.get('Variedad') or p.get('variedad') or '').strip()
                        if var_raw:
                            variedades_row.add(var_raw)
                variedades_vals.append(', '.join(sorted(variedades_row)) if variedades_row else 'Sin Variedad')
            df_filtrada['variedades'] = variedades_vals

            # Verificar si existe columna 'origen' (datos antiguos pueden no tenerla)
            if 'origen' not in df_filtrada.columns:
                df_filtrada['origen'] = 'RFP'  # Default para datos antiguos

            cols_mostrar = [
                "albaran", "fecha", "productor", "tipo_fruta", "variedades", "origen", "guia_despacho",
                "bandejas", "kg_recepcionados", "calific_final", "total_iqf", "total_block", "tiene_calidad"
            ]
            df_mostrar = df_filtrada[cols_mostrar].copy()
            df_mostrar.columns = [
                "Albarán", "Fecha", "Productor", "Tipo Fruta", "Variedades", "Origen", "Guía Despacho",
                "Bandejas", "Kg Recepcionados", "Clasificación", "% IQF", "% Block", "Calidad"
            ]
            # Convertir a numérico y formatear (NO restar bandejas, el servicio ya excluye bandejas del kg_total)
            df_mostrar["Bandejas"] = pd.to_numeric(df_mostrar["Bandejas"], errors='coerce').fillna(0.0)
            df_mostrar["Kg Recepcionados"] = pd.to_numeric(df_mostrar["Kg Recepcionados"], errors='coerce').fillna(0.0)
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
            @st.fragment
            def render_excel_detallado():
                """Fragment para generar Excel detallado sin hacer re-render de toda la página."""
                det_col1, det_col2 = st.columns([1,3])
                with det_col1:
                    # Inicializar estado
                    if 'excel_detallado_data' not in st.session_state:
                        st.session_state.excel_detallado_data = None
                
                    if st.button("📊 Generar Excel Detallado", type="primary", key="btn_generar_excel_det"):
                        try:
                            with st.spinner("Generando Excel detallado en el servidor..."):
                                # Construir parámetros pasando las listas de filtros
                                params_excel = {**params, 'include_prev_week': False, 'include_month_accum': False}

                                # Pasar listas directamente para que requests envíe múltiples query params
                                if tipo_fruta_filtro:
                                    params_excel['tipo_fruta'] = tipo_fruta_filtro if isinstance(tipo_fruta_filtro, list) else [tipo_fruta_filtro]
                                if clasif_filtro:
                                    params_excel['clasificacion'] = clasif_filtro if isinstance(clasif_filtro, list) else [clasif_filtro]
                                if manejo_filtro:
                                    params_excel['manejo'] = manejo_filtro if isinstance(manejo_filtro, list) else [manejo_filtro]
                                if productor_filtro:
                                    params_excel['productor'] = productor_filtro if isinstance(productor_filtro, list) else [productor_filtro]

                                # Pasar filtro de origen (planta) al Excel
                                origen_filtro_usado = st.session_state.get('origen_filtro_usado', [])
                                if origen_filtro_usado:
                                    params_excel['origen'] = origen_filtro_usado

                                resp = requests.get(f"{API_URL}/api/v1/recepciones-mp/report.xlsx", params=params_excel, timeout=180)

                            if resp.status_code == 200:
                                xlsx_bytes = resp.content
                                fname = f"recepciones_detalle_{params['fecha_inicio']}_a_{params['fecha_fin']}.xlsx".replace('/', '-')
                                # Guardar en session_state
                                st.session_state.excel_detallado_data = (xlsx_bytes, fname)
                                st.success("✅ Excel generado correctamente. Haz clic en 'Descargar' para obtenerlo.")
                            else:
                                st.error(f"Error al generar Excel detallado: {resp.status_code} - {resp.text}")
                        except Exception as e:
                            st.error(f"Error al solicitar Excel detallado: {e}")
            
                with det_col2:
                    # Mostrar botón de descarga si hay datos disponibles
                    if st.session_state.excel_detallado_data:
                        xlsx_bytes, fname = st.session_state.excel_detallado_data
                        st.download_button(
                            "📥 Descargar Excel (Detallado - Por Producto)", 
                            xlsx_bytes, 
                            file_name=fname, 
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            key="btn_download_excel_det"
                        )
                        # Botón para limpiar
                        if st.button("🗑️ Limpiar", key="btn_clear_excel_det"):
                            st.session_state.excel_detallado_data = None
            
            # Renderizar fragment de Excel detallado
            render_excel_detallado()
            
            # NUEVO: Botón extra para descargar Reporte de Calidad Detallado
            st.markdown("---")
            
            @st.fragment
            def render_excel_defectos():
                """Fragment para generar Reporte de Calidad Detallado sin hacer re-render de toda la página."""
                st.subheader("📊 Reporte de Calidad Detallado")
            
                def_col1, def_col2 = st.columns([1,3])
                with def_col1:
                    # Inicializar estado
                    if 'excel_defectos_data' not in st.session_state:
                        st.session_state.excel_defectos_data = None
                
                    if st.button("� Generar Reporte de Calidad Detallado", type="primary", key="btn_generar_excel_defectos"):
                        try:
                            with st.spinner("Generando reporte de calidad detallado en el servidor..."):
                                # Obtener origen filtro desde session_state
                                origen_filtro_usado = st.session_state.get('origen_filtro_usado', [])
                                
                                # Si no hay origen guardado, usar todos por defecto
                                if not origen_filtro_usado:
                                    origen_filtro_usado = ["RFP", "VILKUN", "SAN JOSE"]
                                
                                # Usar los mismos parámetros de filtro
                                params_defectos = {
                                    'username': username,
                                    'password': password,
                                    'fecha_inicio': params['fecha_inicio'],
                                    'fecha_fin': params['fecha_fin'],
                                    'solo_hechas': params.get('solo_hechas', True),
                                }
                                
                                # Pasar origen como lista (múltiples parámetros origen=X&origen=Y)
                                if origen_filtro_usado:
                                    # requests maneja listas creando múltiples query params
                                    params_defectos['origen'] = origen_filtro_usado
                            
                                resp = requests.get(
                                    f"{API_URL}/api/v1/recepciones-mp/report-defectos.xlsx",
                                    params=params_defectos,
                                    timeout=180
                                )
                        
                            if resp.status_code == 200:
                                xlsx_bytes = resp.content
                                fname = f"recepciones_calidad_detallado_{params['fecha_inicio']}_a_{params['fecha_fin']}.xlsx".replace('/', '-')
                                # Guardar en session_state
                                st.session_state.excel_defectos_data = (xlsx_bytes, fname)
                                st.success("✅ Reporte de calidad detallado generado correctamente. Haz clic en 'Descargar' para obtenerlo.")
                            else:
                                st.error(f"Error al generar reporte de calidad detallado: {resp.status_code} - {resp.text}")
                        except Exception as e:
                            st.error(f"Error al solicitar reporte de calidad detallado: {e}")
            
                with def_col2:
                    # Mostrar botón de descarga si hay datos disponibles
                    if st.session_state.excel_defectos_data:
                        xlsx_bytes, fname = st.session_state.excel_defectos_data
                        st.download_button(
                            "📥 Descargar Reporte de Calidad Detallado", 
                            xlsx_bytes, 
                            file_name=fname, 
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            key="btn_download_excel_defectos"
                        )
                        # Botón para limpiar
                        if st.button("🗑️ Limpiar", key="btn_clear_excel_defectos"):
                            st.session_state.excel_defectos_data = None
            
            # Renderizar fragment de calidad detallado
            render_excel_defectos()

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

            # Si múltiples plantas están seleccionadas, mostrar un gráfico por cada una
            if len(origen_filtro_usado) >= 2 and 'origen' in df_filtrada.columns:
                # =================================================================
                #  GRÁFICO CONSOLIDADO (Todas las plantas seleccionadas)
                # =================================================================
                plantas_str = " + ".join(origen_filtro_usado)
                st.subheader(f"📊 CONSOLIDADO - Kg recepcionados por día ({plantas_str})")
                chart_consolidado = crear_grafico_planta(df_filtrada, 'CONSOLIDADO', '#8e44ad')
                st.altair_chart(chart_consolidado, use_container_width=True)
                # Calcular total consolidado excluyendo bandejas
                total_consolidado = 0.0
                for _, row in df_filtrada.iterrows():
                    for p in row.get('productos', []) or []:
                        cat = (p.get('Categoria') or '').strip().upper()
                        if 'BANDEJ' not in cat:
                            total_consolidado += p.get('Kg Hechos', 0) or 0
                st.caption(f"**Total Consolidado:** {fmt_numero(total_consolidado, 0)} Kg")
            
                st.markdown("---")
            
                # =================================================================
                #  GRÁFICO RFP
                # =================================================================
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

                st.markdown("---")

                # =================================================================
                #  GRÁFICO SAN JOSE
                # =================================================================
                st.subheader("🏘️ SAN JOSE - Kg recepcionados por día (por Tipo de Fruta)")
                df_san_jose = df_filtrada[df_filtrada['origen'] == 'SAN JOSE']
                if not df_san_jose.empty:
                    chart_san_jose = crear_grafico_planta(df_san_jose, 'SAN JOSE', '#e67e22')
                    st.altair_chart(chart_san_jose, use_container_width=True)
                    # Calcular total excluyendo bandejas
                    total_san_jose = 0.0
                    for _, row in df_san_jose.iterrows():
                        for p in row.get('productos', []) or []:
                            cat = (p.get('Categoria') or '').strip().upper()
                            if 'BANDEJ' not in cat:
                                total_san_jose += p.get('Kg Hechos', 0) or 0
                    st.caption(f"**Total SAN JOSE:** {fmt_numero(total_san_jose, 0)} Kg")
                else:
                    st.info("No hay datos de SAN JOSE en el período seleccionado")

                # Resumen comparativo
                st.markdown("---")
                st.markdown("**📊 Resumen Comparativo:**")
                col_p1, col_p2, col_p3 = st.columns(3)
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
                with col_p3:
                    # Calcular total SAN JOSE excluyendo bandejas
                    total_san_jose_comp = 0.0
                    df_san_jose_comp = df_filtrada[df_filtrada['origen'] == 'SAN JOSE'] if 'origen' in df_filtrada.columns else df_filtrada.head(0)
                    for _, row in df_san_jose_comp.iterrows():
                        for p in row.get('productos', []) or []:
                            cat = (p.get('Categoria') or '').strip().upper()
                            if 'BANDEJ' not in cat:
                                total_san_jose_comp += p.get('Kg Hechos', 0) or 0
                    st.metric("🏘️ SAN JOSE", f"{fmt_numero(total_san_jose_comp, 0)} Kg")
            else:
                # Solo una planta seleccionada - mostrar gráfico normal
                planta_actual = origen_filtro_usado[0] if origen_filtro_usado else "Planta"
                emoji = "🏭" if planta_actual == "RFP" else "🌿" if planta_actual == "VILKUN" else "🏘️"
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

"""
Tab: Clasificación de Pallets
Muestra la clasificación de pallets por IQF A y RETAIL con filtros de fecha, fruta y manejo.
"""
import streamlit as st
import pandas as pd
import altair as alt
import requests
from datetime import datetime, timedelta

from .shared import API_URL, fmt_numero


@st.fragment
def render(username: str, password: str):
    """Renderiza el contenido del tab Clasificación."""
    
    # --- CONFIGURACIÓN DE SALAS (Odoo Keys y Labels) ---
    SALA_MAP_INTERNAL = {
        "Sala 1 - Línea Retail": "Sala 1 - Linea Retail",
        "Sala 2 - Línea Granel": "Sala 2 - Linea Granel",
        "Sala 3 - Línea Granel": "Sala 3 - Linea Granel",
        "Sala 3 - Línea Retail": "Sala 3 - Linea Retail",
        "Sala 4 - Línea Retail": "Sala 4 - Linea Retail",
        "Sala 4 - Línea Chocolate": "Sala 4 - Linea Chocolate",
        "Sala - Vilkun": "Sala - Vilkun"
    }

    st.markdown("### 📦 CLASIFICACIÓN DE PALLETS")
    st.caption("Grados de producto terminado por planta y orden")
    
    # === FILTROS ===
    with st.container():
        col_filtros1, col_filtros2 = st.columns(2)
        
        with col_filtros1:
            # Filtro de fechas
            fecha_inicio_clas = st.date_input(
                "Fecha Inicio",
                value=datetime.now() - timedelta(days=30),
                key="fecha_inicio_clasificacion"
            )
            
            # Filtro de tipo de fruta
            tipo_fruta_opciones = ["Todas", "Arándano", "Frambuesa", "Frutilla", "Mora"]
            tipo_fruta_seleccionado = st.selectbox(
                "Tipo de Fruta",
                options=tipo_fruta_opciones,
                index=0,
                key="tipo_fruta_clasificacion"
            )
        
        
        with col_filtros2:
            fecha_fin_clas = st.date_input(
                "Fecha Fin",
                value=datetime.now(),
                key="fecha_fin_clasificacion"
            )
            
            # Filtro de tipo de manejo
            tipo_manejo_opciones = ["Todos", "Orgánico", "Convencional"]
            tipo_manejo_seleccionado = st.selectbox(
                "Tipo de Manejo",
                options=tipo_manejo_opciones,
                index=0,
                key="tipo_manejo_clasificacion"
            )
        
        # Filtro de Sala de Proceso y Planta (nueva fila)
        col_fil_3_1, col_fil_3_2 = st.columns([2, 1])
        
        with col_fil_3_1:
            sala_proceso_opciones = ["Todas"] + list(SALA_MAP_INTERNAL.keys())
            sala_proceso_seleccionada = st.selectbox(
                "🏢 Sala de Proceso",
                options=sala_proceso_opciones,
                index=0,
                key="sala_proceso_clasificacion",
                help="Selecciona la sala de proceso donde se fabricó el producto"
            )
            
        with col_fil_3_2:
            tipo_operacion_opciones = ["Todas", "VILKUN", "RIO FUTURO"]
            tipo_operacion_seleccionado = st.selectbox(
                "🏢 Planta / Operación",
                options=tipo_operacion_opciones,
                index=0,
                key="tipo_operacion_clasificacion"
            )

        # Mapeo de grados por defecto (se muestran todos al inicio)
        GRADOS_MAP = {
            'IQF AA': '1', 'IQF A': '2', 'PSP': '3', 'W&B': '4', 
            'Block': '5', 'Jugo': '6', 'IQF Retail': '7'
        }
        codigos_grados_seleccionados = list(GRADOS_MAP.values())
        grados_seleccionados = list(GRADOS_MAP.keys())
        
        # Botón consultar
        consultar = st.button("🔍 Consultar Clasificación", use_container_width=True, type="primary")
    
    # --- CSS PREMIUM (Estilo Kiosko/TV) ---
    st.markdown("""
    <style>
        .premium-card {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 1.2rem;
            border-radius: 12px;
            text-align: center;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        .premium-value {
            font-size: 2rem;
            font-weight: 800;
            margin: 0.2rem 0;
        }
        .premium-label {
            font-size: 0.9rem;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .po-container {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 1rem;
            border-left: 5px solid #3498db;
            margin-top: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

    # === CONSULTA Y PRESENTACIÓN ===
    if consultar or st.session_state.get("clasificacion_data"):
        if consultar:
            # Llamar al endpoint
            fecha_inicio_str = fecha_inicio_clas.strftime("%Y-%m-%d")
            fecha_fin_str = fecha_fin_clas.strftime("%Y-%m-%d")
            
            # Preparar parámetros opcionales
            tipo_fruta_param = None if tipo_fruta_seleccionado == "Todas" else tipo_fruta_seleccionado
            tipo_manejo_param = None if tipo_manejo_seleccionado == "Todos" else tipo_manejo_seleccionado
            
            # Obtener clave técnica de la sala
            sala_key = SALA_MAP_INTERNAL.get(sala_proceso_seleccionada)
            sala_param = sala_key if sala_key else None
            
            with st.spinner("⏳ Consultando clasificación de pallets..."):
                try:
                    params = {
                        "username": username,
                        "password": password,
                        "fecha_inicio": fecha_inicio_str,
                        "fecha_fin": fecha_fin_str,
                        "tipo_operacion": tipo_operacion_seleccionado
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
                        st.session_state.clasificacion_data = data
                        count = len(data.get('detalle', []))
                        if count > 0:
                            st.success(f"✅ Se cargaron {count} pallets correctamente ({tipo_operacion_seleccionado})")
                        else:
                            st.info(f"ℹ️ No se encontraron pallets para el periodo seleccionado en Odoo.")
                    else:
                        st.error(f"❌ Error al obtener datos: {response.status_code}")
                        return
                        
                except Exception as e:
                    st.error(f"❌ Error en la consulta: {str(e)}")
                    return
        
        # Mostrar datos
        data = st.session_state.clasificacion_data
        
        # --- REGLA DE ORO: FILTRADO DINÁMICO ESTRICTO (Intersección) ---
        # Filtramos lo que hay en memoria según los widgets actuales de la pantalla
        detalle_raw = data.get('detalle', [])
        
        # 1. Filtrar por Planta (si el usuario cambió el dropdown sin re-consultar)
        if tipo_operacion_seleccionado != "Todas":
            detalle_raw = [d for d in detalle_raw if d.get('planta') == tipo_operacion_seleccionado]
            
        # 2. Filtrar por Fruta
        if tipo_fruta_seleccionado != "Todas":
            detalle_raw = [d for d in detalle_raw if tipo_fruta_seleccionado.lower() in d.get('producto', '').lower()]
            
        # 3. Filtrar por Sala de Proceso (dinámico robusto)
        if sala_proceso_seleccionada != "Todas":
            target_key = SALA_MAP_INTERNAL.get(sala_proceso_seleccionada)
            
            def normalize(text):
                if not text: return ""
                text = text.lower()
                replacements = [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]
                for old, new in replacements:
                    text = text.replace(old, new)
                return text

            target_norm = normalize(target_key or sala_proceso_seleccionada)
            detalle_raw = [
                d for d in detalle_raw 
                if normalize(d.get('sala')) == target_norm or 
                   target_norm in normalize(d.get('sala'))
            ]

        # 4. Filtrar por Manejo
        tipo_manejo_val = tipo_manejo_seleccionado or "Todos"
        if tipo_manejo_val != "Todos":
            # Usar lógica de código si está disponible, o simplemente filtrar detalle
            for d in detalle_raw:
                code = d.get('codigo_producto', '')
                if len(code) >= 4:
                    m_digit = code[3]
                    is_org = m_digit == '2'
                    if tipo_manejo_val == "Orgánico" and not is_org:
                        d['_remove'] = True
                    elif tipo_manejo_val == "Convencional" and is_org:
                        d['_remove'] = True
            detalle_raw = [d for d in detalle_raw if not d.get('_remove')]

        if not detalle_raw:
            st.warning("⚠️ No hay datos con los filtros seleccionados.")
            return

        # Re-mapear grados_raw basado en este detalle ultra-filtrado
        grados_raw = {str(i): 0 for i in range(1, 8)}
        GRADOS_REVERSE = {'IQF AA': '1', 'IQF A': '2', 'PSP': '3', 'W&B': '4', 'Block': '5', 'Jugo': '6', 'IQF Retail': '7'}
        for d in detalle_raw:
            g_code = GRADOS_REVERSE.get(d.get('grado'))
            if g_code:
                grados_raw[g_code] += d.get('kg', 0)
        
        # Mapeo de información visual
        GRADOS_INFO = {
            '1': {'nombre': 'IQF AA', 'emoji': '⭐', 'color': '#FFD700'},
            '2': {'nombre': 'IQF A', 'emoji': '🔵', 'color': '#4472C4'},
            '3': {'nombre': 'PSP', 'emoji': 'Purple', 'color': '#9966FF'},
            '4': {'nombre': 'W&B', 'emoji': '🟤', 'color': '#8B4513'},
            '5': {'nombre': 'Block', 'emoji': '🟦', 'color': '#1E90FF'},
            '6': {'nombre': 'Jugo', 'emoji': '🟠', 'color': '#FF8C00'},
            '7': {'nombre': 'IQF Retail', 'emoji': '🟢', 'color': '#70AD47'}
        }
        
        # === GRÁFICO DE BARRAS INTERACTIVO (Control Principal) ===
        st.markdown("---")
        st.markdown("#### 📈 Distribución por Grado")
        st.info("💡 **Gráfico Interactivo:** Haz clic en los cuadros de la leyenda para filtrar los KPIs y la tabla detallada.")
        
        # Preparar data para el gráfico (usando grados_raw que ya tiene los filtros aplicados)
        base_data_list = []
        for grado_num, info in GRADOS_INFO.items():
            kg = grados_raw.get(grado_num, 0)
            if kg > 0:
                base_data_list.append({
                    'Grado': info['nombre'],
                    'Kilogramos': kg,
                    'Color': info['color'],
                    'grado_num': grado_num
                })
        
        df_chart = pd.DataFrame(base_data_list)
        
        if not df_chart.empty:
            # Selección de Altair (punto bound a leyenda)
            seleccion_chart = alt.selection_point(fields=['Grado'], bind='legend')
            
            # Gráfico de Barras
            bars = alt.Chart(df_chart).mark_bar(
                cornerRadiusTopLeft=8,
                cornerRadiusTopRight=8
            ).encode(
                x=alt.X('Grado:N', title='Grado de Producto', axis=alt.Axis(labelAngle=-45, labelFontSize=12)),
                y=alt.Y('Kilogramos:Q', title='Kilogramos (kg)', axis=alt.Axis(labelFontSize=12)),
                color=alt.Color('Grado:N',
                               scale=alt.Scale(
                                   domain=[info['nombre'] for info in GRADOS_INFO.values()],
                                   range=[info['color'] for info in GRADOS_INFO.values()]
                               ),
                               legend=alt.Legend(title="Click para filtrar", orient="right")),
                opacity=alt.condition(seleccion_chart, alt.value(1), alt.value(0.2)),
                tooltip=[alt.Tooltip('Grado:N'), alt.Tooltip('Kilogramos:Q', format=',.2f')]
            )
            
            chart_final = bars.add_params(
                seleccion_chart
            ).properties(
                height=400
            ).configure_view(
                strokeWidth=0
            )
            
            # Renderizar gráfico y capturar evento de selección
            event = st.altair_chart(chart_final, use_container_width=True, on_select="rerun")
            
            # Definir qué grados mostrar basado en la selección del gráfico
            selected_from_chart = event.get('selection', {}).get('Grado', [])
            
            if selected_from_chart:
                active_grades_names = selected_from_chart
                active_grades_codes = [k for k, v in GRADOS_INFO.items() if v['nombre'] in selected_from_chart]
            else:
                # Si no hay selección, mostramos todos los que tienen data
                active_grades_names = df_chart['Grado'].tolist()
                active_grades_codes = df_chart['grado_num'].tolist()
        else:
            st.warning("⚠️ No hay datos de producción para el período seleccionado.")
            return

        # --- FILTRADO DINÁMICO DE DATOS PARA KPIs Y TABLA ---
        # ATENCIÓN: No sobreescribir con data.get(...), usar los ya filtrados arriba
        grados_mostrar = {k: v for k, v in grados_raw.items() if k in active_grades_codes}
        detalle_mostrar = [item for item in detalle_raw if item.get('grado') in active_grades_names]
        total_kg_filtrado = sum(grados_mostrar.values())
        
        # === KPIs ===
        st.markdown("---")
        st.markdown(f"#### 📊 Totales Filtrados ({len(active_grades_names)} grados)")
        
        col1, col2, col3, col4 = st.columns(4)
        
        def render_compact_card(id_grado, col):
            info = GRADOS_INFO.get(id_grado)
            kg = grados_mostrar.get(id_grado, 0)
            with col:
                st.markdown(f"""
                <div class="premium-card" style="background: linear-gradient(135deg, {info['color']}, {info['color']}dd); padding: 0.8rem;">
                    <div class="premium-label" style="font-size: 0.8rem;">{info['emoji']} {info['nombre']}</div>
                    <div class="premium-value" style="font-size: 1.5rem;">{fmt_numero(kg)} kg</div>
                </div>
                """, unsafe_allow_html=True)

        render_compact_card('1', col1)
        render_compact_card('2', col2)
        render_compact_card('3', col3)
        render_compact_card('4', col4)
            
        col5, col6, col7, col8 = st.columns(4)
        render_compact_card('5', col5)
        render_compact_card('6', col6)
        render_compact_card('7', col7)
        with col8:
            st.markdown(f"""
            <div class="premium-card" style="background: linear-gradient(135deg, #2c3e50, #000000); padding: 0.8rem;">
                <div class="premium-label" style="font-size: 0.8rem;">📦 TOTAL SELECCIONADO</div>
                <div class="premium-value" style="font-size: 1.5rem;">{fmt_numero(total_kg_filtrado)} kg</div>
            </div>
            """, unsafe_allow_html=True)

        
        # === TABLA DETALLADA ===
        if detalle_mostrar:
            st.markdown("---")
            st.markdown(f"#### 📋 Detalle de Pallets ({len(detalle_mostrar)} registros)")
            
            # Convertir a DataFrame
            df_detalle = pd.DataFrame(detalle_mostrar)
            
            # Formatear columnas
            df_detalle['kg'] = df_detalle['kg'].apply(lambda x: f"{x:,.2f}")
            df_detalle['fecha'] = pd.to_datetime(df_detalle['fecha']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Traducir Sala (Key -> Label)
            SALA_REVERSE = {v: k for k, v in SALA_MAP_INTERNAL.items()}
            df_detalle['sala'] = df_detalle['sala'].map(lambda x: SALA_REVERSE.get(x, x))
            
            # Renombrar columnas para display
            df_display = df_detalle[[
                'pallet', 'producto', 'codigo_producto', 'grado', 'kg', 'orden_fabricacion', 'planta', 'sala', 'fecha'
            ]].copy()
            
            df_display.columns = [
                'Pallet', 'Producto', 'Código', 'Grado', 'Kilogramos', 'Orden Fabricación', 'Planta', 'Sala', 'Inicio Proceso'
            ]
            
            # Mostrar tabla
            st.dataframe(
                df_display,
                use_container_width=True,
                height=400,
                hide_index=True
            )
            
            # Exportar a Excel
            if st.button("📥 Exportar a Excel (Filtrado)", key="export_clasificacion"):
                try:
                    import io
                    buffer = io.BytesIO()
                    
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df_display.to_excel(writer, index=False, sheet_name='Clasificación')
                    
                    st.download_button(
                        label="Descargar Excel",
                        data=buffer.getvalue(),
                        file_name=f"clasificacion_filtrada_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except ImportError:
                    st.error("⚠️ Error al exportar. Falta la librería 'openpyxl'.")
        else:
            st.info("ℹ️ No hay detalle para los grados seleccionados")
    else:
        st.info("👆 Selecciona los filtros y haz clic en **Consultar Clasificación** para ver los datos")

        

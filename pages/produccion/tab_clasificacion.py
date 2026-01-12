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
        
        # Filtro de orden de fabricación y Planta (nueva fila)
        col_fil_3_1, col_fil_3_2 = st.columns([2, 1])
        
        with col_fil_3_1:
            orden_fabricacion_input = st.text_input(
                "🔍 Filtrar por Orden de Fabricación (opcional)",
                placeholder="Ej: MO/00123",
                key="orden_fabricacion_clasificacion",
                help="Ingresa el nombre o parte del nombre de la orden de fabricación o transferencia"
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
    
    # === CONSULTA Y PRESENTACIÓN ===
    if consultar or st.session_state.get("clasificacion_data"):
        if consultar:
            # Llamar al endpoint
            fecha_inicio_str = fecha_inicio_clas.strftime("%Y-%m-%d")
            fecha_fin_str = fecha_fin_clas.strftime("%Y-%m-%d")
            
            # Preparar parámetros opcionales
            tipo_fruta_param = None if tipo_fruta_seleccionado == "Todas" else tipo_fruta_seleccionado
            tipo_manejo_param = None if tipo_manejo_seleccionado == "Todos" else tipo_manejo_seleccionado
            orden_fab_param = None if not orden_fabricacion_input.strip() else orden_fabricacion_input.strip()
            
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
                    
                    if orden_fab_param:
                        params["orden_fabricacion"] = orden_fab_param
                    
                    
                    response = requests.get(
                        f"{API_URL}/api/v1/produccion/clasificacion",
                        params=params,
                        timeout=120
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.clasificacion_data = data
                        st.success(f"✅ Datos cargados correctamente ({tipo_operacion_seleccionado})")
                    else:
                        st.error(f"❌ Error al obtener datos: {response.status_code} - {response.text}")
                        return
                        
                except Exception as e:
                    st.error(f"❌ Error en la consulta: {str(e)}")
                    return
        
        # Mostrar datos
        data = st.session_state.clasificacion_data
        
        # Mapeo de grados e información visual
        GRADOS_INFO = {
            '1': {'nombre': 'IQF AA', 'emoji': '⭐', 'color': '#FFD700'},
            '2': {'nombre': 'IQF A', 'emoji': '🔵', 'color': '#4472C4'},
            '3': {'nombre': 'PSP', 'emoji': '🟣', 'color': '#9966FF'},
            '4': {'nombre': 'W&B', 'emoji': '🟤', 'color': '#8B4513'},
            '5': {'nombre': 'Block', 'emoji': '🟦', 'color': '#1E90FF'},
            '6': {'nombre': 'Jugo', 'emoji': '🟠', 'color': '#FF8C00'},
            '7': {'nombre': 'IQF Retail', 'emoji': '🟢', 'color': '#70AD47'}
        }
        
        # === GRÁFICO DE BARRAS INTERACTIVO (Control Principal) ===
        st.markdown("---")
        st.markdown("#### 📈 Distribución por Grado")
        st.info("💡 **Gráfico Interactivo:** Haz clic en los cuadros de la leyenda para filtrar los KPIs y la tabla detallada.")
        
        # Preparar data para el gráfico
        base_data_list = []
        for grado_num, info in GRADOS_INFO.items():
            kg = data.get('grados', {}).get(grado_num, 0)
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
        grados_raw = data.get('grados', {})
        grados_mostrar = {k: v for k, v in grados_raw.items() if k in active_grades_codes}
        detalle_raw = data.get('detalle', [])
        detalle_mostrar = [item for item in detalle_raw if item.get('grado') in active_grades_names]
        total_kg_filtrado = sum(grados_mostrar.values())
        
        # === KPIs ===
        st.markdown("---")
        st.markdown(f"#### 📊 Totales Filtrados ({len(active_grades_names)} grados)")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(f"{GRADOS_INFO['1']['emoji']} {GRADOS_INFO['1']['nombre']}", f"{fmt_numero(grados_mostrar.get('1', 0))} kg")
        with col2:
            st.metric(f"{GRADOS_INFO['2']['emoji']} {GRADOS_INFO['2']['nombre']}", f"{fmt_numero(grados_mostrar.get('2', 0))} kg")
        with col3:
            st.metric(f"{GRADOS_INFO['3']['emoji']} {GRADOS_INFO['3']['nombre']}", f"{fmt_numero(grados_mostrar.get('3', 0))} kg")
        with col4:
            st.metric(f"{GRADOS_INFO['4']['emoji']} {GRADOS_INFO['4']['nombre']}", f"{fmt_numero(grados_mostrar.get('4', 0))} kg")
            
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric(f"{GRADOS_INFO['5']['emoji']} {GRADOS_INFO['5']['nombre']}", f"{fmt_numero(grados_mostrar.get('5', 0))} kg")
        with col6:
            st.metric(f"{GRADOS_INFO['6']['emoji']} {GRADOS_INFO['6']['nombre']}", f"{fmt_numero(grados_mostrar.get('6', 0))} kg")
        with col7:
            st.metric(f"{GRADOS_INFO['7']['emoji']} {GRADOS_INFO['7']['nombre']}", f"{fmt_numero(grados_mostrar.get('7', 0))} kg")
        with col8:
            st.metric("📦 TOTAL SELECCIONADO", f"{fmt_numero(total_kg_filtrado)} kg")

        # Porcentajes de participación
        st.markdown("##### 📊 Participación en Selección")
        if total_kg_filtrado > 0:
            cols_pct = st.columns(len(active_grades_names))
            # Ordenar para que coincidan con los nombres seleccionados
            selected_data_sorted = df_chart[df_chart['Grado'].isin(active_grades_names)]
            for idx, (_, row) in enumerate(selected_data_sorted.iterrows()):
                with cols_pct[idx % len(active_grades_names)]:
                    pct = (row['Kilogramos'] / total_kg_filtrado * 100)
                    st.info(f"**{row['Grado']}**\n\n{pct:.1f}%")
        
        # === TABLA DETALLADA ===
        if detalle_mostrar:
            st.markdown("---")
            st.markdown(f"#### 📋 Detalle de Pallets ({len(detalle_mostrar)} registros)")
            
            # Convertir a DataFrame
            df_detalle = pd.DataFrame(detalle_mostrar)
            
            # Formatear columnas
            df_detalle['kg'] = df_detalle['kg'].apply(lambda x: f"{x:,.2f}")
            df_detalle['fecha'] = pd.to_datetime(df_detalle['fecha']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Renombrar columnas para display
            df_display = df_detalle[[
                'pallet', 'producto', 'codigo_producto', 'grado', 'kg', 'orden_fabricacion', 'planta', 'fecha'
            ]].copy()
            
            df_display.columns = [
                'Pallet', 'Producto', 'Código', 'Grado', 'Kilogramos', 'Orden Fabricación', 'Planta', 'Fecha'
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

        

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
    
    st.markdown("### 📦 Clasificación de Pallets - IQF A & RETAIL")
    st.caption("Clasifica pallets según observaciones de proceso")
    
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

        # Mapeo de grados para el filtro
        GRADOS_OPCIONES = {
            'IQF AA': '1',
            'IQF A': '2',
            'PSP': '3',
            'W&B': '4',
            'Block': '5',
            'Jugo': '6',
            'IQF Retail': '7'
        }
        
        grados_seleccionados = st.multiselect(
            "🏷️ Filtrar por Grados",
            options=list(GRADOS_OPCIONES.keys()),
            default=list(GRADOS_OPCIONES.keys()),
            key="grados_filtro_clasificacion",
            help="Selecciona los grados que deseas visualizar en los resultados"
        )
        
        # Convertir nombres seleccionados a sus códigos numéricos
        codigos_grados_seleccionados = [GRADOS_OPCIONES[name] for name in grados_seleccionados]
        
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
        
        # Mapeo de grados
        GRADOS_INFO = {
            '1': {'nombre': 'IQF AA', 'emoji': '⭐', 'color': '#FFD700'},
            '2': {'nombre': 'IQF A', 'emoji': '🔵', 'color': '#4472C4'},
            '3': {'nombre': 'PSP', 'emoji': '🟣', 'color': '#9966FF'},
            '4': {'nombre': 'W&B', 'emoji': '🟤', 'color': '#8B4513'},
            '5': {'nombre': 'Block', 'emoji': '🟦', 'color': '#1E90FF'},
            '6': {'nombre': 'Jugo', 'emoji': '🟠', 'color': '#FF8C00'},
            '7': {'nombre': 'IQF Retail', 'emoji': '🟢', 'color': '#70AD47'}
        }

        # --- FILTRADO DINÁMICO EN FRONTEND ---
        # 1. Filtrar el diccionario de grados (KPIs)
        grados_raw = data.get('grados', {})
        grados_mostrar = {k: v for k, v in grados_raw.items() if k in codigos_grados_seleccionados}
        
        # 2. Filtrar la lista de detalle (Tabla y Gráfico)
        detalle_raw = data.get('detalle', [])
        detalle_mostrar = [item for item in detalle_raw if item.get('grado') in grados_seleccionados]
        
        # 3. Recalcular total basado en la selección
        total_kg_mostrar = sum(grados_mostrar.values())
        
        # === KPIs ===
        st.markdown("---")
        st.markdown(f"#### 📊 Totales Filtrados ({len(grados_seleccionados)} grados seleccionados)")
        
        # Primera fila: Grados 1-4
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label=f"{GRADOS_INFO['1']['emoji']} {GRADOS_INFO['1']['nombre']}",
                value=f"{fmt_numero(grados_mostrar.get('1', 0))} kg"
            )
        
        with col2:
            st.metric(
                label=f"{GRADOS_INFO['2']['emoji']} {GRADOS_INFO['2']['nombre']}",
                value=f"{fmt_numero(grados_mostrar.get('2', 0))} kg"
            )
        
        with col3:
            st.metric(
                label=f"{GRADOS_INFO['3']['emoji']} {GRADOS_INFO['3']['nombre']}",
                value=f"{fmt_numero(grados_mostrar.get('3', 0))} kg"
            )
        
        with col4:
            st.metric(
                label=f"{GRADOS_INFO['4']['emoji']} {GRADOS_INFO['4']['nombre']}",
                value=f"{fmt_numero(grados_mostrar.get('4', 0))} kg"
            )
        
        # Segunda fila: Grados 5-7 + Total
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.metric(
                label=f"{GRADOS_INFO['5']['emoji']} {GRADOS_INFO['5']['nombre']}",
                value=f"{fmt_numero(grados_mostrar.get('5', 0))} kg"
            )
        
        with col6:
            st.metric(
                label=f"{GRADOS_INFO['6']['emoji']} {GRADOS_INFO['6']['nombre']}",
                value=f"{fmt_numero(grados_mostrar.get('6', 0))} kg"
            )
        
        with col7:
            st.metric(
                label=f"{GRADOS_INFO['7']['emoji']} {GRADOS_INFO['7']['nombre']}",
                value=f"{fmt_numero(grados_mostrar.get('7', 0))} kg"
            )
        
        with col8:
            st.metric(
                label="📦 TOTAL FILTRADO",
                value=f"{fmt_numero(total_kg_mostrar)} kg"
            )
        
        # === GRÁFICO DE BARRAS ===
        st.markdown("---")
        st.markdown("#### 📈 Distribución por Grado (Filtrado)")
        
        if total_kg_mostrar > 0:
            # Crear DataFrame para el gráfico con datos filtrados
            chart_data_list = []
            for grado_num, info in GRADOS_INFO.items():
                if grado_num in codigos_grados_seleccionados:
                    kg = grados_mostrar.get(grado_num, 0)
                    if kg > 0:
                        chart_data_list.append({
                            'Grado': info['nombre'],
                            'Kilogramos': kg,
                            'Color': info['color']
                        })
            
            if chart_data_list:
                chart_data = pd.DataFrame(chart_data_list)
                
                # Crear gráfico con Altair mejorado
                chart = alt.Chart(chart_data).mark_bar(
                    cornerRadiusTopLeft=8,
                    cornerRadiusTopRight=8
                ).encode(
                    x=alt.X('Grado:N', 
                           title='Grado de Producto',
                           axis=alt.Axis(labelAngle=-45, labelFontSize=12, titleFontSize=14)),
                    y=alt.Y('Kilogramos:Q', 
                           title='Kilogramos (kg)',
                           axis=alt.Axis(labelFontSize=12, titleFontSize=14)),
                    color=alt.Color('Grado:N',
                                   scale=alt.Scale(
                                       domain=[info['nombre'] for info in GRADOS_INFO.values()],
                                       range=[info['color'] for info in GRADOS_INFO.values()]
                                   ),
                                   legend=alt.Legend(
                                       title='Grado',
                                       orient='right',
                                       titleFontSize=13,
                                       labelFontSize=12
                                   )),
                    tooltip=[
                        alt.Tooltip('Grado:N', title='Grado'),
                        alt.Tooltip('Kilogramos:Q', title='Kilogramos', format=',.2f')
                    ]
                ).properties(
                    height=450
                ).configure_axis(
                    grid=True,
                    gridOpacity=0.3
                ).configure_view(
                    strokeWidth=0
                )
                
                st.altair_chart(chart, use_container_width=True)
                
                # Porcentajes en columnas
                st.markdown("##### 📊 Detalle de Participación (en lo seleccionado)")
                cols = st.columns(len(chart_data_list))
                
                for idx, (_, row) in enumerate(chart_data.iterrows()):
                    with cols[idx]:
                        pct = (row['Kilogramos'] / total_kg_mostrar * 100) if total_kg_mostrar > 0 else 0
                        st.info(f"**{row['Grado']}**\n\n{pct:.1f}% ({row['Kilogramos']:,.2f} kg)")
            else:
                st.info("ℹ️ No hay datos para los grados seleccionados")
        else:
            st.info("ℹ️ El total para los grados seleccionados es 0.00 kg")
        
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

        

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
        
        # Filtro de orden de fabricación (nueva fila)
        orden_fabricacion_input = st.text_input(
            "🔍 Filtrar por Orden de Fabricación (opcional)",
            placeholder="Ej: MO/00123",
            key="orden_fabricacion_clasificacion",
            help="Ingresa el nombre o parte del nombre de la orden de fabricación"
        )
        
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
                        "fecha_fin": fecha_fin_str
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
                        st.success("✅ Datos cargados correctamente")
                    else:
                        st.error(f"❌ Error al obtener datos: {response.status_code} - {response.text}")
                        return
                        
                except Exception as e:
                    st.error(f"❌ Error en la consulta: {str(e)}")
                    return
        
        # Mostrar datos
        data = st.session_state.clasificacion_data
        
        # === KPIs ===
        st.markdown("---")
        st.markdown("#### 📊 Totales por Clasificación")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="🔵 IQF A",
                value=f"{fmt_numero(data['iqf_a_kg'])} kg",
                delta=None
            )
        
        with col2:
            st.metric(
                label="🟢 RETAIL",
                value=f"{fmt_numero(data['retail_kg'])} kg",
                delta=None
            )
        
        with col3:
            st.metric(
                label="📦 TOTAL",
                value=f"{fmt_numero(data['total_kg'])} kg",
                delta=None
            )
        
        # === GRÁFICO DE BARRAS ===
        st.markdown("---")
        st.markdown("#### 📈 Distribución por Clasificación")
        
        if data['total_kg'] > 0:
            # Crear DataFrame para el gráfico
            chart_data = pd.DataFrame({
                'Clasificación': ['IQF A', 'RETAIL'],
                'Kilogramos': [data['iqf_a_kg'], data['retail_kg']]
            })
            
            # Crear gráfico con Altair
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Clasificación:N', title='Clasificación'),
                y=alt.Y('Kilogramos:Q', title='Kilogramos'),
                color=alt.Color('Clasificación:N', 
                               scale=alt.Scale(domain=['IQF A', 'RETAIL'], 
                                              range=['#4472C4', '#70AD47']),
                               legend=None),
                tooltip=[
                    alt.Tooltip('Clasificación:N', title='Clasificación'),
                    alt.Tooltip('Kilogramos:Q', title='Kilogramos', format=',.2f')
                ]
            ).properties(
                height=400
            )
            
            st.altair_chart(chart, use_container_width=True)
            
            # Porcentajes
            pct_iqf_a = (data['iqf_a_kg'] / data['total_kg'] * 100) if data['total_kg'] > 0 else 0
            pct_retail = (data['retail_kg'] / data['total_kg'] * 100) if data['total_kg'] > 0 else 0
            
            col_pct1, col_pct2 = st.columns(2)
            with col_pct1:
                st.info(f"**IQF A:** {pct_iqf_a:.1f}% del total")
            with col_pct2:
                st.success(f"**RETAIL:** {pct_retail:.1f}% del total")
        else:
            st.info("ℹ️ No hay datos para mostrar con los filtros seleccionados")
        
        # === TABLA DETALLADA ===
        if data['detalle']:
            st.markdown("---")
            st.markdown("#### 📋 Detalle de Pallets")
            
            # Convertir a DataFrame
            df_detalle = pd.DataFrame(data['detalle'])
            
            # Formatear columnas
            df_detalle['kg'] = df_detalle['kg'].apply(lambda x: f"{x:,.2f}")
            df_detalle['fecha'] = pd.to_datetime(df_detalle['fecha']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Renombrar columnas para display
            df_display = df_detalle[[
                'pallet', 'clasificacion', 'kg', 'producto', 'lote', 'fecha'
            ]].copy()
            
            df_display.columns = [
                'Pallet', 'Clasificación', 'Kilogramos', 'Producto', 'Lote', 'Fecha'
            ]
            
            # Mostrar tabla con filtros
            st.dataframe(
                df_display,
                use_container_width=True,
                height=400,
                hide_index=True
            )
            
            # Exportar a Excel
            if st.button("📥 Exportar a Excel", key="export_clasificacion"):
                try:
                    import io
                    buffer = io.BytesIO()
                    
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df_display.to_excel(writer, index=False, sheet_name='Clasificación')
                    
                    st.download_button(
                        label="Descargar Excel",
                        data=buffer.getvalue(),
                        file_name=f"clasificacion_pallets_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except ImportError:
                    st.warning("⚠️ Se requiere 'openpyxl' para exportar a Excel. Instala con: pip install openpyxl")
        else:
            st.info("ℹ️ No hay pallets clasificados en el período seleccionado")
    else:
        st.info("👆 Selecciona los filtros y haz clic en **Consultar Clasificación** para ver los datos")

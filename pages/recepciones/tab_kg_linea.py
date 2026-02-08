"""
Tab KG por Línea: Muestra la cantidad de KG/Hora procesados por cada sala/línea de proceso.

Este tab ayuda a monitorear la productividad de cada línea de proceso,
mostrando cuántos kilos se procesan por hora en cada sala.
"""
import streamlit as st
import httpx
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# URL del API
API_URL = "http://rio-api-dev:8000"


def fetch_kg_por_linea(username: str, password: str, fecha_inicio: str, 
                       fecha_fin: str, planta: str = None) -> Dict[str, Any]:
    """Obtiene los datos de KG/Hora por línea desde el backend."""
    params = {
        "username": username,
        "password": password,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin
    }
    if planta and planta != "Todas":
        params["planta"] = planta
    
    response = httpx.get(f"{API_URL}/api/v1/produccion/kg-por-linea",
                         params=params, timeout=60.0)
    response.raise_for_status()
    return response.json()


def render_kpi_card(titulo: str, valor: str, icono: str, color: str):
    """Renderiza una tarjeta KPI con estilo."""
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {color}22 0%, {color}11 100%);
        border-left: 4px solid {color};
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    ">
        <div style="font-size: 2rem;">{icono}</div>
        <div style="font-size: 0.9rem; color: #888; margin-top: 5px;">{titulo}</div>
        <div style="font-size: 1.8rem; font-weight: bold; color: {color};">{valor}</div>
    </div>
    """, unsafe_allow_html=True)


def render_grafico_kg_hora(datos_lineas: List[Dict]) -> None:
    """Renderiza gráfico de barras de KG/Hora por línea."""
    from streamlit_echarts import st_echarts
    
    if not datos_lineas:
        st.info("No hay datos para mostrar")
        return
    
    # Ordenar por KG/Hora descendente
    datos_ordenados = sorted(datos_lineas, key=lambda x: x.get('kg_hora', 0), reverse=True)
    
    lineas = [d.get('sala', 'Sin Sala') for d in datos_ordenados]
    kg_hora = [round(d.get('kg_hora', 0), 1) for d in datos_ordenados]
    
    # Colores vibrantes para cada barra
    colores = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
               '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
    
    options = {
        "title": {
            "text": "⚡ Productividad por Línea",
            "subtext": "Kilogramos procesados por hora en cada sala",
            "left": "center",
            "textStyle": {"color": "#fff", "fontSize": 18},
            "subtextStyle": {"color": "#aaa", "fontSize": 12}
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{b}<br/>KG/Hora: <b>{c}</b>"
        },
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "15%",
            "top": "20%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": lineas,
            "axisLabel": {
                "rotate": 45,
                "color": "#ccc",
                "fontSize": 11
            },
            "axisLine": {"lineStyle": {"color": "#555"}}
        },
        "yAxis": {
            "type": "value",
            "name": "KG/Hora",
            "nameTextStyle": {"color": "#aaa"},
            "axisLabel": {"color": "#ccc"},
            "splitLine": {"lineStyle": {"color": "#333"}}
        },
        "series": [{
            "name": "KG/Hora",
            "type": "bar",
            "data": kg_hora,
            "itemStyle": {
                "color": {
                    "type": "linear",
                    "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": "#4ECDC4"},
                        {"offset": 1, "color": "#44A08D"}
                    ]
                },
                "borderRadius": [5, 5, 0, 0]
            },
            "label": {
                "show": True,
                "position": "top",
                "color": "#4ECDC4",
                "fontWeight": "bold",
                "formatter": "{c}"
            },
            "emphasis": {
                "itemStyle": {
                    "color": "#5DDFCE"
                }
            }
        }]
    }
    
    st_echarts(options=options, height="400px")


def render_grafico_total_kg(datos_lineas: List[Dict]) -> None:
    """Renderiza gráfico de barras del total de KG por línea."""
    from streamlit_echarts import st_echarts
    
    if not datos_lineas:
        return
    
    # Ordenar por total KG descendente
    datos_ordenados = sorted(datos_lineas, key=lambda x: x.get('total_kg', 0), reverse=True)
    
    lineas = [d.get('sala', 'Sin Sala') for d in datos_ordenados]
    total_kg = [round(d.get('total_kg', 0), 0) for d in datos_ordenados]
    
    options = {
        "title": {
            "text": "📦 Total KG Procesados por Línea",
            "subtext": "Kilogramos totales en el período seleccionado",
            "left": "center",
            "textStyle": {"color": "#fff", "fontSize": 18},
            "subtextStyle": {"color": "#aaa", "fontSize": 12}
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{b}<br/>Total: <b>{c:,.0f}</b> KG"
        },
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "15%",
            "top": "20%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": lineas,
            "axisLabel": {
                "rotate": 45,
                "color": "#ccc",
                "fontSize": 11
            },
            "axisLine": {"lineStyle": {"color": "#555"}}
        },
        "yAxis": {
            "type": "value",
            "name": "KG Totales",
            "nameTextStyle": {"color": "#aaa"},
            "axisLabel": {
                "color": "#ccc",
                "formatter": "{value}"
            },
            "splitLine": {"lineStyle": {"color": "#333"}}
        },
        "series": [{
            "name": "Total KG",
            "type": "bar",
            "data": total_kg,
            "itemStyle": {
                "color": {
                    "type": "linear",
                    "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": "#FF6B6B"},
                        {"offset": 1, "color": "#C44569"}
                    ]
                },
                "borderRadius": [5, 5, 0, 0]
            },
            "label": {
                "show": True,
                "position": "top",
                "color": "#FF6B6B",
                "fontWeight": "bold",
                "formatter": "{c}"
            }
        }]
    }
    
    st_echarts(options=options, height="400px")


def render_tabla_detalle(datos_lineas: List[Dict]) -> None:
    """Renderiza tabla detallada con los datos por línea."""
    if not datos_lineas:
        st.info("No hay datos para mostrar en la tabla")
        return
    
    # Crear DataFrame
    df = pd.DataFrame(datos_lineas)
    
    # Renombrar columnas para mejor presentación
    columnas_renombre = {
        'sala': '🏭 Línea/Sala',
        'total_kg': '📦 Total KG',
        'horas_totales': '⏱️ Horas',
        'kg_hora': '⚡ KG/Hora',
        'procesos': '🔄 Procesos',
        'promedio_kg_proceso': '📊 KG/Proceso'
    }
    
    # Seleccionar y renombrar columnas que existan
    columnas_mostrar = [c for c in columnas_renombre.keys() if c in df.columns]
    df_mostrar = df[columnas_mostrar].copy()
    df_mostrar = df_mostrar.rename(columns=columnas_renombre)
    
    # Formatear números
    if '📦 Total KG' in df_mostrar.columns:
        df_mostrar['📦 Total KG'] = df_mostrar['📦 Total KG'].apply(lambda x: f"{x:,.0f}")
    if '⏱️ Horas' in df_mostrar.columns:
        df_mostrar['⏱️ Horas'] = df_mostrar['⏱️ Horas'].apply(lambda x: f"{x:,.1f}")
    if '⚡ KG/Hora' in df_mostrar.columns:
        df_mostrar['⚡ KG/Hora'] = df_mostrar['⚡ KG/Hora'].apply(lambda x: f"{x:,.1f}")
    if '📊 KG/Proceso' in df_mostrar.columns:
        df_mostrar['📊 KG/Proceso'] = df_mostrar['📊 KG/Proceso'].apply(lambda x: f"{x:,.0f}")
    
    # Ordenar por KG/Hora descendente
    df_mostrar = df_mostrar.sort_values('⚡ KG/Hora', ascending=False, key=lambda x: x.str.replace(',', '').astype(float))
    
    st.dataframe(
        df_mostrar,
        use_container_width=True,
        hide_index=True,
        height=400
    )


def render(username: str, password: str):
    """Renderiza el tab de KG por Línea."""
    
    st.markdown("### ⚡ KG por Línea de Proceso")
    st.markdown("""
    <div style="background: #1a1a2e; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
        <p style="color: #ccc; margin: 0;">
            📊 <b>¿Qué muestra este reporte?</b><br>
            Visualiza la <b>productividad</b> de cada línea/sala de proceso, midiendo cuántos 
            <b>kilogramos por hora</b> se procesan. Útil para identificar líneas más eficientes 
            y optimizar la distribución de trabajo.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # === FILTROS ===
    st.markdown("#### 🔍 Filtros")
    
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        fecha_inicio = st.date_input(
            "📅 Desde",
            value=datetime.now().date() - timedelta(days=7),
            key="kg_linea_fecha_inicio"
        )
    
    with col2:
        fecha_fin = st.date_input(
            "📅 Hasta",
            value=datetime.now().date(),
            key="kg_linea_fecha_fin"
        )
    
    with col3:
        planta = st.selectbox(
            "🏭 Planta",
            options=["Todas", "RIO FUTURO", "VILKUN"],
            key="kg_linea_planta"
        )
    
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        btn_buscar = st.button("🔍 Buscar", type="primary", key="kg_linea_buscar")
    
    st.markdown("---")
    
    # === CARGAR DATOS ===
    if btn_buscar or st.session_state.get("kg_linea_data_loaded", False):
        if btn_buscar:
            try:
                with st.spinner("Cargando datos de productividad por línea..."):
                    datos = fetch_kg_por_linea(
                        username, password,
                        fecha_inicio.isoformat(),
                        fecha_fin.isoformat(),
                        planta
                    )
                    st.session_state["kg_linea_data"] = datos
                    st.session_state["kg_linea_data_loaded"] = True
            except Exception as e:
                st.error(f"Error al cargar datos: {str(e)}")
                return
        
        datos = st.session_state.get("kg_linea_data", {})
        
        if not datos:
            st.warning("No se encontraron datos para el período seleccionado")
            return
        
        lineas = datos.get("lineas", [])
        resumen = datos.get("resumen", {})
        
        # === KPIs RESUMEN ===
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            render_kpi_card(
                "TOTAL KG PROCESADOS",
                f"{resumen.get('total_kg', 0):,.0f}",
                "📦",
                "#4ECDC4"
            )
        
        with col2:
            render_kpi_card(
                "PROMEDIO KG/HORA",
                f"{resumen.get('promedio_kg_hora', 0):,.1f}",
                "⚡",
                "#FF6B6B"
            )
        
        with col3:
            render_kpi_card(
                "TOTAL HORAS",
                f"{resumen.get('total_horas', 0):,.1f}",
                "⏱️",
                "#45B7D1"
            )
        
        with col4:
            render_kpi_card(
                "LÍNEAS ACTIVAS",
                f"{resumen.get('lineas_activas', 0)}",
                "🏭",
                "#96CEB4"
            )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # === GRÁFICOS ===
        st.markdown("### 📊 Análisis Visual")
        
        # Gráfico de KG/Hora
        render_grafico_kg_hora(lineas)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Gráfico de Total KG
        render_grafico_total_kg(lineas)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # === TABLA DETALLE ===
        st.markdown("### 📋 Detalle por Línea")
        render_tabla_detalle(lineas)
    
    else:
        st.info("👆 Selecciona el rango de fechas y presiona **'🔍 Buscar'** para ver los datos de productividad")

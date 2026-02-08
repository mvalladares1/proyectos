"""
Tab KG por Línea: Productividad por sala de proceso.
Muestra KG/Hora y KG totales por cada línea.
"""
import streamlit as st
import httpx
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
from streamlit_echarts import st_echarts

API_URL = "http://rio-api-dev:8000"


def fetch_datos_salas(username: str, password: str, fecha_inicio: str, 
                      fecha_fin: str) -> Dict[str, Any]:
    """Obtiene datos de productividad por sala."""
    params = {
        "username": username,
        "password": password,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "solo_terminadas": True
    }
    
    response = httpx.get(f"{API_URL}/api/v1/rendimiento/dashboard",
                         params=params, timeout=120.0)
    response.raise_for_status()
    return response.json()


def render_grafico_kg_hora(datos_salas: List[Dict]) -> None:
    """Gráfico de barras horizontales de KG/Hora por sala."""
    if not datos_salas:
        st.info("No hay datos para mostrar")
        return
    
    # Filtrar y ordenar por KG/Hora
    datos_validos = [d for d in datos_salas if d.get('kg_por_hora', 0) > 0]
    datos_ordenados = sorted(datos_validos, key=lambda x: x.get('kg_por_hora', 0), reverse=False)[-12:]
    
    if not datos_ordenados:
        st.info("No hay salas con producción en el período")
        return
    
    salas = [d.get('sala', 'Sin Sala')[:25] for d in datos_ordenados]
    kg_hora = [round(d.get('kg_por_hora', 0), 1) for d in datos_ordenados]
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{b}<br/>⚡ KG/Hora: <b>{c}</b>"
        },
        "grid": {
            "left": "25%",
            "right": "10%",
            "bottom": "5%",
            "top": "5%",
            "containLabel": False
        },
        "xAxis": {
            "type": "value",
            "name": "KG/Hora",
            "nameLocation": "middle",
            "nameGap": 30,
            "nameTextStyle": {"color": "#aaa", "fontSize": 12},
            "axisLabel": {"color": "#ccc"},
            "splitLine": {"lineStyle": {"color": "#333"}}
        },
        "yAxis": {
            "type": "category",
            "data": salas,
            "axisLabel": {"color": "#ddd", "fontSize": 11},
            "axisLine": {"lineStyle": {"color": "#555"}}
        },
        "series": [{
            "name": "KG/Hora",
            "type": "bar",
            "data": kg_hora,
            "itemStyle": {
                "color": {
                    "type": "linear",
                    "x": 0, "y": 0, "x2": 1, "y2": 0,
                    "colorStops": [
                        {"offset": 0, "color": "#0099CC"},
                        {"offset": 1, "color": "#00D9FF"}
                    ]
                },
                "borderRadius": [0, 5, 5, 0]
            },
            "label": {
                "show": True,
                "position": "right",
                "color": "#00D9FF",
                "fontWeight": "bold",
                "fontSize": 12
            }
        }]
    }
    
    st_echarts(options=options, height="400px")


def render_tabla(datos_salas: List[Dict]) -> None:
    """Tabla simple con datos por sala."""
    if not datos_salas:
        return
    
    datos_validos = [d for d in datos_salas if d.get('kg_pt', 0) > 0 or d.get('num_mos', 0) > 0]
    
    if not datos_validos:
        st.info("No hay salas con producción")
        return
    
    rows = []
    for d in datos_validos:
        rows.append({
            'Sala': d.get('sala', 'N/A'),
            'KG Producidos': f"{d.get('kg_pt', 0):,.0f}",
            'KG/Hora': f"{d.get('kg_por_hora', 0):,.1f}",
            'Rendimiento %': f"{d.get('rendimiento', 0):.1f}%",
            'HH Totales': f"{d.get('hh_total', 0):,.0f}",
            'Procesos': d.get('num_mos', 0)
        })
    
    df = pd.DataFrame(rows)
    df = df.sort_values('KG/Hora', ascending=False, 
                        key=lambda x: x.str.replace(',', '').astype(float))
    
    st.dataframe(df, use_container_width=True, hide_index=True, height=400)


def render(username: str, password: str):
    """Renderiza el tab de KG por Línea."""
    
    st.markdown("### ⚡ KG por Línea de Proceso")
    st.caption("Productividad de cada sala: KG procesados por hora")
    
    # Filtros
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        fecha_inicio = st.date_input(
            "Desde",
            value=datetime.now().date() - timedelta(days=7),
            key="kg_linea_prod_fecha_inicio"
        )
    
    with col2:
        fecha_fin = st.date_input(
            "Hasta",
            value=datetime.now().date(),
            key="kg_linea_prod_fecha_fin"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        btn_buscar = st.button("🔍 Buscar", type="primary", key="kg_linea_prod_buscar", 
                               use_container_width=True)
    
    st.markdown("---")
    
    # Cargar datos
    if btn_buscar or st.session_state.get("kg_linea_prod_data_loaded", False):
        if btn_buscar:
            try:
                with st.spinner("Cargando datos..."):
                    datos = fetch_datos_salas(
                        username, password,
                        fecha_inicio.isoformat(),
                        fecha_fin.isoformat()
                    )
                    st.session_state["kg_linea_prod_data"] = datos
                    st.session_state["kg_linea_prod_data_loaded"] = True
            except Exception as e:
                st.error(f"Error: {str(e)}")
                return
        
        datos = st.session_state.get("kg_linea_prod_data", {})
        
        if not datos:
            st.warning("No se encontraron datos")
            return
        
        salas = datos.get("salas", [])
        
        if not salas:
            st.warning("No hay datos de salas para el período")
            return
        
        # KPIs simples
        total_kg = sum(s.get('kg_pt', 0) for s in salas)
        salas_activas = len([s for s in salas if s.get('kg_pt', 0) > 0])
        kg_hora_list = [s.get('kg_por_hora', 0) for s in salas if s.get('kg_por_hora', 0) > 0]
        prom_kg_hora = sum(kg_hora_list) / len(kg_hora_list) if kg_hora_list else 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📦 Total KG Producidos", f"{total_kg:,.0f}")
        col2.metric("⚡ Promedio KG/Hora", f"{prom_kg_hora:,.1f}")
        col3.metric("🏭 Salas Activas", f"{salas_activas}")
        
        st.markdown("---")
        
        # Gráfico
        st.markdown("#### KG/Hora por Sala")
        render_grafico_kg_hora(salas)
        
        st.markdown("---")
        
        # Tabla
        st.markdown("#### Detalle por Sala")
        render_tabla(salas)
    
    else:
        st.info("👆 Selecciona fechas y presiona **Buscar**")

"""
Tab KG por Línea: Muestra la cantidad de KG/Hora procesados por cada sala/línea de proceso.

Este tab ayuda a monitorear la productividad de cada línea de proceso,
mostrando cuántos kilos se procesan por hora en cada sala.

FUENTE DE DATOS: Usa el endpoint /api/v1/rendimiento/dashboard que devuelve
datos de salas con: kg_pt, kg_mp, kg_por_hora, hh_total, num_mos, etc.
"""
import streamlit as st
import httpx
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from streamlit_echarts import st_echarts

# URL del API
API_URL = "http://rio-api-dev:8000"


def fetch_datos_salas(username: str, password: str, fecha_inicio: str, 
                      fecha_fin: str) -> Dict[str, Any]:
    """
    Obtiene los datos de productividad por sala desde el backend.
    Usa el endpoint /rendimiento/dashboard que ya tiene datos de salas.
    """
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


def render_kpi_card(titulo: str, valor: str, icono: str, color: str):
    """Renderiza una tarjeta KPI con estilo moderno."""
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {color}22 0%, {color}11 100%);
        border-left: 4px solid {color};
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        height: 130px;
    ">
        <div style="font-size: 2rem;">{icono}</div>
        <div style="font-size: 0.85rem; color: #888; margin-top: 5px;">{titulo}</div>
        <div style="font-size: 1.6rem; font-weight: bold; color: {color};">{valor}</div>
    </div>
    """, unsafe_allow_html=True)


def render_grafico_kg_hora(datos_salas: List[Dict]) -> None:
    """Renderiza gráfico de barras de KG/Hora por sala."""
    if not datos_salas:
        st.info("No hay datos para mostrar")
        return
    
    # Filtrar salas con datos y ordenar por KG/Hora descendente
    datos_validos = [d for d in datos_salas if d.get('kg_por_hora', 0) > 0]
    datos_ordenados = sorted(datos_validos, key=lambda x: x.get('kg_por_hora', 0), reverse=True)[:15]
    
    if not datos_ordenados:
        st.info("No hay salas con producción en el período seleccionado")
        return
    
    salas = [d.get('sala', 'Sin Sala')[:20] for d in datos_ordenados]  # Limitar largo nombre
    kg_hora = [round(d.get('kg_por_hora', 0), 1) for d in datos_ordenados]
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{b}<br/>KG/Hora: <b>{c}</b>"
        },
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "20%",
            "top": "10%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": salas,
            "axisLabel": {
                "rotate": 45,
                "color": "#ccc",
                "fontSize": 10,
                "interval": 0
            },
            "axisLine": {"lineStyle": {"color": "#555"}}
        },
        "yAxis": {
            "type": "value",
            "name": "KG/Hora",
            "nameTextStyle": {"color": "#aaa", "fontSize": 12},
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
                        {"offset": 0, "color": "#00D9FF"},
                        {"offset": 1, "color": "#0099CC"}
                    ]
                },
                "borderRadius": [5, 5, 0, 0]
            },
            "label": {
                "show": True,
                "position": "top",
                "color": "#00D9FF",
                "fontWeight": "bold",
                "fontSize": 11,
                "formatter": "{c}"
            },
            "emphasis": {
                "itemStyle": {"color": "#33E5FF"}
            }
        }]
    }
    
    st_echarts(options=options, height="380px")


def render_grafico_kg_totales(datos_salas: List[Dict]) -> None:
    """Renderiza gráfico de barras del total de KG PT por sala."""
    if not datos_salas:
        return
    
    # Filtrar y ordenar por KG PT descendente
    datos_validos = [d for d in datos_salas if d.get('kg_pt', 0) > 0]
    datos_ordenados = sorted(datos_validos, key=lambda x: x.get('kg_pt', 0), reverse=True)[:15]
    
    if not datos_ordenados:
        return
    
    salas = [d.get('sala', 'Sin Sala')[:20] for d in datos_ordenados]
    kg_pt = [round(d.get('kg_pt', 0), 0) for d in datos_ordenados]
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{b}<br/>Total KG: <b>{c:,.0f}</b>"
        },
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "20%",
            "top": "10%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": salas,
            "axisLabel": {
                "rotate": 45,
                "color": "#ccc",
                "fontSize": 10,
                "interval": 0
            },
            "axisLine": {"lineStyle": {"color": "#555"}}
        },
        "yAxis": {
            "type": "value",
            "name": "KG Totales",
            "nameTextStyle": {"color": "#aaa", "fontSize": 12},
            "axisLabel": {"color": "#ccc"},
            "splitLine": {"lineStyle": {"color": "#333"}}
        },
        "series": [{
            "name": "KG PT",
            "type": "bar",
            "data": kg_pt,
            "itemStyle": {
                "color": {
                    "type": "linear",
                    "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": "#FF6B9D"},
                        {"offset": 1, "color": "#C44569"}
                    ]
                },
                "borderRadius": [5, 5, 0, 0]
            },
            "label": {
                "show": True,
                "position": "top",
                "color": "#FF6B9D",
                "fontWeight": "bold",
                "fontSize": 10,
                "formatter": "{c}"
            }
        }]
    }
    
    st_echarts(options=options, height="380px")


def render_grafico_rendimiento(datos_salas: List[Dict]) -> None:
    """Renderiza gráfico de barras del % rendimiento por sala."""
    if not datos_salas:
        return
    
    # Filtrar y ordenar por rendimiento descendente
    datos_validos = [d for d in datos_salas if d.get('rendimiento', 0) > 0]
    datos_ordenados = sorted(datos_validos, key=lambda x: x.get('rendimiento', 0), reverse=True)[:15]
    
    if not datos_ordenados:
        return
    
    salas = [d.get('sala', 'Sin Sala')[:20] for d in datos_ordenados]
    rendimiento = [round(d.get('rendimiento', 0), 1) for d in datos_ordenados]
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{b}<br/>Rendimiento: <b>{c}%</b>"
        },
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "20%",
            "top": "10%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": salas,
            "axisLabel": {
                "rotate": 45,
                "color": "#ccc",
                "fontSize": 10,
                "interval": 0
            },
            "axisLine": {"lineStyle": {"color": "#555"}}
        },
        "yAxis": {
            "type": "value",
            "name": "% Rendimiento",
            "nameTextStyle": {"color": "#aaa", "fontSize": 12},
            "axisLabel": {"color": "#ccc"},
            "splitLine": {"lineStyle": {"color": "#333"}},
            "max": 100
        },
        "series": [{
            "name": "Rendimiento",
            "type": "bar",
            "data": rendimiento,
            "itemStyle": {
                "color": {
                    "type": "linear",
                    "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": "#98D8AA"},
                        {"offset": 1, "color": "#4CAF50"}
                    ]
                },
                "borderRadius": [5, 5, 0, 0]
            },
            "label": {
                "show": True,
                "position": "top",
                "color": "#98D8AA",
                "fontWeight": "bold",
                "fontSize": 10,
                "formatter": "{c}%"
            }
        }]
    }
    
    st_echarts(options=options, height="380px")


def render_tabla_detalle(datos_salas: List[Dict]) -> None:
    """Renderiza tabla detallada con los datos por sala."""
    if not datos_salas:
        st.info("No hay datos para mostrar en la tabla")
        return
    
    # Filtrar salas con producción
    datos_validos = [d for d in datos_salas if d.get('kg_pt', 0) > 0 or d.get('num_mos', 0) > 0]
    
    if not datos_validos:
        st.info("No hay salas con producción en el período")
        return
    
    # Crear DataFrame con columnas relevantes
    rows = []
    for d in datos_validos:
        rows.append({
            '🏭 Sala': d.get('sala', 'N/A'),
            '📦 KG PT': f"{d.get('kg_pt', 0):,.0f}",
            '📥 KG MP': f"{d.get('kg_mp', 0):,.0f}",
            '📈 Rendimiento': f"{d.get('rendimiento', 0):.1f}%",
            '⚡ KG/Hora': f"{d.get('kg_por_hora', 0):,.1f}",
            '👥 KG/HH': f"{d.get('kg_por_hh', 0):,.1f}",
            '⏱️ HH Total': f"{d.get('hh_total', 0):,.1f}",
            '👷 Dotación Prom': f"{d.get('dotacion_promedio', 0):.1f}",
            '🔄 Procesos': d.get('num_mos', 0)
        })
    
    df = pd.DataFrame(rows)
    
    # Ordenar por KG PT descendente
    df = df.sort_values('📦 KG PT', ascending=False, key=lambda x: x.str.replace(',', '').astype(float))
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=450
    )


def render(username: str, password: str):
    """Renderiza el tab de KG por Línea."""
    
    st.markdown("### ⚡ KG por Línea de Proceso")
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                padding: 15px; border-radius: 10px; margin-bottom: 20px; 
                border-left: 4px solid #00D9FF;">
        <p style="color: #ccc; margin: 0; font-size: 0.95rem;">
            📊 <b>¿Qué muestra este reporte?</b><br>
            Visualiza la <b style="color: #00D9FF;">productividad</b> de cada línea/sala de proceso, 
            midiendo <b style="color: #FF6B9D;">KG por hora</b>, <b style="color: #98D8AA;">rendimiento</b> 
            (KG PT / KG MP) y volumen total procesado. Ideal para comparar eficiencia entre salas.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # === FILTROS ===
    col1, col2, col3 = st.columns([2, 2, 1])
    
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
        st.markdown("<br>", unsafe_allow_html=True)
        btn_buscar = st.button("🔍 Buscar", type="primary", key="kg_linea_buscar", use_container_width=True)
    
    st.markdown("---")
    
    # === CARGAR DATOS ===
    if btn_buscar or st.session_state.get("kg_linea_data_loaded", False):
        if btn_buscar:
            try:
                with st.spinner("🔄 Cargando datos de productividad por línea..."):
                    datos = fetch_datos_salas(
                        username, password,
                        fecha_inicio.isoformat(),
                        fecha_fin.isoformat()
                    )
                    st.session_state["kg_linea_data"] = datos
                    st.session_state["kg_linea_data_loaded"] = True
            except httpx.HTTPStatusError as e:
                st.error(f"❌ Error HTTP {e.response.status_code}: {e.response.text[:200]}")
                return
            except Exception as e:
                st.error(f"❌ Error al cargar datos: {str(e)}")
                return
        
        datos = st.session_state.get("kg_linea_data", {})
        
        if not datos:
            st.warning("⚠️ No se encontraron datos para el período seleccionado")
            return
        
        salas = datos.get("salas", [])
        overview = datos.get("overview", {})
        
        if not salas:
            st.warning("⚠️ No hay datos de salas para el período seleccionado")
            return
        
        # === KPIs RESUMEN ===
        total_kg_pt = sum(s.get('kg_pt', 0) for s in salas)
        total_kg_mp = sum(s.get('kg_mp', 0) for s in salas)
        total_hh = sum(s.get('hh_total', 0) for s in salas)
        total_procesos = sum(s.get('num_mos', 0) for s in salas)
        salas_activas = len([s for s in salas if s.get('kg_pt', 0) > 0])
        promedio_kg_hora = sum(s.get('kg_por_hora', 0) for s in salas if s.get('kg_por_hora', 0) > 0) / max(salas_activas, 1)
        rendimiento_global = (total_kg_pt / total_kg_mp * 100) if total_kg_mp > 0 else 0
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            render_kpi_card("KG PRODUCIDOS", f"{total_kg_pt:,.0f}", "📦", "#FF6B9D")
        
        with col2:
            render_kpi_card("PROM KG/HORA", f"{promedio_kg_hora:,.1f}", "⚡", "#00D9FF")
        
        with col3:
            render_kpi_card("RENDIMIENTO", f"{rendimiento_global:.1f}%", "📈", "#98D8AA")
        
        with col4:
            render_kpi_card("HORAS-HOMBRE", f"{total_hh:,.0f}", "⏱️", "#FFD93D")
        
        with col5:
            render_kpi_card("SALAS ACTIVAS", f"{salas_activas}", "🏭", "#BB86FC")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # === GRÁFICOS ===
        st.markdown("---")
        st.markdown("### 📊 KG por Hora por Sala")
        st.caption("Kilogramos procesados por hora en cada sala - ordenado de mayor a menor productividad")
        render_grafico_kg_hora(salas)
        
        st.markdown("---")
        st.markdown("### 📦 Total KG Procesados por Sala")
        st.caption("Kilogramos de producto terminado (PT) por sala en el período")
        render_grafico_kg_totales(salas)
        
        st.markdown("---")
        st.markdown("### 📈 Rendimiento por Sala")
        st.caption("Porcentaje de rendimiento (KG PT / KG MP × 100) por sala")
        render_grafico_rendimiento(salas)
        
        st.markdown("---")
        
        # === TABLA DETALLE ===
        st.markdown("### 📋 Tabla Detallada por Sala")
        st.caption("Todos los indicadores de productividad por sala")
        render_tabla_detalle(salas)
    
    else:
        st.info("👆 Selecciona el rango de fechas y presiona **'🔍 Buscar'** para ver los datos de productividad por línea")

"""
Tab Rendimiento en Salas: Productividad por sala de proceso.
Muestra KG/Hora, órdenes, KG totales desglosado por sala con filtros de especie y planta.
"""
import streamlit as st
import httpx
import os
import io
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
from streamlit_echarts import st_echarts, JsCode
from .shared import API_URL

# Ruta al logo
_LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                          'data', 'RFP - LOGO OFICIAL.png')


def fetch_datos_produccion(username: str, password: str, fecha_inicio: str,
                           fecha_fin: str) -> Dict[str, Any]:
    """Obtiene datos de producción."""
    params = {
        "username": username,
        "password": password,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "solo_terminadas": False
    }
    response = httpx.get(f"{API_URL}/api/v1/rendimiento/dashboard",
                         params=params, timeout=120.0)
    response.raise_for_status()
    return response.json()


def parsear_fecha(fecha_str: str) -> Optional[datetime]:
    """Parsea fecha y ajusta de UTC a hora Chile (UTC-3)."""
    if not fecha_str:
        return None
    try:
        s = str(fecha_str).strip()
        dt = None
        if 'T' in s:
            dt = datetime.fromisoformat(s.replace('Z', ''))
        elif len(s) >= 19:
            dt = datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S')
        elif len(s) >= 16:
            dt = datetime.strptime(s[:16], '%Y-%m-%d %H:%M')
        elif len(s) >= 10:
            dt = datetime.strptime(s[:10], '%Y-%m-%d')
        if dt:
            dt = dt - timedelta(hours=3)
        return dt
    except Exception:
        pass
    return None


def detectar_planta(mo: Dict) -> str:
    """Detecta la planta a partir del nombre de la MO o sala."""
    mo_name = (mo.get('mo_name') or mo.get('name') or '').upper()
    sala = (mo.get('sala') or mo.get('sala_original') or '').lower()

    if 'VLK' in mo_name or 'vilkun' in sala:
        return 'Vilkun'
    if 'RF' in mo_name:
        return 'Rio Futuro'
    return 'Rio Futuro'


def emoji_kg_hora(kg: float) -> str:
    if kg >= 2000: return '🟢'
    if kg >= 1500: return '🟡'
    if kg >= 1000: return '🟠'
    return '🔴'


def color_kg_hora(kg: float) -> str:
    if kg >= 2000: return '#4caf50'
    if kg >= 1500: return '#8bc34a'
    if kg >= 1000: return '#ffc107'
    if kg >= 500: return '#ff9800'
    return '#f44336'


def emoji_especie(especie: str) -> str:
    """Retorna el emoji correspondiente a la especie."""
    esp = (especie or '').lower().strip()
    if 'arándano' in esp or 'arandano' in esp:
        return '🫐'
    elif 'frutilla' in esp or 'fresa' in esp:
        return '🍓'
    elif 'frambuesa' in esp:
        return '🍇'
    elif 'mix' in esp:
        return '🫐🍓🍇'
    return '🍓'  # Default


def emoji_estado(state: str) -> str:
    """Retorna el emoji correspondiente al estado de la MO."""
    if state == 'done':
        return '✅'
    elif state == 'progress':
        return '🔄'
    elif state == 'confirmed':
        return '📋'
    elif state == 'cancel':
        return '❌'
    return '📝'


def estado_label(state: str) -> str:
    estados = {
        'draft': 'Borrador',
        'confirmed': 'Confirmada',
        'progress': 'En Proceso',
        'done': 'Terminada',
        'cancel': 'Cancelada',
    }
    return estados.get(state, state)


def _build_chart_kg_dia_sala(mos_list: List[Dict], title: str = "⚖️ KG Producidos por Día / Sala",
                             subtitle: str = "Kilogramos de producto terminado desglosados por día y sala") -> Optional[dict]:
    """Construye opciones ECharts para gráfico KG por día/sala. Retorna None si no hay datos."""
    if not mos_list:
        return None

    colores_paleta = [
        '#2196F3', '#FF9800', '#4CAF50', '#F44336', '#9C27B0',
        '#FFEB3B', '#00BCD4', '#E91E63', '#8BC34A', '#673AB7',
        '#FF5722', '#009688', '#03A9F4', '#FFC107', '#00ACC1',
    ]

    dia_sala_kg: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    dia_horas: Dict[str, float] = defaultdict(float)
    todas_salas_set = set()

    for mo in mos_list:
        sala = mo.get('sala') or 'Sin Sala'
        todas_salas_set.add(sala)
        dt = mo.get('_inicio_dt')
        if not dt:
            continue
        dia_key = dt.strftime('%d/%m')
        kg = mo.get('kg_pt', 0) or 0
        dia_sala_kg[dia_key][sala] += kg
        
        # Acumular horas del día para calcular KG/H
        duracion = mo.get('duracion_horas', 0) or 0
        if duracion > 0:
            dia_horas[dia_key] += duracion

    if not dia_sala_kg:
        return None

    dias_sorted = sorted(dia_sala_kg.keys(), key=lambda d: datetime.strptime(d, '%d/%m'))
    salas_sorted = sorted(todas_salas_set)
    color_map = {sala: colores_paleta[i % len(colores_paleta)] for i, sala in enumerate(salas_sorted)}
    
    # Calcular KG/H por día
    dia_kg_hora = {}
    for dia in dias_sorted:
        total_kg_dia = sum(dia_sala_kg[dia].get(s, 0) for s in salas_sorted)
        horas_dia = dia_horas.get(dia, 0)
        if horas_dia > 0:
            dia_kg_hora[dia] = round(total_kg_dia / horas_dia, 0)
        else:
            dia_kg_hora[dia] = 0

    # Umbral fijo para mostrar labels (mostrar si >= 1000 kg)
    umbral_label = 1000

    # Formatter JS: mostrar valor completo con separador de miles, ocultar si es muy pequeño
    label_formatter = JsCode(
        "function(params){if(params.value<" + str(int(umbral_label)) + ")return '';return params.value.toLocaleString('en-US');}"
    ).js_code

    series = []
    for sala in salas_sorted:
        data_vals = [round(dia_sala_kg[dia].get(sala, 0)) for dia in dias_sorted]
        c = color_map[sala]
        series.append({
            "name": sala,
            "type": "bar",
            "stack": "total",
            "data": data_vals,
            "label": {
                "show": True,
                "position": "inside",
                "formatter": label_formatter,
                "fontSize": 9,
                "fontWeight": "bold",
                "color": "#fff",
                "textShadowColor": "rgba(0,0,0,0.7)",
                "textShadowBlur": 3,
            },
            "itemStyle": {
                "color": {
                    "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": c},
                        {"offset": 1, "color": c + "88"}
                    ]
                },
                "borderRadius": [0, 0, 0, 0]
            },
            "emphasis": {
                "itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.4)"}
            }
        })
    if series:
        series[-1]["itemStyle"]["borderRadius"] = [8, 8, 0, 0]
    
    # Agregar serie adicional para mostrar KG/H arriba de cada columna
    # Calcular los valores totales por día para posicionar los labels
    total_kg_por_dia = [sum(dia_sala_kg[dia].get(s, 0) for s in salas_sorted) for dia in dias_sorted]
    
    # Preparar data para labels de KG/H - usar valores reales en vez de None
    kg_hora_values = [int(dia_kg_hora[dia]) if dia_kg_hora[dia] > 0 else 0 for dia in dias_sorted]
    
    # Crear la serie para mostrar KG/H usando markPoint en la última serie de barras
    if series and kg_hora_values:
        mark_points = []
        for i, val in enumerate(kg_hora_values):
            if val > 0:
                mark_points.append({
                    "xAxis": i,
                    "yAxis": total_kg_por_dia[i],
                    "value": f"{val} kg/h"
                })
        
        if mark_points:
            series[-1]["markPoint"] = {
                "data": mark_points,
                "symbol": "none",
                "label": {
                    "show": True,
                    "position": "top",
                    "distance": 8,
                    "fontSize": 10,
                    "fontWeight": "bold",
                    "color": "#999",
                    "formatter": "{c}"
                }
            }

    # Ajustar ancho de barras según cantidad de días
    bar_max_width = 40 if len(dias_sorted) > 20 else 50
    for s in series:
        s["barMaxWidth"] = bar_max_width

    options = {
        "title": {
            "text": title,
            "subtext": subtitle,
            "left": "center",
            "textStyle": {"color": "#333", "fontSize": 16, "fontWeight": "600"},
            "subtextStyle": {"color": "#888", "fontSize": 12}
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(255, 255, 255, 0.96)",
            "borderColor": "#7FA8C9",
            "borderWidth": 2,
            "borderRadius": 8,
            "textStyle": {"color": "#333", "fontSize": 12},
            "extraCssText": "box-shadow: 0 2px 12px rgba(0,0,0,0.15);"
        },
        "legend": {
            "data": salas_sorted,
            "bottom": 0,
            "textStyle": {"color": "#666", "fontSize": 11},
            "itemGap": 12,
            "icon": "roundRect",
            "type": "scroll"
        },
        "grid": {
            "left": "3%", "right": "4%",
            "bottom": "15%", "top": "22%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": dias_sorted,
            "axisLabel": {
                "color": "#666", "fontSize": 11, "fontWeight": "500",
                "interval": 0,
                "rotate": 45 if len(dias_sorted) > 15 else 0
            },
            "axisLine": {"lineStyle": {"color": "#ddd", "width": 1}},
            "axisTick": {"show": False}
        },
        "yAxis": {
            "type": "value",
            "name": "⚖️ KG",
            "nameTextStyle": {"color": "#3d7a9e", "fontSize": 13, "fontWeight": "600"},
            "axisLabel": {"color": "#666", "fontSize": 11},
            "splitLine": {"lineStyle": {"color": "#f0f0f0", "type": "solid"}},
            "axisLine": {"show": False}
        },
        "series": series,
        "dataZoom": [
            {"type": "inside", "xAxisIndex": 0, "start": 0, "end": 100}
        ] if len(dias_sorted) > 14 else []
    }

    return options, salas_sorted


def _render_grafico_salas(mos_filtradas: List[Dict], salas_data: Dict[str, Dict]):
    """Gráfico de KG desglosado por día y sala."""
    result = _build_chart_kg_dia_sala(mos_filtradas)
    if not result:
        return
    options, salas_sorted = result
    altura = max(450, 380 + len(salas_sorted) * 8)
    st_echarts(options=options, height=f"{altura}px")


def _render_graficos_kg_hora(mos_filtradas: List[Dict], salas_data: Dict[str, Dict]):
    """Renderiza gráficos dedicados de KG/H: uno general por día y uno por cada sala."""
    if not mos_filtradas:
        return
    
    st.markdown("---")
    st.markdown("""
    <div style="background: #ffffff;
                padding: 20px; border-radius: 12px; margin-bottom: 15px;
                border-left: 5px solid #0d3b66; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
        <h3 style="margin:0; color:#0d3b66 !important;">⚡ Rendimiento KG/Hora</h3>
        <p style="margin:5px 0 0 0; color:#555 !important; font-size:13px;">
            Análisis detallado de productividad por hora
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # === GRÁFICO GENERAL: KG/Hora y KG/Hora Efectiva POR TURNO ===
    turnos_data = {}
    for t_name in ["Día", "Tarde"]:
        turnos_data[t_name] = {
            'dia_kg': defaultdict(float),
            'dia_horas': defaultdict(float),
            'dia_detenciones': defaultdict(float),
        }
    
    for mo in mos_filtradas:
        dt = mo.get('_inicio_dt')
        if not dt:
            continue
        dia_key = dt.strftime('%d/%m')
        turno = _clasificar_turno(dt)
        kg = mo.get('kg_pt', 0) or 0
        horas = mo.get('duracion_horas', 0) or 0
        detenciones = mo.get('detenciones', 0) or 0
        td = turnos_data[turno]
        td['dia_kg'][dia_key] += kg
        td['dia_detenciones'][dia_key] += detenciones
        if horas > 0:
            td['dia_horas'][dia_key] += horas
    
    tab_dia, tab_tarde = st.tabs(["☀️ Turno Día", "🌙 Turno Tarde"])
    
    for turno_tab, turno_name, turno_key in [(tab_dia, "Día", "dia"), (tab_tarde, "Tarde", "tarde")]:
        with turno_tab:
            td = turnos_data[turno_name]
            if not td['dia_kg']:
                st.info(f"No hay datos para Turno {turno_name}")
                continue
            
            dias_sorted = sorted(td['dia_kg'].keys(), key=lambda d: datetime.strptime(d, '%d/%m'))
            kg_hora_vals = []
            kg_hora_ef_vals = []
            detenciones_vals = []
            
            for dia in dias_sorted:
                horas = td['dia_horas'].get(dia, 0)
                kg_total = td['dia_kg'][dia]
                detenciones = td['dia_detenciones'].get(dia, 0)
                detenciones_vals.append(round(detenciones, 1))
                
                # KG/Hora (basado en duración total)
                if horas > 0:
                    kg_hora_vals.append(round(kg_total / horas, 0))
                else:
                    kg_hora_vals.append(0)
                
                # KG/Hora Efectiva (descontando detenciones)
                horas_ef = max(horas - detenciones, 0)
                if horas_ef > 0:
                    kg_hora_ef_vals.append(round(kg_total / horas_ef, 0))
                else:
                    kg_hora_ef_vals.append(0)
            
            total_det = sum(td['dia_detenciones'].values())
            icono = "☀️" if turno_name == "Día" else "🌙"
            
            # Promedios
            total_kg_turno = sum(td['dia_kg'].values())
            total_horas_turno = sum(td['dia_horas'].values())
            total_det_turno = sum(td['dia_detenciones'].values())
            prom_kg_hora = total_kg_turno / total_horas_turno if total_horas_turno > 0 else 0
            horas_ef_turno = max(total_horas_turno - total_det_turno, 0)
            prom_kg_hora_ef = total_kg_turno / horas_ef_turno if horas_ef_turno > 0 else 0
            
            subtexto = (f"KG/Hora: {prom_kg_hora:,.0f}  ·  KG/Hora Efectiva: {prom_kg_hora_ef:,.0f}"
                        f"  ·  Detenciones: {total_det:,.1f} hrs  ·  {len(dias_sorted)} días")
            
            opts_turno = {
                "title": {
                    "text": f"{icono} Turno {turno_name} — KG/Hora por Día",
                    "subtext": subtexto,
                    "left": "center",
                    "textStyle": {"color": "#3d7a9e", "fontSize": 15, "fontWeight": "bold"},
                    "subtextStyle": {"color": "#888", "fontSize": 12}
                },
                "tooltip": {
                    "trigger": "axis",
                    "axisPointer": {"type": "cross", "crossStyle": {"color": "#999"}},
                    "backgroundColor": "rgba(255, 255, 255, 0.96)",
                    "borderColor": "#6BA3C4",
                    "borderWidth": 2,
                    "borderRadius": 8,
                    "textStyle": {"color": "#333", "fontSize": 12},
                    "extraCssText": "box-shadow: 0 2px 12px rgba(0,0,0,0.15);"
                },
                "legend": {
                    "data": ["KG/Hora", "KG/Hora Efectiva"],
                    "bottom": 0,
                    "textStyle": {"color": "#666", "fontSize": 11},
                    "itemGap": 15
                },
                "grid": {
                    "left": "3%", "right": "5%",
                    "bottom": "15%", "top": "18%",
                    "containLabel": True
                },
                "xAxis": {
                    "type": "category",
                    "data": dias_sorted,
                    "axisLabel": {
                        "color": "#666", "fontSize": 11, "fontWeight": "500",
                        "interval": 0, "rotate": 35 if len(dias_sorted) > 10 else 0
                    },
                    "axisLine": {"lineStyle": {"color": "#ddd", "width": 1}},
                    "axisTick": {"show": False}
                },
                "yAxis": {
                    "type": "value",
                    "name": "⚡ KG/Hora",
                    "nameTextStyle": {"color": "#3d7a9e", "fontSize": 13, "fontWeight": "600"},
                    "axisLabel": {"color": "#666", "fontSize": 11},
                    "splitLine": {"lineStyle": {"color": "#f0f0f0", "type": "solid"}},
                    "axisLine": {"show": False}
                },
                "labelLayout": {
                    "hideOverlap": True,
                    "moveOverlap": "shiftY"
                },
                "series": [
                    {
                        "name": "KG/Hora",
                        "type": "line",
                        "yAxisIndex": 0,
                        "data": kg_hora_vals,
                        "smooth": True,
                        "symbolSize": 9,
                        "symbol": "circle",
                        "itemStyle": {
                            "color": "#6BA3C4",
                            "borderWidth": 2,
                            "borderColor": "#fff"
                        },
                        "lineStyle": {
                            "color": "#6BA3C4",
                            "width": 3.5,
                            "shadowColor": "rgba(107, 163, 196, 0.4)",
                            "shadowBlur": 8
                        },
                        "areaStyle": {
                            "color": {
                                "type": "linear",
                                "x": 0, "y": 0, "x2": 0, "y2": 1,
                                "colorStops": [
                                    {"offset": 0, "color": "rgba(107, 163, 196, 0.25)"},
                                    {"offset": 1, "color": "rgba(107, 163, 196, 0.02)"}
                                ]
                            }
                        },
                        "label": {
                            "show": True,
                            "position": "top",
                            "fontSize": 10,
                            "fontWeight": "600",
                            "color": "#5A8FAD",
                            "distance": 8,
                            "formatter": JsCode("function(params){return params.value>0?Math.round(params.value):''}").js_code
                        },
                        "z": 2
                    },
                    {
                        "name": "KG/Hora Efectiva",
                        "type": "line",
                        "yAxisIndex": 0,
                        "data": kg_hora_ef_vals,
                        "smooth": True,
                        "symbolSize": 9,
                        "symbol": "diamond",
                        "itemStyle": {
                            "color": "#C9997D",
                            "borderWidth": 2,
                            "borderColor": "#fff"
                        },
                        "lineStyle": {
                            "color": "#C9997D",
                            "width": 3.5,
                            "type": "solid",
                            "shadowColor": "rgba(201, 153, 125, 0.4)",
                            "shadowBlur": 8
                        },
                        "areaStyle": {
                            "color": {
                                "type": "linear",
                                "x": 0, "y": 0, "x2": 0, "y2": 1,
                                "colorStops": [
                                    {"offset": 0, "color": "rgba(201, 153, 125, 0.25)"},
                                    {"offset": 1, "color": "rgba(201, 153, 125, 0.02)"}
                                ]
                            }
                        },
                        "label": {
                            "show": True,
                            "position": "bottom",
                            "fontSize": 10,
                            "fontWeight": "600",
                            "color": "#B38967",
                            "distance": 8,
                            "formatter": JsCode("function(params){return params.value>0?Math.round(params.value):''}").js_code
                        },
                        "z": 3
                    },
                    {
                        "name": "Detenciones",
                        "type": "line",
                        "yAxisIndex": 0,
                        "data": detenciones_vals,
                        "showSymbol": False,
                        "lineStyle": {"width": 0, "opacity": 0},
                        "itemStyle": {"opacity": 0},
                        "tooltip": {"show": True}
                    }
                ]
            }
            st_echarts(options=opts_turno, height="450px", key=f"kg_hora_{turno_key}")
    
    # === GRÁFICOS POR SALA: KG/H POR DÍA ===
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 🏭 KG/Hora por Sala")
    
    filtro_turno_sala = st.selectbox(
        "Filtrar por turno",
        ["Todos", "☀️ Día", "🌙 Tarde"],
        index=0,
        key="filtro_turno_sala"
    )
    
    colores_sala = [
        '#2196F3', '#F44336', '#4CAF50', '#FFC107', '#9C27B0',
        '#FF9800', '#00BCD4', '#E91E63', '#009688', '#673AB7',
        '#FF5722', '#03A9F4', '#8BC34A', '#00ACC1', '#FFEB3B',
    ]
    
    # Ordenar salas por KG/Hora promedio
    salas_ordenadas = sorted(
        salas_data.items(),
        key=lambda x: (x[1]['kg_con_duracion'] / x[1]['duracion_total'])
        if x[1]['duracion_total'] > 0 else 0,
        reverse=True
    )
    
    for idx, (sala, sd) in enumerate(salas_ordenadas):
        # Filtrar órdenes por turno si aplica
        if filtro_turno_sala == "☀️ Día":
            ordenes_filtradas = [o for o in sd['ordenes'] if _clasificar_turno(o.get('_inicio_dt')) == "Día"]
        elif filtro_turno_sala == "🌙 Tarde":
            ordenes_filtradas = [o for o in sd['ordenes'] if _clasificar_turno(o.get('_inicio_dt')) == "Tarde"]
        else:
            ordenes_filtradas = sd['ordenes']
        
        if not ordenes_filtradas:
            continue
        
        # Agrupar por día para esta sala
        sala_dia_kg = defaultdict(float)
        sala_dia_horas = defaultdict(float)
        sala_dia_hh_efectiva = defaultdict(float)
        sala_dia_detenciones = defaultdict(float)
        
        for orden in ordenes_filtradas:
            dt = orden.get('_inicio_dt')
            if not dt:
                continue
            dia_key = dt.strftime('%d/%m')
            kg = orden.get('kg_pt', 0) or 0
            horas = orden.get('duracion_horas', 0) or 0
            hh_ef = orden.get('hh_efectiva', 0) or 0
            detenciones = orden.get('detenciones', 0) or 0
            sala_dia_kg[dia_key] += kg
            sala_dia_hh_efectiva[dia_key] += hh_ef
            sala_dia_detenciones[dia_key] += detenciones
            if horas > 0:
                sala_dia_horas[dia_key] += horas
        
        if not sala_dia_kg:
            continue
        
        dias_sala_sorted = sorted(sala_dia_kg.keys(), key=lambda d: datetime.strptime(d, '%d/%m'))
        kg_hora_efectiva_sala_vals = []  # kg_pt / duracion_horas
        kg_hh_efectiva_sala_vals = []    # kg_pt / hh_efectiva
        detenciones_sala_vals = []  # detenciones por día para tooltip
        
        for dia in dias_sala_sorted:
            horas = sala_dia_horas.get(dia, 0)
            hh_ef = sala_dia_hh_efectiva.get(dia, 0)
            kg_total = sala_dia_kg[dia]
            detenciones = sala_dia_detenciones.get(dia, 0)
            detenciones_sala_vals.append(round(detenciones, 1))
            
            # KG/Hora
            if horas > 0:
                kg_hora_efectiva_sala_vals.append(round(kg_total / horas, 0))
            else:
                kg_hora_efectiva_sala_vals.append(0)
            
            # KG/Hora Efectiva (descontando detenciones)
            horas_efectivas = max(horas - detenciones, 0)
            if horas_efectivas > 0:
                kg_hh_efectiva_sala_vals.append(round(kg_total / horas_efectivas, 0))
            else:
                kg_hh_efectiva_sala_vals.append(0)
        
        # Promedios basados en órdenes filtradas
        total_kg_sala = sum(sala_dia_kg.values())
        total_horas_sala = sum(sala_dia_horas.values())
        total_det_sala = sum(sala_dia_detenciones.values())
        prom_sala = total_kg_sala / total_horas_sala if total_horas_sala > 0 else 0
        horas_ef_sala = max(total_horas_sala - total_det_sala, 0)
        prom_sala_efectiva = total_kg_sala / horas_ef_sala if horas_ef_sala > 0 else 0
        turno_label = f" ({filtro_turno_sala})" if filtro_turno_sala != "Todos" else ""
        color_sala = colores_sala[idx % len(colores_sala)]
        
        opts_sala = {
            "title": {
                "text": f"🏭 {sala}{turno_label}",
                "subtext": f"KG/Hora: {prom_sala:,.0f}  ·  KG/Hora Efectiva: {prom_sala_efectiva:,.0f}  ·  Det: {total_det_sala:,.1f}h  ·  {len(ordenes_filtradas)} órdenes",
                "left": "center",
                "textStyle": {"color": "#3d7a9e", "fontSize": 14, "fontWeight": "600"},
                "subtextStyle": {"color": "#888", "fontSize": 11}
            },
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "cross", "crossStyle": {"color": "#999"}},
                "backgroundColor": "rgba(255, 255, 255, 0.96)",
                "borderColor": "#6BA3C4",
                "borderWidth": 2,
                "borderRadius": 8,
                "textStyle": {"color": "#333", "fontSize": 12},
                "extraCssText": "box-shadow: 0 2px 12px rgba(0,0,0,0.15);"
            },
            "legend": {
                "data": ["KG/Hora", "KG/Hora Efectiva"],
                "bottom": 0,
                "textStyle": {"color": "#666", "fontSize": 10},
                "itemGap": 12
            },
            "grid": {
                "left": "3%", "right": "5%",
                "bottom": "15%", "top": "18%",
                "containLabel": True
            },
            "xAxis": {
                "type": "category",
                "data": dias_sala_sorted,
                "axisLabel": {
                    "color": "#666", "fontSize": 11, "fontWeight": "500",
                    "interval": 0, "rotate": 35 if len(dias_sala_sorted) > 10 else 0
                },
                "axisLine": {"lineStyle": {"color": "#ddd"}},
                "axisTick": {"show": False}
            },
            "yAxis": {
                "type": "value",
                "name": "⚡ KG/Hora",
                "nameTextStyle": {"color": "#3d7a9e", "fontSize": 13, "fontWeight": "600"},
                "axisLabel": {"color": "#666", "fontSize": 11},
                "splitLine": {"lineStyle": {"color": "#f0f0f0", "type": "solid"}},
                "axisLine": {"show": False}
            },
            "series": [
                {
                    "name": "KG/Hora",
                    "type": "line",
                    "yAxisIndex": 0,
                    "data": kg_hora_efectiva_sala_vals,
                    "smooth": True,
                    "symbolSize": 8,
                    "symbol": "circle",
                    "itemStyle": {
                        "color": "#6BA3C4",
                        "borderWidth": 2,
                        "borderColor": "#fff"
                    },
                    "lineStyle": {
                        "color": "#6BA3C4",
                        "width": 4,
                        "shadowColor": "rgba(107, 163, 196, 0.4)",
                        "shadowBlur": 8
                    },
                    "areaStyle": {
                        "color": {
                            "type": "linear",
                            "x": 0, "y": 0, "x2": 0, "y2": 1,
                            "colorStops": [
                                {"offset": 0, "color": "rgba(107, 163, 196, 0.25)"},
                                {"offset": 1, "color": "rgba(107, 163, 196, 0.02)"}
                            ]
                        }
                    },
                    "label": {
                        "show": True,
                        "position": "top",
                        "fontSize": 10,
                        "fontWeight": "bold",
                        "color": "#5A8FAD",
                        "formatter": JsCode("function(params){return params.value>0?Math.round(params.value):''}").js_code
                    },
                    "z": 2
                },
                {
                    "name": "KG/Hora Efectiva",
                    "type": "line",
                    "yAxisIndex": 0,
                    "data": kg_hh_efectiva_sala_vals,
                    "smooth": True,
                    "symbolSize": 8,
                    "symbol": "diamond",
                    "itemStyle": {
                        "color": "#C9997D",
                        "borderWidth": 2,
                        "borderColor": "#fff"
                    },
                    "lineStyle": {
                        "color": "#C9997D",
                        "width": 4,
                        "type": "solid",
                        "shadowColor": "rgba(201, 153, 125, 0.4)",
                        "shadowBlur": 8
                    },
                    "areaStyle": {
                        "color": {
                            "type": "linear",
                            "x": 0, "y": 0, "x2": 0, "y2": 1,
                            "colorStops": [
                                {"offset": 0, "color": "rgba(201, 153, 125, 0.25)"},
                                {"offset": 1, "color": "rgba(201, 153, 125, 0.02)"}
                            ]
                        }
                    },
                    "label": {
                        "show": True,
                        "position": "bottom",
                        "fontSize": 10,
                        "fontWeight": "bold",
                        "color": "#B38967",
                        "formatter": JsCode("function(params){return params.value>0?Math.round(params.value):''}").js_code
                    },
                    "z": 3
                },
                {
                    "name": "Detenciones",
                    "type": "line",
                    "yAxisIndex": 0,
                    "data": detenciones_sala_vals,
                    "showSymbol": False,
                    "lineStyle": {"width": 0, "opacity": 0},
                    "itemStyle": {"opacity": 0},
                    "tooltip": {"show": True}
                }
            ]
        }
        
        st_echarts(options=opts_sala, height="380px", key=f"kg_hora_sala_{idx}")


def _clasificar_turno(dt):
    """Clasifica en turno Día o Tarde basado en hora de inicio.
    Día: L-J 8:00-17:30, V 8:00-16:30, S 8:00-13:00
    Tarde: L-J 17:30-23:30, V 16:30-22:30, S 14:00-22:00
    """
    if dt is None:
        return "Día"
    hora = dt.hour + dt.minute / 60.0
    dow = dt.weekday()  # 0=Lun, 4=Vie, 5=Sáb
    if dow <= 3:  # Lunes a Jueves
        return "Día" if hora < 17.5 else "Tarde"
    elif dow == 4:  # Viernes
        return "Día" if hora < 16.5 else "Tarde"
    elif dow == 5:  # Sábado
        return "Día" if hora < 13 else "Tarde"
    return "Día"


def _render_comparacion_turnos(mos_filtradas: List[Dict]):
    """Renderiza gráfico de barras comparando Turno Día vs Turno Tarde por sala."""
    if not mos_filtradas:
        return
    
    st.markdown("---")
    st.markdown("""
    <div style="background: #ffffff;
                padding: 20px; border-radius: 12px; margin-bottom: 15px;
                border-left: 5px solid #E8A87C; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
        <h3 style="margin:0; color:#C27A50 !important;">☀️🌙 Comparación Turno Día vs Turno Tarde</h3>
        <p style="margin:5px 0 0 0; color:#555 !important; font-size:13px;">
            KG/Hora y KG/Hora Efectiva por sala y turno
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Agrupar por sala y turno
    sala_turno = {}  # {sala: {turno: {kg, horas, detenciones, ordenes}}}
    
    for mo in mos_filtradas:
        dt = mo.get('_inicio_dt')
        if not dt:
            continue
        sala = mo.get('sala') or 'Sin Sala'
        turno = _clasificar_turno(dt)
        kg = mo.get('kg_pt', 0) or 0
        horas = mo.get('duracion_horas', 0) or 0
        detenciones = mo.get('detenciones', 0) or 0
        
        if sala not in sala_turno:
            sala_turno[sala] = {}
        if turno not in sala_turno[sala]:
            sala_turno[sala][turno] = {'kg': 0, 'horas': 0, 'detenciones': 0, 'ordenes': 0}
        
        st_data = sala_turno[sala][turno]
        st_data['kg'] += kg
        st_data['ordenes'] += 1
        if horas > 0:
            st_data['horas'] += horas
            st_data['detenciones'] += detenciones
    
    if not sala_turno:
        return
    
    # Ordenar salas por KG/Hora total
    salas_sorted = sorted(sala_turno.keys(), key=lambda s: (
        sala_turno[s].get('Día', {}).get('kg', 0) + sala_turno[s].get('Tarde', {}).get('kg', 0)
    ) / max(
        sala_turno[s].get('Día', {}).get('horas', 0) + sala_turno[s].get('Tarde', {}).get('horas', 0), 1
    ), reverse=True)
    
    # Preparar datos para el gráfico
    kg_hora_dia = []
    kg_hora_tarde = []
    kg_hora_ef_dia = []
    kg_hora_ef_tarde = []
    ordenes_dia = []
    ordenes_tarde = []
    
    for sala in salas_sorted:
        # Turno Día
        d = sala_turno[sala].get('Día', {'kg': 0, 'horas': 0, 'detenciones': 0, 'ordenes': 0})
        kh_d = round(d['kg'] / d['horas']) if d['horas'] > 0 else 0
        horas_ef_d = max(d['horas'] - d['detenciones'], 0)
        kh_ef_d = round(d['kg'] / horas_ef_d) if horas_ef_d > 0 else 0
        kg_hora_dia.append(kh_d)
        kg_hora_ef_dia.append(kh_ef_d)
        ordenes_dia.append(d['ordenes'])
        
        # Turno Tarde
        t = sala_turno[sala].get('Tarde', {'kg': 0, 'horas': 0, 'detenciones': 0, 'ordenes': 0})
        kh_t = round(t['kg'] / t['horas']) if t['horas'] > 0 else 0
        horas_ef_t = max(t['horas'] - t['detenciones'], 0)
        kh_ef_t = round(t['kg'] / horas_ef_t) if horas_ef_t > 0 else 0
        kg_hora_tarde.append(kh_t)
        kg_hora_ef_tarde.append(kh_ef_t)
        ordenes_tarde.append(t['ordenes'])
    
    # Totales generales por turno
    total_d = {'kg': 0, 'horas': 0, 'det': 0, 'ord': 0}
    total_t = {'kg': 0, 'horas': 0, 'det': 0, 'ord': 0}
    for sala in sala_turno:
        dd = sala_turno[sala].get('Día', {'kg': 0, 'horas': 0, 'detenciones': 0, 'ordenes': 0})
        tt = sala_turno[sala].get('Tarde', {'kg': 0, 'horas': 0, 'detenciones': 0, 'ordenes': 0})
        total_d['kg'] += dd['kg']; total_d['horas'] += dd['horas']; total_d['det'] += dd['detenciones']; total_d['ord'] += dd['ordenes']
        total_t['kg'] += tt['kg']; total_t['horas'] += tt['horas']; total_t['det'] += tt['detenciones']; total_t['ord'] += tt['ordenes']
    
    prom_d = round(total_d['kg'] / total_d['horas']) if total_d['horas'] > 0 else 0
    prom_t = round(total_t['kg'] / total_t['horas']) if total_t['horas'] > 0 else 0
    ef_h_d = max(total_d['horas'] - total_d['det'], 0)
    ef_h_t = max(total_t['horas'] - total_t['det'], 0)
    prom_ef_d = round(total_d['kg'] / ef_h_d) if ef_h_d > 0 else 0
    prom_ef_t = round(total_t['kg'] / ef_h_t) if ef_h_t > 0 else 0
    
    # KPIs resumen
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#FFF8E1,#FFFDE7);padding:15px;border-radius:10px;border-left:4px solid #FFB74D;text-align:center;">
            <div style="font-size:13px;color:#F57C00;font-weight:600;">☀️ Turno Día</div>
            <div style="font-size:22px;font-weight:700;color:#E65100;">{prom_d:,} <span style="font-size:12px;">kg/h</span></div>
            <div style="font-size:11px;color:#888;">Efectiva: {prom_ef_d:,} kg/h · {total_d['ord']} órdenes · Det: {total_d['det']:,.1f}h</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#E8EAF6,#F3E5F5);padding:15px;border-radius:10px;border-left:4px solid #7E57C2;text-align:center;">
            <div style="font-size:13px;color:#5E35B1;font-weight:600;">🌙 Turno Tarde</div>
            <div style="font-size:22px;font-weight:700;color:#4527A0;">{prom_t:,} <span style="font-size:12px;">kg/h</span></div>
            <div style="font-size:11px;color:#888;">Efectiva: {prom_ef_t:,} kg/h · {total_t['ord']} órdenes · Det: {total_t['det']:,.1f}h</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Gráfico de barras agrupadas
    opts_comp = {
        "title": {
            "text": "☀️🌙 KG/Hora por Sala — Día vs Tarde",
            "subtext": f"Día: {prom_d:,} kg/h ({total_d['ord']} órd)  ·  Tarde: {prom_t:,} kg/h ({total_t['ord']} órd)",
            "left": "center",
            "textStyle": {"color": "#3d7a9e", "fontSize": 15, "fontWeight": "bold"},
            "subtextStyle": {"color": "#888", "fontSize": 12}
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(255, 255, 255, 0.96)",
            "borderColor": "#ddd",
            "borderWidth": 1,
            "borderRadius": 8,
            "textStyle": {"color": "#333", "fontSize": 12},
            "extraCssText": "box-shadow: 0 2px 12px rgba(0,0,0,0.15);",
        },
        "legend": {
            "data": ["☀️ KG/Hora Día", "🌙 KG/Hora Tarde", "☀️ KG/H Efectiva Día", "🌙 KG/H Efectiva Tarde"],
            "bottom": 0,
            "textStyle": {"color": "#666", "fontSize": 10},
            "itemGap": 10
        },
        "grid": {
            "left": "3%", "right": "5%",
            "bottom": "18%", "top": "18%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": salas_sorted,
            "axisLabel": {
                "color": "#666", "fontSize": 10, "fontWeight": "500",
                "interval": 0, "rotate": 25 if len(salas_sorted) > 4 else 0
            },
            "axisLine": {"lineStyle": {"color": "#ddd"}},
            "axisTick": {"show": False}
        },
        "yAxis": {
            "type": "value",
            "name": "KG/Hora",
            "nameTextStyle": {"color": "#3d7a9e", "fontSize": 12, "fontWeight": "600"},
            "axisLabel": {"color": "#666", "fontSize": 11},
            "splitLine": {"lineStyle": {"color": "#f0f0f0"}},
            "axisLine": {"show": False}
        },
        "series": [
            {
                "name": "☀️ KG/Hora Día",
                "type": "bar",
                "data": kg_hora_dia,
                "barGap": "0%",
                "barCategoryGap": "35%",
                "itemStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#FFB74D"},
                            {"offset": 1, "color": "#FF9800"}
                        ]
                    },
                    "borderRadius": [4, 4, 0, 0]
                },
                "label": {
                    "show": True, "position": "top",
                    "fontSize": 9, "fontWeight": "600", "color": "#E65100",
                    "formatter": JsCode("function(p){return p.value>0?p.value.toLocaleString():''}").js_code
                }
            },
            {
                "name": "🌙 KG/Hora Tarde",
                "type": "bar",
                "data": kg_hora_tarde,
                "itemStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#9575CD"},
                            {"offset": 1, "color": "#7E57C2"}
                        ]
                    },
                    "borderRadius": [4, 4, 0, 0]
                },
                "label": {
                    "show": True, "position": "top",
                    "fontSize": 9, "fontWeight": "600", "color": "#4527A0",
                    "formatter": JsCode("function(p){return p.value>0?p.value.toLocaleString():''}").js_code
                }
            },
            {
                "name": "☀️ KG/H Efectiva Día",
                "type": "bar",
                "data": kg_hora_ef_dia,
                "itemStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#FFCC80"},
                            {"offset": 1, "color": "#FFB74D"}
                        ]
                    },
                    "borderRadius": [4, 4, 0, 0],
                    "opacity": 0.7
                },
                "label": {
                    "show": True, "position": "top",
                    "fontSize": 9, "fontWeight": "600", "color": "#F57C00",
                    "formatter": JsCode("function(p){return p.value>0?p.value.toLocaleString():''}").js_code
                }
            },
            {
                "name": "🌙 KG/H Efectiva Tarde",
                "type": "bar",
                "data": kg_hora_ef_tarde,
                "itemStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#B39DDB"},
                            {"offset": 1, "color": "#9575CD"}
                        ]
                    },
                    "borderRadius": [4, 4, 0, 0],
                    "opacity": 0.7
                },
                "label": {
                    "show": True, "position": "top",
                    "fontSize": 9, "fontWeight": "600", "color": "#5E35B1",
                    "formatter": JsCode("function(p){return p.value>0?p.value.toLocaleString():''}").js_code
                }
            }
        ]
    }
    st_echarts(options=opts_comp, height="480px", key="comp_turnos_barras")


def render(username: str = None, password: str = None):
    """Render principal del tab Rendimiento en Salas."""

    if not username:
        username = st.session_state.get("odoo_username", "")
    if not password:
        password = st.session_state.get("odoo_api_key", "")

    if not username or not password:
        st.warning("⚠️ Debes iniciar sesión para ver este módulo")
        return

    # === FONDO BLANCO SOLO PARA ESTA PÁGINA ===
    st.markdown("""
    <style>
    /* Fondo blanco principal */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
    .main .block-container, section[data-testid="stMainBlockContainer"] {
        background-color: #ffffff !important;
    }
    /* Sidebar sin cambios */
    [data-testid="stSidebar"] {
        background-color: inherit !important;
    }
    [data-testid="stSidebar"] * {
        color: inherit !important;
    }
    /* Textos oscuros para contraste */
    .stApp .main h1, .stApp .main h2, .stApp .main h3, .stApp .main h4, .stApp .main h5, .stApp .main h6 {
        color: #1a1a2e !important;
    }
    .stApp .main p, .stApp .main span, .stApp .main label, .stApp .main div {
        color: #333 !important;
    }
    /* Métricas */
    [data-testid="stMetricValue"] {
        color: #1a1a2e !important;
    }
    [data-testid="stMetricLabel"] {
        color: #555 !important;
    }
    [data-testid="stMetricDelta"] svg {
        fill: currentColor !important;
    }
    /* === INPUTS, SELECTS, DATE PICKERS === */
    .stApp .main [data-baseweb="input"],
    .stApp .main [data-baseweb="base-input"],
    .stApp .main [data-baseweb="select"] > div,
    .stApp .main [data-baseweb="popover"] > div,
    .stApp .main input,
    .stApp .main [data-testid="stDateInput"] > div > div,
    .stApp .main [data-testid="stDateInput"] input,
    .stApp .main [data-testid="stSelectbox"] > div > div,
    .stApp .main [data-testid="stMultiSelect"] > div > div {
        background-color: #ffffff !important;
        color: #333 !important;
        border-color: #ccc !important;
    }
    .stApp .main [data-baseweb="input"] input,
    .stApp .main [data-baseweb="select"] input {
        color: #333 !important;
        -webkit-text-fill-color: #333 !important;
    }
    /* Select dropdown value text */
    .stApp .main [data-baseweb="select"] span,
    .stApp .main [data-baseweb="select"] div[aria-selected] {
        color: #333 !important;
    }
    /* Select dropdown arrow */
    .stApp .main [data-baseweb="select"] svg {
        fill: #666 !important;
    }
    /* Date input containers */
    .stApp .main [data-testid="stDateInput"] > div > div > div {
        background-color: #ffffff !important;
        border: 1px solid #ccc !important;
        border-radius: 8px !important;
    }
    /* === BOTONES === */
    .stApp .main .stButton button {
        background-color: #0d3b66 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
    }
    .stApp .main .stButton button:hover {
        background-color: #1a5276 !important;
        color: #ffffff !important;
    }
    .stApp .main .stButton button p,
    .stApp .main .stButton button span {
        color: #ffffff !important;
    }
    /* Botones de descarga */
    .stApp .main .stDownloadButton button {
        background-color: #0d3b66 !important;
        color: #ffffff !important;
    }
    .stApp .main .stDownloadButton button p,
    .stApp .main .stDownloadButton button span {
        color: #ffffff !important;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #f0f2f5 !important;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #555 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #0d3b66 !important;
        font-weight: 600 !important;
    }
    /* Expanders */
    [data-testid="stExpander"] {
        background-color: #f8f9fa !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary span {
        color: #333 !important;
    }
    /* Dividers */
    .stApp .main hr {
        border-color: #e0e0e0 !important;
    }
    /* Info/Warning boxes */
    .stApp .main .stAlert {
        background-color: #f0f7ff !important;
        border: 1px solid #cce0ff !important;
    }
    .stApp .main .stAlert p, .stApp .main .stAlert span {
        color: #333 !important;
    }
    /* Selectbox labels */
    .stApp .main [data-testid="stSelectbox"] label,
    .stApp .main [data-testid="stDateInput"] label {
        color: #333 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # === HEADER ===
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0d3b66 0%, #1a5276 100%);
                padding: 25px; border-radius: 15px; margin-bottom: 20px;
                box-shadow: 0 4px 12px rgba(13,59,102,0.15);">
        <h2 style="margin:0; color:#ffffff !important;">🏭 Rendimiento en Salas</h2>
        <p style="margin:5px 0 0 0; color:#b0c4de !important;">
            Rendimiento, KG/Hora y detalle de órdenes por sala de proceso
        </p>
    </div>
    """, unsafe_allow_html=True)

    # === FILTROS ===
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        fecha_inicio = st.date_input("📅 Desde",
                                     value=datetime.now().date() - timedelta(days=7),
                                     key="rend_sala_fecha_inicio")
    with col2:
        fecha_fin = st.date_input("📅 Hasta",
                                  value=datetime.now().date(),
                                  key="rend_sala_fecha_fin")
    with col3:
        planta_opciones = ["Todos", "Rio Futuro", "Vilkun"]
        planta_sel = st.selectbox("🏭 Planta", planta_opciones, key="rend_sala_planta")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        btn = st.button("🔍 Buscar", type="primary", use_container_width=True,
                         key="rend_sala_buscar")

    st.markdown("---")

    if btn:
        st.session_state['rend_sala_loaded'] = True

    if not st.session_state.get('rend_sala_loaded'):
        st.info("👆 Selecciona el rango de fechas y presiona **Buscar**")
        return

    # === CARGAR DATOS ===
    try:
        with st.spinner("Cargando datos de producción..."):
            data = fetch_datos_produccion(
                username, password,
                fecha_inicio.isoformat(),
                fecha_fin.isoformat()
            )
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return

    mos_raw = data.get('mos', [])

    if not mos_raw:
        st.warning("No hay órdenes de producción en el período seleccionado")
        return

    # === ENRIQUECER MOs ===
    for mo in mos_raw:
        mo['_planta'] = detectar_planta(mo)
        # Determinar estado: si no viene explícito, inferir
        if not mo.get('_estado'):
            mo['_estado'] = 'done' if mo.get('fecha_termino') else 'progress'

        mo['_inicio_dt'] = parsear_fecha(mo.get('fecha_inicio'))
        mo['_fin_dt'] = parsear_fecha(mo.get('fecha_termino'))

    # Excluir canceladas
    mos_all = [mo for mo in mos_raw if mo.get('_estado') != 'cancel']

    # === FILTRO PLANTA ===
    if planta_sel != "Todos":
        mos_all = [mo for mo in mos_all if mo['_planta'] == planta_sel]

    if not mos_all:
        st.warning("No hay órdenes con los filtros seleccionados")
        return

    # Excluir túneles estáticos (no son líneas de proceso)
    mos_all = [mo for mo in mos_all
               if not any(t in (mo.get('sala') or '').lower()
                          for t in ['estatico', 'estático'])]

    if not mos_all:
        st.warning("No hay órdenes de líneas de proceso en el período")
        return

    # === EXTRAER ESPECIES Y SALAS DISPONIBLES ===
    especies_set = set()
    salas_set = set()
    for mo in mos_all:
        esp = mo.get('especie', '') or 'Otro'
        if esp and esp != 'Otro':
            especies_set.add(esp)
        sala = mo.get('sala') or 'Sin Sala'
        salas_set.add(sala)

    especies_list = sorted(especies_set)
    salas_list = sorted(salas_set)

    # === FILTROS SECUNDARIOS (especie + sala) ===
    col_e, col_s = st.columns(2)
    with col_e:
        especie_opciones = ["Todos"] + especies_list
        especie_sel = st.selectbox("🍓 Especie", especie_opciones, key="rend_sala_especie")
    with col_s:
        sala_opciones = ["Todos"] + salas_list
        sala_sel = st.selectbox("🏠 Sala", sala_opciones, key="rend_sala_sala")

    st.markdown("---")

    # === APLICAR FILTROS SECUNDARIOS ===
    mos_filtradas = mos_all
    if especie_sel != "Todos":
        mos_filtradas = [mo for mo in mos_filtradas if mo.get('especie') == especie_sel]
    if sala_sel != "Todos":
        mos_filtradas = [mo for mo in mos_filtradas
                         if (mo.get('sala') or 'Sin Sala') == sala_sel]

    if not mos_filtradas:
        st.warning("No hay órdenes con los filtros seleccionados")
        return

    # === AGRUPAR POR SALA ===
    salas_data = _procesar_mos_a_salas(mos_filtradas)

    # === KPIs GENERALES ===
    total_ordenes = len(mos_filtradas)
    total_kg = sum(s['total_kg'] for s in salas_data.values())
    prom_kg_hora = _calcular_kg_hora(mos_filtradas)
    hechas_total = sum(s['hechas'] for s in salas_data.values())
    no_hechas_total = sum(s['no_hechas'] for s in salas_data.values())

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("📋 Órdenes", f"{total_ordenes:,}",
                   help=f"✅ {hechas_total} hechas | 🔄 {no_hechas_total} en proceso")
    with k2:
        st.metric("⚖️ KG Procesados", f"{total_kg:,.0f}")
    with k3:
        st.metric("⚡ KG/Hora Prom", f"{prom_kg_hora:,.0f}")
    with k4:
        st.metric("🏭 Salas Activas", f"{len(salas_data)}")

    # === BOTÓN DESCARGAR INFORME ===
    pdf_bytes = _generar_informe_pdf(
        fecha_inicio, fecha_fin, planta_sel, especie_sel, sala_sel,
        total_ordenes, total_kg, prom_kg_hora, hechas_total, no_hechas_total,
        salas_data, mos_filtradas
    )
    st.download_button(
        label="📥 Descargar Informe PDF",
        data=pdf_bytes,
        file_name=f"Informe_Rendimiento_{fecha_inicio}_{fecha_fin}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    st.markdown("---")

    # === GRÁFICO KG POR DÍA/SALA ===
    _render_grafico_salas(mos_filtradas, salas_data)
    
    # === GRÁFICOS DE KG/HORA ===
    _render_graficos_kg_hora(mos_filtradas, salas_data)

    # === COMPARACIÓN TURNO DÍA VS TURNO TARDE (BARRAS) ===
    _render_comparacion_turnos(mos_filtradas)

    st.markdown("---")

    # === TARJETAS POR SALA ===
    colores_sala = [
        '#2196F3', '#F44336', '#4CAF50', '#FFC107', '#9C27B0',
        '#FF9800', '#00BCD4', '#E91E63', '#009688', '#673AB7',
        '#FF5722', '#03A9F4', '#8BC34A', '#00ACC1', '#FFEB3B',
    ]

    # Ordenar salas por KG/Hora (kg_con_duracion/duracion) descendente
    salas_ordenadas = sorted(
        salas_data.items(),
        key=lambda x: (x[1]['kg_con_duracion'] / x[1]['duracion_total'])
        if x[1]['duracion_total'] > 0 else 0,
        reverse=True
    )

    for idx, (sala, sd) in enumerate(salas_ordenadas):
        prom = sd['kg_con_duracion'] / sd['duracion_total'] if sd['duracion_total'] > 0 else 0
        em = emoji_kg_hora(prom)
        c = colores_sala[idx % len(colores_sala)]
        total = sd['hechas'] + sd['no_hechas']

        # Tarjeta de sala
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {c}18, {c}08);
                    border: 1px solid {c}40; border-radius: 12px; padding: 18px;
                    margin-bottom: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.08);">
            <div style="display: flex; justify-content: space-between;
                        align-items: center; flex-wrap: wrap;">
                <div style="color: {c}; font-weight: 600; font-size: 18px;">
                    {em} 🏭 {sala}
                </div>
                <div style="color: #666; font-size: 13px;">
                    {total} órdenes
                    ({sd['hechas']} ✅ hechas | {sd['no_hechas']} 🔄 en proceso)
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Métricas de la sala
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            st.metric("📋 Órdenes", f"{total}")
        with mc2:
            st.metric("⚖️ KG Procesados", f"{sd['total_kg']:,.0f}")
        with mc3:
            st.metric("⚡ KG/Hora Prom", f"{prom:,.0f}")
        with mc4:
            pct_hechas = (sd['hechas'] / total * 100) if total > 0 else 0
            st.metric("✅ % Completadas", f"{pct_hechas:.0f}%")

        # Desplegable con detalle de órdenes
        with st.expander(f"📋 Ver {total} órdenes de {sala}", expanded=False):
            ordenes_sorted = sorted(
                sd['ordenes'],
                key=lambda o: o.get('_inicio_dt') or datetime.min,
                reverse=True
            )

            for oi, orden in enumerate(ordenes_sorted):
                kg_h = orden.get('kg_hora_efectiva', 0) or orden.get('kg_por_hora', 0) or 0
                kg_total_o = orden.get('kg_pt', 0) or 0
                dot = orden.get('dotacion', 0) or 0
                rend = orden.get('rendimiento', 0) or 0
                especie_o = orden.get('especie', '-')
                mo_name = orden.get('mo_name', 'N/A')
                estado_code = orden.get('state', 'progress')
                estado = estado_label(estado_code)
                em_estado = emoji_estado(estado_code)

                inicio_dt = orden.get('_inicio_dt')
                fin_dt = orden.get('_fin_dt')
                hora_ini = inicio_dt.strftime("%d/%m %H:%M") if inicio_dt else '-'
                hora_fin = fin_dt.strftime("%d/%m %H:%M") if fin_dt else '-'
                duracion_str = ""
                if inicio_dt and fin_dt:
                    dur_h = (fin_dt - inicio_dt).total_seconds() / 3600
                    duracion_str = f"{dur_h:.1f}h"

                em_o = emoji_kg_hora(kg_h)
                em_esp = emoji_especie(especie_o)
                det_o = orden.get('detenciones', 0) or 0
                det_str = f" — ⏸️ Det: {det_o:.1f}h" if det_o > 0 else ""
                
                # Badge de estado con color
                if estado_code == 'done':
                    badge_color = "#4caf50"
                    badge_text = "✅ Cerrada"
                elif estado_code == 'progress':
                    badge_color = "#2196F3"
                    badge_text = "🔄 En Proceso"
                elif estado_code == 'cancel':
                    badge_color = "#f44336"
                    badge_text = "❌ Cancelada"
                else:
                    badge_color = "#9e9e9e"
                    badge_text = f"📋 {estado}"

                st.markdown(
                    f'**{em_o} {mo_name}** — '
                    f'<span style="background:{badge_color};color:white;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600;">{badge_text}</span>'
                    f' — {em_esp} {especie_o}{det_str}',
                    unsafe_allow_html=True
                )

                # CSS para ajustar tamaño de fuente en métricas
                st.markdown("""
                <style>
                [data-testid="stMetricValue"] {
                    font-size: 1.2rem !important;
                }
                [data-testid="stMetricLabel"] {
                    font-size: 0.85rem !important;
                }
                </style>
                """, unsafe_allow_html=True)

                oc1, oc2, oc3, oc4, oc5, oc6, oc7, oc8 = st.columns([1, 1, 0.8, 1.2, 1.2, 0.8, 1, 1])
                with oc1:
                    st.metric("⚡ KG/Hora", f"{kg_h:,.0f}")
                with oc2:
                    st.metric("⚖️ KG Total", f"{kg_total_o:,.0f}")
                with oc3:
                    st.metric("👷 Dotación", f"{int(dot)}")
                with oc4:
                    st.metric("🕐 Inicio", hora_ini)
                with oc5:
                    st.metric("🕑 Fin", hora_fin, delta=duracion_str if duracion_str else None, delta_color="off")
                with oc6:
                    merma = max(100 - rend, 0)
                    st.metric("📈 Rend.", f"{rend:.1f}%", delta=f"-{merma:.1f}% merma" if merma > 0 else None, delta_color="inverse")
                with oc7:
                    hh = orden.get('hh', 0) or 0
                    st.metric("⏱️ HH", f"{hh:,.1f}")
                with oc8:
                    hh_efectiva = orden.get('hh_efectiva', 0) or 0
                    st.metric("⏱️ HH Efectiva", f"{hh_efectiva:,.1f}")

                if oi < len(ordenes_sorted) - 1:
                    st.divider()

        st.markdown("---")

    # === SECCIÓN COMPARACIÓN ===
    _render_comparacion(
        username, password,
        fecha_inicio, fecha_fin,
        planta_sel, especie_sel, sala_sel,
        salas_data, mos_filtradas
    )


def _calcular_kg_hora(mos_list: List[Dict]) -> float:
    """Calcula KG/Hora solo con MOs que tienen duración > 0 (promedio ponderado real)."""
    mos_con_dur = [mo for mo in mos_list if (mo.get('duracion_horas', 0) or 0) > 0]
    if not mos_con_dur:
        return 0
    total_kg = sum(mo.get('kg_pt', 0) or 0 for mo in mos_con_dur)
    total_horas = sum(mo.get('duracion_horas', 0) or 0 for mo in mos_con_dur)
    return round(total_kg / total_horas, 1) if total_horas > 0 else 0


def _procesar_mos_a_salas(mos_list: List[Dict]) -> Dict[str, Dict]:
    """Agrupa MOs en datos por sala (reutilizable para principal y comparación)."""
    salas: Dict[str, Dict] = {}
    for mo in mos_list:
        sala = mo.get('sala') or 'Sin Sala'
        if sala not in salas:
            salas[sala] = {
                'ordenes': [],
                'total_kg': 0.0,
                'kg_con_duracion': 0.0,
                'duracion_total': 0.0,
                'detenciones_total': 0.0,
                'hechas': 0,
                'no_hechas': 0,
            }
        sd = salas[sala]
        sd['ordenes'].append(mo)
        kg = mo.get('kg_pt', 0) or 0
        dur = mo.get('duracion_horas', 0) or 0
        det = mo.get('detenciones', 0) or 0
        sd['total_kg'] += kg
        if dur > 0:
            sd['kg_con_duracion'] += kg
            sd['duracion_total'] += dur
            sd['detenciones_total'] += det
        if mo.get('fecha_termino'):
            sd['hechas'] += 1
        else:
            sd['no_hechas'] += 1
    return salas


def _generar_informe_pdf(
    fecha_inicio, fecha_fin, planta_sel, especie_sel, sala_sel,
    total_ordenes, total_kg, prom_kg_hora, hechas_total, no_hechas_total,
    salas_data, mos_filtradas
) -> bytes:
    """Genera un informe PDF con los datos filtrados del tab Rendimiento en Salas."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Spacer,
                                     Paragraph, Image, KeepTogether, PageBreak)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)

    story = []
    styles = getSampleStyleSheet()

    # Colores corporativos
    azul_corp = HexColor('#0d3b66')
    azul_claro = HexColor('#7FA8C9')
    gris = HexColor('#666666')
    verde = HexColor('#4caf50')
    rojo = HexColor('#f44336')
    fondo_header = HexColor('#0d3b66')
    fondo_fila = HexColor('#f5f7fa')

    # Estilos personalizados
    titulo_style = ParagraphStyle('TituloInforme', parent=styles['Title'],
                                   fontSize=18, textColor=azul_corp,
                                   spaceAfter=4, alignment=TA_CENTER)
    subtitulo_style = ParagraphStyle('Subtitulo', parent=styles['Normal'],
                                      fontSize=11, textColor=gris,
                                      spaceAfter=10, alignment=TA_CENTER)
    seccion_style = ParagraphStyle('Seccion', parent=styles['Heading2'],
                                    fontSize=13, textColor=azul_corp,
                                    spaceBefore=14, spaceAfter=6)
    normal_style = ParagraphStyle('NormalCustom', parent=styles['Normal'],
                                   fontSize=9, textColor=black)
    celda_style = ParagraphStyle('Celda', parent=styles['Normal'],
                                  fontSize=8, textColor=black, leading=10)
    celda_header = ParagraphStyle('CeldaHeader', parent=styles['Normal'],
                                   fontSize=8, textColor=white, leading=10,
                                   alignment=TA_CENTER)
    celda_right = ParagraphStyle('CeldaRight', parent=styles['Normal'],
                                  fontSize=8, textColor=black, leading=10,
                                  alignment=TA_RIGHT)

    # === LOGO ===
    if os.path.exists(_LOGO_PATH):
        logo = Image(_LOGO_PATH, width=5*cm, height=5*cm)
        logo.hAlign = 'CENTER'
        story.append(logo)
        story.append(Spacer(1, 3*mm))

    # === TÍTULO ===
    story.append(Paragraph("Informe de Rendimiento en Salas", titulo_style))
    story.append(Paragraph(
        f"Período: {fecha_inicio} al {fecha_fin}",
        subtitulo_style
    ))

    # Filtros aplicados
    filtros = []
    if planta_sel != "Todos":
        filtros.append(f"Planta: {planta_sel}")
    if especie_sel != "Todos":
        filtros.append(f"Especie: {especie_sel}")
    if sala_sel != "Todos":
        filtros.append(f"Sala: {sala_sel}")
    if filtros:
        story.append(Paragraph(f"Filtros: {' | '.join(filtros)}", subtitulo_style))

    story.append(Paragraph(
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle('Fecha', parent=styles['Normal'],
                       fontSize=8, textColor=gris, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 5*mm))

    # === KPIs GENERALES ===
    story.append(Paragraph("Resumen General", seccion_style))

    kpi_data = [
        ['Órdenes Totales', 'KG Procesados', 'KG/Hora Prom', 'Completadas', 'En Proceso', 'Salas'],
        [f'{total_ordenes:,}', f'{total_kg:,.0f}', f'{prom_kg_hora:,.0f}',
         f'{hechas_total}', f'{no_hechas_total}', f'{len(salas_data)}']
    ]
    kpi_table = Table(kpi_data, colWidths=[3*cm, 3.2*cm, 3*cm, 2.5*cm, 2.5*cm, 2*cm])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), fondo_header),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 11),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 1), (-1, 1), azul_corp),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ('BACKGROUND', (0, 1), (-1, 1), fondo_fila),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 6*mm))

    # === PRODUCCIÓN POR DÍA ===
    story.append(Paragraph("Producción por Día", seccion_style))

    DIAS_ES = {'Mon': 'Lun', 'Tue': 'Mar', 'Wed': 'Mié', 'Thu': 'Jue',
               'Fri': 'Vie', 'Sat': 'Sáb', 'Sun': 'Dom'}

    dia_kg = defaultdict(float)
    dia_ordenes = defaultdict(int)
    for mo in mos_filtradas:
        dt = mo.get('_inicio_dt')
        if not dt:
            continue
        dia_key = dt.strftime('%Y-%m-%d')
        dia_kg[dia_key] += mo.get('kg_pt', 0) or 0
        dia_ordenes[dia_key] += 1

    dias_sorted = sorted(dia_kg.items())

    if dias_sorted:
        dia_rows = [['Día', 'Fecha', 'Órdenes', 'KG Producidos', '% del Total']]
        for fecha, kg in dias_sorted:
            dt = datetime.strptime(fecha, '%Y-%m-%d')
            dia_en = dt.strftime('%a')
            dia_esp = DIAS_ES.get(dia_en, dia_en)
            pct = (kg / total_kg * 100) if total_kg > 0 else 0
            dia_rows.append([
                dia_esp,
                dt.strftime('%d/%m/%Y'),
                str(dia_ordenes.get(fecha, 0)),
                f'{kg:,.0f}',
                f'{pct:.1f}%'
            ])
        # Fila total
        dia_rows.append(['', 'TOTAL', str(sum(dia_ordenes.values())),
                          f'{total_kg:,.0f}', '100%'])

        dia_table = Table(dia_rows, colWidths=[1.8*cm, 2.5*cm, 2*cm, 3.5*cm, 2.5*cm])
        dia_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), fondo_header),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), HexColor('#e8edf2')),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [white, fondo_fila]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(dia_table)
        
        # === GRÁFICO DE PRODUCCIÓN DIARIA ===
        if len(dias_sorted) > 0:
            fechas_prod = [f for f, kg in dias_sorted]
            kg_prod = [kg for f, kg in dias_sorted]
            labels_prod = [datetime.strptime(f, '%Y-%m-%d').strftime('%d/%m') for f in fechas_prod]
            
            fig_prod, ax_prod = plt.subplots(figsize=(7, 3))
            fig_prod.patch.set_facecolor('white')
            ax_prod.set_facecolor('#fafbfc')
            
            # Barras con degradado de color
            colores_prod = ['#0d3b66' if kg == max(kg_prod) else '#7FA8C9' for kg in kg_prod]
            bars = ax_prod.bar(range(len(labels_prod)), kg_prod, color=colores_prod, 
                               edgecolor='white', linewidth=1.5, alpha=0.85)
            
            ax_prod.set_xlabel('Día', fontsize=9, fontweight='600', color='#666')
            ax_prod.set_ylabel('KG Producidos', fontsize=9, fontweight='600', color='#0d3b66')
            ax_prod.set_title('📊 Producción Diaria (KG)', fontsize=11, fontweight='bold', 
                             color='#0d3b66', pad=12)
            ax_prod.set_xticks(range(len(labels_prod)))
            ax_prod.set_xticklabels(labels_prod, rotation=45 if len(labels_prod) > 5 else 0,
                                    ha='right' if len(labels_prod) > 5 else 'center',
                                    fontsize=8, color='#666')
            ax_prod.tick_params(axis='y', labelsize=8, colors='#666')
            ax_prod.grid(axis='y', alpha=0.2, linestyle='-', linewidth=0.5)
            ax_prod.spines['top'].set_visible(False)
            ax_prod.spines['right'].set_visible(False)
            ax_prod.spines['left'].set_color('#ddd')
            ax_prod.spines['bottom'].set_color('#ddd')
            
            # Añadir valores encima de las barras
            for i, (bar, val) in enumerate(zip(bars, kg_prod)):
                height = bar.get_height()
                ax_prod.text(bar.get_x() + bar.get_width()/2., height + max(kg_prod)*0.02,
                            f'{val:,.0f}', ha='center', va='bottom', 
                            fontsize=7, fontweight='600', color='#0d3b66')
            
            plt.tight_layout()
            
            img_buf_prod = io.BytesIO()
            plt.savefig(img_buf_prod, format='png', dpi=150, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            img_buf_prod.seek(0)
            plt.close(fig_prod)
            
            img_prod = Image(img_buf_prod, width=17*cm, height=7*cm)
            story.append(Spacer(1, 4*mm))
            story.append(img_prod)
    
    story.append(Spacer(1, 6*mm))

    # === RENDIMIENTO KG/HORA POR DÍA ===
    story.append(Paragraph("Rendimiento KG/Hora por Día", seccion_style))
    
    dia_kg_hora_data = defaultdict(float)
    dia_horas_data = defaultdict(float)
    dia_hh_efectiva_data = defaultdict(float)
    dia_detenciones_data = defaultdict(float)
    
    for mo in mos_filtradas:
        dt = mo.get('_inicio_dt')
        if not dt:
            continue
        dia_key = dt.strftime('%Y-%m-%d')
        kg = mo.get('kg_pt', 0) or 0
        horas = mo.get('duracion_horas', 0) or 0
        hh_ef = mo.get('hh_efectiva', 0) or 0
        det = mo.get('detenciones', 0) or 0
        
        dia_kg_hora_data[dia_key] += kg
        dia_hh_efectiva_data[dia_key] += hh_ef
        dia_detenciones_data[dia_key] += det
        if horas > 0:
            dia_horas_data[dia_key] += horas
    
    if dia_kg_hora_data:
        kgh_rows = [['Día', 'Fecha', 'KG Producidos', 'Horas', 'KG/Hora', 'HH Efectiva', 'Detenciones']]
        for fecha in sorted(dia_kg_hora_data.keys()):
            dt = datetime.strptime(fecha, '%Y-%m-%d')
            dia_en = dt.strftime('%a')
            dia_esp = DIAS_ES.get(dia_en, dia_en)
            kg = dia_kg_hora_data[fecha]
            horas = dia_horas_data.get(fecha, 0)
            hh_ef = dia_hh_efectiva_data.get(fecha, 0)
            det = dia_detenciones_data.get(fecha, 0)
            kg_h = (kg / horas) if horas > 0 else 0
            
            kgh_rows.append([
                dia_esp,
                dt.strftime('%d/%m/%Y'),
                f'{kg:,.0f}',
                f'{horas:.1f}',
                f'{kg_h:,.0f}',
                f'{hh_ef:.1f}',
                f'{det:.1f}'
            ])
        
        kgh_table = Table(kgh_rows, colWidths=[1.5*cm, 2.3*cm, 2.8*cm, 1.8*cm, 2.3*cm, 2.3*cm, 2.3*cm])
        kgh_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), fondo_header),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, fondo_fila]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(kgh_table)
        
        # === GRÁFICO KG/HORA EFECTIVA ===
        # Preparar datos para el gráfico
        fechas_graf = sorted(dia_kg_hora_data.keys())
        dias_labels = [datetime.strptime(f, '%Y-%m-%d').strftime('%d/%m') for f in fechas_graf]
        kg_hora_vals = []
        kg_hh_vals = []
        
        for fecha in fechas_graf:
            kg = dia_kg_hora_data[fecha]
            horas = dia_horas_data.get(fecha, 0)
            det = dia_detenciones_data.get(fecha, 0)
            
            # KG/Hora (duración total)
            if horas > 0:
                kg_hora_vals.append(kg / horas)
            else:
                kg_hora_vals.append(0)
            
            # KG/Hora Efectiva (descontando detenciones)
            horas_efectivas = max(horas - det, 0)
            if horas_efectivas > 0:
                kg_hh_vals.append(kg / horas_efectivas)
            else:
                kg_hh_vals.append(0)
        
        # Generar gráfico con matplotlib
        fig, ax = plt.subplots(figsize=(7, 3.5))
        fig.patch.set_facecolor('white')
        ax.set_facecolor('#fafbfc')
        
        x_pos = list(range(len(dias_labels)))
        
        # KG/Hora - línea azul elegante
        ax.plot(x_pos, kg_hora_vals, color='#6BA3C4', linewidth=2.5, 
                marker='o', markersize=6, label='KG/Hora',
                markerfacecolor='#6BA3C4', markeredgecolor='white', markeredgewidth=1.5,
                zorder=3)
        ax.fill_between(x_pos, kg_hora_vals, alpha=0.2, color='#6BA3C4', zorder=1)
        
        # Agregar valores numéricos en puntos azules
        for i, (x, y) in enumerate(zip(x_pos, kg_hora_vals)):
            if y > 0:
                ax.text(x, y, f'{y:,.0f}', 
                       ha='center', va='bottom', fontsize=8, 
                       fontweight='600', color='#5A8FAD',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                edgecolor='none', alpha=0.7))
        
        # KG/Hora Efectiva - línea beige/salmón
        ax.plot(x_pos, kg_hh_vals, color='#C9997D', linewidth=2.5,
                marker='D', markersize=5, label='KG/Hora Efectiva',
                markerfacecolor='#C9997D', markeredgecolor='white', markeredgewidth=1.5,
                zorder=3)
        ax.fill_between(x_pos, kg_hh_vals, alpha=0.2, color='#C9997D', zorder=1)
        
        # Agregar valores numéricos en puntos beige
        for i, (x, y) in enumerate(zip(x_pos, kg_hh_vals)):
            if y > 0:
                ax.text(x, y, f'{y:,.0f}', 
                       ha='center', va='top', fontsize=8, 
                       fontweight='600', color='#B38967',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                edgecolor='none', alpha=0.7))
        
        # Estilo del gráfico
        ax.set_xlabel('Día', fontsize=10, fontweight='600', color='#666')
        ax.set_ylabel('KG/Hora', fontsize=10, fontweight='600', color='#0d3b66')
        ax.set_title('⚡ KG/Hora y KG/Hora Efectiva por Día', 
                     fontsize=12, fontweight='bold', color='#0d3b66', pad=15)
        
        ax.set_xticks(x_pos)
        ax.set_xlim(-0.5, len(dias_labels) - 0.5)
        ax.set_xticklabels(dias_labels, rotation=45 if len(dias_labels) > 7 else 0, 
                           ha='right' if len(dias_labels) > 7 else 'center',
                           fontsize=8, color='#666')
        ax.tick_params(axis='y', labelsize=9, colors='#666')
        ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5, color='#ddd', zorder=0)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#ddd')
        ax.spines['bottom'].set_color('#ddd')
        
        # Leyenda
        ax.legend(loc='upper left', frameon=True, fancybox=True, shadow=True,
                  fontsize=9, edgecolor='#ddd', facecolor='white', framealpha=0.95)
        
        plt.tight_layout()
        
        # Convertir a imagen para PDF
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight', 
                    facecolor='white', edgecolor='none')
        img_buf.seek(0)
        plt.close(fig)
        
        # Agregar imagen al PDF
        img_graf = Image(img_buf, width=17*cm, height=8.5*cm)
        story.append(Spacer(1, 4*mm))
        story.append(img_graf)
    story.append(Spacer(1, 6*mm))

    # === DETALLE POR SALA ===
    story.append(Paragraph("Detalle por Sala", seccion_style))

    salas_ordenadas = sorted(
        salas_data.items(),
        key=lambda x: (x[1]['kg_con_duracion'] / x[1]['duracion_total'])
        if x[1]['duracion_total'] > 0 else 0,
        reverse=True
    )

    # Tabla resumen de salas
    sala_rows = [['Sala', 'Órds', 'KG Totales', 'KG/Hora', 'HH Efec.', 'Comp.', 'Proceso']]
    for sala, sd in salas_ordenadas:
        kh = sd['kg_con_duracion'] / sd['duracion_total'] if sd['duracion_total'] > 0 else 0
        total_s = sd['hechas'] + sd['no_hechas']
        # Calcular HH efectiva total de la sala
        hh_ef_sala = sum(o.get('hh_efectiva', 0) or 0 for o in sd['ordenes'])
        sala_rows.append([
            Paragraph(sala, celda_style),
            str(total_s),
            f"{sd['total_kg']:,.0f}",
            f"{kh:,.0f}",
            f"{hh_ef_sala:.1f}",
            str(sd['hechas']),
            str(sd['no_hechas'])
        ])

    sala_table = Table(sala_rows, colWidths=[4*cm, 1.3*cm, 2.5*cm, 2*cm, 1.8*cm, 1.5*cm, 1.5*cm])
    sala_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), fondo_header),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, fondo_fila]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(sala_table)
    
    # === GRÁFICO COMPARATIVO DE SALAS ===
    if len(salas_ordenadas) > 0:
        nombres_salas = [sala for sala, sd in salas_ordenadas[:10]]  # Top 10 salas
        kg_hora_salas = [
            (sd['kg_con_duracion'] / sd['duracion_total']) if sd['duracion_total'] > 0 else 0 
            for sala, sd in salas_ordenadas[:10]
        ]
        kg_totales_salas = [sd['total_kg'] for sala, sd in salas_ordenadas[:10]]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.5, 3))
        fig.patch.set_facecolor('white')
        
        # Gráfico 1: KG/Hora por Sala
        colores_barras = ['#6BA3C4' if i == 0 else '#A8C4C9' for i in range(len(nombres_salas))]
        ax1.barh(nombres_salas, kg_hora_salas, color=colores_barras, edgecolor='white', linewidth=1.5)
        ax1.set_xlabel('KG/Hora', fontsize=9, fontweight='600', color='#666')
        ax1.set_title('Rendimiento por Sala', fontsize=10, fontweight='bold', color='#0d3b66', pad=10)
        ax1.tick_params(axis='both', labelsize=8, colors='#666')
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['left'].set_color('#ddd')
        ax1.spines['bottom'].set_color('#ddd')
        ax1.grid(axis='x', alpha=0.2, linestyle='-', linewidth=0.5)
        
        # Añadir valores a las barras
        for i, v in enumerate(kg_hora_salas):
            ax1.text(v + max(kg_hora_salas) * 0.02, i, f'{v:,.0f}', 
                    va='center', fontsize=8, fontweight='600', color='#0d3b66')
        
        # Gráfico 2: KG Totales por Sala
        colores_barras2 = ['#C9997D' if i == 0 else '#C9AFA8' for i in range(len(nombres_salas))]
        ax2.barh(nombres_salas, kg_totales_salas, color=colores_barras2, edgecolor='white', linewidth=1.5)
        ax2.set_xlabel('KG Procesados', fontsize=9, fontweight='600', color='#666')
        ax2.set_title('Producción Total por Sala', fontsize=10, fontweight='bold', color='#0d3b66', pad=10)
        ax2.tick_params(axis='both', labelsize=8, colors='#666')
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.spines['left'].set_color('#ddd')
        ax2.spines['bottom'].set_color('#ddd')
        ax2.grid(axis='x', alpha=0.2, linestyle='-', linewidth=0.5)
        
        # Añadir valores a las barras
        for i, v in enumerate(kg_totales_salas):
            ax2.text(v + max(kg_totales_salas) * 0.02, i, f'{v:,.0f}', 
                    va='center', fontsize=8, fontweight='600', color='#0d3b66')
        
        plt.tight_layout()
        
        # Convertir a imagen
        img_buf_salas = io.BytesIO()
        plt.savefig(img_buf_salas, format='png', dpi=150, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        img_buf_salas.seek(0)
        plt.close(fig)
        
        img_salas = Image(img_buf_salas, width=17*cm, height=7*cm)
        story.append(Spacer(1, 4*mm))
        story.append(img_salas)
    
    story.append(Spacer(1, 6*mm))

    # === DETALLE DE ÓRDENES POR SALA ===
    story.append(PageBreak())
    story.append(Paragraph("Detalle de Órdenes por Sala", seccion_style))
    story.append(Spacer(1, 3*mm))
    
    for sala, sd in salas_ordenadas:
        kh_sala = sd['kg_con_duracion'] / sd['duracion_total'] if sd['duracion_total'] > 0 else 0
        story.append(Paragraph(
            f"{sala} — {len(sd['ordenes'])} órdenes — {sd['total_kg']:,.0f} KG — {kh_sala:,.0f} KG/h",
            ParagraphStyle('SalaTitulo', parent=styles['Heading3'],
                           fontSize=10, textColor=azul_corp, spaceBefore=8, spaceAfter=4)
        ))
        
        # === MINI GRÁFICO DE KG/HORA PARA LA SALA ===
        # Agrupar datos de la sala por día
        sala_dia_data = defaultdict(lambda: {'kg': 0, 'horas': 0, 'det': 0, 'hh_ef': 0})
        for orden in sd['ordenes']:
            dt = orden.get('_inicio_dt')
            if not dt:
                continue
            dia_key = dt.strftime('%d/%m')
            sala_dia_data[dia_key]['kg'] += orden.get('kg_pt', 0) or 0
            sala_dia_data[dia_key]['horas'] += orden.get('duracion_horas', 0) or 0
            sala_dia_data[dia_key]['det'] += orden.get('detenciones', 0) or 0
            sala_dia_data[dia_key]['hh_ef'] += orden.get('hh_efectiva', 0) or 0
        
        if len(sala_dia_data) > 1:  # Solo mostrar si hay más de un día
            dias_sala = sorted(sala_dia_data.keys(), key=lambda d: datetime.strptime(d, '%d/%m'))
            kg_hora_sala_vals = []
            kg_hh_sala_vals = []
            
            for dia in dias_sala:
                data = sala_dia_data[dia]
                # KG/Hora (duración total)
                if data['horas'] > 0:
                    kg_hora_sala_vals.append(data['kg'] / data['horas'])
                else:
                    kg_hora_sala_vals.append(0)
                
                # KG/Hora Efectiva (descontando detenciones)
                horas_ef = max(data['horas'] - data['det'], 0)
                if horas_ef > 0:
                    kg_hh_sala_vals.append(data['kg'] / horas_ef)
                else:
                    kg_hh_sala_vals.append(0)
            
            # Crear mini gráfico
            fig_sala, ax_sala = plt.subplots(figsize=(6, 2))
            fig_sala.patch.set_facecolor('white')
            ax_sala.set_facecolor('#fafbfc')
            
            x_sala = list(range(len(dias_sala)))
            ax_sala.plot(x_sala, kg_hora_sala_vals, color='#6BA3C4', linewidth=2,
                        marker='o', markersize=4, label='KG/Hora',
                        markerfacecolor='#6BA3C4', markeredgecolor='white', markeredgewidth=1)
            ax_sala.plot(x_sala, kg_hh_sala_vals, color='#C9997D', linewidth=2,
                        marker='D', markersize=3.5, label='KG/Hora Efectiva',
                        markerfacecolor='#C9997D', markeredgecolor='white', markeredgewidth=1)
            
            # Agregar valores numéricos en los puntos
            for i, (x, y) in enumerate(zip(x_sala, kg_hora_sala_vals)):
                if y > 0:
                    ax_sala.text(x, y, f'{y:,.0f}', ha='center', va='bottom', 
                               fontsize=6, fontweight='600', color='#5A8FAD')
            for i, (x, y) in enumerate(zip(x_sala, kg_hh_sala_vals)):
                if y > 0:
                    ax_sala.text(x, y, f'{y:,.0f}', ha='center', va='top', 
                               fontsize=6, fontweight='600', color='#B38967')
            
            ax_sala.set_xticks(x_sala)
            ax_sala.set_xticklabels(dias_sala, fontsize=7, color='#666')
            ax_sala.tick_params(axis='y', labelsize=7, colors='#666')
            ax_sala.grid(True, alpha=0.15, linestyle='-', linewidth=0.5)
            ax_sala.spines['top'].set_visible(False)
            ax_sala.spines['right'].set_visible(False)
            ax_sala.spines['left'].set_color('#ddd')
            ax_sala.spines['bottom'].set_color('#ddd')
            ax_sala.legend(loc='upper left', fontsize=7, frameon=False)
            ax_sala.set_ylabel('KG/Hora', fontsize=8, color='#666')
            
            plt.tight_layout()
            
            img_buf_sala = io.BytesIO()
            plt.savefig(img_buf_sala, format='png', dpi=120, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            img_buf_sala.seek(0)
            plt.close(fig_sala)
            
            img_mini_sala = Image(img_buf_sala, width=14*cm, height=5*cm)
            story.append(img_mini_sala)
            story.append(Spacer(1, 2*mm))

        orden_rows = [['Orden', 'Estado', 'Especie', 'KG Total', 'KG/Hora', 'Dot.', 'HH', 'HH Ef.', 'Det.(h)', 'Inicio', 'Fin', 'Rend.']]
        ordenes_sorted = sorted(
            sd['ordenes'],
            key=lambda o: o.get('_inicio_dt') or datetime.min,
            reverse=True
        )

        for orden in ordenes_sorted:
            kg_h = orden.get('kg_hora_efectiva', 0) or orden.get('kg_por_hora', 0) or 0
            kg_o = orden.get('kg_pt', 0) or 0
            dot = orden.get('dotacion', 0) or 0
            rend = orden.get('rendimiento', 0) or 0
            especie_o = orden.get('especie', '-')
            mo_name = orden.get('mo_name', 'N/A')
            estado_code = orden.get('state', 'progress')
            estado = estado_label(estado_code)
            hh = orden.get('hh', 0) or 0
            hh_efectiva = orden.get('hh_efectiva', 0) or 0
            detenciones = orden.get('detenciones', 0) or 0
            ini = orden.get('_inicio_dt')
            fin = orden.get('_fin_dt')
            hora_ini = ini.strftime("%d/%m %H:%M") if ini else '-'
            hora_fin = fin.strftime("%d/%m %H:%M") if fin else '-'
            
            # Emoji para estado
            estado_emoji = '✅' if estado_code == 'done' else '🔄' if estado_code == 'progress' else '📋'

            orden_rows.append([
                Paragraph(mo_name, celda_style),
                estado_emoji,
                especie_o,
                f"{kg_o:,.0f}",
                f"{kg_h:,.0f}",
                str(int(dot)),
                f"{hh:.1f}",
                f"{hh_efectiva:.1f}",
                f"{detenciones:.1f}",
                hora_ini,
                hora_fin,
                f"{rend:.1f}%"
            ])

        col_widths = [2.8*cm, 0.8*cm, 1.4*cm, 1.6*cm, 1.4*cm, 0.9*cm, 1.1*cm, 1.1*cm, 1.1*cm, 1.8*cm, 1.8*cm, 1.2*cm]
        orden_table = Table(orden_rows, colWidths=col_widths)
        orden_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.3, HexColor('#dddddd')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, fondo_fila]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(orden_table)
        story.append(Spacer(1, 3*mm))

    # Build PDF
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def _render_comparacion(
    username, password,
    fecha_inicio_principal, fecha_fin_principal,
    planta_sel, especie_sel, sala_sel,
    salas_principal, mos_principal
):
    """Sección de Comparación: comparación día a día real entre dos períodos."""

    st.markdown("""
    <div style="background: #ffffff;
                padding: 25px; border-radius: 15px; margin-bottom: 20px;
                border-left: 5px solid #D999B2; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
        <h2 style="margin:0; color:#B07090 !important;">📊 Comparación de Períodos</h2>
        <p style="margin:5px 0 0 0; color:#555 !important;">
            Compara la producción día a día contra otro período.
            Se aplican los mismos filtros de Planta, Especie y Sala.
        </p>
    </div>
    """, unsafe_allow_html=True)

    filtros_activos = []
    if planta_sel != "Todos":
        filtros_activos.append(f"🏭 {planta_sel}")
    if especie_sel != "Todos":
        filtros_activos.append(f"🍓 {especie_sel}")
    if sala_sel != "Todos":
        filtros_activos.append(f"🏠 {sala_sel}")
    if filtros_activos:
        st.caption(f"Filtros aplicados: {' · '.join(filtros_activos)}")

    cc1, cc2, cc3 = st.columns([1, 1, 1])
    with cc1:
        comp_inicio = st.date_input("📅 Comparar Desde",
                                     value=fecha_inicio_principal - timedelta(days=7),
                                     key="rend_comp_fecha_inicio")
    with cc2:
        comp_fin = st.date_input("📅 Comparar Hasta",
                                  value=fecha_inicio_principal - timedelta(days=1),
                                  key="rend_comp_fecha_fin")
    with cc3:
        st.markdown("<br>", unsafe_allow_html=True)
        btn_comp = st.button("🔍 Comparar", type="primary", use_container_width=True,
                              key="rend_comp_buscar")

    if btn_comp:
        st.session_state['rend_comp_loaded'] = True

    if not st.session_state.get('rend_comp_loaded'):
        st.info("👆 Selecciona el rango de fechas a comparar y presiona **Comparar**")
        return

    # Cargar datos del período comparación
    try:
        with st.spinner("Cargando datos del período de comparación..."):
            data_comp = fetch_datos_produccion(
                username, password,
                comp_inicio.isoformat(),
                comp_fin.isoformat()
            )
    except Exception as e:
        st.error(f"Error al cargar datos de comparación: {str(e)}")
        return

    mos_comp_raw = data_comp.get('mos', [])
    if not mos_comp_raw:
        st.warning("No hay órdenes en el período de comparación")
        return

    # Enriquecer y filtrar igual que el principal
    for mo in mos_comp_raw:
        mo['_planta'] = detectar_planta(mo)
        if not mo.get('_estado'):
            mo['_estado'] = 'done' if mo.get('fecha_termino') else 'progress'
        mo['_inicio_dt'] = parsear_fecha(mo.get('fecha_inicio'))
        mo['_fin_dt'] = parsear_fecha(mo.get('fecha_termino'))

    mos_comp = [mo for mo in mos_comp_raw if mo.get('_estado') != 'cancel']
    mos_comp = [mo for mo in mos_comp
                if not any(t in (mo.get('sala') or '').lower()
                           for t in ['estatico', 'estático'])]

    if planta_sel != "Todos":
        mos_comp = [mo for mo in mos_comp if mo['_planta'] == planta_sel]
    if especie_sel != "Todos":
        mos_comp = [mo for mo in mos_comp if mo.get('especie') == especie_sel]
    if sala_sel != "Todos":
        mos_comp = [mo for mo in mos_comp
                     if (mo.get('sala') or 'Sin Sala') == sala_sel]

    if not mos_comp:
        st.warning("No hay órdenes con los mismos filtros en el período de comparación")
        return

    salas_comp = _procesar_mos_a_salas(mos_comp)

    # === LABELS ===
    lbl_a = f"{fecha_inicio_principal.strftime('%d/%m')} - {fecha_fin_principal.strftime('%d/%m')}"
    lbl_b = f"{comp_inicio.strftime('%d/%m')} - {comp_fin.strftime('%d/%m')}"

    # === Traducción de días ===
    DIAS_ES = {'Mon': 'Lun', 'Tue': 'Mar', 'Wed': 'Mié', 'Thu': 'Jue',
               'Fri': 'Vie', 'Sat': 'Sáb', 'Sun': 'Dom'}

    def _dia_es(fecha_str):
        """Convierte '2026-01-03' a 'Vie 03/01'."""
        dt = datetime.strptime(fecha_str, '%Y-%m-%d')
        dia_en = dt.strftime('%a')
        dia_esp = DIAS_ES.get(dia_en, dia_en)
        return f"{dia_esp} {dt.strftime('%d/%m')}"

    # === AGRUPAR KG POR DÍA ===
    def _kg_por_dia(mos_list):
        dia_kg = defaultdict(float)
        dia_ordenes = defaultdict(int)
        dia_horas = defaultdict(float)
        for mo in mos_list:
            dt = mo.get('_inicio_dt')
            if not dt:
                continue
            dia_key = dt.strftime('%Y-%m-%d')
            dia_kg[dia_key] += mo.get('kg_pt', 0) or 0
            dia_ordenes[dia_key] += 1
            # Acumular horas del día
            duracion = mo.get('duracion_horas', 0) or 0
            if duracion > 0:
                dia_horas[dia_key] += duracion
        return dict(sorted(dia_kg.items())), dict(sorted(dia_ordenes.items())), dict(sorted(dia_horas.items()))

    dias_kg_a, dias_ord_a, dias_horas_a = _kg_por_dia(mos_principal)
    dias_kg_b, dias_ord_b, dias_horas_b = _kg_por_dia(mos_comp)

    dias_a_list = sorted(dias_kg_a.items())
    dias_b_list = sorted(dias_kg_b.items())

    if not dias_a_list and not dias_b_list:
        st.warning("No hay datos diarios para comparar")
        return

    # === TOTALES ===
    kg_a_total = sum(kg for _, kg in dias_a_list)
    kg_b_total = sum(kg for _, kg in dias_b_list)
    ord_a_total = len(mos_principal)
    ord_b_total = len(mos_comp)
    dias_a_count = len(dias_a_list)
    dias_b_count = len(dias_b_list)
    prom_dia_a = kg_a_total / dias_a_count if dias_a_count > 0 else 0
    prom_dia_b = kg_b_total / dias_b_count if dias_b_count > 0 else 0

    def _delta(actual, anterior):
        if anterior == 0:
            return None
        pct = ((actual - anterior) / anterior) * 100
        return pct

    # KG/Hora promedio por período
    kgh_a = _calcular_kg_hora(mos_principal)
    kgh_b = _calcular_kg_hora(mos_comp)

    # === HEADER V/S ===
    st.markdown(f"""
    <div style="text-align: center; margin: 15px 0;">
        <span style="color: #0d3b66; font-size: 18px; font-weight: bold;">📅 {lbl_a}  ({dias_a_count} días)</span>
        <span style="color: #999; font-size: 24px; margin: 0 20px; font-weight: bold;">VS</span>
        <span style="color: #B07090; font-size: 18px; font-weight: bold;">📅 {lbl_b}  ({dias_b_count} días)</span>
    </div>
    """, unsafe_allow_html=True)

    # === KPIs COMPARATIVOS ===
    def _kpi_card(label, icon, val_a_str, val_b_str, diff_str, pct_val, is_positive):
        """Genera HTML de una tarjeta KPI comparativa."""
        diff_color = "#4caf50" if is_positive else "#f44336"
        arrow = "▲" if is_positive else "▼"
        pct_str = f"{pct_val:+.1f}%" if pct_val is not None else "—"
        return (
            '<div style="background:#f8f9fa;border-radius:12px;padding:16px 14px;text-align:center;border:1px solid #e0e0e0;">'
            f'<div style="color:#666;font-size:11px;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px;">{icon} {label}</div>'
            '<div style="display:flex;justify-content:center;align-items:baseline;gap:12px;margin-bottom:6px;">'
            f'<span style="color:#0d3b66;font-size:26px;font-weight:bold;">{val_a_str}</span>'
            '<span style="color:#888;font-size:14px;">vs</span>'
            f'<span style="color:#B07090;font-size:18px;font-weight:600;">{val_b_str}</span>'
            '</div>'
            f'<div style="color:{diff_color};font-size:14px;font-weight:bold;">'
            f'{arrow} {diff_str} ({pct_str})'
            '</div></div>'
        )

    def _fmt_kpi(label, icon, va, vb, fmt_fn):
        diff = va - vb
        pct = _delta(va, vb)
        is_pos = diff >= 0
        sign = "+" if is_pos else ""
        return _kpi_card(label, icon, fmt_fn(va), fmt_fn(vb), sign + fmt_fn(diff), pct, is_pos)

    fmt_int = lambda v: f"{v:,}"
    fmt_dec = lambda v: f"{v:,.0f}"

    diff_kg = kg_a_total - kg_b_total
    diff_kg_color = "#4caf50" if diff_kg >= 0 else "#f44336"
    diff_kg_sign = "+" if diff_kg >= 0 else ""

    cards_html = (
        '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:10px 0 20px 0;">'
        + _fmt_kpi("Órdenes", "📋", ord_a_total, ord_b_total, fmt_int)
        + _fmt_kpi("KG Totales", "⚖️", kg_a_total, kg_b_total, fmt_dec)
        + _fmt_kpi("KG/Hora", "⚡", kgh_a, kgh_b, fmt_dec)
        + _fmt_kpi("KG/Día", "📊", prom_dia_a, prom_dia_b, fmt_dec)
        + '<div style="background:#f8f9fa;border-radius:12px;padding:16px 14px;text-align:center;border:1px solid #e0e0e0;">'
        + '<div style="color:#666;font-size:11px;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px;">⚖️ DIFERENCIA KG</div>'
        + f'<div style="color:{diff_kg_color};font-size:32px;font-weight:bold;">{diff_kg_sign}{diff_kg:,.0f}</div>'
        + '</div></div>'
    )
    st.markdown(cards_html, unsafe_allow_html=True)

    st.markdown("---")

    # === GRÁFICO: producción diaria de cada período con fechas reales ===
    # Eje X muestra fechas reales de ambos períodos combinadas
    labels_a = [_dia_es(f) for f, _ in dias_a_list]
    labels_b = [_dia_es(f) for f, _ in dias_b_list]
    vals_a = [round(kg) for _, kg in dias_a_list]
    vals_b = [round(kg) for _, kg in dias_b_list]
    
    # Calcular KG/H por día para cada período
    kg_hora_a = []
    for fecha, kg in dias_a_list:
        horas = dias_horas_a.get(fecha, 0)
        if horas > 0:
            kg_hora_a.append({"value": round(kg), "kg_hora": round(kg / horas, 0)})
        else:
            kg_hora_a.append({"value": round(kg), "kg_hora": 0})
    
    kg_hora_b = []
    for fecha, kg in dias_b_list:
        horas = dias_horas_b.get(fecha, 0)
        if horas > 0:
            kg_hora_b.append({"value": round(kg), "kg_hora": round(kg / horas, 0)})
        else:
            kg_hora_b.append({"value": round(kg), "kg_hora": 0})

    # Gráficos uno debajo del otro para mayor visibilidad
    opts_a = {
        "title": {
            "text": f"📅 Período Actual: {lbl_a}",
            "subtext": f"{ord_a_total} órdenes · {kg_a_total:,.0f} KG · {kgh_a:,.0f} KG/H · {prom_dia_a:,.0f} KG/día",
            "left": "center",
            "textStyle": {"color": "#0d3b66", "fontSize": 14, "fontWeight": "bold"},
            "subtextStyle": {"color": "#666", "fontSize": 11}
        },
        "tooltip": {
            "trigger": "axis", "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(255, 255, 255, 0.96)", "borderColor": "#ddd",
            "borderRadius": 10, "textStyle": {"color": "#333", "fontSize": 13}
        },
        "grid": {"left": "3%", "right": "4%", "bottom": "12%", "top": "18%", "containLabel": True},
        "xAxis": {
            "type": "category", "data": labels_a,
            "axisLabel": {"color": "#555", "fontSize": 11, "fontWeight": "bold", "interval": 0, "rotate": 25 if len(labels_a) > 10 else 0},
            "axisLine": {"lineStyle": {"color": "#ccc"}}, "axisTick": {"show": False}
        },
        "yAxis": {
            "type": "value", "name": "KG",
            "nameTextStyle": {"color": "#666", "fontSize": 12},
            "axisLabel": {"color": "#666", "fontSize": 11},
            "splitLine": {"lineStyle": {"color": "#e8e8e8", "type": "dashed"}}
        },
        "series": [
            {
                "type": "bar", "data": vals_a, "barMaxWidth": 45,
                "itemStyle": {
                    "color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                              "colorStops": [{"offset": 0, "color": "#7FA8C9"}, {"offset": 1, "color": "#7FA8C955"}]},
                    "borderRadius": [8, 8, 0, 0]
                },
                "label": {"show": True, "position": "top", "fontSize": 11, "fontWeight": "bold", "color": "#7FA8C9"}
            },
            {
                "name": "KG/H",
                "type": "scatter",
                "data": kg_hora_a,
                "symbolSize": 0,
                "z": 999,
                "label": {
                    "show": True,
                    "position": "top",
                    "distance": 22,
                    "formatter": JsCode("function(params){return params.data.kg_hora > 0 ? Math.round(params.data.kg_hora) + ' kg/h' : '';}").js_code,
                    "fontSize": 10,
                    "fontWeight": "bold",
                    "color": "#999",
                },
                "itemStyle": {"opacity": 0}
            }
        ]
    }
    st_echarts(options=opts_a, height="420px", key="comp_periodo_a")

    opts_b = {
        "title": {
            "text": f"📅 Período Comparación: {lbl_b}",
            "subtext": f"{ord_b_total} órdenes · {kg_b_total:,.0f} KG · {kgh_b:,.0f} KG/H · {prom_dia_b:,.0f} KG/día",
            "left": "center",
            "textStyle": {"color": "#B07090", "fontSize": 14, "fontWeight": "bold"},
            "subtextStyle": {"color": "#666", "fontSize": 11}
        },
        "tooltip": {
            "trigger": "axis", "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(255, 255, 255, 0.96)", "borderColor": "#ddd",
            "borderRadius": 10, "textStyle": {"color": "#333", "fontSize": 13}
        },
        "grid": {"left": "3%", "right": "4%", "bottom": "12%", "top": "18%", "containLabel": True},
        "xAxis": {
            "type": "category", "data": labels_b,
            "axisLabel": {"color": "#555", "fontSize": 11, "fontWeight": "bold", "interval": 0, "rotate": 25 if len(labels_b) > 10 else 0},
            "axisLine": {"lineStyle": {"color": "#ccc"}}, "axisTick": {"show": False}
        },
        "yAxis": {
            "type": "value", "name": "KG",
            "nameTextStyle": {"color": "#666", "fontSize": 12},
            "axisLabel": {"color": "#666", "fontSize": 11},
            "splitLine": {"lineStyle": {"color": "#e8e8e8", "type": "dashed"}}
        },
        "series": [
            {
                "type": "bar", "data": vals_b, "barMaxWidth": 45,
                "itemStyle": {
                    "color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                              "colorStops": [{"offset": 0, "color": "#D999B2"}, {"offset": 1, "color": "#D999B255"}]},
                    "borderRadius": [8, 8, 0, 0]
                },
                "label": {"show": True, "position": "top", "fontSize": 11, "fontWeight": "bold", "color": "#D999B2"}
            },
            {
                "name": "KG/H",
                "type": "scatter",
                "data": kg_hora_b,
                "symbolSize": 0,
                "z": 999,
                "label": {
                    "show": True,
                    "position": "top",
                    "distance": 22,
                    "formatter": JsCode("function(params){return params.data.kg_hora > 0 ? Math.round(params.data.kg_hora) + ' kg/h' : '';}").js_code,
                    "fontSize": 10,
                    "fontWeight": "bold",
                    "color": "#999",
                },
                "itemStyle": {"opacity": 0}
            }
        ]
    }
    st_echarts(options=opts_b, height="420px", key="comp_periodo_b")

    st.markdown("---")

    # === RESUMEN COMPARATIVO ===
    st.markdown("##### 📋 Resumen por Período")

    # Tabla período actual
    st.markdown(f"""
    <div style="margin-bottom: 15px;">
        <div style="background: #e8f4f8; padding: 10px 15px; border-radius: 10px 10px 0 0;
                    border-left: 4px solid #0d3b66; font-weight: bold; color: #0d3b66; font-size: 14px;">
            📅 Período Actual: {lbl_a} — {dias_a_count} días — {ord_a_total} órdenes — {kg_a_total:,.0f} KG total — Prom: {prom_dia_a:,.0f} KG/día
        </div>
    """, unsafe_allow_html=True)

    for fecha, kg in dias_a_list:
        ordenes = dias_ord_a.get(fecha, 0)
        pct_of_total = (kg / kg_a_total * 100) if kg_a_total > 0 else 0
        bar_width = pct_of_total * 2  # scale for visual bar
        dia_label = _dia_es(fecha)
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: 1.2fr 1fr 0.8fr 2fr;
                    gap: 8px; padding: 8px 15px; background: #fafafa;
                    border-left: 4px solid #0d3b6633; align-items: center; font-size: 13px;">
            <span style="color: #333; font-weight: bold;">{dia_label}</span>
            <span style="color: #0d3b66; font-weight: bold; font-size: 15px;">{kg:,.0f} KG</span>
            <span style="color: #666;">{ordenes} órdenes</span>
            <div style="display: flex; align-items: center; gap: 5px;">
                <div style="background: #7FA8C944; height: 10px; border-radius: 5px; width: {min(bar_width, 100)}%; min-width: 2px;">
                    <div style="background: #7FA8C9; height: 100%; border-radius: 5px; width: 100%;"></div>
                </div>
                <span style="color: #666; font-size: 11px;">{pct_of_total:.0f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Tabla período comparación
    st.markdown(f"""
    <div style="margin-bottom: 15px; margin-top: 15px;">
        <div style="background: #fce4ec; padding: 10px 15px; border-radius: 10px 10px 0 0;
                    border-left: 4px solid #B07090; font-weight: bold; color: #B07090; font-size: 14px;">
            📅 Período Comparación: {lbl_b} — {dias_b_count} días — {ord_b_total} órdenes — {kg_b_total:,.0f} KG total — Prom: {prom_dia_b:,.0f} KG/día
        </div>
    """, unsafe_allow_html=True)

    for fecha, kg in dias_b_list:
        ordenes = dias_ord_b.get(fecha, 0)
        pct_of_total = (kg / kg_b_total * 100) if kg_b_total > 0 else 0
        bar_width = pct_of_total * 2
        dia_label = _dia_es(fecha)
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: 1.2fr 1fr 0.8fr 2fr;
                    gap: 8px; padding: 8px 15px; background: #fafafa;
                    border-left: 4px solid #B0709033; align-items: center; font-size: 13px;">
            <span style="color: #333; font-weight: bold;">{dia_label}</span>
            <span style="color: #B07090; font-weight: bold; font-size: 15px;">{kg:,.0f} KG</span>
            <span style="color: #666;">{ordenes} órdenes</span>
            <div style="display: flex; align-items: center; gap: 5px;">
                <div style="background: #D999B244; height: 10px; border-radius: 5px; width: {min(bar_width, 100)}%; min-width: 2px;">
                    <div style="background: #D999B2; height: 100%; border-radius: 5px; width: 100%;"></div>
                </div>
                <span style="color: #666; font-size: 11px;">{pct_of_total:.0f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # === RESUMEN FINAL ===
    total_diff = kg_a_total - kg_b_total
    td_color = "#4caf50" if total_diff >= 0 else "#f44336"
    td_sign = "+" if total_diff >= 0 else ""
    td_icon = "▲" if total_diff >= 0 else "▼"
    td_pct = f"({td_sign}{(total_diff / kg_b_total * 100):.0f}%)" if kg_b_total > 0 else ""

    prom_diff = prom_dia_a - prom_dia_b
    pd_color = "#4caf50" if prom_diff >= 0 else "#f44336"
    pd_sign = "+" if prom_diff >= 0 else ""
    pd_icon = "▲" if prom_diff >= 0 else "▼"

    st.markdown(f"""
    <div style="background: #f8f9fa; border-radius: 12px; padding: 20px;
                margin-top: 15px; border: 1px solid #e0e0e0;">
        <div style="text-align: center; margin-bottom: 12px; color: #1a1a2e; font-size: 16px; font-weight: bold;">
            📊 Conclusión
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; text-align: center;">
            <div>
                <div style="color: #666; font-size: 12px;">KG Totales</div>
                <div style="color: {td_color}; font-size: 24px; font-weight: bold;">{td_icon} {td_sign}{total_diff:,.0f}</div>
                <div style="color: #888; font-size: 12px;">{td_pct}</div>
            </div>
            <div>
                <div style="color: #666; font-size: 12px;">KG Promedio/Día</div>
                <div style="color: {pd_color}; font-size: 24px; font-weight: bold;">{pd_icon} {pd_sign}{prom_diff:,.0f}</div>
                <div style="color: #888; font-size: 12px;">{prom_dia_a:,.0f} vs {prom_dia_b:,.0f}</div>
            </div>
            <div>
                <div style="color: #666; font-size: 12px;">Órdenes</div>
                <div style="color: #1a1a2e; font-size: 24px; font-weight: bold;">{ord_a_total} vs {ord_b_total}</div>
                <div style="color: #888; font-size: 12px;">{dias_a_count} vs {dias_b_count} días</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # === GRÁFICO KG POR SALA - COMPARACIÓN ===
    todas_salas = sorted(set(list(salas_principal.keys()) + list(salas_comp.keys())))

    if todas_salas:
        nombres_sala = []
        kg_sala_a = []
        kg_sala_b = []

        for sala in todas_salas:
            nombres_sala.append(sala)
            sa = salas_principal.get(sala)
            sc = salas_comp.get(sala)
            kg_sala_a.append(round(sa['total_kg']) if sa else 0)
            kg_sala_b.append(round(sc['total_kg']) if sc else 0)

        options_sala = {
            "title": {
                "text": f"🏭 KG Totales por Sala — {lbl_a} vs {lbl_b}",
                "subtext": "Comparación de producción total por sala entre ambos períodos",
                "left": "center",
                "textStyle": {"color": "#0d3b66", "fontSize": 15, "fontWeight": "bold"},
                "subtextStyle": {"color": "#666", "fontSize": 11}
            },
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "shadow"},
                "backgroundColor": "rgba(255, 255, 255, 0.96)",
                "borderColor": "#ddd",
                "borderRadius": 10,
                "textStyle": {"color": "#333", "fontSize": 13},
                "extraCssText": "box-shadow: 0 2px 12px rgba(0,0,0,0.15);"
            },
            "legend": {
                "data": [f"📅 {lbl_a}", f"📅 {lbl_b}"],
                "bottom": 0,
                "textStyle": {"color": "#555", "fontSize": 12},
                "itemGap": 30,
                "icon": "roundRect"
            },
            "grid": {
                "left": "3%", "right": "4%",
                "bottom": "15%", "top": "20%",
                "containLabel": True
            },
            "xAxis": {
                "type": "category",
                "data": nombres_sala,
                "axisLabel": {
                    "color": "#555", "fontSize": 11, "fontWeight": "bold",
                    "rotate": 20 if len(nombres_sala) > 5 else 0,
                    "interval": 0
                },
                "axisLine": {"lineStyle": {"color": "#ccc", "width": 2}},
                "axisTick": {"show": False}
            },
            "yAxis": {
                "type": "value",
                "name": "⚖️ KG Totales",
                "nameTextStyle": {"color": "#666", "fontSize": 13, "fontWeight": "bold"},
                "axisLabel": {"color": "#666", "fontSize": 11},
                "splitLine": {"lineStyle": {"color": "#e8e8e8", "type": "dashed"}},
                "axisLine": {"show": False}
            },
            "series": [
                {
                    "name": f"📅 {lbl_a}",
                    "type": "bar",
                    "data": kg_sala_a,
                    "barMaxWidth": 40,
                    "barGap": "20%",
                    "itemStyle": {
                        "color": {
                            "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                            "colorStops": [
                                {"offset": 0, "color": "#7FA8C9"},
                                {"offset": 1, "color": "#7FA8C955"}
                            ]
                        },
                        "borderRadius": [8, 8, 0, 0]
                    },
                    "label": {
                        "show": True, "position": "top",
                        "fontSize": 11, "fontWeight": "bold", "color": "#7FA8C9",
                        "formatter": "{c}"
                    }
                },
                {
                    "name": f"📅 {lbl_b}",
                    "type": "bar",
                    "data": kg_sala_b,
                    "barMaxWidth": 40,
                    "itemStyle": {
                        "color": {
                            "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                            "colorStops": [
                                {"offset": 0, "color": "#D999B2"},
                                {"offset": 1, "color": "#D999B255"}
                            ]
                        },
                        "borderRadius": [8, 8, 0, 0]
                    },
                    "label": {
                        "show": True, "position": "top",
                        "fontSize": 11, "fontWeight": "bold", "color": "#D999B2",
                        "formatter": "{c}"
                    }
                }
            ]
        }

        st_echarts(options=options_sala, height="450px", key="comp_sala_chart")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # === GRÁFICO KG/H PROMEDIO POR SALA - COMPARACIÓN ===
        nombres_sala_kgh = []
        kgh_sala_a = []
        kgh_sala_b = []
        
        for sala in todas_salas:
            sa = salas_principal.get(sala)
            sc = salas_comp.get(sala)
            
            # Calcular KG/H promedio de cada sala
            kgh_a = (sa['kg_con_duracion'] / sa['duracion_total']) if sa and sa['duracion_total'] > 0 else 0
            kgh_b = (sc['kg_con_duracion'] / sc['duracion_total']) if sc and sc['duracion_total'] > 0 else 0
            
            # Solo incluir salas que tengan datos en al menos uno de los períodos
            if kgh_a > 0 or kgh_b > 0:
                nombres_sala_kgh.append(sala)
                kgh_sala_a.append(round(kgh_a, 0))
                kgh_sala_b.append(round(kgh_b, 0))
        
        if nombres_sala_kgh:
            options_kgh_sala = {
                "title": {
                    "text": f"⚡ KG/Hora Promedio por Sala — {lbl_a} vs {lbl_b}",
                    "subtext": "Comparación de productividad promedio por sala entre ambos períodos",
                    "left": "center",
                    "textStyle": {"color": "#B8860B", "fontSize": 15, "fontWeight": "bold"},
                    "subtextStyle": {"color": "#666", "fontSize": 11}
                },
                "tooltip": {
                    "trigger": "axis",
                    "axisPointer": {"type": "shadow"},
                    "backgroundColor": "rgba(255, 255, 255, 0.96)",
                    "borderColor": "#ddd",
                    "borderRadius": 10,
                    "textStyle": {"color": "#333", "fontSize": 13},
                    "extraCssText": "box-shadow: 0 2px 12px rgba(0,0,0,0.15);",
                    "formatter": "{b}<br/>{a}: {c} kg/h"
                },
                "legend": {
                    "data": [f"📅 {lbl_a}", f"📅 {lbl_b}"],
                    "bottom": 0,
                    "textStyle": {"color": "#555", "fontSize": 12},
                    "itemGap": 30,
                    "icon": "roundRect"
                },
                "grid": {
                    "left": "3%", "right": "4%",
                    "bottom": "15%", "top": "20%",
                    "containLabel": True
                },
                "xAxis": {
                    "type": "category",
                    "data": nombres_sala_kgh,
                    "axisLabel": {
                        "color": "#555", "fontSize": 11, "fontWeight": "bold",
                        "rotate": 20 if len(nombres_sala_kgh) > 5 else 0,
                        "interval": 0
                    },
                    "axisLine": {"lineStyle": {"color": "#ccc", "width": 2}},
                    "axisTick": {"show": False}
                },
                "yAxis": {
                    "type": "value",
                    "name": "⚡ KG/Hora",
                    "nameTextStyle": {"color": "#B8860B", "fontSize": 13, "fontWeight": "bold"},
                    "axisLabel": {"color": "#666", "fontSize": 11},
                    "splitLine": {"lineStyle": {"color": "#e8e8e8", "type": "dashed"}},
                    "axisLine": {"show": False}
                },
                "series": [
                    {
                        "name": f"📅 {lbl_a}",
                        "type": "bar",
                        "data": kgh_sala_a,
                        "barMaxWidth": 40,
                        "barGap": "20%",
                        "itemStyle": {
                            "color": {
                                "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                                "colorStops": [
                                    {"offset": 0, "color": "#7FA8C9"},
                                    {"offset": 1, "color": "#7FA8C955"}
                                ]
                            },
                            "borderRadius": [8, 8, 0, 0]
                        },
                        "label": {
                            "show": True, "position": "top",
                            "fontSize": 11, "fontWeight": "bold", "color": "#7FA8C9",
                            "formatter": JsCode("function(params){return params.value > 0 ? Math.round(params.value) : ''}").js_code
                        }
                    },
                    {
                        "name": f"📅 {lbl_b}",
                        "type": "bar",
                        "data": kgh_sala_b,
                        "barMaxWidth": 40,
                        "itemStyle": {
                            "color": {
                                "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                                "colorStops": [
                                    {"offset": 0, "color": "#D999B2"},
                                    {"offset": 1, "color": "#D999B255"}
                                ]
                            },
                            "borderRadius": [8, 8, 0, 0]
                        },
                        "label": {
                            "show": True, "position": "top",
                            "fontSize": 11, "fontWeight": "bold", "color": "#D999B2",
                            "formatter": JsCode("function(params){return params.value > 0 ? Math.round(params.value) : ''}").js_code
                        }
                    }
                ]
            }
            
            st_echarts(options=options_kgh_sala, height="450px", key="comp_kgh_sala_chart")


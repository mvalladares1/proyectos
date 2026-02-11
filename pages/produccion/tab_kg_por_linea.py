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
        '#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#F44336',
        '#00BCD4', '#FFEB3B', '#673AB7', '#009688', '#FF5722',
        '#03A9F4', '#8BC34A', '#E91E63', '#00ACC1', '#FFC107',
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

    # Calcular el máximo total por día para determinar umbral de visibilidad de labels
    max_total_dia = 0
    for dia in dias_sorted:
        total_dia = sum(dia_sala_kg[dia].get(s, 0) for s in salas_sorted)
        if total_dia > max_total_dia:
            max_total_dia = total_dia
    umbral_label = max_total_dia * 0.08  # Solo mostrar label si el segmento es >= 8% del máximo

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
            "nameTextStyle": {"color": "#7FA8C9", "fontSize": 13, "fontWeight": "600"},
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
    <div style="background: linear-gradient(135deg, #fafbfc 0%, #f4f5f7 100%);
                padding: 20px; border-radius: 12px; margin-bottom: 15px;
                border-left: 5px solid #7FA8C9; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <h3 style="margin:0; color:#7FA8C9;">⚡ Rendimiento KG/Hora</h3>
        <p style="margin:5px 0 0 0; color:#666; font-size:13px;">
            Análisis detallado de productividad por hora
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # === GRÁFICO GENERAL: KG/H POR DÍA (TODAS LAS SALAS) ===
    dia_kg = defaultdict(float)
    dia_horas = defaultdict(float)
    dia_hh_efectiva = defaultdict(float)
    dia_detenciones = defaultdict(float)
    
    for mo in mos_filtradas:
        dt = mo.get('_inicio_dt')
        if not dt:
            continue
        dia_key = dt.strftime('%d/%m')
        kg = mo.get('kg_pt', 0) or 0
        horas = mo.get('duracion_horas', 0) or 0
        hh_ef = mo.get('hh_efectiva', 0) or 0
        det = mo.get('detenciones', 0) or 0
        dia_kg[dia_key] += kg
        dia_hh_efectiva[dia_key] += hh_ef
        dia_detenciones[dia_key] += det
        if horas > 0:
            dia_horas[dia_key] += horas
    
    if dia_kg:
        dias_sorted = sorted(dia_kg.keys(), key=lambda d: datetime.strptime(d, '%d/%m'))
        kg_hora_vals = []
        tooltip_data = []
        for dia in dias_sorted:
            horas = dia_horas.get(dia, 0)
            hh_ef = dia_hh_efectiva.get(dia, 0)
            det = dia_detenciones.get(dia, 0)
            if horas > 0:
                kg_h = round(dia_kg[dia] / horas, 0)
                kg_hora_vals.append(kg_h)
            else:
                kg_h = 0
                kg_hora_vals.append(0)
            tooltip_data.append({
                'dia': dia,
                'kg_h': kg_h,
                'hh_efectiva': hh_ef,
                'detenciones': det
            })
        
        opts_general = {
            "title": {
                "text": "⚡ KG/Hora y Horas Efectivas por Día",
                "subtext": "Productividad diaria de todas las salas combinadas",
                "left": "center",
                "textStyle": {"color": "#7FA8C9", "fontSize": 15, "fontWeight": "bold"},
                "subtextStyle": {"color": "#888", "fontSize": 12}
            },
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "line"},
                "backgroundColor": "rgba(255, 255, 255, 0.96)",
                "borderColor": "#7FA8C9",
                "borderWidth": 2,
                "borderRadius": 8,
                "textStyle": {"color": "#333", "fontSize": 13}
            },
            "legend": {
                "data": ["KG/Hora", "HH Efectivas"],
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
                    "interval": 0, "rotate": 25 if len(dias_sorted) > 10 else 0
                },
                "axisLine": {"lineStyle": {"color": "#ddd", "width": 1}},
                "axisTick": {"show": False}
            },
            "yAxis": [
                {
                    "type": "value",
                    "name": "⚡ KG/Hora",
                    "nameTextStyle": {"color": "#7FA8C9", "fontSize": 13, "fontWeight": "600"},
                    "axisLabel": {"color": "#666", "fontSize": 11},
                    "splitLine": {"lineStyle": {"color": "#f0f0f0", "type": "solid"}},
                    "axisLine": {"show": False}
                },
                {
                    "type": "value",
                    "name": "⏱️ HH",
                    "nameTextStyle": {"color": "#92C48C", "fontSize": 13, "fontWeight": "600"},
                    "axisLabel": {"color": "#666", "fontSize": 11},
                    "splitLine": {"show": False},
                    "axisLine": {"show": False}
                }
            ],
            "series": [
                {
                    "name": "KG/Hora",
                    "type": "line",
                    "yAxisIndex": 0,
                    "data": kg_hora_vals,
                    "smooth": True,
                    "symbolSize": 8,
                    "itemStyle": {
                        "color": "#7FA8C9",
                        "borderWidth": 2,
                        "borderColor": "#fff"
                    },
                    "lineStyle": {
                        "color": "#7FA8C9",
                        "width": 3,
                        "shadowColor": "rgba(91, 155, 213, 0.3)",
                        "shadowBlur": 8
                    },
                    "label": {
                        "show": True,
                        "position": "top",
                        "fontSize": 10,
                        "fontWeight": "600",
                        "color": "#7FA8C9",
                        "formatter": JsCode("function(params){return params.value>0?Math.round(params.value):'';}").js_code
                    }
                },
                {
                    "name": "HH Efectivas",
                    "type": "line",
                    "yAxisIndex": 1,
                    "data": [tooltip_data[i]['hh_efectiva'] for i in range(len(dias_sorted))],
                    "smooth": True,
                    "symbolSize": 8,
                    "itemStyle": {
                        "color": "#92C48C",
                        "borderWidth": 2,
                        "borderColor": "#fff"
                    },
                    "lineStyle": {
                        "color": "#92C48C",
                        "width": 3,
                        "type": "solid"
                    },
                    "label": {
                        "show": True,
                        "position": "bottom",
                        "fontSize": 10,
                        "fontWeight": "600",
                        "color": "#92C48C",
                        "formatter": JsCode("function(params){return params.value>0?params.value.toFixed(1):'';}").js_code
                    }
                }
            ]
        }
        st_echarts(options=opts_general, height="420px", key="kg_hora_general")
    
    # === GRÁFICOS POR SALA: KG/H POR DÍA ===
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 🏭 KG/Hora por Sala")
    
    colores_sala = [
        '#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#F44336',
        '#00BCD4', '#FFEB3B', '#673AB7', '#009688', '#FF5722',
        '#03A9F4', '#8BC34A', '#E91E63', '#00ACC1', '#FFC107',
    ]
    
    # Ordenar salas por KG/Hora promedio
    salas_ordenadas = sorted(
        salas_data.items(),
        key=lambda x: (x[1]['kg_con_duracion'] / x[1]['duracion_total'])
        if x[1]['duracion_total'] > 0 else 0,
        reverse=True
    )
    
    for idx, (sala, sd) in enumerate(salas_ordenadas):
        # Agrupar por día para esta sala
        sala_dia_kg = defaultdict(float)
        sala_dia_horas = defaultdict(float)
        sala_dia_hh_efectiva = defaultdict(float)
        sala_dia_detenciones = defaultdict(float)
        
        for orden in sd['ordenes']:
            dt = orden.get('_inicio_dt')
            if not dt:
                continue
            dia_key = dt.strftime('%d/%m')
            kg = orden.get('kg_pt', 0) or 0
            horas = orden.get('duracion_horas', 0) or 0
            hh_ef = orden.get('hh_efectiva', 0) or 0
            det = orden.get('detenciones', 0) or 0
            sala_dia_kg[dia_key] += kg
            sala_dia_hh_efectiva[dia_key] += hh_ef
            sala_dia_detenciones[dia_key] += det
            if horas > 0:
                sala_dia_horas[dia_key] += horas
        
        if not sala_dia_kg:
            continue
        
        dias_sala_sorted = sorted(sala_dia_kg.keys(), key=lambda d: datetime.strptime(d, '%d/%m'))
        kg_hora_sala_vals = []
        sala_tooltip_data = []
        for dia in dias_sala_sorted:
            horas = sala_dia_horas.get(dia, 0)
            hh_ef = sala_dia_hh_efectiva.get(dia, 0)
            det = sala_dia_detenciones.get(dia, 0)
            if horas > 0:
                kg_h = round(sala_dia_kg[dia] / horas, 0)
                kg_hora_sala_vals.append(kg_h)
            else:
                kg_h = 0
                kg_hora_sala_vals.append(0)
            sala_tooltip_data.append({
                'dia': dia,
                'kg_h': kg_h,
                'hh_efectiva': hh_ef,
                'detenciones': det
            })
        
        prom_sala = sd['kg_con_duracion'] / sd['duracion_total'] if sd['duracion_total'] > 0 else 0
        color_sala = colores_sala[idx % len(colores_sala)]
        
        opts_sala = {
            "title": {
                "text": f"🏭 {sala}",
                "subtext": f"Promedio: {prom_sala:,.0f} kg/h · {sd['hechas'] + sd['no_hechas']} órdenes",
                "left": "center",
                "textStyle": {"color": color_sala, "fontSize": 14, "fontWeight": "600"},
                "subtextStyle": {"color": "#888", "fontSize": 11}
            },
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "line"},
                "backgroundColor": "rgba(255, 255, 255, 0.96)",
                "borderColor": color_sala,
                "borderWidth": 2,
                "borderRadius": 8,
                "textStyle": {"color": "#333", "fontSize": 13}
            },
            "legend": {
                "data": ["KG/Hora", "HH Efectivas"],
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
                    "color": "#666", "fontSize": 10, "fontWeight": "500",
                    "interval": 0, "rotate": 25 if len(dias_sala_sorted) > 10 else 0
                },
                "axisLine": {"lineStyle": {"color": "#ddd"}},
                "axisTick": {"show": False}
            },
            "yAxis": [
                {
                    "type": "value",
                    "name": "KG/H",
                    "nameTextStyle": {"color": color_sala, "fontSize": 12, "fontWeight": "600"},
                    "axisLabel": {"color": "#666", "fontSize": 10},
                    "splitLine": {"lineStyle": {"color": "#f0f0f0", "type": "solid"}},
                    "axisLine": {"show": False}
                },
                {
                    "type": "value",
                    "name": "HH",
                    "nameTextStyle": {"color": "#92C48C", "fontSize": 12, "fontWeight": "600"},
                    "axisLabel": {"color": "#666", "fontSize": 10},
                    "splitLine": {"show": False},
                    "axisLine": {"show": False}
                }
            ],
            "series": [
                {
                    "name": "KG/Hora",
                    "type": "line",
                    "yAxisIndex": 0,
                    "data": kg_hora_sala_vals,
                    "smooth": True,
                    "symbolSize": 7,
                    "itemStyle": {
                        "color": color_sala,
                        "borderWidth": 2,
                        "borderColor": "#fff"
                    },
                    "lineStyle": {
                        "color": color_sala,
                        "width": 3
                    },
                    "label": {
                        "show": True,
                        "position": "top",
                        "fontSize": 9,
                        "fontWeight": "600",
                        "color": color_sala,
                        "formatter": JsCode("function(params){return params.value>0?Math.round(params.value):'';}").js_code
                    }
                },
                {
                    "name": "HH Efectivas",
                    "type": "line",
                    "yAxisIndex": 1,
                    "data": [sala_tooltip_data[i]['hh_efectiva'] for i in range(len(dias_sala_sorted))],
                    "smooth": True,
                    "symbolSize": 6,
                    "itemStyle": {
                        "color": "#92C48C",
                        "borderWidth": 2,
                        "borderColor": "#fff"
                    },
                    "lineStyle": {
                        "color": "#92C48C",
                        "width": 2,
                        "type": "solid"
                    },
                    "label": {
                        "show": True,
                        "position": "bottom",
                        "fontSize": 8,
                        "fontWeight": "600",
                        "color": "#92C48C",
                        "formatter": JsCode("function(params){return params.value>0?params.value.toFixed(1):'';}").js_code
                    }
                }
            ]
        }
        
        st_echarts(options=opts_sala, height="340px", key=f"kg_hora_sala_{idx}")


def render(username: str = None, password: str = None):
    """Render principal del tab Rendimiento en Salas."""

    if not username:
        username = st.session_state.get("odoo_username", "")
    if not password:
        password = st.session_state.get("odoo_api_key", "")

    if not username or not password:
        st.warning("⚠️ Debes iniciar sesión para ver este módulo")
        return

    # === HEADER ===
    st.markdown("""
    <div style="background: linear-gradient(135deg, #fafbfc 0%, #f4f5f7 100%);
                padding: 25px; border-radius: 15px; margin-bottom: 20px;
                border-left: 5px solid #7FA8C9; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <h2 style="margin:0; color:#7FA8C9;">🏭 Rendimiento en Salas</h2>
        <p style="margin:5px 0 0 0; color:#666;">
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

    st.markdown("---")

    # === TARJETAS POR SALA ===
    colores_sala = [
        '#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#F44336',
        '#00BCD4', '#FFEB3B', '#673AB7', '#009688', '#FF5722',
        '#03A9F4', '#8BC34A', '#E91E63', '#00ACC1', '#FFC107',
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

                st.markdown(f"**{em_o} {mo_name}** — {em_estado} {estado} — {em_esp} {especie_o}{det_str}")

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
                    st.metric("📈 Rend.", f"{rend:.1f}%")
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
                'hechas': 0,
                'no_hechas': 0,
            }
        sd = salas[sala]
        sd['ordenes'].append(mo)
        kg = mo.get('kg_pt', 0) or 0
        dur = mo.get('duracion_horas', 0) or 0
        sd['total_kg'] += kg
        if dur > 0:
            sd['kg_con_duracion'] += kg
            sd['duracion_total'] += dur
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
                                     Paragraph, Image, KeepTogether)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

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
    story.append(Spacer(1, 6*mm))

    # === DETALLE DE ÓRDENES POR SALA ===
    for sala, sd in salas_ordenadas:
        kh_sala = sd['kg_con_duracion'] / sd['duracion_total'] if sd['duracion_total'] > 0 else 0
        story.append(Paragraph(
            f"{sala} — {len(sd['ordenes'])} órdenes — {sd['total_kg']:,.0f} KG — {kh_sala:,.0f} KG/h",
            ParagraphStyle('SalaTitulo', parent=styles['Heading3'],
                           fontSize=10, textColor=azul_corp, spaceBefore=8, spaceAfter=4)
        ))

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
    <div style="background: linear-gradient(135deg, #fafbfc 0%, #f4f5f7 100%);
                padding: 25px; border-radius: 15px; margin-bottom: 20px;
                border-left: 5px solid #D999B2; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <h2 style="margin:0; color:#D999B2;">📊 Comparación de Períodos</h2>
        <p style="margin:5px 0 0 0; color:#666;">
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
        <span style="color: #7FA8C9; font-size: 18px; font-weight: bold;">📅 {lbl_a}  ({dias_a_count} días)</span>
        <span style="color: #888; font-size: 24px; margin: 0 20px; font-weight: bold;">VS</span>
        <span style="color: #D999B2; font-size: 18px; font-weight: bold;">📅 {lbl_b}  ({dias_b_count} días)</span>
    </div>
    """, unsafe_allow_html=True)

    # === KPIs COMPARATIVOS ===
    def _kpi_card(label, icon, val_a_str, val_b_str, diff_str, pct_val, is_positive):
        """Genera HTML de una tarjeta KPI comparativa."""
        diff_color = "#4caf50" if is_positive else "#f44336"
        arrow = "▲" if is_positive else "▼"
        pct_str = f"{pct_val:+.1f}%" if pct_val is not None else "—"
        return (
            '<div style="background:rgba(255,255,255,0.04);border-radius:12px;padding:16px 14px;text-align:center;border:1px solid rgba(255,255,255,0.08);">'
            f'<div style="color:#888;font-size:11px;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px;">{icon} {label}</div>'
            '<div style="display:flex;justify-content:center;align-items:baseline;gap:12px;margin-bottom:6px;">'
            f'<span style="color:#7FA8C9;font-size:26px;font-weight:bold;">{val_a_str}</span>'
            '<span style="color:#555;font-size:14px;">vs</span>'
            f'<span style="color:#D999B2;font-size:18px;font-weight:600;">{val_b_str}</span>'
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
        + '<div style="background:rgba(255,255,255,0.04);border-radius:12px;padding:16px 14px;text-align:center;border:1px solid rgba(255,255,255,0.08);">'
        + '<div style="color:#888;font-size:11px;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px;">⚖️ DIFERENCIA KG</div>'
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
            "textStyle": {"color": "#7FA8C9", "fontSize": 14, "fontWeight": "bold"},
            "subtextStyle": {"color": "#999", "fontSize": 11}
        },
        "tooltip": {
            "trigger": "axis", "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(10,10,30,0.95)", "borderColor": "#555",
            "borderRadius": 10, "textStyle": {"color": "#fff", "fontSize": 13}
        },
        "grid": {"left": "3%", "right": "4%", "bottom": "12%", "top": "18%", "containLabel": True},
        "xAxis": {
            "type": "category", "data": labels_a,
            "axisLabel": {"color": "#fff", "fontSize": 11, "fontWeight": "bold", "interval": 0, "rotate": 25 if len(labels_a) > 10 else 0},
            "axisLine": {"lineStyle": {"color": "#444"}}, "axisTick": {"show": False}
        },
        "yAxis": {
            "type": "value", "name": "KG",
            "nameTextStyle": {"color": "#aaa", "fontSize": 12},
            "axisLabel": {"color": "#ccc", "fontSize": 11},
            "splitLine": {"lineStyle": {"color": "#2a2a4a", "type": "dashed"}}
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
            "textStyle": {"color": "#D999B2", "fontSize": 14, "fontWeight": "bold"},
            "subtextStyle": {"color": "#999", "fontSize": 11}
        },
        "tooltip": {
            "trigger": "axis", "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(10,10,30,0.95)", "borderColor": "#555",
            "borderRadius": 10, "textStyle": {"color": "#fff", "fontSize": 13}
        },
        "grid": {"left": "3%", "right": "4%", "bottom": "12%", "top": "18%", "containLabel": True},
        "xAxis": {
            "type": "category", "data": labels_b,
            "axisLabel": {"color": "#fff", "fontSize": 11, "fontWeight": "bold", "interval": 0, "rotate": 25 if len(labels_b) > 10 else 0},
            "axisLine": {"lineStyle": {"color": "#444"}}, "axisTick": {"show": False}
        },
        "yAxis": {
            "type": "value", "name": "KG",
            "nameTextStyle": {"color": "#aaa", "fontSize": 12},
            "axisLabel": {"color": "#ccc", "fontSize": 11},
            "splitLine": {"lineStyle": {"color": "#2a2a4a", "type": "dashed"}}
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
        <div style="background: rgba(0,212,255,0.12); padding: 10px 15px; border-radius: 10px 10px 0 0;
                    border-left: 4px solid #7FA8C9; font-weight: bold; color: #7FA8C9; font-size: 14px;">
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
                    gap: 8px; padding: 8px 15px; background: rgba(255,255,255,0.03);
                    border-left: 4px solid #7FA8C933; align-items: center; font-size: 13px;">
            <span style="color: #ccc; font-weight: bold;">{dia_label}</span>
            <span style="color: #7FA8C9; font-weight: bold; font-size: 15px;">{kg:,.0f} KG</span>
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
        <div style="background: rgba(224,64,251,0.12); padding: 10px 15px; border-radius: 10px 10px 0 0;
                    border-left: 4px solid #D999B2; font-weight: bold; color: #D999B2; font-size: 14px;">
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
                    gap: 8px; padding: 8px 15px; background: rgba(255,255,255,0.03);
                    border-left: 4px solid #D999B233; align-items: center; font-size: 13px;">
            <span style="color: #ccc; font-weight: bold;">{dia_label}</span>
            <span style="color: #D999B2; font-weight: bold; font-size: 15px;">{kg:,.0f} KG</span>
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
    <div style="background: rgba(255,255,255,0.06); border-radius: 12px; padding: 20px;
                margin-top: 15px; border: 1px solid rgba(255,255,255,0.12);">
        <div style="text-align: center; margin-bottom: 12px; color: #fff; font-size: 16px; font-weight: bold;">
            📊 Conclusión
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; text-align: center;">
            <div>
                <div style="color: #aaa; font-size: 12px;">KG Totales</div>
                <div style="color: {td_color}; font-size: 24px; font-weight: bold;">{td_icon} {td_sign}{total_diff:,.0f}</div>
                <div style="color: #666; font-size: 12px;">{td_pct}</div>
            </div>
            <div>
                <div style="color: #aaa; font-size: 12px;">KG Promedio/Día</div>
                <div style="color: {pd_color}; font-size: 24px; font-weight: bold;">{pd_icon} {pd_sign}{prom_diff:,.0f}</div>
                <div style="color: #666; font-size: 12px;">{prom_dia_a:,.0f} vs {prom_dia_b:,.0f}</div>
            </div>
            <div>
                <div style="color: #aaa; font-size: 12px;">Órdenes</div>
                <div style="color: #fff; font-size: 24px; font-weight: bold;">{ord_a_total} vs {ord_b_total}</div>
                <div style="color: #666; font-size: 12px;">{dias_a_count} vs {dias_b_count} días</div>
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
                "textStyle": {"color": "#fff", "fontSize": 15, "fontWeight": "bold"},
                "subtextStyle": {"color": "#999", "fontSize": 11}
            },
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "shadow"},
                "backgroundColor": "rgba(10, 10, 30, 0.95)",
                "borderColor": "#555",
                "borderRadius": 10,
                "textStyle": {"color": "#fff", "fontSize": 13},
                "extraCssText": "box-shadow: 0 4px 20px rgba(0,0,0,0.5);"
            },
            "legend": {
                "data": [f"📅 {lbl_a}", f"📅 {lbl_b}"],
                "bottom": 0,
                "textStyle": {"color": "#ccc", "fontSize": 12},
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
                    "color": "#fff", "fontSize": 11, "fontWeight": "bold",
                    "rotate": 20 if len(nombres_sala) > 5 else 0,
                    "interval": 0
                },
                "axisLine": {"lineStyle": {"color": "#444", "width": 2}},
                "axisTick": {"show": False}
            },
            "yAxis": {
                "type": "value",
                "name": "⚖️ KG Totales",
                "nameTextStyle": {"color": "#aaa", "fontSize": 13, "fontWeight": "bold"},
                "axisLabel": {"color": "#ccc", "fontSize": 11},
                "splitLine": {"lineStyle": {"color": "#2a2a4a", "type": "dashed"}},
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
                    "textStyle": {"color": "#ffc107", "fontSize": 15, "fontWeight": "bold"},
                    "subtextStyle": {"color": "#999", "fontSize": 11}
                },
                "tooltip": {
                    "trigger": "axis",
                    "axisPointer": {"type": "shadow"},
                    "backgroundColor": "rgba(10, 10, 30, 0.95)",
                    "borderColor": "#ffc107",
                    "borderRadius": 10,
                    "textStyle": {"color": "#fff", "fontSize": 13},
                    "extraCssText": "box-shadow: 0 4px 20px rgba(0,0,0,0.5);",
                    "formatter": JsCode("""
                        function(params) {
                            var result = params[0].name + '<br/>';
                            for (var i = 0; i < params.length; i++) {
                                result += params[i].marker + ' ' + params[i].seriesName + ': ' + 
                                         params[i].value.toLocaleString('en-US') + ' kg/h<br/>';
                            }
                            if (params.length === 2 && params[0].value > 0 && params[1].value > 0) {
                                var diff = params[0].value - params[1].value;
                                var pct = ((diff / params[1].value) * 100).toFixed(1);
                                var color = diff >= 0 ? '#4caf50' : '#f44336';
                                var arrow = diff >= 0 ? '▲' : '▼';
                                result += '<br/><b style="color:' + color + '">' + arrow + ' Diferencia: ' + 
                                         (diff >= 0 ? '+' : '') + diff.toFixed(0) + ' kg/h (' + 
                                         (diff >= 0 ? '+' : '') + pct + '%)</b>';
                            }
                            return result;
                        }
                    """).js_code
                },
                "legend": {
                    "data": [f"📅 {lbl_a}", f"📅 {lbl_b}"],
                    "bottom": 0,
                    "textStyle": {"color": "#ccc", "fontSize": 12},
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
                        "color": "#fff", "fontSize": 11, "fontWeight": "bold",
                        "rotate": 20 if len(nombres_sala_kgh) > 5 else 0,
                        "interval": 0
                    },
                    "axisLine": {"lineStyle": {"color": "#444", "width": 2}},
                    "axisTick": {"show": False}
                },
                "yAxis": {
                    "type": "value",
                    "name": "⚡ KG/Hora",
                    "nameTextStyle": {"color": "#ffc107", "fontSize": 13, "fontWeight": "bold"},
                    "axisLabel": {"color": "#ccc", "fontSize": 11},
                    "splitLine": {"lineStyle": {"color": "#2a2a4a", "type": "dashed"}},
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
                            "formatter": JsCode("function(params){return params.value > 0 ? Math.round(params.value) : '';}").js_code
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
                            "formatter": JsCode("function(params){return params.value > 0 ? Math.round(params.value) : '';}").js_code
                        }
                    }
                ]
            }
            
            st_echarts(options=options_kgh_sala, height="450px", key="comp_kgh_sala_chart")


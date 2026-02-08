"""
Tab KG por Línea: Productividad por sala de proceso.
Muestra KG/Hora de cada orden de forma visual y clara.
"""
import streamlit as st
import httpx
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from streamlit_echarts import st_echarts
from .shared import API_URL


def fetch_datos_produccion(username: str, password: str, fecha_inicio: str, 
                           fecha_fin: str) -> Dict[str, Any]:
    """Obtiene datos de productividad."""
    params = {
        "username": username,
        "password": password,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "solo_terminadas": False  # Incluir todos excepto cancelados
    }
    
    response = httpx.get(f"{API_URL}/api/v1/rendimiento/dashboard",
                         params=params, timeout=120.0)
    response.raise_for_status()
    return response.json()


def render_tarjeta_orden(mo: Dict, idx: int) -> None:
    """Renderiza una tarjeta visual para una orden de producción."""
    
    sala = mo.get('sala', 'Sin Sala')
    producto = mo.get('producto', 'Sin Producto')
    kg_hora = mo.get('kg_por_hora', 0) or 0
    dotacion = mo.get('dotacion', 0) or 0
    hh_efectiva = mo.get('hh_efectiva', 0) or 0
    kg_pt = mo.get('kg_pt', 0) or 0
    nombre = mo.get('nombre', '')
    
    # Horario
    inicio = mo.get('fecha_inicio', '')
    fin = mo.get('fecha_fin', '')
    
    hora_inicio = ""
    hora_fin = ""
    fecha_str = ""
    if inicio:
        try:
            dt_inicio = datetime.fromisoformat(str(inicio).replace('Z', ''))
            hora_inicio = dt_inicio.strftime('%H:%M')
            fecha_str = dt_inicio.strftime('%d/%m')
        except:
            pass
    if fin:
        try:
            dt_fin = datetime.fromisoformat(str(fin).replace('Z', ''))
            hora_fin = dt_fin.strftime('%H:%M')
        except:
            pass
    
    horario = f"{hora_inicio} - {hora_fin}" if hora_inicio and hora_fin else "Sin horario"
    
    # Color según KG/Hora
    if kg_hora >= 800:
        color_kg = "#00D26A"  # Verde - Excelente
        emoji_kg = "🟢"
    elif kg_hora >= 500:
        color_kg = "#FFD93D"  # Amarillo - Bueno
        emoji_kg = "🟡"
    elif kg_hora > 0:
        color_kg = "#FF6B6B"  # Rojo - Bajo
        emoji_kg = "🔴"
    else:
        color_kg = "#666"  # Gris - Sin datos
        emoji_kg = "⚪"
    
    # Tarjeta con estilo
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
        border-left: 5px solid {color_kg};
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    ">
        <!-- Header: Sala y Fecha -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 24px;">🏭</span>
                <span style="color: #00D9FF; font-size: 18px; font-weight: bold;">{sala}</span>
            </div>
            <div style="color: #888; font-size: 14px;">
                📅 {fecha_str} &nbsp; ⏰ {horario}
            </div>
        </div>
        
        <!-- Producto -->
        <div style="color: #ccc; font-size: 13px; margin-bottom: 15px; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 8px;">
            📦 {producto[:50]}{'...' if len(producto) > 50 else ''}
        </div>
        
        <!-- KPIs en fila -->
        <div style="display: flex; justify-content: space-around; text-align: center;">
            <!-- KG/HORA - Principal -->
            <div style="flex: 1.5;">
                <div style="color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">KG/Hora</div>
                <div style="color: {color_kg}; font-size: 42px; font-weight: bold; line-height: 1.2;">
                    {kg_hora:,.0f}
                </div>
                <div style="font-size: 18px;">{emoji_kg}</div>
            </div>
            
            <!-- Separador -->
            <div style="width: 1px; background: #333; margin: 0 15px;"></div>
            
            <!-- Dotación -->
            <div style="flex: 1;">
                <div style="color: #888; font-size: 11px; text-transform: uppercase;">Dotación</div>
                <div style="color: #FFD93D; font-size: 28px; font-weight: bold;">
                    {dotacion}
                </div>
                <div style="color: #666; font-size: 11px;">personas</div>
            </div>
            
            <!-- Separador -->
            <div style="width: 1px; background: #333; margin: 0 15px;"></div>
            
            <!-- Horas Efectivas -->
            <div style="flex: 1;">
                <div style="color: #888; font-size: 11px; text-transform: uppercase;">HH Efectivas</div>
                <div style="color: #00D9FF; font-size: 28px; font-weight: bold;">
                    {hh_efectiva:.1f}
                </div>
                <div style="color: #666; font-size: 11px;">horas</div>
            </div>
            
            <!-- Separador -->
            <div style="width: 1px; background: #333; margin: 0 15px;"></div>
            
            <!-- KG Producidos -->
            <div style="flex: 1;">
                <div style="color: #888; font-size: 11px; text-transform: uppercase;">KG Producidos</div>
                <div style="color: #00D26A; font-size: 28px; font-weight: bold;">
                    {kg_pt:,.0f}
                </div>
                <div style="color: #666; font-size: 11px;">kilos</div>
            </div>
        </div>
        
        <!-- Orden ID pequeño -->
        <div style="color: #555; font-size: 10px; text-align: right; margin-top: 10px;">
            {nombre}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_grafico_barras_kg_hora(mos: List[Dict]) -> None:
    """Gráfico de barras mostrando KG/Hora de cada orden."""
    if not mos:
        return
    
    # Filtrar y preparar datos
    datos = []
    for mo in mos:
        kg_hora = mo.get('kg_por_hora', 0) or 0
        if kg_hora > 0:
            sala = mo.get('sala', 'Sin Sala')[:20]
            fecha = ""
            inicio = mo.get('fecha_inicio', '')
            if inicio:
                try:
                    dt = datetime.fromisoformat(str(inicio).replace('Z', ''))
                    fecha = dt.strftime('%d/%m %H:%M')
                except:
                    pass
            
            label = f"{sala} ({fecha})"
            datos.append({
                'label': label,
                'kg_hora': kg_hora,
                'sala': sala
            })
    
    if not datos:
        st.info("No hay órdenes con KG/Hora registrado")
        return
    
    # Ordenar por KG/Hora descendente y tomar top 15
    datos = sorted(datos, key=lambda x: x['kg_hora'], reverse=True)[:15]
    datos = datos[::-1]  # Invertir para que el mayor quede arriba
    
    labels = [d['label'] for d in datos]
    valores = [d['kg_hora'] for d in datos]
    
    # Colores según valor
    colores = []
    for v in valores:
        if v >= 800:
            colores.append('#00D26A')
        elif v >= 500:
            colores.append('#FFD93D')
        else:
            colores.append('#FF6B6B')
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{b}<br/>⚡ <b>{c}</b> KG/Hora"
        },
        "grid": {
            "left": "3%",
            "right": "15%",
            "bottom": "3%",
            "top": "3%",
            "containLabel": True
        },
        "xAxis": {
            "type": "value",
            "name": "KG/Hora",
            "nameLocation": "middle",
            "nameGap": 30,
            "axisLabel": {"color": "#888"},
            "splitLine": {"lineStyle": {"color": "#333"}}
        },
        "yAxis": {
            "type": "category",
            "data": labels,
            "axisLabel": {"color": "#ccc", "fontSize": 11},
            "axisLine": {"lineStyle": {"color": "#555"}}
        },
        "series": [{
            "type": "bar",
            "data": [{"value": v, "itemStyle": {"color": c}} for v, c in zip(valores, colores)],
            "barWidth": "60%",
            "label": {
                "show": True,
                "position": "right",
                "formatter": "{c}",
                "color": "#fff",
                "fontWeight": "bold",
                "fontSize": 14
            }
        }]
    }
    
    st_echarts(options=options, height="500px")


def render_resumen_por_sala(mos: List[Dict]) -> None:
    """Resumen consolidado por sala."""
    if not mos:
        return
    
    # Agrupar por sala
    salas = {}
    for mo in mos:
        sala = mo.get('sala', 'Sin Sala')
        kg_hora = mo.get('kg_por_hora', 0) or 0
        kg_pt = mo.get('kg_pt', 0) or 0
        
        if sala not in salas:
            salas[sala] = {'ordenes': 0, 'kg_total': 0, 'kg_hora_sum': 0, 'kg_hora_count': 0}
        
        salas[sala]['ordenes'] += 1
        salas[sala]['kg_total'] += kg_pt
        if kg_hora > 0:
            salas[sala]['kg_hora_sum'] += kg_hora
            salas[sala]['kg_hora_count'] += 1
    
    # Crear tabla
    filas = []
    for sala, data in salas.items():
        kg_hora_prom = data['kg_hora_sum'] / data['kg_hora_count'] if data['kg_hora_count'] > 0 else 0
        filas.append({
            'Sala': sala,
            'Órdenes': data['ordenes'],
            'KG Producidos': f"{data['kg_total']:,.0f}",
            'KG/Hora Promedio': f"{kg_hora_prom:,.0f}"
        })
    
    # Ordenar por KG/Hora
    filas = sorted(filas, key=lambda x: float(x['KG/Hora Promedio'].replace(',', '')), reverse=True)
    
    df = pd.DataFrame(filas)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render(username: str = None, password: str = None):
    """Render principal del tab KG por Línea."""
    
    # Obtener credenciales
    if not username:
        username = st.session_state.get("username", "")
    if not password:
        password = st.session_state.get("password", "")
    
    if not username or not password:
        st.warning("⚠️ Debes iniciar sesión para ver este módulo")
        return
    
    # === HEADER ===
    st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h2 style="color: #00D9FF; margin-bottom: 5px;">⚡ Productividad por Línea</h2>
        <p style="color: #888;">Visualiza los KG/Hora de cada orden de producción por sala</p>
    </div>
    """, unsafe_allow_html=True)
    
    # === LEYENDA DE COLORES ===
    st.markdown("""
    <div style="display: flex; justify-content: center; gap: 30px; margin-bottom: 20px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 10px;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="color: #00D26A; font-size: 20px;">●</span>
            <span style="color: #aaa;">Excelente (≥800 kg/h)</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="color: #FFD93D; font-size: 20px;">●</span>
            <span style="color: #aaa;">Bueno (500-799 kg/h)</span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="color: #FF6B6B; font-size: 20px;">●</span>
            <span style="color: #aaa;">Bajo (&lt;500 kg/h)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # === FILTROS ===
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
        filtro_sala = st.text_input(
            "🔍 Filtrar Sala",
            placeholder="Ej: Sala 3, Tunel...",
            key="kg_linea_filtro_sala"
        )
    
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        btn_buscar = st.button("🔍 Buscar", type="primary", use_container_width=True)
    
    st.markdown("---")
    
    # === CARGAR DATOS ===
    if btn_buscar or st.session_state.get("kg_linea_datos"):
        if btn_buscar:
            try:
                with st.spinner("Cargando datos de producción..."):
                    datos = fetch_datos_produccion(
                        username, password,
                        fecha_inicio.isoformat(),
                        fecha_fin.isoformat()
                    )
                    st.session_state["kg_linea_datos"] = datos
            except Exception as e:
                st.error(f"Error al cargar datos: {str(e)}")
                return
        
        datos = st.session_state.get("kg_linea_datos", {})
        mos = datos.get("mos", [])
        
        if not mos:
            st.warning("No se encontraron órdenes de producción en el período seleccionado")
            return
        
        # Aplicar filtro de sala si existe
        if filtro_sala:
            mos = [mo for mo in mos if filtro_sala.lower() in (mo.get('sala', '') or '').lower()]
        
        # === KPIs GENERALES ===
        total_ordenes = len(mos)
        total_kg = sum(mo.get('kg_pt', 0) or 0 for mo in mos)
        kg_hora_values = [mo.get('kg_por_hora', 0) or 0 for mo in mos if (mo.get('kg_por_hora', 0) or 0) > 0]
        kg_hora_prom = sum(kg_hora_values) / len(kg_hora_values) if kg_hora_values else 0
        salas_unicas = len(set(mo.get('sala', '') for mo in mos if mo.get('sala')))
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📋 Órdenes", f"{total_ordenes:,}")
        with col2:
            st.metric("📦 KG Producidos", f"{total_kg:,.0f}")
        with col3:
            st.metric("⚡ KG/Hora Promedio", f"{kg_hora_prom:,.0f}")
        with col4:
            st.metric("🏭 Líneas Activas", f"{salas_unicas}")
        
        st.markdown("---")
        
        # === GRÁFICO DE BARRAS ===
        st.markdown("### 📊 Ranking de KG/Hora por Orden")
        st.caption("Las barras más largas indican mayor productividad. Cada barra es una orden de producción.")
        render_grafico_barras_kg_hora(mos)
        
        st.markdown("---")
        
        # === RESUMEN POR SALA ===
        st.markdown("### 🏭 Resumen por Sala")
        render_resumen_por_sala(mos)
        
        st.markdown("---")
        
        # === TARJETAS INDIVIDUALES ===
        st.markdown("### 📋 Detalle de Cada Orden")
        st.caption("Cada tarjeta muestra los datos completos de una orden de producción")
        
        # Ordenar por fecha de inicio descendente
        mos_ordenadas = sorted(mos, key=lambda x: x.get('fecha_inicio', '') or '', reverse=True)
        
        # Mostrar en grid de 2 columnas
        for i in range(0, len(mos_ordenadas), 2):
            col1, col2 = st.columns(2)
            
            with col1:
                if i < len(mos_ordenadas):
                    render_tarjeta_orden(mos_ordenadas[i], i)
            
            with col2:
                if i + 1 < len(mos_ordenadas):
                    render_tarjeta_orden(mos_ordenadas[i + 1], i + 1)
    
    else:
        # Estado inicial
        st.info("👆 Selecciona el rango de fechas y presiona **Buscar** para ver la productividad por línea")

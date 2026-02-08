"""
Tab KG por Línea: Rendimiento por sala de proceso, agrupado por día.
Muestra cada proceso individual con todos sus datos.
"""
import streamlit as st
import httpx
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
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


def parsear_fecha_hora(fecha_str: str) -> Optional[datetime]:
    """Parsea fecha/hora de diferentes formatos."""
    if not fecha_str:
        return None
    try:
        if 'T' in str(fecha_str):
            return datetime.fromisoformat(str(fecha_str).replace('Z', ''))
        else:
            return datetime.strptime(str(fecha_str)[:19], '%Y-%m-%d %H:%M:%S')
    except:
        return None


def formatear_hora(dt: Optional[datetime]) -> str:
    """Formatea datetime a HH:MM."""
    if not dt:
        return "-"
    return dt.strftime("%H:%M")


def formatear_duracion(inicio: Optional[datetime], fin: Optional[datetime]) -> str:
    """Calcula y formatea duración."""
    if not inicio or not fin:
        return "-"
    duracion = fin - inicio
    horas = duracion.total_seconds() / 3600
    h = int(horas)
    m = int((horas - h) * 60)
    return f"{h}h {m}m"


def render(username: str = None, password: str = None):
    """Render principal del tab KG por Línea."""
    
    # Obtener credenciales
    if not username:
        username = st.session_state.get("odoo_username", "")
    if not password:
        password = st.session_state.get("odoo_api_key", "")
    
    if not username or not password:
        st.warning("⚠️ Debes iniciar sesión para ver este módulo")
        return
    
    # === HEADER ===
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                padding: 25px; border-radius: 15px; margin-bottom: 25px;
                border-left: 5px solid #00d4ff;">
        <h2 style="margin:0; color:#00d4ff;">📊 Rendimiento por Línea de Proceso</h2>
        <p style="margin:5px 0 0 0; color:#aaa; font-size:14px;">
            Visualiza el KG/Hora de cada sala, desglosado por día y por orden de producción
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # === FILTROS ===
    col1, col2, col3 = st.columns([1, 1, 1])
    
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
        btn_buscar = st.button("🔍 Buscar", type="primary", use_container_width=True)
    
    # === CARGAR DATOS ===
    if btn_buscar or st.session_state.get("kg_linea_data"):
        if btn_buscar:
            with st.spinner("Cargando datos de producción..."):
                try:
                    data = fetch_datos_produccion(
                        username, password,
                        fecha_inicio.isoformat(),
                        fecha_fin.isoformat()
                    )
                    st.session_state["kg_linea_data"] = data
                except Exception as e:
                    st.error(f"Error al cargar datos: {e}")
                    return
        
        data = st.session_state.get("kg_linea_data", {})
        mos = data.get("mos", [])
        
        if not mos:
            st.info("No hay órdenes de producción en el rango seleccionado")
            return
        
        # === PROCESAR Y AGRUPAR POR DÍA Y SALA ===
        por_dia_sala = defaultdict(lambda: defaultdict(list))
        
        for mo in mos:
            # Parsear fecha de inicio (campos del backend: fecha_inicio, fecha_termino)
            inicio_str = mo.get('fecha_inicio') or mo.get('inicio_proceso')
            inicio_dt = parsear_fecha_hora(inicio_str)
            
            # Si no tiene fecha de inicio, usar la fecha general
            if not inicio_dt:
                fecha_str = mo.get('fecha', '')
                if fecha_str:
                    try:
                        inicio_dt = datetime.strptime(fecha_str[:10], '%Y-%m-%d')
                    except:
                        continue
                else:
                    continue
            
            fecha_dia = inicio_dt.strftime("%Y-%m-%d")
            sala = mo.get('sala', '') or mo.get('sala_original', '') or 'Sin Sala'
            
            # Parsear fecha fin
            fin_str = mo.get('fecha_termino') or mo.get('fin_proceso')
            fin_dt = parsear_fecha_hora(fin_str)
            
            # Obtener KG/Hora (campo de Odoo)
            kg_hora = mo.get('kg_hora_efectiva') or mo.get('kg_por_hora') or 0
            
            proceso_info = {
                'nombre': mo.get('mo_name', mo.get('name', '-')),
                'producto': mo.get('product_name', mo.get('producto', '-')),
                'inicio_dt': inicio_dt,
                'fin_dt': fin_dt,
                'hora_inicio': formatear_hora(inicio_dt),
                'hora_fin': formatear_hora(fin_dt),
                'duracion': formatear_duracion(inicio_dt, fin_dt),
                'kg_hora': round(kg_hora, 1) if kg_hora else 0,
                'kg_hh': round(mo.get('kg_hh_efectiva', 0) or 0, 1),
                'dotacion': mo.get('dotacion', 0) or 0,
                'hh_efectiva': round(mo.get('hh_efectiva', 0) or 0, 2),
                'kg_producidos': round(mo.get('kg_pt', 0) or mo.get('kg_producidos', 0) or 0, 1),
                'estado': mo.get('state', '-')
            }
            
            por_dia_sala[fecha_dia][sala].append(proceso_info)
        
        # Ordenar días de más reciente a más antiguo
        dias_ordenados = sorted(por_dia_sala.keys(), reverse=True)
        
        # === KPIs GENERALES ===
        total_procesos = sum(len(p) for sala in por_dia_sala.values() for p in sala.values())
        total_kg = sum(p['kg_producidos'] for sala in por_dia_sala.values() for procs in sala.values() for p in procs)
        kg_horas_validos = [p['kg_hora'] for sala in por_dia_sala.values() for procs in sala.values() for p in procs if p['kg_hora'] > 0]
        promedio_kg_hora = sum(kg_horas_validos) / len(kg_horas_validos) if kg_horas_validos else 0
        salas_unicas = set(sala for dia in por_dia_sala.values() for sala in dia.keys())
        
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 20px; border-radius: 12px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{total_procesos}</div>
                <div style="color: rgba(255,255,255,0.8); font-size: 12px;">ÓRDENES DE PRODUCCIÓN</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                        padding: 20px; border-radius: 12px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{total_kg:,.0f}</div>
                <div style="color: rgba(255,255,255,0.8); font-size: 12px;">KG PRODUCIDOS</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        padding: 20px; border-radius: 12px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{promedio_kg_hora:,.0f}</div>
                <div style="color: rgba(255,255,255,0.8); font-size: 12px;">KG/HORA PROMEDIO</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                        padding: 20px; border-radius: 12px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{len(salas_unicas)}</div>
                <div style="color: rgba(255,255,255,0.8); font-size: 12px;">LÍNEAS ACTIVAS</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # === MOSTRAR POR CADA DÍA ===
        for fecha_dia in dias_ordenados:
            salas_del_dia = por_dia_sala[fecha_dia]
            
            # Formatear fecha legible
            fecha_dt = datetime.strptime(fecha_dia, "%Y-%m-%d")
            dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            dia_semana = dias_semana[fecha_dt.weekday()]
            mes = meses[fecha_dt.month - 1]
            fecha_display = f"{dia_semana} {fecha_dt.day} de {mes}, {fecha_dt.year}"
            
            # Calcular totales del día
            procesos_dia = sum(len(procs) for procs in salas_del_dia.values())
            kg_dia = sum(p['kg_producidos'] for procs in salas_del_dia.values() for p in procs)
            
            # Header del día
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
                        padding: 15px 20px; border-radius: 10px; margin: 20px 0 15px 0;
                        display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 22px; font-weight: bold; color: white;">📅 {fecha_display}</span>
                </div>
                <div style="text-align: right;">
                    <span style="color: #90caf9; font-size: 14px; margin-right: 20px;">
                        📦 {procesos_dia} órdenes
                    </span>
                    <span style="color: #a5d6a7; font-size: 14px;">
                        ⚖️ {kg_dia:,.0f} KG
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Ordenar salas por total de KG/Hora
            salas_ordenadas = sorted(
                salas_del_dia.items(),
                key=lambda x: sum(p['kg_hora'] for p in x[1]) / len(x[1]) if x[1] else 0,
                reverse=True
            )
            
            # === POR CADA SALA DEL DÍA ===
            for sala, procesos in salas_ordenadas:
                # Ordenar procesos por hora de inicio
                procesos_ordenados = sorted(procesos, key=lambda x: x['inicio_dt'] or datetime.min)
                
                # Calcular promedio de la sala en el día
                kg_horas_sala = [p['kg_hora'] for p in procesos_ordenados if p['kg_hora'] > 0]
                promedio_sala = sum(kg_horas_sala) / len(kg_horas_sala) if kg_horas_sala else 0
                
                # Color según rendimiento
                if promedio_sala >= 2000:
                    color_sala = "#4caf50"  # Verde - Excelente
                    emoji = "🟢"
                elif promedio_sala >= 1500:
                    color_sala = "#8bc34a"  # Verde claro - Bueno
                    emoji = "🟡"
                elif promedio_sala >= 1000:
                    color_sala = "#ff9800"  # Naranja - Regular
                    emoji = "🟠"
                else:
                    color_sala = "#f44336"  # Rojo - Bajo
                    emoji = "🔴"
                
                with st.expander(f"{emoji} **{sala}** — Promedio: **{promedio_sala:,.0f} KG/Hora** — {len(procesos_ordenados)} procesos", expanded=True):
                    
                    # Usar DataFrame de pandas para mejor visualización
                    datos_tabla = []
                    for proc in procesos_ordenados:
                        datos_tabla.append({
                            "🏭 Proceso": proc['nombre'],
                            "📦 Producto": proc['producto'][:40] if len(proc['producto']) > 40 else proc['producto'],
                            "🕐 Inicio": proc['hora_inicio'],
                            "🕕 Fin": proc['hora_fin'],
                            "⏱️ Duración": proc['duracion'],
                            "👷 Dotación": int(proc['dotacion']),
                            "⚡ KG/Hora": int(proc['kg_hora']),
                            "📊 KG/HH": int(proc['kg_hh']),
                            "⚖️ KG Prod.": int(proc['kg_producidos'])
                        })
                    
                    if datos_tabla:
                        df = pd.DataFrame(datos_tabla)
                        
                        # Estilo del dataframe
                        st.dataframe(
                            df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "⚡ KG/Hora": st.column_config.NumberColumn(
                                    "⚡ KG/Hora",
                                    help="Kilogramos por hora efectiva",
                                    format="%d"
                                ),
                                "⚖️ KG Prod.": st.column_config.NumberColumn(
                                    "⚖️ KG Prod.",
                                    help="Kilogramos producidos",
                                    format="%d"
                                ),
                            }
                        )
                    
                    # Mini resumen de la sala
                    total_kg_sala = sum(p['kg_producidos'] for p in procesos_ordenados)
                    dotacion_prom = sum(p['dotacion'] for p in procesos_ordenados) / len(procesos_ordenados) if procesos_ordenados else 0
                    
                    col_r1, col_r2, col_r3 = st.columns(3)
                    with col_r1:
                        st.metric("📊 Total KG", f"{total_kg_sala:,.0f}")
                    with col_r2:
                        st.metric("👷 Dotación Prom", f"{dotacion_prom:.0f}")
                    with col_r3:
                        st.metric("⚡ KG/Hora Prom", f"{promedio_sala:,.0f}")
            
            st.markdown("<br>", unsafe_allow_html=True)

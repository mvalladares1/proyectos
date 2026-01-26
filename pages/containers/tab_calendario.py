"""
Tab de Calendario de Pedidos - Vista Timeline/Gantt/Semanal/Diaria
Visualización modular y optimizada de todos los pedidos con avance, cliente, fruta y sala.
Diseño modular con componentes reutilizables y API optimizada.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import calendar

from .shared import (
    STATE_OPTIONS, API_URL,
    get_sale_state_display,
    get_odoo_link
)
import httpx


# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

CAPACIDAD_DIARIA_SALA = 50000  # KG por día por sala
DIAS_URGENTE = 7
DIAS_CRITICO = 3

COLORES_FRUTA = {
    "frambuesa": "#e74c3c",
    "arándano": "#3498db", 
    "mora": "#9b59b6",
    "frutilla": "#e91e63",
    "cereza": "#c0392b",
    "default": "#95a5a6"
}


# ============================================================================
# FUNCIONES DE DATOS (API)
# ============================================================================

def fetch_all_pedidos(username: str, password: str, start_date: str, end_date: str) -> List[Dict]:
    """Obtiene todos los pedidos para vista calendario (optimizado)."""
    try:
        params = {
            "username": username,
            "password": password,
            "start_date": start_date,
            "end_date": end_date
        }
        
        response = httpx.get(
            f"{API_URL}/api/v1/containers/proyecciones",
            params=params,
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener pedidos: {str(e)}")
        return []


# ============================================================================
# UTILIDADES DE PROCESAMIENTO
# ============================================================================

def extraer_tipo_fruta(producto_nombre: str) -> str:
    """Extrae el tipo de fruta del nombre del producto."""
    producto_lower = producto_nombre.lower()
    
    if "framb" in producto_lower:
        return "frambuesa"
    elif "arán" in producto_lower or "blue" in producto_lower:
        return "arándano"
    elif "mora" in producto_lower or "black" in producto_lower:
        return "mora"
    elif "frutilla" in producto_lower or "fresa" in producto_lower:
        return "frutilla"
    elif "cerez" in producto_lower or "cherry" in producto_lower:
        return "cereza"
    
    return "default"


def get_color_fruta(tipo_fruta: str) -> str:
    """Retorna color según tipo de fruta."""
    return COLORES_FRUTA.get(tipo_fruta, COLORES_FRUTA["default"])


def get_color_avance(avance: float) -> str:
    """Retorna color según porcentaje de avance."""
    if avance >= 100:
        return "#2ecc71"  # Verde
    elif avance >= 75:
        return "#3498db"  # Azul
    elif avance >= 50:
        return "#f39c12"  # Naranja
    elif avance >= 25:
        return "#e67e22"  # Naranja oscuro
    else:
        return "#e74c3c"  # Rojo


def get_producto_principal(lineas: List[Dict]) -> Tuple[str, str]:
    """
    Extrae el producto principal y su tipo de fruta.
    Returns: (nombre_producto, tipo_fruta)
    """
    if not lineas:
        return "Sin producto", "default"
    
    # Línea con mayor cantidad
    linea_principal = max(lineas, key=lambda x: x.get("product_uom_qty", 0))
    prod = linea_principal.get("product_id", {})
    
    if isinstance(prod, dict):
        nombre = prod.get("name", "N/A")
    elif isinstance(prod, (list, tuple)) and len(prod) > 1:
        nombre = prod[1]
    else:
        nombre = "N/A"
    
    tipo_fruta = extraer_tipo_fruta(nombre)
    return nombre, tipo_fruta


def get_sala_proceso(productions: List[Dict]) -> str:
    """Extrae la sala de proceso de las fabricaciones."""
    if not productions:
        return "Sin asignar"
    
    salas = set()
    for prod in productions:
        sala = prod.get("sala_proceso", "")
        if sala and sala != "N/A" and sala != "False":
            salas.add(sala)
    
    return ", ".join(sorted(salas)) if salas else "Sin asignar"


def calcular_urgencia(fecha_entrega: datetime) -> Tuple[str, str, int]:
    """
    Calcula nivel de urgencia.
    Returns: (nivel, emoji, dias_restantes)
    """
    dias = (fecha_entrega.replace(tzinfo=None) - datetime.now()).days
    
    if dias < 0:
        return "atrasado", "🔴", dias
    elif dias <= DIAS_CRITICO:
        return "critico", "⚡", dias
    elif dias <= DIAS_URGENTE:
        return "urgente", "🟡", dias
    else:
        return "normal", "🟢", dias


def parse_fecha(fecha_str: any) -> Optional[datetime]:
    """Parse seguro de fechas."""
    if not fecha_str:
        return None
    
    try:
        if 'T' in str(fecha_str):
            return datetime.fromisoformat(str(fecha_str).replace('Z', '+00:00'))
        else:
            return datetime.strptime(str(fecha_str)[:10], '%Y-%m-%d')
    except:
        return None


def procesar_pedidos(pedidos_raw: List[Dict]) -> List[Dict]:
    """
    Procesa pedidos raw agregando campos calculados.
    Optimizado para evitar recalcular en cada vista.
    """
    pedidos_procesados = []
    
    for p in pedidos_raw:
        # Fechas
        fecha_entrega = parse_fecha(p.get("commitment_date") or p.get("date_order"))
        if not fecha_entrega:
            continue
        
        # Producto y fruta
        producto_nombre, tipo_fruta = get_producto_principal(p.get("lineas", []))
        
        # Sala
        sala = get_sala_proceso(p.get("productions", []))
        
        # Urgencia
        nivel_urgencia, emoji_urgencia, dias_restantes = calcular_urgencia(fecha_entrega)
        
        # KGs
        kg_total = p.get("kg_total", 0)
        kg_producidos = p.get("kg_producidos", 0)
        avance = p.get("avance_pct", 0)
        
        # Estimar fecha inicio (5000 kg/día de capacidad estimada)
        dias_estimados = max(1, int(kg_total / 5000))
        fecha_inicio_estimada = fecha_entrega - timedelta(days=dias_estimados)
        
        pedidos_procesados.append({
            **p,  # Datos originales
            "_fecha_entrega": fecha_entrega,
            "_fecha_inicio_estimada": fecha_inicio_estimada,
            "_producto_nombre": producto_nombre,
            "_tipo_fruta": tipo_fruta,
            "_sala": sala,
            "_nivel_urgencia": nivel_urgencia,
            "_emoji_urgencia": emoji_urgencia,
            "_dias_restantes": dias_restantes,
            "_color_fruta": get_color_fruta(tipo_fruta),
            "_color_avance": get_color_avance(avance)
        })
    
    return pedidos_procesados


# ============================================================================
# CÁLCULOS Y MÉTRICAS
# ============================================================================

def calcular_kpis(pedidos: List[Dict]) -> Dict:
    """Calcula KPIs principales."""
    if not pedidos:
        return {
            "total_pedidos": 0,
            "kg_total": 0,
            "kg_producidos": 0,
            "avance_global": 0,
            "clientes_unicos": 0,
            "pedidos_criticos": 0,
            "pedidos_atrasados": 0,
            "carga_semanal": 0,
            "capacidad_disponible": 0
        }
    
    total_pedidos = len(pedidos)
    kg_total = sum(p.get("kg_total", 0) for p in pedidos)
    kg_producidos = sum(p.get("kg_producidos", 0) for p in pedidos)
    avance_global = (kg_producidos / kg_total * 100) if kg_total > 0 else 0
    clientes_unicos = len(set(p.get("partner_name", "N/A") for p in pedidos))
    
    # Pedidos críticos y atrasados
    pedidos_criticos = len([p for p in pedidos if p.get("_nivel_urgencia") in ["critico", "urgente"]])
    pedidos_atrasados = len([p for p in pedidos if p.get("_nivel_urgencia") == "atrasado"])
    
    # Carga semanal (próximos 7 días)
    hoy = datetime.now()
    proxima_semana = hoy + timedelta(days=7)
    
    kg_semana = sum(
        p.get("kg_total", 0) 
        for p in pedidos 
        if p.get("_fecha_entrega") and hoy <= p["_fecha_entrega"] <= proxima_semana
    )
    
    # Capacidad disponible estimada (50t/día * 7 días * 2 salas = 700t)
    capacidad_semanal = CAPACIDAD_DIARIA_SALA * 7 * 2
    capacidad_disponible = max(0, capacidad_semanal - kg_semana)
    
    return {
        "total_pedidos": total_pedidos,
        "kg_total": kg_total,
        "kg_producidos": kg_producidos,
        "avance_global": avance_global,
        "clientes_unicos": clientes_unicos,
        "pedidos_criticos": pedidos_criticos,
        "pedidos_atrasados": pedidos_atrasados,
        "carga_semanal": kg_semana,
        "capacidad_disponible": capacidad_disponible
    }


def aplicar_filtros(pedidos: List[Dict], filtros: Dict) -> List[Dict]:
    """Aplica filtros dinámicos a los pedidos."""
    filtrados = pedidos.copy()
    
    if filtros.get("clientes"):
        filtrados = [p for p in filtrados if p.get("partner_name") in filtros["clientes"]]
    
    if filtros.get("productos"):
        filtrados = [p for p in filtrados if p.get("_tipo_fruta") in filtros["productos"]]
    
    if filtros.get("salas"):
        filtrados = [p for p in filtrados if p.get("_sala") in filtros["salas"]]
    
    if filtros.get("solo_atrasados"):
        filtrados = [p for p in filtrados if p.get("_nivel_urgencia") == "atrasado"]
    
    if filtros.get("solo_urgentes"):
        filtrados = [p for p in filtrados if p.get("_nivel_urgencia") in ["critico", "urgente", "atrasado"]]
    
    return filtrados


# ============================================================================
# COMPONENTES DE UI
# ============================================================================

def render_kpis(kpis: Dict):
    """Renderiza fila de KPIs principales."""
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("📋 Pedidos", f"{kpis['total_pedidos']:,}")
    
    with col2:
        st.metric("📦 KG Total", f"{kpis['kg_total']/1000:,.1f}t")
    
    with col3:
        st.metric("📊 Carga Sem.", f"{kpis['carga_semanal']/1000:,.1f}t")
    
    with col4:
        delta_cap = kpis['capacidad_disponible'] / 1000
        st.metric("🏭 Cap. Disp.", f"{delta_cap:,.1f}t", 
                 delta=f"{delta_cap:,.1f}t disp.", delta_color="normal")
    
    with col5:
        st.metric("⚡ Críticos", kpis['pedidos_criticos'], 
                 delta=None if kpis['pedidos_criticos'] == 0 else "Atención", 
                 delta_color="inverse")
    
    with col6:
        st.metric("🔴 Atrasados", kpis['pedidos_atrasados'],
                 delta=None if kpis['pedidos_atrasados'] == 0 else "Urgente",
                 delta_color="inverse")


def render_filtros(pedidos: List[Dict]) -> Dict:
    """Renderiza panel de filtros y retorna filtros seleccionados."""
    st.markdown("### 🔍 Filtros")
    
    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 2])
    
    # Extraer opciones únicas
    clientes = sorted(set(p.get("partner_name", "N/A") for p in pedidos))
    frutas = sorted(set(p.get("_tipo_fruta", "default") for p in pedidos))
    salas = sorted(set(p.get("_sala", "Sin asignar") for p in pedidos))
    
    with col_f1:
        filtro_clientes = st.multiselect(
            "Cliente",
            options=clientes,
            key="cal_filtro_clientes"
        )
    
    with col_f2:
        filtro_productos = st.multiselect(
            "Tipo Fruta",
            options=frutas,
            format_func=lambda x: x.capitalize(),
            key="cal_filtro_productos"
        )
    
    with col_f3:
        filtro_salas = st.multiselect(
            "Sala Proceso",
            options=salas,
            key="cal_filtro_salas"
        )
    
    with col_f4:
        col_toggle1, col_toggle2 = st.columns(2)
        with col_toggle1:
            solo_urgentes = st.checkbox("⚡ Solo Urgentes", key="cal_solo_urgentes")
        with col_toggle2:
            solo_atrasados = st.checkbox("🔴 Solo Atrasados", key="cal_solo_atrasados")
    
    return {
        "clientes": filtro_clientes,
        "productos": filtro_productos,
        "salas": filtro_salas,
        "solo_urgentes": solo_urgentes,
        "solo_atrasados": solo_atrasados
    }


def render_gantt_chart(pedidos: List[Dict]):
    """Renderiza vista Gantt/Timeline."""
    if not pedidos:
        st.info("No hay pedidos para mostrar")
        return
    
    st.markdown("### 📊 Timeline de Pedidos")
    
    # Ordenar por fecha de entrega
    pedidos_ordenados = sorted(pedidos, key=lambda x: x["_fecha_entrega"])
    
    fig = go.Figure()
    
    for p in pedidos_ordenados:
        nombre_display = f"{p.get('name', 'N/A')} - {p.get('partner_name', 'N/A')[:25]}"
        
        # Barra base (gris claro - tiempo total estimado)
        # Convertir a timestamps para que plotly pueda serializar
        fecha_inicio_ts = p["_fecha_inicio_estimada"].timestamp() * 1000
        fecha_fin_ts = p["_fecha_entrega"].timestamp() * 1000
        
        fig.add_trace(go.Bar(
            name="",
            x=[fecha_fin_ts - fecha_inicio_ts],
            y=[nombre_display],
            base=fecha_inicio_ts,
            orientation='h',
            marker=dict(
                color='rgba(200, 200, 200, 0.3)',
                line=dict(color=p["_color_fruta"], width=2)
            ),
            showlegend=False,
            hovertemplate=(
                f"<b>{p.get('name')}</b><br>"
                f"Cliente: {p.get('partner_name')}<br>"
                f"🍇 {p['_producto_nombre'][:40]}<br>"
                f"🏭 {p['_sala']}<br>"
                f"📦 {p.get('kg_total', 0):,.0f} kg<br>"
                f"Entrega: {p['_fecha_entrega'].strftime('%d/%m/%Y')}<br>"
                f"{p['_emoji_urgencia']} {p['_dias_restantes']} días<br>"
                "<extra></extra>"
            )
        ))
        
        # Barra de avance (color según tipo de fruta)
        avance_pct = p.get("avance_pct", 0) / 100
        if avance_pct > 0:
            duracion_avance = (fecha_fin_ts - fecha_inicio_ts) * avance_pct
            
            fig.add_trace(go.Bar(
                name="",
                x=[duracion_avance],
                y=[nombre_display],
                base=fecha_inicio_ts,
                orientation='h',
                marker=dict(color=p["_color_fruta"]),
                showlegend=False,
                hovertemplate=(
                    f"Avance: {p.get('avance_pct', 0):.1f}%<br>"
                    f"Producidos: {p.get('kg_producidos', 0):,.0f} kg<br>"
                    "<extra></extra>"
                )
            ))
        
        # Marcador de urgencia si aplica
        if p["_nivel_urgencia"] in ["critico", "atrasado"]:
            fig.add_trace(go.Scatter(
                x=[fecha_fin_ts],
                y=[nombre_display],
                mode='markers',
                marker=dict(
                    symbol='diamond',
                    size=12,
                    color='red',
                    line=dict(color='darkred', width=2)
                ),
                showlegend=False,
                hovertemplate=f"{p['_emoji_urgencia']} {p['_nivel_urgencia'].upper()}<extra></extra>"
            ))
    
    # Línea vertical "Hoy"
    fig.add_vline(
        x=datetime.now().timestamp() * 1000,
        line_dash="dash",
        line_color="red",
        line_width=2,
        annotation_text="HOY",
        annotation_position="top"
    )
    
    fig.update_layout(
        height=max(500, len(pedidos_ordenados) * 35),
        barmode='overlay',
        showlegend=False,
        xaxis=dict(
            title="Fecha",
            type='date',
            tickformat='%d/%m'
        ),
        yaxis=dict(title=""),
        hovermode='closest',
        margin=dict(l=250, r=20, t=40, b=40)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_vista_semanal(pedidos: List[Dict]):
    """Renderiza vista semanal tipo calendario."""
    if not pedidos:
        st.info("No hay pedidos para mostrar")
        return
    
    st.markdown("### 📅 Vista Semanal")
    
    # Calcular lunes de esta semana
    hoy = datetime.now()
    lunes = hoy - timedelta(days=hoy.weekday())
    
    # Generar 7 días (lunes a domingo)
    dias_semana = [lunes + timedelta(days=i) for i in range(7)]
    
    # Agrupar pedidos por día
    pedidos_por_dia = {dia.date(): [] for dia in dias_semana}
    
    for p in pedidos:
        fecha_dia = p["_fecha_entrega"].date()
        if fecha_dia in pedidos_por_dia:
            pedidos_por_dia[fecha_dia].append(p)
    
    # Renderizar columnas de días
    cols = st.columns(7)
    dias_nombres = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    
    for idx, (dia, nombre_dia) in enumerate(zip(dias_semana, dias_nombres)):
        with cols[idx]:
            # Header del día
            es_hoy = dia.date() == hoy.date()
            header_style = "background-color: #3498db; color: white;" if es_hoy else ""
            
            st.markdown(
                f"""
                <div style="text-align: center; padding: 10px; border-radius: 5px; {header_style}">
                    <div style="font-weight: bold;">{nombre_dia}</div>
                    <div>{dia.day}/{dia.month}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Pedidos del día
            pedidos_dia = pedidos_por_dia[dia.date()]
            
            if pedidos_dia:
                # Carga total del día
                carga_dia = sum(p.get("kg_total", 0) for p in pedidos_dia) / 1000
                
                st.markdown(f"**{len(pedidos_dia)} pedidos**")
                st.markdown(f"📦 {carga_dia:.1f}t")
                
                # Alerta de sobrecarga
                if carga_dia > (CAPACIDAD_DIARIA_SALA * 2 / 1000):
                    st.warning("⚠️ Sobrecarga")
                
                st.divider()
                
                # Lista de pedidos
                for p in pedidos_dia[:3]:  # Mostrar máximo 3
                    color = p["_color_fruta"]
                    avance = p.get("avance_pct", 0)
                    
                    st.markdown(
                        f"""
                        <div style="
                            border-left: 4px solid {color};
                            padding: 5px;
                            margin-bottom: 5px;
                            background-color: {color}15;
                            border-radius: 3px;
                            font-size: 11px;
                        ">
                            <div style="font-weight: bold;">{p.get('name')}</div>
                            <div>{p['_emoji_urgencia']} {p.get('partner_name', '')[:20]}</div>
                            <div>🍇 {p['_tipo_fruta'].capitalize()}</div>
                            <div>📊 {avance:.0f}% | {p.get('kg_total', 0)/1000:.1f}t</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                if len(pedidos_dia) > 3:
                    st.caption(f"+ {len(pedidos_dia) - 3} más")
            else:
                st.info("Sin pedidos")


def render_vista_diaria(pedidos: List[Dict]):
    """Renderiza vista diaria detallada de hoy."""
    hoy = datetime.now().date()
    
    st.markdown(f"### 🗓️ {hoy.strftime('%A %d de %B, %Y')}")
    
    # Filtrar pedidos de hoy y próximos días
    pedidos_hoy = [p for p in pedidos if p["_fecha_entrega"].date() == hoy]
    pedidos_criticos = [p for p in pedidos if p["_nivel_urgencia"] in ["atrasado", "critico"]]
    pedidos_urgentes = [p for p in pedidos if p["_nivel_urgencia"] == "urgente"]
    
    # Sección de críticos
    if pedidos_criticos:
        st.markdown("#### 🔴⚡ CRÍTICOS Y ATRASADOS")
        
        for p in pedidos_criticos:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{p['_emoji_urgencia']} {p.get('name')} - {p.get('partner_name')}**")
                    st.caption(f"🍇 {p['_producto_nombre'][:50]} | 🏭 {p['_sala']}")
                    st.caption(f"📅 Entrega: {p['_fecha_entrega'].strftime('%d/%m/%Y')} ({p['_dias_restantes']} días)")
                
                with col2:
                    st.metric("KG", f"{p.get('kg_total', 0)/1000:.1f}t")
                    st.progress(p.get("avance_pct", 0) / 100)
                
                with col3:
                    st.metric("Avance", f"{p.get('avance_pct', 0):.0f}%")
                    if st.button("Ver", key=f"ver_{p.get('id')}"):
                        st.info(f"Abrir detalle de {p.get('name')}")
                
                st.divider()
    
    # Pedidos de hoy
    if pedidos_hoy:
        st.markdown("#### 📋 ENTREGAS DE HOY")
        
        for p in pedidos_hoy:
            st.markdown(
                f"""
                **{p.get('name')}** - {p.get('partner_name')}  
                🍇 {p['_producto_nombre'][:50]} | 🏭 {p['_sala']}  
                📊 {p.get('kg_total', 0):,.0f} kg | Avance: {p.get('avance_pct', 0):.1f}%
                """
            )
            st.divider()
    
    # Carga por sala
    st.markdown("#### 🏭 CARGA POR SALA HOY")
    
    # Calcular carga por sala
    salas_carga = {}
    for p in pedidos:
        if p["_fecha_entrega"].date() == hoy:
            sala = p["_sala"]
            if sala not in salas_carga:
                salas_carga[sala] = 0
            salas_carga[sala] += p.get("kg_total", 0)
    
    if salas_carga:
        for sala, kg in salas_carga.items():
            porcentaje = (kg / CAPACIDAD_DIARIA_SALA) * 100
            st.markdown(f"**{sala}**")
            st.progress(min(porcentaje / 100, 1.0))
            st.caption(f"{kg/1000:.1f}t / {CAPACIDAD_DIARIA_SALA/1000:.0f}t ({porcentaje:.0f}%)")
    else:
        st.info("Sin carga programada para hoy")


def render_tabla_detallada(pedidos: List[Dict]):
    """Renderiza tabla detallada con todos los pedidos."""
    if not pedidos:
        st.info("No hay pedidos para mostrar")
        return
    
    st.markdown("### 📋 Tabla Detallada")
    
    # Preparar DataFrame
    tabla_data = []
    for p in pedidos:
        tabla_data.append({
            "🔔": p["_emoji_urgencia"],
            "SO": p.get("name", "N/A"),
            "Cliente": p.get("partner_name", "N/A")[:30],
            "🍇 Producto": p["_tipo_fruta"].capitalize(),
            "🏭 Sala": p["_sala"],
            "📅 Entrega": p["_fecha_entrega"].strftime("%d/%m/%Y"),
            "Días": p["_dias_restantes"],
            "KG Total": p.get("kg_total", 0),
            "KG Prod.": p.get("kg_producidos", 0),
            "Avance %": p.get("avance_pct", 0),
            "Estado": get_sale_state_display(p.get("state", ""))
        })
    
    df = pd.DataFrame(tabla_data)
    
    # Ordenar por días restantes
    df = df.sort_values("Días")
    
    # Mostrar tabla con estilos
    st.dataframe(
        df.style.format({
            "KG Total": "{:,.0f}",
            "KG Prod.": "{:,.0f}",
            "Avance %": "{:.1f}%"
        }).background_gradient(subset=["Avance %"], cmap="RdYlGn", vmin=0, vmax=100),
        use_container_width=True,
        hide_index=True,
        height=600
    )


# ============================================================================
# RENDER PRINCIPAL
# ============================================================================

def render(username: str, password: str):
    """Función principal de renderizado del tab calendario."""
    
    st.markdown("## 📅 Calendario de Pedidos")
    st.caption("Vista temporal completa de todos los pedidos con estado, avance y detalles")
    
    # =========================================================================
    # CONTROLES SUPERIORES
    # =========================================================================
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 2, 1])
    
    with col_ctrl1:
        fecha_inicio = st.date_input(
            "Desde",
            value=(datetime.now() - timedelta(days=30)).date(),
            key="cal_fecha_inicio"
        )
    
    with col_ctrl2:
        fecha_fin = st.date_input(
            "Hasta",
            value=(datetime.now() + timedelta(days=90)).date(),
            key="cal_fecha_fin"
        )
    
    with col_ctrl3:
        actualizar = st.button("🔄 Actualizar", type="primary", use_container_width=True)
    
    # =========================================================================
    # CARGAR Y PROCESAR DATOS
    # =========================================================================
    if actualizar:
        with st.spinner("📊 Cargando pedidos..."):
            pedidos_raw = fetch_all_pedidos(
                username, password,
                start_date=fecha_inicio.isoformat(),
                end_date=fecha_fin.isoformat()
            )
            
            if pedidos_raw:
                pedidos_procesados = procesar_pedidos(pedidos_raw)
                st.session_state["calendario_pedidos"] = pedidos_procesados
                st.success(f"✓ {len(pedidos_procesados)} pedidos cargados")
            else:
                st.warning("No se encontraron pedidos")
                st.session_state["calendario_pedidos"] = []
                return
    
    pedidos = st.session_state.get("calendario_pedidos", [])
    
    if not pedidos:
        st.info("👆 Haz clic en 'Actualizar' para cargar pedidos")
        return
    
    st.divider()
    
    # =========================================================================
    # KPIs PRINCIPALES
    # =========================================================================
    kpis = calcular_kpis(pedidos)
    render_kpis(kpis)
    
    st.divider()
    
    # =========================================================================
    # FILTROS
    # =========================================================================
    filtros = render_filtros(pedidos)
    pedidos_filtrados = aplicar_filtros(pedidos, filtros)
    
    if len(pedidos_filtrados) < len(pedidos):
        st.info(f"📊 Mostrando {len(pedidos_filtrados)} de {len(pedidos)} pedidos")
    
    st.divider()
    
    # =========================================================================
    # VISTAS PRINCIPALES (TABS)
    # =========================================================================
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Timeline / Gantt",
        "📅 Vista Semanal",
        "🗓️ Vista Diaria",
        "📋 Tabla Detallada"
    ])
    
    with tab1:
        render_gantt_chart(pedidos_filtrados)
    
    with tab2:
        render_vista_semanal(pedidos_filtrados)
    
    with tab3:
        render_vista_diaria(pedidos_filtrados)
    
    with tab4:
        render_tabla_detallada(pedidos_filtrados)

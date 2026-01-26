"""
Tab de Proyección de Ventas.
Analiza las SO futuras para planificación de producción.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import List, Dict

from .shared import (
    fetch_containers, STATE_OPTIONS, API_URL,
    get_state_color, get_sale_state_display,
    get_date_urgency_color, get_odoo_link, format_date_with_urgency
)
import httpx


def fetch_proyecciones(username: str, password: str, start_date: str, end_date: str,
                       partner_id: int = None, state: str = None) -> List[Dict]:
    """
    Obtiene SO proyectadas (futuras) desde la API.
    Filtra por commitment_date >= start_date.
    """
    try:
        params = {
            "username": username,
            "password": password,
            "start_date": start_date,
            "end_date": end_date
        }
        if partner_id:
            params["partner_id"] = partner_id
        if state:
            params["state"] = state
        
        # Usamos el endpoint específico para proyecciones
        response = httpx.get(
            f"{API_URL}/api/v1/containers/proyecciones",
            params=params,
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener proyecciones: {str(e)}")
        return []


def render(username: str, password: str):
    """Renderiza el tab de Proyección de Ventas."""
    
    # =========================================================================
    # FILTROS
    # =========================================================================
    st.markdown("### 📅 Filtros de Proyección")
    
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    
    with col_f1:
        fecha_inicio = st.date_input(
            "Fecha Inicio",
            value=datetime.now().date(),
            help="Fecha desde la cual buscar entregas",
            key="proy_fecha_inicio"
        )
    
    with col_f2:
        fecha_fin = st.date_input(
            "Fecha Fin",
            value=datetime.now().date() + timedelta(days=90),
            help="Fecha hasta la cual buscar entregas",
            key="proy_fecha_fin"
        )
    
    with col_f3:
        estado = st.selectbox(
            "Estado SO",
            options=["Todos", "Confirmado", "Borrador"],
            index=0,
            key="proy_estado"
        )
    
    # Botón de búsqueda
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        buscar = st.button("🔍 Buscar Proyecciones", type="primary", use_container_width=True, key="btn_buscar_proy")
    
    st.divider()
    
    # =========================================================================
    # CARGAR DATOS
    # =========================================================================
    if buscar:
        state_map = {"Todos": None, "Confirmado": "sale", "Borrador": "draft"}
        state_filter = state_map.get(estado)
        
        with st.spinner("🔍 Buscando proyecciones..."):
            proyecciones = fetch_proyecciones(
                username, password,
                start_date=fecha_inicio.isoformat(),
                end_date=fecha_fin.isoformat(),
                state=state_filter
            )
            st.session_state["proyecciones_data"] = proyecciones
            
            if proyecciones:
                st.success(f"✓ {len(proyecciones)} SO encontradas")
            else:
                st.warning("No se encontraron SO en el período seleccionado")
    
    # Obtener datos del session_state
    proyecciones = st.session_state.get("proyecciones_data", [])
    
    if not proyecciones:
        st.info("👆 Configura los filtros y haz clic en **'Buscar Proyecciones'** para comenzar")
        return
    
    # =========================================================================
    # KPIs PRINCIPALES
    # =========================================================================
    st.markdown("### 📊 Resumen de Proyecciones")
    
    total_so = len(proyecciones)
    total_kg = sum([p.get("kg_total", 0) for p in proyecciones])
    clientes_unicos = len(set([p.get("partner_name", "N/A") for p in proyecciones]))
    
    # Fecha más próxima
    fechas = []
    for p in proyecciones:
        fecha_str = p.get("commitment_date") or p.get("date_order")
        if fecha_str:
            try:
                if 'T' in str(fecha_str):
                    f = datetime.fromisoformat(str(fecha_str).replace('Z', '+00:00'))
                else:
                    f = datetime.strptime(str(fecha_str)[:10], '%Y-%m-%d')
                fechas.append(f)
            except:
                pass
    
    fecha_proxima = min(fechas) if fechas else None
    dias_proxima = (fecha_proxima.replace(tzinfo=None) - datetime.now()).days if fecha_proxima else None
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Total SO", f"{total_so:,}")
    
    with col2:
        st.metric("📦 KG Comprometidos", f"{total_kg:,.0f} kg")
    
    with col3:
        st.metric("👥 Clientes", clientes_unicos)
    
    with col4:
        if fecha_proxima and dias_proxima is not None:
            color = "🔴" if dias_proxima <= 7 else "🟡" if dias_proxima <= 14 else "🟢"
            st.metric("📅 Próxima Entrega", f"{color} {dias_proxima}d")
        else:
            st.metric("📅 Próxima Entrega", "—")
    
    st.divider()
    
    # =========================================================================
    # GRÁFICOS
    # =========================================================================
    col_g1, col_g2 = st.columns(2)
    
    # --- Gráfico 1: Timeline por Semana ---
    with col_g1:
        st.markdown("#### 📅 Timeline de Entregas")
        
        # Preparar datos por semana
        df = pd.DataFrame(proyecciones)
        if "commitment_date" in df.columns:
            df["fecha"] = pd.to_datetime(df["commitment_date"], errors='coerce')
        else:
            df["fecha"] = pd.to_datetime(df.get("date_order", None), errors='coerce')
        
        df = df.dropna(subset=["fecha"])
        
        if not df.empty:
            df["semana"] = df["fecha"].dt.isocalendar().week
            df["año"] = df["fecha"].dt.year
            df["semana_label"] = df.apply(lambda x: f"S{x['semana']:02d}-{x['año']}", axis=1)
            
            resumen_semana = df.groupby("semana_label").agg({
                "kg_total": "sum",
                "name": "count"
            }).reset_index()
            resumen_semana.columns = ["Semana", "KG Total", "# SO"]
            resumen_semana = resumen_semana.sort_values("Semana")
            
            fig_timeline = px.bar(
                resumen_semana,
                x="Semana",
                y="KG Total",
                text="# SO",
                color="KG Total",
                color_continuous_scale=["#4ecdc4", "#2ecc71", "#f1c40f", "#e74c3c"],
                title=""
            )
            fig_timeline.update_traces(textposition="outside", texttemplate="%{text} SO")
            fig_timeline.update_layout(
                height=350,
                showlegend=False,
                xaxis_title="Semana",
                yaxis_title="KG",
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("No hay datos de fecha para mostrar timeline")
    
    # --- Gráfico 2: Distribución por Cliente ---
    with col_g2:
        st.markdown("#### 👥 Distribución por Cliente")
        
        df_cliente = pd.DataFrame(proyecciones)
        if not df_cliente.empty and "partner_name" in df_cliente.columns:
            resumen_cliente = df_cliente.groupby("partner_name").agg({
                "kg_total": "sum"
            }).reset_index()
            resumen_cliente.columns = ["Cliente", "KG Total"]
            resumen_cliente = resumen_cliente.sort_values("KG Total", ascending=False).head(10)
            
            fig_cliente = px.pie(
                resumen_cliente,
                values="KG Total",
                names="Cliente",
                title="",
                hole=0.4
            )
            fig_cliente.update_traces(textinfo="percent+label", textposition="outside")
            fig_cliente.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig_cliente, use_container_width=True)
        else:
            st.info("No hay datos de cliente para mostrar distribución")
    
    st.divider()
    
    # =========================================================================
    # ANÁLISIS POR PRODUCTO
    # =========================================================================
    st.markdown("### 🍇 Análisis por Producto/Fruta")
    
    # Extraer productos de las líneas de orden
    productos_data = []
    for proy in proyecciones:
        for linea in proy.get("lineas", []):
            # Extraer nombre del producto
            prod = linea.get("product_id", {})
            if isinstance(prod, dict):
                prod_name = prod.get("name", "N/A")
            elif isinstance(prod, (list, tuple)) and len(prod) > 1:
                prod_name = prod[1]
            else:
                prod_name = "N/A"
            
            productos_data.append({
                "so": proy.get("name"),
                "cliente": proy.get("partner_name"),
                "producto": prod_name,
                "kg": linea.get("product_uom_qty", 0),
                "fecha": proy.get("commitment_date") or proy.get("date_order")
            })
    
    if productos_data:
        df_prod = pd.DataFrame(productos_data)
        
        # Agrupar por producto
        resumen_prod = df_prod.groupby("producto").agg({
            "kg": "sum",
            "so": "nunique"
        }).reset_index()
        resumen_prod.columns = ["Producto", "KG Total", "# SO"]
        resumen_prod = resumen_prod.sort_values("KG Total", ascending=False)
        
        col_p1, col_p2 = st.columns([2, 1])
        
        with col_p1:
            # Gráfico de barras horizontales
            fig_prod = px.bar(
                resumen_prod.head(15),
                y="Producto",
                x="KG Total",
                orientation="h",
                color="KG Total",
                color_continuous_scale="Viridis",
                text="KG Total"
            )
            fig_prod.update_traces(texttemplate="%{text:,.0f} kg", textposition="outside")
            fig_prod.update_layout(
                height=max(400, len(resumen_prod.head(15)) * 30),
                showlegend=False,
                yaxis=dict(categoryorder='total ascending'),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_prod, use_container_width=True)
        
        with col_p2:
            st.markdown("**Top 10 Productos**")
            st.dataframe(
                resumen_prod.head(10).style.format({
                    "KG Total": "{:,.0f}",
                    "# SO": "{:,.0f}"
                }),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("No hay datos de líneas de producto disponibles")
    
    st.divider()
    
    # =========================================================================
    # TABLA DE DETALLE
    # =========================================================================
    st.markdown("### 📋 Detalle de Proyecciones")
    
    # Preparar datos para tabla
    tabla_data = []
    for proy in proyecciones:
        fecha_entrega = proy.get("commitment_date") or proy.get("date_order") or "—"
        tabla_data.append({
            "SO": proy.get("name", "N/A"),
            "Cliente": proy.get("partner_name", "N/A"),
            "Fecha Entrega": format_date_with_urgency(fecha_entrega),
            "KG Total": proy.get("kg_total", 0),
            "KG Producidos": proy.get("kg_producidos", 0),
            "Avance %": proy.get("avance_pct", 0),
            "Estado": get_sale_state_display(proy.get("state", "")),
            "# Líneas": len(proy.get("lineas", []))
        })
    
    df_tabla = pd.DataFrame(tabla_data)
    
    # Ordenar por fecha
    # df_tabla = df_tabla.sort_values("Fecha Entrega")
    
    # Mostrar tabla con estilos
    st.dataframe(
        df_tabla.style.format({
            "KG Total": "{:,.0f}",
            "KG Producidos": "{:,.0f}",
            "Avance %": "{:.1f}%"
        }).background_gradient(subset=["KG Total"], cmap="Blues"),
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # =========================================================================
    # ALERTAS DE CAPACIDAD
    # =========================================================================
    st.divider()
    st.markdown("### ⚠️ Alertas de Capacidad")
    
    # Calcular KG/día requeridos
    dias_periodo = (fecha_fin - fecha_inicio).days or 1
    kg_por_dia = total_kg / dias_periodo
    
    # Capacidad estimada (puedes ajustar este valor)
    CAPACIDAD_DIARIA_KG = 50000  # 50 toneladas/día ejemplo
    
    col_cap1, col_cap2 = st.columns(2)
    
    with col_cap1:
        utilizacion = (kg_por_dia / CAPACIDAD_DIARIA_KG) * 100
        
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=utilizacion,
            number={"suffix": "%"},
            title={"text": "Utilización de Capacidad"},
            delta={"reference": 80},
            gauge={
                "axis": {"range": [0, 150]},
                "bar": {"color": "#3498db"},
                "steps": [
                    {"range": [0, 60], "color": "#2ecc71"},
                    {"range": [60, 80], "color": "#f1c40f"},
                    {"range": [80, 100], "color": "#e67e22"},
                    {"range": [100, 150], "color": "#e74c3c"}
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 100
                }
            }
        ))
        fig_gauge.update_layout(height=300)
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col_cap2:
        st.markdown("**Métricas de Capacidad**")
        st.metric("📊 KG/día Requeridos", f"{kg_por_dia:,.0f}")
        st.metric("🏭 Capacidad Diaria", f"{CAPACIDAD_DIARIA_KG:,.0f} kg")
        
        if utilizacion > 100:
            st.error(f"⚠️ **SOBRECARGA**: Se requiere {utilizacion - 100:.1f}% más capacidad")
        elif utilizacion > 80:
            st.warning(f"⚡ **ALTA CARGA**: {utilizacion:.1f}% de capacidad comprometida")
        else:
            st.success(f"✅ **OK**: {utilizacion:.1f}% de capacidad utilizada")

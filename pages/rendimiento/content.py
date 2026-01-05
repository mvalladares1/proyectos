"""
Contenido principal del dashboard de Trazabilidad.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from .shared import fmt_numero, get_trazabilidad_inversa, get_sankey_data


def render(username: str, password: str):
    """Renderiza el contenido principal del dashboard."""
    
    # Sidebar - Filtros de fecha para Sankey
    st.sidebar.header("📅 Período para Diagrama")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        fecha_inicio = st.date_input(
            "Desde",
            datetime.now() - timedelta(days=30),
            format="DD/MM/YYYY"
        )
    with col2:
        fecha_fin = st.date_input(
            "Hasta",
            datetime.now(),
            format="DD/MM/YYYY"
        )
    
    # Tabs
    tab1, tab2 = st.tabs(["🔍 Trazabilidad Inversa", "🔗 Diagrama Sankey"])
    
    with tab1:
        _render_trazabilidad(username, password)
    
    with tab2:
        _render_sankey(username, password, fecha_inicio, fecha_fin)


def _render_trazabilidad(username: str, password: str):
    """Renderiza el tab de trazabilidad inversa."""
    st.subheader("🔍 Trazabilidad Inversa: PT → MP")
    st.markdown("Ingresa un lote de Producto Terminado para encontrar los lotes de Materia Prima originales.")
    
    lote_pt_input = st.text_input("Número de Lote PT", placeholder="Ej: 0000304776")
    
    if st.button("Buscar Origen", type="primary"):
        if not lote_pt_input:
            st.warning("Ingresa un número de lote")
            return
        
        with st.spinner("Buscando trazabilidad..."):
            traz = get_trazabilidad_inversa(username, password, lote_pt_input)
            
            if traz.get('error'):
                st.warning(traz['error'])
                return
            
            st.success(f"✅ Lote encontrado: **{traz['lote_pt']}**")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Producto PT:** {traz.get('producto_pt', 'N/A')}")
                st.markdown(f"**Fecha Creación:** {traz.get('fecha_creacion', 'N/A')}")
            with col2:
                if traz.get('mo'):
                    st.markdown(f"**MO:** {traz['mo'].get('name', 'N/A')}")
                    st.markdown(f"**Fecha MO:** {traz['mo'].get('fecha', 'N/A')}")
            
            st.markdown("---")
            st.markdown("### 📦 Lotes MP Originales")
            
            lotes_mp = traz.get('lotes_mp', [])
            if lotes_mp:
                df_mp = pd.DataFrame(lotes_mp)
                df_mp['kg'] = df_mp['kg'].apply(lambda x: fmt_numero(x, 2))
                st.dataframe(
                    df_mp[['lot_name', 'product_name', 'kg', 'proveedor', 'fecha_recepcion']],
                    use_container_width=True,
                    hide_index=True
                )
                st.metric("Total Kg MP", fmt_numero(traz.get('total_kg_mp', 0), 2))
            else:
                st.info("No se encontraron lotes MP asociados")


def _render_sankey(username: str, password: str, fecha_inicio, fecha_fin):
    """Renderiza el tab del diagrama Sankey."""
    st.subheader("🔗 Diagrama Sankey: Container → Fabricación → Pallets")
    st.caption("Visualización del flujo de containers, fabricaciones y pallets")
    
    if st.button("🔄 Generar Diagrama", type="primary"):
        with st.spinner("Generando diagrama Sankey..."):
            sankey_data = get_sankey_data(
                username, password,
                fecha_inicio.strftime("%Y-%m-%d"),
                fecha_fin.strftime("%Y-%m-%d")
            )
            
            if not sankey_data:
                st.error("Error al obtener datos del servidor")
                return
            
            if not sankey_data.get('nodes') or not sankey_data.get('links'):
                st.warning("No hay datos suficientes para generar el diagrama en el período seleccionado.")
                return
            
            # Crear figura Sankey
            fig = go.Figure(data=[go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=[n["label"] for n in sankey_data["nodes"]],
                    color=[n["color"] for n in sankey_data["nodes"]],
                    customdata=[n.get("detail", "") for n in sankey_data["nodes"]],
                    hovertemplate="%{label}<br>%{customdata}<extra></extra>"
                ),
                link=dict(
                    source=[l["source"] for l in sankey_data["links"]],
                    target=[l["target"] for l in sankey_data["links"]],
                    value=[l["value"] for l in sankey_data["links"]]
                )
            )])
            
            fig.update_layout(
                title="Flujo: Container → Fabricación → Pallets",
                height=700,
                font=dict(size=10)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Estadísticas
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Containers", len([n for n in sankey_data["nodes"] if n["color"] == "#3498db"]))
            with col2:
                st.metric("Fabricaciones", len([n for n in sankey_data["nodes"] if n["color"] == "#e74c3c"]))
            with col3:
                total_pallets = len([n for n in sankey_data["nodes"] if n["color"] in ["#f39c12", "#2ecc71"]])
                st.metric("Pallets", total_pallets)
            
            # Leyenda
            st.markdown("##### Leyenda:")
            st.markdown("🔵 Containers | 🔴 Fabricaciones | 🟠 Pallets IN | 🟢 Pallets OUT")
    else:
        st.info("👆 Selecciona las fechas en el sidebar y haz clic en **Generar Diagrama**")

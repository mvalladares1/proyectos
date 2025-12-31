"""
Rendimiento Productivo: Dashboard de trazabilidad.
Trazabilidad: Lote MP → MO → Lote PT
Versión simplificada: Solo Trazabilidad Inversa y Diagrama Sankey
"""
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.auth import proteger_modulo, get_credenciales


# --- Funciones de formateo chileno ---
def fmt_numero(valor, decimales=0):
    """Formatea número con punto como miles y coma como decimal"""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "0"
    try:
        if decimales > 0:
            formatted = f"{valor:,.{decimales}f}"
        else:
            formatted = f"{valor:,.0f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except:
        return str(valor)


# Configuración de página
st.set_page_config(page_title="Trazabilidad", page_icon="🔍", layout="wide")

# Autenticación
if not proteger_modulo("trazabilidad"):
    st.stop()

username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales. Por favor inicie sesión nuevamente.")
    st.stop()

st.title("🔍 Trazabilidad Productiva")
st.caption("Seguimiento de lotes: Materia Prima (MP) → Producto Terminado (PT)")

# API URL
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# --- Filtros ---
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

# === Solo 2 tabs: Trazabilidad y Diagrama ===
tab1, tab2 = st.tabs(["🔍 Trazabilidad Inversa", "🔗 Diagrama Sankey"])

# --- TAB 1: Trazabilidad Inversa ---
with tab1:
    st.subheader("🔍 Trazabilidad Inversa: PT → MP")
    st.markdown("Ingresa un lote de Producto Terminado para encontrar los lotes de Materia Prima originales.")
    
    lote_pt_input = st.text_input("Número de Lote PT", placeholder="Ej: 0000304776")
    
    if st.button("Buscar Origen", type="primary"):
        if lote_pt_input:
            with st.spinner("Buscando trazabilidad..."):
                try:
                    params = {"username": username, "password": password}
                    resp = requests.get(
                        f"{API_URL}/api/v1/rendimiento/trazabilidad-inversa/{lote_pt_input}",
                        params=params,
                        timeout=60
                    )
                    if resp.status_code == 200:
                        traz = resp.json()
                        
                        if traz.get('error'):
                            st.warning(traz['error'])
                        else:
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
                                st.dataframe(df_mp[['lot_name', 'product_name', 'kg', 'proveedor', 'fecha_recepcion']], 
                                           use_container_width=True, hide_index=True)
                                st.metric("Total Kg MP", fmt_numero(traz.get('total_kg_mp', 0), 2))
                            else:
                                st.info("No se encontraron lotes MP asociados")
                    else:
                        st.error(f"Error: {resp.status_code}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Ingresa un número de lote")

# --- TAB 2: Diagrama Sankey ---
with tab2:
    import plotly.graph_objects as go
    
    st.subheader("🔗 Diagrama Sankey: Container → Fabricación → Pallets")
    st.caption("Visualización del flujo de containers, fabricaciones y pallets")
    
    if st.button("🔄 Generar Diagrama", type="primary"):
        with st.spinner("Generando diagrama Sankey..."):
            try:
                params = {
                    "username": username, 
                    "password": password,
                    "start_date": fecha_inicio.strftime("%Y-%m-%d"),
                    "end_date": fecha_fin.strftime("%Y-%m-%d"),
                    "limit": 30
                }
                
                resp = requests.get(
                    f"{API_URL}/api/v1/containers/sankey",
                    params=params,
                    timeout=120
                )
                
                if resp.status_code == 200:
                    sankey_data = resp.json()
                    
                    if not sankey_data.get('nodes') or not sankey_data.get('links'):
                        st.warning("No hay datos suficientes para generar el diagrama en el período seleccionado.")
                    else:
                        # Crear figura Sankey
                        fig = go.Figure(data=[go.Sankey(
                            node=dict(
                                pad=15,
                                thickness=20,
                                line=dict(color="black", width=0.5),
                                label=[n["label"] for n in sankey_data["nodes"]],
                                color=[n["color"] for n in sankey_data["nodes"]]
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
                    st.error(f"Error al obtener datos: {resp.status_code}")
                    
            except requests.exceptions.ConnectionError:
                st.error("No se puede conectar al servidor API.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        st.info("👆 Selecciona las fechas en el sidebar y haz clic en **Generar Diagrama**")

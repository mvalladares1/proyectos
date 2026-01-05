"""
Tab: Cámaras
Stock por cámaras de frío, ocupación y detalle por tipo de fruta.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from .shared import fmt_numero, filtrar_camaras_principales


@st.fragment
def render(username: str, password: str, camaras_data_all: list):
    """Renderiza el contenido del tab Cámaras como fragment independiente."""
    st.header("Stock por Cámaras")
    
    if not camaras_data_all:
        st.info("No hay datos de cámaras disponibles")
        return
    
    # Opción para ver todas o solo las principales
    mostrar_todas = st.checkbox("Mostrar todas las ubicaciones", value=False, key="mostrar_todas_camaras")

    if mostrar_todas:
        camaras_data_tab = camaras_data_all
    else:
        camaras_data_tab = filtrar_camaras_principales(camaras_data_all)
    
    # Métricas generales (solo de las cámaras mostradas)
    total_camaras = len(camaras_data_tab)
    total_capacity = sum(c.get("capacity_pallets", 0) for c in camaras_data_tab)
    total_occupied = sum(c.get("occupied_pallets", 0) for c in camaras_data_tab)
    ocupacion_pct = (total_occupied / total_capacity * 100) if total_capacity > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cámaras", fmt_numero(total_camaras))
    col2.metric("Capacidad Total", f"{fmt_numero(total_capacity)} pallets")
    col3.metric("Posiciones Ocupadas", f"{fmt_numero(total_occupied)} pallets")
    col4.metric("Ocupación", f"{fmt_numero(ocupacion_pct, 1)}%")
    
    st.divider()
    
    # Tabla de cámaras con stock
    st.subheader("Detalle por Cámara")
    
    camaras_list = []
    for camara in camaras_data_tab:
        total_kg = sum(camara["stock_data"].values())
        ocupacion = (camara["occupied_pallets"] / camara["capacity_pallets"] * 100) if camara["capacity_pallets"] > 0 else 0
        
        camaras_list.append({
            "Cámara": camara["name"],
            "Ubicación Completa": camara["full_name"],
            "Padre": camara["parent_name"],
            "Capacidad": camara["capacity_pallets"],
            "Ocupado": camara["occupied_pallets"],
            "Disponible": camara["capacity_pallets"] - camara["occupied_pallets"],
            "Ocupación %": round(ocupacion, 1),
            "Stock (kg)": round(total_kg, 0),
            "Tipos": len(camara["stock_data"])
        })
    
    df_camaras = pd.DataFrame(camaras_list)
    
    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        min_ocupacion = st.slider("Ocupación mínima (%)", 0, 100, 0)
    with col_f2:
        buscar_camara = st.text_input("Buscar cámara", "")
    
    # Aplicar filtros sobre datos originales
    mask = df_camaras["Ocupación %"] >= min_ocupacion
    if buscar_camara:
        mask = mask & (
            df_camaras["Cámara"].str.contains(buscar_camara, case=False, na=False) |
            df_camaras["Ubicación Completa"].str.contains(buscar_camara, case=False, na=False)
        )
    
    # Crear df formateado con filtro aplicado
    df_filtered = df_camaras[mask].copy()
    df_filtered["Capacidad"] = df_filtered["Capacidad"].apply(lambda x: fmt_numero(x))
    df_filtered["Ocupado"] = df_filtered["Ocupado"].apply(lambda x: fmt_numero(x))
    df_filtered["Disponible"] = df_filtered["Disponible"].apply(lambda x: fmt_numero(x))
    df_filtered["Ocupación %"] = df_filtered["Ocupación %"].apply(lambda x: fmt_numero(x, 1))
    df_filtered["Stock (kg)"] = df_filtered["Stock (kg)"].apply(lambda x: fmt_numero(x))

    st.dataframe(
        df_filtered,
        use_container_width=True,
        height=300,
        hide_index=True
    )
    
    # Detalle de stock por Tipo Fruta / Manejo
    st.subheader("Stock por Tipo Fruta / Manejo")
    
    @st.fragment
    def _fragment_detalle_camara():
        """Fragment para drill-down de detalle por cámara."""
        # Seleccionar cámara
        camara_names = [c["name"] for c in camaras_data_tab]
        selected_camara = st.selectbox("Seleccionar cámara", camara_names, key="sel_camara_detalle")
        
        if selected_camara:
            camara_detail = next((c for c in camaras_data_tab if c["name"] == selected_camara), None)
            if camara_detail and camara_detail["stock_data"]:
            stock_items = [
                {"Tipo Fruta - Manejo": k, "Stock (kg)": round(v, 2)}
                for k, v in camara_detail["stock_data"].items()
            ]
            df_stock = pd.DataFrame(stock_items).sort_values("Stock (kg)", ascending=False)
            
            # Asignar color según manejo
            def get_color(tipo_manejo):
                if "Orgánico" in tipo_manejo:
                    return "#28a745"  # Verde para orgánico
                else:
                    return "#007bff"  # Azul para convencional
            
            df_stock["Color"] = df_stock["Tipo Fruta - Manejo"].apply(get_color)
            
            fig = px.bar(
                df_stock,
                x="Tipo Fruta - Manejo",
                y="Stock (kg)",
                color="Tipo Fruta - Manejo",
                color_discrete_map={k: get_color(k) for k in df_stock["Tipo Fruta - Manejo"].unique()}
            )
            fig.update_layout(
                showlegend=False,
                height=400,
                xaxis_title="",
                yaxis_title="Stock (kg)",
                xaxis_tickangle=-45
            )
            fig.update_traces(
                hovertemplate="<b>%{x}</b><br>Stock: %{y:,.2f} kg<extra></extra>"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
                # Tabla debajo del gráfico con formato chileno
                df_stock_display = df_stock[["Tipo Fruta - Manejo", "Stock (kg)"]].copy()
                df_stock_display["Stock (kg)"] = df_stock_display["Stock (kg)"].apply(lambda x: fmt_numero(x, 2))
                st.dataframe(df_stock_display, use_container_width=True, height=300, hide_index=True)
    
    _fragment_detalle_camara()

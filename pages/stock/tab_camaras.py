"""
Tab: Cámaras
Stock por cámaras de frío, ocupación y detalle por tipo de fruta.
Incluye sección separada para cámaras VLK.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from .shared import fmt_numero, filtrar_camaras_principales, CAMARAS_CONFIG


def _render_tabla_camaras(camaras_list: list, title: str = "Detalle"):
    """Renderiza tabla de cámaras con formato."""
    if not camaras_list:
        st.info(f"No hay cámaras {title} disponibles")
        return
    
    df_camaras = pd.DataFrame(camaras_list)
    
    # Formatear para display
    df_display = df_camaras.copy()
    df_display["Capacidad"] = df_display["Capacidad"].apply(lambda x: fmt_numero(x))
    df_display["Ocupado"] = df_display["Ocupado"].apply(lambda x: fmt_numero(x))
    df_display["Disponible"] = df_display["Disponible"].apply(lambda x: fmt_numero(x))
    df_display["Ocupación %"] = df_display["Ocupación %"].apply(lambda x: fmt_numero(x, 1))
    df_display["Stock (kg)"] = df_display["Stock (kg)"].apply(lambda x: fmt_numero(x))
    
    st.dataframe(
        df_display,
        use_container_width=True,
        height=200,
        hide_index=True
    )


def _procesar_camaras_a_lista(camaras_data: list) -> list:
    """Procesa datos de cámaras a formato de lista para tabla."""
    camaras_list = []
    for camara in camaras_data:
        total_kg = sum(camara.get("stock_data", {}).values())
        cap = camara.get("capacity_pallets", 1)
        ocup = camara.get("occupied_pallets", 0)
        ocupacion = (ocup / cap * 100) if cap > 0 else 0
        
        camaras_list.append({
            "Cámara": camara.get("name", ""),
            "Ubicación Completa": camara.get("full_name", ""),
            "Capacidad": cap,
            "Ocupado": ocup,
            "Disponible": cap - ocup,
            "Ocupación %": round(ocupacion, 1),
            "Stock (kg)": round(total_kg, 0),
            "Tipos": len(camara.get("stock_data", {}))
        })
    return camaras_list


@st.fragment
def render(username: str, password: str, camaras_data_all: list):
    """Renderiza el contenido del tab Cámaras como fragment independiente."""
    st.header("📦 Stock por Cámaras")
    
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
    
    # Separar cámaras por grupo
    vlk_camaras = [c for c in camaras_data_tab if "VLK" in c.get("name", "") or "VLK" in c.get("full_name", "")]
    rf_camaras = [c for c in camaras_data_tab if c not in vlk_camaras]
    
    # === SECCIÓN VLK ===
    st.subheader("🏢 Cámaras VLK")
    
    if vlk_camaras:
        # Métricas VLK
        vlk_capacity = sum(c.get("capacity_pallets", 0) for c in vlk_camaras)
        vlk_occupied = sum(c.get("occupied_pallets", 0) for c in vlk_camaras)
        vlk_ocupacion = (vlk_occupied / vlk_capacity * 100) if vlk_capacity > 0 else 0
        
        col_v1, col_v2, col_v3 = st.columns(3)
        col_v1.metric("Cámaras VLK", len(vlk_camaras))
        col_v2.metric("Ocupado VLK", f"{fmt_numero(vlk_occupied)} / {fmt_numero(vlk_capacity)}")
        col_v3.metric("Ocupación VLK", f"{fmt_numero(vlk_ocupacion, 1)}%")
        
        vlk_list = _procesar_camaras_a_lista(vlk_camaras)
        _render_tabla_camaras(vlk_list, "VLK")
    else:
        st.info("No hay cámaras VLK disponibles")
    
    st.divider()
    
    # === SECCIÓN RF/STOCK ===
    st.subheader("🏭 Cámaras RF/Stock")
    
    if rf_camaras:
        # Métricas RF
        rf_capacity = sum(c.get("capacity_pallets", 0) for c in rf_camaras)
        rf_occupied = sum(c.get("occupied_pallets", 0) for c in rf_camaras)
        rf_ocupacion = (rf_occupied / rf_capacity * 100) if rf_capacity > 0 else 0
        
        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric("Cámaras RF", len(rf_camaras))
        col_r2.metric("Ocupado RF", f"{fmt_numero(rf_occupied)} / {fmt_numero(rf_capacity)}")
        col_r3.metric("Ocupación RF", f"{fmt_numero(rf_ocupacion, 1)}%")
        
        rf_list = _procesar_camaras_a_lista(rf_camaras)
        _render_tabla_camaras(rf_list, "RF")
    else:
        st.info("No hay cámaras RF/Stock disponibles")
    
    st.divider()
    
    # Detalle de stock por Tipo Fruta / Manejo
    st.subheader("📊 Stock por Tipo Fruta / Manejo")
    
    @st.fragment
    def _fragment_detalle_camara():
        """Fragment para drill-down de detalle por cámara."""
        # Seleccionar cámara
        camara_names = [c["name"] for c in camaras_data_tab]
        selected_camara = st.selectbox("Seleccionar cámara", camara_names, key="sel_camara_detalle")
        
        if selected_camara:
            camara_detail = next((c for c in camaras_data_tab if c["name"] == selected_camara), None)
            if camara_detail and camara_detail.get("stock_data"):
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
                st.dataframe(df_stock_display, use_container_width=True, height=200, hide_index=True)
            else:
                st.info("Esta cámara no tiene stock registrado")
    
    _fragment_detalle_camara()

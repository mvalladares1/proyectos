"""
Tab: Pallets
Consulta de pallets por ubicación con filtros y exportación.
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from .shared import fmt_numero, fetch_pallets


@st.fragment
def render(username: str, password: str, camaras_data: list):
    """Renderiza el contenido del tab Pallets como fragment independiente."""
    st.header("Consulta de Pallets")
    
    if not camaras_data:
        st.info("Primero carga los datos de cámaras en la pestaña anterior")
        return
    
    # Selección de ubicación
    col1, col2 = st.columns(2)
    
    with col1:
        camara_names_map = {c["name"]: c["id"] for c in camaras_data}
        selected_location_name = st.selectbox(
            "Seleccionar ubicación",
            list(camara_names_map.keys()),
            key="location_selector"
        )
        selected_location_id = camara_names_map[selected_location_name]
    
    with col2:
        # Obtener categorías disponibles
        selected_camara_data = next((c for c in camaras_data if c["id"] == selected_location_id), None)
        categories = list(selected_camara_data["stock_data"].keys()) if selected_camara_data else []
        
        # Inicializar debounce state
        if 'pallets_filter_debounce' not in st.session_state:
            st.session_state.pallets_filter_debounce = "Todos"
        
        filter_category = st.selectbox(
            "Filtrar por Tipo Fruta / Manejo",
            ["Todos"] + categories,
            key="category_filter",
            help="🕒 Filtrado automático"
        )
    
    # Lógica de búsqueda automática (sin botón)
    # Usar session_state para controlar si debemos mostrar datos o no (opcional, aquí mostramos siempre si hay ubicación)
    
    if selected_location_id:
        st.session_state.stock_pallets_loading = True
        
        # SKELETON LOADER
        skeleton = st.empty()
        with skeleton.container():
             st.markdown("""
            <div style="animation: pulse 1.5s infinite;">
                <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                    <div style="flex: 1; height: 100px; background-color: #f0f2f6; border-radius: 8px;"></div>
                    <div style="flex: 1; height: 100px; background-color: #f0f2f6; border-radius: 8px;"></div>
                    <div style="flex: 1; height: 100px; background-color: #f0f2f6; border-radius: 8px;"></div>
                </div>
                <div style="height: 300px; background-color: #f0f2f6; border-radius: 8px;"></div>
            </div>
            <style>
                @keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 0.3; } 100% { opacity: 0.6; } }
            </style>
            """, unsafe_allow_html=True)

        try:
            category_param = None if filter_category == "Todos" else filter_category
            
            # Carga real
            pallets_data = fetch_pallets(username, password, selected_location_id, category_param)
            
            # Limpiar skeleton
            skeleton.empty()
            
            # PLACEHOLDER PARA CONTENIDO - evita que se muestre debajo del skeleton
            content_placeholder = st.container()
            
            with content_placeholder:
                if pallets_data:
                    # st.toast no es necesario en cada refresco automático, puede ser molesto
                    # st.toast(f"✅ {fmt_numero(len(pallets_data))} registros encontrados", icon="✅")
                    pass
                
                if pallets_data:
                    st.toast(f"✅ {fmt_numero(len(pallets_data))} registros encontrados", icon="✅")
                
                    # Métricas
                    total_qty = sum(p.get("quantity", 0) for p in pallets_data)
                    avg_age = sum(p.get("days_old", 0) for p in pallets_data) / len(pallets_data) if pallets_data else 0
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Registros", fmt_numero(len(pallets_data)))
                    col2.metric("Stock Total (kg)", fmt_numero(total_qty, 2))
                    col3.metric("Antigüedad Promedio", f"{fmt_numero(avg_age, 0)} días")
                
                st.divider()
                
                # Tabla de pallets
                df_pallets = pd.DataFrame(pallets_data)
                
                # Reordenar columnas en el dataset completo
                column_order = ["pallet", "product", "lot", "quantity", "category", "condition", "in_date", "days_old"]
                df_pallets = df_pallets[[c for c in column_order if c in df_pallets.columns]]
                
                # Renombrar columnas
                df_pallets.columns = ["Pallet", "Producto", "Lote", "Cantidad (kg)", "Categoría", "Condición", "Fecha Ingreso", "Días"]
                
                # Formatear números en el dataset completo
                df_pallets["Cantidad (kg)"] = df_pallets["Cantidad (kg)"].apply(lambda x: fmt_numero(x, 2))
                
                # Paginación
                ITEMS_PER_PAGE = 50
                total_items = len(df_pallets)
                total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
                
                if 'pallets_page' not in st.session_state:
                    st.session_state.pallets_page = 1
                if st.session_state.pallets_page > total_pages:
                    st.session_state.pallets_page = 1
                
                col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
                with col_nav2:
                    st.session_state.pallets_page = st.number_input(
                        "Página",
                        min_value=1,
                        max_value=total_pages,
                        value=st.session_state.pallets_page,
                        key="pallets_page_input"
                    )
                
                st.caption(f"Mostrando {total_items} pallets | Página {st.session_state.pallets_page} de {total_pages}")
                
                start_idx = (st.session_state.pallets_page - 1) * ITEMS_PER_PAGE
                end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
                df_page = df_pallets.iloc[start_idx:end_idx]
                
                # Resaltar antigüedad
                def highlight_age(row):
                    days = row["Días"]
                    if days > 30:
                        return ['background-color: rgba(255, 153, 102, 0.3)'] * len(row)
                    elif days > 15:
                        return ['background-color: rgba(255, 243, 205, 0.3)'] * len(row)
                    return [''] * len(row)
                
                st.dataframe(
                    df_page.style.apply(highlight_age, axis=1),
                    use_container_width=True,
                    height=500
                )
                
                # Descargar CSV (de todos los datos, no solo la página)
                csv = df_pallets.to_csv(index=False)
                st.download_button(
                    "📥 Descargar CSV",
                    csv,
                    f"pallets_{selected_location_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.warning("No se encontraron pallets con los filtros aplicados")
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            st.session_state.stock_pallets_loading = False
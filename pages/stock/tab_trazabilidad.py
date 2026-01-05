"""
Tab: Trazabilidad
Análisis FIFO y antigüedad de lotes por categoría.
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from .shared import fmt_numero, fetch_lotes


@st.fragment
def render(username: str, password: str, camaras_data: list):
    """Renderiza el contenido del tab Trazabilidad como fragment independiente."""
    st.header("Trazabilidad de Lotes")
    st.markdown("Análisis FIFO y antigüedad de lotes por categoría")
    
    if not camaras_data:
        st.info("Primero carga los datos de cámaras")
        return
    
    # Obtener todas las categorías únicas
    all_categories = set()
    for c in camaras_data:
        all_categories.update(c["stock_data"].keys())
    
    selected_category = st.selectbox(
        "Seleccionar Tipo Fruta - Manejo",
        sorted(all_categories),
        key="category_traza"
    )
    
    # Filtro opcional de ubicaciones
    location_filter = st.multiselect(
        "Filtrar por ubicaciones (opcional)",
        [c["name"] for c in camaras_data],
        key="location_filter_traza"
    )
    
    if st.button("🔍 Consultar Lotes", type="primary", disabled=st.session_state.stock_lotes_loading):
        st.session_state.stock_lotes_loading = True
        try:
            location_ids = [c["id"] for c in camaras_data if c["name"] in location_filter] if location_filter else None
            
            with st.spinner("🔄 Analizando lotes desde Odoo..."):
                lotes_data = fetch_lotes(username, password, selected_category, location_ids)
            
            if lotes_data:
                st.toast(f"✅ {fmt_numero(len(lotes_data))} lotes encontrados", icon="✅")
            
                # Métricas
                total_qty = sum(l.get("quantity", 0) for l in lotes_data)
                total_pallets = sum(l.get("pallets", 0) for l in lotes_data)
                oldest_days = max((l.get("days_old", 0) for l in lotes_data), default=0)
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Lotes", fmt_numero(len(lotes_data)))
                col2.metric("Stock Total (kg)", fmt_numero(total_qty, 2))
                col3.metric("Pallets", fmt_numero(total_pallets))
                col4.metric("Lote Más Antiguo", f"{fmt_numero(oldest_days)} días")
                
                st.divider()
                
                # Gráfico de antigüedad
                st.subheader("Distribución de Antigüedad")
                df_lotes = pd.DataFrame(lotes_data)
                
                # Histograma
                st.bar_chart(df_lotes.set_index("lot")["days_old"])
                
                # Tabla detallada
                st.subheader("Detalle de Lotes (ordenado por antigüedad)")
                
                # Formatear tabla
                df_display = df_lotes.copy()
                df_display["locations"] = df_display["locations"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
                
                column_rename = {
                    "lot": "Lote",
                    "product": "Producto",
                    "quantity": "Cantidad (kg)",
                    "pallets": "Pallets",
                    "in_date": "Fecha Ingreso",
                    "days_old": "Días",
                    "locations": "Ubicaciones"
                }
                df_display = df_display.rename(columns=column_rename)
                
                # Formatear números
                df_display["Cantidad (kg)"] = df_display["Cantidad (kg)"].apply(lambda x: fmt_numero(x, 2))
                df_display["Pallets"] = df_display["Pallets"].apply(lambda x: fmt_numero(x))
                
                # Paginación
                ITEMS_PER_PAGE = 50
                total_items = len(df_display)
                total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
                
                if 'trazabilidad_page' not in st.session_state:
                    st.session_state.trazabilidad_page = 1
                if st.session_state.trazabilidad_page > total_pages:
                    st.session_state.trazabilidad_page = 1
                
                col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
                with col_nav2:
                    st.session_state.trazabilidad_page = st.number_input(
                        "Página",
                        min_value=1,
                        max_value=total_pages,
                        value=st.session_state.trazabilidad_page,
                        key="trazabilidad_page_input"
                    )
                
                st.caption(f"Mostrando {total_items} lotes | Página {st.session_state.trazabilidad_page} de {total_pages}")
                
                start_idx = (st.session_state.trazabilidad_page - 1) * ITEMS_PER_PAGE
                end_idx = min(start_idx + ITEMS_PER_PAGE, total_items)
                df_page = df_display.iloc[start_idx:end_idx]
                
                # Resaltar según antigüedad
                def color_age(val):
                    try:
                        days = int(val)
                        if days > 45:
                            return 'background-color: #dc3545; color: white'
                        elif days > 30:
                            return 'background-color: #ffc107'
                        elif days > 15:
                            return 'background-color: #28a745; color: white'
                        return ''
                    except:
                        return ''
                
                st.dataframe(
                    df_page.style.applymap(color_age, subset=["Días"]),
                    use_container_width=True,
                    height=500
                )
                
                # Análisis FIFO
                st.subheader("📊 Análisis FIFO")
                
                # Lotes críticos (> 30 días)
                critical_lots = df_display[df_display["Días"] > 30]
                if not critical_lots.empty:
                    st.warning(f"⚠️ {len(critical_lots)} lotes con más de 30 días de antigüedad")
                    st.dataframe(critical_lots, use_container_width=True)
                else:
                    st.success("✅ No hay lotes críticos por antigüedad")
                
                # Descargar
                csv = df_display.to_csv(index=False)
                st.download_button(
                    "📥 Descargar Trazabilidad",
                    csv,
                    f"trazabilidad_{selected_category.replace('/', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.warning("No se encontraron lotes para la categoría seleccionada")
        finally:
            st.session_state.stock_lotes_loading = False
            st.rerun()
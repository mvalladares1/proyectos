"""
Tab: Pallets por Recepción
Vista detallada de pallets, pesos y filtros por manejo/fruta.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from .shared import fmt_numero, fetch_pallets_data, fetch_pallets_excel

@st.fragment
def render(username: str, password: str):
    st.subheader("📦 Pallets por Recepción")
    st.caption("Consulta la cantidad de pallets y pesos totales por recepción")

    # Filtros superiores
    col1, col2, col3, col4 = st.columns([1, 1, 1.5, 1])
    with col1:
        fecha_inicio = st.date_input("Desde", datetime.now() - timedelta(days=7), format="DD/MM/YYYY", key="pallets_desde")
    with col2:
        fecha_fin = st.date_input("Hasta", datetime.now(), format="DD/MM/YYYY", key="pallets_hasta")
    
    with col3:
        sel_origen = st.multiselect("Planta / Origen", ["RFP", "VILKUN", "SAN JOSE"], default=["RFP", "VILKUN", "SAN JOSE"], placeholder="Todas", key="pallets_origen")
        
    with col4:
        st.write("") # Espaciador
        st.write("")
        btn_consultar = st.button("🔍 Consultar Pallets", type="primary", key="btn_consultar_pallets")

    # CARGAR DATOS
    if btn_consultar or st.session_state.get('pallets_loaded', False):
        st.session_state.pallets_loaded = True
        
        # Carga de datos desde API
        if btn_consultar or st.session_state.pallets_data is None:
            with st.spinner("Cargando información de pallets..."):
                data = fetch_pallets_data(username, password, fecha_inicio.strftime("%Y-%m-%d"), fecha_fin.strftime("%Y-%m-%d"), origen=sel_origen)
                st.session_state.pallets_data = data

        if st.session_state.pallets_data:
            df = pd.DataFrame(st.session_state.pallets_data)
            
            # Filtros dinámicos sobre el dataframe ya cargado
            st.markdown("---")
            st.markdown("#### 🔍 Filtros Adicionales")
            f1, f2, f3 = st.columns(3)
            with f1:
                manejos_raw = df['manejo'].unique()
                manejos_set = set()
                for m_str in manejos_raw:
                    for part in str(m_str).split(", "):
                        if part: manejos_set.add(part)
                
                sel_manejo = st.multiselect("Filtrar Manejo", sorted(list(manejos_set)), default=[], placeholder="Todos")
            
            with f2:
                frutas_raw = df['tipo_fruta'].unique()
                frutas_set = set()
                for f_str in frutas_raw:
                    for part in str(f_str).split(", "):
                        if part: frutas_set.add(part)
                
                sel_fruta = st.multiselect("Filtrar Tipo de Fruta", sorted(list(frutas_set)), default=[], placeholder="Todos")
            
            with f3:
                productores = sorted(df['productor'].unique())
                sel_prod = st.multiselect("Filtrar Productor", productores, default=[], placeholder="Todos")

            # Aplicar filtros al DataFrame
            df_filtered = df.copy()
            if sel_manejo:
                df_filtered = df_filtered[df_filtered['manejo'].apply(lambda x: any(m in str(x) for m in sel_manejo))]
            if sel_fruta:
                df_filtered = df_filtered[df_filtered['tipo_fruta'].apply(lambda x: any(f in str(x) for f in sel_fruta))]
            if sel_prod:
                df_filtered = df_filtered[df_filtered['productor'].isin(sel_prod)]

            # Resumen de KPIs
            total_pallets = df_filtered['cantidad_pallets'].sum()
            total_kg = df_filtered['total_kg'].sum()
            
            st.markdown("### 📊 Resumen")
            r1, r2, r3 = st.columns(3)
            with r1:
                st.metric("Recepciones", len(df_filtered))
            with r2:
                st.metric("Total Pallets", fmt_numero(total_pallets))
            with r3:
                st.metric("Total Kg", f"{fmt_numero(total_kg, 2)} kg")

            st.markdown("---")
            
            # Mostrar tabla detallada
            st.subheader(f"📋 Detalle de Pallets ({len(df_filtered)})")
            
            # Preparar copia para visualización formateada
            df_view = df_filtered.copy()
            
            # Ordenar por fecha descendente
            df_view = df_view.sort_values(by="fecha", ascending=False)
            
            st.dataframe(
                df_view[['fecha', 'origen', 'albaran', 'productor', 'guia_despacho', 'manejo', 'tipo_fruta', 'cantidad_pallets', 'total_kg']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "fecha": st.column_config.TextColumn("Fecha", width="small"),
                    "origen": st.column_config.TextColumn("Planta", width="small"),
                    "albaran": st.column_config.TextColumn("Albarán", width="medium"),
                    "productor": st.column_config.TextColumn("Productor", width="large"),
                    "guia_despacho": st.column_config.TextColumn("Guía Despacho", width="small"),
                    "manejo": st.column_config.TextColumn("Manejo", width="medium"),
                    "tipo_fruta": st.column_config.TextColumn("Fruta", width="small"),
                    "cantidad_pallets": st.column_config.NumberColumn("Pallets", format="%d"),
                    "total_kg": st.column_config.NumberColumn("Total Kg", format="%.2f")
                }
            )

            # Botón de exportación
            col_exp1, col_exp2 = st.columns([1, 4])
            with col_exp1:
                csv = df_filtered.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 CSV Simple",
                    data=csv,
                    file_name=f'pallets_recepcion_{fecha_inicio}_{fecha_fin}.csv',
                    mime='text/csv',
                    key="download_pallets_csv"
                )
            
            with col_exp2:
                if st.button("📗 Generar Excel Detallado (Pallet x Fila)", key="btn_generate_excel"):
                    with st.spinner("Generando Excel detallado..."):
                        xlsx = fetch_pallets_excel(
                            username, password, 
                            fecha_inicio.strftime("%Y-%m-%d"), 
                            fecha_fin.strftime("%Y-%m-%d"),
                            manejo=sel_manejo,
                            tipo_fruta=sel_fruta,
                            origen=sel_origen
                        )
                        if xlsx:
                            st.download_button(
                                label="⬇️ Descargar Excel Generado",
                                data=xlsx,
                                file_name=f'detalle_pallets_{fecha_inicio}_{fecha_fin}.xlsx',
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                key="download_pallets_xlsx"
                            )
                            st.success("✅ Excel generado correctamente")
                        else:
                            st.error("❌ Error al generar Excel. Verifica la conexión.")
        else:
            st.warning("No se encontraron datos para el rango seleccionado.")
    else:
        st.info("Selecciona el rango de fechas y presiona 'Consultar Pallets' para ver la información.")

    # Ayuda
    with st.expander("ℹ️ Información sobre este Tab"):
        st.markdown("""
        Este tab muestra la consolidación de pallets por cada recepción validada.
        - **Pallets:** Obtenidos de las líneas de movimiento con paquetes registrados (`stock.move.line`).
        - **Total Kg:** Sumatoria de los kilos hechos en cada línea filtrada.
        - **Filtros:** Puedes filtrar por Manejo (Convencional/Orgánico) y Tipo de Fruta si el producto lo tiene definido en su ficha.
        """)

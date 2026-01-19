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
            
            # Mostrar advertencia si hay guías duplicadas
            guias_dup = df_filtered[df_filtered['es_duplicada'] == True]
            
            if len(guias_dup) > 0:
                guias_duplicadas_lista = sorted(guias_dup['guia_despacho'].unique())
                
                # Banner de advertencia
                st.warning(f"⚠️ **{len(guias_duplicadas_lista)} guía(s) duplicada(s) detectada(s)**")
                
                # Sección especial para guías duplicadas agrupadas
                st.markdown("### 🔍 Guías Duplicadas Agrupadas (Para Comparación)")
                
                # Ordenar por guía y luego por fecha para agrupar duplicados
                df_dup_agrupado = guias_dup.copy()
                df_dup_agrupado = df_dup_agrupado.sort_values(by=["guia_despacho", "fecha"], ascending=[True, False])
                
                # Mostrar tabla de duplicados agrupados
                st.dataframe(
                    df_dup_agrupado[['guia_despacho', 'fecha', 'origen', 'albaran', 'productor', 'manejo', 'tipo_fruta', 'cantidad_pallets', 'total_kg', 'odoo_url']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "guia_despacho": st.column_config.TextColumn("⚠️ Guía Duplicada", width="medium", help="Guías agrupadas para comparación"),
                        "fecha": st.column_config.TextColumn("Fecha", width="small"),
                        "origen": st.column_config.TextColumn("Planta", width="small"),
                        "albaran": st.column_config.TextColumn("Albarán", width="medium"),
                        "productor": st.column_config.TextColumn("Productor", width="large"),
                        "manejo": st.column_config.TextColumn("Manejo", width="medium"),
                        "tipo_fruta": st.column_config.TextColumn("Fruta", width="small"),
                        "cantidad_pallets": st.column_config.NumberColumn("Pallets", format="%d"),
                        "total_kg": st.column_config.NumberColumn("Total Kg", format="%.2f"),
                        "odoo_url": st.column_config.LinkColumn(
                            "Ver en Odoo",
                            width="small",
                            help="Click para abrir en Odoo",
                            display_text="🔗 Abrir"
                        )
                    }
                )
                
                # Resumen por guía duplicada
                st.markdown("#### 📊 Resumen de Duplicados")
                for guia in guias_duplicadas_lista:
                    with st.expander(f"🔸 Guía: **{guia}** ({len(df_dup_agrupado[df_dup_agrupado['guia_despacho'] == guia])} recepciones)"):
                        df_guia = df_dup_agrupado[df_dup_agrupado['guia_despacho'] == guia]
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Pallets", int(df_guia['cantidad_pallets'].sum()))
                        with col2:
                            st.metric("Total Kg", f"{df_guia['total_kg'].sum():.2f}")
                        with col3:
                            st.metric("Recepciones", len(df_guia))
                        
                        # Tabla detallada de esta guía
                        st.dataframe(
                            df_guia[['fecha', 'albaran', 'productor', 'origen', 'cantidad_pallets', 'total_kg', 'odoo_url']],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "fecha": "Fecha",
                                "albaran": "Albarán",
                                "productor": "Productor",
                                "origen": "Planta",
                                "cantidad_pallets": st.column_config.NumberColumn("Pallets", format="%d"),
                                "total_kg": st.column_config.NumberColumn("Kg", format="%.2f"),
                                "odoo_url": st.column_config.LinkColumn("Odoo", display_text="🔗")
                            }
                        )
                
                st.markdown("---")
            
            # Mostrar tabla completa
            st.subheader(f"📋 Detalle Completo de Pallets ({len(df_filtered)})")
            
            # Preparar copia para visualización formateada
            df_view = df_filtered.copy()
            
            # Ordenar por guía (para agrupar duplicados) y luego por fecha
            df_view = df_view.sort_values(by=["guia_despacho", "fecha"], ascending=[True, False])
            
            # Crear columna visual para guías duplicadas
            def format_guia_duplicada(row):
                guia = row.get('guia_despacho', '')
                es_duplicada = row.get('es_duplicada', False)
                if es_duplicada and guia:
                    return f"⚠️ {guia}"
                return guia
            
            df_view['guia_display'] = df_view.apply(format_guia_duplicada, axis=1)
            
            st.dataframe(
                df_view[['fecha', 'origen', 'albaran', 'productor', 'guia_display', 'manejo', 'tipo_fruta', 'cantidad_pallets', 'total_kg', 'odoo_url']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "fecha": st.column_config.TextColumn("Fecha", width="small"),
                    "origen": st.column_config.TextColumn("Planta", width="small"),
                    "albaran": st.column_config.TextColumn("Albarán", width="medium"),
                    "productor": st.column_config.TextColumn("Productor", width="large"),
                    "guia_display": st.column_config.TextColumn("Guía Despacho", width="medium", help="⚠️ indica guías duplicadas"),
                    "manejo": st.column_config.TextColumn("Manejo", width="medium"),
                    "tipo_fruta": st.column_config.TextColumn("Fruta", width="small"),
                    "cantidad_pallets": st.column_config.NumberColumn("Pallets", format="%d"),
                    "total_kg": st.column_config.NumberColumn("Total Kg", format="%.2f"),
                    "odoo_url": st.column_config.LinkColumn(
                        "Ver en Odoo",
                        width="small",
                        help="Click para abrir en Odoo",
                        display_text="🔗 Abrir"
                    )
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
        
        ### 📊 Características:
        - **Pallets:** Obtenidos de las líneas de movimiento con paquetes registrados (`stock.move.line`).
        - **Total Kg:** Sumatoria de los kilos hechos en cada línea filtrada.
        - **Filtros:** Puedes filtrar por Manejo (Convencional/Orgánico) y Tipo de Fruta si el producto lo tiene definido en su ficha.
        
        ### 🔍 Detección de Duplicados:
        - **Guías Duplicadas:** Las guías de despacho que aparecen en múltiples recepciones se marcan con ⚠️.
        - **Vista Agrupada:** Cuando hay duplicados, se muestra una sección especial con las guías agrupadas para facilitar la comparación.
        - **Resumen por Guía:** Cada guía duplicada tiene un resumen expandible con métricas totales (pallets, kg, recepciones).
        
        ### 🔗 Enlaces a Odoo:
        - **Ver en Odoo:** Click en el enlace 🔗 para abrir la recepción directamente en Odoo.
        - Formato: Abre el formulario del picking en una nueva pestaña del navegador.
        
        ### 📋 Tablas Disponibles:
        1. **Guías Duplicadas Agrupadas:** Solo muestra las guías que están duplicadas, ordenadas por número de guía para facilitar comparación.
        2. **Detalle Completo:** Muestra todas las recepciones, ordenadas por guía y fecha (duplicados quedan juntos).
        """)

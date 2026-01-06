"""
Gráficos para el módulo de Producción
"""
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta


def grafico_congelado_semanal(mos_data: list):
    """
    Gráficos de barras separados por túnel de congelado.
    Muestra Kg congelados por semana para cada túnel.
    Crea un gráfico independiente por cada túnel.
    
    Args:
        mos_data: Lista de órdenes de fabricación (MOs)
    """
    if not mos_data:
        st.info("No hay datos de congelado disponibles")
        return
    
    # Preparar datos por túnel
    datos_por_tunel = {}
    salas_encontradas = set()
    
    for mo in mos_data:
        sala = mo.get('sala', '').strip()
        sala_tipo = mo.get('sala_tipo', '').strip()
        product_name = mo.get('product_name', '').strip()
        salas_encontradas.add(f"{sala} ({sala_tipo})")
        
        # CASO ESPECIAL: Túnel Continuo por nombre de producto
        es_tunel_continuo = '[1.4]' in product_name and 'TÚNEL CONTÍNUO' in product_name.upper()
        
        # SOLO túneles de congelado - filtro estricto
        sala_lower = sala.lower()
        es_tunel_estatico = sala_tipo == 'CONGELADO' and ('tunel' in sala_lower or 'túnel' in sala_lower)
        
        if not (es_tunel_estatico or es_tunel_continuo):
            continue
        
        # Usar nombre específico para túnel continuo
        if es_tunel_continuo:
            tunel_nombre = 'Tunel Continuo'
        else:
            tunel_nombre = sala
        
        # Obtener fecha
        fecha_str = mo.get('fecha') or mo.get('fecha_inicio') or mo.get('fecha_fin')
        if not fecha_str:
            continue
        
        try:
            fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
        except:
            try:
                fecha = datetime.strptime(fecha_str[:10], '%Y-%m-%d')
            except:
                continue
        
        # Obtener semana ISO
        iso_year, iso_week, _ = fecha.isocalendar()
        semana_label = f"S{iso_week:02d}"
        
        # Obtener kg procesados (salida)
        # EXCLUIR subproductos intermedios (PROCESO/TUNEL en nombre)
        product_upper = product_name.upper()
        es_subproducto = 'PROCESO' in product_upper or 'TUNEL' in product_upper or 'TÚNEL' in product_upper
        
        kg_pt = mo.get('kg_pt', 0) or 0
        
        if kg_pt > 0 and not es_subproducto:
            if tunel_nombre not in datos_por_tunel:
                datos_por_tunel[tunel_nombre] = []
            
            datos_por_tunel[tunel_nombre].append({
                'Semana': semana_label,
                'Kg': kg_pt,
                'iso_year': iso_year,
                'iso_week': iso_week
            })
    
    if not datos_por_tunel:
        st.warning(f"No se encontraron datos de túneles de congelado en el período seleccionado")
        with st.expander("🔍 Debug: Ver datos disponibles"):
            st.write(f"**Total de MOs recibidos:** {len(mos_data)}")
            salas_unicas = sorted(list(salas_encontradas))
            st.write(f"**Total de salas diferentes:** {len(salas_unicas)}")
            st.write("**Salas encontradas:**")
            for sala in salas_unicas:
                st.write(f"- '{sala}'")
            
            if mos_data:
                st.write("---")
                st.write("**Primer MO de ejemplo:**")
                primer_mo = mos_data[0]
                st.json(primer_mo)
        return
    
    # Crear un gráfico por cada túnel
    for tunel_nombre in sorted(datos_por_tunel.keys()):
        st.markdown(f"#### ❄️ {tunel_nombre}")
        
        datos_tunel = datos_por_tunel[tunel_nombre]
        df = pd.DataFrame(datos_tunel)
        
        # Agrupar por semana
        df_grouped = df.groupby(['Semana', 'iso_year', 'iso_week'], as_index=False).agg({'Kg': 'sum'})
        
        # Ordenar por semana ISO
        df_grouped = df_grouped.sort_values(['iso_year', 'iso_week'])
        
        # Crear gráfico de barras
        chart = alt.Chart(df_grouped).mark_bar(color='steelblue').encode(
            x=alt.X('Semana:N', 
                    title='Semana ISO',
                    sort=df_grouped['Semana'].unique().tolist(),
                    axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('Kg:Q', 
                    title='Kg Congelados',
                    axis=alt.Axis(format=',.0f')),
            tooltip=[
                alt.Tooltip('Semana:N', title='Semana'),
                alt.Tooltip('Kg:Q', title='Kg Congelados', format=',.0f')
            ]
        ).properties(
            title=f'Kg Congelados por Semana - {tunel_nombre}',
            height=350
        )
        
        st.altair_chart(chart, use_container_width=True)
        
        # Tabla resumen para este túnel
        with st.expander(f"📊 Ver tabla de datos - {tunel_nombre}"):
            st.markdown("**Kg Congelados por Semana**")
            df_table = df_grouped[['Semana', 'Kg']].copy()
            df_table['Kg'] = df_table['Kg'].apply(lambda x: f"{x:,.0f}")
            
            # Agregar total
            total_kg = df_grouped['Kg'].sum()
            df_total = pd.DataFrame([{'Semana': 'TOTAL', 'Kg': f"{total_kg:,.0f}"}])
            df_table = pd.concat([df_table, df_total], ignore_index=True)
            
            st.dataframe(df_table, use_container_width=True, hide_index=True)
        
        st.markdown("---")  # Separador entre túneles


def grafico_vaciado_por_sala(mos_data: list):
    """
    Gráficos de barras separados por sala con desglose de líneas.
    Muestra rendimiento individual de cada línea dentro de su sala.
    Crea un gráfico independiente por cada sala.
    
    Args:
        mos_data: Lista de órdenes de fabricación (MOs)
    """
    if not mos_data:
        st.info("No hay datos de proceso disponibles")
        return
    
    # Preparar datos
    datos_por_sala = {}
    salas_encontradas = set()
    
    for mo in mos_data:
        sala_completa = mo.get('sala', '').strip()
        sala_tipo = mo.get('sala_tipo', '').strip()
        product_name = mo.get('product_name', '').strip()
        salas_encontradas.add(f"{sala_completa} ({sala_tipo})")
        
        # EXCLUIR túnel continuo (ya está en congelado)
        es_tunel_continuo = '[1.4]' in product_name and 'TÚNEL CONTÍNUO' in product_name.upper()
        if es_tunel_continuo:
            continue
        
        # SOLO salas de proceso - filtro estricto
        sala_lower = sala_completa.lower()
        tiene_tunel = 'tunel' in sala_lower or 'túnel' in sala_lower
        
        if sala_tipo != 'PROCESO' or tiene_tunel or not sala_completa or sala_completa == 'SIN SALA':
            continue
        
        # Extraer sala y línea
        if ' - ' in sala_completa:
            partes = sala_completa.split(' - ', 1)
            sala = partes[0].strip()
            linea = partes[1].strip()
        else:
            sala = sala_completa
            linea = 'Principal'
        
        # Obtener fecha
        fecha_str = mo.get('fecha') or mo.get('fecha_inicio') or mo.get('fecha_fin')
        if not fecha_str:
            continue
        
        try:
            fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
        except:
            try:
                fecha = datetime.strptime(fecha_str[:10], '%Y-%m-%d')
            except:
                continue
        
        # Obtener semana ISO
        iso_year, iso_week, _ = fecha.isocalendar()
        semana_label = f"S{iso_week:02d}"
        
        # Obtener kg procesados y rendimiento
        # EXCLUIR subproductos intermedios (PROCESO/TUNEL en nombre)
        product_upper = product_name.upper()
        es_subproducto = 'PROCESO' in product_upper or 'TUNEL' in product_upper or 'TÚNEL' in product_upper
        
        kg_pt = mo.get('kg_pt', 0) or 0
        rendimiento = mo.get('rendimiento', 0) or 0
        
        if kg_pt > 0 and not es_subproducto:
            if sala not in datos_por_sala:
                datos_por_sala[sala] = []
            
            datos_por_sala[sala].append({
                'Semana': semana_label,
                'Línea': linea,
                'Sala-Línea': f"{sala} - {linea}",
                'Kg PT': kg_pt,
                'Rendimiento': rendimiento,
                'iso_year': iso_year,
                'iso_week': iso_week
            })
    
    if not datos_por_sala:
        st.warning(f"No se encontraron datos de proceso/vaciado en el período seleccionado")
        with st.expander("🔍 Debug: Ver datos disponibles"):
            st.write(f"**Total de MOs recibidos:** {len(mos_data)}")
            salas_unicas = sorted(list(salas_encontradas))
            st.write(f"**Total de salas diferentes:** {len(salas_unicas)}")
            st.write("**Salas encontradas:**")
            for sala in salas_unicas:
                st.write(f"- '{sala}'")
            
            if mos_data:
                st.write("---")
                st.write("**Primer MO de ejemplo:**")
                primer_mo = mos_data[0]
                st.json(primer_mo)
        return
    
    # Crear un gráfico por cada sala
    for sala_nombre in sorted(datos_por_sala.keys()):
        st.markdown(f"#### 🏭 {sala_nombre}")
        
        datos_sala = datos_por_sala[sala_nombre]
        df = pd.DataFrame(datos_sala)
        
        # Agrupar por semana y línea
        df_grouped = df.groupby(['Semana', 'Línea', 'Sala-Línea', 'iso_year', 'iso_week'], as_index=False).agg({
            'Kg PT': 'sum',
            'Rendimiento': 'mean'
        })
        
        # Ordenar por semana ISO
        df_grouped = df_grouped.sort_values(['iso_year', 'iso_week'])
        
        # Crear dos pestañas: Kg PT y Rendimiento
        tab_kg, tab_rend = st.tabs(["📊 Kg Procesados", "📈 Rendimiento %"])
        
        with tab_kg:
            # Gráfico de Kg procesados
            chart_kg = alt.Chart(df_grouped).mark_bar().encode(
                x=alt.X('Semana:N', 
                        title='Semana ISO',
                        sort=df_grouped['Semana'].unique().tolist(),
                        axis=alt.Axis(labelAngle=-45)),
                y=alt.Y('Kg PT:Q', 
                        title='Kg Procesados',
                        axis=alt.Axis(format=',.0f')),
                color=alt.Color('Línea:N',
                               title='Línea',
                               scale=alt.Scale(scheme='category10')),
                tooltip=[
                    alt.Tooltip('Semana:N', title='Semana'),
                    alt.Tooltip('Línea:N', title='Línea'),
                    alt.Tooltip('Kg PT:Q', title='Kg Procesados', format=',.0f')
                ]
            ).properties(
                title=f'Kg Procesados por Semana - {sala_nombre}',
                height=350
            )
            
            st.altair_chart(chart_kg, use_container_width=True)
        
        with tab_rend:
            # Verificar si hay datos de rendimiento
            if df_grouped['Rendimiento'].sum() == 0 or df_grouped['Rendimiento'].isna().all():
                st.warning("No hay datos de rendimiento disponibles para esta sala")
            else:
                # Gráfico de Rendimiento
                chart_rend = alt.Chart(df_grouped).mark_bar().encode(
                    x=alt.X('Semana:N', 
                            title='Semana ISO',
                            sort=df_grouped['Semana'].unique().tolist(),
                            axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y('Rendimiento:Q', 
                            title='Rendimiento %',
                            axis=alt.Axis(format='.1f')),
                    color=alt.Color('Línea:N',
                                   title='Línea',
                                   scale=alt.Scale(scheme='category10')),
                    tooltip=[
                        alt.Tooltip('Semana:N', title='Semana'),
                        alt.Tooltip('Línea:N', title='Línea'),
                        alt.Tooltip('Rendimiento:Q', title='Rendimiento %', format='.2f')
                    ]
                ).properties(
                    title=f'Rendimiento % por Semana - {sala_nombre}',
                    height=350
                )
                
                st.altair_chart(chart_rend, use_container_width=True)
        
        # Tabla resumen para esta sala
        with st.expander(f"📊 Ver tabla de datos - {sala_nombre}"):
            # Tabla de Kg PT
            st.markdown("**Kg Procesados por Línea y Semana**")
            df_pivot_kg = df_grouped.pivot_table(
                index='Línea', 
                columns='Semana', 
                values='Kg PT', 
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            
            # Agregar total por línea
            df_pivot_kg['TOTAL'] = df_pivot_kg.iloc[:, 1:].sum(axis=1)
            
            # Formatear números
            for col in df_pivot_kg.columns[1:]:
                df_pivot_kg[col] = df_pivot_kg[col].apply(lambda x: f"{x:,.0f}")
            
            st.dataframe(df_pivot_kg, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # Tabla de Rendimiento
            st.markdown("**Rendimiento % Promedio por Línea y Semana**")
            df_pivot_rend = df_grouped.pivot_table(
                index='Línea', 
                columns='Semana', 
                values='Rendimiento', 
                aggfunc='mean',
                fill_value=0
            ).reset_index()
            
            # Formatear números
            for col in df_pivot_rend.columns[1:]:
                df_pivot_rend[col] = df_pivot_rend[col].apply(lambda x: f"{x:.2f}%")
            
            st.dataframe(df_pivot_rend, use_container_width=True, hide_index=True)
        
        st.markdown("---")  # Separador entre salas

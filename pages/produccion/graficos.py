"""
Gráficos para el módulo de Producción
"""
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta


def grafico_congelado_semanal(mos_data: list):
    """
    Gráfico de barras agrupado por semana para túneles de congelado.
    Muestra Kg congelados por semana para cada túnel.
    
    Args:
        mos_data: Lista de órdenes de fabricación (MOs)
    """
    if not mos_data:
        st.info("No hay datos de congelado disponibles")
        return
    
    # Preparar datos
    datos_grafico = []
    salas_encontradas = set()
    
    for mo in mos_data:
        sala = mo.get('sala', '').strip()
        sala_tipo = mo.get('sala_tipo', '').strip()
        product_name = mo.get('product_name', '').strip()
        salas_encontradas.add(f"{sala} ({sala_tipo})")
        
        # CASO ESPECIAL: Túnel Continuo por nombre de producto
        es_tunel_continuo = '[1.4]' in product_name and 'TÚNEL CONTÍNUO' in product_name.upper()
        
        # SOLO túneles de congelado - filtro estricto
        # Debe cumplir ALGUNA de estas condiciones:
        # 1. (sala_tipo == 'CONGELADO' Y nombre contiene "tunel")
        # 2. Es túnel continuo por nombre de producto
        sala_lower = sala.lower()
        es_tunel_estatico = sala_tipo == 'CONGELADO' and ('tunel' in sala_lower or 'túnel' in sala_lower)
        
        if not (es_tunel_estatico or es_tunel_continuo):
            continue
        
        # Usar nombre específico para túnel continuo
        if es_tunel_continuo:
            sala = 'Tunel Continuo'
        
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
        kg_pt = mo.get('kg_pt', 0) or 0
        
        if kg_pt > 0:
            datos_grafico.append({
                'Semana': semana_label,
                'Túnel': sala,
                'Kg': kg_pt,
                'iso_year': iso_year,
                'iso_week': iso_week
            })
    
    if not datos_grafico:
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
    
    # Crear DataFrame
    df = pd.DataFrame(datos_grafico)
    
    # Agrupar por semana y túnel
    df_grouped = df.groupby(['Semana', 'Túnel', 'iso_year', 'iso_week'], as_index=False).agg({'Kg': 'sum'})
    
    # Ordenar por semana ISO
    df_grouped = df_grouped.sort_values(['iso_year', 'iso_week'])
    
    # Crear gráfico de barras agrupadas con Altair
    chart = alt.Chart(df_grouped).mark_bar().encode(
        x=alt.X('Semana:N', 
                title='Semana ISO',
                sort=df_grouped['Semana'].unique().tolist(),
                axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Kg:Q', 
                title='Kg Congelados',
                axis=alt.Axis(format=',.0f')),
        color=alt.Color('Túnel:N',
                       title='Túnel de Congelado',
                       scale=alt.Scale(scheme='tableau10')),
        tooltip=[
            alt.Tooltip('Semana:N', title='Semana'),
            alt.Tooltip('Túnel:N', title='Túnel'),
            alt.Tooltip('Kg:Q', title='Kg Congelados', format=',.0f')
        ]
    ).properties(
        title='📈 Kg Congelados por Semana y Túnel',
        height=400
    ).configure_axis(
        labelFontSize=11,
        titleFontSize=13
    ).configure_title(
        fontSize=16,
        anchor='start'
    )
    
    st.altair_chart(chart, use_container_width=True)
    
    # Tabla resumen
    with st.expander("📊 Ver tabla de datos"):
        df_pivot = df_grouped.pivot_table(
            index='Semana', 
            columns='Túnel', 
            values='Kg', 
            aggfunc='sum',
            fill_value=0
        ).reset_index()
        
        # Agregar total por semana
        df_pivot['TOTAL'] = df_pivot.iloc[:, 1:].sum(axis=1)
        
        # Formatear números
        for col in df_pivot.columns[1:]:
            df_pivot[col] = df_pivot[col].apply(lambda x: f"{x:,.0f}")
        
        st.dataframe(df_pivot, use_container_width=True, hide_index=True)


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
        kg_pt = mo.get('kg_pt', 0) or 0
        rendimiento = mo.get('rendimiento', 0) or 0
        
        if kg_pt > 0:
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
            # Gráfico de Rendimiento
            chart_rend = alt.Chart(df_grouped).mark_bar().encode(
                x=alt.X('Semana:N', 
                        title='Semana ISO',
                        sort=df_grouped['Semana'].unique().tolist(),
                        axis=alt.Axis(labelAngle=-45)),
                y=alt.Y('Rendimiento:Q', 
                        title='Rendimiento %',
                        axis=alt.Axis(format='.1f'),
                        scale=alt.Scale(domain=[0, 100])),
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

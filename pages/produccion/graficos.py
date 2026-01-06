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
        sala = mo.get('sala_proceso', '').strip()
        salas_encontradas.add(sala)
        
        # Verificar si es un túnel (búsqueda flexible)
        sala_lower = sala.lower()
        if not ('tunel' in sala_lower or 'túnel' in sala_lower):
            continue
        
        # Obtener fecha
        fecha_str = mo.get('fecha_inicio') or mo.get('fecha_fin') or mo.get('fecha_planificada')
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
        with st.expander("🔍 Debug: Ver salas encontradas en los datos"):
            salas_unicas = sorted(list(salas_encontradas))
            st.write(f"Total de salas diferentes: {len(salas_unicas)}")
            for sala in salas_unicas:
                st.write(f"- {sala}")
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
    Gráfico de barras agrupado por sala con desglose de líneas.
    Muestra rendimiento individual de cada línea dentro de su sala.
    
    Args:
        mos_data: Lista de órdenes de fabricación (MOs)
    """
    if not mos_data:
        st.info("No hay datos de proceso disponibles")
        return
    
    # Preparar datos
    datos_grafico = []
    salas_encontradas = set()
    
    for mo in mos_data:
        sala_completa = mo.get('sala_proceso', '').strip()
        salas_encontradas.add(sala_completa)
        
        # Excluir túneles (búsqueda flexible)
        sala_lower = sala_completa.lower()
        if 'tunel' in sala_lower or 'túnel' in sala_lower:
            continue
        
        if not sala_completa or sala_completa == 'SIN SALA':
            continue
        
        # Extraer sala y línea
        # Formato esperado: "Sala 1 - Linea Retail", "Sala 2 - Linea Granel", etc.
        if ' - ' in sala_completa:
            partes = sala_completa.split(' - ', 1)
            sala = partes[0].strip()
            linea = partes[1].strip()
        else:
            sala = sala_completa
            linea = 'Principal'
        
        # Obtener fecha
        fecha_str = mo.get('fecha_inicio') or mo.get('fecha_fin') or mo.get('fecha_planificada')
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
            datos_grafico.append({
                'Semana': semana_label,
                'Sala': sala,
                'Línea': linea,
                'Sala-Línea': f"{sala} - {linea}",
                'Kg PT': kg_pt,
                'Rendimiento': rendimiento,
                'iso_year': iso_year,
                'iso_week': iso_week
            })
    
    if not datos_grafico:
        st.warning(f"No se encontraron datos de proceso/vaciado en el período seleccionado")
        with st.expander("🔍 Debug: Ver salas encontradas en los datos"):
            salas_unicas = sorted(list(salas_encontradas))
            st.write(f"Total de salas diferentes: {len(salas_unicas)}")
            for sala in salas_unicas:
                st.write(f"- {sala}")
        return
    
    # Crear DataFrame
    df = pd.DataFrame(datos_grafico)
    
    # Agrupar por semana, sala y línea
    df_grouped = df.groupby(['Semana', 'Sala', 'Línea', 'Sala-Línea', 'iso_year', 'iso_week'], as_index=False).agg({
        'Kg PT': 'sum',
        'Rendimiento': 'mean'  # Promedio de rendimiento
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
            color=alt.Color('Sala-Línea:N',
                           title='Sala - Línea',
                           scale=alt.Scale(scheme='tableau20')),
            tooltip=[
                alt.Tooltip('Semana:N', title='Semana'),
                alt.Tooltip('Sala:N', title='Sala'),
                alt.Tooltip('Línea:N', title='Línea'),
                alt.Tooltip('Kg PT:Q', title='Kg Procesados', format=',.0f')
            ]
        ).properties(
            title='📊 Kg Procesados por Semana, Sala y Línea',
            height=400
        ).configure_axis(
            labelFontSize=11,
            titleFontSize=13
        ).configure_title(
            fontSize=16,
            anchor='start'
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
            color=alt.Color('Sala-Línea:N',
                           title='Sala - Línea',
                           scale=alt.Scale(scheme='tableau20')),
            tooltip=[
                alt.Tooltip('Semana:N', title='Semana'),
                alt.Tooltip('Sala:N', title='Sala'),
                alt.Tooltip('Línea:N', title='Línea'),
                alt.Tooltip('Rendimiento:Q', title='Rendimiento %', format='.2f')
            ]
        ).properties(
            title='📈 Rendimiento % por Semana, Sala y Línea',
            height=400
        ).configure_axis(
            labelFontSize=11,
            titleFontSize=13
        ).configure_title(
            fontSize=16,
            anchor='start'
        )
        
        st.altair_chart(chart_rend, use_container_width=True)
    
    # Tabla resumen
    with st.expander("📊 Ver tabla de datos"):
        # Tabla de Kg PT
        st.markdown("**Kg Procesados por Sala-Línea y Semana**")
        df_pivot_kg = df_grouped.pivot_table(
            index='Sala-Línea', 
            columns='Semana', 
            values='Kg PT', 
            aggfunc='sum',
            fill_value=0
        ).reset_index()
        
        # Agregar total por sala-línea
        df_pivot_kg['TOTAL'] = df_pivot_kg.iloc[:, 1:].sum(axis=1)
        
        # Formatear números
        for col in df_pivot_kg.columns[1:]:
            df_pivot_kg[col] = df_pivot_kg[col].apply(lambda x: f"{x:,.0f}")
        
        st.dataframe(df_pivot_kg, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Tabla de Rendimiento
        st.markdown("**Rendimiento % Promedio por Sala-Línea y Semana**")
        df_pivot_rend = df_grouped.pivot_table(
            index='Sala-Línea', 
            columns='Semana', 
            values='Rendimiento', 
            aggfunc='mean',
            fill_value=0
        ).reset_index()
        
        # Formatear números
        for col in df_pivot_rend.columns[1:]:
            df_pivot_rend[col] = df_pivot_rend[col].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(df_pivot_rend, use_container_width=True, hide_index=True)

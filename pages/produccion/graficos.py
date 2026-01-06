"""
Gráficos para el módulo de Producción
"""
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta


def _agrupar_por_periodo(fecha: datetime, agrupacion: str):
    """
    Agrupa una fecha según el período especificado.
    
    Args:
        fecha: Fecha a agrupar
        agrupacion: "Día", "Semana" o "Mes"
    
    Returns:
        tuple: (label, sort_year, sort_value)
    """
    if agrupacion == "Día":
        return (
            fecha.strftime("%d/%m"),  # Label: 06/01
            fecha.year,
            fecha.timetuple().tm_yday  # Día del año para ordenar
        )
    elif agrupacion == "Mes":
        return (
            fecha.strftime("%b"),  # Label: Ene, Feb
            fecha.year,
            fecha.month
        )
    else:  # Semana (default)
        iso_year, iso_week, _ = fecha.isocalendar()
        return (
            f"S{iso_week:02d}",  # Label: S01, S02
            iso_year,
            iso_week
        )


def grafico_congelado_semanal(mos_data: list, agrupacion: str = "Semana"):
    """
    Gráficos de barras separados por túnel de congelado.
    Muestra Kg congelados por período (día/semana/mes) para cada túnel.
    Crea un gráfico independiente por cada túnel.
    
    Args:
        mos_data: Lista de órdenes de fabricación (MOs)
        agrupacion: "Día", "Semana" o "Mes"
    """
    if not mos_data:
        st.info("No hay datos de congelado disponibles")
        return
    
    periodo_label = {"Día": "Diario", "Semana": "Semana ISO", "Mes": "Mes"}.get(agrupacion, "Semana ISO")
    
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
        
        # Obtener período de agrupación
        periodo_label_str, sort_year, sort_value = _agrupar_por_periodo(fecha, agrupacion)
        
        # Obtener kg procesados (salida)
        kg_pt = mo.get('kg_pt', 0) or 0
        
        if kg_pt > 0:
            if tunel_nombre not in datos_por_tunel:
                datos_por_tunel[tunel_nombre] = []
            
            datos_por_tunel[tunel_nombre].append({
                'Periodo': periodo_label_str,
                'Kg': kg_pt,
                'sort_year': sort_year,
                'sort_value': sort_value
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
        
        # Agrupar por período
        df_grouped = df.groupby(['Periodo', 'sort_year', 'sort_value'], as_index=False).agg({'Kg': 'sum'})
        
        # Ordenar por año y valor
        df_grouped = df_grouped.sort_values(['sort_year', 'sort_value'])
        
        # Crear gráfico de barras
        chart = alt.Chart(df_grouped).mark_bar(color='steelblue').encode(
            x=alt.X('Periodo:N', 
                    title=periodo_label,
                    sort=df_grouped['Periodo'].unique().tolist(),
                    axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('Kg:Q', 
                    title='Kg Congelados',
                    axis=alt.Axis(format=',.0f')),
            tooltip=[
                alt.Tooltip('Periodo:N', title=periodo_label),
                alt.Tooltip('Kg:Q', title='Kg Congelados', format=',.0f')
            ]
        ).properties(
            title=f'Kg Congelados por {agrupacion} - {tunel_nombre}',
            height=350
        )
        
        st.altair_chart(chart, use_container_width=True)
        
        # Tabla resumen para este túnel
        with st.expander(f"📊 Ver tabla de datos - {tunel_nombre}"):
            st.markdown(f"**Kg Congelados por {agrupacion}**")
            df_table = df_grouped[['Periodo', 'Kg']].copy()
            df_table['Kg'] = df_table['Kg'].apply(lambda x: f"{x:,.0f}")
            
            # Agregar total
            total_kg = df_grouped['Kg'].sum()
            df_total = pd.DataFrame([{'Periodo': 'TOTAL', 'Kg': f"{total_kg:,.0f}"}])
            df_table = pd.concat([df_table, df_total], ignore_index=True)
            
            st.dataframe(df_table, use_container_width=True, hide_index=True)
        
        st.markdown("---")  # Separador entre túneles


def grafico_vaciado_por_sala(mos_data: list, agrupacion: str = "Semana"):
    """
    Gráficos de barras separados por sala con desglose de líneas.
    Muestra rendimiento individual de cada línea dentro de su sala.
    Crea un gráfico independiente por cada sala.
    
    Args:
        mos_data: Lista de órdenes de fabricación (MOs)
        agrupacion: "Día", "Semana" o "Mes"
    """
    if not mos_data:
        st.info("No hay datos de proceso disponibles")
        return
    
    periodo_label = {"Día": "Día", "Semana": "Semana ISO", "Mes": "Mes"}.get(agrupacion, "Semana ISO")
    
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
        
        # Obtener período de agrupación
        periodo_label_str, sort_year, sort_value = _agrupar_por_periodo(fecha, agrupacion)
        
        # Obtener kg procesados y rendimiento
        kg_pt = mo.get('kg_pt', 0) or 0
        rendimiento = mo.get('rendimiento', 0) or 0
        
        if kg_pt > 0:
            if sala not in datos_por_sala:
                datos_por_sala[sala] = []
            
            datos_por_sala[sala].append({
                'Periodo': periodo_label_str,
                'Línea': linea,
                'Sala-Línea': f"{sala} - {linea}",
                'Kg PT': kg_pt,
                'Rendimiento': rendimiento,
                'sort_year': sort_year,
                'sort_value': sort_value
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
        
        # Agrupar por período y línea
        df_grouped = df.groupby(['Periodo', 'Línea', 'Sala-Línea', 'sort_year', 'sort_value'], as_index=False).agg({
            'Kg PT': 'sum',
            'Rendimiento': 'mean'
        })
        
        # Ordenar por año y valor
        df_grouped = df_grouped.sort_values(['sort_year', 'sort_value'])
        
        # Crear dos pestañas: Kg PT y Rendimiento
        tab_kg, tab_rend = st.tabs(["📊 Kg Procesados", "📈 Rendimiento %"])
        
        with tab_kg:
            # Gráfico de Kg procesados
            chart_kg = alt.Chart(df_grouped).mark_bar().encode(
                x=alt.X('Periodo:N', 
                        title=periodo_label,
                        sort=df_grouped['Periodo'].unique().tolist(),
                        axis=alt.Axis(labelAngle=-45)),
                y=alt.Y('Kg PT:Q', 
                        title='Kg Procesados',
                        axis=alt.Axis(format=',.0f')),
                color=alt.Color('Línea:N',
                               title='Línea',
                               scale=alt.Scale(scheme='category10')),
                tooltip=[
                    alt.Tooltip('Periodo:N', title=periodo_label),
                    alt.Tooltip('Línea:N', title='Línea'),
                    alt.Tooltip('Kg PT:Q', title='Kg Procesados', format=',.0f')
                ]
            ).properties(
                title=f'Kg Procesados por {agrupacion} - {sala_nombre}',
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
                    x=alt.X('Periodo:N', 
                            title=periodo_label,
                            sort=df_grouped['Periodo'].unique().tolist(),
                            axis=alt.Axis(labelAngle=-45)),
                    y=alt.Y('Rendimiento:Q', 
                            title='Rendimiento %',
                            axis=alt.Axis(format='.1f')),
                    color=alt.Color('Línea:N',
                                   title='Línea',
                                   scale=alt.Scale(scheme='category10')),
                    tooltip=[
                        alt.Tooltip('Periodo:N', title=periodo_label),
                        alt.Tooltip('Línea:N', title='Línea'),
                        alt.Tooltip('Rendimiento:Q', title='Rendimiento %', format='.2f')
                    ]
                ).properties(
                    title=f'Rendimiento % por {agrupacion} - {sala_nombre}',
                    height=350
                )
                
                st.altair_chart(chart_rend, use_container_width=True)
        
        # Tabla resumen para esta sala
        with st.expander(f"📊 Ver tabla de datos - {sala_nombre}"):
            # Tabla de Kg PT
            st.markdown(f"**Kg Procesados por Línea y {agrupacion}**")
            df_pivot_kg = df_grouped.pivot_table(
                index='Línea', 
                columns='Periodo', 
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
            st.markdown(f"**Rendimiento % Promedio por Línea y {agrupacion}**")
            df_pivot_rend = df_grouped.pivot_table(
                index='Línea', 
                columns='Periodo', 
                values='Rendimiento', 
                aggfunc='mean',
                fill_value=0
            ).reset_index()
            
            # Formatear números
            for col in df_pivot_rend.columns[1:]:
                df_pivot_rend[col] = df_pivot_rend[col].apply(lambda x: f"{x:.2f}%")
            
            st.dataframe(df_pivot_rend, use_container_width=True, hide_index=True)
        
        st.markdown("---")  # Separador entre salas

"""
Gráficos para el módulo de Producción
"""
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta


def fmt_numero(valor, decimales=0):
    """Formatea número con separador de miles."""
    try:
        v = float(valor)
        if decimales == 0 and v == int(v):
            return f"{int(v):,}".replace(",", ".")
        return f"{v:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)


def fmt_porcentaje(valor):
    """Formatea porcentaje."""
    try:
        return f"{float(valor):.1f}%"
    except:
        return "0.0%"


def get_alert_color(rendimiento):
    """Obtiene el emoji de alerta según el rendimiento."""
    if rendimiento >= 90:
        return "🟢"
    elif rendimiento >= 85:
        return "🟡"
    else:
        return "🔴"


def _generar_todos_los_periodos(fecha_inicio: datetime, fecha_fin: datetime, agrupacion: str):
    """
    Genera todos los períodos entre fecha_inicio y fecha_fin según la agrupación.
    Esto asegura que los gráficos muestren días con 0 producción.
    
    Args:
        fecha_inicio: Fecha de inicio del rango
        fecha_fin: Fecha de fin del rango
        agrupacion: "Día", "Semana" o "Mes"
    
    Returns:
        list: Lista de tuplas (label, sort_year, sort_value)
    """
    periodos = []
    fecha_actual = fecha_inicio
    
    if agrupacion == "Día":
        while fecha_actual <= fecha_fin:
            periodos.append(_agrupar_por_periodo(fecha_actual, agrupacion))
            fecha_actual += timedelta(days=1)
    elif agrupacion == "Mes":
        while fecha_actual <= fecha_fin:
            periodos.append(_agrupar_por_periodo(fecha_actual, agrupacion))
            # Avanzar al primer día del siguiente mes
            if fecha_actual.month == 12:
                fecha_actual = fecha_actual.replace(year=fecha_actual.year + 1, month=1, day=1)
            else:
                fecha_actual = fecha_actual.replace(month=fecha_actual.month + 1, day=1)
    else:  # Semana
        while fecha_actual <= fecha_fin:
            periodos.append(_agrupar_por_periodo(fecha_actual, agrupacion))
            fecha_actual += timedelta(weeks=1)
    
    # Eliminar duplicados manteniendo el orden
    seen = set()
    unique_periodos = []
    for p in periodos:
        if p not in seen:
            seen.add(p)
            unique_periodos.append(p)
    
    return unique_periodos


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


def grafico_salas_consolidado(mos_data: list, agrupacion: str = "Semana"):
    """
    Gráfico consolidado de SALAS de proceso con barras apiladas.
    Muestra solo salas (acumulado, sin detalle de líneas).
    
    Args:
        mos_data: Lista de órdenes de fabricación (MOs)
        agrupacion: "Día", "Semana" o "Mes"
    """
    if not mos_data:
        st.info("No hay datos de salas disponibles")
        return
    
    periodo_label = {"Día": "Día", "Semana": "Semana ISO", "Mes": "Mes"}.get(agrupacion, "Semana ISO")
    
    # Preparar datos solo de salas
    datos_salas = []
    
    for mo in mos_data:
        sala_completa = mo.get('sala', '').strip()
        sala_tipo = mo.get('sala_tipo', '').strip()
        product_name = mo.get('product_name', '').strip()
        kg_pt = mo.get('kg_pt', 0) or 0
        
        if kg_pt <= 0 or not sala_completa or sala_completa == 'SIN SALA':
            continue
        
        # Excluir túneles
        sala_lower = sala_completa.lower()
        es_tunel_continuo = '[1.4]' in product_name and 'TÚNEL CONTÍNUO' in product_name.upper()
        es_tunel = 'tunel' in sala_lower or 'túnel' in sala_lower or es_tunel_continuo
        
        if es_tunel or sala_tipo != 'PROCESO':
            continue
        
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
        
        # Usar la sala completa (incluye línea)
        linea_nombre = sala_completa
        
        datos_salas.append({
            'Periodo': periodo_label_str,
            'Sala': linea_nombre,
            'Kg': kg_pt,
            'sort_year': sort_year,
            'sort_value': sort_value
        })
    
    if not datos_salas:
        st.info("No hay datos de salas para mostrar")
        return
    
    df = pd.DataFrame(datos_salas)
    
    # Agrupar por período y sala
    df_grouped = df.groupby(['Periodo', 'Sala', 'sort_year', 'sort_value'], as_index=False).agg({
        'Kg': 'sum'
    })
    
    # Ordenar por año y valor
    df_grouped = df_grouped.sort_values(['sort_year', 'sort_value'])
    
    # Colores para salas
    colores_sala = ['#ff7f0e', '#d62728', '#e377c2', '#bcbd22', '#7f7f7f', '#98df8a', '#17becf', '#9467bd']
    salas = df_grouped['Sala'].unique().tolist()
    color_map = {sala: colores_sala[i % len(colores_sala)] for i, sala in enumerate(salas)}
    
    # Crear gráfico de barras apiladas
    chart = alt.Chart(df_grouped).mark_bar().encode(
        x=alt.X('Periodo:N', 
                title=periodo_label,
                sort=df_grouped['Periodo'].unique().tolist(),
                axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Kg:Q', 
                title='Kg Procesados',
                axis=alt.Axis(format=',.0f'),
                stack='zero'),
        color=alt.Color('Sala:N',
                       title='Sala',
                       scale=alt.Scale(domain=list(color_map.keys()), 
                                      range=list(color_map.values()))),
        tooltip=[
            alt.Tooltip('Periodo:N', title=periodo_label),
            alt.Tooltip('Sala:N', title='Sala'),
            alt.Tooltip('Kg:Q', title='Kg Procesados', format=',.0f')
        ]
    ).properties(
        title=f'🏭 Producción Acumulada por Línea ({agrupacion})',
        height=350,
        width='container'
    )
    
    st.altair_chart(chart, use_container_width=True)
    
    # Tabla resumen
    with st.expander("📋 Ver detalle por Línea", expanded=False):
        resumen = df_grouped.groupby('Sala').agg({'Kg': 'sum'}).reset_index()
        resumen = resumen.rename(columns={'Sala': 'Línea'})
        resumen = resumen.sort_values('Kg', ascending=False)
        resumen['Kg'] = resumen['Kg'].apply(lambda x: fmt_numero(x, 0))
        st.dataframe(resumen, hide_index=True, use_container_width=True)


def grafico_tuneles_consolidado(mos_data: list, agrupacion: str = "Semana"):
    """
    Gráfico consolidado de TÚNELES de congelado con barras apiladas.
    Muestra solo túneles (acumulado por túnel).
    
    Args:
        mos_data: Lista de órdenes de fabricación (MOs)
        agrupacion: "Día", "Semana" o "Mes"
    """
    if not mos_data:
        st.info("No hay datos de túneles disponibles")
        return
    
    periodo_label = {"Día": "Día", "Semana": "Semana ISO", "Mes": "Mes"}.get(agrupacion, "Semana ISO")
    
    # Preparar datos solo de túneles
    datos_tuneles = []
    
    for mo in mos_data:
        sala_completa = mo.get('sala', '').strip()
        sala_tipo = mo.get('sala_tipo', '').strip()
        product_name = mo.get('product_name', '').strip()
        kg_pt = mo.get('kg_pt', 0) or 0
        
        if kg_pt <= 0 or not sala_completa or sala_completa == 'SIN SALA':
            continue
        
        # Solo túneles
        sala_lower = sala_completa.lower()
        es_tunel_continuo = '[1.4]' in product_name and 'TÚNEL CONTÍNUO' in product_name.upper()
        es_tunel_estatico = sala_tipo == 'CONGELADO' and ('tunel' in sala_lower or 'túnel' in sala_lower)
        
        if not (es_tunel_continuo or es_tunel_estatico):
            continue
        
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
        
        # Nombre del túnel
        if es_tunel_continuo:
            tunel_nombre = 'Túnel Continuo'
        else:
            tunel_nombre = sala_completa
        
        datos_tuneles.append({
            'Periodo': periodo_label_str,
            'Túnel': tunel_nombre,
            'Kg': kg_pt,
            'sort_year': sort_year,
            'sort_value': sort_value
        })
    
    if not datos_tuneles:
        st.info("No hay datos de túneles para mostrar")
        return
    
    df = pd.DataFrame(datos_tuneles)
    
    # Agrupar por período y túnel
    df_grouped = df.groupby(['Periodo', 'Túnel', 'sort_year', 'sort_value'], as_index=False).agg({
        'Kg': 'sum'
    })
    
    # Ordenar por año y valor
    df_grouped = df_grouped.sort_values(['sort_year', 'sort_value'])
    
    # Colores para túneles (azules/fríos)
    colores_tunel = ['#1f77b4', '#2ca02c', '#17becf', '#9467bd', '#8c564b', '#3498db', '#1abc9c']
    tuneles = df_grouped['Túnel'].unique().tolist()
    color_map = {tunel: colores_tunel[i % len(colores_tunel)] for i, tunel in enumerate(tuneles)}
    
    # Crear gráfico de barras apiladas
    chart = alt.Chart(df_grouped).mark_bar().encode(
        x=alt.X('Periodo:N', 
                title=periodo_label,
                sort=df_grouped['Periodo'].unique().tolist(),
                axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Kg:Q', 
                title='Kg Congelados',
                axis=alt.Axis(format=',.0f'),
                stack='zero'),
        color=alt.Color('Túnel:N',
                       title='Túnel',
                       scale=alt.Scale(domain=list(color_map.keys()), 
                                      range=list(color_map.values()))),
        tooltip=[
            alt.Tooltip('Periodo:N', title=periodo_label),
            alt.Tooltip('Túnel:N', title='Túnel'),
            alt.Tooltip('Kg:Q', title='Kg Congelados', format=',.0f')
        ]
    ).properties(
        title=f'❄️ Congelado Acumulado por Túnel ({agrupacion})',
        height=350,
        width='container'
    )
    
    st.altair_chart(chart, use_container_width=True)
    
    # Tabla resumen
    with st.expander("📋 Ver detalle por Túnel", expanded=False):
        resumen = df_grouped.groupby('Túnel').agg({'Kg': 'sum'}).reset_index()
        resumen = resumen.sort_values('Kg', ascending=False)
        resumen['Kg'] = resumen['Kg'].apply(lambda x: fmt_numero(x, 0))
        st.dataframe(resumen, hide_index=True, use_container_width=True)


def grafico_congelado_semanal(mos_data: list, agrupacion: str = "Semana", salas_data: list = None):

    """
    Gráficos de barras separados por túnel de congelado.
    Muestra Kg congelados por período (día/semana/mes) para cada túnel.
    Crea un gráfico independiente por cada túnel con sus KPIs.
    
    Args:
        mos_data: Lista de órdenes de fabricación (MOs)
        agrupacion: "Día", "Semana" o "Mes"
        salas_data: Lista con datos agregados de KPIs por sala/túnel
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
        
        # Obtener rango de fechas del dataset
        fechas_mo = []
        for mo in mos_data:
            fecha_str = mo.get('fecha') or mo.get('fecha_inicio') or mo.get('fecha_fin')
            if fecha_str:
                try:
                    fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                    fechas_mo.append(fecha)
                except:
                    try:
                        fecha = datetime.strptime(fecha_str[:10], '%Y-%m-%d')
                        fechas_mo.append(fecha)
                    except:
                        pass
        
        # Generar todos los períodos (incluyendo los que no tienen datos)
        if fechas_mo:
            fecha_min = min(fechas_mo)
            fecha_max = max(fechas_mo)
            todos_periodos = _generar_todos_los_periodos(fecha_min, fecha_max, agrupacion)
            
            # Crear DataFrame con todos los períodos
            df_todos = pd.DataFrame(todos_periodos, columns=['Periodo', 'sort_year', 'sort_value'])
            
            # Hacer merge para incluir períodos con 0
            df_grouped = df_todos.merge(df_grouped, on=['Periodo', 'sort_year', 'sort_value'], how='left')
            df_grouped['Kg'] = df_grouped['Kg'].fillna(0)
        
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
        
        # Buscar KPIs del túnel en salas_data
        sala_info = None
        if salas_data:
            for sala in salas_data:
                if sala.get('sala', '').strip() == tunel_nombre:
                    sala_info = sala
                    break
        
        # Mostrar KPIs del túnel (solo electricidad para congelado)
        if sala_info:
            st.markdown("---")
            st.markdown("**⚡ KPIs del Túnel**")
            cols = st.columns(4)
            with cols[0]:
                st.metric("Rendimiento", fmt_porcentaje(sala_info.get('rendimiento', 0)))
            with cols[1]:
                st.metric("Kg Entrada", fmt_numero(sala_info.get('kg_mp', 0), 0))
            with cols[2]:
                st.metric("Kg Salida", fmt_numero(sala_info.get('kg_pt', 0), 0))
            with cols[3]:
                costo_elec = sala_info.get('costo_electricidad', 0)
                st.metric("⚡ Costo Elec.", f"${fmt_numero(costo_elec, 0)}",
                         help="Costo de electricidad del túnel")
            
            st.markdown("**⚡ Eficiencia Energética**")
            cols2 = st.columns(3)
            with cols2[0]:
                kwh_total = sala_info.get('total_electricidad', 0)
                st.metric("KWh Total", fmt_numero(kwh_total, 1),
                         help="Total de kilovatios-hora consumidos")
            with cols2[1]:
                kwh_por_kg = sala_info.get('kwh_por_kg', 0)
                st.metric("KWh/Kg", fmt_numero(kwh_por_kg, 2),
                         help="Consumo de energía por kilogramo congelado")
            with cols2[2]:
                st.metric("MOs", sala_info.get('num_mos', 0))
        
        st.markdown("---")  # Separador entre túneles


def grafico_vaciado_por_sala(mos_data: list, agrupacion: str = "Semana", salas_data: list = None):
    """
    Gráficos de barras separados por sala con desglose de líneas.
    Muestra rendimiento individual de cada línea dentro de su sala con sus KPIs.
    Crea un gráfico independiente por cada sala.
    
    Args:
        mos_data: Lista de órdenes de fabricación (MOs)
        agrupacion: "Día", "Semana" o "Mes"
        salas_data: Lista con datos agregados de KPIs por sala
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
        
        # Obtener rango de fechas del dataset
        fechas_mo = []
        for mo in mos_data:
            fecha_str = mo.get('fecha') or mo.get('fecha_inicio') or mo.get('fecha_fin')
            if fecha_str:
                try:
                    fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                    fechas_mo.append(fecha)
                except:
                    try:
                        fecha = datetime.strptime(fecha_str[:10], '%Y-%m-%d')
                        fechas_mo.append(fecha)
                    except:
                        pass
        
        # Generar todos los períodos y líneas (incluyendo combinaciones con 0)
        if fechas_mo:
            fecha_min = min(fechas_mo)
            fecha_max = max(fechas_mo)
            todos_periodos = _generar_todos_los_periodos(fecha_min, fecha_max, agrupacion)
            lineas_unicas = df_grouped['Línea'].unique()
            
            # Crear todas las combinaciones de período x línea
            all_combinations = []
            for periodo, sort_year, sort_value in todos_periodos:
                for linea in lineas_unicas:
                    all_combinations.append({
                        'Periodo': periodo,
                        'Línea': linea,
                        'Sala-Línea': f"{sala_nombre} - {linea}",
                        'sort_year': sort_year,
                        'sort_value': sort_value
                    })
            
            df_todos = pd.DataFrame(all_combinations)
            
            # Hacer merge para incluir períodos con 0
            df_grouped = df_todos.merge(
                df_grouped,
                on=['Periodo', 'Línea', 'Sala-Línea', 'sort_year', 'sort_value'],
                how='left'
            )
            df_grouped['Kg PT'] = df_grouped['Kg PT'].fillna(0)
            df_grouped['Rendimiento'] = df_grouped['Rendimiento'].fillna(0)
        
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
        
        # Buscar KPIs de la sala en salas_data
        sala_info = None
        if salas_data:
            for sala in salas_data:
                sala_data_nombre = sala.get('sala', '').strip()
                # Comparar sin considerar líneas
                if ' - ' in sala_data_nombre:
                    sala_base = sala_data_nombre.split(' - ', 1)[0].strip()
                else:
                    sala_base = sala_data_nombre
                
                if sala_base == sala_nombre:
                    sala_info = sala
                    break
        
        # Mostrar KPIs de la sala (sin electricidad para proceso)
        if sala_info:
            st.markdown("---")
            alert = get_alert_color(sala_info.get('rendimiento', 0))
            st.markdown(f"**{alert} KPIs de la Sala**")
            
            # Fila 1: KPIs principales de rendimiento
            cols = st.columns(5)
            with cols[0]:
                st.metric("Rendimiento", fmt_porcentaje(sala_info.get('rendimiento', 0)))
            with cols[1]:
                st.metric("Kg/Hora", fmt_numero(sala_info.get('kg_por_hora', 0), 1))
            with cols[2]:
                st.metric("Kg/HH", fmt_numero(sala_info.get('kg_por_hh', 0), 1))
            with cols[3]:
                st.metric("Kg/Operario", fmt_numero(sala_info.get('kg_por_operario', 0), 1))
            with cols[4]:
                st.metric("Merma (Kg)", fmt_numero(sala_info.get('merma', 0), 0))
            
            # Fila 2: Datos de producción
            st.markdown("**📦 Datos de Producción**")
            cols2 = st.columns(4)
            with cols2[0]:
                st.markdown(f"**Kg MP:** {fmt_numero(sala_info['kg_mp'])}")
            with cols2[1]:
                st.markdown(f"**Kg PT:** {fmt_numero(sala_info['kg_pt'])}")
            with cols2[2]:
                st.markdown(f"**HH Total:** {fmt_numero(sala_info.get('hh_total', 0), 1)}")
            with cols2[3]:
                st.markdown(f"**Dotación Prom:** {sala_info.get('dotacion_promedio', 0):.1f}")
            
            # Fila 3: KPIs efectivos (sin electricidad)
            st.markdown("**⚡ KPIs Efectivos (Promedios)**")
            cols3 = st.columns(4)
            with cols3[0]:
                hh_efectiva_prom = sala_info.get('hh_efectiva_promedio', 0)
                st.metric("HH Efectiva", fmt_numero(hh_efectiva_prom, 1), 
                         help="Promedio de Horas Hombre efectivas por orden de fabricación")
            with cols3[1]:
                kg_hora_efectiva = sala_info.get('kg_por_hora_efectiva', 0)
                st.metric("Kg/Hora Efect.", fmt_numero(kg_hora_efectiva, 1),
                         help="Kg procesados por hora efectiva")
            with cols3[2]:
                kg_hh_efectiva = sala_info.get('kg_por_hh_efectiva', 0)
                st.metric("Kg/HH Efect.", fmt_numero(kg_hh_efectiva, 1),
                         help="Kg procesados por HH efectiva")
            with cols3[3]:
                detenciones_prom = sala_info.get('detenciones_promedio', 0)
                st.metric("Detenciones (h)", fmt_numero(detenciones_prom, 1),
                         help="Promedio de horas de detención por orden de fabricación")
        
        st.markdown("---")  # Separador entre salas

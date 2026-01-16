"""
Tab: Reportería General
KPIs consolidados de producción, rendimientos por fruta/manejo y salas.
"""
import streamlit as st
import pandas as pd
import altair as alt
import plotly.graph_objects as go
import requests
import io
from datetime import datetime, timedelta

from .shared import (
    API_URL, fmt_numero, fmt_porcentaje, get_alert_color,
    filtrar_mos_por_planta, fetch_dashboard_completo, skeleton_loader
)
from .graficos import grafico_congelado_semanal, grafico_vaciado_por_sala, grafico_salas_consolidado, grafico_tuneles_consolidado


def render(username: str, password: str):
    """Renderiza el contenido del tab Reportería General."""
    st.subheader("📊 Reportería General de Producción")
    
    # KPIs rápidos
    if "prod_reporteria_error" not in st.session_state:
        st.session_state.prod_reporteria_error = None

    if st.session_state.prod_reporteria_error:
        st.error(st.session_state.prod_reporteria_error)
        
    # --- Selector de Período ---
    st.markdown("#### 📅 Seleccionar Período")
    
    periodo_tipo = st.radio(
        "Tipo de informe",
        ["📆 Última Semana", "📊 Acumulado Temporada", "📅 Período Personalizado"],
        horizontal=True,
        key="periodo_tipo_prod",
        label_visibility="collapsed"
    )
    
    # Calcular fechas según selección
    hoy = datetime.now().date()
    
    if hoy.month >= 11 and hoy.day >= 20:
        inicio_temporada = datetime(hoy.year, 11, 20).date()
    elif hoy.month == 12:
        inicio_temporada = datetime(hoy.year, 11, 20).date()
    else:
        inicio_temporada = datetime(hoy.year - 1, 11, 20).date()
    
    if "Última Semana" in periodo_tipo:
        fecha_inicio_default = hoy - timedelta(days=7)
        fecha_fin_default = hoy
        mostrar_inputs = False
    elif "Acumulado" in periodo_tipo:
        fecha_inicio_default = inicio_temporada
        fecha_fin_default = hoy
        mostrar_inputs = False
    else:
        fecha_inicio_default = hoy - timedelta(days=7)
        fecha_fin_default = hoy
        mostrar_inputs = True
    
    if mostrar_inputs:
        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            fecha_inicio_rep = st.date_input(
                "Desde", fecha_inicio_default, 
                format="DD/MM/YYYY", key="prod_rep_fecha_inicio"
            )
        with col_f2:
            fecha_fin_rep = st.date_input(
                "Hasta", fecha_fin_default, 
                format="DD/MM/YYYY", key="prod_rep_fecha_fin"
            )
    else:
        fecha_inicio_rep = fecha_inicio_default
        fecha_fin_rep = fecha_fin_default
        st.info(f"📅 **Período:** {fecha_inicio_rep.strftime('%d/%m/%Y')} → {fecha_fin_rep.strftime('%d/%m/%Y')} ({(fecha_fin_rep - fecha_inicio_rep).days + 1} días)")
    
    solo_terminadas = st.checkbox(
        "Solo fabricaciones terminadas (done)", 
        value=True, key="solo_terminadas_prod",
        help="Activa para ver solo OFs completadas."
    )
    
    # Filtro de Planta
    st.markdown("**🏭 Filtro de Planta**")
    col_planta1, col_planta2 = st.columns(2)
    with col_planta1:
        filtro_rfp_prod = st.checkbox("RFP", value=True, key="prod_rfp")
    with col_planta2:
        filtro_vilkun_prod = st.checkbox("VILKUN", value=True, key="prod_vilkun")
    
    # Selector de Agrupación para Gráficos
    st.markdown("**📊 Agrupación de Gráficos**")
    agrupacion = st.radio(
        "Formato de visualización:",
        options=["Día", "Semana", "Mes"],
        index=1,  # Por defecto: Semana
        horizontal=True,
        key="prod_agrupacion",
        help="Define cómo se agrupan los datos en los gráficos de barras"
    )
    
    if st.button("🔄 Consultar Reportería", type="primary", key="btn_consultar_reporteria", disabled=st.session_state.prod_reporteria_loading):
        st.session_state.prod_reporteria_loading = True
        st.session_state.prod_reporteria_error = None
        try:
            # Progress bar personalizado
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            with progress_placeholder.container():
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Fase 1: Conexión
                status_text.text("🔗 Conectando con Odoo...")
                progress_bar.progress(20)
                
                fi = fecha_inicio_rep.strftime("%Y-%m-%d")
                ff = fecha_fin_rep.strftime("%Y-%m-%d")
                
                # Fase 2: Consulta
                status_text.text("📊 Consultando datos de producción...")
                progress_bar.progress(50)
                
                st.session_state.prod_dashboard_data = fetch_dashboard_completo(username, password, fi, ff, solo_terminadas)
                
                # Fase 3: Procesamiento
                status_text.text("⚙️ Procesando rendimientos...")
                progress_bar.progress(80)
                
                # Fase 4: Completado
                progress_bar.progress(100)
                status_text.text("✅ Datos cargados correctamente")
            
            # Limpiar placeholders
            progress_placeholder.empty()
            
            if st.session_state.prod_dashboard_data:
                st.session_state.prod_reporteria_error = None
                st.toast("✅ Datos de reportería cargados", icon="✅")
            else:
                st.session_state.prod_reporteria_error = "❌ No se pudieron cargar los datos. Revisa la conexión o intenta nuevamente."
        except Exception as e:
            progress_placeholder.empty()
            st.session_state.prod_reporteria_error = f"Error al cargar reportería: {str(e)}"
            st.error(st.session_state.prod_reporteria_error)
            st.toast(f"❌ Error: {str(e)[:100]}", icon="❌")
        finally:
            st.session_state.prod_reporteria_loading = False
    
    # Extraer datos
    dashboard = st.session_state.get('prod_dashboard_data')
    data = dashboard.get('overview') if dashboard else None
    consolidado = dashboard.get('consolidado') if dashboard else None
    salas = dashboard.get('salas') if dashboard else None
    mos_original = dashboard.get('mos') if dashboard else None
    
    # Aplicar filtro de planta
    if mos_original:
        mos = filtrar_mos_por_planta(mos_original, filtro_rfp_prod, filtro_vilkun_prod)
        if len(mos) != len(mos_original):
            plantas_activas = []
            if filtro_rfp_prod:
                plantas_activas.append("RFP")
            if filtro_vilkun_prod:
                plantas_activas.append("VILKUN")
            st.info(f"🏭 Mostrando {len(mos)} de {len(mos_original)} fabricaciones ({', '.join(plantas_activas)})")
    else:
        mos = None
    
    if data:
        st.markdown("---")
        # Renderizar resumen de volumen de masa primero (destacado)
        if mos:
            _render_volumen_masa(mos, data, agrupacion, filtro_rfp_prod, filtro_vilkun_prod)
        _render_kpis_tabs(data, mos, consolidado, salas, fecha_inicio_rep, fecha_fin_rep, username, password, agrupacion)
        st.markdown("---")
    elif st.session_state.prod_reporteria_loading:
        # Mostrar skeleton loader mientras carga
        skeleton_loader()
    else:
        st.info("👆 Selecciona un rango de fechas y haz clic en **Consultar Reportería** para ver los datos consolidados.")
        _render_info_ayuda()


def _render_volumen_masa(mos, data, agrupacion, filtro_rfp, filtro_vilkun):
    """Renderiza resumen de volumen de masa con KPIs destacados y gráfico ampliado."""
    from .shared import detectar_planta
    
    st.subheader("📊 Volumen de Masa por Período")
    
    # Determinar qué plantas están activas
    plantas_activas = []
    if filtro_rfp:
        plantas_activas.append("RFP")
    if filtro_vilkun:
        plantas_activas.append("VILKUN")
    
    planta_label = " + ".join(plantas_activas) if plantas_activas else "Todas"
    st.caption(f"Volumen total de producción agrupado por {agrupacion.lower()} | Plantas: **{planta_label}**")
    
    # KPIs destacados de volumen
    total_kg_mp = sum(mo.get('kg_mp', 0) or 0 for mo in mos)
    total_kg_pt = sum(mo.get('kg_pt', 0) or 0 for mo in mos)
    total_mos = len(mos)
    rendimiento_promedio = (total_kg_pt / total_kg_mp * 100) if total_kg_mp > 0 else 0
    
    # Separar por tipo de sala
    mos_proceso = [mo for mo in mos if mo.get('sala_tipo') == 'PROCESO']
    mos_congelado = [mo for mo in mos if mo.get('sala_tipo') == 'CONGELADO']
    
    kg_proceso = sum(mo.get('kg_pt', 0) or 0 for mo in mos_proceso)
    kg_congelado = sum(mo.get('kg_pt', 0) or 0 for mo in mos_congelado)
    
    # Métricas principales en cards grandes
    st.markdown("""
    <style>
    .volumen-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 15px;
    }
    .volumen-card h2 {
        color: #4fd1c5;
        font-size: 2.5rem;
        margin: 0;
    }
    .volumen-card p {
        color: #a0aec0;
        margin: 5px 0 0 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    vol_cols = st.columns(4)
    with vol_cols[0]:
        st.metric("📦 Kg MP Total", fmt_numero(total_kg_mp, 0))
    with vol_cols[1]:
        st.metric("📤 Kg PT Total", fmt_numero(total_kg_pt, 0))
    with vol_cols[2]:
        st.metric("🏭 Kg Proceso", fmt_numero(kg_proceso, 0))
    with vol_cols[3]:
        st.metric("❄️ Kg Congelado", fmt_numero(kg_congelado, 0))
    
    # Preparar datos para gráfico ampliado
    df_mos = pd.DataFrame(mos)
    
    if df_mos.empty or 'fecha' not in df_mos.columns:
        st.warning("No hay datos de fabricaciones para mostrar en el gráfico.")
        return
    
    # Convertir fecha
    df_mos['fecha_dt'] = pd.to_datetime(df_mos['fecha'], errors='coerce')
    df_mos = df_mos.dropna(subset=['fecha_dt'])
    
    if df_mos.empty:
        st.warning("No hay fechas válidas para graficar.")
        return
    
    # Agrupar por período
    if agrupacion == "Día":
        df_mos['periodo'] = df_mos['fecha_dt'].dt.strftime('%Y-%m-%d')
        # IMPORTANTE: Normalizar a medianoche para que agrupe bien por día
        df_mos['periodo_sort'] = df_mos['fecha_dt'].dt.normalize()
    elif agrupacion == "Semana":
        df_mos['periodo'] = df_mos['fecha_dt'].dt.strftime('S%W-%Y')
        df_mos['periodo_sort'] = df_mos['fecha_dt'].dt.to_period('W').dt.start_time
    else:  # Mes
        df_mos['periodo'] = df_mos['fecha_dt'].dt.strftime('%b-%Y')
        df_mos['periodo_sort'] = df_mos['fecha_dt'].dt.to_period('M').dt.start_time
    
    # Clasificar túneles: Estático vs Continuo
    def clasificar_tunel(sala):
        if not sala:
            return sala
        sala_upper = str(sala).upper()
        if 'ESTATICO' in sala_upper or 'ESTÁTICO' in sala_upper:
            return f"{sala} (Estático)"
        return sala
    
    df_mos['sala_clasificada'] = df_mos['sala'].apply(clasificar_tunel)
    
    # Agregar columna de planta
    df_mos['planta'] = df_mos.apply(
        lambda row: detectar_planta(row.get('mo_name', ''), row.get('sala', '')), 
        axis=1
    )
    
    # Agrupar por período y sala
    df_grouped = df_mos.groupby(['periodo', 'periodo_sort', 'sala_clasificada', 'sala_tipo']).agg({
        'kg_pt': 'sum',
        'kg_mp': 'sum',
        'mo_id': 'count'
    }).reset_index()
    df_grouped.columns = ['Período', 'periodo_sort', 'Sala', 'Tipo', 'Kg PT', 'Kg MP', 'Órdenes']
    df_grouped = df_grouped.sort_values('periodo_sort')
    
    # Crear tabs para Proceso y Congelado
    vol_tabs = st.tabs(["🏭 Salas (Proceso)", "❄️ Túneles (Congelado)"])
    
    # Modal para mostrar detalles de ODFs al clickear
    @st.dialog("📋 Detalles de Órdenes de Fabricación", width="large")
    def mostrar_odfs_modal(periodo, sala, tipo):
        """Muestra el modal con las ODFs del período y sala seleccionada."""
        st.subheader(f"📊 {tipo.title()} - {sala}")
        st.caption(f"Período: {periodo}")
        
        # Filtrar ODFs del período y sala
        mos_filtradas = [
            mo for mo in mos
            if (
                (agrupacion == "Día" and pd.to_datetime(mo['fecha']).strftime('%Y-%m-%d') == periodo) or
                (agrupacion == "Semana" and pd.to_datetime(mo['fecha']).strftime('S%W-%Y') == periodo) or
                (agrupacion == "Mes" and pd.to_datetime(mo['fecha']).strftime('%b-%Y') == periodo)
            )
            and clasificar_tunel(mo.get('sala', '')) == sala
        ]
        
        if not mos_filtradas:
            st.warning("No se encontraron órdenes para este período y sala.")
            return
        
        st.info(f"🔢 Total: **{len(mos_filtradas)}** órdenes de fabricación")
        
        # Preparar datos para tabla
        df_odfs = pd.DataFrame([{
            'ODF': mo['mo_name'],
            'Fecha': pd.to_datetime(mo['fecha']).strftime('%Y-%m-%d'),
            'Producto': mo.get('producto', 'N/A'),
            'Kg PT': mo.get('kg_pt', 0),
            'Kg MP': mo.get('kg_mp', 0),
            'Sala': mo.get('sala', 'N/A'),
            'Estado': mo.get('estado', 'N/A'),
            'ID': mo['mo_id']
        } for mo in mos_filtradas])
        
        # Mostrar tabla con enlaces a Odoo
        st.dataframe(
            df_odfs[['ODF', 'Fecha', 'Producto', 'Kg PT', 'Kg MP', 'Sala', 'Estado']].style.format({
                'Kg PT': '{:,.2f}',
                'Kg MP': '{:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # Enlaces a Odoo
        st.markdown("### 🔗 Enlaces a Odoo")
        cols_odoo = st.columns(3)
        for idx, odf in enumerate(df_odfs.itertuples()):
            col_idx = idx % 3
            with cols_odoo[col_idx]:
                odoo_url = f"https://riofuturo.server98c6e.oerpondemand.net/web#id={odf.ID}&menu_id=390&cids=1&action=604&model=mrp.production&view_type=form"
                st.markdown(f"🔹 [{odf.ODF}]({odoo_url})")
    
    with vol_tabs[0]:
        df_proceso = df_grouped[df_grouped['Tipo'] == 'PROCESO'].copy()
        if not df_proceso.empty:
            # Crear gráfico interactivo con Plotly
            fig = go.Figure()
            
            # Agrupar por sala para crear una barra por sala
            for sala in df_proceso['Sala'].unique():
                df_sala = df_proceso[df_proceso['Sala'] == sala]
                fig.add_trace(go.Bar(
                    x=df_sala['Período'],
                    y=df_sala['Kg PT'],
                    name=sala,
                    customdata=df_sala[['Sala', 'Kg MP', 'Órdenes']],
                    hovertemplate='<b>Período:</b> %{x}<br>' +
                                  '<b>Sala:</b> %{customdata[0]}<br>' +
                                  '<b>Kg Producidos:</b> %{y:,.0f}<br>' +
                                  '<b>Kg MP:</b> %{customdata[1]:,.0f}<br>' +
                                  '<b>Órdenes:</b> %{customdata[2]}<extra></extra>'
                ))
            
            fig.update_layout(
                title=f"Volumen por {agrupacion} - Salas de Proceso",
                xaxis_title=f'Período ({agrupacion})',
                yaxis_title='Kilogramos Producidos',
                barmode='group',
                height=400,
                hovermode='closest'
            )
            
            # Mostrar gráfico con evento de clic
            event = st.plotly_chart(fig, use_container_width=True, key="proceso_chart", on_select="rerun")
            
            # Capturar clic
            if event and "selection" in event and "points" in event["selection"]:
                points = event["selection"]["points"]
                if points:
                    punto = points[0]
                    periodo_sel = punto.get("x")
                    trace_idx = punto.get("curve_number", 0)
                    sala_sel = fig.data[trace_idx].name
                    mostrar_odfs_modal(periodo_sel, sala_sel, "proceso")
            
            # Tabla resumen
            with st.expander("📋 Ver datos detallados"):
                st.dataframe(
                    df_proceso[['Período', 'Sala', 'Kg PT', 'Kg MP', 'Órdenes']].style.format({
                        'Kg PT': '{:,.0f}',
                        'Kg MP': '{:,.0f}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("No hay datos de proceso para mostrar.")
    
    with vol_tabs[1]:
        df_congelado = df_grouped[df_grouped['Tipo'] == 'CONGELADO'].copy()
        if not df_congelado.empty:
            # Crear gráfico interactivo con Plotly
            fig = go.Figure()
            
            # Agrupar por túnel
            for tunel in df_congelado['Sala'].unique():
                df_tunel = df_congelado[df_congelado['Sala'] == tunel]
                fig.add_trace(go.Bar(
                    x=df_tunel['Período'],
                    y=df_tunel['Kg PT'],
                    name=tunel,
                    customdata=df_tunel[['Sala', 'Órdenes']],
                    hovertemplate='<b>Período:</b> %{x}<br>' +
                                  '<b>Túnel:</b> %{customdata[0]}<br>' +
                                  '<b>Kg Congelados:</b> %{y:,.0f}<br>' +
                                  '<b>Órdenes:</b> %{customdata[1]}<extra></extra>'
                ))
            
            fig.update_layout(
                title=f"Volumen por {agrupacion} - Túneles de Congelado",
                xaxis_title=f'Período ({agrupacion})',
                yaxis_title='Kilogramos Congelados',
                barmode='group',
                height=400,
                hovermode='closest'
            )
            
            # Mostrar gráfico con evento de clic
            event = st.plotly_chart(fig, use_container_width=True, key="congelado_chart", on_select="rerun")
            
            # Capturar clic
            if event and "selection" in event and "points" in event["selection"]:
                points = event["selection"]["points"]
                if points:
                    punto = points[0]
                    periodo_sel = punto.get("x")
                    trace_idx = punto.get("curve_number", 0)
                    tunel_sel = fig.data[trace_idx].name
                    mostrar_odfs_modal(periodo_sel, tunel_sel, "congelado")
            
            # Tabla resumen
            with st.expander("📋 Ver datos detallados"):
                st.dataframe(
                    df_congelado[['Período', 'Sala', 'Kg PT', 'Órdenes']].style.format({
                        'Kg PT': '{:,.0f}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("No hay datos de congelado para mostrar.")
    
    st.markdown("---")


def _render_kpis_tabs(data, mos=None, consolidado=None, salas=None, fecha_inicio_rep=None, fecha_fin_rep=None, username=None, password=None, agrupacion="Semana"):
    """Renderiza los sub-tabs de KPIs: Proceso y Congelado."""
    vista_tabs = st.tabs(["🏭 Proceso (Vaciado)", "❄️ Congelado (Túneles)"])
    
    with vista_tabs[0]:
        @st.fragment
        def _fragment_kpis_proceso():
            """Fragment para KPIs de Proceso - se ejecuta independientemente."""
            st.subheader("🏭 KPIs de Proceso (Vaciado)")
            st.caption("Salas de vaciado, líneas retail/granel - generan merma real")
            
            proc_cols = st.columns(5)
            with proc_cols[0]:
                st.metric("Kg MP Procesados", fmt_numero(data.get('proceso_kg_mp', 0), 0))
            with proc_cols[1]:
                st.metric("Kg PT Producidos", fmt_numero(data.get('proceso_kg_pt', 0), 0))
            with proc_cols[2]:
                rend = data.get('proceso_rendimiento', 0)
                alert = get_alert_color(rend)
                st.metric(f"Rendimiento {alert}", fmt_porcentaje(rend), delta=f"{rend-85:.1f}% vs 85%")
            with proc_cols[3]:
                st.metric("Merma Proceso", fmt_numero(data.get('proceso_merma_kg', 0), 0) + " Kg")
            with proc_cols[4]:
                st.metric("Kg/HH", fmt_numero(data.get('proceso_kg_por_hh', 0), 1))
            
            proc_cols2 = st.columns(4)
            with proc_cols2[0]:
                st.metric("MOs Proceso", data.get('proceso_mos', 0))
            with proc_cols2[1]:
                st.metric("HH Proceso", fmt_numero(data.get('proceso_hh', 0), 1))
            with proc_cols2[2]:
                st.metric("Merma %", fmt_porcentaje(data.get('proceso_merma_pct', 0)))
            with proc_cols2[3]:
                st.metric("Lotes Únicos", data.get('lotes_unicos', 0))
        
        _fragment_kpis_proceso()
        
        # === RESUMEN POR FRUTA Y MANEJO ===
        if consolidado:
            st.markdown("---")
            _render_resumen_fruta_manejo(consolidado)
        
        # NOTA: El gráfico acumulado por línea está en Volumen de Masa arriba
        
        # === GRÁFICO TEMPORAL DE PROCESO/VACIADO POR SALA (DETALLE POR LÍNEA) ===
        if mos:
            st.markdown("---")
            titulo_agrupacion = {"Día": "Diario", "Semana": "Semanal", "Mes": "Mensual"}.get(agrupacion, "Semanal")
            st.markdown(f"### 📊 Análisis {titulo_agrupacion} por Sala y Línea (Detalle)")
            grafico_vaciado_por_sala(mos, agrupacion, salas)

        
        # === DETALLE DE FABRICACIONES - PROCESO ===
        if mos:
            # Filtrar solo MOs de proceso
            mos_proceso = [mo for mo in mos if mo.get('sala_tipo') == 'PROCESO']
            if mos_proceso:
                _render_detalle_fabricaciones(mos_proceso, fecha_inicio_rep, fecha_fin_rep, username, password, tipo_filtro='PROCESO')
    
    with vista_tabs[1]:
        @st.fragment
        def _fragment_kpis_congelado():
            """Fragment para KPIs de Congelado - se ejecuta independientemente."""
            st.subheader("❄️ KPIs de Congelado")
            st.caption("Túneles de congelación (Estáticos + Continuo)")
            
            cong_cols = st.columns(6)
            with cong_cols[0]:
                st.metric("Kg Entrada", fmt_numero(data.get('congelado_kg_mp', 0), 0))
            with cong_cols[1]:
                st.metric("Kg Salida", fmt_numero(data.get('congelado_kg_pt', 0), 0))
            with cong_cols[2]:
                cong_rend = data.get('congelado_rendimiento', 0)
                st.metric("Rendimiento", fmt_porcentaje(cong_rend))
            with cong_cols[3]:
                st.metric("MOs Congelado", data.get('congelado_mos', 0))
            with cong_cols[4]:
                st.metric("Proveedores", data.get('congelado_proveedores', 0))
            with cong_cols[5]:
                st.metric("Lotes Únicos", data.get('congelado_lotes', 0))
        
        _fragment_kpis_congelado()
        
        # NOTA: El gráfico acumulado por túnel está en Volumen de Masa arriba
        
        # === GRÁFICO TEMPORAL DE CONGELADO (DETALLE POR TÚNEL) ===
        if mos:
            st.markdown("---")
            titulo_agrupacion = {"Día": "Diario", "Semana": "Semanal", "Mes": "Mensual"}.get(agrupacion, "Semanal")
            st.markdown(f"### 📊 Análisis {titulo_agrupacion} de Congelado (Detalle)")
            grafico_congelado_semanal(mos, agrupacion, salas)

        
        # === DETALLE DE FABRICACIONES - CONGELADO ===
        if mos:
            # Filtrar solo MOs de congelado
            mos_congelado = [mo for mo in mos if mo.get('sala_tipo') == 'CONGELADO']
            if mos_congelado:
                _render_detalle_fabricaciones(mos_congelado, fecha_inicio_rep, fecha_fin_rep, username, password, tipo_filtro='CONGELADO')


def _render_resumen_fruta_manejo(consolidado):
    """Renderiza resumen por tipo de fruta y manejo."""
    st.subheader("📊 Resumen por Tipo de Fruta y Manejo")
    
    por_fruta = consolidado.get('por_fruta', [])
    por_fm = consolidado.get('por_fruta_manejo', [])
    
    if por_fruta and por_fm:
        tabla_rows = []
        total_kg_mp = 0
        total_kg_pt = 0
        total_merma = 0
        
        for fruta_data in sorted(por_fruta, key=lambda x: x.get('kg_pt', 0), reverse=True):
            tipo_fruta = fruta_data.get('tipo_fruta', 'N/A')
            
            tabla_rows.append({
                'tipo': 'fruta',
                'Descripción': tipo_fruta,
                'Kg MP': fruta_data.get('kg_mp', 0),
                'Kg PT': fruta_data.get('kg_pt', 0),
                'Rendimiento': None,
                'Merma': fruta_data.get('merma', 0)
            })
            total_kg_mp += fruta_data.get('kg_mp', 0)
            total_kg_pt += fruta_data.get('kg_pt', 0)
            total_merma += fruta_data.get('merma', 0)
            
            manejos_fruta = [fm for fm in por_fm if fm.get('tipo_fruta') == tipo_fruta]
            for manejo_data in sorted(manejos_fruta, key=lambda x: x.get('kg_pt', 0), reverse=True):
                manejo = manejo_data.get('manejo', 'N/A')
                if 'orgánico' in manejo.lower() or 'organico' in manejo.lower():
                    icono = '🌱'
                elif 'convencional' in manejo.lower():
                    icono = '🏭'
                else:
                    icono = '📋'
                
                tabla_rows.append({
                    'tipo': 'manejo',
                    'Descripción': f"    → {icono} {manejo}",
                    'Kg MP': manejo_data.get('kg_mp', 0),
                    'Kg PT': manejo_data.get('kg_pt', 0),
                    'Rendimiento': manejo_data.get('rendimiento', 0),
                    'Merma': manejo_data.get('merma', 0)
                })
        
        rend_total = (total_kg_pt / total_kg_mp * 100) if total_kg_mp > 0 else 0
        tabla_rows.append({
            'tipo': 'total',
            'Descripción': 'TOTAL GENERAL',
            'Kg MP': total_kg_mp,
            'Kg PT': total_kg_pt,
            'Rendimiento': rend_total,
            'Merma': total_merma
        })
        
        df_resumen = pd.DataFrame(tabla_rows)
        df_display = df_resumen.copy()
        df_display['Kg MP'] = df_display['Kg MP'].apply(lambda x: fmt_numero(x, 0) if pd.notna(x) else "—")
        df_display['Kg PT'] = df_display['Kg PT'].apply(lambda x: fmt_numero(x, 0) if pd.notna(x) else "—")
        df_display['Rendimiento'] = df_display['Rendimiento'].apply(
            lambda x: f"{get_alert_color(x)} {fmt_porcentaje(x)}" if pd.notna(x) and x > 0 else "—"
        )
        df_display['Merma'] = df_display['Merma'].apply(lambda x: fmt_numero(x, 0) if pd.notna(x) else "—")
        
        num_filas = len(df_display)
        table_height = min(600, max(200, num_filas * 40 + 60))
        
        df_show = df_display[['Descripción', 'Kg MP', 'Kg PT', 'Rendimiento', 'Merma']]
        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            height=table_height,
            column_config={
                'Descripción': st.column_config.TextColumn('Tipo / Manejo', width=250),
                'Kg MP': st.column_config.TextColumn('Kg MP', width=120),
                'Kg PT': st.column_config.TextColumn('Kg PT', width=120),
                'Rendimiento': st.column_config.TextColumn('Rendimiento', width=150),
                'Merma': st.column_config.TextColumn('Merma (Kg)', width=120),
            }
        )
    
    st.markdown("---")
    
    # Gráfico de rendimiento
    if por_fruta:
        st.subheader("📈 Rendimiento por Tipo de Fruta")
        
        df_fruta = pd.DataFrame(por_fruta)
        num_frutas = len(df_fruta)
        chart_height = max(300, min(500, num_frutas * 80))
        bar_size = max(30, min(60, 400 // num_frutas)) if num_frutas > 0 else 50
        
        def get_bar_color(rend):
            if rend >= 90:
                return '#22c55e'
            elif rend >= 80:
                return '#f59e0b'
            else:
                return '#ef4444'
        
        df_fruta['color'] = df_fruta['rendimiento'].apply(get_bar_color)
        
        bars = alt.Chart(df_fruta).mark_bar(size=bar_size).encode(
            y=alt.Y('tipo_fruta:N', sort='-x', title='Tipo de Fruta', 
                   axis=alt.Axis(labelFontSize=14, labelLimit=200)),
            x=alt.X('rendimiento:Q', title='Rendimiento %', 
                   scale=alt.Scale(domain=[0, 105]),
                   axis=alt.Axis(labelFontSize=12)),
            color=alt.Color('color:N', scale=None, legend=None),
            tooltip=[
                alt.Tooltip('tipo_fruta:N', title='Fruta'),
                alt.Tooltip('rendimiento:Q', title='Rendimiento %', format='.1f'),
                alt.Tooltip('kg_mp:Q', title='Kg MP', format=',.0f'),
                alt.Tooltip('kg_pt:Q', title='Kg PT', format=',.0f'),
                alt.Tooltip('num_lotes:Q', title='Lotes')
            ]
        )
        
        text = alt.Chart(df_fruta).mark_text(
            align='left', baseline='middle', dx=5, fontSize=14, fontWeight='bold', color='white'
        ).encode(
            y=alt.Y('tipo_fruta:N', sort='-x'),
            x=alt.X('rendimiento:Q'),
            text=alt.Text('rendimiento:Q', format='.1f')
        )
        
        rule_90 = alt.Chart(pd.DataFrame({'x': [90]})).mark_rule(
            color='#ef4444', strokeDash=[6,4], strokeWidth=2
        ).encode(x='x:Q')
        rule_85 = alt.Chart(pd.DataFrame({'x': [85]})).mark_rule(
            color='#f59e0b', strokeDash=[6,4], strokeWidth=2
        ).encode(x='x:Q')
        
        chart = (bars + text + rule_90 + rule_85).properties(
            height=chart_height
        ).configure_view(strokeWidth=0).configure_axis(grid=True, gridColor='#333')
        
        st.altair_chart(chart, use_container_width=True)
        st.caption("📊 **Línea roja**: 90% (Meta) | **Línea naranja**: 85% (Mínimo)")


def _render_detalle_fabricaciones(mos, fecha_inicio_rep, fecha_fin_rep, username, password, tipo_filtro=None):
    """Renderiza tabla de fabricaciones con filtros.
    
    Args:
        tipo_filtro: 'PROCESO', 'CONGELADO' o None (todas)
    """
    st.markdown("---")
    if tipo_filtro == 'PROCESO':
        st.subheader("📋 Detalle de Fabricaciones - Proceso (Vaciado)")
    elif tipo_filtro == 'CONGELADO':
        st.subheader("📋 Detalle de Fabricaciones - Congelado (Túneles)")
    else:
        st.subheader("📋 Detalle de Fabricaciones - Todas")
    
    df_mos_original = pd.DataFrame(mos)
    
    # Crear sufijo único para las claves según el tipo de filtro
    key_suffix = f"_{tipo_filtro}" if tipo_filtro else "_global"
    
    with st.expander("🔍 Filtros de Fabricaciones", expanded=True):
        st.markdown("**🎯 Filtro Principal:**")
        filter_tipo_col = st.columns([2, 1, 1])
        with filter_tipo_col[0]:
            if 'sala_tipo' in df_mos_original.columns:
                tipos_unicos = sorted(df_mos_original['sala_tipo'].dropna().unique().tolist())
                tipo_labels = {'PROCESO': '🏭 Proceso (Vaciado)', 'CONGELADO': '❄️ Congelado (Túneles)', 'SIN_SALA': '⚠️ Sin Sala'}
                tipos_display = [tipo_labels.get(t, t) for t in tipos_unicos]
                tipo_sel_display = st.multiselect(
                    "📌 Tipo de Operación", tipos_display, key=f"filtro_tipo_detalle{key_suffix}",
                    help="Filtra entre Proceso (Vaciado) vs Congelado (Túneles)"
                )
                tipo_reverse = {v: k for k, v in tipo_labels.items()}
                tipos_sel = [tipo_reverse.get(t, t) for t in tipo_sel_display]
            else:
                tipos_sel = []
        
        st.markdown("---")
        st.markdown("**🔧 Filtros Adicionales:**")
        
        filter_cols = st.columns(5)
        with filter_cols[0]:
            of_buscar = st.text_input("🔎 Buscar OF", "", key=f"filtro_of_detalle{key_suffix}", placeholder="Ej: WH/MO/00123")
        with filter_cols[1]:
            productos_unicos = sorted(df_mos_original['product_name'].dropna().unique().tolist())
            productos_sel = st.multiselect("📦 Producto", productos_unicos, key=f"filtro_producto_detalle{key_suffix}")
        with filter_cols[2]:
            if 'especie' in df_mos_original.columns:
                especies_unicas = sorted(df_mos_original['especie'].dropna().unique().tolist())
                especies_sel = st.multiselect("🍓 Especie", especies_unicas, key=f"filtro_especie_detalle{key_suffix}")
            else:
                especies_sel = []
        with filter_cols[3]:
            if 'manejo' in df_mos_original.columns:
                manejos_unicos = sorted(df_mos_original['manejo'].dropna().unique().tolist())
                manejos_sel = st.multiselect("🏷️ Manejo", manejos_unicos, key=f"filtro_manejo_detalle{key_suffix}")
            else:
                manejos_sel = []
        with filter_cols[4]:
            salas_unicas = sorted(df_mos_original['sala'].dropna().unique().tolist())
            salas_sel = st.multiselect("🏭 Sala", salas_unicas, key=f"filtro_sala_detalle{key_suffix}")
    
    # Aplicar filtros
    df_mos = df_mos_original.copy()
    
    if of_buscar:
        df_mos = df_mos[df_mos['mo_name'].str.contains(of_buscar, case=False, na=False)]
    if productos_sel:
        df_mos = df_mos[df_mos['product_name'].isin(productos_sel)]
    if especies_sel and 'especie' in df_mos.columns:
        df_mos = df_mos[df_mos['especie'].isin(especies_sel)]
    if manejos_sel and 'manejo' in df_mos.columns:
        df_mos = df_mos[df_mos['manejo'].isin(manejos_sel)]
    if salas_sel:
        df_mos = df_mos[df_mos['sala'].isin(salas_sel)]
    if tipos_sel and 'sala_tipo' in df_mos.columns:
        df_mos = df_mos[df_mos['sala_tipo'].isin(tipos_sel)]
    
    df_mos['estado'] = df_mos['rendimiento'].apply(get_alert_color)
    
    # Preparar columnas
    cols_to_show = ['estado', 'mo_name', 'product_name']
    col_names = ['', 'OF', 'Producto']
    
    if 'especie' in df_mos.columns:
        cols_to_show.append('especie')
        col_names.append('Especie')
    if 'manejo' in df_mos.columns:
        cols_to_show.append('manejo')
        col_names.append('Manejo')
    
    if 'sala_tipo' in df_mos.columns:
        tipo_mapping = {'PROCESO': '🏭 Vaciado', 'CONGELADO': '❄️ Túnel', 'SIN_SALA': '⚠️ Sin Sala'}
        df_mos['tipo_display'] = df_mos['sala_tipo'].apply(lambda x: tipo_mapping.get(x, x))
        cols_to_show.append('tipo_display')
        col_names.append('Tipo Proceso')
    
    cols_to_show.extend(['sala', 'kg_mp', 'kg_pt', 'rendimiento', 'kg_merma'])
    col_names.extend(['Sala', 'Kg MP', 'Kg PT', 'Rend %', 'Merma'])
    
    if 'costo_electricidad' in df_mos.columns:
        cols_to_show.append('costo_electricidad')
        col_names.append('⚡ Elec $')
    
    cols_to_show.append('fecha')
    col_names.append('Fecha')
    
    df_mos_display = df_mos[cols_to_show].copy()
    df_mos_display.columns = col_names
    
    df_mos_display['Kg MP'] = df_mos_display['Kg MP'].apply(lambda x: fmt_numero(x, 0))
    df_mos_display['Kg PT'] = df_mos_display['Kg PT'].apply(lambda x: fmt_numero(x, 0))
    df_mos_display['Rend %'] = df_mos_display['Rend %'].apply(lambda x: fmt_porcentaje(x))
    df_mos_display['Merma'] = df_mos_display['Merma'].apply(lambda x: fmt_numero(x, 0))
    if '⚡ Elec $' in df_mos_display.columns:
        df_mos_display['⚡ Elec $'] = df_mos_display['⚡ Elec $'].apply(lambda x: f"${fmt_numero(x, 0)}" if x > 0 else "-")
    
    total_registros = len(df_mos_original)
    filtrados = len(df_mos)
    
    if filtrados < total_registros:
        st.caption(f"📋 Mostrando **{filtrados}** de {total_registros} órdenes (filtrado)")
    else:
        st.caption(f"📋 Mostrando {filtrados} órdenes")
    
    if filtrados > 0:
        st.dataframe(df_mos_display, use_container_width=True, hide_index=True, height=400)
    else:
        st.warning("No hay fabricaciones que coincidan con los filtros.")
    
    # Exportaciones
    st.markdown("---")
    st.subheader("📥 Descargar Datos de Producción")
    
    col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 1])
    
    export_cols = ['mo_name', 'product_name']
    export_names = ['OF', 'Producto']
    if 'especie' in df_mos.columns:
        export_cols.append('especie')
        export_names.append('Especie')
    if 'manejo' in df_mos.columns:
        export_cols.append('manejo')
        export_names.append('Manejo')
    export_cols.extend(['sala', 'kg_mp', 'kg_pt', 'rendimiento', 'kg_merma'])
    export_names.extend(['Sala', 'Kg MP', 'Kg PT', 'Rendimiento %', 'Merma Kg'])
    if 'sala_tipo' in df_mos.columns:
        export_cols.append('sala_tipo')
        export_names.append('Tipo Operación')
    if 'costo_electricidad' in df_mos.columns:
        export_cols.append('costo_electricidad')
        export_names.append('Costo Electricidad $')
    export_cols.extend(['duracion_horas', 'dotacion', 'fecha'])
    export_names.extend(['Horas', 'Dotación', 'Fecha'])
    
    df_export = df_mos[export_cols].copy()
    df_export.columns = export_names
    
    with col_exp1:
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button("📄 Descargar CSV", csv, "produccion_fabricaciones.csv", "text/csv", key=f"download_csv_prod{key_suffix}")
    
    with col_exp2:
        try:
            excel_buffer = io.BytesIO()
            df_export.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)
            st.download_button(
                "📊 Descargar Excel", excel_buffer,
                "produccion_fabricaciones.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_excel_prod{key_suffix}"
            )
        except Exception as e:
            st.warning(f"No se pudo generar Excel: {e}")
    
    with col_exp3:
        if st.button("📕 Generar Informe PDF", key=f"btn_pdf_prod{key_suffix}", type="secondary"):
            fi = fecha_inicio_rep.strftime("%Y-%m-%d")
            ff = fecha_fin_rep.strftime("%Y-%m-%d")
            try:
                with st.spinner("Generando informe PDF..."):
                    resp = requests.get(
                        f"{API_URL}/api/v1/rendimiento/report.pdf",
                        params={"username": username, "password": password, "fecha_inicio": fi, "fecha_fin": ff},
                        timeout=180
                    )
                if resp.status_code == 200:
                    pdf_bytes = resp.content
                    fname = f"produccion_{fi}_a_{ff}.pdf".replace('/', '-')
                    st.download_button("⬇️ Descargar PDF", data=pdf_bytes, file_name=fname, mime='application/pdf', key=f"download_pdf_prod{key_suffix}")
                    st.success("PDF generado correctamente")
                else:
                    st.error(f"Error al generar PDF: {resp.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")


def _render_info_ayuda():
    """Renderiza información de ayuda."""
    with st.expander("ℹ️ ¿Qué incluye la reportería general?"):
        st.markdown("""
        ### Métricas Disponibles
        
        | Métrica | Descripción |
        |---------|-------------|
        | **Rendimiento %** | Kg PT / Kg MP × 100 (ponderado por volumen) |
        | **Merma** | Kg MP - Kg PT |
        | **Kg/HH** | Productividad: Kg PT / Horas Hombre |
        | **Kg/Hora** | Velocidad: Kg PT / Horas de proceso |
        
        ### Alertas de Rendimiento
        
        - 🟢 **≥ 95%** - Excelente
        - 🟡 **90-95%** - Atención
        - 🔴 **< 90%** - Crítico
        """)

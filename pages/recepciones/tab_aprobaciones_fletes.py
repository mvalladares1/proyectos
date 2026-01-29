"""
Tab de Aprobaciones de Fletes para Máximo Sepúlveda.
Consolida datos de Odoo + Sistema de Logística para mostrar:
- OCs pendientes de aprobación
- Costos reales vs presupuestados
- % de desviación
- KPIs de negociación
- Aprobaciones masivas
"""

import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from recepciones.shared import fmt_dinero, API_URL


def render_tab(username, password):
    """Renderiza el tab de aprobaciones de fletes"""
    
    st.header("✅ Aprobaciones de Órdenes de Compra - Fletes y Transportes")
    
    # KPIs del período
    render_kpis_periodo(username, password)
    
    st.markdown("---")
    
    # Tabla de OCs pendientes con datos consolidados
    render_tabla_aprobaciones(username, password)


@st.cache_data(ttl=300)  # Cache 5 minutos
def get_ocs_pendientes(username, password):
    """Obtiene OCs pendientes con datos consolidados"""
    try:
        response = requests.get(
            f"{API_URL}/api/v1/aprobaciones-fletes/pendientes",
            params={'username': username, 'password': password},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data', [])
        else:
            st.error(f"Error al obtener OCs: {response.status_code}")
            return []
    
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return []


@st.cache_data(ttl=300)
def get_kpis_fletes(username, password, dias=30):
    """Obtiene KPIs de fletes"""
    try:
        response = requests.get(
            f"{API_URL}/api/v1/aprobaciones-fletes/kpis",
            params={'username': username, 'password': password, 'dias': dias},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('kpis', {})
        else:
            return {}
    
    except Exception as e:
        st.error(f"Error al obtener KPIs: {e}")
        return {}


def aprobar_oc(username, password, oc_id):
    """Aprueba una OC"""
    try:
        response = requests.post(
            f"{API_URL}/api/v1/aprobaciones-fletes/aprobar",
            params={'username': username, 'password': password, 'oc_id': oc_id},
            timeout=30
        )
        
        return response.status_code == 200
    
    except Exception as e:
        st.error(f"Error al aprobar OC: {e}")
        return False


def aprobar_multiples_ocs(username, password, oc_ids):
    """Aprueba múltiples OCs"""
    try:
        # FastAPI espera lista en query params: oc_ids=1&oc_ids=2&oc_ids=3
        params = {'username': username, 'password': password}
        for oc_id in oc_ids:
            params[f'oc_ids'] = oc_id
        
        response = requests.post(
            f"{API_URL}/api/v1/aprobaciones-fletes/aprobar-multiples",
            params=params,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json().get('resultado', {})
        else:
            return None
    
    except Exception as e:
        st.error(f"Error al aprobar OCs: {e}")
        return None


def render_kpis_periodo(username, password):
    """Renderiza KPIs del período"""
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 KPIs del Período")
    
    with col2:
        dias = st.selectbox("Período", [7, 15, 30, 60, 90], index=2, key="periodo_kpis")
    
    kpis = get_kpis_fletes(username, password, dias)
    
    if kpis:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Total OCs",
                kpis.get('total_ocs', 0),
                help=f"OCs de fletes en los últimos {dias} días"
            )
        
        with col2:
            pendientes = kpis.get('pendientes', 0)
            st.metric(
                "⏳ Pendientes",
                pendientes,
                delta=f"-{pendientes}" if pendientes > 0 else "Al día",
                delta_color="inverse"
            )
        
        with col3:
            st.metric(
                "✅ Aprobadas",
                kpis.get('aprobadas', 0)
            )
        
        with col4:
            monto_total = kpis.get('monto_total', 0)
            st.metric(
                "💰 Monto Total",
                fmt_dinero(monto_total, decimales=0)
            )
        
        with col5:
            promedio = kpis.get('promedio_por_oc', 0)
            st.metric(
                "📊 Promedio/OC",
                fmt_dinero(promedio, decimales=0)
            )


def render_tabla_aprobaciones(username, password):
    """Renderiza tabla de OCs pendientes con aprobaciones"""
    
    st.subheader("📋 Órdenes de Compra Pendientes de Aprobación")
    
    # Botón para refrescar datos
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refrescar Datos", key="btn_refresh"):
            st.cache_data.clear()
            st.rerun()
    
    # Obtener datos
    with st.spinner("Cargando órdenes pendientes..."):
        ocs = get_ocs_pendientes(username, password)
    
    if not ocs:
        st.info("✅ No hay órdenes de compra pendientes de aprobación")
        return
    
    st.info(f"📦 {len(ocs)} órdenes pendientes de aprobación")
    
    # Calcular estadísticas de negociación
    ocs_con_desviacion = [oc for oc in ocs if oc.get('desviacion_pct') is not None]
    
    if ocs_con_desviacion:
        negociaciones_favorables = sum(1 for oc in ocs_con_desviacion if oc['desviacion_favorable'])
        negociaciones_desfavorables = len(ocs_con_desviacion) - negociaciones_favorables
        desviacion_promedio = sum(oc['desviacion_pct'] for oc in ocs_con_desviacion) / len(ocs_con_desviacion)
        ahorro_total = sum((oc['costo_presupuestado'] - oc['costo_real']) for oc in ocs_con_desviacion if oc['desviacion_favorable'])
        sobrecosto_total = sum((oc['costo_real'] - oc['costo_presupuestado']) for oc in ocs_con_desviacion if not oc['desviacion_favorable'])
        
        st.markdown("### 📊 Análisis de Negociación")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "OCs Analizadas",
                len(ocs_con_desviacion),
                help="OCs con información de costos presupuestados"
            )
        
        with col2:
            st.metric(
                "✅ Negociaciones Favorables",
                negociaciones_favorables,
                delta=f"{(negociaciones_favorables/len(ocs_con_desviacion)*100):.0f}%",
                delta_color="normal"
            )
        
        with col3:
            st.metric(
                "⚠️ Negociaciones Desfavorables",
                negociaciones_desfavorables,
                delta=f"{(negociaciones_desfavorables/len(ocs_con_desviacion)*100):.0f}%",
                delta_color="inverse"
            )
        
        with col4:
            color_desviacion = "normal" if desviacion_promedio <= 0 else "inverse"
            st.metric(
                "📈 Desviación Promedio",
                f"{desviacion_promedio:+.1f}%",
                delta="Favorable" if desviacion_promedio <= 0 else "Desfavorable",
                delta_color=color_desviacion
            )
        
        with col5:
            balance = ahorro_total - sobrecosto_total
            st.metric(
                "💰 Balance Total",
                fmt_dinero(balance, decimales=0),
                delta=f"Ahorro: {fmt_dinero(ahorro_total, decimales=0)}" if balance > 0 else f"Sobrecosto: {fmt_dinero(sobrecosto_total, decimales=0)}",
                delta_color="normal" if balance >= 0 else "inverse"
            )
        
        st.markdown("---")
    
    # Convertir a DataFrame para mostrar
    df_data = []
    for oc in ocs:
        df_data.append({
            'ID': oc['oc_id'],
            'OC': oc['oc_name'],
            'Estado': oc['oc_state'],
            'Proveedor': oc['proveedor'],
            'Monto': oc['oc_amount'],
            'Fecha': oc['fecha_orden'][:10] if oc['fecha_orden'] else '',
            'Ruta': oc['ruta_name'] if oc['tiene_info_logistica'] else 'N/A',
            'Distancia (km)': f"{oc['distancia_km']:.1f}" if oc['tiene_info_logistica'] and oc['distancia_km'] > 0 else 'N/A',
            'Costo Real': oc['costo_real'] if oc['tiene_info_logistica'] else 0,
            'Info Logística': '✅' if oc['tiene_info_logistica'] else '❌',
        })
    
    df = pd.DataFrame(df_data)
    
    # Selector de OCs para aprobación masiva
    st.markdown("### Selecciona OCs para aprobar")
    
    # Usar checkbox para selección masiva
    if st.checkbox("Seleccionar todas", key="select_all"):
        selected_ids = [oc['oc_id'] for oc in ocs]
    else:
        selected_ids = []
    
    # Mostrar tabla con checkboxes individuales
    for idx, oc in enumerate(ocs):
        # Determinar emoji de estado de negociación
        emoji_negociacion = ""
        color_negociacion = "blue"
        
        if oc.get('desviacion_pct') is not None:
            if oc['desviacion_favorable']:
                emoji_negociacion = "✅💰"  # Negociación favorable
                color_negociacion = "green"
            else:
                emoji_negociacion = "⚠️📈"  # Negociación desfavorable
                color_negociacion = "orange"
        
        # Título del expander con link a Odoo
        titulo_expander = f"{'✅' if oc['tiene_info_logistica'] else '❌'} {emoji_negociacion} **[{oc['oc_name']}]({oc['oc_url']})** - {oc['proveedor']} - {fmt_dinero(oc['oc_amount'], decimales=0)}"
        
        with st.expander(titulo_expander):
            col1, col2, col3 = st.columns([1, 3, 1])
            
            with col1:
                is_selected = st.checkbox(
                    f"Seleccionar",
                    value=oc['oc_id'] in selected_ids,
                    key=f"check_oc_{oc['oc_id']}"
                )
                
                if is_selected and oc['oc_id'] not in selected_ids:
                    selected_ids.append(oc['oc_id'])
                elif not is_selected and oc['oc_id'] in selected_ids:
                    selected_ids.remove(oc['oc_id'])
            
            with col2:
                # Información detallada
                st.markdown(f"**Estado:** {oc['oc_state']}")
                st.markdown(f"**Fecha:** {oc['fecha_orden'][:10] if oc['fecha_orden'] else 'N/A'}")
                st.markdown(f"**Creado por:** {oc['usuario_creador']}")
                
                if oc['tiene_info_logistica']:
                    st.markdown(f"**🚚 Ruta:** {oc['ruta_name']}")
                    st.markdown(f"**📏 Distancia:** {oc['distancia_km']:.1f} km")
                    
                    # Tipo de vehículo
                    if oc.get('tipo_vehiculo'):
                        st.markdown(f"**🚛 Tipo Vehículo:** {oc['tipo_vehiculo']}")
                    
                    st.markdown(f"**💰 Costo Real:** {fmt_dinero(oc['costo_real'], decimales=0)}")
                    
                    if oc['costo_ruta_negociado'] and oc['costo_ruta_negociado'] > 0:
                        st.markdown(f"**💵 Costo Negociado:** {fmt_dinero(oc['costo_ruta_negociado'], decimales=0)}")
                    
                    # Análisis de desviación
                    if oc.get('costo_presupuestado'):
                        st.markdown(f"**📊 Costo Presupuestado:** {fmt_dinero(oc['costo_presupuestado'], decimales=0)}")
                        
                        if oc.get('ruta_presupuesto_nombre'):
                            st.markdown(f"**📍 Ruta Presupuesto:** {oc['ruta_presupuesto_nombre']} ({oc['ruta_presupuesto_km']:.0f} km)")
                        
                        if oc.get('desviacion_pct') is not None:
                            desv = oc['desviacion_pct']
                            if oc['desviacion_favorable']:
                                st.success(f"✅ **Desviación: {desv:+.1f}%** (Ahorro de {fmt_dinero(oc['costo_presupuestado'] - oc['costo_real'], decimales=0)})")
                            else:
                                st.warning(f"⚠️ **Desviación: {desv:+.1f}%** (Sobrecosto de {fmt_dinero(oc['costo_real'] - oc['costo_presupuestado'], decimales=0)})")
                    
                    if oc['cantidad_kg'] > 0:
                        st.markdown(f"**⚖️ Cantidad:** {oc['cantidad_kg']:,.0f} kg")
                        st.markdown(f"**📊 Costo/kg:** {fmt_dinero(oc['costo_por_kg'], decimales=2)}")
                else:
                    st.warning("⚠️ No hay información del sistema de logística para esta OC")
                
                # Mostrar líneas de la OC
                if oc.get('lines'):
                    st.markdown("**Líneas de la OC:**")
                    for line in oc['lines']:
                        producto = line.get('product_id', [False, 'N/A'])[1] if line.get('product_id') else line.get('name', 'N/A')
                        cantidad = line.get('product_qty', 0)
                        precio_unit = line.get('price_unit', 0)
                        subtotal = line.get('price_subtotal', 0)
                        
                        st.markdown(f"  - {producto}: {cantidad} x {fmt_dinero(precio_unit)} = {fmt_dinero(subtotal)}")
            
            with col3:
                if st.button(f"✅ Aprobar", key=f"btn_aprobar_{oc['oc_id']}", type="primary"):
                    with st.spinner("Aprobando..."):
                        if aprobar_oc(username, password, oc['oc_id']):
                            st.success(f"✅ OC {oc['oc_name']} aprobada")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ Error al aprobar OC")
    
    # Botón de aprobación masiva
    st.markdown("---")
    if selected_ids:
        col1, col2, col3 = st.columns([1, 2, 2])
        
        with col1:
            st.info(f"📦 {len(selected_ids)} OCs seleccionadas")
        
        with col2:
            if st.button(f"✅ Aprobar {len(selected_ids)} OCs seleccionadas", type="primary", key="btn_aprobar_masivo"):
                with st.spinner(f"Aprobando {len(selected_ids)} órdenes..."):
                    resultado = aprobar_multiples_ocs(username, password, selected_ids)
                    
                    if resultado:
                        st.success(f"✅ {resultado['aprobadas']} OCs aprobadas correctamente")
                        
                        if resultado['fallidas'] > 0:
                            st.warning(f"⚠️ {resultado['fallidas']} OCs fallaron")
                        
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ Error en aprobación masiva")

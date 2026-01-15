"""
Dashboard de Reconciliación de Producción
==========================================

Gestión completa de ODFs:
1. Trigger SO Asociada - Activa automatización de Odoo
2. Reconciliación KG - Calcula y actualiza campos de seguimiento
"""
import streamlit as st
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Añadir directorios al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.auth import proteger_modulo, get_credenciales, tiene_acceso_dashboard, tiene_acceso_pagina

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos
from produccion import shared_reconciliacion as shared
from produccion import tab_trigger_lista, tab_trigger_ejecutar, tab_reconciliar_kg

# Configuración de página
st.set_page_config(
    page_title="Reconciliación Producción",
    page_icon="🔄",
    layout="wide"
)

# Verificar autenticación
if not proteger_modulo("reconciliacion"):
    st.stop()

if not tiene_acceso_dashboard("reconciliacion"):
    st.error("🚫 No tienes permisos para ver este dashboard.")
    st.stop()

# Obtener credenciales
username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales válidas.")
    st.stop()

# Inicializar session state
shared.init_session_state_trigger()
shared.init_session_state_reconciliacion()

# Título
st.title("🔄 Reconciliación de Producción")
st.caption("Gestión de SO Asociada y Campos KG en ODFs")

# === PRE-CALCULAR PERMISOS ===
_perm_trigger = tiene_acceso_pagina("reconciliacion", "trigger_so")
_perm_kg = tiene_acceso_pagina("reconciliacion", "reconciliar_kg")

# ============================================================================
# SIDEBAR - FILTROS COMPARTIDOS
# ============================================================================

st.sidebar.header("⚙️ Configuración")

# Rango de fechas
st.sidebar.subheader("📅 Rango de Fechas")

col1, col2 = st.sidebar.columns(2)

with col1:
    fecha_inicio = st.date_input(
        "Desde",
        value=datetime.now().date() - timedelta(days=7),
        help="Fecha inicio de búsqueda",
        key="fecha_inicio"
    )

with col2:
    fecha_fin = st.date_input(
        "Hasta",
        value=datetime.now().date(),
        help="Fecha fin de búsqueda",
        key="fecha_fin"
    )

st.sidebar.divider()

# Configuración
st.sidebar.subheader("⚡ Configuración")

wait_seconds = st.sidebar.slider(
    "Espera entre operaciones",
    min_value=1.0,
    max_value=5.0,
    value=2.0,
    step=0.5,
    help="Segundos entre operaciones (trigger)",
    key="wait_seconds"
)

limit = st.sidebar.number_input(
    "Límite de ODFs",
    min_value=1,
    max_value=200,
    value=50,
    help="Máximo de ODFs a buscar",
    key="limit"
)

st.sidebar.divider()

# Botones de búsqueda
st.sidebar.subheader("🔍 Búsqueda")

buscar_trigger = st.sidebar.button(
    "🔄 Buscar ODFs sin SO",
    use_container_width=True,
    help="Busca ODFs que tienen PO Cliente pero no SO Asociada"
)

buscar_kg = st.sidebar.button(
    "🔢 Buscar ODFs para KG",
    use_container_width=True,
    help="Busca ODFs con SO Asociada para reconciliar KG"
)

# Manejar búsquedas
if buscar_trigger:
    with st.spinner("🔍 Buscando ODFs sin SO Asociada..."):
        resultado = shared.buscar_odfs_sin_so(
            fecha_inicio=fecha_inicio.isoformat(),
            fecha_fin=fecha_fin.isoformat(),
            limit=limit
        )
        
        if resultado.get('success'):
            st.session_state['trigger_odfs_pendientes'] = resultado.get('odfs', [])
            st.session_state['trigger_total_pendientes'] = resultado.get('total', 0)
            st.sidebar.success(f"✓ {resultado.get('total', 0)} ODFs encontrados")
        else:
            st.sidebar.error(f"❌ {resultado.get('error')}")
            st.session_state['trigger_odfs_pendientes'] = []

if buscar_kg:
    with st.spinner("🔍 Buscando ODFs con SO Asociada..."):
        resultado = shared.buscar_odfs_para_reconciliar(
            fecha_inicio=fecha_inicio.isoformat(),
            fecha_fin=fecha_fin.isoformat(),
            limit=limit
        )
        
        if resultado.get('success'):
            # Filtrar solo los que tienen SO Asociada
            odfs_con_so = [
                odf for odf in resultado.get('odfs', [])
                if odf.get('x_studio_po_asociada')
            ]
            st.session_state['trigger_odfs_kg'] = odfs_con_so
            st.sidebar.success(f"✓ {len(odfs_con_so)} ODFs encontrados")
        else:
            st.sidebar.error(f"❌ {resultado.get('error')}")
            st.session_state['trigger_odfs_kg'] = []

# ============================================================================
# MÉTRICAS PRINCIPALES
# ============================================================================

col1, col2, col3 = st.columns(3)

with col1:
    total_sin_so = st.session_state.get('trigger_total_pendientes', 0)
    st.metric("📋 ODFs sin SO", total_sin_so)

with col2:
    total_con_so = len(st.session_state.get('trigger_odfs_kg', []))
    st.metric("🔢 ODFs con SO", total_con_so)

with col3:
    dias = (fecha_fin - fecha_inicio).days + 1
    st.metric("📅 Rango", f"{dias} días")

st.divider()

# ============================================================================
# TABS PRINCIPALES
# ============================================================================

tab_trigger_lista_ui, tab_trigger_exec_ui, tab_kg_ui = st.tabs([
    "📋 Lista ODFs sin SO",
    "🚀 Trigger SO Asociada",
    "🔢 Reconciliar KG"
])

# Tab 1: Lista de ODFs sin SO
with tab_trigger_lista_ui:
    if _perm_trigger:
        tab_trigger_lista.render()
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos.")

# Tab 2: Ejecutar Trigger
with tab_trigger_exec_ui:
    if _perm_trigger:
        tab_trigger_ejecutar.render(wait_seconds)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos.")

# Tab 3: Reconciliar KG
with tab_kg_ui:
    if _perm_kg:
        tab_reconciliar_kg.render(wait_seconds)
    else:
        st.error("🚫 **Acceso Restringido** - No tienes permisos.")

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption("""
💡 **Tips:**
- **Trigger SO Asociada**: Borra y reescribe PO Cliente para activar automatización de Odoo
- **Reconciliar KG**: Calcula KG Totales/Consumidos/Disponibles basándose en SO y subproductos
- Los ODFs fallidos en Trigger generalmente no tienen SO con ese origen (normal)
""")


def render_distribucion_so(analisis: List[Dict]):
    """
    Gráfico de torta de distribución de consumo por SO.
    """
    if not analisis:
        return
    
    df = pd.DataFrame(analisis)
    
    fig = px.pie(
        df,
        values='kg_consumidos',
        names='so_nombre',
        title='📊 Distribución de Consumo por SO',
        hole=0.3
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_eficiencia_comparativa(analisis: List[Dict]):
    """
    Barra comparativa de eficiencia por SO.
    """
    if not analisis:
        return
    
    df = pd.DataFrame(analisis)
    
    fig = px.bar(
        df,
        x='so_nombre',
        y='eficiencia_%',
        title='📈 Eficiencia por SO',
        labels={'eficiencia_%': 'Eficiencia (%)', 'so_nombre': 'Sale Order'},
        color='eficiencia_%',
        color_continuous_scale=['red', 'yellow', 'green']
    )
    
    fig.add_hline(y=85, line_dash="dash", line_color="green", annotation_text="Target 85%")
    
    st.plotly_chart(fig, use_container_width=True)


def render_tabla_consumos_raw(consumos: List[Dict], limit: int = 20):
    """
    Tabla expandible de consumos atómicos (para debug).
    """
    with st.expander(f"🔍 Ver consumos raw (primeros {limit})"):
        df = pd.DataFrame(consumos[:limit])
        if not df.empty:
            # Formatear timestamp
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )


# ============================================
# RENDERIZADO DE ALERTAS
# ============================================

def render_alertas(alertas: List[Dict]):
    """
    Muestra alertas detectadas con iconos y colores.
    """
    if not alertas:
        st.success("✅ No hay alertas")
        return
    
    st.subheader("⚠️ Alertas Detectadas")
    
    for alerta in alertas:
        tipo = alerta.get('tipo', 'INFO')
        mensaje = alerta.get('mensaje', '')
        detalle = alerta.get('detalle', '')
        
        if tipo == 'WARNING':
            st.warning(f"⚠️ {mensaje}")
        elif tipo == 'ERROR':
            st.error(f"❌ {mensaje}")
        else:
            st.info(f"ℹ️ {mensaje}")
        
        if detalle:
            st.caption(f"   → {detalle}")


# ============================================
# RENDERIZADO DE RESUMEN
# ============================================

def render_resumen(resumen: Dict):
    """
    KPIs principales en métricas.
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "SO en esta ODF",
            resumen.get('total_so', 0),
            help="Número de Sale Orders diferentes procesadas"
        )
    
    with col2:
        st.metric(
            "Kg Consumidos",
            f"{resumen.get('total_kg_consumidos', 0):,.1f}",
            help="Total de materia prima consumida"
        )
    
    with col3:
        st.metric(
            "Kg Producidos",
            f"{resumen.get('total_kg_producidos', 0):,.1f}",
            help="Total producido en esta ODF"
        )
    
    with col4:
        eficiencia = resumen.get('eficiencia_global_%', 0)
        delta_color = "normal" if eficiencia >= 85 else "inverse"
        st.metric(
            "Eficiencia Global",
            f"{eficiencia:.1f}%",
            delta=f"{eficiencia - 85:.1f}%" if eficiencia > 0 else None,
            delta_color=delta_color,
            help="Producido / Consumido * 100"
        )
    
    if resumen.get('so_dominante'):
        st.info(f"📌 **SO Dominante:** {resumen['so_dominante']}")


# ============================================
# RENDERIZADO DE ANÁLISIS DETALLADO
# ============================================

def render_analisis_detallado(analisis: List[Dict]):
    """
    Tabla con todas las métricas por SO.
    """
    if not analisis:
        st.warning("No hay análisis disponible")
        return
    
    st.subheader("📋 Análisis Detallado por SO")
    
    df = pd.DataFrame(analisis)
    
    # Formatear columnas
    if 'inicio' in df.columns:
        df['Inicio'] = pd.to_datetime(df['inicio']).dt.strftime('%H:%M:%S')
    if 'fin' in df.columns:
        df['Fin'] = pd.to_datetime(df['fin']).dt.strftime('%H:%M:%S')
    
    # Seleccionar columnas para mostrar
    columnas_mostrar = {
        'so_nombre': 'Sale Order',
        'kg_consumidos': 'Kg Consumidos',
        'kg_producidos_estimado': 'Kg Producidos',
        'eficiencia_%': 'Eficiencia %',
        'tiempo_minutos': 'Tiempo (min)',
        'velocidad_kg_h': 'Velocidad (kg/h)',
        'porcentaje_odf': '% de ODF'
    }
    
    # Renombrar
    df_display = df[[k for k in columnas_mostrar.keys() if k in df.columns]].copy()
    df_display.columns = [columnas_mostrar[c] for c in df_display.columns]
    
    # Colorear eficiencia
    def color_eficiencia(val):
        if val >= 85:
            return 'background-color: #d4edda'
        elif val >= 70:
            return 'background-color: #fff3cd'
        else:
            return 'background-color: #f8d7da'
    
    if 'Eficiencia %' in df_display.columns:
        styled = df_display.style.applymap(
            color_eficiencia,
            subset=['Eficiencia %']
        ).format({
            'Kg Consumidos': '{:,.1f}',
            'Kg Producidos': '{:,.1f}',
            'Eficiencia %': '{:.1f}%',
            'Tiempo (min)': '{:.0f}',
            'Velocidad (kg/h)': '{:.1f}',
            '% de ODF': '{:.1f}%'
        })
        
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_display, use_container_width=True, hide_index=True)


# ============================================
# MAIN APP
# ============================================

def main():
    st.title("🔄 Reconciliación de Producción")
    
    st.markdown("""
    ### El problema que resolvemos:
    
    **Una ODF puede consumir materiales de MÚLTIPLES SO en un flujo continuo.**
    
    Odoo registra los hechos (consumos con timestamp).
    Este dashboard **interpreta** la realidad comercial:
    - Detecta automáticamente dónde termina una SO y empieza otra
    - Calcula eficiencia real por pedido
    - Visualiza la distribución temporal de los pedidos
    - Genera alertas cuando algo está fuera de rango
    
    ---
    """)
    
    # Configuración
    api_url = st.session_state.get('api_url', 'http://127.0.0.1:8002')
    
    # Input de ODF
    odf_id = st.number_input(
        "🔢 ID de la ODF a analizar",
        min_value=1,
        value=None,
        placeholder="Ej: 1234",
        help="Ingresa el ID de la Manufacturing Order"
    )
    
    if not odf_id:
        st.info("👆 Ingresa un ID de ODF para comenzar el análisis")
        st.stop()
    
    # Botón de análisis
    if st.button("🚀 Analizar ODF", type="primary", use_container_width=True):
        with st.spinner(f"Analizando ODF #{odf_id}..."):
            try:
                resultado = reconciliar_odf(odf_id, api_url)
                st.session_state['ultimo_resultado'] = resultado
                st.success(f"✅ Análisis completado: {resultado['odf_nombre']}")
            except requests.HTTPError as e:
                st.error(f"❌ Error HTTP: {e}")
                st.stop()
            except Exception as e:
                st.error(f"❌ Error: {e}")
                st.stop()
    
    # Mostrar resultado si existe
    if 'ultimo_resultado' in st.session_state:
        resultado = st.session_state['ultimo_resultado']
        
        st.divider()
        
        # Header
        st.header(f"📦 {resultado['odf_nombre']}")
        
        # Resumen
        render_resumen(resultado['resumen'])
        
        st.divider()
        
        # Alertas
        render_alertas(resultado['alertas'])
        
        st.divider()
        
        # Timeline
        st.subheader("🕒 Timeline de SO")
        render_timeline_so(resultado['segmentos_so'])
        
        # Visualizaciones lado a lado
        col1, col2 = st.columns(2)
        
        with col1:
            render_distribucion_so(resultado['analisis_so'])
        
        with col2:
            render_eficiencia_comparativa(resultado['analisis_so'])
        
        st.divider()
        
        # Tabla detallada
        render_analisis_detallado(resultado['analisis_so'])
        
        st.divider()
        
        # Datos raw
        render_tabla_consumos_raw(resultado['consumos_raw'])
        
        # Timestamp
        st.caption(f"📅 Análisis generado: {resultado['timestamp_analisis']}")


if __name__ == "__main__":
    main()

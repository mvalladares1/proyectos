"""
Dashboard de Automatizaciones - Túneles Estáticos
Permite crear órdenes de fabricación y monitorear su estado.
"""

import streamlit as st
import requests
from datetime import datetime
from typing import List, Dict
import pandas as pd

# Configuración de la página
st.set_page_config(
    page_title="Automatizaciones",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importar autenticación
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.auth import proteger_pagina, obtener_info_sesion
from shared.constants import API_URL

# Requerir autenticación
proteger_pagina()

# Obtener info de sesión
session_info = obtener_info_sesion()

# ============ Estilos Custom (Mobile-First) ============

st.markdown("""
<style>
    /* Botones grandes para mobile */
    .stButton > button {
        width: 100%;
        min-height: 48px;
        font-size: 16px;
        font-weight: 600;
        border-radius: 8px;
    }
    
    /* Input más grande */
    .stTextInput > div > div > input {
        font-size: 16px;
        min-height: 48px;
    }
    
    /* Radio buttons más grandes */
    .stRadio > div {
        gap: 12px;
    }
    
    .stRadio > div > label {
        min-height: 48px;
        font-size: 16px;
        padding: 8px 12px;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        cursor: pointer;
    }
    
    /* Cards de pallets */
    .pallet-card {
        background: #f8f9fa;
        border-left: 4px solid #4CAF50;
        padding: 12px;
        margin: 8px 0;
        border-radius: 4px;
    }
    
    /* Cards de órdenes */
    .orden-card {
        background: white;
        border: 1px solid #e0e0e0;
        padding: 16px;
        margin: 12px 0;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .orden-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Estados */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .badge-draft { background: #FFF3CD; color: #856404; }
    .badge-progress { background: #D1ECF1; color: #0C5460; }
    .badge-done { background: #D4EDDA; color: #155724; }
    .badge-cancel { background: #F8D7DA; color: #721C24; }
</style>
""", unsafe_allow_html=True)

# ============ Título ============

st.title("🤖 Automatizaciones")
st.markdown("**Túneles Estáticos** - Creación automatizada de órdenes de fabricación")

# ============ Tabs ============

tab1, tab2 = st.tabs(["📦 Crear Orden", "📊 Monitor de Órdenes"])

# ============ TAB 1: Crear Orden ============

with tab1:
    st.header("Crear Orden de Fabricación")
    
    # Obtener lista de túneles
    @st.cache_data(ttl=3600)
    def get_tuneles():
        try:
            response = requests.get(
                f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/procesos",
                headers={"Authorization": f"Bearer {session_info.get('token')}"}
            )
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []
    
    tuneles = get_tuneles()
    
    if not tuneles:
        st.error("❌ No se pudieron cargar los túneles disponibles")
    else:
        # Selector de túnel
        st.subheader("1️⃣ Seleccionar Túnel")
        
        tunel_options = {t['codigo']: f"{t['codigo']} - {t['nombre']} ({t['sucursal']})" for t in tuneles}
        selected_tunel = st.radio(
            "Túnel:",
            options=list(tunel_options.keys()),
            format_func=lambda x: tunel_options[x],
            horizontal=False,
            label_visibility="collapsed"
        )
        
        # Opción de búsqueda automática para VLK
        buscar_ubicacion_auto = False
        if selected_tunel == 'VLK':
            buscar_ubicacion_auto = st.checkbox(
                "🔍 Buscar ubicación automáticamente (para pallets mal ubicados)",
                value=True,
                help="Si está activado, busca la ubicación real del pallet aunque no esté en VLK/Camara 0°"
            )
        
        st.divider()
        
        # Input de pallets
        st.subheader("2️⃣ Agregar Pallets")
        
        # Inicializar session state para pallets
        if 'pallets_list' not in st.session_state:
            st.session_state.pallets_list = []
        
        # Tabs para modo de ingreso
        input_tab1, input_tab2 = st.tabs(["➕ Individual", "📋 Múltiple"])
        
        with input_tab1:
            col1, col2 = st.columns([3, 1])
            with col1:
                pallet_codigo = st.text_input(
                    "Código del pallet",
                    placeholder="PAC0002683",
                    key="pallet_input",
                    label_visibility="collapsed"
                )
            with col2:
                if st.button("➕ Agregar", use_container_width=True, type="primary"):
                    if pallet_codigo:
                        # Validar pallet
                        with st.spinner("Validando pallet..."):
                            try:
                                response = requests.post(
                                    f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/validar-pallets",
                                    headers={"Authorization": f"Bearer {session_info.get('token')}"},
                                    json={
                                        "pallets": [pallet_codigo],
                                        "buscar_ubicacion": buscar_ubicacion_auto
                                    }
                                )
                                if response.status_code == 200:
                                    validacion = response.json()[0]
                                    
                                    if validacion['existe']:
                                        # Agregar a la lista
                                        st.session_state.pallets_list.append({
                                            'codigo': validacion['codigo'],
                                            'kg': validacion.get('kg', 0.0),
                                            'ubicacion': validacion.get('ubicacion_nombre', 'N/A'),
                                            'advertencia': validacion.get('advertencia')
                                        })
                                        st.success(f"✅ {pallet_codigo} agregado!")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {validacion.get('error', 'Pallet no encontrado')}")
                                else:
                                    st.error("Error al validar pallet")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    else:
                        st.warning("⚠️ Ingresa un código de pallet")
        
        with input_tab2:
            pallets_textarea = st.text_area(
                "Ingresa múltiples pallets (uno por línea)",
                placeholder="PAC0002683\nPAC0006041\nPAC0005928",
                height=150,
                label_visibility="collapsed"
            )
            
            if st.button("➕ Agregar Todos", use_container_width=True, type="primary"):
                if pallets_textarea:
                    codigos = [c.strip() for c in pallets_textarea.split('\n') if c.strip()]
                    
                    if codigos:
                        with st.spinner(f"Validando {len(codigos)} pallets..."):
                            try:
                                response = requests.post(
                                    f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/validar-pallets",
                                    headers={"Authorization": f"Bearer {session_info.get('token')}"},
                                    json={
                                        "pallets": codigos,
                                        "buscar_ubicacion": buscar_ubicacion_auto
                                    }
                                )
                                if response.status_code == 200:
                                    validaciones = response.json()
                                    
                                    agregados = 0
                                    for val in validaciones:
                                        if val['existe']:
                                            st.session_state.pallets_list.append({
                                                'codigo': val['codigo'],
                                                'kg': val.get('kg', 0.0),
                                                'ubicacion': val.get('ubicacion_nombre', 'N/A'),
                                                'advertencia': val.get('advertencia')
                                            })
                                            agregados += 1
                                    
                                    if agregados > 0:
                                        st.success(f"✅ {agregados}/{len(codigos)} pallets agregados")
                                        st.rerun()
                                    else:
                                        st.error("❌ Ningún pallet fue encontrado")
                                else:
                                    st.error("Error al validar pallets")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                else:
                    st.warning("⚠️ Ingresa al menos un código de pallet")
        
        st.divider()
        
        # Lista de pallets agregados
        st.subheader("3️⃣ Pallets a Procesar")
        
        if st.session_state.pallets_list:
            # Resumen
            total_kg = sum(p['kg'] for p in st.session_state.pallets_list if p['kg'] > 0)
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Pallets", len(st.session_state.pallets_list))
            col2.metric("Total Kg", f"{total_kg:,.2f}")
            col3.metric("Promedio Kg/Pallet", f"{total_kg/len(st.session_state.pallets_list):,.2f}" if len(st.session_state.pallets_list) > 0 else "0")
            
            st.markdown("---")
            
            # Mostrar pallets
            for idx, pallet in enumerate(st.session_state.pallets_list):
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    kg_display = f"{pallet['kg']:,.2f} Kg" if pallet['kg'] > 0 else "⚠️ Sin stock"
                    ubicacion_display = f"📍 {pallet['ubicacion']}" if pallet['ubicacion'] != 'N/A' else ""
                    
                    st.markdown(f"""
                    <div class="pallet-card">
                        <strong>{pallet['codigo']}</strong> - {kg_display}<br>
                        <small>{ubicacion_display}</small>
                        {f'<br><small style="color: orange;">⚠️ {pallet["advertencia"]}</small>' if pallet.get('advertencia') else ''}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if st.button("🗑️", key=f"delete_{idx}", help="Eliminar pallet"):
                        st.session_state.pallets_list.pop(idx)
                        st.rerun()
                
                # Si no tiene kg, permitir ingresar manualmente
                if pallet['kg'] <= 0:
                    kg_manual = st.number_input(
                        f"Kg para {pallet['codigo']}",
                        min_value=0.0,
                        step=0.1,
                        key=f"kg_{idx}",
                        help="Este pallet no tiene stock. Ingresa los Kg manualmente."
                    )
                    if kg_manual > 0:
                        st.session_state.pallets_list[idx]['kg'] = kg_manual
            
            st.divider()
            
            # Botón para crear orden
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Limpiar Todo", use_container_width=True):
                    st.session_state.pallets_list = []
                    st.rerun()
            
            
            # ✅ Rate limiting: Prevenir doble-click
            if 'creando_orden' not in st.session_state:
                st.session_state.creando_orden = False
            
            with col2:
                # Deshabilitar botón si está procesando
                if st.button(
                    "✅ Crear Orden de Fabricación", 
                    use_container_width=True, 
                    type="primary",
                    disabled=st.session_state.creando_orden
                ):
                    # Validar que todos tengan kg
                    pallets_sin_kg = [p for p in st.session_state.pallets_list if p['kg'] <= 0]
                    
                    if pallets_sin_kg:
                        st.error(f"❌ {len(pallets_sin_kg)} pallets sin cantidad. Ingresa los Kg manualmente.")
                    else:
                        # ✅ Marcar como "creando" para deshabilitar botón
                        st.session_state.creando_orden = True
                        
                        # Crear orden
                        with st.spinner("Creando orden de fabricación..."):
                            try:
                                pallets_payload = [
                                    {'codigo': p['codigo'], 'kg': p['kg']}
                                    for p in st.session_state.pallets_list
                                ]
                                
                                response = requests.post(
                                    f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/crear",
                                    headers={"Authorization": f"Bearer {session_info.get('token')}"},
                                    json={
                                        "tunel": selected_tunel,
                                        "pallets": pallets_payload,
                                        "buscar_ubicacion_auto": buscar_ubicacion_auto
                                    },
                                    timeout=30  # ✅ Timeout de 30 segundos
                                )
                                
                                if response.status_code == 200:
                                    result = response.json()
                                    st.success(f"✅ {result.get('mensaje', 'Orden creada exitosamente')}")
                                    st.info(f"📋 Orden: **{result.get('mo_name')}**")
                                    st.info(f"📊 Total: **{result.get('total_kg'):,.2f} Kg** en **{result.get('pallets_count')}** pallets")
                                    
                                    # Mostrar componentes y subproductos creados
                                    if result.get('componentes_count') or result.get('subproductos_count'):
                                        col_a, col_b = st.columns(2)
                                        if result.get('componentes_count'):
                                            col_a.metric("🔵 Componentes", result['componentes_count'])
                                        if result.get('subproductos_count'):
                                            col_b.metric("🟢 Subproductos", result['subproductos_count'])
                                    
                                    # Mostrar advertencias si existen
                                    if result.get('advertencias'):
                                        for adv in result['advertencias']:
                                            st.warning(f"⚠️ {adv}")
                                    
                                    # Limpiar lista y resetear flag
                                    st.session_state.pallets_list = []
                                    st.session_state.creando_orden = False
                                    st.balloons()
                                    
                                    # Refrescar después de 2 segundos
                                    import time
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    error_detail = response.json().get('detail', 'Error desconocido')
                                    st.error(f"❌ Error al crear orden: {error_detail}")
                                    st.session_state.creando_orden = False  # Reset en caso de error
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                                st.session_state.creando_orden = False  # Reset en caso de excepción
        else:
            st.info("👆 Agrega pallets para comenzar")


# ============ TAB 2: Monitor de Órdenes ============

with tab2:
    st.header("Monitor de Órdenes")
    
    # Filtros
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        filtro_tunel = st.selectbox(
            "Túnel",
            options=['Todos'] + [t['codigo'] for t in tuneles],
            index=0
        )
    
    with col2:
        filtro_estado = st.selectbox(
            "Estado",
            options=['Todos', 'draft', 'confirmed', 'progress', 'done', 'cancel'],
            format_func=lambda x: {
                'Todos': 'Todos',
                'draft': '📝 Borrador',
                'confirmed': '✅ Confirmado',
                'progress': '🔄 En Progreso',
                'done': '✔️ Hecho',
                'cancel': '❌ Cancelado'
            }.get(x, x),
            index=0
        )
    
    with col3:
        if st.button("🔄 Actualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Obtener órdenes
    @st.cache_data(ttl=300)  # ✅ Optimizado: 5 minutos (antes 1 min)
    def get_ordenes(tunel=None, estado=None):
        try:
            params = {"limit": 20}
            if tunel and tunel != 'Todos':
                params['tunel'] = tunel
            if estado and estado != 'Todos':
                params['estado'] = estado
            
            response = requests.get(
                f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/ordenes",
                headers={"Authorization": f"Bearer {session_info.get('token')}"},
                params=params
            )
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []
    
    ordenes = get_ordenes(
        tunel=filtro_tunel if filtro_tunel != 'Todos' else None,
        estado=filtro_estado if filtro_estado != 'Todos' else None
    )
    
    if not ordenes:
        st.info("📭 No hay órdenes para mostrar")
    else:
        st.markdown(f"**{len(ordenes)} órdenes encontradas**")
        
        # Mapeo de estados a badges
        estado_badge = {
            'draft': 'badge-draft',
            'confirmed': 'badge-progress',
            'progress': 'badge-progress',
            'done': 'badge-done',
            'cancel': 'badge-cancel'
        }
        
        estado_emoji = {
            'draft': '📝',
            'confirmed': '✅',
            'progress': '🔄',
            'done': '✔️',
            'cancel': '❌'
        }
        
        # Mostrar órdenes
        for orden in ordenes:
            estado_class = estado_badge.get(orden['estado'], 'badge-draft')
            emoji = estado_emoji.get(orden['estado'], '📋')
            
            st.markdown(f"""
            <div class="orden-card">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h4 style="margin: 0;">{emoji} {orden['nombre']}</h4>
                        <p style="margin: 4px 0; color: #666;">
                            <strong>{orden.get('tunel', 'N/A')}</strong> | {orden['producto']}
                        </p>
                    </div>
                    <span class="badge {estado_class}">{orden['estado'].upper()}</span>
                </div>
                <div style="margin-top: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                    <div>
                        <small style="color: #666;">Total Kg</small><br>
                        <strong style="font-size: 18px;">{orden['kg_total']:,.2f}</strong>
                    </div>
                    <div>
                        <small style="color: #666;">Fecha Creación</small><br>
                        <strong>{orden.get('fecha_creacion', 'N/A')[:10] if orden.get('fecha_creacion') else 'N/A'}</strong>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

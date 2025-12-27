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
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.auth import proteger_pagina, obtener_info_sesion, get_credenciales

# API URL
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# Requerir autenticación
proteger_pagina()

# Obtener info de sesión y credenciales
session_info = obtener_info_sesion()
username, password = get_credenciales()

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
    
    /* Cards de pallets (dark mode compatible) */
    .pallet-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border-left: 4px solid #22c55e;
        padding: 16px;
        margin: 8px 0;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    
    .pallet-card strong {
        color: #ffffff;
        font-size: 1.05em;
    }
    
    .pallet-card small {
        color: #94a3b8;
    }
    
    /* Cards de órdenes (dark mode compatible) */
    .orden-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border: 1px solid #475569;
        padding: 16px;
        margin: 12px 0;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    
    .orden-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    
    /* Estados */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .badge-draft { background: #78350f; color: #fde68a; }
    .badge-progress { background: #1e3a8a; color: #93c5fd; }
    .badge-done { background: #14532d; color: #86efac; }
    .badge-cancel { background: #7f1d1d; color: #fca5a5; }
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
    def get_tuneles(_username, _password):
        try:
            response = requests.get(
                f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/procesos",
                params={"username": _username, "password": _password},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []
    
    tuneles = get_tuneles(username, password)
    
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
                        # Verificar duplicados primero
                        codigos_existentes = {p['codigo'] for p in st.session_state.pallets_list}
                        if pallet_codigo.strip() in codigos_existentes:
                            st.warning(f"⚠️ {pallet_codigo} ya está en la lista")
                        else:
                            # Validar pallet
                            with st.spinner("Validando pallet..."):
                                try:
                                    response = requests.post(
                                        f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/validar-pallets",
                                        params={"username": username, "password": password},
                                        json={
                                            "pallets": [pallet_codigo],
                                            "buscar_ubicacion": buscar_ubicacion_auto
                                        },
                                        timeout=10
                                    )
                                    if response.status_code == 200:
                                        validacion = response.json()[0]
                                        
                                        if validacion.get('existe') and validacion.get('kg', 0) > 0:
                                            # Agregar a la lista
                                            st.session_state.pallets_list.append({
                                                'codigo': validacion['codigo'],
                                                'kg': validacion.get('kg', 0.0),
                                                'ubicacion': validacion.get('ubicacion_nombre', 'N/A'),
                                                'advertencia': validacion.get('advertencia'),
                                                'producto_id': validacion.get('producto_id'),
                                                'producto_nombre': validacion.get('producto_nombre', 'N/A'),
                                                'manual': False
                                            })
                                            st.success(f"✅ {pallet_codigo} agregado!")
                                            st.rerun()
                                        else:
                                            # Verificar si hay info de recepción
                                            reception_info = validacion.get('reception_info')
                                            if reception_info:
                                                # SI ES PALLET EN RECEPCIÓN PENDIENTE:
                                                st.session_state.pallets_list.append({
                                                    'codigo': validacion['codigo'],
                                                    'kg': validacion.get('kg', 0.0),
                                                    'ubicacion': f"RECEPCIÓN PENDIENTE ({reception_info['state']})",
                                                    'advertencia': f"Pallet en recepción {reception_info['picking_name']}. Validar en Odoo.",
                                                    'producto_id': validacion.get('product_id'),
                                                    'producto_nombre': validacion.get('producto_nombre', 'N/A'),
                                                    'manual': False,
                                                    'pendiente_recepcion': True,
                                                    'odoo_url': reception_info['odoo_url']
                                                })
                                                
                                                st.warning(f"⚠️ Pallet {pallet_codigo} agregado desde Recepción Pendiente.")
                                                st.rerun()
                                                
                                            else:
                                                # NO se encontró en stock NI en recepciones pendientes
                                                st.error(f"❌ Pallet {pallet_codigo} NO existe en Odoo.")
                                                st.info("Verifica que el código sea correcto o que el pallet esté registrado en alguna recepción.")
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
                    codigos_raw = [c.strip() for c in pallets_textarea.split('\n') if c.strip()]
                    
                    # Filtrar duplicados ya existentes en la lista
                    codigos_existentes = {p['codigo'] for p in st.session_state.pallets_list}
                    codigos = [c for c in codigos_raw if c not in codigos_existentes]
                    duplicados_ignorados = len(codigos_raw) - len(codigos)
                    
                    if not codigos:
                        st.warning("⚠️ Todos los pallets ya están en la lista")
                    else:
                        with st.spinner(f"Validando {len(codigos)} pallets..."):
                            try:
                                response = requests.post(
                                    f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/validar-pallets",
                                    params={"username": username, "password": password},
                                    json={
                                        "pallets": codigos,
                                        "buscar_ubicacion": buscar_ubicacion_auto
                                    },
                                    timeout=15
                                )
                                if response.status_code == 200:
                                    validaciones = response.json()
                                    
                                    agregados = 0
                                    en_recepcion = 0
                                    no_encontrados = []
                                    
                                    for val in validaciones:
                                        # Caso 1: Existe en stock
                                        if val.get('existe') and val.get('kg', 0) > 0:
                                            st.session_state.pallets_list.append({
                                                'codigo': val['codigo'],
                                                'kg': val.get('kg', 0.0),
                                                'ubicacion': val.get('ubicacion_nombre', 'N/A'),
                                                'advertencia': val.get('advertencia'),
                                                'producto_id': val.get('producto_id'),
                                                'producto_nombre': val.get('producto_nombre', 'N/A'),
                                                'manual': False
                                            })
                                            agregados += 1
                                        # Caso 2: Pallet en recepción pendiente
                                        elif val.get('reception_info'):
                                            reception_info = val['reception_info']
                                            st.session_state.pallets_list.append({
                                                'codigo': val['codigo'],
                                                'kg': val.get('kg', 0.0),
                                                'ubicacion': f"RECEPCIÓN PENDIENTE ({reception_info['state']})",
                                                'advertencia': f"Pallet en recepción {reception_info['picking_name']}",
                                                'producto_id': val.get('product_id'),
                                                'producto_nombre': val.get('producto_nombre', 'N/A'),
                                                'manual': False,
                                                'pendiente_recepcion': True,
                                                'odoo_url': reception_info['odoo_url']
                                            })
                                            en_recepcion += 1
                                        else:
                                            no_encontrados.append(val['codigo'])
                                    
                                    # Mostrar resumen
                                    msgs = []
                                    if agregados > 0:
                                        msgs.append(f"✅ {agregados} en stock")
                                    if en_recepcion > 0:
                                        msgs.append(f"⚠️ {en_recepcion} en recepción pendiente")
                                    if duplicados_ignorados > 0:
                                        msgs.append(f"🔄 {duplicados_ignorados} duplicados ignorados")
                                    if no_encontrados:
                                        msgs.append(f"❌ {len(no_encontrados)} no encontrados")
                                    
                                    if agregados + en_recepcion > 0:
                                        st.success(" | ".join(msgs))
                                        st.rerun()
                                    else:
                                        st.error("❌ Ningún pallet fue encontrado: " + ", ".join(no_encontrados))
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
                
                # Si tiene link a Odoo (pallet pendiente), mostrar botón
                if pallet.get('odoo_url'):
                    st.markdown(f"[🔗 Abrir Recepción en Odoo]({pallet['odoo_url']})")
            
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
                                    params={"username": username, "password": password},
                                    json={
                                        "tunel": selected_tunel,
                                        "pallets": pallets_payload,
                                        "buscar_ubicacion_auto": buscar_ubicacion_auto
                                    },
                                    timeout=60  # ✅ Timeout de 60 segundos (crear MO puede tardar)
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
        # Nuevo filtro: incluyedo opción de ver solo problemas
        filtro_estado = st.selectbox(
            "Estado / Filtro",
            options=['Todos', 'pendientes_stock', 'draft', 'confirmed', 'progress', 'done', 'cancel'],
            format_func=lambda x: {
                'Todos': 'Todos',
                'pendientes_stock': '🟠 Con Pendientes de Stock',
                'draft': '📝 Borrador',
                'confirmed': '✅ Confirmado',
                'progress': '🔄 En Progreso',
                'done': '✔️ Hecho',
                'cancel': '❌ Cancelado'
            }.get(x, x),
            index=1 # Por defecto mostramos las pendientes/problemáticas primero para agilizar
        )
    
    with col3:
        if st.button("🔄 Actualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Obtener órdenes
    @st.cache_data(ttl=60) 
    def get_ordenes(_username, _password, tunel=None, estado=None):
        try:
            params = {
                "username": _username,
                "password": _password,
                "limit": 50 # Aumentar límite para ver más
            }
            if tunel and tunel != 'Todos':
                params['tunel'] = tunel
            
            # Si el filtro es un estado real de Odoo, lo mandamos
            # Si es 'pendientes_stock', filtramos en cliente sobre las drafts/confirmed
            if estado and estado not in ['Todos', 'pendientes_stock']:
                params['estado'] = estado
            
            response = requests.get(
                f"{API_URL}/api/v1/automatizaciones/tuneles-estaticos/ordenes",
                params=params
            )
            if response.status_code == 200:
                data = response.json()
                # Filtrado cliente para 'pendientes_stock'
                if estado == 'pendientes_stock':
                    return [o for o in data if o.get('tiene_pendientes')]
                return data
            return []
        except:
            return []
    
    ordenes = get_ordenes(
        username, 
        password,
        tunel=filtro_tunel if filtro_tunel != 'Todos' else None,
        estado=filtro_estado
    )
    
    if not ordenes:
        st.info("📭 No hay órdenes con este criterio")
    else:
        st.markdown(f"**{len(ordenes)} órdenes encontradas**")
        
        # Mostrar órdenes con diseño expandido
        for orden in ordenes:
            # Configuración de colores por estado (visibles en dark theme)
            estado = orden.get('estado', 'draft')
            tiene_pendientes = orden.get('tiene_pendientes', False)
            
            if tiene_pendientes:
                # Override visual para destacar problemas
                color_borde = '#f59e0b' # Naranja warning
                color_badge_bg = '#78350f'
                color_badge_text = '#fcd34d'
                estado_label = '🟠 PENDIENTE STOCK'
            elif estado == 'draft':
                color_borde = '#fbbf24'
                color_badge_bg = '#78350f'
                color_badge_text = '#fde68a'
                estado_label = '📝 BORRADOR'
            elif estado == 'confirmed':
                color_borde = '#3b82f6'
                color_badge_bg = '#1e3a8a'
                color_badge_text = '#93c5fd'
                estado_label = '✅ CONFIRMADO'
            elif estado == 'progress':
                color_borde = '#f97316'
                color_badge_bg = '#7c2d12'
                color_badge_text = '#fed7aa'
                estado_label = '🔄 EN PROCESO'
            elif estado == 'done':
                color_borde = '#22c55e'
                color_badge_bg = '#14532d'
                color_badge_text = '#86efac'
                estado_label = '✔️ TERMINADO'
            else:  # cancel
                color_borde = '#ef4444'
                color_badge_bg = '#7f1d1d'
                color_badge_text = '#fca5a5'
                estado_label = '❌ CANCELADO'
            
            # Formatear fecha
            fecha_str = orden.get('fecha_creacion', 'N/A')
            if fecha_str != 'N/A':
                try:
                    from datetime import datetime
                    fecha_dt = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                    fecha_str = fecha_dt.strftime('%d/%m/%Y %H:%M')
                except:
                    fecha_str = fecha_str[:16] if len(fecha_str) > 16 else fecha_str
            
            # Calcular info adicional (estimaciones si no vienen del backend)
            total_kg = orden.get('total_kg', 0)
            pallets = orden.get('pallets_count', int(total_kg / 400) if total_kg > 0 else 0)
            componentes = orden.get('componentes_count', pallets)
            subproductos = orden.get('subproductos_count', pallets)
            
            # Calcular electricidad estimada (0.15 USD/kg aprox)
            electricidad = orden.get('costo_electricidad', total_kg * 0.15)
            
            # Renderizar HTML - SIN INDENTACIÓN para evitar que st.markdown lo trate como código
            html_content = f'''<div style="background: linear-gradient(135deg, #1a1a2e 0%, #252538 100%); border-left: 5px solid {color_borde}; border-radius: 14px; padding: 24px; margin-bottom: 20px; box-shadow: 0 6px 16px rgba(0,0,0,0.6);">
<div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 20px;">
<div style="flex: 1;">
<h3 style="margin: 0 0 8px 0; font-size: 1.2em; color: #ffffff; font-weight: 700;">{orden.get('mo_name', orden.get('nombre', 'N/A'))}</h3>
<p style="margin: 0; color: #a0a0b0; font-size: 0.95em;">🏭 <strong style="color: #e0e0e0;">{orden.get('tunel', 'N/A')}</strong> | 📦 {orden.get('producto_nombre', orden.get('producto', 'N/A'))}</p>
</div>
<span style="background: {color_badge_bg}; color: {color_badge_text}; padding: 8px 16px; border-radius: 24px; font-size: 0.7em; font-weight: 800; white-space: nowrap; margin-left: 16px; letter-spacing: 1px;">{estado_label}</span>
</div>
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
<div style="background: rgba(59,130,246,0.1); border-left: 3px solid #3b82f6; border-radius: 10px; padding: 16px;">
<div style="color: #93c5fd; font-size: 0.7em; font-weight: 700; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px;">🔵 Componentes (Entrada)</div>
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
<div><div style="color: #888; font-size: 0.7em; margin-bottom: 4px;">Total Kg</div><div style="color: #ffffff; font-size: 1.3em; font-weight: 700;">{orden.get('kg_total', 0):,.1f}</div></div>
<div><div style="color: #888; font-size: 0.7em; margin-bottom: 4px;">Registros</div><div style="color: #ffffff; font-size: 1.3em; font-weight: 700;">{componentes}</div></div>
</div>
</div>
<div style="background: rgba(34,197,94,0.1); border-left: 3px solid #22c55e; border-radius: 10px; padding: 16px;">
<div style="color: #86efac; font-size: 0.7em; font-weight: 700; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px;">🟢 Subproductos (Salida)</div>
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
<div><div style="color: #888; font-size: 0.7em; margin-bottom: 4px;">Total Kg</div><div style="color: #ffffff; font-size: 1.3em; font-weight: 700;">{orden.get('kg_total', 0):,.1f}</div></div>
<div><div style="color: #888; font-size: 0.7em; margin-bottom: 4px;">Registros</div><div style="color: #ffffff; font-size: 1.3em; font-weight: 700;">{subproductos}</div></div>
</div>
</div>
</div>
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.1);">
<div><div style="color: #888; font-size: 0.7em; margin-bottom: 4px; text-transform: uppercase;">📦 Pallets</div><div style="color: #ffffff; font-size: 1.1em; font-weight: 600;">{pallets} unidades</div></div>
<div><div style="color: #888; font-size: 0.7em; margin-bottom: 4px; text-transform: uppercase;">📅 Creación</div><div style="color: #ffffff; font-size: 1.1em; font-weight: 600;">{fecha_str}</div></div>
<div style="background: rgba(251,191,36,0.15); border-left: 3px solid #fbbf24; border-radius: 8px; padding: 12px;">
<div style="color: #fde68a; font-size: 0.7em; margin-bottom: 4px; text-transform: uppercase; font-weight: 700;">⚡ Electricidad</div>
<div style="color: #ffffff; font-size: 1.3em; font-weight: 700;">${electricidad:,.2f}</div>
<div style="color: #a0a0b0; font-size: 0.65em; margin-top: 2px;">~$0.15/kg</div>
</div>
</div>
</div>'''
            st.markdown(html_content, unsafe_allow_html=True)



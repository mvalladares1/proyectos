"""
Tab: Monitor de Órdenes
Visualización y gestión de órdenes de túneles estáticos.
"""
import streamlit as st
import pandas as pd
import requests
import os

from .shared import (
    API_URL, get_tuneles, get_ordenes, get_pendientes_orden,
    agregar_disponibles, completar_pendientes, reset_estado_pendientes,
    format_fecha, get_estado_visual
)


def render(username: str, password: str, tuneles: list):
    """Renderiza el contenido del tab Monitor de Órdenes."""
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
            "Estado / Filtro",
            options=['Todos', 'stock_pendiente', 'pendientes', 'done', 'cancel'],
            format_func=lambda x: {
                'Todos': '📋 Todas (sin canceladas)',
                'stock_pendiente': '🟠 Con Stock Pendiente',
                'pendientes': '🟡 Pendientes (Odoo)',
                'done': '✅ Finalizadas',
                'cancel': '❌ Canceladas'
            }.get(x, x),
            index=0
        )
    
    with col3:
        if st.button("🔄 Actualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Obtener órdenes
    ordenes = get_ordenes(
        username, password,
        tunel=filtro_tunel if filtro_tunel != 'Todos' else None,
        estado=filtro_estado
    )
    
    st.caption(f"🔍 Filtro: {filtro_estado} | Órdenes: {len(ordenes)}")
    
    if not ordenes:
        st.info("📭 No hay órdenes con este criterio")
        return
    
    st.markdown(f"**{len(ordenes)} órdenes encontradas**")
    
    for orden in ordenes:
        _render_orden_card(orden, username, password)


def _render_orden_card(orden, username, password):
    """Renderiza la tarjeta de una orden."""
    estado = orden.get('estado', 'draft')
    tiene_pendientes = orden.get('tiene_pendientes', False)
    
    visual = get_estado_visual(estado, tiene_pendientes)
    color_borde = visual['borde']
    color_badge_bg = visual['badge_bg']
    color_badge_text = visual['badge_text']
    estado_label = visual['label']
    
    fecha_str = format_fecha(orden.get('fecha_creacion', 'N/A'))
    
    # Construir link clickeable a Odoo
    mo_id = orden.get('id')
    mo_name = orden.get('mo_name', orden.get('nombre', 'N/A'))
    odoo_url = f"https://riofuturo.server98c6e.oerpondemand.net/web#id={mo_id}&menu_id=390&cids=1&action=604&model=mrp.production&view_type=form"
    nombre_clickeable = f'<a href="{odoo_url}" target="_blank" style="color: #ffffff; text-decoration: none; border-bottom: 2px solid #3b82f6; padding-bottom: 2px; transition: all 0.2s;">{mo_name}</a>'
    
    total_kg = orden.get('kg_total', 0)
    pallets = orden.get('pallets_count', 0)
    componentes = orden.get('componentes_count', 0)
    subproductos = orden.get('subproductos_count', 0)
    electricidad = orden.get('electricidad_costo', 0)
    
    html_content = f'''<div style="background: linear-gradient(135deg, #1a1a2e 0%, #252538 100%); border-left: 5px solid {color_borde}; border-radius: 14px; padding: 24px; margin-bottom: 20px; box-shadow: 0 6px 16px rgba(0,0,0,0.6);">
<div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 20px;">
<div style="flex: 1;">
<h3 style="margin: 0 0 8px 0; font-size: 1.2em; color: #ffffff; font-weight: 700;">{nombre_clickeable}</h3>
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
    
    with st.container():
        st.markdown(html_content, unsafe_allow_html=True)
        
        if tiene_pendientes:
            _render_pendientes(orden, username, password)


def _render_pendientes(orden, username, password):
    """Renderiza la sección de pendientes de una orden."""
    orden_id = orden.get('id')
    
    col_act1, col_act2 = st.columns([2, 1])
    with col_act1:
        st.warning(f"⚠️ Esta orden tiene pallets esperando recepción")
    
    with col_act2:
        # Botón rápido para agregar disponibles (se habilitará si hay alguno)
        pass

    with st.expander(f"📋 Ver detalle de pendientes - {orden.get('nombre', 'N/A')}", expanded=False):
        # Botón de debug para resetear estado (solo visible en desarrollo)
        ENV = os.getenv("ENV", "prod")
        if ENV == "development":
            col_reset, col_info = st.columns([1, 3])
            with col_reset:
                if st.button("🔄 RESET", key=f"reset_{orden_id}", help="Resetea los timestamps de agregado para re-validar", type="secondary"):
                    with st.spinner("Reseteando estado..."):
                        resp = reset_estado_pendientes(username, password, orden_id)
                        if resp and resp.status_code == 200:
                            result = resp.json()
                            st.success(f"✅ {result.get('mensaje')}")
                            st.rerun()
                        elif resp:
                            try:
                                error_data = resp.json()
                                st.error(f"❌ Reset falló: {error_data.get('detail', resp.text)}")
                            except:
                                st.error(f"❌ Reset falló: HTTP {resp.status_code}")
                        else:
                            st.error("❌ No se pudo conectar al servidor para reset")
            with col_info:
                st.caption("🐛 DEBUG: Limpia los estados 'Ya agregado' para forzar re-validación")
            
            st.divider()
        
        # Siempre cargar datos frescos al abrir el expander
        with st.spinner("Cargando datos..."):
            detalle = get_pendientes_orden(username, password, orden_id)
        
        if detalle and detalle.get('success'):
            resumen = detalle.get('resumen', {})
            
            # Mostrar notificación si hay cambios
            if detalle.get('hay_cambios_nuevos'):
                nuevos = detalle.get('nuevos_disponibles', 0)
                st.success(f"🎉 {nuevos} pallet(s) ahora disponible(s)! Haz click en 'Agregar Disponibles' para incorporarlos a la orden.")
            
            # Mostrar resumen con progreso
            total = resumen.get('total', 0)
            agregados = resumen.get('agregados', 0)
            disponibles = resumen.get('disponibles', 0)
            pendientes = resumen.get('pendientes', 0)
            
            if total > 0:
                progreso = (agregados / total * 100)
                st.progress(progreso / 100)
                st.markdown(f"""
                **Progreso:** {agregados}/{total} agregados ({progreso:.0f}%)  
                ✅ {agregados} agregados | 🟢 {disponibles} disponibles | 🟠 {pendientes} pendientes
                """)
            else:
                st.markdown(f"""
                **Resumen:** ✅ {agregados} agregados | 
                🟢 {disponibles} disponibles | 
                🟠 {pendientes} pendientes
                """)
            
            pallets = detalle.get('pallets', [])
            if pallets:
                st.markdown("##### 📦 Pallets Pendientes")
                for p in pallets:
                    col_info, col_link = st.columns([4, 1])
                    with col_info:
                        estado_emoji = '🟢' if p['estado_label'] == 'Disponible' else '🟠'
                        cambio = '🆕' if p.get('nuevo_disponible') else ('📊' if p.get('cambio_detectado') else '')
                        st.markdown(f"{estado_emoji} **{p['codigo']}** - {p['kg']:,.2f} Kg | {p['estado_label']} {cambio}")
                    
                    with col_link:
                        if p.get('picking_id'):
                            picking_url = f"https://riofuturo.server98c6e.oerpondemand.net/web#id={p['picking_id']}&menu_id=243&cids=1&action=396&model=stock.picking&view_type=form"
                            st.markdown(f"[🔗 Recepción]({picking_url})", unsafe_allow_html=True)
                        else:
                            st.caption(p.get('picking_name', 'N/A'))
            
            electricidad_total = detalle.get('electricidad_total', 0)
            if electricidad_total > 0:
                st.markdown(f"##### ⚡ Electricidad: **${electricidad_total:,.2f}**")
            
            componentes = detalle.get('componentes', [])
            if componentes:
                st.markdown("##### 🔵 Componentes (Entrada)")
                comp_no_elec = [c for c in componentes if not c.get('es_electricidad')]
                comp_elec = [c for c in componentes if c.get('es_electricidad')]
                
                if comp_no_elec:
                    df_comp = pd.DataFrame([
                        {
                            'Producto': c['producto'][:40],
                            'Lote': c['lote'],
                            'Pallet': c['pallet'],
                            'Kg': f"{c['kg']:,.2f}"
                        }
                        for c in comp_no_elec
                    ])
                    st.dataframe(df_comp, use_container_width=True, hide_index=True)
                
                if comp_elec:
                    st.caption(f"⚡ Electricidad: {len(comp_elec)} registro(s)")
            
            subproductos = detalle.get('subproductos', [])
            if subproductos:
                st.markdown("##### 🟢 Subproductos (Salida)")
                df_sub = pd.DataFrame([
                    {
                        'Producto': s['producto'][:40],
                        'Lote': s['lote'],
                        'Pallet': s['pallet'],
                        'Kg': f"{s['kg']:,.2f}"
                    }
                    for s in subproductos
                ])
                st.dataframe(df_sub, use_container_width=True, hide_index=True)
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                if detalle.get('hay_disponibles_sin_agregar') or disponibles > 0:
                    if st.button("✅ Agregar Disponibles", key=f"agregar_{orden_id}", type="primary"):
                        resp = agregar_disponibles(username, password, orden_id)
                        if resp and resp.status_code == 200:
                            result = resp.json()
                            st.success(f"✅ {result.get('mensaje')}")
                            st.cache_data.clear()
                            st.rerun()
                        elif resp:
                            error_data = resp.json() if resp.headers.get('content-type') == 'application/json' else {}
                            st.error(f"❌ Error: {error_data.get('detail', resp.text)}")
            
            with col_b:
                # Validación mejorada para completar pendientes
                pallets_sin_agregar = [p for p in pallets if p['estado'] in ['pendiente', 'disponible']]
                
                if pallets_sin_agregar:
                    st.warning(f"⚠️ Aún quedan {len(pallets_sin_agregar)} pallet(s) sin agregar")
                elif detalle.get('todos_listos') or (pendientes == 0 and disponibles == 0):
                    if st.button("☑️ Completar Pendientes", key=f"completar_{orden_id}", type="secondary"):
                        resp = completar_pendientes(username, password, orden_id)
                        if resp and resp.status_code == 200:
                            result = resp.json()
                            st.success(f"✅ {result.get('mensaje', 'Pendientes completados!')}")
                            st.cache_data.clear()
                            st.rerun()
                        elif resp:
                            try:
                                error_data = resp.json()
                                error_msg = error_data.get('detail', error_data.get('error', resp.text))
                            except:
                                error_msg = resp.text
                            st.error(f"❌ {error_msg}")
                        else:
                            st.error("❌ No se pudo conectar con el servidor")
            
            # Links a Odoo
            pendientes_lista = [p for p in pallets if p['estado'] == 'pendiente']
            if pendientes_lista:
                picking_ids = list(set(p.get('picking_id') for p in pendientes_lista if p.get('picking_id')))
                if picking_ids:
                    st.markdown("**📋 Recepciones pendientes de aprobar:**")
                    for pid in picking_ids:
                        picking_name = next((p['picking_name'] for p in pendientes_lista if p.get('picking_id') == pid), f"Picking {pid}")
                        odoo_url = f"https://riofuturo.server98c6e.oerpondemand.net/web#id={pid}&model=stock.picking&view_type=form"
                        st.markdown(f"- **{picking_name}**")
                        st.link_button(f"🔗 Ir a {picking_name}", odoo_url, type="secondary")
        else:
            # Error al cargar datos
            error_msg = detalle.get('error', 'Error desconocido') if detalle else 'No se recibió respuesta del servidor'
            st.error(f"❌ {error_msg}")
            if detalle:
                st.json(detalle)  # Mostrar respuesta completa para debug

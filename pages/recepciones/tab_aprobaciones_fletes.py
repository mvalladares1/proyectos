"""
Tab de Aprobaciones de Fletes - Exclusivo para Maximo Sepúlveda y Felipe Horst
Muestra únicamente OCs de FLETES/TRANSPORTES pendientes de aprobación
Conecta directamente con Odoo sin pasar por el backend
"""

import streamlit as st
import pandas as pd
import xmlrpc.client
from datetime import datetime
import time


URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'

USUARIOS = {
    'Maximo Sepúlveda': 241,
    'Felipe Horst': 17,
    'Francisco Luttecke': 258
}


def get_odoo_connection(username, password):
    """Conexión a Odoo"""
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, username, password, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        return models, uid
    except Exception as e:
        st.error(f"Error de conexión a Odoo: {e}")
        return None, None


@st.cache_data(ttl=60)
def obtener_actividades_usuario(_models, _uid, username, password, user_id):
    """Obtener todas las actividades pendientes de un usuario"""
    try:
        actividades = _models.execute_kw(
            DB, _uid, password,
            'mail.activity', 'search_read',
            [[
                ('user_id', '=', user_id),
                ('res_model', '=', 'purchase.order'),
                ('activity_type_id.name', 'in', ['Grant Approval', 'Approval'])
            ]],
            {'fields': ['id', 'res_id', 'res_name', 'activity_type_id', 'date_deadline', 'summary', 'state'], 'limit': 300}
        )
        return actividades
    except Exception as e:
        st.error(f"Error al obtener actividades: {e}")
        return []


@st.cache_data(ttl=60)
def obtener_detalles_oc_fletes(_models, _uid, username, password, oc_ids):
    """Obtener detalles de OCs - SOLO FLETES"""
    if not oc_ids:
        return []
    
    try:
        ocs = _models.execute_kw(
            DB, _uid, password,
            'purchase.order', 'search_read',
            [[('id', 'in', oc_ids)]],
            {'fields': ['id', 'name', 'state', 'partner_id', 'amount_total', 
                       'x_studio_selection_field_yUNPd', 'x_studio_categora_de_producto', 'create_date', 'user_id']}
        )
        
        # Filtrar solo fletes
        ocs_fletes = []
        for oc in ocs:
            lineas = _models.execute_kw(
                DB, _uid, password,
                'purchase.order.line', 'search_read',
                [[('order_id', '=', oc['id'])]],
                {'fields': ['product_id', 'name'], 'limit': 1}
            )
            
            producto_nombre = ''
            if lineas and lineas[0].get('product_id'):
                producto_nombre = lineas[0]['product_id'][1]
                oc['producto'] = producto_nombre
            elif lineas and lineas[0].get('name'):
                producto_nombre = lineas[0]['name']
                oc['producto'] = producto_nombre
            else:
                oc['producto'] = 'N/A'
            
            # FILTRO: Solo fletes
            es_flete = False
            
            if 'FLETE' in producto_nombre.upper() or 'TRANSPORTE' in producto_nombre.upper():
                es_flete = True
            
            if oc.get('x_studio_categora_de_producto') == 'SERVICIOS':
                area = oc.get('x_studio_selection_field_yUNPd', '')
                if area and isinstance(area, (list, tuple)):
                    area = area[1]
                if 'TRANSPORTES' in str(area).upper():
                    es_flete = True
            
            if es_flete:
                ocs_fletes.append(oc)
        
        return ocs_fletes
    except Exception as e:
        st.error(f"Error al obtener detalles de OCs: {e}")
        return []


def obtener_todas_actividades_oc(models, uid, username, password, oc_id):
    """Obtener todas las actividades de una OC para ver el flujo"""
    try:
        actividades = models.execute_kw(
            DB, uid, password,
            'mail.activity', 'search_read',
            [[
                ('res_model', '=', 'purchase.order'),
                ('res_id', '=', oc_id)
            ]],
            {'fields': ['id', 'user_id', 'activity_type_id', 'state', 'date_deadline', 'create_date']}
        )
        return actividades
    except Exception as e:
        return []


def aprobar_actividad(models, uid, username, password, activity_id):
    """Aprobar una actividad"""
    try:
        models.execute_kw(
            DB, uid, password,
            'mail.activity', 'action_feedback',
            [[activity_id]],
            {'feedback': 'Aprobado desde dashboard'}
        )
        return True, "Aprobación exitosa"
    except Exception as e:
        return False, str(e)


def rechazar_actividad(models, uid, username, password, activity_id, motivo):
    """Rechazar una actividad"""
    try:
        models.execute_kw(
            DB, uid, password,
            'mail.activity', 'action_feedback',
            [[activity_id]],
            {'feedback': f'RECHAZADO: {motivo}'}
        )
        return True, "Rechazo registrado"
    except Exception as e:
        return False, str(e)


def render_tab(username, password):
    """Renderiza el tab de aprobaciones de fletes"""
    
    st.header("🚚 Aprobaciones de Fletes y Transportes")
    st.info("📦 Esta pestaña muestra únicamente Órdenes de Compra de FLETES y TRANSPORTES")
    
    # Selector de usuario
    col1, col2 = st.columns([2, 1])
    with col1:
        usuario_seleccionado = st.selectbox(
            "Seleccionar Usuario:",
            list(USUARIOS.keys()),
            index=0,
            key="usuario_fletes"
        )
    
    with col2:
        if st.button("🔄 Refrescar Datos", key="refresh_fletes"):
            st.cache_data.clear()
            st.rerun()
    
    user_id = USUARIOS[usuario_seleccionado]
    
    # Obtener conexión
    models, uid = get_odoo_connection(username, password)
    if not models or not uid:
        st.error("No se pudo conectar a Odoo")
        return
    
    # Obtener actividades pendientes
    with st.spinner(f"Cargando aprobaciones de {usuario_seleccionado}..."):
        actividades = obtener_actividades_usuario(models, uid, username, password, user_id)
        
        if not actividades:
            st.success(f"✅ No hay aprobaciones de FLETES pendientes para {usuario_seleccionado}")
            st.balloons()
            return
        
        # Obtener detalles de OCs (filtradas por fletes)
        oc_ids = [act['res_id'] for act in actividades]
        ocs_detalles = obtener_detalles_oc_fletes(models, uid, username, password, oc_ids)
        
        if not ocs_detalles:
            st.success(f"✅ No hay aprobaciones de FLETES pendientes para {usuario_seleccionado}")
            st.info("ℹ️ Hay actividades pendientes pero no son de fletes/transportes")
            st.balloons()
            return
    
    # Crear diccionario de OCs por ID
    ocs_dict = {oc['id']: oc for oc in ocs_detalles}
    
    # Combinar datos
    datos_completos = []
    for act in actividades:
        oc = ocs_dict.get(act['res_id'])
        if oc:
            proveedor = oc['partner_id'][1] if oc.get('partner_id') and isinstance(oc['partner_id'], (list, tuple)) else 'N/A'
            area = oc.get('x_studio_selection_field_yUNPd')
            if area and isinstance(area, (list, tuple)):
                area = area[1]
            
            datos_completos.append({
                'actividad_id': act['id'],
                'oc_id': oc['id'],
                'oc_name': oc['name'],
                'proveedor': proveedor,
                'monto': oc.get('amount_total', 0),
                'area': str(area) if area else 'N/A',
                'producto': oc.get('producto', 'N/A'),
                'estado_oc': oc['state'],
                'estado_actividad': act.get('state', 'N/A'),
                'fecha_limite': act.get('date_deadline', 'N/A'),
                'fecha_creacion': oc.get('create_date', 'N/A'),
                'tipo_actividad': act['activity_type_id'][1] if act.get('activity_type_id') else 'N/A'
            })
    
    df = pd.DataFrame(datos_completos)
    
    # Métricas principales
    st.markdown("### 📊 Resumen")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total OCs Fletes", len(df))
    
    with col2:
        total_monto = df['monto'].sum()
        st.metric("Monto Total", f"${total_monto:,.0f}")
    
    with col3:
        vencidas = len(df[df['estado_actividad'] == 'overdue'])
        st.metric("Vencidas", vencidas, delta=f"{vencidas} OCs" if vencidas > 0 else "0 OCs")
    
    with col4:
        hoy = len(df[df['fecha_limite'] == datetime.now().strftime('%Y-%m-%d')])
        st.metric("Vencen Hoy", hoy)
    
    st.markdown("---")
    
    # Filtros
    st.markdown("### 🔍 Filtros")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        estados_disponibles = ['Todos'] + sorted(df['estado_actividad'].unique().tolist())
        filtro_estado = st.selectbox("Estado", estados_disponibles, key="filtro_estado_fletes")
    
    with col2:
        areas_disponibles = ['Todas'] + sorted(df['area'].unique().tolist())
        filtro_area = st.selectbox("Área", areas_disponibles, key="filtro_area_fletes")
    
    with col3:
        min_monto = st.number_input("Monto Mínimo", min_value=0, value=0, step=100000, key="min_monto_fletes")
    
    with col4:
        max_monto = st.number_input("Monto Máximo", min_value=0, value=int(df['monto'].max()), step=100000, key="max_monto_fletes")
    
    # Aplicar filtros
    df_filtrado = df.copy()
    if filtro_estado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['estado_actividad'] == filtro_estado]
    if filtro_area != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['area'] == filtro_area]
    df_filtrado = df_filtrado[(df_filtrado['monto'] >= min_monto) & (df_filtrado['monto'] <= max_monto)]
    
    st.markdown(f"**Mostrando {len(df_filtrado)} de {len(df)} OCs de Fletes**")
    
    st.markdown("---")
    
    # Tabla de OCs con acciones
    st.markdown("### 📋 Órdenes de Compra Pendientes")
    
    # Ordenar por monto descendente
    df_filtrado = df_filtrado.sort_values('monto', ascending=False)
    
    # Mostrar cada OC con opciones de aprobación
    for idx, row in df_filtrado.iterrows():
        with st.expander(f"🚚 **{row['oc_name']}** - {row['proveedor'][:40]} - **${row['monto']:,.0f}**"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                **Detalles de la Orden:**
                - **OC:** {row['oc_name']}
                - **Proveedor:** {row['proveedor']}
                - **Monto:** ${row['monto']:,.0f}
                - **Área:** {row['area']}
                - **Estado OC:** {row['estado_oc']}
                - **Estado Aprobación:** {row['estado_actividad']}
                - **Fecha Límite:** {row['fecha_limite']}
                - **Producto:** {row['producto'][:80]}
                """)
                
                # Mostrar flujo de aprobaciones
                with st.spinner("Cargando flujo de aprobaciones..."):
                    todas_acts = obtener_todas_actividades_oc(models, uid, username, password, row['oc_id'])
                    if todas_acts:
                        st.markdown("**Flujo de Aprobaciones:**")
                        for act in todas_acts:
                            usuario = act['user_id'][1] if act.get('user_id') and isinstance(act['user_id'], (list, tuple)) else 'N/A'
                            tipo = act['activity_type_id'][1] if act.get('activity_type_id') else 'N/A'
                            estado_icon = "✅" if act['state'] == 'done' else "⏳" if act['state'] == 'overdue' else "🔵"
                            st.markdown(f"  {estado_icon} {usuario} - {tipo} - {act['state']}")
            
            with col2:
                st.markdown("**Acciones:**")
                
                # Botón aprobar
                if st.button(f"✅ Aprobar", key=f"aprobar_flete_{row['actividad_id']}"):
                    with st.spinner("Aprobando..."):
                        exito, mensaje = aprobar_actividad(models, uid, username, password, row['actividad_id'])
                        if exito:
                            st.success(f"✅ {row['oc_name']} aprobada correctamente")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {mensaje}")
                
                # Botón rechazar
                with st.form(key=f"form_rechazar_flete_{row['actividad_id']}"):
                    motivo = st.text_area("Motivo del rechazo:", key=f"motivo_flete_{row['actividad_id']}")
                    rechazar = st.form_submit_button("❌ Rechazar")
                    
                    if rechazar:
                        if not motivo:
                            st.warning("⚠️ Debe ingresar un motivo")
                        else:
                            with st.spinner("Rechazando..."):
                                exito, mensaje = rechazar_actividad(models, uid, username, password, row['actividad_id'], motivo)
                                if exito:
                                    st.success(f"❌ {row['oc_name']} rechazada")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error: {mensaje}")
            
            st.markdown("---")
    
    # Sección de aprobación masiva
    st.markdown("---")
    st.markdown("### ⚡ Aprobación Masiva")
    st.warning("⚠️ Esta acción aprobará TODAS las OCs de fletes filtradas actualmente visibles")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"Se aprobarán {len(df_filtrado)} OCs de fletes por un total de ${df_filtrado['monto'].sum():,.0f}")
    
    with col2:
        if st.button("✅ Aprobar Todas", type="primary", key="aprobar_todas_fletes"):
            with st.spinner("Aprobando todas las OCs..."):
                exitosas = 0
                fallidas = 0
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, (index, row) in enumerate(df_filtrado.iterrows()):
                    status_text.text(f"Aprobando {row['oc_name']}...")
                    exito, _ = aprobar_actividad(models, uid, username, password, row['actividad_id'])
                    if exito:
                        exitosas += 1
                    else:
                        fallidas += 1
                    
                    progress_bar.progress((idx + 1) / len(df_filtrado))
                    time.sleep(0.2)
                
                progress_bar.empty()
                status_text.empty()
                
                if fallidas == 0:
                    st.success(f"✅ {exitosas} OCs aprobadas correctamente")
                    st.balloons()
                else:
                    st.warning(f"⚠️ {exitosas} OCs aprobadas, {fallidas} fallidas")
                
                st.cache_data.clear()
                time.sleep(2)
                st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(f"*Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

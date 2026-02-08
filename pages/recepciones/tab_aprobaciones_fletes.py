"""
Tab de Aprobaciones de Fletes - Exclusivo para área TRANSPORTES/SERVICIOS
Muestra únicamente OCs de FLETES/TRANSPORTES pendientes de aprobación
Integrado con sistema de logística para comparación de presupuestos
"""

import streamlit as st
import pandas as pd
import xmlrpc.client
from datetime import datetime
import time
import requests
import json
from typing import Dict, List, Optional


URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
API_LOGISTICA_RUTAS = 'https://riofuturoprocesos.com/api/logistica/rutas'
API_LOGISTICA_COSTES = 'https://riofuturoprocesos.com/api/logistica/db/coste-rutas'
API_MINDICADOR = 'https://mindicador.cl/api'

# Umbral de costo por kg en USD
UMBRAL_COSTO_KG_USD = 0.11  # 11 centavos de dólar

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


@st.cache_data(ttl=300)
def obtener_rutas_logistica():
    """Obtener rutas del sistema de logística"""
    try:
        response = requests.get(API_LOGISTICA_RUTAS, timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.warning(f"No se pudo conectar al sistema de logística: {e}")
        return []


@st.cache_data(ttl=300)
def obtener_costes_rutas():
    """Obtener costes de rutas presupuestadas"""
    try:
        response = requests.get(API_LOGISTICA_COSTES, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Puede ser directamente una lista o un diccionario con 'value'
            if isinstance(data, list):
                return data
            return data.get('value', [])
        return []
    except Exception as e:
        st.warning(f"No se pudo conectar a costes de rutas: {e}")
        return []


@st.cache_data(ttl=3600)  # Cache por 1 hora
def obtener_tipo_cambio_usd():
    """Obtener tipo de cambio USD/CLP desde Banco Central (mindicador.cl)"""
    try:
        response = requests.get(API_MINDICADOR, timeout=10)
        if response.status_code == 200:
            data = response.json()
            dolar = data.get('dolar', {}).get('valor')
            if dolar:
                return float(dolar)
        return None
    except Exception as e:
        st.warning(f"No se pudo obtener tipo de cambio USD: {e}")
        return None


def buscar_ruta_en_logistica(oc_name: str, rutas_logistica: List[Dict]) -> Optional[Dict]:
    """Buscar ruta en sistema de logística por nombre de OC"""
    for ruta in rutas_logistica:
        if ruta.get('purchase_order_name') == oc_name:
            return ruta
    return None


def calcular_comparacion_presupuesto(oc_monto: float, costo_lineas_odoo: float, ruta_info: Optional[Dict], costes_rutas: List[Dict], tipo_cambio_usd: Optional[float] = None) -> Dict:
    """Calcular comparación entre monto OC y presupuesto de logística"""
    resultado = {
        'tiene_ruta': False,
        'costo_calculado': costo_lineas_odoo,  # Costo desde líneas de Odoo (PxQ)
        'costo_calculado_str': f"${costo_lineas_odoo:,.0f}" if costo_lineas_odoo else '⚠️ Sin líneas',
        'costo_presupuestado': None,
        'costo_presupuestado_str': '⚠️ Sin presupuesto',
        'tipo_camion': None,
        'tipo_camion_str': '⚠️ Sin tipo asignado',
        'diferencia': None,
        'diferencia_porcentaje': None,
        'alerta': None,
        'route_name': None,
        'route_name_str': 'Sin ruta',
        'kilometers': None,
        # Nuevos campos para costo por kg
        'cost_per_kg_clp': None,
        'cost_per_kg_usd': None,
        'cost_per_kg_usd_str': '⚠️ Sin dato',
        'alerta_costo_kg': None
    }
    
    if not ruta_info:
        return resultado
    
    resultado['tiene_ruta'] = True
    resultado['kilometers'] = ruta_info.get('total_distance_km', 0)
    resultado['route_name_str'] = 'Procesando...'
    
    # Extraer cost_per_kg de la ruta y calcular en USD
    cost_per_kg_clp = ruta_info.get('cost_per_kg', 0)
    if cost_per_kg_clp and cost_per_kg_clp > 0:
        resultado['cost_per_kg_clp'] = cost_per_kg_clp
        if tipo_cambio_usd and tipo_cambio_usd > 0:
            cost_per_kg_usd = cost_per_kg_clp / tipo_cambio_usd
            resultado['cost_per_kg_usd'] = cost_per_kg_usd
            resultado['cost_per_kg_usd_str'] = f"${cost_per_kg_usd:.3f}"
            
            # Comparar con umbral de $0.11 USD
            if cost_per_kg_usd > UMBRAL_COSTO_KG_USD * 1.2:  # >20% sobre umbral
                resultado['alerta_costo_kg'] = f"🔴 ${cost_per_kg_usd:.3f} (>{UMBRAL_COSTO_KG_USD})"
            elif cost_per_kg_usd > UMBRAL_COSTO_KG_USD:
                resultado['alerta_costo_kg'] = f"🟡 ${cost_per_kg_usd:.3f} (>{UMBRAL_COSTO_KG_USD})"
            else:
                resultado['alerta_costo_kg'] = f"🟢 ${cost_per_kg_usd:.3f}"
        else:
            resultado['cost_per_kg_usd_str'] = '⚠️ Sin TC'
    
    # Buscar costo presupuestado - el campo 'routes' puede ser:
    # 1. Un ID numérico (int)
    # 2. Un string con ID numérico
    # 3. Un JSON string con array de objetos [{"route_name": ..., "cost_type": ..., "cost_value": ...}]
    routes_field = ruta_info.get('routes', False)
    
    if routes_field:
        # Caso 1 y 2: Si es False, None o vacío, skip
        if routes_field == False or routes_field == 'false':
            pass
        # Caso 3: Intentar parsear como JSON
        elif isinstance(routes_field, str) and routes_field.startswith('['):
            try:
                routes_data = json.loads(routes_field)
                if isinstance(routes_data, list) and len(routes_data) > 0:
                    # Tomar el primer elemento del array
                    route_info = routes_data[0]
                    resultado['route_name'] = route_info.get('route_name')
                    resultado['route_name_str'] = resultado['route_name'] or 'Sin nombre'
                    resultado['costo_presupuestado'] = route_info.get('cost_value')
                    resultado['costo_presupuestado_str'] = f"${resultado['costo_presupuestado']:,.0f}" if resultado['costo_presupuestado'] else '⚠️ Sin presupuesto'
                    
                    # Mapear cost_type a tipo de camión
                    cost_type = route_info.get('cost_type', '')
                    if cost_type == 'truck_8':
                        resultado['tipo_camion'] = '🚛 Camión 8 Ton'
                    elif cost_type == 'truck_12_14':
                        resultado['tipo_camion'] = '🚚 Camión 12-14 Ton'
                    elif cost_type == 'short_rampla':
                        resultado['tipo_camion'] = '🚐 Rampla Corta'
                    elif cost_type == 'rampla':
                        resultado['tipo_camion'] = '🚛 Rampla'
                    resultado['tipo_camion_str'] = resultado['tipo_camion'] or '⚠️ Sin tipo'
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        # Caso 1 y 2: Es un ID numérico, buscar en costes_rutas
        elif isinstance(routes_field, (int, str)):
            try:
                route_id = int(routes_field)
                for coste in costes_rutas:
                    if coste.get('id') == route_id:
                        resultado['route_name'] = coste.get('route_name')
                        resultado['route_name_str'] = resultado['route_name'] or 'Sin nombre'
                        # Determinar tipo de camión y costo presupuestado
                        if coste.get('truck_8_cost'):
                            resultado['costo_presupuestado'] = coste.get('truck_8_cost')
                            resultado['tipo_camion'] = '🚛 Camión 8 Ton'
                        elif coste.get('truck_12_14_cost'):
                            resultado['costo_presupuestado'] = coste.get('truck_12_14_cost')
                            resultado['tipo_camion'] = '🚚 Camión 12-14 Ton'
                        elif coste.get('short_rampla_cost'):
                            resultado['costo_presupuestado'] = coste.get('short_rampla_cost')
                            resultado['tipo_camion'] = '🚐 Rampla Corta'
                        elif coste.get('rampla_cost'):
                            resultado['costo_presupuestado'] = coste.get('rampla_cost')
                            resultado['tipo_camion'] = '🚛 Rampla'
                        resultado['costo_presupuestado_str'] = f"${resultado['costo_presupuestado']:,.0f}" if resultado['costo_presupuestado'] else '⚠️ Sin presupuesto'
                        resultado['tipo_camion_str'] = resultado['tipo_camion'] or '⚠️ Sin tipo'
                        break
            except (ValueError, TypeError):
                pass
    
    # Calcular diferencias
    if resultado['costo_calculado'] and oc_monto:
        diferencia = oc_monto - resultado['costo_calculado']
        resultado['diferencia'] = diferencia
        if resultado['costo_calculado'] > 0:
            resultado['diferencia_porcentaje'] = (diferencia / resultado['costo_calculado']) * 100
            
            # Alertas: Positivo = SOBRECOSTO (malo), Negativo = AHORRO (bueno)
            if resultado['diferencia_porcentaje'] > 20:
                resultado['alerta'] = '🔴 Sobrecosto >20%'
            elif resultado['diferencia_porcentaje'] > 10:
                resultado['alerta'] = '🟡 Sobrecosto >10%'
            elif resultado['diferencia_porcentaje'] < -20:
                resultado['alerta'] = '🟢 Ahorro >20%'
            elif resultado['diferencia_porcentaje'] < -10:
                resultado['alerta'] = '🟢 Ahorro >10%'
            else:
                resultado['alerta'] = '🟢 Dentro de rango'
    
    # Comparar con presupuesto
    if resultado['costo_presupuestado'] and oc_monto and resultado['costo_presupuestado'] > 0:
        dif_presupuesto = oc_monto - resultado['costo_presupuestado']
        dif_presupuesto_pct = (dif_presupuesto / resultado['costo_presupuestado']) * 100
        
        # Solo crear alerta si hay sobrecosto significativo (positivo)
        if resultado.get('diferencia_porcentaje') is None or abs(dif_presupuesto_pct) > abs(resultado.get('diferencia_porcentaje', 0)):
            if dif_presupuesto_pct > 20:
                resultado['alerta_presupuesto'] = f"🔴 Sobrecosto vs presupuesto: {dif_presupuesto_pct:+.1f}%"
            elif dif_presupuesto_pct > 10:
                resultado['alerta_presupuesto'] = f"🟡 Sobrecosto vs presupuesto: {dif_presupuesto_pct:+.1f}%"
            elif dif_presupuesto_pct < -10:
                resultado['alerta_presupuesto'] = f"🟢 Ahorro vs presupuesto: {dif_presupuesto_pct:+.1f}%"
    
    return resultado


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
            {'fields': ['id', 'res_id', 'res_name', 'activity_type_id', 'date_deadline', 'summary', 'state'], 'limit': 500}
        )
        return actividades
    except Exception as e:
        st.error(f"Error al obtener actividades: {e}")
        return []


@st.cache_data(ttl=60)
def obtener_detalles_oc_fletes(_models, _uid, username, password, oc_ids):
    """Obtener detalles de OCs - SOLO AREA TRANSPORTES, CATEGORIA SERVICIOS"""
    if not oc_ids:
        return [], []
    
    try:
        ocs = _models.execute_kw(
            DB, _uid, password,
            'purchase.order', 'search_read',
            [[('id', 'in', oc_ids)]],
            {'fields': ['id', 'name', 'state', 'partner_id', 'amount_untaxed', 
                       'x_studio_selection_field_yUNPd', 'x_studio_categora_de_producto', 
                       'create_date', 'user_id', 'date_order']}
        )
        
        # Filtrar EXCLUSIVAMENTE: Área TRANSPORTES + Categoría SERVICIOS
        ocs_fletes = []
        ocs_filtradas = []  # Para debug
        
        for oc in ocs:
            # Verificar categoría SERVICIOS (OBLIGATORIO)
            categoria = oc.get('x_studio_categora_de_producto')
            if categoria != 'SERVICIOS':
                ocs_filtradas.append({
                    'oc': oc['name'],
                    'razon': f'Categoría: {categoria} (se requiere SERVICIOS)'
                })
                continue
            
            # Verificar área TRANSPORTES (OBLIGATORIO)
            area = oc.get('x_studio_selection_field_yUNPd')
            if area and isinstance(area, (list, tuple)):
                area = area[1]
            
            if not area or 'TRANSPORTES' not in str(area).upper():
                ocs_filtradas.append({
                    'oc': oc['name'],
                    'razon': f'Área: {area} (se requiere TRANSPORTES)'
                })
                continue
            
            # Obtener producto/servicio y calcular costo desde líneas
            lineas = _models.execute_kw(
                DB, _uid, password,
                'purchase.order.line', 'search_read',
                [[('order_id', '=', oc['id'])]],
                {'fields': ['product_id', 'name', 'price_unit', 'product_qty', 'price_subtotal']}
            )
            
            if lineas and lineas[0].get('product_id'):
                oc['producto'] = lineas[0]['product_id'][1]
            elif lineas and lineas[0].get('name'):
                oc['producto'] = lineas[0]['name']
            else:
                oc['producto'] = 'N/A'
            
            # Calcular costo desde líneas (PxQ)
            oc['costo_lineas'] = sum(linea.get('price_subtotal', 0) for linea in lineas)
            
            ocs_fletes.append(oc)
        
        return ocs_fletes, ocs_filtradas
    except Exception as e:
        st.error(f"Error al obtener detalles de OCs: {e}")
        return [], []


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
    st.info("📦 Área: **TRANSPORTES** | Categoría: **SERVICIOS** | Integración: Sistema de Logística")
    
    # Inicializar estado de sesión
    if 'datos_cargados_fletes' not in st.session_state:
        st.session_state.datos_cargados_fletes = False
    
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
        if st.button("📥 Cargar Datos", key="cargar_fletes", type="primary"):
            st.session_state.datos_cargados_fletes = True
            st.cache_data.clear()
            st.rerun()
    
    # Si no se han cargado datos, mostrar mensaje y salir
    if not st.session_state.datos_cargados_fletes:
        st.info("👆 Presiona 'Cargar Datos' para ver las aprobaciones pendientes")
        return
    
    user_id = USUARIOS[usuario_seleccionado]
    
    # Obtener conexión
    models, uid = get_odoo_connection(username, password)
    if not models or not uid:
        st.error("No se pudo conectar a Odoo")
        return
    
    # Obtener datos de logística y tipo de cambio
    with st.spinner("Cargando datos de logística..."):
        rutas_logistica = obtener_rutas_logistica()
        costes_rutas = obtener_costes_rutas()
        tipo_cambio_usd = obtener_tipo_cambio_usd()
        
        info_tc = f" | 💱 USD: ${tipo_cambio_usd:,.0f}" if tipo_cambio_usd else " | ⚠️ Sin TC"
        st.caption(f"✅ {len(rutas_logistica)} rutas | {len(costes_rutas)} presupuestos{info_tc}")
    
    # Obtener actividades pendientes
    with st.spinner(f"Cargando aprobaciones de {usuario_seleccionado}..."):
        actividades = obtener_actividades_usuario(models, uid, username, password, user_id)
        
        if not actividades:
            st.success(f"✅ No hay aprobaciones de FLETES pendientes para {usuario_seleccionado}")
            st.balloons()
            return
        
        # Obtener detalles de OCs (filtradas por área TRANSPORTES + categoría SERVICIOS)
        oc_ids = [act['res_id'] for act in actividades]
        ocs_detalles, ocs_filtradas = obtener_detalles_oc_fletes(models, uid, username, password, oc_ids)
        
        # Mostrar información de filtrado
        if ocs_filtradas:
            with st.expander(f"ℹ️ {len(ocs_filtradas)} OCs excluidas (no son TRANSPORTES/SERVICIOS)"):
                for filtro in ocs_filtradas:
                    st.caption(f"• {filtro['oc']}: {filtro['razon']}")
        
        if not ocs_detalles:
            st.success(f"✅ No hay aprobaciones de FLETES pendientes para {usuario_seleccionado}")
            st.info("ℹ️ Todas las actividades pendientes fueron filtradas (no son TRANSPORTES/SERVICIOS)")
            st.balloons()
            return
    
    # Crear diccionario de OCs por ID
    ocs_dict = {oc['id']: oc for oc in ocs_detalles}
    
    # Combinar datos y enriquecer con info de logística
    datos_completos = []
    for act in actividades:
        oc = ocs_dict.get(act['res_id'])
        if oc:
            proveedor = oc['partner_id'][1] if oc.get('partner_id') and isinstance(oc['partner_id'], (list, tuple)) else 'N/A'
            area = oc.get('x_studio_selection_field_yUNPd')
            if area and isinstance(area, (list, tuple)):
                area = area[1]
            
            # Buscar en logística
            ruta_info = buscar_ruta_en_logistica(oc['name'], rutas_logistica)
            comparacion = calcular_comparacion_presupuesto(
                oc.get('amount_untaxed', 0), 
                oc.get('costo_lineas', 0),
                ruta_info, 
                costes_rutas,
                tipo_cambio_usd
            )
            
            datos_completos.append({
                'actividad_id': act['id'],
                'oc_id': oc['id'],
                'oc_name': oc['name'],
                'proveedor': proveedor,
                'monto': oc.get('amount_untaxed', 0),
                'area': str(area) if area else 'N/A',
                'producto': oc.get('producto', 'N/A'),
                'estado_oc': oc['state'],
                'estado_actividad': act.get('state', 'N/A'),
                'fecha_limite': act.get('date_deadline', 'N/A'),
                'fecha_creacion': oc.get('create_date', 'N/A'),
                'fecha_orden': oc.get('date_order') if oc.get('date_order') else None,
                'tipo_actividad': act['activity_type_id'][1] if act.get('activity_type_id') else 'N/A',
                **comparacion  # Agregar info de logística
            })
    
    df = pd.DataFrame(datos_completos)
    
    # Métricas principales
    st.markdown("### 📊 Resumen")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Total OCs", len(df))
    
    with col2:
        total_monto = df['monto'].sum()
        st.metric("Monto Total", f"${total_monto:,.0f}")
    
    with col3:
        vencidas = len(df[df['estado_actividad'] == 'overdue'])
        st.metric("Vencidas", vencidas, delta=f"-{vencidas}" if vencidas > 0 else "0")
    
    with col4:
        con_ruta = len(df[df['tiene_ruta'] == True])
        st.metric("Con Ruta Logística", con_ruta)
    
    with col5:
        con_alerta = len(df[df['alerta'].notna() & (df['alerta'].str.contains('🔴|🟡'))])
        st.metric("Con Alertas", con_alerta, delta=f"-{con_alerta}" if con_alerta > 0 else "0")
    
    with col6:
        # Promedio de costo por kg en USD
        df_con_costo = df[df['cost_per_kg_usd'].notna() & (df['cost_per_kg_usd'] > 0)]
        if len(df_con_costo) > 0:
            prom_costo_kg_usd = df_con_costo['cost_per_kg_usd'].mean()
            delta_vs_umbral = ((prom_costo_kg_usd - UMBRAL_COSTO_KG_USD) / UMBRAL_COSTO_KG_USD) * 100
            st.metric(
                "Prom. $/Kg USD", 
                f"${prom_costo_kg_usd:.3f}",
                delta=f"{delta_vs_umbral:+.1f}% vs $0.11",
                delta_color="inverse"  # Verde si es negativo (mejor), rojo si es positivo (peor)
            )
        else:
            st.metric("Prom. $/Kg USD", "⚠️ Sin datos")
    
    st.markdown("---")
    
    # Filtros mejorados
    st.markdown("### 🔍 Filtros")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        estados_disponibles = ['Todos'] + sorted(df['estado_actividad'].unique().tolist())
        filtro_estado = st.selectbox("Estado Actividad", estados_disponibles, key="filtro_estado_fletes")
    
    with col2:
        proveedores_disponibles = ['Todos'] + sorted(df['proveedor'].unique().tolist())
        filtro_proveedor = st.selectbox("Proveedor", proveedores_disponibles, key="filtro_proveedor_fletes")
    
    with col3:
        filtro_oc = st.text_input("Buscar OC", "", key="filtro_oc_fletes", placeholder="Ej: OC12067")
    
    col4, col5 = st.columns(2)
    
    # Calcular rango de fechas válido (excluyendo nulos)
    df_con_fecha = df[df['fecha_orden'].notna()]
    if not df_con_fecha.empty:
        fecha_min = pd.to_datetime(df_con_fecha['fecha_orden']).min().date()
        fecha_max = pd.to_datetime(df_con_fecha['fecha_orden']).max().date()
    else:
        fecha_min = datetime.now().date()
        fecha_max = datetime.now().date()
    
    with col4:
        fecha_desde = st.date_input(
            "📅 Fecha desde", 
            value=fecha_min,
            key="fecha_desde_fletes"
        )
    
    with col5:
        fecha_hasta = st.date_input(
            "📅 Fecha hasta", 
            value=fecha_max,
            key="fecha_hasta_fletes"
        )
    
    col6, col7, col8 = st.columns(3)
    
    with col6:
        min_monto = st.number_input("💰 Monto Mínimo", min_value=0, value=0, step=100000, key="min_monto_fletes")
    
    with col7:
        max_monto = st.number_input("💰 Monto Máximo", min_value=0, value=int(df['monto'].max()) if not df.empty else 10000000, step=100000, key="max_monto_fletes")
    
    with col8:
        filtro_alerta = st.selectbox("⚠️ Estado Info", ["Todas", "Info Completa", "Info Incompleta"], key="filtro_alerta_fletes")
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    if filtro_estado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['estado_actividad'] == filtro_estado]
    
    if filtro_proveedor != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['proveedor'] == filtro_proveedor]
    
    if filtro_oc:
        df_filtrado = df_filtrado[df_filtrado['oc_name'].str.contains(filtro_oc, case=False, na=False)]
    
    # Filtro de fechas - manejar valores nulos
    df_filtrado['fecha_orden_dt'] = pd.to_datetime(df_filtrado['fecha_orden'], errors='coerce').dt.date
    # Solo filtrar filas que tienen fecha válida
    df_con_fecha_valida = df_filtrado[df_filtrado['fecha_orden_dt'].notna()]
    df_sin_fecha = df_filtrado[df_filtrado['fecha_orden_dt'].isna()]
    
    df_con_fecha_filtrada = df_con_fecha_valida[
        (df_con_fecha_valida['fecha_orden_dt'] >= fecha_desde) & 
        (df_con_fecha_valida['fecha_orden_dt'] <= fecha_hasta)
    ]
    
    # Incluir OCs sin fecha en el resultado (opcional: puedes quitarlo si prefieres excluirlas)
    df_filtrado = pd.concat([df_con_fecha_filtrada, df_sin_fecha], ignore_index=True)
    
    df_filtrado = df_filtrado[(df_filtrado['monto'] >= min_monto) & (df_filtrado['monto'] <= max_monto)]
    
    # Aplicar filtro de estado de información
    if filtro_alerta == "Info Completa":
        # Info completa = tiene ruta Y tiene presupuesto Y tiene tipo de camión
        df_filtrado = df_filtrado[
            (df_filtrado['tiene_ruta'] == True) & 
            (df_filtrado['costo_presupuestado'].notna()) & 
            (df_filtrado['tipo_camion'].notna())
        ]
    elif filtro_alerta == "Info Incompleta":
        # Info incompleta = NO tiene ruta O NO tiene presupuesto O NO tiene tipo de camión
        df_filtrado = df_filtrado[
            (df_filtrado['tiene_ruta'] == False) | 
            (df_filtrado['costo_presupuestado'].isna()) | 
            (df_filtrado['tipo_camion'].isna())
        ]
    
    st.markdown(f"**Mostrando {len(df_filtrado)} de {len(df)} OCs de Fletes**")
    
    st.markdown("---")
    
    # Selector de vista
    modo_vista = st.radio(
        "Seleccionar Vista:",
        ["📂 Expanders (Detallado)", "📋 Tabla con Selección Múltiple"],
        horizontal=True,
        key="modo_vista_fletes"
    )
    
    st.markdown("---")
    
    # Vista de tabla o expanders
    if modo_vista == "📋 Tabla con Selección Múltiple":
        render_vista_tabla_mejorada(df_filtrado, models, uid, username, password)
    else:
        render_vista_expanders(df_filtrado, models, uid, username, password)
    
    # Footer
    st.markdown("---")
    st.markdown(f"*Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")


def render_vista_tabla_mejorada(df: pd.DataFrame, models, uid, username, password):
    """Vista de tabla con selección múltiple para aprobar - Agrupada por Proveedor"""
    st.markdown("### 📋 Tabla con Aprobación Múltiple (Agrupada por Proveedor)")
    
    if df.empty:
        st.info("No hay OCs que mostrar con los filtros aplicados")
        return
    
    # Preparar datos para tabla
    df_display = df.copy()
    
    # Agregar columna de info completa
    df_display['info_completa'] = df_display.apply(
        lambda x: '✅' if (x['tiene_ruta'] and pd.notna(x['costo_presupuestado']) and pd.notna(x['tipo_camion'])) else '⚠️',
        axis=1
    )
    
    # Formatear fecha para mostrar
    df_display['fecha_str'] = pd.to_datetime(df_display['fecha_orden'], errors='coerce').dt.strftime('%d/%m/%Y').fillna('Sin fecha')
    
    # Ordenar por proveedor y luego por OC
    df_display = df_display.sort_values(['proveedor', 'oc_name'])
    
    # === VISTA AGRUPADA POR PROVEEDOR ===
    proveedores = df_display['proveedor'].unique()
    
    st.markdown(f"**{len(proveedores)} proveedores | {len(df_display)} OCs totales**")
    
    # Selector de proveedores para filtrar la vista
    proveedores_seleccionados = st.multiselect(
        "🏢 Filtrar por Proveedor (dejar vacío para ver todos):",
        sorted(proveedores),
        key="filtro_proveedores_tabla"
    )
    
    if proveedores_seleccionados:
        df_vista = df_display[df_display['proveedor'].isin(proveedores_seleccionados)]
    else:
        df_vista = df_display
    
    st.markdown("---")
    
    # Crear tabla agrupada
    for proveedor in sorted(df_vista['proveedor'].unique()):
        df_proveedor = df_vista[df_vista['proveedor'] == proveedor]
        total_monto_proveedor = df_proveedor['monto'].sum()
        n_ocs = len(df_proveedor)
        n_vencidas = len(df_proveedor[df_proveedor['estado_actividad'] == 'overdue'])
        
        # Header del proveedor con métricas
        header_text = f"🏢 **{proveedor}** | {n_ocs} OCs | ${total_monto_proveedor:,.0f}"
        if n_vencidas > 0:
            header_text += f" | ⏰ {n_vencidas} vencidas"
        
        with st.expander(header_text, expanded=len(proveedores_seleccionados) > 0):
            # Crear dataframe para mostrar
            df_tabla_proveedor = pd.DataFrame({
                'OC': df_proveedor['oc_name'],
                'Fecha': df_proveedor['fecha_str'],
                'Monto': df_proveedor['monto'].apply(lambda x: f"${x:,.0f}"),
                'Costo Calc.': df_proveedor['costo_calculado_str'],
                'Presupuesto': df_proveedor['costo_presupuestado_str'],
                '$/Kg USD': df_proveedor['alerta_costo_kg'].fillna(df_proveedor['cost_per_kg_usd_str']),
                'Tipo Camión': df_proveedor['tipo_camion_str'].str[:15],
                'Alerta': df_proveedor['alerta'].fillna('⚪'),
                'Est.': df_proveedor['estado_actividad'].apply(lambda x: '⏰' if x == 'overdue' else '🔵'),
                'Info': df_proveedor['info_completa'],
                'ID': df_proveedor['actividad_id']
            })
            
            # Mostrar tabla del proveedor
            st.dataframe(
                df_tabla_proveedor.drop(columns=['ID']),
                use_container_width=True,
                hide_index=True,
                height=min(400, len(df_tabla_proveedor) * 40 + 40)
            )
            
            # Selección de OCs de este proveedor
            ocs_proveedor = []
            for _, row in df_tabla_proveedor.iterrows():
                oc_data = df_proveedor[df_proveedor['actividad_id'] == row['ID']].iloc[0].to_dict()
                ocs_proveedor.append({
                    'label': f"{row['OC']} - {row['Fecha']} - {row['Monto']}",
                    'data': oc_data
                })
            
            # Multiselect para este proveedor
            key_proveedor = f"select_{proveedor.replace(' ', '_')[:20]}"
            seleccionadas = st.multiselect(
                f"Seleccionar OCs de {proveedor[:30]}:",
                [oc['label'] for oc in ocs_proveedor],
                key=key_proveedor
            )
            
            if seleccionadas:
                ocs_sel_proveedor = [oc['data'] for oc in ocs_proveedor if oc['label'] in seleccionadas]
                total_sel = sum(oc['monto'] for oc in ocs_sel_proveedor)
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.caption(f"✅ {len(seleccionadas)} seleccionadas | ${total_sel:,.0f}")
                
                with col2:
                    if st.button(f"✅ Aprobar", key=f"aprobar_{key_proveedor}", type="primary"):
                        with st.spinner("Aprobando..."):
                            exitosas = 0
                            for oc in ocs_sel_proveedor:
                                exito, _ = aprobar_actividad(models, uid, username, password, oc['actividad_id'])
                                if exito:
                                    exitosas += 1
                            st.success(f"✅ {exitosas} OCs aprobadas")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                
                with col3:
                    if st.button(f"❌ Rechazar", key=f"rechazar_{key_proveedor}"):
                        st.session_state[f'rechazar_proveedor_{key_proveedor}'] = True
                
                # Modal de rechazo
                if st.session_state.get(f'rechazar_proveedor_{key_proveedor}'):
                    motivo = st.text_area(f"Motivo del rechazo:", key=f"motivo_{key_proveedor}")
                    if st.button(f"Confirmar Rechazo", key=f"confirmar_rechazo_{key_proveedor}"):
                        if motivo:
                            with st.spinner("Rechazando..."):
                                exitosas = 0
                                for oc in ocs_sel_proveedor:
                                    exito, _ = rechazar_actividad(models, uid, username, password, oc['actividad_id'], motivo)
                                    if exito:
                                        exitosas += 1
                                st.success(f"❌ {exitosas} OCs rechazadas")
                                st.session_state[f'rechazar_proveedor_{key_proveedor}'] = False
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                        else:
                            st.warning("Ingresa un motivo de rechazo")
    
    st.markdown("---")
    
    # Leyenda
    st.caption("✅ = Info Completa | ⚠️ = Info Incompleta | ⏰ = Vencida | 🔵 = En plazo")
    st.caption(f"$/Kg USD: 🟢 = ≤${UMBRAL_COSTO_KG_USD} | 🟡 = >${UMBRAL_COSTO_KG_USD} | 🔴 = >20% sobre umbral")


def render_vista_expanders(df: pd.DataFrame, models, uid, username, password):
    """Vista de expanders optimizada con paginación"""
    st.markdown("### 📂 Vista Detallada (Expanders)")
    
    if df.empty:
        st.info("No hay OCs que mostrar con los filtros aplicados")
        return
    
    # Ordenar por monto descendente
    df = df.sort_values('monto', ascending=False)
    
    # Configurar paginación
    items_por_pagina = 10
    total_paginas = (len(df) - 1) // items_por_pagina + 1
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pagina_actual = st.number_input(
            "Página", 
            min_value=1, 
            max_value=max(1, total_paginas),
            value=1,
            key="pagina_expander"
        )
    
    st.markdown(f"**Mostrando página {pagina_actual} de {total_paginas}**")
    
    inicio = (pagina_actual - 1) * items_por_pagina
    fin = inicio + items_por_pagina
    df_pagina = df.iloc[inicio:fin]
    
    # Mostrar cada OC con opciones de aprobación
    for idx, row in df_pagina.iterrows():
        # Título del expander con info clave
        titulo_expander = f"🚚 **{row['oc_name']}** - {row['proveedor'][:40]} - **${row['monto']:,.0f}**"
        if row.get('alerta'):
            titulo_expander += f" | {row['alerta']}"
        
        with st.expander(titulo_expander):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                **Detalles de la Orden:**
                - **OC:** {row['oc_name']} | [Ver en Odoo]({URL}/web#id={row['oc_id']}&model=purchase.order&view_type=form)
                - **Proveedor:** {row['proveedor']}
                - **Monto OC:** ${row['monto']:,.0f}
                - **Área:** {row['area']}
                - **Estado OC:** {row['estado_oc']}
                - **Estado Aprobación:** {row['estado_actividad']}
                - **Fecha Límite:** {row['fecha_limite']}
                - **Fecha Orden:** {row['fecha_orden']}
                - **Producto/Servicio:** {row['producto'][:80]}
                """)
                
                # Información de logística
                if row.get('tiene_ruta'):
                    st.markdown("---")
                    st.markdown("**📍 Información de Logística:**")
                    
                    st.info(f"**Tipo de Vehículo:** {row['tipo_camion_str']}")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Costo Calculado", row['costo_calculado_str'])
                        st.caption(f"Ruta: {row['route_name_str']}")
                    
                    with col_b:
                        st.metric("Presupuesto", row['costo_presupuestado_str'])
                        if row.get('kilometers'):
                            st.caption(f"Distancia: {row['kilometers']:.1f} km")
                        else:
                            st.caption("Distancia: No disponible")
                    
                    if row.get('diferencia') is not None and row.get('diferencia_porcentaje') is not None:
                        dif_color = "green" if row['diferencia'] < 0 else "red"
                        st.markdown(f"Diferencia vs calculado: **:{dif_color}[${row['diferencia']:+,.0f}]** ({row['diferencia_porcentaje']:+.1f}%)")
                    
                    if row.get('alerta_presupuesto'):
                        st.warning(row['alerta_presupuesto'])
                else:
                    st.warning("⚠️ Esta OC **no está registrada** en el sistema de logística. Por favor, registre la ruta antes de aprobar.")
                
                # Mostrar flujo de aprobaciones
                st.markdown("---")
                with st.spinner("Cargando flujo..."):
                    todas_acts = obtener_todas_actividades_oc(models, uid, username, password, row['oc_id'])
                    if todas_acts:
                        st.markdown("**Flujo de Aprobaciones:**")
                        for act in todas_acts:
                            usuario = act['user_id'][1] if act.get('user_id') and isinstance(act['user_id'], (list, tuple)) else 'N/A'
                            tipo = act['activity_type_id'][1] if act.get('activity_type_id') else 'N/A'
                            estado_icon = "✅" if act['state'] == 'done' else "⏰" if act['state'] == 'overdue' else "🔵"
                            st.markdown(f"  {estado_icon} {usuario} - {tipo} - {act['state']}")
            
            with col2:
                st.markdown("**Acciones:**")
                
                # Botón aprobar
                if st.button(f"✅ Aprobar", key=f"aprobar_flete_{row['actividad_id']}", type="primary"):
                    with st.spinner("Aprobando..."):
                        exito, mensaje = aprobar_actividad(models, uid, username, password, row['actividad_id'])
                        if exito:
                            st.success(f"✅ {row['oc_name']} aprobada")
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

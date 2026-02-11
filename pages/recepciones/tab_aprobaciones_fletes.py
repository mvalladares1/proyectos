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
API_LOGISTICA_RUTAS = 'https://riofuturoprocesos.com/api/logistica/db/rutas'
API_LOGISTICA_COSTES = 'https://riofuturoprocesos.com/api/logistica/db/coste-rutas'
API_MINDICADOR = 'https://mindicador.cl/api'

# Umbral de costo por kg en USD
UMBRAL_COSTO_KG_USD = 0.11  # 11 centavos de dólar


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


def _get_cache_key_fecha():
    """Genera una clave de cache que cambia cada día a las 8 AM hora chilena"""
    from datetime import datetime, timedelta
    import pytz
    
    # Timezone de Chile
    tz_chile = pytz.timezone('America/Santiago')
    now_chile = datetime.now(tz_chile)
    
    # Si es antes de las 8 AM, usar la fecha del día anterior
    # Esto hace que el cache se renueve a las 8 AM
    if now_chile.hour < 8:
        fecha_cache = (now_chile - timedelta(days=1)).date()
    else:
        fecha_cache = now_chile.date()
    
    return str(fecha_cache)


@st.cache_data(show_spinner="Obteniendo tipo de cambio USD/CLP del Banco Central...")
def obtener_tipo_cambio_usd(_cache_key=None):
    """
    Obtener tipo de cambio USD/CLP desde Banco Central (mindicador.cl).
    Cache se renueva cada día a las 8 AM hora chilena.
    """
    try:
        # Primero intentar mindicador (Banco Central de Chile) con timeout largo
        response = requests.get(API_MINDICADOR, timeout=20)
        if response.status_code == 200:
            data = response.json()
            dolar = data.get('dolar', {}).get('valor')
            if dolar:
                return float(dolar)
        
        # Fallback a exchangerate-api.com si mindicador falla
        response = requests.get('https://api.exchangerate-api.com/v4/latest/USD', timeout=5)
        if response.status_code == 200:
            data = response.json()
            clp = data.get('rates', {}).get('CLP')
            if clp:
                return float(clp)
    except:
        pass
    
    # Si todo falla, usar valor por defecto
    st.warning("⚠️ No se pudo obtener tipo de cambio USD - Usando valor de respaldo $860")
    return 860.0


def get_tipo_cambio():
    """Wrapper para obtener tipo de cambio con cache diario renovado a las 8 AM"""
    return obtener_tipo_cambio_usd(_cache_key=_get_cache_key_fecha())


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
        'route_correlativo': None,  # Campo 'name' de la ruta
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
    resultado['route_correlativo'] = ruta_info.get('name', None)  # Correlativo de la ruta
    resultado['route_name_str'] = 'Procesando...'
    
    # Extraer total_qnt (cantidad real en kg) - viene como string
    total_qnt_str = ruta_info.get('total_qnt', 0)
    try:
        resultado['total_qnt'] = float(total_qnt_str) if total_qnt_str else 0
    except (ValueError, TypeError):
        resultado['total_qnt'] = 0
    
    # Extraer cost_per_kg de la ruta y calcular en USD
    cost_per_kg_clp = ruta_info.get('cost_per_kg', 0)
    
    # Convertir a float si es string
    try:
        cost_per_kg_clp = float(cost_per_kg_clp) if cost_per_kg_clp else 0
    except (ValueError, TypeError):
        cost_per_kg_clp = 0
    
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
def obtener_ocs_fletes_con_aprobaciones(_models, _uid, username, password):
    """
    Obtener TODAS las OCs de TRANSPORTES/SERVICIOS con información de aprobaciones.
    Optimizado para reducir queries a Odoo.
    """
    try:
        # Buscar OCs de SERVICIOS - TODAS excepto canceladas
        # Estados: 'draft', 'sent', 'to approve', 'purchase', 'done'
        # Excluir: 'cancel'
        ocs = _models.execute_kw(
            DB, _uid, password,
            'purchase.order', 'search_read',
            [[
                ('x_studio_categora_de_producto', '=', 'SERVICIOS'),
                ('state', '!=', 'cancel')
            ]],
            {'fields': ['id', 'name', 'state', 'partner_id', 'amount_untaxed', 
                       'x_studio_selection_field_yUNPd', 'x_studio_categora_de_producto', 
                       'create_date', 'user_id', 'date_order'],
             'limit': 1000,  # Aumentar límite
             'order': 'date_order desc'}
        )
        
        # Filtrar solo área TRANSPORTES
        ocs_fletes = []
        oc_ids = []
        for oc in ocs:
            area = oc.get('x_studio_selection_field_yUNPd')
            if area and isinstance(area, (list, tuple)):
                area = area[1]
            
            if not area or 'TRANSPORTES' not in str(area).upper():
                continue
            
            ocs_fletes.append(oc)
            oc_ids.append(oc['id'])
        
        if not oc_ids:
            return []
        
        # OPTIMIZACIÓN 1: Obtener TODAS las líneas de una vez
        todas_lineas = _models.execute_kw(
            DB, _uid, password,
            'purchase.order.line', 'search_read',
            [[('order_id', 'in', oc_ids)]],
            {'fields': ['order_id', 'product_id', 'name', 'price_unit', 'product_qty', 'price_subtotal']}
        )
        
        # Agrupar líneas por OC
        lineas_por_oc = {}
        for linea in todas_lineas:
            oc_id = linea['order_id'][0] if isinstance(linea['order_id'], (list, tuple)) else linea['order_id']
            if oc_id not in lineas_por_oc:
                lineas_por_oc[oc_id] = []
            lineas_por_oc[oc_id].append(linea)
        
        # OPTIMIZACIÓN 2: Obtener TODAS las actividades de una vez
        todas_actividades = _models.execute_kw(
            DB, _uid, password,
            'mail.activity', 'search_read',
            [[
                ('res_model', '=', 'purchase.order'),
                ('res_id', 'in', oc_ids),
                ('activity_type_id.name', 'in', ['Grant Approval', 'Approval'])
            ]],
            {'fields': ['res_id', 'id', 'user_id', 'date_deadline', 'state']}
        )
        
        # Agrupar actividades por OC (tomar la primera)
        actividades_por_oc = {}
        for act in todas_actividades:
            oc_id = act['res_id']
            if oc_id not in actividades_por_oc:
                actividades_por_oc[oc_id] = act
        
        # OPTIMIZACIÓN 3: Obtener aprobaciones desde studio.approval.entry (fuente real)
        todas_aprobaciones_entry = _models.execute_kw(
            DB, _uid, password,
            'studio.approval.entry', 'search_read',
            [[
                ('res_id', 'in', oc_ids),
                ('rule_id', 'in', [144, 122])
            ]],
            {'fields': ['res_id', 'user_id', 'rule_id', 'create_date', 'approved']}
        )
        
        # Nombres de reglas hardcodeados (evita leer studio.approval.rule que requiere permisos admin)
        reglas_aprobacion = {
            144: 'Aprobación Transportes 1',
            122: 'Aprobación Transportes 2'
        }
        
        # Agrupar aprobaciones y rechazos por OC
        aprobaciones_por_oc = {}
        rechazos_por_oc = {}
        for entry in todas_aprobaciones_entry:
            oc_id = entry['res_id']
            
            nombre_usuario = entry['user_id'][1] if entry.get('user_id') and isinstance(entry['user_id'], (list, tuple)) else 'Desconocido'
            rule_id = entry['rule_id'][0] if isinstance(entry['rule_id'], (list, tuple)) else entry['rule_id']
            rol = reglas_aprobacion.get(rule_id, 'Aprobador')
            
            info = {
                'usuario': nombre_usuario,
                'rol': rol,
                'fecha': entry.get('create_date')
            }
            
            if entry.get('approved'):
                if oc_id not in aprobaciones_por_oc:
                    aprobaciones_por_oc[oc_id] = []
                aprobaciones_por_oc[oc_id].append(info)
            else:
                if oc_id not in rechazos_por_oc:
                    rechazos_por_oc[oc_id] = []
                rechazos_por_oc[oc_id].append(info)
        
        # Procesar cada OC con los datos pre-cargados
        for oc in ocs_fletes:
            oc_id = oc['id']
            
            # Líneas
            lineas = lineas_por_oc.get(oc_id, [])
            if lineas and lineas[0].get('product_id'):
                oc['producto'] = lineas[0]['product_id'][1]
            elif lineas and lineas[0].get('name'):
                oc['producto'] = lineas[0]['name']
            else:
                oc['producto'] = 'N/A'
            
            oc['costo_lineas'] = sum(linea.get('price_subtotal', 0) for linea in lineas)
            oc['total_kilos'] = sum(linea.get('product_qty', 0) for linea in lineas)
            
            # Aprobaciones desde studio.approval.entry
            aprobaciones = aprobaciones_por_oc.get(oc_id, [])
            
            oc['aprobaciones'] = aprobaciones
            oc['num_aprobaciones'] = len(aprobaciones)
            oc['aprobadores'] = [a['usuario'] for a in aprobaciones]
            oc['rechazos'] = rechazos_por_oc.get(oc_id, [])
            oc['rechazadores'] = [r['usuario'] for r in oc['rechazos']]
            
            # Actividad pendiente
            actividad = actividades_por_oc.get(oc_id)
            if actividad:
                oc['actividad_id'] = actividad['id']
                oc['actividad_usuario'] = actividad['user_id'][1] if actividad.get('user_id') else 'N/A'
                oc['actividad_fecha_limite'] = actividad.get('date_deadline')
                oc['actividad_estado'] = actividad.get('state', 'planned')
            else:
                oc['actividad_id'] = None
                oc['actividad_usuario'] = None
                oc['actividad_fecha_limite'] = None
                oc['actividad_estado'] = None
        
        return ocs_fletes
    except Exception as e:
        st.error(f"Error al obtener OCs de fletes: {e}")
        return []


def obtener_aprobaciones_oc(_models, _uid, password, oc_id):
    """
    Obtener las aprobaciones de una OC desde studio.approval.entry.
    Lee las entradas de aprobación reales en vez del chatter.
    """
    try:
        # Buscar aprobaciones reales en studio.approval.entry
        entries = _models.execute_kw(
            DB, _uid, password,
            'studio.approval.entry', 'search_read',
            [[
                ('res_id', '=', int(oc_id)),
                ('rule_id', 'in', [144, 122]),
                ('approved', '=', True)
            ]],
            {'fields': ['user_id', 'rule_id', 'create_date']}
        )
        
        # Nombres de reglas hardcodeados (evita leer studio.approval.rule que requiere permisos admin)
        reglas_aprobacion = {
            144: 'Aprobación Transportes 1',
            122: 'Aprobación Transportes 2'
        }
        
        aprobaciones = []
        for entry in entries:
            nombre_usuario = entry['user_id'][1] if entry.get('user_id') and isinstance(entry['user_id'], (list, tuple)) else 'Desconocido'
            rule_id = entry['rule_id'][0] if isinstance(entry['rule_id'], (list, tuple)) else entry['rule_id']
            rol = reglas_aprobacion.get(rule_id, 'Aprobador')
            
            aprobaciones.append({
                'usuario': nombre_usuario,
                'rol': rol,
                'fecha': entry.get('create_date')
            })
        
        return aprobaciones
    except Exception as e:
        return []


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


def aprobar_oc(models, uid, username, password, oc_id, activity_id=None):
    """Aprobar una OC usando reglas de Studio - registra aprobación sin confirmar hasta tener todas las requeridas"""
    try:
        # Contexto en español para todas las operaciones
        contexto = {'lang': 'es_ES'}
        
        # 1. Determinar qué regla usar según el usuario y su rol
        if username.lower() == 'msepulveda@riofuturo.cl':
            rule_id = 144
            rol_usuario = 'Gerente de procesos'
        elif username.lower() == 'fhorst@riofuturo.cl':
            rule_id = 122
            rol_usuario = 'Gerente de Control de gestión'
        else:
            # Usuario no configurado, usar regla por defecto
            rule_id = 144
            rol_usuario = 'Gerente de procesos'
        
        # 2. Obtener nombre de la OC para mensajes
        oc_data = models.execute_kw(
            DB, uid, password,
            'purchase.order', 'read',
            [[int(oc_id)]],
            {'fields': ['name'], 'context': contexto}
        )
        oc_name = oc_data[0]['name'] if oc_data else f"OC#{oc_id}"
        
        # 3. Verificar si ya tiene aprobación del usuario
        mi_entrada = models.execute_kw(
            DB, uid, password,
            'studio.approval.entry', 'search_read',
            [[('res_id', '=', int(oc_id)), ('rule_id', '=', rule_id), ('user_id', '=', int(uid))]],
            {'fields': ['id', 'approved'], 'context': contexto}
        )
        
        if mi_entrada and mi_entrada[0]['approved']:
            return False, f"✅ {oc_name}: Ya aprobado como {rol_usuario}"
        
        # DEBUG: Ver todas las entradas de aprobación de esta OC
        todas_entradas = models.execute_kw(
            DB, uid, password,
            'studio.approval.entry', 'search_read',
            [[('res_id', '=', int(oc_id))]],
            {'fields': ['id', 'user_id', 'rule_id', 'approved'], 'context': contexto}
        )
        
        # DEBUG: Siempre mostrar las entradas para diagnóstico
        debug_info = f"\n\n📋 DEBUG - Entradas de aprobación para {oc_name}:\n"
        if todas_entradas:
            for entrada in todas_entradas:
                debug_info += f"  - Entry ID {entrada['id']}: User ID {entrada['user_id']}, Rule ID {entrada['rule_id']}, Approved: {entrada['approved']}\n"
        else:
            debug_info += "  (No hay entradas creadas - la OC no tiene flujo de aprobación activo)\n"
        debug_info += f"\n🔍 Tú eres User ID {uid}, buscando entrada con Rule ID {rule_id} ({rol_usuario})"
        
        # Buscar la entrada de aprobación pendiente para este usuario y regla
        entrada_pendiente = models.execute_kw(
            DB, uid, password,
            'studio.approval.entry', 'search',
            [[
                ('res_id', '=', int(oc_id)),
                ('rule_id', '=', rule_id),
                ('user_id', '=', int(uid))
            ]],
            {'context': contexto}
        )
        
        if not entrada_pendiente:
            return False, f"❌ {oc_name}: No tienes entrada de aprobación asignada.{debug_info}\n\n💡 Esto significa que tu usuario no está configurado en las reglas de aprobación de Odoo Studio."
        
        # Aprobar usando write directamente (evita validaciones de permisos sobre studio.approval.rule)
        try:
            models.execute_kw(
                DB, uid, password,
                'studio.approval.entry', 'write',
                [entrada_pendiente, {'approved': True}],
                {'context': contexto}
            )
        except Exception as e_approve:
            return False, f"❌ {oc_name}: Error al aprobar: {str(e_approve)}"
        
        # Contar aprobaciones totales (de todos los usuarios)
        aprobaciones_existentes = models.execute_kw(
            DB, uid, password,
            'studio.approval.entry', 'search_read',
            [[('res_id', '=', int(oc_id)), ('rule_id', 'in', [144, 122]), ('approved', '=', True)]],
            {'fields': ['id', 'user_id', 'rule_id'], 'context': contexto}
        )
        
        # 4. Si hay actividad pendiente, completarla para limpieza visual
        if activity_id is not None and pd.notna(activity_id):
            try:
                models.execute_kw(
                    DB, uid, password,
                    'mail.activity', 'action_feedback',
                    [[int(activity_id)]],
                    {'feedback': 'Aprobado desde dashboard', 'context': contexto}
                )
            except:
                pass
        
        # 5. Determinar qué hacer según el número de aprobaciones
        num_aprobaciones = len(aprobaciones_existentes)
        
        if num_aprobaciones >= 2:
            # Ya están las 2 aprobaciones - confirmar la orden
            try:
                models.execute_kw(
                    DB, uid, password,
                    'purchase.order', 'button_confirm',
                    [[int(oc_id)]],
                    {'context': contexto}
                )
                
                # Después de confirmar, actualizar qty_received = product_qty en todas las líneas
                try:
                    # Leer la orden confirmada para obtener las líneas
                    orden = models.execute_kw(
                        DB, uid, password,
                        'purchase.order', 'read',
                        [[int(oc_id)]],
                        {'fields': ['order_line'], 'context': contexto}
                    )
                    
                    if orden and orden[0].get('order_line'):
                        lineas_ids = orden[0]['order_line']
                        
                        # Leer las líneas para obtener product_qty
                        lineas = models.execute_kw(
                            DB, uid, password,
                            'purchase.order.line', 'read',
                            [lineas_ids],
                            {'fields': ['id', 'product_qty'], 'context': contexto}
                        )
                        
                        # Actualizar cada línea con qty_received = product_qty
                        for linea in lineas:
                            models.execute_kw(
                                DB, uid, password,
                                'purchase.order.line', 'write',
                                [[linea['id']], {'qty_received': linea['product_qty']}],
                                {'context': contexto}
                            )
                except Exception as e_lineas:
                    # Si falla la actualización de líneas, no es crítico
                    pass
                
                return True, f"✅ {oc_name}: Aprobado como {rol_usuario}"
            except Exception as e:
                return True, f"✅ {oc_name}: Aprobado como {rol_usuario} (error al confirmar orden)"
        else:
            # Primera aprobación - NO confirmar, solo notificar
            # La actividad para el segundo aprobador debe crearse manualmente o mediante reglas de Studio
            return True, f"✅ {oc_name}: Aprobado como {rol_usuario}"
        
    except Exception as e:
        return False, str(e)


def quitar_aprobacion(models, uid, password, oc_id):
    """Quitar la aprobación o rechazo del usuario actual de una OC"""
    try:
        # Buscar cualquier entrada del usuario (aprobada o rechazada)
        entradas = models.execute_kw(
            DB, uid, password,
            'studio.approval.entry', 'search',
            [[('res_id', '=', int(oc_id)), ('rule_id', 'in', [144, 122]), ('user_id', '=', int(uid))]]
        )
        
        if not entradas:
            return False, "No tienes aprobación ni rechazo registrado para esta OC"
        
        # Eliminar la entrada
        models.execute_kw(
            DB, uid, password,
            'studio.approval.entry', 'unlink',
            [entradas]
        )
        
        return True, "Aprobación/rechazo eliminado correctamente"
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


def rechazar_oc(models, uid, username, password, oc_id, motivo, activity_id=None):
    """
    Rechazar una OC de flete:
    1. Registrar rechazo en studio.approval.entry (approved=False) para que aparezca con ícono rojo
    2. Si hay actividad pendiente, completarla con feedback de rechazo
    3. Publicar nota de rechazo en el chatter
    4. Crear actividad de seguimiento asignada al responsable de la OC
    """
    try:
        contexto = {'lang': 'es_ES'}
        resultados_parciales = []
        
        # 1. Determinar regla del usuario
        if username.lower() == 'msepulveda@riofuturo.cl':
            rule_id = 144
        elif username.lower() == 'fhorst@riofuturo.cl':
            rule_id = 122
        else:
            rule_id = 144
        
        # Verificar si el usuario ya tiene una entrada (aprobada o rechazada)
        entrada_existente = models.execute_kw(
            DB, uid, password,
            'studio.approval.entry', 'search',
            [[('res_id', '=', int(oc_id)), ('rule_id', '=', rule_id), ('user_id', '=', int(uid))]]
        )
        
        if entrada_existente:
            # Actualizar la entrada existente a rechazada
            models.execute_kw(
                DB, uid, password,
                'studio.approval.entry', 'write',
                [entrada_existente, {'approved': False}]
            )
            resultados_parciales.append("Entrada de aprobación marcada como rechazada")
        else:
            # Crear nueva entrada con approved=False (rechazo)
            models.execute_kw(
                DB, uid, password,
                'studio.approval.entry', 'create',
                [{
                    'res_id': int(oc_id),
                    'rule_id': rule_id,
                    'user_id': int(uid),
                    'approved': False
                }],
                {'context': contexto}
            )
            resultados_parciales.append("Rechazo registrado en aprobaciones")
        
        # 2. Si hay actividad pendiente, completarla con feedback de rechazo
        if activity_id and pd.notna(activity_id):
            try:
                models.execute_kw(
                    DB, uid, password,
                    'mail.activity', 'action_feedback',
                    [[int(activity_id)]],
                    {'feedback': f'RECHAZADO: {motivo}', 'context': contexto}
                )
                resultados_parciales.append("Actividad completada con rechazo")
            except:
                pass
        
        # 3. Crear actividad de seguimiento para el responsable de la OC
        try:
            # Obtener el responsable de la OC
            oc_data = models.execute_kw(
                DB, uid, password,
                'purchase.order', 'read',
                [int(oc_id)],
                {'fields': ['user_id', 'name'], 'context': contexto}
            )
            responsable_id = uid  # Por defecto, asignar al mismo usuario
            oc_name = f"OC {oc_id}"
            if oc_data and oc_data[0].get('user_id'):
                responsable_id = oc_data[0]['user_id'][0]
                oc_name = oc_data[0].get('name', oc_name)
            
            # Buscar el tipo de actividad "To Do" o "Por hacer"
            activity_type_ids = models.execute_kw(
                DB, uid, password,
                'mail.activity.type', 'search',
                [[('name', 'in', ['To Do', 'Por hacer'])]],
                {'limit': 1}
            )
            activity_type_id = activity_type_ids[0] if activity_type_ids else 4  # 4 = To Do por defecto
            
            models.execute_kw(
                DB, uid, password,
                'mail.activity', 'create',
                [{
                    'res_model_id': models.execute_kw(DB, uid, password, 'ir.model', 'search', [[('model', '=', 'purchase.order')]])[0],
                    'res_id': int(oc_id),
                    'activity_type_id': activity_type_id,
                    'user_id': responsable_id,
                    'summary': f'OC Rechazada - Revisar',
                    'note': f'Rechazada por {username}. Motivo: {motivo}',
                    'date_deadline': datetime.now().strftime('%Y-%m-%d'),
                }],
                {'context': contexto}
            )
            resultados_parciales.append("Actividad de seguimiento creada")
        except Exception as e_act:
            resultados_parciales.append(f"Error al crear actividad: {str(e_act)[:50]}")
        
        resumen = " | ".join(resultados_parciales)
        return True, f"❌ Rechazada - {resumen}"
    except Exception as e:
        return False, str(e)


def render_tab(username, password):
    """Renderiza el tab de aprobaciones de fletes"""
    
    st.header("🚚 Aprobaciones de Fletes y Transportes")
    st.info("📦 Área: **TRANSPORTES** | Categoría: **SERVICIOS** | Requiere 2 aprobaciones")
    
    # Inicializar estado de sesión
    if 'datos_cargados_fletes' not in st.session_state:
        st.session_state.datos_cargados_fletes = False
    
    # Botón para cargar datos
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"👤 Usuario conectado: **{username}**")
    
    with col2:
        if st.button("📥 Cargar/Actualizar Datos", key="cargar_fletes", type="primary"):
            st.session_state.datos_cargados_fletes = True
            st.cache_data.clear()
            st.rerun()
    
    # Si no se han cargado datos, mostrar mensaje y salir
    if not st.session_state.datos_cargados_fletes:
        st.info("👆 Presiona 'Cargar/Actualizar Datos' para ver las OCs de fletes")
        return
    
    # Obtener conexión
    models, uid = get_odoo_connection(username, password)
    if not models or not uid:
        st.error("No se pudo conectar a Odoo")
        return
    
    # Obtener datos de logística y tipo de cambio
    with st.spinner("Cargando datos de logística..."):
        rutas_logistica = obtener_rutas_logistica()
        costes_rutas = obtener_costes_rutas()
        tipo_cambio_usd = get_tipo_cambio()
        
        info_tc = f" | 💱 USD: ${tipo_cambio_usd:,.0f}" if tipo_cambio_usd else " | ⚠️ Sin TC"
        st.caption(f"✅ {len(rutas_logistica)} rutas | {len(costes_rutas)} presupuestos{info_tc}")
    
    # Obtener todas las OCs de fletes con información de aprobaciones
    with st.spinner("Cargando OCs de fletes..."):
        ocs_fletes = obtener_ocs_fletes_con_aprobaciones(models, uid, username, password)
        
        if not ocs_fletes:
            st.success("✅ No hay OCs de FLETES en proceso de aprobación")
            return
    
    # Enriquecer con info de logística y crear DataFrame
    datos_completos = []
    for oc in ocs_fletes:
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
        
        # Determinar estado de aprobación
        num_aprob = oc.get('num_aprobaciones', 0)
        rechazos = oc.get('rechazos', [])
        if oc['state'] == 'purchase':
            estado_aprobacion = '🟢 Aprobada'
            estado_aprobacion_num = '2/2'
        elif rechazos:
            rechazadores_str = ', '.join(oc.get('rechazadores', []))
            estado_aprobacion = f'❌ Rechazada ({num_aprob}/2)'
            estado_aprobacion_num = f'{num_aprob}/2'
        elif num_aprob >= 2:
            estado_aprobacion = '🟢 2/2'
            estado_aprobacion_num = '2/2'
        elif num_aprob == 1:
            estado_aprobacion = '🟡 1/2'
            estado_aprobacion_num = '1/2'
        else:
            estado_aprobacion = '🔴 0/2'
            estado_aprobacion_num = '0/2'
        
        # Formatear aprobadores y rechazadores
        aprobadores_str = ', '.join(oc.get('aprobadores', [])) if oc.get('aprobadores') else ''
        rechazadores_str_fmt = ', '.join([f'❌{r}' for r in oc.get('rechazadores', [])]) if oc.get('rechazadores') else ''
        if aprobadores_str and rechazadores_str_fmt:
            aprobadores_str = f"{aprobadores_str} | {rechazadores_str_fmt}"
        elif rechazadores_str_fmt:
            aprobadores_str = rechazadores_str_fmt
        if not aprobadores_str:
            aprobadores_str = 'Sin aprobaciones'
        
        # Extraer creador de la OC
        creador = oc['user_id'][1] if oc.get('user_id') and isinstance(oc['user_id'], (list, tuple)) else 'N/A'
        
        # Calcular $/km (monto OC / kilómetros)
        costo_por_km = None
        kilometers = comparacion.get('kilometers')
        if kilometers:
            try:
                kilometers_float = float(kilometers)
                if kilometers_float > 0:
                    costo_por_km = oc.get('amount_untaxed', 0) / kilometers_float
            except (ValueError, TypeError):
                pass
        
        datos_completos.append({
            'actividad_id': oc.get('actividad_id'),
            'oc_id': oc['id'],
            'oc_name': oc['name'],
            'proveedor': proveedor,
            'monto': oc.get('amount_untaxed', 0),
            'area': str(area) if area else 'N/A',
            'producto': oc.get('producto', 'N/A'),
            'estado_oc': oc['state'],
            'estado_aprobacion': estado_aprobacion,
            'estado_aprobacion_num': estado_aprobacion_num,
            'num_aprobaciones': num_aprob,
            'aprobadores': aprobadores_str,
            'actividad_usuario': oc.get('actividad_usuario'),
            'actividad_estado': oc.get('actividad_estado'),
            'fecha_limite': oc.get('actividad_fecha_limite', 'N/A'),
            'fecha_creacion': oc.get('create_date', 'N/A'),
            'fecha_orden': oc.get('date_order') if oc.get('date_order') else None,
            'creador': creador,
            'total_kilos': oc.get('total_kilos', 0),  # Kilos desde líneas Odoo (puede ser incorrecto)
            'total_qnt_ruta': comparacion.get('total_qnt', 0),  # Kilos reales desde ruta (correcto)
            'costo_por_km': costo_por_km,
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
        pendientes = len(df[df['num_aprobaciones'] < 2])
        st.metric("Pendientes", pendientes, delta=f"-{pendientes}" if pendientes > 0 else "0")
    
    with col4:
        con_1_aprob = len(df[df['num_aprobaciones'] == 1])
        st.metric("Con 1 Aprob.", con_1_aprob)
    
    with col5:
        aprobadas = len(df[(df['num_aprobaciones'] >= 2) | (df['estado_oc'] == 'purchase')])
        st.metric("Aprobadas (2/2)", aprobadas)
    
    with col6:
        # Promedio de costo por kg en USD
        # Verificar si la columna existe en el DataFrame
        if 'cost_per_kg_usd' in df.columns:
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
                st.metric("Prom. $/Kg USD", "⚠️ Sin rutas vinculadas")
        else:
            st.metric("Prom. $/Kg USD", "⚠️ Sin datos")
    
    st.markdown("---")
    
    # Filtros mejorados
    st.markdown("### 🔍 Filtros")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_aprobacion = st.selectbox(
            "Estado Aprobación", 
            ['Todas', 'Pendientes (0/2 y 1/2)', 'Sin aprobar (0/2)', 'Con 1 aprob. (1/2)', 'Aprobadas (2/2)'],
            key="filtro_aprobacion_fletes"
        )
    
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
    
    col9, _, _ = st.columns(3)
    
    with col9:
        filtro_costo_kg = st.selectbox(
            "🟢🟡🔴 $/kg USD",
            ["Todos", "🟢 Verde (≤$0.11)", "🟡 Amarillo (>$0.11)", "🔴 Rojo (>$0.132)", "🟢🟡 Verde y Amarillo"],
            key="filtro_costo_kg_fletes"
        )
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    # Filtro de estado de aprobación
    if filtro_aprobacion == 'Pendientes (0/2 y 1/2)':
        df_filtrado = df_filtrado[df_filtrado['num_aprobaciones'] < 2]
    elif filtro_aprobacion == 'Sin aprobar (0/2)':
        df_filtrado = df_filtrado[df_filtrado['num_aprobaciones'] == 0]
    elif filtro_aprobacion == 'Con 1 aprob. (1/2)':
        df_filtrado = df_filtrado[df_filtrado['num_aprobaciones'] == 1]
    elif filtro_aprobacion == 'Aprobadas (2/2)':
        df_filtrado = df_filtrado[(df_filtrado['num_aprobaciones'] >= 2) | (df_filtrado['estado_oc'] == 'purchase')]
    
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
    
    # Aplicar filtro de $/kg USD
    if filtro_costo_kg != "Todos":
        # Filtrar solo OCs que tienen cost_per_kg_usd
        df_con_costo_kg = df_filtrado[df_filtrado['cost_per_kg_usd'].notna()]
        
        if filtro_costo_kg == "🟢 Verde (≤$0.11)":
            df_filtrado = df_con_costo_kg[df_con_costo_kg['cost_per_kg_usd'] <= UMBRAL_COSTO_KG_USD]
        elif filtro_costo_kg == "🟡 Amarillo (>$0.11)":
            df_filtrado = df_con_costo_kg[
                (df_con_costo_kg['cost_per_kg_usd'] > UMBRAL_COSTO_KG_USD) &
                (df_con_costo_kg['cost_per_kg_usd'] <= UMBRAL_COSTO_KG_USD * 1.2)
            ]
        elif filtro_costo_kg == "🔴 Rojo (>$0.132)":
            df_filtrado = df_con_costo_kg[df_con_costo_kg['cost_per_kg_usd'] > UMBRAL_COSTO_KG_USD * 1.2]
        elif filtro_costo_kg == "🟢🟡 Verde y Amarillo":
            df_filtrado = df_con_costo_kg[df_con_costo_kg['cost_per_kg_usd'] <= UMBRAL_COSTO_KG_USD * 1.2]
    
    st.markdown(f"**Mostrando {len(df_filtrado)} de {len(df)} OCs de Fletes**")
    
    st.markdown("---")
    
    # Selector de vista
    modo_vista = st.radio(
        "Seleccionar Vista:",
        ["� Tabla con Selección Múltiple", "📂 Expanders (Detallado)"],
        horizontal=True,
        key="modo_vista_fletes",
        index=0  # Por defecto Tabla con Selección Múltiple
    )
    
    st.markdown("---")
    
    # Vista de tabla o expanders
    if modo_vista == "� Expanders (Detallado)":
        render_vista_expanders(df_filtrado, models, uid, username, password)
    else:
        render_vista_tabla_mejorada(df_filtrado, models, uid, username, password)
    
    # Footer
    st.markdown("---")
    st.markdown(f"*Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")


def render_proveedor_table(proveedor: str, df_proveedor: pd.DataFrame, models, uid, username, password):
    """Renderizar tabla de un proveedor específico con selección y acciones"""
    # Filtrar solo OCs que se pueden aprobar (menos de 2 aprobaciones y no completamente aprobadas)
    df_aprobables = df_proveedor[
        (df_proveedor['num_aprobaciones'] < 2) &
        (df_proveedor['estado_oc'] != 'purchase')
    ]
    
    if len(df_aprobables) == 0:
        st.caption("✅ Todas las OCs de este proveedor ya están completamente aprobadas")
        
        # Solo mostrar tabla informativa sin selección
        def comparar_presupuesto(row):
            if pd.isna(row['costo_presupuestado']) or not row['costo_presupuestado']:
                return '⚠️ Sin ppto'
            if pd.isna(row['monto']) or not row['monto']:
                return '-'
            dif = row['monto'] - row['costo_presupuestado']
            dif_pct = (dif / row['costo_presupuestado']) * 100
            if dif <= 0:
                return f"🟢 -{abs(dif_pct):.0f}%"
            elif dif_pct <= 10:
                return f"🟡 +{dif_pct:.0f}%"
            else:
                return f"🔴 +{dif_pct:.0f}%"
        
        df_tabla_info = pd.DataFrame({
            'OC': df_proveedor['oc_name'],
            'Fecha': df_proveedor['fecha_str'],
            'Monto': df_proveedor['monto'].apply(lambda x: f"${x:,.0f}"),
            'vs Ppto': df_proveedor.apply(comparar_presupuesto, axis=1),
            'Aprob.': df_proveedor['estado_aprobacion'],
            'Aprobadores': df_proveedor['aprobadores'].str[:40],
        })
        
        st.dataframe(df_tabla_info, use_container_width=True, hide_index=True)
        return
    
    # Key único para este proveedor
    key_proveedor = f"select_{proveedor.replace(' ', '_')[:20]}"
    
    # Inicializar estado de selección si no existe
    if f'selected_{key_proveedor}' not in st.session_state:
        st.session_state[f'selected_{key_proveedor}'] = set()
    
    # Inicializar contador de versión (para forzar recreación de checkboxes)
    if f'checkbox_version_{key_proveedor}' not in st.session_state:
        st.session_state[f'checkbox_version_{key_proveedor}'] = 0
    
    # --- Fragment: solo la selección de checkboxes se re-renderiza al hacer click ---
    @st.fragment
    def _fragment_seleccion():
        # Callback para "Seleccionar todas" - solo reacciona al click real del usuario
        def on_select_all_change():
            sa_key = f"select_all_{key_proveedor}"
            if st.session_state[sa_key]:
                # Usuario marcó "seleccionar todas"
                st.session_state[f'selected_{key_proveedor}'] = set(df_aprobables['oc_id'].tolist())
                st.session_state[f'checkbox_version_{key_proveedor}'] += 1
            else:
                # Usuario desmarcó "seleccionar todas"
                st.session_state[f'selected_{key_proveedor}'] = set()
                st.session_state[f'checkbox_version_{key_proveedor}'] += 1
        
        # Checkbox "Seleccionar todas"
        col_check, col_info = st.columns([1, 3])
        with col_check:
            # Pre-inicializar el key si no existe
            sa_key = f"select_all_{key_proveedor}"
            if sa_key not in st.session_state:
                st.session_state[sa_key] = False
            
            st.checkbox(
                "Seleccionar todas",
                key=sa_key,
                on_change=on_select_all_change
            )
        
        with col_info:
            if st.session_state[f'selected_{key_proveedor}']:
                st.caption(f"✅ {len(st.session_state[f'selected_{key_proveedor}'])} OCs seleccionadas")
        
        # Función para comparar con presupuesto
        def comparar_presupuesto(row):
            if pd.isna(row['costo_presupuestado']) or not row['costo_presupuestado']:
                return '⚠️ Sin ppto'
            if pd.isna(row['monto']) or not row['monto']:
                return '-'
            dif = row['monto'] - row['costo_presupuestado']
            dif_pct = (dif / row['costo_presupuestado']) * 100
            if dif <= 0:
                return f"🟢 -{abs(dif_pct):.0f}%"
            elif dif_pct <= 10:
                return f"🟡 +{dif_pct:.0f}%"
            else:
                return f"🔴 +{dif_pct:.0f}%"
        
        # Cabeceras de la tabla
        col_sel_h, col_oc_h, col_ruta_h, col_fecha_h, col_monto_h, col_kg_h, col_km_h, col_ppto_h, col_aprob_h = st.columns([0.5, 1.1, 0.7, 0.9, 0.9, 0.7, 0.7, 0.7, 1.5])
        with col_sel_h:
            st.markdown("**✅**")
        with col_oc_h:
            st.markdown("**OC**")
        with col_ruta_h:
            st.markdown("**Ruta**")
        with col_fecha_h:
            st.markdown("**Fecha**")
        with col_monto_h:
            st.markdown("**Monto**")
        with col_kg_h:
            st.markdown("**$/kg USD**")
        with col_km_h:
            st.markdown("**$/km**")
        with col_ppto_h:
            st.markdown("**vs Ppto**")
        with col_aprob_h:
            st.markdown("**Aprobación**")
        
        st.markdown("---")
        
        # Obtener versión actual de checkboxes
        checkbox_version = st.session_state.get(f'checkbox_version_{key_proveedor}', 0)
        
        # Callback para manejar cambios de checkboxes individuales
        def on_checkbox_change(oc_id, cb_key):
            if st.session_state[cb_key]:
                st.session_state[f'selected_{key_proveedor}'].add(oc_id)
            else:
                st.session_state[f'selected_{key_proveedor}'].discard(oc_id)
        
        # Pre-inicializar keys de checkboxes ANTES de renderizar
        for _idx, _row in df_aprobables.iterrows():
            cb_key = f"check_{key_proveedor}_{_row['oc_id']}_v{checkbox_version}"
            if cb_key not in st.session_state:
                st.session_state[cb_key] = _row['oc_id'] in st.session_state[f'selected_{key_proveedor}']
        
        # Mostrar tabla con checkboxes
        for _idx, _row in df_aprobables.iterrows():
            # Contenedor para cada fila con expander
            with st.container():
                # Fila principal con datos
                col_sel, col_oc, col_ruta, col_fecha, col_monto, col_kg, col_km, col_ppto, col_aprob = st.columns([0.5, 1.1, 0.7, 0.9, 0.9, 0.7, 0.7, 0.7, 1.5])
                
                with col_sel:
                    cb_key = f"check_{key_proveedor}_{_row['oc_id']}_v{checkbox_version}"
                    st.checkbox(
                        f"Sel {_row['oc_name']}",
                        key=cb_key,
                        label_visibility="collapsed",
                        on_change=on_checkbox_change,
                        args=(_row['oc_id'], cb_key)
                    )
            
                with col_oc:
                    st.markdown(f"**{_row['oc_name']}**")
                
                with col_ruta:
                    ruta_correlativo = _row.get('route_correlativo', None)
                    st.text(ruta_correlativo if ruta_correlativo else "-")
                
                with col_fecha:
                    fecha_str = pd.to_datetime(_row['fecha_orden'], errors='coerce').strftime('%d/%m/%Y') if pd.notna(_row['fecha_orden']) else 'Sin fecha'
                    st.text(fecha_str)
                
                with col_monto:
                    st.text(f"${_row['monto']:,.0f}")
                
                with col_kg:
                    if _row.get('cost_per_kg_usd'):
                        costo_kg = _row['cost_per_kg_usd']
                        if costo_kg > UMBRAL_COSTO_KG_USD * 1.2:
                            st.markdown(f"🔴 ${costo_kg:.3f}")
                        elif costo_kg > UMBRAL_COSTO_KG_USD:
                            st.markdown(f"🟡 ${costo_kg:.3f}")
                        else:
                            st.markdown(f"🟢 ${costo_kg:.3f}")
                    else:
                        st.text("-")
                
                with col_km:
                    if _row.get('costo_por_km'):
                        costo_km = _row['costo_por_km']
                        st.text(f"${costo_km:,.0f}")
                    else:
                        st.text("-")
                
                with col_ppto:
                    st.text(comparar_presupuesto(_row))
                
                with col_aprob:
                    st.text(f"{_row['estado_aprobacion']} - {_row['aprobadores'][:30]}")
                
                # Expander de detalles fuera de las columnas para ocupar ancho completo
                with st.expander("📋 Ver detalles", expanded=False):
                    col_det1, col_det2, col_det3 = st.columns(3)
                    
                    with col_det1:
                        st.markdown("**📋 Información General**")
                        st.markdown(f"**OC:** {_row['oc_name']}")
                        st.markdown(f"**Creador:** {_row.get('creador', 'N/A')}")
                        st.markdown(f"**Fecha:** {fecha_str}")
                        st.markdown(f"**Proveedor:** {_row.get('proveedor', 'N/A')[:30]}")
                    
                    with col_det2:
                        st.markdown("**💰 Costos y Cantidades**")
                        st.markdown(f"**Monto OC:** ${_row['monto']:,.0f}")
                        
                        # Determinar si mostrar alerta basado en cost_per_kg_usd
                        mostrar_alerta = False
                        if _row.get('cost_per_kg_usd'):
                            costo_kg_usd = _row['cost_per_kg_usd']
                            if costo_kg_usd > UMBRAL_COSTO_KG_USD * 1.2:  # Rojo
                                mostrar_alerta = True
                        
                        # Usar cantidad desde ruta (total_qnt_ruta) que es la correcta
                        total_kilos_ruta = _row.get('total_qnt_ruta', 0)
                        if total_kilos_ruta > 0:
                            cantidad_str = f"{total_kilos_ruta:,.0f} kg"
                            if mostrar_alerta:
                                cantidad_str += " ⚠️"
                            st.markdown(f"**Cantidad:** {cantidad_str}")
                            # $/kg calculado desde monto / kilos reales de la ruta
                            costo_kg_oc = _row['monto'] / total_kilos_ruta
                            st.markdown(f"**Costo/kg OC (CLP):** ${costo_kg_oc:,.0f}")
                        else:
                            # Fallback a kilos de Odoo si no hay datos de ruta
                            total_kilos_odoo = _row.get('total_kilos', 0)
                            if total_kilos_odoo > 0:
                                cantidad_str = f"{total_kilos_odoo:,.0f} kg"
                                if mostrar_alerta:
                                    cantidad_str += " ⚠️"
                                st.markdown(f"**Cantidad:** {cantidad_str}")
                                costo_kg_oc = _row['monto'] / total_kilos_odoo
                                st.markdown(f"**Costo/kg OC (CLP):** ${costo_kg_oc:,.0f}")
                            else:
                                st.markdown(f"**Cantidad:** N/A")
                                st.markdown(f"**Costo/kg OC:** N/A")
                        
                        # $/kg USD desde ruta
                        if _row.get('cost_per_kg_usd'):
                            costo_kg_usd = _row['cost_per_kg_usd']
                            if costo_kg_usd > UMBRAL_COSTO_KG_USD * 1.2:
                                st.markdown(f"**Costo/kg USD:** 🔴 ${costo_kg_usd:.3f} (>${UMBRAL_COSTO_KG_USD})")
                            elif costo_kg_usd > UMBRAL_COSTO_KG_USD:
                                st.markdown(f"**Costo/kg USD:** 🟡 ${costo_kg_usd:.3f} (>${UMBRAL_COSTO_KG_USD})")
                            else:
                                st.markdown(f"**Costo/kg USD:** 🟢 ${costo_kg_usd:.3f}")
                        else:
                            st.markdown(f"**Costo/kg USD:** N/A")
                    
                    with col_det3:
                        st.markdown("**🚛 Logística y Presupuesto**")
                        if ruta_correlativo:
                            st.markdown(f"**Ruta:** {ruta_correlativo}")
                        else:
                            st.markdown(f"**Ruta:** ⚠️ Sin ruta asignada")
                        
                        route_name = _row.get('route_name', 'N/A')
                        if route_name and route_name != 'N/A':
                            st.markdown(f"**Nombre Ruta:** {route_name[:30]}")
                        
                        # Kilómetros y $/km
                        kilometers = _row.get('kilometers', 0)
                        try:
                            kilometers_float = float(kilometers) if kilometers else 0
                            if kilometers_float > 0:
                                st.markdown(f"**Kilómetros:** {kilometers_float:,.0f} km")
                                if _row.get('costo_por_km'):
                                    st.markdown(f"**Costo/km:** ${_row['costo_por_km']:,.0f}")
                        except (ValueError, TypeError):
                            pass
                        
                        tipo_camion = _row.get('tipo_camion', 'N/A')
                        st.markdown(f"**Tipo Camión:** {tipo_camion if tipo_camion else 'N/A'}")
                        
                        # Comparación con presupuesto
                        if pd.notna(_row.get('costo_presupuestado')) and _row.get('costo_presupuestado'):
                            costo_ppto = _row['costo_presupuestado']
                            st.markdown(f"**Presupuesto:** ${costo_ppto:,.0f}")
                            
                            dif = _row['monto'] - costo_ppto
                            dif_pct = (dif / costo_ppto) * 100
                            
                            if dif > 0:
                                if dif_pct > 20:
                                    st.markdown(f"**vs Ppto:** 🔴 Sobrecosto +{dif_pct:.1f}% (${dif:,.0f})")
                                elif dif_pct > 10:
                                    st.markdown(f"**vs Ppto:** 🟡 Sobrecosto +{dif_pct:.1f}% (${dif:,.0f})")
                                else:
                                    st.markdown(f"**vs Ppto:** 🟢 Sobrecosto +{dif_pct:.1f}% (${dif:,.0f})")
                            else:
                                st.markdown(f"**vs Ppto:** 🟢 Ahorro {dif_pct:.1f}% (${abs(dif):,.0f})")
                        else:
                            st.markdown(f"**Presupuesto:** ⚠️ Sin presupuesto")
                    
                    # Estado de aprobación
                    st.markdown("---")
                    st.markdown(f"**📝 Estado Aprobación:** {_row['estado_aprobacion']}")
                    if _row.get('aprobadores') and _row['aprobadores'] != 'Sin aprobaciones':
                        st.markdown(f"**Aprobadores:** {_row['aprobadores']}")
                
                st.markdown("---")  # Separador entre filas
        if st.session_state[f'selected_{key_proveedor}']:
            st.markdown("---")
            
            ocs_seleccionadas = df_aprobables[df_aprobables['oc_id'].isin(st.session_state[f'selected_{key_proveedor}'])]
            total_sel = ocs_seleccionadas['monto'].sum()
            
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                st.markdown(f"**💰 Total: ${total_sel:,.0f}**")
            
            with col2:
                if st.button(f"✅ Aprobar", key=f"aprobar_{key_proveedor}", type="primary"):
                    with st.spinner("Aprobando..."):
                        resultados = []
                        for oc_id in st.session_state[f'selected_{key_proveedor}']:
                            oc_data = df_aprobables[df_aprobables['oc_id'] == oc_id].iloc[0]
                            activity_id = oc_data.get('actividad_id')
                            success, msg = aprobar_oc(models, uid, username, password, oc_id, activity_id)
                            resultados.append((oc_data['oc_name'], success, msg))
                        
                        for oc_name, success, msg in resultados:
                            if success:
                                st.success(f"{oc_name}: {msg}")
                            else:
                                st.error(f"{oc_name}: {msg}")
                        
                        obtener_ocs_fletes_con_aprobaciones.clear()
                        time.sleep(1)
                        st.rerun(scope="app")
            
            with col3:
                if st.button(f"🔄 Quitar aprobación", key=f"quitar_{key_proveedor}"):
                    with st.spinner("Quitando aprobaciones..."):
                        resultados = []
                        for oc_id in st.session_state[f'selected_{key_proveedor}']:
                            oc_data = df_aprobables[df_aprobables['oc_id'] == oc_id].iloc[0]
                            success, msg = quitar_aprobacion(models, uid, password, oc_id)
                            resultados.append((oc_data['oc_name'], success, msg))
                        
                        for oc_name, success, msg in resultados:
                            if success:
                                st.success(f"{oc_name}: {msg}")
                            else:
                                st.warning(f"{oc_name}: {msg}")
                        
                        obtener_ocs_fletes_con_aprobaciones.clear()
                        time.sleep(1)
                        st.rerun(scope="app")
            
            with col4:
                if st.button(f"❌ Rechazar", key=f"rechazar_{key_proveedor}"):
                    st.session_state[f'mostrar_motivo_rechazo_{key_proveedor}'] = True
        
        # Formulario de rechazo con motivo (fuera de las columnas para que tenga ancho completo)
        if st.session_state.get(f'mostrar_motivo_rechazo_{key_proveedor}', False):
            st.warning("⚠️ Ingresa el motivo del rechazo:")
            motivo = st.text_input(
                "Motivo del rechazo",
                key=f"motivo_rechazo_{key_proveedor}",
                placeholder="Ej: Precio fuera de rango, proveedor incorrecto, etc."
            )
            col_confirmar, col_cancelar, _ = st.columns([1, 1, 3])
            with col_confirmar:
                if st.button("✅ Confirmar rechazo", key=f"confirmar_rechazo_{key_proveedor}", type="primary", disabled=not motivo):
                    with st.spinner("Rechazando..."):
                        resultados = []
                        for oc_id in st.session_state[f'selected_{key_proveedor}']:
                            oc_data = df_aprobables[df_aprobables['oc_id'] == oc_id].iloc[0]
                            activity_id = oc_data.get('actividad_id')
                            success, msg = rechazar_oc(models, uid, username, password, oc_id, motivo, activity_id)
                            resultados.append((oc_data['oc_name'], success, msg))
                        
                        for oc_name, success, msg in resultados:
                            if success:
                                st.info(f"{oc_name}: {msg}")
                            else:
                                st.error(f"{oc_name}: {msg}")
                        
                        st.session_state[f'mostrar_motivo_rechazo_{key_proveedor}'] = False
                        obtener_ocs_fletes_con_aprobaciones.clear()
                        time.sleep(1)
                        st.rerun(scope="app")
            with col_cancelar:
                if st.button("❌ Cancelar", key=f"cancelar_rechazo_{key_proveedor}"):
                    st.session_state[f'mostrar_motivo_rechazo_{key_proveedor}'] = False
                    st.rerun()
    
    # Ejecutar el fragment
    _fragment_seleccion()


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
        n_pendientes = len(df_proveedor[df_proveedor['num_aprobaciones'] < 2])
        
        # Header del proveedor con métricas
        header_text = f"🏢 **{proveedor}** | {n_ocs} OCs | ${total_monto_proveedor:,.0f}"
        if n_pendientes > 0:
            header_text += f" | ⏳ {n_pendientes} pendientes"
        
        with st.expander(header_text, expanded=len(proveedores_seleccionados) > 0):
            # Llamar al fragmento que renderiza la tabla del proveedor
            render_proveedor_table(proveedor, df_proveedor, models, uid, username, password)
    
    st.markdown("---")
    
    # Leyenda
    st.caption("🔴 0/2 = Sin aprobaciones | 🟡 1/2 = Una aprobación | 🟢 2/2 = Completamente aprobada")
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
        
        # Key único para esta OC basado en índice o actividad_id
        key_suffix = f"{row['actividad_id']}" if pd.notna(row.get('actividad_id')) else f"oc_{row['oc_id']}_{idx}"
        
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
                - **Estado Aprobación:** {row['estado_aprobacion']} ({row['estado_aprobacion_num']})
                - **Aprobadores:** {row['aprobadores']}
                - **Actividad Asignada:** {row.get('actividad_usuario', 'N/A')}
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
                
                # Solo mostrar botones si no está completamente aprobada
                if row['num_aprobaciones'] < 2 and row['estado_oc'] != 'purchase':
                    # Botón aprobar
                    if st.button(f"✅ Aprobar", key=f"aprobar_flete_{key_suffix}", type="primary"):
                        with st.spinner("Aprobando..."):
                            exito, mensaje = aprobar_oc(models, uid, username, password, row['oc_id'], row.get('actividad_id'))
                            if exito:
                                st.success(f"✅ {row['oc_name']} aprobada por {username}")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ Error: {mensaje}")
                    
                    # Botón rechazar
                    with st.form(key=f"form_rechazar_flete_{key_suffix}"):
                        motivo = st.text_area("Motivo del rechazo:", key=f"motivo_flete_{key_suffix}")
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
                else:
                    if row['estado_oc'] == 'purchase' or row['num_aprobaciones'] >= 2:
                        st.success("✅ OC completamente aprobada")
                    else:
                        st.info("ℹ️ Esta OC ya no requiere más aprobaciones")

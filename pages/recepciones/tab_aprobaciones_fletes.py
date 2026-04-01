"""
Tab de Aprobaciones de Fletes - Exclusivo para área TRANSPORTES/SERVICIOS
Muestra únicamente OCs de FLETES/TRANSPORTES pendientes de aprobación
Integrado con sistema de logística para comparación de presupuestos
"""

import streamlit as st
import pandas as pd
import xmlrpc.client
from datetime import datetime, timedelta
import time
import requests
import json
from typing import Dict, List, Optional
import altair as alt


URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
API_LOGISTICA_COSTES = 'https://riofuturoprocesos.com/api/logistica/db/coste-rutas'
API_BACKEND_RUTAS = 'https://riofuturoprocesos.com/api/v1/aprobaciones-fletes/rutas-por-ocs'
API_BACKEND_ANALISIS = 'https://riofuturoprocesos.com/api/v1/aprobaciones-fletes/analisis-fletes'
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
def obtener_rutas_para_ocs(oc_names: tuple) -> Dict[str, Dict]:
    """
    Obtiene rutas cruzadas para una lista de OCs desde el backend.
    El backend hace: OC → RT → ruta (con fallback a backup si faltan).
    
    Args:
        oc_names: Tupla de nombres de OC (tuple para que sea hasheable para cache)
        
    Returns:
        Dict mapeando OC name → ruta data
    """
    if not oc_names:
        return {}
    
    try:
        # Llamar al backend con body JSON (evita límite de URL)
        payload = {'oc_names': list(oc_names), 'incluir_metadata': False}
        response = requests.post(API_BACKEND_RUTAS, json=payload, timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {})
        else:
            st.warning(f"Error al obtener rutas del backend: {response.status_code}")
            return {}
    except Exception as e:
        st.warning(f"No se pudo conectar al backend para obtener rutas: {e}")
        return {}


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


def buscar_ruta_en_logistica(oc_name: str, rutas_por_oc: Dict[str, Dict]) -> Optional[Dict]:
    """
    Buscar ruta en el mapa precargado OC→ruta.
    El mapa viene del backend que ya hizo el cruce OC→RT→ruta con fallback.
    """
    if not oc_name:
        return None
    
    return rutas_por_oc.get(oc_name.strip())


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
                ('rule_id', 'in', [144, 120])
            ]],
            {'fields': ['res_id', 'user_id', 'rule_id', 'create_date', 'approved']}
        )
        
        # Nombres de reglas hardcodeados (evita leer studio.approval.rule que requiere permisos admin)
        reglas_aprobacion = {
            144: 'Aprobación Transportes 1',
            120: 'Aprobación Transportes 2'
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
                ('rule_id', 'in', [144, 120]),
                ('approved', '=', True)
            ]],
            {'fields': ['user_id', 'rule_id', 'create_date']}
        )
        
        # Nombres de reglas hardcodeados (evita leer studio.approval.rule que requiere permisos admin)
        reglas_aprobacion = {
            144: 'Aprobación Transportes 1',
            120: 'Aprobación Transportes 2'
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
            rule_id = 120
            rol_usuario = 'Gerente de Control de gestión'
        else:
            # Usuario no configurado, usar regla por defecto
            rule_id = 144
            rol_usuario = 'Gerente de procesos'
        
        # 2. Obtener nombre y estado de la OC para mensajes
        try:
            oc_data = models.execute_kw(
                DB, uid, password,
                'purchase.order', 'read',
                [[int(oc_id)]],
                {'fields': ['name', 'state'], 'context': contexto}
            )
            if not oc_data:
                return False, f"❌ OC#{oc_id}: No se encontró la orden de compra"
            
            oc_name = oc_data[0]['name']
            oc_state = oc_data[0]['state']
        except Exception as e:
            return False, f"❌ OC#{oc_id}: Error al leer orden de compra: {str(e)}"
        
        # 3. Verificar entradas existentes del usuario (aprobadas O rechazadas)
        mi_entrada = models.execute_kw(
            DB, uid, password,
            'studio.approval.entry', 'search_read',
            [[('res_id', '=', int(oc_id)), ('rule_id', '=', rule_id), ('user_id', '=', int(uid))]],
            {'fields': ['id', 'approved'], 'context': contexto}
        )
        
        if mi_entrada:
            if mi_entrada[0]['approved']:
                return False, f"✅ {oc_name}: Ya aprobado como {rol_usuario}"
            else:
                # Tiene un rechazo previo → sobrescribir con aprobación
                # Primero verificar que el registro aún exista
                try:
                    entrada_existe = models.execute_kw(
                        DB, uid, password,
                        'studio.approval.entry', 'search_count',
                        [[('id', '=', mi_entrada[0]['id'])]]
                    )
                    if entrada_existe == 0:
                        return False, f"❌ {oc_name}: La entrada de aprobación ya no existe. Recarga la página."
                    
                    models.execute_kw(
                        DB, uid, password,
                        'studio.approval.entry', 'write',
                        [[mi_entrada[0]['id']], {'approved': True}]
                    )
                except Exception as e:
                    return False, f"❌ {oc_name}: Error al actualizar aprobación: {str(e)}"
        else:
            # No tiene entrada → crear nueva aprobación
            try:
                models.execute_kw(
                    DB, uid, password,
                    'studio.approval.entry', 'create',
                    [{
                        'res_id': int(oc_id),
                        'rule_id': rule_id,
                        'user_id': int(uid),
                        'approved': True
                    }],
                    {'context': contexto}
                )
            except Exception as e:
                return False, f"❌ {oc_name}: Error al crear aprobación: {str(e)}"
        
        # Contar aprobaciones totales (de todos los usuarios)
        aprobaciones_existentes = models.execute_kw(
            DB, uid, password,
            'studio.approval.entry', 'search_read',
            [[('res_id', '=', int(oc_id)), ('rule_id', 'in', [144, 120]), ('approved', '=', True)]],
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
            [[('res_id', '=', int(oc_id)), ('rule_id', 'in', [144, 120]), ('user_id', '=', int(uid))]]
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
            rule_id = 120
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
    
    # Inicializar estado de vista (principal o analisis)
    if 'vista_aprobaciones_fletes' not in st.session_state:
        st.session_state.vista_aprobaciones_fletes = 'principal'
    
    # Si estamos en vista de análisis, renderizar esa vista
    if st.session_state.vista_aprobaciones_fletes == 'analisis':
        render_vista_analisis(username, password)
        return
    
    # ========== VISTA PRINCIPAL ==========
    
    # Header con botón de análisis
    col_header, col_analisis = st.columns([4, 1])
    with col_header:
        st.header("🚚 Aprobaciones de Fletes y Transportes")
    with col_analisis:
        if st.button("📊 Análisis", key="btn_ir_analisis", help="Ver análisis financiero"):
            st.session_state.vista_aprobaciones_fletes = 'analisis'
            st.rerun()
    
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
            # Limpiar caché específico de fletes y general
            obtener_ocs_fletes_con_aprobaciones.clear()
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
    
    # Obtener todas las OCs de fletes con información de aprobaciones PRIMERO
    with st.spinner("Cargando OCs de fletes..."):
        ocs_fletes = obtener_ocs_fletes_con_aprobaciones(models, uid, username, password)
        
        if not ocs_fletes:
            st.success("✅ No hay OCs de FLETES en proceso de aprobación")
            return
    
    # Obtener datos de logística y tipo de cambio
    with st.spinner("Cargando datos de logística..."):
        # Extraer nombres de OC para buscar rutas
        oc_names = tuple(oc['name'] for oc in ocs_fletes if oc.get('name'))
        
        # Obtener rutas cruzadas desde backend (hace el fallback automático)
        rutas_por_oc = obtener_rutas_para_ocs(oc_names)
        costes_rutas = obtener_costes_rutas()
        tipo_cambio_usd = get_tipo_cambio()
        
        info_tc = f" | 💱 USD: ${tipo_cambio_usd:,.0f}" if tipo_cambio_usd else " | ⚠️ Sin TC"
        st.caption(f"✅ {len(rutas_por_oc)} rutas vinculadas de {len(oc_names)} OCs | {len(costes_rutas)} presupuestos{info_tc}")
    
    # Enriquecer con info de logística y crear DataFrame
    datos_completos = []
    for oc in ocs_fletes:
        proveedor = oc['partner_id'][1] if oc.get('partner_id') and isinstance(oc['partner_id'], (list, tuple)) else 'N/A'
        area = oc.get('x_studio_selection_field_yUNPd')
        if area and isinstance(area, (list, tuple)):
            area = area[1]
        
        # Buscar ruta en el mapa precargado OC→ruta
        ruta_info = buscar_ruta_en_logistica(oc['name'], rutas_por_oc)
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
        # Pendientes = num_aprobaciones < 2 Y NO estado purchase (ya aprobadas en Odoo)
        pendientes = len(df[(df['num_aprobaciones'] < 2) & (df['estado_oc'] != 'purchase')])
        st.metric("Pendientes", pendientes, delta=f"-{pendientes}" if pendientes > 0 else "0")
    
    with col4:
        con_1_aprob = len(df[(df['num_aprobaciones'] == 1) & (df['estado_oc'] != 'purchase')])
        st.metric("Con 1 Aprob.", con_1_aprob)
    
    with col5:
        aprobadas = len(df[(df['num_aprobaciones'] >= 2) | (df['estado_oc'] == 'purchase')])
        st.metric("Aprobadas (2/2)", aprobadas)
    
    with col6:
        # Promedio de costo por kg en USD
        # IMPORTANTE: NO usar cost_per_kg_usd de la ruta (viene mal calculado si OC tiene qty=1)
        # Recalcular usando: monto (CLP) / tipo_cambio / total_qnt_ruta (kg reales de logística)
        if 'monto' in df.columns and 'total_qnt_ruta' in df.columns:
            # Filtrar: OCs con kg reales desde logística > 0
            df_con_kg = df[
                (df['total_qnt_ruta'].notna()) &
                (df['total_qnt_ruta'] > 0) &
                (df['monto'].notna()) &
                (df['monto'] > 0)
            ].copy()
            
            # DEBUG: Ver qué valores hay
            st.caption(f"DEBUG: {len(df_con_kg)} OCs con kg | TC: {tipo_cambio_usd}")
            if len(df_con_kg) > 0:
                sample = df_con_kg[['oc_name', 'monto', 'total_qnt_ruta']].head(3)
                st.caption(f"Muestra: {sample.to_dict('records')}")
            
            if len(df_con_kg) > 0 and tipo_cambio_usd and tipo_cambio_usd > 0:
                # Calcular costo real por kg: monto_usd / kg_reales
                df_con_kg['costo_kg_real_usd'] = (df_con_kg['monto'] / tipo_cambio_usd) / df_con_kg['total_qnt_ruta']
                prom_costo_kg_usd = df_con_kg['costo_kg_real_usd'].mean()
                delta_vs_umbral = ((prom_costo_kg_usd - UMBRAL_COSTO_KG_USD) / UMBRAL_COSTO_KG_USD) * 100
                st.metric(
                    "Prom. $/Kg USD", 
                    f"${prom_costo_kg_usd:.3f}",
                    delta=f"{delta_vs_umbral:+.1f}% vs $0.11",
                    delta_color="inverse"  # Verde si es negativo (mejor), rojo si es positivo (peor)
                )
            else:
                st.metric("Prom. $/Kg USD", "⚠️ Sin rutas con kg")
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
    # IMPORTANTE: excluir OCs con estado 'purchase' de filtros pendientes,
    # ya que pueden tener num_aprobaciones < 2 pero ya estar aprobadas en Odoo
    if filtro_aprobacion == 'Pendientes (0/2 y 1/2)':
        df_filtrado = df_filtrado[(df_filtrado['num_aprobaciones'] < 2) & (df_filtrado['estado_oc'] != 'purchase')]
    elif filtro_aprobacion == 'Sin aprobar (0/2)':
        df_filtrado = df_filtrado[(df_filtrado['num_aprobaciones'] == 0) & (df_filtrado['estado_oc'] != 'purchase')]
    elif filtro_aprobacion == 'Con 1 aprob. (1/2)':
        df_filtrado = df_filtrado[(df_filtrado['num_aprobaciones'] == 1) & (df_filtrado['estado_oc'] != 'purchase')]
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
    
    # Limpiar OCs seleccionadas que ya no están en df_aprobables (aprobadas o filtradas)
    ocs_actuales = set(df_aprobables['oc_id'].tolist())
    ocs_seleccionadas_antiguas = st.session_state[f'selected_{key_proveedor}']
    ocs_a_remover = ocs_seleccionadas_antiguas - ocs_actuales
    if ocs_a_remover:
        st.session_state[f'selected_{key_proveedor}'] = ocs_seleccionadas_antiguas & ocs_actuales
        st.session_state[f'checkbox_version_{key_proveedor}'] += 1

    # No escribir directamente sobre la key del checkbox "Seleccionar todas"
    # después de su instanciación. El estado se actualiza desde su callback.
    
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
        col_sel_h, col_oc_h, col_ruta_h, col_fecha_h, col_monto_h, col_kg_h, col_km_h, col_ppto_h, col_aprob_h, col_aprobadores_h, col_detalle_h = st.columns([0.35, 1.0, 0.6, 0.75, 0.8, 0.6, 0.6, 0.6, 0.8, 1.0, 0.7])
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
        with col_aprobadores_h:
            st.markdown("**Aprobadores**")
        with col_detalle_h:
            st.markdown("**Detalle**")
        
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
                col_sel, col_oc, col_ruta, col_fecha, col_monto, col_kg, col_km, col_ppto, col_aprob, col_aprobadores, col_detalle = st.columns([0.35, 1.0, 0.6, 0.75, 0.8, 0.6, 0.6, 0.6, 0.8, 1.0, 0.7])
                
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
                    st.text(f"{_row['estado_aprobacion']}")

                with col_aprobadores:
                    aprobadores_preview = _row['aprobadores'] if isinstance(_row['aprobadores'], str) else ''
                    if len(aprobadores_preview) > 18:
                        aprobadores_preview = f"{aprobadores_preview[:18]}…"
                    st.text(aprobadores_preview)

                detalle_key = f"detalle_visible_{key_proveedor}_{_row['oc_id']}"
                if detalle_key not in st.session_state:
                    st.session_state[detalle_key] = False

                with col_detalle:
                    label_detalle = "Ocultar" if st.session_state[detalle_key] else "Detalles"
                    if st.button(label_detalle, key=f"btn_{detalle_key}", use_container_width=True):
                        st.session_state[detalle_key] = not st.session_state[detalle_key]

                # Detalle expandido para ocupar ancho completo
                if st.session_state[detalle_key]:
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
                
                st.divider()
        if st.session_state[f'selected_{key_proveedor}']:
            st.markdown("---")
            
            ocs_seleccionadas = df_aprobables[df_aprobables['oc_id'].isin(st.session_state[f'selected_{key_proveedor}'])]
            total_sel = ocs_seleccionadas['monto'].sum()
            
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                st.markdown(f"**💰 Total: ${total_sel:,.0f}**")
            
            with col2:
                if st.button(f"✅ Aprobar", key=f"aprobar_{key_proveedor}", type="primary"):
                    # Copiar datos de OCs seleccionadas ANTES de procesar
                    ocs_a_procesar = []
                    for oc_id in st.session_state[f'selected_{key_proveedor}']:
                        oc_filtrada = df_aprobables[df_aprobables['oc_id'] == oc_id]
                        if not oc_filtrada.empty:
                            oc_data = oc_filtrada.iloc[0]
                            ocs_a_procesar.append({
                                'oc_id': oc_id,
                                'oc_name': oc_data['oc_name'],
                                'activity_id': oc_data.get('actividad_id')
                            })
                    
                    # Limpiar selección ANTES de empezar a aprobar
                    st.session_state[f'selected_{key_proveedor}'] = set()
                    st.session_state[f'checkbox_version_{key_proveedor}'] = st.session_state.get(f'checkbox_version_{key_proveedor}', 0) + 1
                    
                    with st.spinner("Aprobando..."):
                        resultados = []
                        for oc in ocs_a_procesar:
                            success, msg = aprobar_oc(models, uid, username, password, oc['oc_id'], oc['activity_id'])
                            resultados.append((oc['oc_name'], success, msg))
                        
                        for oc_name, success, msg in resultados:
                            if success:
                                st.success(f"{oc_name}: {msg}")
                            else:
                                st.error(f"{oc_name}: {msg}")
                        
                        # Limpiar caché y recargar
                        obtener_ocs_fletes_con_aprobaciones.clear()
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun(scope="app")
            
            with col3:
                if st.button(f"🔄 Quitar aprobación", key=f"quitar_{key_proveedor}"):
                    # Copiar datos de OCs seleccionadas ANTES de procesar
                    ocs_a_procesar = []
                    for oc_id in st.session_state[f'selected_{key_proveedor}']:
                        oc_filtrada = df_aprobables[df_aprobables['oc_id'] == oc_id]
                        if not oc_filtrada.empty:
                            oc_data = oc_filtrada.iloc[0]
                            ocs_a_procesar.append({
                                'oc_id': oc_id,
                                'oc_name': oc_data['oc_name']
                            })
                    
                    # Limpiar selección ANTES de empezar a procesar
                    st.session_state[f'selected_{key_proveedor}'] = set()
                    st.session_state[f'checkbox_version_{key_proveedor}'] = st.session_state.get(f'checkbox_version_{key_proveedor}', 0) + 1
                    
                    with st.spinner("Quitando aprobaciones..."):
                        resultados = []
                        for oc in ocs_a_procesar:
                            success, msg = quitar_aprobacion(models, uid, password, oc['oc_id'])
                            resultados.append((oc['oc_name'], success, msg))
                        
                        for oc_name, success, msg in resultados:
                            if success:
                                st.success(f"{oc_name}: {msg}")
                            else:
                                st.warning(f"{oc_name}: {msg}")
                        
                        # Limpiar caché y recargar
                        obtener_ocs_fletes_con_aprobaciones.clear()
                        st.cache_data.clear()
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
                    # Copiar datos de OCs seleccionadas ANTES de procesar
                    ocs_a_procesar = []
                    for oc_id in st.session_state[f'selected_{key_proveedor}']:
                        oc_filtrada = df_aprobables[df_aprobables['oc_id'] == oc_id]
                        if not oc_filtrada.empty:
                            oc_data = oc_filtrada.iloc[0]
                            ocs_a_procesar.append({
                                'oc_id': oc_id,
                                'oc_name': oc_data['oc_name'],
                                'activity_id': oc_data.get('actividad_id')
                            })
                    
                    # Limpiar selección ANTES de empezar a rechazar
                    st.session_state[f'selected_{key_proveedor}'] = set()
                    st.session_state[f'checkbox_version_{key_proveedor}'] = st.session_state.get(f'checkbox_version_{key_proveedor}', 0) + 1
                    
                    with st.spinner("Rechazando..."):
                        resultados = []
                        for oc in ocs_a_procesar:
                            success, msg = rechazar_oc(models, uid, username, password, oc['oc_id'], motivo, oc['activity_id'])
                            resultados.append((oc['oc_name'], success, msg))
                        
                        for oc_name, success, msg in resultados:
                            if success:
                                st.info(f"{oc_name}: {msg}")
                            else:
                                st.error(f"{oc_name}: {msg}")
                        
                        # Limpiar estado y recargar
                        st.session_state[f'mostrar_motivo_rechazo_{key_proveedor}'] = False
                        obtener_ocs_fletes_con_aprobaciones.clear()
                        st.cache_data.clear()
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
        # Pendientes = num_aprobaciones < 2 Y NO estado purchase (ya aprobadas en Odoo)
        n_pendientes = len(df_proveedor[(df_proveedor['num_aprobaciones'] < 2) & (df_proveedor['estado_oc'] != 'purchase')])
        
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
                                # Limpiar caché específico y general
                                obtener_ocs_fletes_con_aprobaciones.clear()
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


# =============================================================================
# VISTA DE ANÁLISIS FINANCIERO
# =============================================================================

def cargar_datos_analisis(username: str, password: str, fecha_desde: str, fecha_hasta: str) -> Dict:
    """Carga datos de análisis desde el backend"""
    try:
        params = {
            'username': username,
            'password': password,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'solo_aprobadas': False,
            'incluir_facturas': True
        }
        response = requests.get(API_BACKEND_ANALISIS, params=params, timeout=120)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f"Error del servidor: {response.status_code}"}
    except requests.exceptions.Timeout:
        return {'error': "Timeout al cargar datos (120s)"}
    except Exception as e:
        return {'error': str(e)}


def render_vista_analisis(username: str, password: str):
    """Renderiza la vista de análisis financiero de fletes"""
    
    # Header con botón de volver
    col_titulo, col_volver = st.columns([4, 1])
    with col_titulo:
        st.header("📊 Análisis Financiero de Fletes")
    with col_volver:
        if st.button("← Volver", key="btn_volver_analisis", type="secondary"):
            st.session_state.vista_aprobaciones_fletes = 'principal'
            st.rerun()
    
    st.info("📈 Análisis de OCs de fletes: montos netos, IVA, facturas y estados de pago")
    
    # Inicializar datos en session_state si no existen
    if 'datos_analisis_fletes' not in st.session_state:
        st.session_state.datos_analisis_fletes = None
    if 'analisis_fecha_desde' not in st.session_state:
        st.session_state.analisis_fecha_desde = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    if 'analisis_fecha_hasta' not in st.session_state:
        st.session_state.analisis_fecha_hasta = datetime.now().strftime('%Y-%m-%d')
    
    # Controles de carga
    st.markdown("### 📅 Período de análisis")
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        fecha_desde = st.date_input(
            "Desde",
            value=datetime.strptime(st.session_state.analisis_fecha_desde, '%Y-%m-%d'),
            key="analisis_fecha_desde_input"
        )
    
    with col2:
        fecha_hasta = st.date_input(
            "Hasta",
            value=datetime.strptime(st.session_state.analisis_fecha_hasta, '%Y-%m-%d'),
            key="analisis_fecha_hasta_input"
        )
    
    with col3:
        st.write("")  # Espaciador
        st.write("")
        cargar = st.button("🔄 Cargar Datos", key="btn_cargar_analisis", type="primary")
    
    # Cargar datos si se presiona el botón
    if cargar:
        st.session_state.analisis_fecha_desde = fecha_desde.strftime('%Y-%m-%d')
        st.session_state.analisis_fecha_hasta = fecha_hasta.strftime('%Y-%m-%d')
        
        with st.spinner("Cargando datos de Odoo... (esto puede tomar unos segundos)"):
            datos = cargar_datos_analisis(
                username, password,
                st.session_state.analisis_fecha_desde,
                st.session_state.analisis_fecha_hasta
            )
            
            if 'error' in datos:
                st.error(f"❌ {datos['error']}")
                return
            
            st.session_state.datos_analisis_fletes = datos
    
    # Si no hay datos, mostrar mensaje
    if not st.session_state.datos_analisis_fletes:
        st.info("👆 Selecciona un rango de fechas y presiona 'Cargar Datos'")
        return
    
    datos = st.session_state.datos_analisis_fletes
    
    # Verificar que la respuesta sea exitosa
    if not datos.get('success'):
        st.error("❌ Error al obtener datos")
        return
    
    resumen = datos.get('resumen', {})
    ocs = datos.get('ocs', [])
    
    if not ocs:
        st.warning("No hay OCs de fletes en el período seleccionado")
        return
    
    # Crear DataFrame
    df = pd.DataFrame(ocs)
    
    # Convertir fechas
    if 'date_order' in df.columns:
        df['fecha'] = pd.to_datetime(df['date_order']).dt.date
        df['semana'] = pd.to_datetime(df['date_order']).dt.to_period('W').astype(str)
        df['mes'] = pd.to_datetime(df['date_order']).dt.to_period('M').astype(str)
    
    # Extraer nombre de proveedor
    if 'partner_id' in df.columns:
        df['proveedor'] = df['partner_id'].apply(
            lambda x: x[1] if isinstance(x, (list, tuple)) and len(x) > 1 else 'Sin proveedor'
        )
    
    # Marcar estado de facturación
    df['facturado'] = df['invoice_ids'].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)
    
    # FILTROS
    st.markdown("---")
    st.markdown("### 🔍 Filtros")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        proveedores = ['Todos'] + sorted(df['proveedor'].unique().tolist())
        filtro_proveedor = st.selectbox("Proveedor", proveedores, key="analisis_filtro_proveedor")
    
    with col_f2:
        estados = ['Todos'] + sorted(df['state'].unique().tolist())
        filtro_estado = st.selectbox("Estado OC", estados, key="analisis_filtro_estado")
    
    with col_f3:
        filtro_factura = st.selectbox(
            "Facturación",
            ['Todas', 'Facturadas', 'Sin facturar'],
            key="analisis_filtro_factura"
        )
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    if filtro_proveedor != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['proveedor'] == filtro_proveedor]
    
    if filtro_estado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['state'] == filtro_estado]
    
    if filtro_factura == 'Facturadas':
        df_filtrado = df_filtrado[df_filtrado['facturado'] == True]
    elif filtro_factura == 'Sin facturar':
        df_filtrado = df_filtrado[df_filtrado['facturado'] == False]
    
    # MÉTRICAS PRINCIPALES
    st.markdown("---")
    st.markdown("### 💰 Resumen Financiero")
    
    total_neto = df_filtrado['amount_untaxed'].sum() if 'amount_untaxed' in df_filtrado.columns else 0
    total_iva = df_filtrado['amount_tax'].sum() if 'amount_tax' in df_filtrado.columns else 0
    total_bruto = df_filtrado['amount_total'].sum() if 'amount_total' in df_filtrado.columns else 0
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.metric("Total Neto (sin IVA)", f"${total_neto:,.0f}")
    
    with col_m2:
        st.metric("IVA (19%)", f"${total_iva:,.0f}")
    
    with col_m3:
        st.metric("Total Bruto", f"${total_bruto:,.0f}")
    
    with col_m4:
        st.metric("Cantidad OCs", len(df_filtrado))
    
    # Estado de OCs y facturas
    st.markdown("### 📋 Estado de OCs")
    
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    
    confirmadas = len(df_filtrado[df_filtrado['state'] == 'purchase'])
    borrador = len(df_filtrado[df_filtrado['state'].isin(['draft', 'sent', 'to approve'])])
    facturadas = len(df_filtrado[df_filtrado['facturado'] == True])
    sin_facturar = len(df_filtrado[df_filtrado['facturado'] == False])
    
    with col_e1:
        st.metric("✅ Confirmadas", confirmadas)
    
    with col_e2:
        st.metric("📝 En proceso", borrador)
    
    with col_e3:
        st.metric("📄 Facturadas", facturadas)
    
    with col_e4:
        st.metric("⏳ Sin facturar", sin_facturar)
    
    # GRÁFICOS
    st.markdown("---")
    st.markdown("### 📈 Gráficos")
    
    tab_graf1, tab_graf2, tab_graf3 = st.tabs(["📅 Por Semana", "🏢 Por Proveedor", "📊 Estados"])
    
    with tab_graf1:
        if 'semana' in df_filtrado.columns:
            df_semana = df_filtrado.groupby('semana').agg({
                'amount_untaxed': 'sum',
                'amount_total': 'sum',
                'name': 'count'
            }).reset_index()
            df_semana.columns = ['Semana', 'Neto', 'Total', 'Cantidad']
            
            # Preparar datos para Altair (formato largo)
            df_semana_long = df_semana.melt(
                id_vars=['Semana'], 
                value_vars=['Neto', 'Total'],
                var_name='Tipo', 
                value_name='Monto'
            )
            
            chart = alt.Chart(df_semana_long).mark_bar().encode(
                x=alt.X('Semana:N', axis=alt.Axis(labelAngle=-45, labelFontSize=12, titleFontSize=14)),
                y=alt.Y('Monto:Q', axis=alt.Axis(labelFontSize=12, titleFontSize=14, format='~s')),
                color=alt.Color('Tipo:N', scale=alt.Scale(scheme='blues')),
                xOffset='Tipo:N'
            ).properties(
                height=400
            ).configure_axis(
                labelFontSize=12,
                titleFontSize=14
            ).configure_legend(
                labelFontSize=12,
                titleFontSize=14
            )
            
            st.altair_chart(chart, use_container_width=True)
            
            with st.expander("Ver datos por semana"):
                df_semana_fmt = df_semana.copy()
                df_semana_fmt['Neto'] = df_semana_fmt['Neto'].apply(lambda x: f"${x:,.0f}")
                df_semana_fmt['Total'] = df_semana_fmt['Total'].apply(lambda x: f"${x:,.0f}")
                st.dataframe(df_semana_fmt, use_container_width=True)
    
    with tab_graf2:
        df_proveedor = df_filtrado.groupby('proveedor').agg({
            'amount_untaxed': 'sum',
            'amount_total': 'sum',
            'name': 'count'
        }).reset_index()
        df_proveedor.columns = ['Proveedor', 'Neto', 'Total', 'Cantidad']
        df_proveedor = df_proveedor.sort_values('Total', ascending=False).head(15)
        
        chart_prov = alt.Chart(df_proveedor).mark_bar().encode(
            x=alt.X('Total:Q', axis=alt.Axis(labelFontSize=12, titleFontSize=14, format='~s'), title='Monto Total'),
            y=alt.Y('Proveedor:N', sort='-x', axis=alt.Axis(labelFontSize=11, titleFontSize=14)),
            color=alt.value('#1f77b4')
        ).properties(
            height=400
        )
        
        st.altair_chart(chart_prov, use_container_width=True)
        
        with st.expander("Ver datos por proveedor"):
            df_prov_fmt = df_proveedor.copy()
            df_prov_fmt['Neto'] = df_prov_fmt['Neto'].apply(lambda x: f"${x:,.0f}")
            df_prov_fmt['Total'] = df_prov_fmt['Total'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(df_prov_fmt, use_container_width=True)
    
    with tab_graf3:
        # Gráfico de estados
        df_estado = df_filtrado.groupby('state').agg({
            'amount_total': 'sum',
            'name': 'count'
        }).reset_index()
        df_estado.columns = ['Estado', 'Monto', 'Cantidad']
        
        # Traducir estados
        estado_map = {
            'draft': 'Borrador',
            'sent': 'Enviado',
            'to approve': 'Por aprobar',
            'purchase': 'Confirmada',
            'done': 'Completada',
            'cancel': 'Cancelada'
        }
        df_estado['Estado'] = df_estado['Estado'].map(estado_map).fillna(df_estado['Estado'])
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("**Por cantidad**")
            chart_cant = alt.Chart(df_estado).mark_bar().encode(
                x=alt.X('Estado:N', axis=alt.Axis(labelAngle=-45, labelFontSize=11, titleFontSize=13)),
                y=alt.Y('Cantidad:Q', axis=alt.Axis(labelFontSize=11, titleFontSize=13)),
                color=alt.value('#2ca02c')
            ).properties(height=300)
            st.altair_chart(chart_cant, use_container_width=True)
        
        with col_g2:
            st.markdown("**Por monto**")
            chart_monto = alt.Chart(df_estado).mark_bar().encode(
                x=alt.X('Estado:N', axis=alt.Axis(labelAngle=-45, labelFontSize=11, titleFontSize=13)),
                y=alt.Y('Monto:Q', axis=alt.Axis(labelFontSize=11, titleFontSize=13, format='~s')),
                color=alt.value('#1f77b4')
            ).properties(height=300)
            st.altair_chart(chart_monto, use_container_width=True)
    
    # TABLA DE DETALLE
    st.markdown("---")
    st.markdown("### 📋 Detalle de OCs")
    
    # Preparar tabla
    cols_mostrar = ['name', 'proveedor', 'fecha', 'amount_untaxed', 'amount_tax', 'amount_total', 'state', 'facturado']
    cols_disponibles = [c for c in cols_mostrar if c in df_filtrado.columns]
    
    df_tabla = df_filtrado[cols_disponibles].copy()
    
    # Renombrar columnas
    rename_map = {
        'name': 'OC',
        'proveedor': 'Proveedor',
        'fecha': 'Fecha',
        'amount_untaxed': 'Neto',
        'amount_tax': 'IVA',
        'amount_total': 'Total',
        'state': 'Estado',
        'facturado': 'Facturada'
    }
    df_tabla = df_tabla.rename(columns={k: v for k, v in rename_map.items() if k in df_tabla.columns})
    
    # Formatear montos
    for col in ['Neto', 'IVA', 'Total']:
        if col in df_tabla.columns:
            df_tabla[col] = df_tabla[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "$0")
    
    # Formato estado
    if 'Estado' in df_tabla.columns:
        df_tabla['Estado'] = df_tabla['Estado'].map(estado_map).fillna(df_tabla['Estado'])
    
    # Formato facturada
    if 'Facturada' in df_tabla.columns:
        df_tabla['Facturada'] = df_tabla['Facturada'].apply(lambda x: '✅' if x else '❌')
    
    st.dataframe(df_tabla, use_container_width=True, height=400)
    
    # Botón para descargar
    csv = df_filtrado.to_csv(index=False)
    st.download_button(
        label="📥 Descargar CSV",
        data=csv,
        file_name=f"analisis_fletes_{st.session_state.analisis_fecha_desde}_{st.session_state.analisis_fecha_hasta}.csv",
        mime="text/csv"
    )

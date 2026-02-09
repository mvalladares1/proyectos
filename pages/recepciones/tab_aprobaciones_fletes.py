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
        
        # OPTIMIZACIÓN 3: Obtener mensajes de aprobación en lote
        todos_mensajes = _models.execute_kw(
            DB, _uid, password,
            'mail.message', 'search_read',
            [[
                ('model', '=', 'purchase.order'),
                ('res_id', 'in', oc_ids),
                ('body', 'ilike', 'Aprobado como')
            ]],
            {'fields': ['res_id', 'body', 'author_id', 'date', 'create_date'], 'order': 'date desc'}
        )
        
        # Agrupar mensajes por OC
        mensajes_por_oc = {}
        for msg in todos_mensajes:
            oc_id = msg['res_id']
            if oc_id not in mensajes_por_oc:
                mensajes_por_oc[oc_id] = []
            mensajes_por_oc[oc_id].append(msg)
        
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
            
            # Aprobaciones desde mensajes
            mensajes_oc = mensajes_por_oc.get(oc_id, [])
            aprobaciones = []
            for msg in mensajes_oc:
                autor = msg.get('author_id')
                if autor and isinstance(autor, (list, tuple)):
                    nombre_usuario = autor[1]
                else:
                    nombre_usuario = 'Desconocido'
                
                body = msg.get('body', '')
                rol = 'Aprobador'
                if 'Aprobado como' in body:
                    try:
                        import re
                        match = re.search(r'Aprobado como ([^<]+)', body)
                        if match:
                            rol = match.group(1).strip()
                    except:
                        pass
                
                aprobaciones.append({
                    'usuario': nombre_usuario,
                    'rol': rol,
                    'fecha': msg.get('date') or msg.get('create_date')
                })
            
            oc['aprobaciones'] = aprobaciones
            oc['num_aprobaciones'] = len(aprobaciones)
            oc['aprobadores'] = [a['usuario'] for a in aprobaciones]
            
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
    Obtener las aprobaciones de una OC leyendo el chatter (mail.message).
    Busca mensajes que contengan "Aprobado como" para detectar aprobaciones.
    """
    try:
        # Buscar mensajes en el chatter de la OC
        mensajes = _models.execute_kw(
            DB, _uid, password,
            'mail.message', 'search_read',
            [[
                ('model', '=', 'purchase.order'),
                ('res_id', '=', oc_id),
                ('body', 'ilike', 'Aprobado como')
            ]],
            {'fields': ['body', 'author_id', 'date', 'create_date'], 'order': 'date desc'}
        )
        
        aprobaciones = []
        for msg in mensajes:
            autor = msg.get('author_id')
            if autor and isinstance(autor, (list, tuple)):
                nombre_usuario = autor[1]
            else:
                nombre_usuario = 'Desconocido'
            
            # Extraer el rol de aprobación del body (ej: "Aprobado como Aprobaciones / Finanzas")
            body = msg.get('body', '')
            rol = 'Aprobador'
            if 'Aprobado como' in body:
                try:
                    # El formato típico es: "Aprobado como Rol / SubRol"
                    import re
                    match = re.search(r'Aprobado como ([^<]+)', body)
                    if match:
                        rol = match.group(1).strip()
                except:
                    pass
            
            aprobaciones.append({
                'usuario': nombre_usuario,
                'rol': rol,
                'fecha': msg.get('date') or msg.get('create_date')
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
        # 1. Verificar cuántas aprobaciones tiene actualmente esta OC para la regla 144
        aprobaciones_existentes = models.execute_kw(
            DB, uid, password,
            'studio.approval.entry', 'search_read',
            [[('res_id', '=', int(oc_id)), ('rule_id', '=', 144), ('approved', '=', True)]],
            {'fields': ['id', 'user_id']}
        )
        
        # Si el usuario actual ya aprobó, no hacer nada
        if any(aprobacion['user_id'][0] == uid for aprobacion in aprobaciones_existentes if aprobacion.get('user_id')):
            return False, "Ya aprobaste esta OC anteriormente"
        
        # 2. Crear la entrada de aprobación en Studio
        # Esto registra que el usuario actual ha aprobado según la regla 144
        models.execute_kw(
            DB, uid, password,
            'studio.approval.entry', 'create',
            [{
                'res_id': int(oc_id),
                'rule_id': 144,  # ID de la regla de aprobación para TRANSPORTES
                'user_id': int(uid),
                'approved': True
            }]
        )
        
        # 3. Si hay actividad pendiente, completarla para limpieza visual
        if activity_id is not None and pd.notna(activity_id):
            try:
                models.execute_kw(
                    DB, uid, password,
                    'mail.activity', 'action_feedback',
                    [[int(activity_id)]],
                    {'feedback': 'Aprobado desde dashboard'}
                )
            except:
                pass
        
        # 4. Determinar qué hacer según el número de aprobaciones
        num_aprobaciones = len(aprobaciones_existentes) + 1
        
        if num_aprobaciones >= 2:
            # Ya están las 2 aprobaciones - confirmar la orden
            try:
                models.execute_kw(
                    DB, uid, password,
                    'purchase.order', 'button_confirm',
                    [[int(oc_id)]]
                )
                return True, f"✅ Segunda aprobación - Orden confirmada"
            except Exception as e:
                return True, f"✅ Segunda aprobación registrada (error al confirmar: {str(e)[:80]})"
        else:
            # Primera aprobación - NO confirmar, solo notificar
            # La actividad para el segundo aprobador debe crearse manualmente o mediante reglas de Studio
            return True, f"✅ Primera aprobación registrada - Pendiente segunda aprobación (1/2)"
        
    except Exception as e:
        return False, str(e)


def quitar_aprobacion(models, uid, password, oc_id):
    """Quitar la aprobación del usuario actual de una OC"""
    try:
        # Buscar la aprobación del usuario actual para esta OC
        aprobaciones = models.execute_kw(
            DB, uid, password,
            'studio.approval.entry', 'search',
            [[('res_id', '=', int(oc_id)), ('rule_id', '=', 144), ('user_id', '=', int(uid)), ('approved', '=', True)]]
        )
        
        if not aprobaciones:
            return False, "No tienes aprobación registrada para esta OC"
        
        # Eliminar la aprobación
        models.execute_kw(
            DB, uid, password,
            'studio.approval.entry', 'unlink',
            [aprobaciones]
        )
        
        return True, "Aprobación eliminada correctamente"
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
        tipo_cambio_usd = obtener_tipo_cambio_usd()
        
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
        if oc['state'] == 'purchase':
            estado_aprobacion = '🟢 Aprobada'
            estado_aprobacion_num = '2/2'
        elif num_aprob >= 2:
            estado_aprobacion = '🟢 2/2'
            estado_aprobacion_num = '2/2'
        elif num_aprob == 1:
            estado_aprobacion = '🟡 1/2'
            estado_aprobacion_num = '1/2'
        else:
            estado_aprobacion = '🔴 0/2'
            estado_aprobacion_num = '0/2'
        
        # Formatear aprobadores
        aprobadores_str = ', '.join(oc.get('aprobadores', [])) if oc.get('aprobadores') else 'Sin aprobaciones'
        
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
        n_pendientes = len(df_proveedor[df_proveedor['num_aprobaciones'] < 2])
        
        # Header del proveedor con métricas
        header_text = f"🏢 **{proveedor}** | {n_ocs} OCs | ${total_monto_proveedor:,.0f}"
        if n_pendientes > 0:
            header_text += f" | ⏳ {n_pendientes} pendientes"
        
        with st.expander(header_text, expanded=len(proveedores_seleccionados) > 0):
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
            
            # Crear dataframe para mostrar
            df_tabla_proveedor = pd.DataFrame({
                'OC': df_proveedor['oc_name'],
                'Fecha': df_proveedor['fecha_str'],
                'Monto': df_proveedor['monto'].apply(lambda x: f"${x:,.0f}"),
                'vs Ppto': df_proveedor.apply(comparar_presupuesto, axis=1),
                'Aprob.': df_proveedor['estado_aprobacion'],
                'Aprobadores': df_proveedor['aprobadores'].str[:40],
                '$/Kg USD': df_proveedor['alerta_costo_kg'].fillna(df_proveedor['cost_per_kg_usd_str']),
                'Tipo Camión': df_proveedor['tipo_camion_str'].str[:15],
                'ID': df_proveedor['actividad_id'],
                'OC_ID': df_proveedor['oc_id']
            })
            
            # Mostrar tabla del proveedor
            st.dataframe(
                df_tabla_proveedor.drop(columns=['ID', 'OC_ID']),
                use_container_width=True,
                hide_index=True,
                height=min(400, len(df_tabla_proveedor) * 40 + 40)
            )
            
            # Filtrar solo OCs que se pueden aprobar (menos de 2 aprobaciones y no completamente aprobadas)
            df_aprobables = df_proveedor[
                (df_proveedor['num_aprobaciones'] < 2) &
                (df_proveedor['estado_oc'] != 'purchase')
            ]
            
            if len(df_aprobables) == 0:
                st.caption("✅ Todas las OCs de este proveedor ya están completamente aprobadas")
                continue
            
            # Selección de OCs aprobables de este proveedor
            ocs_proveedor = []
            for _, row in df_aprobables.iterrows():
                ocs_proveedor.append({
                    'label': f"{row['oc_name']} - {row['estado_aprobacion']} - ${row['monto']:,.0f}",
                    'data': row.to_dict()
                })
            
            # Multiselect para este proveedor
            key_proveedor = f"select_{proveedor.replace(' ', '_')[:20]}"
            seleccionadas = st.multiselect(
                f"Seleccionar OCs para aprobar ({len(ocs_proveedor)} disponibles):",
                [oc['label'] for oc in ocs_proveedor],
                key=key_proveedor
            )
            
            if seleccionadas:
                ocs_sel_proveedor = [oc['data'] for oc in ocs_proveedor if oc['label'] in seleccionadas]
                total_sel = sum(oc['monto'] for oc in ocs_sel_proveedor)
                
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.caption(f"✅ {len(seleccionadas)} seleccionadas | ${total_sel:,.0f}")
                
                with col2:
                    if st.button(f"✅ Aprobar", key=f"aprobar_{key_proveedor}", type="primary"):
                        with st.spinner("Aprobando..."):
                            exitosas = 0
                            errores = []
                            for oc in ocs_sel_proveedor:
                                exito, msg = aprobar_oc(models, uid, username, password, oc['oc_id'], oc.get('actividad_id'))
                                if exito:
                                    exitosas += 1
                                else:
                                    errores.append(f"{oc['oc_name']}: {msg}")
                            
                            if exitosas > 0:
                                st.success(f"✅ {exitosas} OCs aprobadas por {username}")
                            if errores:
                                st.warning(f"⚠️ Errores: {', '.join(errores)}")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                
                with col3:
                    if st.button(f"🔙 Quitar mi aprobación", key=f"quitar_{key_proveedor}"):
                        with st.spinner("Eliminando aprobaciones..."):
                            exitosas = 0
                            errores = []
                            for oc in ocs_sel_proveedor:
                                exito, msg = quitar_aprobacion(models, uid, password, oc['oc_id'])
                                if exito:
                                    exitosas += 1
                                else:
                                    errores.append(f"{oc['oc_name']}: {msg}")
                            
                            if exitosas > 0:
                                st.success(f"🔙 {exitosas} aprobaciones eliminadas")
                            if errores:
                                st.info(f"ℹ️ {', '.join(errores)}")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                
                with col4:
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
                                    if oc.get('actividad_id'):
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

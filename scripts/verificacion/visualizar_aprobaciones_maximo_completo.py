#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualización completa de aprobaciones pendientes de Maximo para fletes
Con comparación detallada entre Odoo y área de logística
"""
import xmlrpc.client
from datetime import datetime
from collections import defaultdict

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

MAXIMO_ID = 241

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

print("\n" + "="*80)
print("VISUALIZACIÓN COMPLETA: APROBACIONES DE MAXIMO - FLETES")
print("="*80)
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 1. BUSCAR TODAS LAS ACTIVIDADES DE MAXIMO (cualquier tipo)
print("\n1. ACTIVIDADES DE MAXIMO (TODOS LOS TIPOS):")
print("-" * 80)

actividades_maximo_todas = models.execute_kw(
    DB, uid, PASSWORD,
    'mail.activity', 'search_read',
    [[
        ('user_id', '=', MAXIMO_ID),
        ('res_model', '=', 'purchase.order')
    ]],
    {'fields': ['id', 'res_id', 'res_name', 'activity_type_id', 'date_deadline', 'summary', 'state'], 'limit': 200}
)

print(f"  Total actividades de Maximo: {len(actividades_maximo_todas)}")

# Agrupar por tipo de actividad
actividades_por_tipo = defaultdict(list)
for act in actividades_maximo_todas:
    tipo = act['activity_type_id'][1] if act.get('activity_type_id') and isinstance(act['activity_type_id'], (list, tuple)) else 'Sin tipo'
    actividades_por_tipo[tipo].append(act)

print(f"\n  Actividades por tipo:")
for tipo, acts in sorted(actividades_por_tipo.items()):
    print(f"    {tipo}: {len(acts)} actividades")

# Agrupar por estado
actividades_por_estado = defaultdict(list)
for act in actividades_maximo_todas:
    estado = act.get('state', 'sin_estado')
    actividades_por_estado[estado].append(act)

print(f"\n  Actividades por estado:")
for estado, acts in sorted(actividades_por_estado.items()):
    print(f"    {estado}: {len(acts)} actividades")

# 2. BUSCAR OCs DE FLETES/TRANSPORTES
print("\n2. ÓRDENES DE COMPRA DE FLETES/TRANSPORTES:")
print("-" * 80)

ocs_servicios = models.execute_kw(
    DB, uid, PASSWORD,
    'purchase.order', 'search_read',
    [[
        ('x_studio_categora_de_producto', '=', 'SERVICIOS')
    ]],
    {'fields': ['id', 'name', 'state', 'partner_id', 'amount_total', 'x_studio_selection_field_yUNPd', 'x_studio_logistica'], 'limit': 500}
)

print(f"  Total OCs SERVICIOS: {len(ocs_servicios)}")

# Filtrar fletes
ocs_fletes = []
for oc in ocs_servicios:
    lineas = models.execute_kw(
        DB, uid, PASSWORD,
        'purchase.order.line', 'search_read',
        [[('order_id', '=', oc['id'])]],
        {'fields': ['product_id', 'name'], 'limit': 10}
    )
    
    es_flete = False
    producto_info = ""
    
    for linea in lineas:
        producto_nombre = ""
        if linea.get('product_id'):
            producto_nombre = linea['product_id'][1] if isinstance(linea['product_id'], (list, tuple)) else ''
        elif linea.get('name'):
            producto_nombre = linea['name']
        
        if producto_nombre and ('FLETE' in producto_nombre.upper() or 'TRANSPORTE' in producto_nombre.upper()):
            es_flete = True
            producto_info = producto_nombre
            break
    
    area = oc.get('x_studio_selection_field_yUNPd', '')
    if area and isinstance(area, (list, tuple)):
        area = area[1]
    
    logistica = oc.get('x_studio_logistica', '')
    
    if 'LOGISTICA' in str(area).upper() or 'LOGÍSTICA' in str(area).upper():
        es_flete = True
    
    if 'si' in str(logistica).lower() or 'yes' in str(logistica).lower():
        es_flete = True
    
    if es_flete:
        ocs_fletes.append({
            'id': oc['id'],
            'name': oc['name'],
            'state': oc['state'],
            'partner_id': oc.get('partner_id'),
            'amount_total': oc.get('amount_total', 0),
            'area': area,
            'logistica': logistica,
            'producto': producto_info
        })

print(f"  OCs FLETES identificadas: {len(ocs_fletes)}")

# Agrupar por estado
ocs_por_estado = defaultdict(list)
for oc in ocs_fletes:
    ocs_por_estado[oc['state']].append(oc)

print(f"\n  OCs de fletes por estado:")
for estado, ocs in sorted(ocs_por_estado.items()):
    total_monto = sum(oc['amount_total'] for oc in ocs)
    print(f"    {estado:15} : {len(ocs):3} OCs | ${total_monto:,.0f}")

# 3. COMPARACIÓN DETALLADA
print("\n3. COMPARACIÓN: OCs vs ACTIVIDADES DE MAXIMO:")
print("-" * 80)

# Crear mapas
actividades_por_res_id = {act['res_id']: act for act in actividades_maximo_todas}
ocs_con_actividad_maximo = []
ocs_sin_actividad_maximo = []

for oc in ocs_fletes:
    if oc['id'] in actividades_por_res_id:
        ocs_con_actividad_maximo.append({
            'oc': oc,
            'actividad': actividades_por_res_id[oc['id']]
        })
    else:
        ocs_sin_actividad_maximo.append(oc)

print(f"\n  ✓ OCs con actividad de Maximo: {len(ocs_con_actividad_maximo)}")
print(f"  ✗ OCs sin actividad de Maximo: {len(ocs_sin_actividad_maximo)}")

# 4. DETALLE DE OCs CON ACTIVIDADES DE MAXIMO
if ocs_con_actividad_maximo:
    print("\n4. OCs CON ACTIVIDAD DE MAXIMO (PENDIENTES):")
    print("-" * 80)
    
    # Ordenar por fecha límite
    ocs_con_actividad_maximo.sort(key=lambda x: x['actividad'].get('date_deadline', ''))
    
    total_monto = 0
    for item in ocs_con_actividad_maximo:
        oc = item['oc']
        act = item['actividad']
        proveedor = oc['partner_id'][1] if oc.get('partner_id') and isinstance(oc['partner_id'], (list, tuple)) else 'N/A'
        
        total_monto += oc['amount_total']
        
        print(f"\n  {oc['name']} - ${oc['amount_total']:,.0f}")
        print(f"    Estado OC: {oc['state']}")
        print(f"    Proveedor: {proveedor[:50]}")
        print(f"    Área: {oc['area']}")
        print(f"    Producto: {oc['producto'][:60] if oc['producto'] else 'N/A'}")
        
        tipo_act = act['activity_type_id'][1] if act.get('activity_type_id') and isinstance(act['activity_type_id'], (list, tuple)) else 'N/A'
        print(f"    📌 ACTIVIDAD:")
        print(f"       Tipo: {tipo_act}")
        print(f"       Estado: {act.get('state', 'N/A')}")
        print(f"       Fecha límite: {act.get('date_deadline', 'N/A')}")
        print(f"       Resumen: {act.get('summary', 'N/A')}")
    
    print(f"\n  💰 MONTO TOTAL PENDIENTE DE APROBAR: ${total_monto:,.0f}")
else:
    print("\n4. ⚠ NO HAY OCs CON ACTIVIDADES PENDIENTES DE MAXIMO")

# 5. ANÁLISIS DE OCs SIN ACTIVIDAD (si hay muchas)
if ocs_sin_actividad_maximo:
    print(f"\n5. OCs SIN ACTIVIDAD DE MAXIMO ({len(ocs_sin_actividad_maximo)}):")
    print("-" * 80)
    
    # Verificar si tienen actividades de otros
    ocs_con_otras_actividades = []
    ocs_sin_ninguna_actividad = []
    
    for oc in ocs_sin_actividad_maximo[:20]:  # Primeras 20
        acts_oc = models.execute_kw(
            DB, uid, PASSWORD,
            'mail.activity', 'search_read',
            [[
                ('res_model', '=', 'purchase.order'),
                ('res_id', '=', oc['id'])
            ]],
            {'fields': ['id', 'user_id', 'activity_type_id', 'state']}
        )
        
        if acts_oc:
            ocs_con_otras_actividades.append({'oc': oc, 'actividades': acts_oc})
        else:
            ocs_sin_ninguna_actividad.append(oc)
    
    print(f"\n  Con actividades de otros usuarios: {len(ocs_con_otras_actividades)}")
    print(f"  Sin ninguna actividad: {len(ocs_sin_ninguna_actividad)}")
    
    if ocs_con_otras_actividades:
        print(f"\n  Ejemplos con actividades de otros:")
        for item in ocs_con_otras_actividades[:5]:
            oc = item['oc']
            acts = item['actividades']
            proveedor = oc['partner_id'][1] if oc.get('partner_id') and isinstance(oc['partner_id'], (list, tuple)) else 'N/A'
            
            print(f"\n    {oc['name']} ({oc['state']}) - ${oc['amount_total']:,.0f}")
            print(f"      Proveedor: {proveedor[:40]}")
            print(f"      Actividades:")
            for a in acts:
                user = a['user_id'][1] if a.get('user_id') and isinstance(a['user_id'], (list, tuple)) else 'N/A'
                tipo = a['activity_type_id'][1] if a.get('activity_type_id') and isinstance(a['activity_type_id'], (list, tuple)) else 'N/A'
                print(f"        - {user[:30]:30} | {tipo:20} | {a.get('state', 'N/A')}")

# 6. COMPARACIÓN CON ÁREA LOGÍSTICA
print("\n6. ANÁLISIS POR ÁREA SOLICITANTE:")
print("-" * 80)

ocs_por_area = defaultdict(list)
for oc in ocs_fletes:
    area = oc.get('area', 'SIN AREA')
    ocs_por_area[str(area)].append(oc)

print(f"\n  Distribución de OCs por área:")
for area, ocs in sorted(ocs_por_area.items()):
    total_monto = sum(oc['amount_total'] for oc in ocs)
    print(f"    {area:30} : {len(ocs):3} OCs | ${total_monto:,.0f}")

# Ver cuántas de cada área tienen actividad de Maximo
print(f"\n  OCs con actividad de Maximo por área:")
for area in sorted(ocs_por_area.keys()):
    ocs_area = [oc for oc in ocs_fletes if str(oc.get('area', 'SIN AREA')) == area]
    ocs_area_con_maximo = [oc for oc in ocs_area if oc['id'] in actividades_por_res_id]
    if ocs_area:
        porcentaje = (len(ocs_area_con_maximo) / len(ocs_area)) * 100
        print(f"    {area:30} : {len(ocs_area_con_maximo):3} / {len(ocs_area):3} ({porcentaje:.1f}%)")

# 7. RESUMEN EJECUTIVO
print("\n" + "="*80)
print("RESUMEN EJECUTIVO:")
print("="*80)
print(f"  📊 Total OCs de fletes encontradas: {len(ocs_fletes)}")
print(f"  👤 Actividades asignadas a Maximo: {len(actividades_maximo_todas)}")
print(f"  ✅ OCs con actividad de Maximo: {len(ocs_con_actividad_maximo)}")
print(f"  ❌ OCs sin actividad de Maximo: {len(ocs_sin_actividad_maximo)}")

if ocs_con_actividad_maximo:
    total_pendiente = sum(item['oc']['amount_total'] for item in ocs_con_actividad_maximo)
    print(f"\n  💰 Monto total pendiente de aprobar: ${total_pendiente:,.0f}")
    
    # Por estado de actividad
    by_estado_act = defaultdict(int)
    for item in ocs_con_actividad_maximo:
        estado = item['actividad'].get('state', 'sin_estado')
        by_estado_act[estado] += 1
    
    print(f"\n  Estado de actividades:")
    for estado, count in sorted(by_estado_act.items()):
        print(f"    {estado}: {count}")

if len(ocs_con_actividad_maximo) == 0 and len(ocs_fletes) > 0:
    print(f"\n  ⚠⚠⚠ ALERTA: {len(ocs_fletes)} OCs de fletes pero 0 con actividad de Maximo")
    print(f"      Verificar configuración de reglas de aprobación")

print("\n" + "="*80)

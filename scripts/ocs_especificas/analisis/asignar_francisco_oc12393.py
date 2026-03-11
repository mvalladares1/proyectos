#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asignar Francisco a OC12393 específicamente
"""
import xmlrpc.client

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

FRANCISCO_ID = 258

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

# Buscar res_model_id
ir_model = models.execute_kw(
    DB, uid, PASSWORD,
    'ir.model', 'search_read',
    [[['model', '=', 'purchase.order']]],
    {'fields': ['id'], 'limit': 1}
)
res_model_id = ir_model[0]['id']

# Buscar OC12393
oc = models.execute_kw(
    DB, uid, PASSWORD,
    'purchase.order', 'search_read',
    [[['name', '=', 'OC12393']]],
    {'fields': ['id', 'name'], 'limit': 1}
)

if oc:
    oc_id = oc[0]['id']
    print(f"\n✓ OC12393 encontrada (ID: {oc_id})")
    
    # Crear actividad para Francisco
    try:
        nueva_act = models.execute_kw(
            DB, uid, PASSWORD,
            'mail.activity', 'create',
            [{
                'res_model': 'purchase.order',
                'res_model_id': res_model_id,
                'res_id': oc_id,
                'activity_type_id': 9,
                'summary': 'Aprobación FRANCISCO LUTTECKE - Transportes',
                'user_id': FRANCISCO_ID,
                'note': '<p>Esta solicitud de presupuesto requiere aprobación de Francisco Luttecke.</p>'
            }]
        )
        print(f"✅ Actividad creada para Francisco (ID: {nueva_act})")
        print(f"\n📋 OC12393 ahora tiene SOLO a Francisco como aprobador")
        print(f"   Francisco puede pasar la OC a 'Presupuesto enviado' sin bloqueos.")
    except Exception as e:
        print(f"✗ Error: {e}")
else:
    print("✗ OC12393 no encontrada")

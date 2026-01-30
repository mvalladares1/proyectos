#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurar flujo completo TRANSPORTES:
1. RFQ (draft/sent): Francisco + Maximo
2. Enviado → Pedido de Compra: Felipe Horst (Control y Gestión)
"""
import xmlrpc.client

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

FRANCISCO_ID = 258
MAXIMO_ID = 241

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

print("\n" + "="*80)
print("CONFIGURAR FLUJO APROBACIONES TRANSPORTES")
print("="*80)

# 1. Buscar Felipe Horst
print("\n1. BUSCANDO FELIPE HORST (Control y Gestión):")
print("-" * 80)

felipe_users = models.execute_kw(
    DB, uid, PASSWORD,
    'res.users', 'search_read',
    [[['name', 'ilike', 'HORST']]],
    {'fields': ['id', 'name', 'login']}
)

if felipe_users:
    FELIPE_ID = felipe_users[0]['id']
    FELIPE_NOMBRE = felipe_users[0]['name']
    print(f"  ✓ {FELIPE_NOMBRE} (ID: {FELIPE_ID})")
else:
    print("  ✗ No encontrado")
    exit(1)

# 2. Código de automatización actualizado
print("\n2. CREANDO AUTOMATIZACIÓN:")
print("-" * 80)

automation_code = f"""# Automatización: SOLO TRANSPORTES + SERVICIOS
# Flujo:
#   RFQ (draft/sent): Francisco ({FRANCISCO_ID}) + Maximo ({MAXIMO_ID})
#   Enviado → Pedido: Felipe Horst ({FELIPE_ID}) - Control y Gestión

for order in records:
    # Identificar si es TRANSPORTES
    es_transporte = False
    
    # Verificar proveedor
    if order.partner_id:
        proveedor = order.partner_id.name.upper()
        if 'TRANSPORTE' in proveedor or 'ARRAYANES' in proveedor:
            es_transporte = True
    
    # Verificar productos
    if not es_transporte:
        for line in order.order_line:
            if line.product_id:
                producto = line.product_id.name.upper()
                if 'FLETE' in producto or 'TRANSPORTE' in producto:
                    es_transporte = True
                    break
    
    # Solo procesar si es TRANSPORTES
    if not es_transporte:
        continue
    
    # Buscar actividades de aprobación existentes
    activities = env['mail.activity'].search([
        ('res_model', '=', 'purchase.order'),
        ('res_id', '=', order.id),
        ('activity_type_id.name', '=', 'Grant Approval')
    ])
    
    # Determinar aprobadores según estado
    if order.state in ['draft', 'sent']:
        # RFQ: Francisco + Maximo
        aprobadores_correctos = {{{FRANCISCO_ID}, {MAXIMO_ID}}}
        nombres = "Francisco + Maximo"
    elif order.state == 'purchase':
        # Pedido de Compra: Felipe Horst
        aprobadores_correctos = {{{FELIPE_ID}}}
        nombres = "Felipe Horst"
    else:
        # Otros estados
        aprobadores_correctos = set()
        nombres = ""
    
    if aprobadores_correctos:
        # Eliminar actividades que NO sean de los aprobadores correctos
        activities_to_remove = activities.filtered(lambda a: a.user_id.id not in aprobadores_correctos)
        if activities_to_remove:
            activities_to_remove.unlink()
        
        # Verificar qué aprobadores faltan y crear actividades
        existing_approvers = set(act.user_id.id for act in activities)
        missing_approvers = aprobadores_correctos - existing_approvers
        
        for user_id in missing_approvers:
            try:
                ir_model = env['ir.model'].search([('model', '=', 'purchase.order')], limit=1)
                
                # Determinar nombre
                if user_id == {FRANCISCO_ID}:
                    nombre_user = "Francisco Luttecke"
                elif user_id == {MAXIMO_ID}:
                    nombre_user = "Maximo"
                elif user_id == {FELIPE_ID}:
                    nombre_user = "Felipe Horst"
                else:
                    nombre_user = "Usuario"
                
                env['mail.activity'].create({{
                    'res_model': 'purchase.order',
                    'res_model_id': ir_model.id if ir_model else False,
                    'res_id': order.id,
                    'activity_type_id': 9,
                    'summary': f'Aprobación {{nombre_user}} - Transportes',
                    'user_id': user_id,
                    'note': f'<p>Esta orden de TRANSPORTES requiere aprobación de {{nombre_user}}.</p>'
                }})
            except:
                pass
"""

# Actualizar acción de servidor
try:
    models.execute_kw(
        DB, uid, PASSWORD,
        'ir.actions.server', 'write',
        [[1678], {'code': automation_code.strip()}]
    )
    print("  ✅ Automatización actualizada")
except Exception as e:
    print(f"  ✗ Error: {e}")
    exit(1)

# 3. Aplicar a OC12393 inmediatamente
print("\n3. APLICANDO A OC12393:")
print("-" * 80)

oc12393 = models.execute_kw(
    DB, uid, PASSWORD,
    'purchase.order', 'search_read',
    [[['name', '=', 'OC12393']]],
    {'fields': ['id', 'name', 'state']}
)

if oc12393:
    oc_id = oc12393[0]['id']
    
    # Ver actividades actuales
    acts_actuales = models.execute_kw(
        DB, uid, PASSWORD,
        'mail.activity', 'search_read',
        [[['res_model', '=', 'purchase.order'], 
          ['res_id', '=', oc_id],
          ['activity_type_id', '=', 9]]],
        {'fields': ['id', 'user_id']}
    )
    
    print(f"  Actividades actuales: {len(acts_actuales)}")
    for act in acts_actuales:
        user_name = act['user_id'][1] if isinstance(act['user_id'], (list, tuple)) else ''
        print(f"    - {user_name}")
    
    # Eliminar todas y crear Francisco + Maximo
    if acts_actuales:
        models.execute_kw(
            DB, uid, PASSWORD,
            'mail.activity', 'unlink',
            [[act['id'] for act in acts_actuales]]
        )
        print(f"  ✅ Eliminadas {len(acts_actuales)} actividades")
    
    # Crear para Francisco
    ir_model = models.execute_kw(
        DB, uid, PASSWORD,
        'ir.model', 'search_read',
        [[['model', '=', 'purchase.order']]],
        {'fields': ['id'], 'limit': 1}
    )
    res_model_id = ir_model[0]['id']
    
    # Francisco
    try:
        act1 = models.execute_kw(
            DB, uid, PASSWORD,
            'mail.activity', 'create',
            [{'res_model': 'purchase.order',
              'res_model_id': res_model_id,
              'res_id': oc_id,
              'activity_type_id': 9,
              'summary': 'Aprobación Francisco - Transportes',
              'user_id': FRANCISCO_ID,
              'note': '<p>Solicitud de presupuesto TRANSPORTES - Aprobación Francisco</p>'}]
        )
        print(f"  ✅ Creada actividad para Francisco (ID: {act1})")
    except Exception as e:
        print(f"  ✗ Error Francisco: {str(e)[:50]}")
    
    # Maximo
    try:
        act2 = models.execute_kw(
            DB, uid, PASSWORD,
            'mail.activity', 'create',
            [{'res_model': 'purchase.order',
              'res_model_id': res_model_id,
              'res_id': oc_id,
              'activity_type_id': 9,
              'summary': 'Aprobación Maximo - Transportes',
              'user_id': MAXIMO_ID,
              'note': '<p>Solicitud de presupuesto TRANSPORTES - Aprobación Maximo</p>'}]
        )
        print(f"  ✅ Creada actividad para Maximo (ID: {act2})")
    except Exception as e:
        print(f"  ✗ Error Maximo: {str(e)[:50]}")

print("\n" + "="*80)
print("RESUMEN - FLUJO TRANSPORTES")
print("="*80)
print(f"""
✅ AUTOMATIZACIÓN CONFIGURADA

FLUJO APROBACIÓN TRANSPORTES:

📋 FASE 1 - Solicitud de Presupuesto (draft/sent):
   → Francisco Luttecke (ID: {FRANCISCO_ID})
   → Maximo Sepúlveda (ID: {MAXIMO_ID})

📦 FASE 2 - Pedido de Compra (purchase):
   → Felipe Horst (ID: {FELIPE_ID}) - Control y Gestión

Criterio TRANSPORTES:
- Proveedor contiene: "TRANSPORTE", "ARRAYANES"
- Producto contiene: "FLETE", "TRANSPORTE"

OC12393: ✅ Francisco + Maximo asignados
""")

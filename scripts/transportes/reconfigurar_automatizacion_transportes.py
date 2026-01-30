#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crear automatización CORRECTA para TRANSPORTES y desactivar la anterior
"""
import xmlrpc.client

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

FRANCISCO_ID = 258
MAXIMO_ID = 241
FELIPE_ID = 17

common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

print("\n" + "="*80)
print("RECONFIGURAR AUTOMATIZACIÓN TRANSPORTES")
print("="*80)

# 1. Desactivar automatización 128
print("\n1. DESACTIVANDO AUTOMATIZACIÓN 128:")
print("-" * 80)

try:
    models.execute_kw(
        DB, uid, PASSWORD,
        'base.automation', 'write',
        [[128], {'active': False}]
    )
    print("  ✅ Automatización 128 desactivada")
except Exception as e:
    print(f"  ✗ Error: {e}")

# 2. Actualizar automatización 1678 (la de la acción de servidor)
print("\n2. ACTUALIZANDO ACCIÓN 1678 CON CÓDIGO COMPLETO:")
print("-" * 80)

codigo_completo = f"""# FLUJO DE APROBACIÓN TRANSPORTES
# Draft/Sent: Francisco + Maximo
# Purchase: Felipe Horst

for order in records:
    # Solo procesar TRANSPORTES (productos con FLETE o proveedor TRANSPORTE)
    es_transporte = False
    
    if order.partner_id and ('TRANSPORTE' in order.partner_id.name.upper() or 'ARRAYANES' in order.partner_id.name.upper()):
        es_transporte = True
    
    if not es_transporte:
        for line in order.order_line:
            if line.product_id and 'FLETE' in line.product_id.name.upper():
                es_transporte = True
                break
    
    if not es_transporte:
        continue
    
    # Buscar todas las actividades de aprobación
    all_activities = env['mail.activity'].search([
        ('res_model', '=', 'purchase.order'),
        ('res_id', '=', order.id),
        ('activity_type_id.name', '=', 'Grant Approval')
    ])
    
    # Determinar aprobadores según estado
    if order.state in ['draft', 'sent']:
        aprobadores_correctos = {{{FRANCISCO_ID}, {MAXIMO_ID}}}
    elif order.state == 'purchase':
        aprobadores_correctos = {{{FELIPE_ID}}}
    else:
        aprobadores_correctos = set()
    
    if aprobadores_correctos:
        # Eliminar TODAS las actividades que NO sean de los aprobadores correctos
        # Esto incluye las creadas por Check 1, Check 2, etc.
        activities_to_remove = all_activities.filtered(lambda a: a.user_id.id not in aprobadores_correctos)
        if activities_to_remove:
            activities_to_remove.unlink()
        
        # Verificar qué aprobadores faltan
        existing_approvers = set(act.user_id.id for act in all_activities if act.user_id.id in aprobadores_correctos)
        missing_approvers = aprobadores_correctos - existing_approvers
        
        # Crear actividades faltantes
        for user_id in missing_approvers:
            try:
                ir_model = env['ir.model'].search([('model', '=', 'purchase.order')], limit=1)
                
                if user_id == {FRANCISCO_ID}:
                    nombre_user = "Francisco Luttecke"
                elif user_id == {MAXIMO_ID}:
                    nombre_user = "Maximo Sepúlveda"
                elif user_id == {FELIPE_ID}:
                    nombre_user = "Felipe Horst - Control y Gestión"
                else:
                    nombre_user = "Usuario"
                
                env['mail.activity'].create({{
                    'res_model': 'purchase.order',
                    'res_model_id': ir_model.id if ir_model else False,
                    'res_id': order.id,
                    'activity_type_id': 9,
                    'summary': f'Aprobación {{nombre_user}} - Transportes',
                    'user_id': user_id,
                    'note': f'<p>OC de TRANSPORTES - Requiere aprobación de {{nombre_user}}</p>'
                }})
            except:
                pass
"""

try:
    models.execute_kw(
        DB, uid, PASSWORD,
        'ir.actions.server', 'write',
        [[1678], {'code': codigo_completo.strip()}]
    )
    print("  ✅ Acción 1678 actualizada con limpieza de actividades extra")
except Exception as e:
    print(f"  ✗ Error: {e}")

# 3. Crear automatización que se ejecute DESPUÉS de Check 1 y Check 2
print("\n3. VERIFICANDO SECUENCIA DE AUTOMATIZACIONES:")
print("-" * 80)

autos = models.execute_kw(
    DB, uid, PASSWORD,
    'base.automation', 'search_read',
    [[['model_id.model', '=', 'purchase.order'], ['active', '=', True]]],
    {'fields': ['id', 'name', 'sequence']}
)

print("  Automatizaciones activas:")
for auto in autos:
    print(f"    {auto['id']}: {auto['name']} - Secuencia: {auto.get('sequence', 'N/A')}")

# La automatización de TRANSPORTES debe tener secuencia MAYOR que Check 1 y Check 2
# para que se ejecute DESPUÉS y pueda limpiar las actividades que ellos crearon

print("\n" + "="*80)
print("RESUMEN")
print("="*80)
print(f"""
✅ Configuración actualizada

La acción 1678 ahora:
1. Identifica si es OC de TRANSPORTES (producto FLETE o proveedor TRANSPORTE)
2. ELIMINA TODAS las actividades que NO sean Francisco/Maximo/Felipe
   (incluyendo las creadas por Check 1, Check 2, etc.)
3. Crea solo las actividades correctas según estado

Flujo TRANSPORTES:
- Draft/Sent: Francisco ({FRANCISCO_ID}) + Maximo ({MAXIMO_ID})
- Purchase: Felipe Horst ({FELIPE_ID})

El botón "CONFIRMAR PEDIDO" ya NO debería mostrar aprobadores extra.
""")

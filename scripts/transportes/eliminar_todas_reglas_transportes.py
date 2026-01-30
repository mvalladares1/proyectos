import xmlrpc.client

# Conexión a Odoo
url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 80)
print("ACTUALIZAR ACCIÓN 1678 PARA ELIMINAR TODAS LAS APROBACIONES")
print("=" * 80)

# Código actualizado que elimina TODAS las actividades de aprobación
# y solo crea las de Francisco/Maximo/Felipe
nuevo_codigo = """# FLUJO DE APROBACIÓN TRANSPORTES - ELIMINA TODAS LAS REGLAS DEL SISTEMA
# Draft/Sent: Francisco + Maximo
# Purchase: Felipe Horst

FRANCISCO_ID = 258
MAXIMO_ID = 241
FELIPE_ID = 17

for order in records:
    # Solo procesar TRANSPORTES
    es_transporte = False
    
    if order.partner_id and ('TRANSPORTE' in order.partner_id.name.upper() or 'ARRAYANES' in order.partner_id.name.upper()):
        es_transporte = True
    
    if not es_transporte:
        for line in order.order_line:
            if line.product_id and ('FLETE' in line.product_id.name.upper() or 'TRANSPORTE' in line.product_id.name.upper()):
                es_transporte = True
                break
    
    if not es_transporte:
        continue
    
    # ELIMINAR TODAS LAS ACTIVIDADES DE APROBACIÓN EXISTENTES
    # Esto incluye las creadas por reglas del sistema
    env['mail.activity'].search([
        ('res_id', '=', order.id),
        ('res_model', '=', 'purchase.order'),
        ('activity_type_id', '=', 9)  # Grant Approval
    ]).unlink()
    
    # Crear SOLO las actividades correctas según estado
    if order.state in ['draft', 'sent', 'to approve']:
        # Francisco + Maximo
        env['mail.activity'].create({
            'res_id': order.id,
            'res_model': 'purchase.order',
            'activity_type_id': 9,
            'summary': 'Aprobación Francisco Luttecke - Transportes',
            'user_id': FRANCISCO_ID
        })
        
        env['mail.activity'].create({
            'res_id': order.id,
            'res_model': 'purchase.order',
            'activity_type_id': 9,
            'summary': 'Aprobación Maximo Sepúlveda - Transportes',
            'user_id': MAXIMO_ID
        })
        
    elif order.state == 'purchase':
        # Felipe Horst
        env['mail.activity'].create({
            'res_id': order.id,
            'res_model': 'purchase.order',
            'activity_type_id': 9,
            'summary': 'Aprobación Felipe Horst - Transportes',
            'user_id': FELIPE_ID
        })
"""

print("\n1. ACTUALIZANDO ACCIÓN 1678:")
print("-" * 80)
try:
    result = models.execute_kw(db, uid, password, 'ir.actions.server', 'write',
        [[1678], {'code': nuevo_codigo}])
    
    if result:
        print("  ✅ Acción 1678 actualizada exitosamente")
        print("\n  La acción ahora:")
        print("  1. ELIMINA TODAS las actividades de aprobación (incluyendo reglas del sistema)")
        print("  2. Crea SOLO Francisco + Maximo (draft/sent) o Felipe (purchase)")
        print("  3. Se ejecuta en cada cambio de estado (on_write)")
    else:
        print("  ❌ Error actualizando")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Ahora ejecutar manualmente en OC12332 para limpiar
print("\n2. LIMPIANDO OC12332 AHORA:")
print("-" * 80)

oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC12332']]],
    {'fields': ['id', 'state']})

if oc:
    oc_id = oc[0]['id']
    
    # Eliminar TODAS las actividades
    actividades = models.execute_kw(db, uid, password, 'mail.activity', 'search',
        [[
            ('res_id', '=', oc_id),
            ('res_model', '=', 'purchase.order'),
            ('activity_type_id', '=', 9)
        ]])
    
    if actividades:
        models.execute_kw(db, uid, password, 'mail.activity', 'unlink', [actividades])
        print(f"  ❌ Eliminadas {len(actividades)} actividades existentes")
    
    # Obtener res_model_id
    model_id = models.execute_kw(db, uid, password, 'ir.model', 'search',
        [[['model', '=', 'purchase.order']]])
    
    if model_id:
        # Crear solo Francisco + Maximo (estado draft)
        act1 = models.execute_kw(db, uid, password, 'mail.activity', 'create',
            [{
                'res_id': oc_id,
                'res_model': 'purchase.order',
                'res_model_id': model_id[0],
                'activity_type_id': 9,
                'summary': 'Aprobación Francisco Luttecke - Transportes',
                'user_id': 258
            }])
        
        act2 = models.execute_kw(db, uid, password, 'mail.activity', 'create',
            [{
                'res_id': oc_id,
                'res_model': 'purchase.order',
                'res_model_id': model_id[0],
                'activity_type_id': 9,
                'summary': 'Aprobación Maximo Sepúlveda - Transportes',
                'user_id': 241
            }])
    
    print(f"  ✅ Creadas 2 nuevas actividades: Francisco + Maximo")

print("\n" + "=" * 80)
print("✅ RECARGA OC12332 - Ahora solo deberían aparecer Francisco y Maximo")
print("=" * 80)

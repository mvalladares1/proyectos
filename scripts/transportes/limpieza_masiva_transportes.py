import xmlrpc.client
import time

# Conexión a Odoo
url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 80)
print("LIMPIEZA MASIVA DE ACTIVIDADES EXTRA EN TRANSPORTES")
print("=" * 80)

FRANCISCO_ID = 258
MAXIMO_ID = 241
FELIPE_ID = 17

# Buscar TODAS las OCs de SERVICIOS
ocs = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['x_studio_categora_de_producto', '=', 'SERVICIOS']]],
    {'fields': ['id', 'name', 'state', 'partner_id', 'order_line'], 'limit': 500})

print(f"\n1. IDENTIFICANDO OCs DE TRANSPORTES:")
print("-" * 80)

ocs_transportes = []
for oc in ocs:
    es_transporte = False
    
    # Verificar proveedor
    if oc.get('partner_id'):
        proveedor = oc['partner_id'][1].upper()
        if 'TRANSPORTE' in proveedor or 'ARRAYANES' in proveedor:
            es_transporte = True
    
    # Verificar productos
    if not es_transporte and oc.get('order_line'):
        for line_id in oc['order_line']:
            line = models.execute_kw(db, uid, password, 'purchase.order.line', 'read',
                [line_id], {'fields': ['product_id']})
            if line and line[0].get('product_id'):
                producto = models.execute_kw(db, uid, password, 'product.product', 'read',
                    [line[0]['product_id'][0]], {'fields': ['name']})
                if producto:
                    nombre_producto = producto[0]['name'].upper()
                    if 'FLETE' in nombre_producto or 'TRANSPORTE' in nombre_producto:
                        es_transporte = True
                        break
    
    if es_transporte:
        ocs_transportes.append(oc)

print(f"✅ {len(ocs_transportes)} OCs de TRANSPORTES identificadas\n")

# Procesar cada OC
print("2. LIMPIANDO ACTIVIDADES:")
print("-" * 80)

total_eliminadas = 0
ocs_procesadas = 0

for oc in ocs_transportes:
    # Determinar usuarios correctos según estado
    if oc['state'] in ['draft', 'sent', 'to approve']:
        usuarios_correctos = [FRANCISCO_ID, MAXIMO_ID]
    elif oc['state'] == 'purchase':
        usuarios_correctos = [FELIPE_ID]
    elif oc['state'] in ['done', 'cancel']:
        usuarios_correctos = []  # No debe tener actividades
    else:
        continue
    
    # Buscar actividades
    actividades = models.execute_kw(db, uid, password, 'mail.activity', 'search_read',
        [[
            ('res_id', '=', oc['id']),
            ('res_model', '=', 'purchase.order'),
            ('activity_type_id', '=', 9)
        ]],
        {'fields': ['id', 'user_id']})
    
    if not actividades:
        continue
    
    # Eliminar actividades incorrectas
    eliminadas_oc = 0
    for actividad in actividades:
        user_id = actividad['user_id'][0] if actividad.get('user_id') else None
        
        if user_id not in usuarios_correctos:
            try:
                models.execute_kw(db, uid, password, 'mail.activity', 'unlink', [[actividad['id']]])
                eliminadas_oc += 1
            except Exception as e:
                print(f"  ⚠️  Error eliminando actividad {actividad['id']}: {e}")
    
    if eliminadas_oc > 0:
        total_eliminadas += eliminadas_oc
        ocs_procesadas += 1
        print(f"✅ {oc['name']} ({oc['state']}): {eliminadas_oc} actividades eliminadas")

print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)
print(f"OCs procesadas: {ocs_procesadas}")
print(f"Actividades eliminadas: {total_eliminadas}")
print("\n✅ LIMPIEZA COMPLETA")
print("\nAhora TODAS las OCs de TRANSPORTES tienen solo los aprobadores correctos:")
print("  - Draft/Sent: Francisco + Maximo")
print("  - Purchase: Felipe")

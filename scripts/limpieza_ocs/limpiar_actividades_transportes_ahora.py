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
print("LIMPIAR ACTIVIDADES EXTRA DE TRANSPORTES - EJECUCIÓN INMEDIATA")
print("=" * 80)

# IDs de usuarios correctos
FRANCISCO_ID = 258
MAXIMO_ID = 241
FELIPE_ID = 17

# Buscar todas las OCs de SERVICIOS
print("\n1. BUSCANDO OCS DE SERVICIOS:")
print("-" * 80)
ocs_servicios = models.execute_kw(db, uid, password, 'purchase.order', 'search_read', 
    [[['x_studio_categora_de_producto', '=', 'SERVICIOS']]],
    {'fields': ['name', 'state', 'partner_id', 'order_line']})

print(f"  Total OCs SERVICIOS encontradas: {len(ocs_servicios)}")

# Identificar TRANSPORTES
ocs_transportes = []
for oc in ocs_servicios:
    es_transporte = False
    
    # Verificar nombre del proveedor
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

print(f"  OCs TRANSPORTES identificadas: {len(ocs_transportes)}")

# Procesar cada OC de TRANSPORTES
print(f"\n2. LIMPIANDO ACTIVIDADES EXTRA:")
print("-" * 80)

actividades_eliminadas_total = 0
ocs_procesadas = 0

for oc in ocs_transportes:
    if oc['state'] == 'cancel':
        continue
    
    # Buscar TODAS las actividades de aprobación de esta OC
    actividades = models.execute_kw(db, uid, password, 'mail.activity', 'search_read',
        [[
            ['res_id', '=', oc['id']],
            ['res_model', '=', 'purchase.order'],
            ['activity_type_id', '=', 9]  # Grant Approval
        ]],
        {'fields': ['id', 'user_id', 'summary']})
    
    # Determinar qué usuarios son correctos según el estado
    if oc['state'] in ['draft', 'sent', 'to approve']:
        usuarios_correctos = [FRANCISCO_ID, MAXIMO_ID]
    elif oc['state'] == 'purchase':
        usuarios_correctos = [FELIPE_ID]
    else:
        usuarios_correctos = []
    
    # Eliminar actividades que NO sean de usuarios correctos
    actividades_eliminadas_oc = 0
    for actividad in actividades:
        user_id = actividad['user_id'][0] if actividad.get('user_id') else None
        
        if user_id not in usuarios_correctos:
            try:
                models.execute_kw(db, uid, password, 'mail.activity', 'unlink', [[actividad['id']]])
                actividades_eliminadas_oc += 1
                print(f"  ❌ {oc['name']}: Eliminada actividad de {actividad['user_id'][1]}")
            except Exception as e:
                print(f"  ⚠️  Error eliminando actividad {actividad['id']}: {e}")
    
    if actividades_eliminadas_oc > 0:
        actividades_eliminadas_total += actividades_eliminadas_oc
        ocs_procesadas += 1

print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)
print(f"OCs TRANSPORTES procesadas: {ocs_procesadas}")
print(f"Actividades EXTRA eliminadas: {actividades_eliminadas_total}")
print("\n✅ Ahora el botón CONFIRMAR PEDIDO solo debe mostrar aprobadores correctos:")
print("   - Draft/Sent: Francisco + Maximo")
print("   - Purchase: Felipe Horst")

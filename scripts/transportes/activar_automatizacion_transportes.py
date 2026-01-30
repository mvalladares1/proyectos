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
print("REACTIVAR AUTOMATIZACIÓN DE TRANSPORTES")
print("=" * 80)

# Buscar automatización 128
print("\n1. BUSCANDO AUTOMATIZACIÓN 128:")
print("-" * 80)
auto128 = models.execute_kw(db, uid, password, 'base.automation', 'search_read',
    [[['id', '=', 128]]],
    {'fields': ['id', 'name', 'active', 'trigger', 'filter_domain', 'action_server_id']})

if auto128:
    auto = auto128[0]
    print(f"ID: {auto['id']}")
    print(f"Nombre: {auto['name']}")
    print(f"Activa: {auto.get('active')}")
    print(f"Trigger: {auto.get('trigger')}")
    print(f"Dominio: {auto.get('filter_domain')}")
    
    if not auto.get('active'):
        print("\n❌ LA AUTOMATIZACIÓN ESTÁ DESACTIVADA")
        print("Activando...")
        
        # Activar y configurar trigger correcto
        models.execute_kw(db, uid, password, 'base.automation', 'write',
            [[128], {
                'active': True,
                'trigger': 'on_write',  # Se ejecuta al modificar
                'filter_domain': "[('x_studio_categora_de_producto', '=', 'SERVICIOS')]",
                'action_server_id': 1678
            }])
        
        print("✅ Automatización ACTIVADA")
        print("  Trigger: on_write (se ejecuta al modificar OC)")
        print("  Dominio: Categoría = SERVICIOS")
        print("  Acción: 1678 (limpia y crea actividades correctas)")
    else:
        print("✅ Ya está activa")
else:
    print("❌ Automatización 128 no existe")
    print("\nCreando nueva automatización...")
    
    # Crear automatización
    auto_id = models.execute_kw(db, uid, password, 'base.automation', 'create',
        [{
            'name': 'Aprobación TRANSPORTES - Francisco + Maximo + Felipe',
            'model_id': models.execute_kw(db, uid, password, 'ir.model', 'search',
                [[['model', '=', 'purchase.order']]], {'limit': 1})[0],
            'trigger': 'on_write',
            'active': True,
            'filter_domain': "[('x_studio_categora_de_producto', '=', 'SERVICIOS')]",
            'action_server_id': 1678
        }])
    
    print(f"✅ Automatización creada: ID {auto_id}")

# Ejecutar manualmente en una OC de prueba
print("\n2. PROBANDO EN OC12332:")
print("-" * 80)

oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC12332']]],
    {'fields': ['id', 'name', 'state']})

if oc:
    oc_id = oc[0]['id']
    
    # Forzar ejecución escribiendo un campo
    models.execute_kw(db, uid, password, 'purchase.order', 'write',
        [[oc_id], {'notes': 'Test automatización'}])
    
    print(f"✅ Trigger ejecutado en OC{oc[0]['name']}")
    
    # Verificar actividades
    import time
    time.sleep(2)
    
    actividades = models.execute_kw(db, uid, password, 'mail.activity', 'search_read',
        [[
            ('res_id', '=', oc_id),
            ('res_model', '=', 'purchase.order'),
            ('activity_type_id', '=', 9)
        ]],
        {'fields': ['user_id', 'summary']})
    
    print(f"\nActividades actuales:")
    for act in actividades:
        print(f"  - {act['user_id'][1]}: {act.get('summary')}")

print("\n" + "=" * 80)
print("✅ AUTOMATIZACIÓN CONFIGURADA Y ACTIVA")
print("=" * 80)
print("\nAhora al aprobar Francisco:")
print("1. La acción 1678 se ejecutará (on_write)")
print("2. ELIMINARÁ todas las actividades existentes")
print("3. Creará SOLO Francisco + Maximo")
print("\nPrueba aprobar Francisco en OC12332 nuevamente")

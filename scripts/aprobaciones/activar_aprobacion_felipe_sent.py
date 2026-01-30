"""
Crear automatización para que Felipe apruebe cuando OC TRANSPORTES está en SENT
"""
import xmlrpc.client

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 80)
print("CREAR AUTOMATIZACIÓN FELIPE - TRANSPORTES EN SENT")
print("=" * 80)

# IDs importantes
FELIPE_ID = 17

# 1. Buscar model_id para purchase.order
model_id = models.execute_kw(db, uid, password,
    'ir.model', 'search_read',
    [[['model', '=', 'purchase.order']]],
    {'fields': ['id', 'name'], 'limit': 1}
)

if not model_id:
    print("❌ No se encontró el modelo purchase.order")
    exit(1)

MODEL_ID = model_id[0]['id']
print(f"\n✅ Modelo purchase.order encontrado (ID: {MODEL_ID})")

# 2. Buscar activity_type_id para "Grant Approval"
activity_type = models.execute_kw(db, uid, password,
    'mail.activity.type', 'search_read',
    [[['name', '=', 'Grant Approval']]],
    {'fields': ['id', 'name'], 'limit': 1}
)

if not activity_type:
    print("❌ No se encontró el tipo de actividad 'Grant Approval'")
    exit(1)

ACTIVITY_TYPE_ID = activity_type[0]['id']
print(f"✅ Tipo de actividad 'Grant Approval' encontrado (ID: {ACTIVITY_TYPE_ID})")

# 3. Crear acción de servidor primero
print("\n" + "-" * 80)
print("1. CREANDO ACCIÓN DE SERVIDOR")
print("-" * 80)

action_code = """
# Crear actividad de aprobación para Felipe Horst (ID: 17)
for record in records:
    if record.x_studio_categora_de_producto == 'SERVICIOS' and record.state == 'sent':
        # Verificar si ya existe actividad para Felipe
        existing = env['mail.activity'].search([
            ('res_model', '=', 'purchase.order'),
            ('res_id', '=', record.id),
            ('user_id', '=', 17),
            ('activity_type_id', '=', 9)  # Grant Approval
        ])
        
        if not existing:
            env['mail.activity'].create({
                'res_model': 'purchase.order',
                'res_id': record.id,
                'user_id': 17,  # Felipe Horst
                'activity_type_id': 9,  # Grant Approval
                'summary': 'Aprobación Felipe - Transportes',
                'note': 'Aprobar OC de TRANSPORTES para pasar a Purchase Order'
            })
"""

action_vals = {
    'name': 'TRANSPORTES: Aprobación Felipe (SENT → PURCHASE)',
    'model_id': MODEL_ID,
    'state': 'code',
    'code': action_code,
}

action_id = models.execute_kw(db, uid, password,
    'ir.actions.server', 'create',
    [action_vals]
)

print(f"✅ Acción de servidor creada (ID: {action_id})")

# 4. Crear automatización
print("\n" + "-" * 80)
print("2. CREANDO AUTOMATIZACIÓN")
print("-" * 80)

automation_vals = {
    'name': 'TRANSPORTES: Aprobación Felipe cuando pasa a SENT',
    'model_id': MODEL_ID,
    'trigger': 'on_write',  # Se activa al modificar
    'filter_domain': "[('x_studio_categora_de_producto', '=', 'SERVICIOS'), ('state', '=', 'sent')]",
    'filter_pre_domain': "[('state', '!=', 'sent')]",  # Antes NO era sent
    'active': True,
    'action_server_id': action_id,
}

automation_id = models.execute_kw(db, uid, password,
    'base.automation', 'create',
    [automation_vals]
)

print(f"✅ Automatización creada (ID: {automation_id})")

# 5. Verificar
print("\n" + "=" * 80)
print("VERIFICANDO AUTOMATIZACIÓN CREADA")
print("=" * 80)

automation = models.execute_kw(db, uid, password,
    'base.automation', 'read',
    [automation_id],
    {'fields': ['name', 'model_id', 'trigger', 'filter_domain', 'filter_pre_domain', 'active', 'action_server_id']}
)[0]

print(f"\n📋 Automatización: {automation['name']}")
print(f"   ID: {automation_id}")
print(f"   Modelo: {automation['model_id'][1]}")
print(f"   Trigger: {automation['trigger']}")
print(f"   Activa: {automation['active']}")
print(f"   Filtro: {automation['filter_domain']}")
print(f"   Pre-filtro: {automation['filter_pre_domain']}")
print(f"   Acción: {automation['action_server_id'][1]}")

print("\n" + "=" * 80)
print("✅ AUTOMATIZACIÓN CREADA EXITOSAMENTE")
print("=" * 80)
print("\nFLUJO COMPLETO:")
print("  1. OC en draft → Clic CONFIRMAR PEDIDO")
print("  2. → Francisco aprueba")
print("  3. → Maximo aprueba")
print("  4. → Botón ejecuta, OC pasa a SENT")
print("  5. → Automatización detecta cambio a SENT")
print("  6. → Crea actividad de aprobación para Felipe")
print("  7. → Felipe aprueba")
print("  8. → OC pasa a PURCHASE")
print("\n⚠️  Recarga Odoo (Ctrl+F5) para que tome efecto")

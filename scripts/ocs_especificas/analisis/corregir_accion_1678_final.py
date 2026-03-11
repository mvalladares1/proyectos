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
print("CORREGIR CÓDIGO DE ACCIÓN 1678")
print("=" * 80)

# Código corregido con res_model_id
codigo_corregido = """# FLUJO DE APROBACIÓN TRANSPORTES
# Draft/Sent: Francisco + Maximo  
# Purchase: Felipe Horst

FRANCISCO_ID = 258
MAXIMO_ID = 241
FELIPE_ID = 17

# Obtener res_model_id de purchase.order
purchase_model = env['ir.model'].search([('model', '=', 'purchase.order')], limit=1)
if not purchase_model:
    raise UserError('No se encontró modelo purchase.order')

model_id = purchase_model.id

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
    env['mail.activity'].search([
        ('res_id', '=', order.id),
        ('res_model', '=', 'purchase.order'),
        ('activity_type_id', '=', 9)
    ]).unlink()
    
    # Crear SOLO las actividades correctas según estado
    if order.state in ['draft', 'sent', 'to approve']:
        # Francisco + Maximo
        env['mail.activity'].create({
            'res_id': order.id,
            'res_model': 'purchase.order',
            'res_model_id': model_id,
            'activity_type_id': 9,
            'summary': 'Aprobación Francisco Luttecke - Transportes',
            'user_id': FRANCISCO_ID
        })
        
        env['mail.activity'].create({
            'res_id': order.id,
            'res_model': 'purchase.order',
            'res_model_id': model_id,
            'activity_type_id': 9,
            'summary': 'Aprobación Maximo Sepúlveda - Transportes',
            'user_id': MAXIMO_ID
        })
        
    elif order.state == 'purchase':
        # Felipe Horst
        env['mail.activity'].create({
            'res_id': order.id,
            'res_model': 'purchase.order',
            'res_model_id': model_id,
            'activity_type_id': 9,
            'summary': 'Aprobación Felipe Horst - Transportes',
            'user_id': FELIPE_ID
        })
"""

print("\n1. ACTUALIZANDO ACCIÓN 1678:")
print("-" * 80)
try:
    result = models.execute_kw(db, uid, password, 'ir.actions.server', 'write',
        [[1678], {'code': codigo_corregido}])
    
    if result:
        print("✅ Acción 1678 actualizada con res_model_id")
    else:
        print("❌ Error actualizando acción")
except Exception as e:
    print(f"❌ Error: {e}")

# Desactivar automatización 129
print("\n2. DESACTIVANDO AUTOMATIZACIÓN 129:")
print("-" * 80)
try:
    models.execute_kw(db, uid, password, 'base.automation', 'write',
        [[129], {'active': False}])
    print("✅ Automatización 129 desactivada")
except:
    pass

print("\n" + "=" * 80)
print("IMPORTANTE:")
print("=" * 80)
print("La acción 1678 está corregida PERO NO HAY AUTOMATIZACIÓN ACTIVA")
print("\nEl problema es que cuando Francisco aprueba, NO se ejecuta ninguna automatización.")
print("Las actividades extra vienen de ODOO directamente, no de nuestras automatizaciones.")
print("\nLa solución es NO usar automatizaciones, sino ELIMINAR manualmente")
print("las actividades extra DESPUÉS de cada aprobación.")

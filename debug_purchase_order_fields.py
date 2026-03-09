"""
Debug: Verificar campos disponibles en purchase.order y lógica actual
"""
import xmlrpc.client
from datetime import datetime

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 100)
print("DEBUG: CAMPOS PURCHASE.ORDER Y LÓGICA DE PROYECCIONES")
print("=" * 100)

# 1. Obtener campos de purchase.order que contengan 'fecha' o 'date'
print("\n📋 CAMPOS DE PURCHASE.ORDER CON 'fecha' O 'date':")
print("-" * 80)

fields = models.execute_kw(db, uid, password, 'purchase.order', 'fields_get', [], {'attributes': ['type', 'string']})
fecha_fields = {k: v for k, v in fields.items() if 'fecha' in k.lower() or 'date' in k.lower()}

for field_name, info in sorted(fecha_fields.items()):
    print(f"  {field_name:45} | Tipo: {info.get('type', 'N/A'):10} | Label: {info.get('string', 'N/A')}")

# 2. Buscar OCs sin factura para ejemplo
print("\n" + "=" * 100)
print("📋 EJEMPLO OC SIN FACTURA (para verificar campos):")
print("-" * 80)

oc_ejemplo = models.execute_kw(db, uid, password,
    'purchase.order', 'search_read',
    [[['state', '=', 'purchase'], ['invoice_ids', '=', False]]],
    {'fields': list(fecha_fields.keys()) + ['name', 'partner_id', 'amount_total', 'state', 'currency_id'],
     'limit': 5}
)

for oc in oc_ejemplo:
    print(f"\n🔷 {oc['name']} | Partner: {oc.get('partner_id', ['',''])[1] if oc.get('partner_id') else 'N/A'}")
    print(f"   Total: {oc.get('amount_total', 0):,.0f} {oc.get('currency_id', ['','CLP'])[1] if oc.get('currency_id') else 'CLP'}")
    print(f"   Estado: {oc.get('state')}")
    print(f"   Fechas:")
    for field in sorted(fecha_fields.keys()):
        value = oc.get(field)
        if value:
            print(f"     {field:40} = {value}")

# 3. Verificar cuentas específicas mencionadas
print("\n" + "=" * 100)
print("📋 VERIFICAR CUENTAS ESPECÍFICAS:")
print("-" * 80)

cuentas_verificar = ['21020101', '11060101', '62010101', '21010102']
for codigo in cuentas_verificar:
    cuenta = models.execute_kw(db, uid, password,
        'account.account', 'search_read',
        [[['code', '=', codigo]]],
        {'fields': ['id', 'code', 'name'], 'limit': 1}
    )
    if cuenta:
        print(f"  {codigo}: ID={cuenta[0]['id']:6} | {cuenta[0]['name']}")
    else:
        print(f"  {codigo}: ❌ NO ENCONTRADA")

# 4. Ver OC específica OC12621
print("\n" + "=" * 100)
print("📋 OC12621 DETALLE COMPLETO:")
print("-" * 80)

oc_12621 = models.execute_kw(db, uid, password,
    'purchase.order', 'search_read',
    [[['name', '=', 'OC12621']]],
    {'fields': list(fecha_fields.keys()) + ['name', 'partner_id', 'amount_total', 'state', 'currency_id', 'payment_term_id', 'invoice_ids'],
     'limit': 1}
)

if oc_12621:
    oc = oc_12621[0]
    print(f"ID: {oc['id']}")
    print(f"Nombre: {oc['name']}")
    print(f"Proveedor: {oc.get('partner_id', ['',''])[1] if oc.get('partner_id') else 'N/A'}")
    print(f"Total: {oc.get('amount_total', 0):,.2f}")
    print(f"Moneda: {oc.get('currency_id', ['','CLP'])[1] if oc.get('currency_id') else 'CLP'}")
    print(f"Estado: {oc.get('state')}")
    print(f"Plazo pago: {oc.get('payment_term_id')}")
    print(f"Facturas: {oc.get('invoice_ids')}")
    print(f"\nTodas las fechas:")
    for field in sorted(fecha_fields.keys()):
        value = oc.get(field)
        print(f"  {field:40} = {value}")
else:
    print("❌ OC12621 no encontrada")

print("\n" + "=" * 100)
print("ANÁLISIS COMPLETADO")
print("=" * 100)

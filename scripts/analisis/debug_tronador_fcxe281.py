"""
Debug para verificar que TRONADOR SAC muestra correctamente:
- Monto cobrado en el periodo correcto
- Monto pendiente en la fecha estimada de pago
"""
import requests
import json
from xmlrpc import client as xmlrpc_client

# Odoo
ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# API
API_URL = "http://167.114.114.51:8002"

print("=" * 70)
print("VERIFICACIÓN FCXE 000281 - TRONADOR SAC")
print("=" * 70)

# 2. Consultar API primero para verificar cómo se muestra
print("\n" + "=" * 70)
print("DATOS EN API (1.1.1)")
print("=" * 70)

resp = requests.get(
    f"{API_URL}/api/v1/flujo-caja/semanal",
    params={
        "fecha_inicio": "2026-01-01",
        "fecha_fin": "2026-02-28",
        "username": USERNAME,
        "password": PASSWORD
    },
    timeout=120
)

data = resp.json()
conceptos = data.get('actividades', {}).get('OPERACION', {}).get('conceptos', [])
concepto_111 = next((c for c in conceptos if c.get('id') == '1.1.1'), None)

if concepto_111:
    print(f"\n📊 Concepto 1.1.1 - Total: ${concepto_111.get('total', 0):,.0f}")
    
    for cuenta in concepto_111.get('cuentas', []):
        nombre = cuenta.get('nombre', '')
        print(f"\n  {nombre}")
        
        for etiq in cuenta.get('etiquetas', []):
            if 'TRONADOR' in str(etiq.get('nombre', '')).upper():
                print(f"\n    🔍 TRONADOR encontrado:")
                print(f"       Monto total: ${etiq.get('monto', 0):,.0f}")
                print(f"       Real: ${etiq.get('real', 0):,.0f}")
                print(f"       Proyectado: ${etiq.get('proyectado', 0):,.0f}")
                
                print(f"\n       Montos por periodo:")
                for periodo, monto in sorted(etiq.get('montos_por_mes', {}).items()):
                    if monto != 0:
                        print(f"         {periodo}: ${monto:,.0f}")
else:
    print("❌ Concepto 1.1.1 no encontrado")

# 1. Consultar datos directamente en Odoo
print("\n" + "=" * 70)
print("DATOS EN ODOO:")
print("=" * 70)

common = xmlrpc_client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
uid = common.authenticate(ODOO_DB, USERNAME, PASSWORD, {})
models = xmlrpc_client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

factura = models.execute_kw(ODOO_DB, uid, PASSWORD, 'account.move', 'search_read',
    [[['name', '=', 'FCXE 000281']]],
    {'fields': ['id', 'name', 'partner_id', 'invoice_date', 'invoice_date_due',
                'amount_total', 'amount_residual', 'payment_state', 
                'x_studio_fecha_estimada_de_pago', 'currency_id'],
     'limit': 1}
)

if factura:
    f = factura[0]
    print("\n📄 DATOS EN ODOO:")
    print(f"  Factura: {f['name']}")
    print(f"  Partner: {f['partner_id']}")
    print(f"  Fecha factura: {f['invoice_date']}")
    print(f"  Fecha vencimiento: {f['invoice_date_due']}")
    print(f"  Fecha estimada pago: {f.get('x_studio_fecha_estimada_de_pago', 'N/A')}")
    print(f"  Total: {f['amount_total']} {f['currency_id']}")
    print(f"  Residual: {f['amount_residual']}")
    print(f"  Payment state: {f['payment_state']}")
    
    cobrado = f['amount_total'] - f['amount_residual']
    print(f"\n  Cobrado: {cobrado}")
    print(f"  Pendiente: {f['amount_residual']}")
else:
    print("❌ Factura FCXE 000281 no encontrada")

# 2. Consultar API para verificar cómo se muestra
print("\n" + "=" * 70)
print("DATOS EN API (1.1.1)")
print("=" * 70)

resp = requests.get(
    f"{API_URL}/api/v1/flujo-caja/semanal",
    params={
        "fecha_inicio": "2026-01-01",
        "fecha_fin": "2026-02-28",
        "username": USERNAME,
        "password": PASSWORD
    },
    timeout=120
)

data = resp.json()
conceptos = data.get('actividades', {}).get('OPERACION', {}).get('conceptos', [])
concepto_111 = next((c for c in conceptos if c.get('id') == '1.1.1'), None)

if concepto_111:
    print(f"\n📊 Concepto 1.1.1 - Total: ${concepto_111.get('total', 0):,.0f}")
    
    for cuenta in concepto_111.get('cuentas', []):
        nombre = cuenta.get('nombre', '')
        print(f"\n  {nombre}")
        
        for etiq in cuenta.get('etiquetas', []):
            if 'TRONADOR' in str(etiq.get('nombre', '')).upper():
                print(f"\n    🔍 TRONADOR encontrado:")
                print(f"       Monto total: ${etiq.get('monto', 0):,.0f}")
                print(f"       Real: ${etiq.get('real', 0):,.0f}")
                print(f"       Proyectado: ${etiq.get('proyectado', 0):,.0f}")
                
                print(f"\n       Montos por periodo:")
                for periodo, monto in sorted(etiq.get('montos_por_mes', {}).items()):
                    if monto != 0:
                        print(f"         {periodo}: ${monto:,.0f}")
                
                # Buscar facturas
                for fact in etiq.get('facturas', []):
                    if 'FCXE 000281' in str(fact.get('name', '')):
                        print(f"\n       Factura FCXE 000281:")
                        print(f"         Total: ${fact.get('total', 0):,.0f}")
                        print(f"         Cobrado: ${fact.get('cobrado', 0):,.0f}")
                        print(f"         Pendiente: ${fact.get('pendiente', 0):,.0f}")
else:
    print("❌ Concepto 1.1.1 no encontrado")

print("\n✅ Debug completado")

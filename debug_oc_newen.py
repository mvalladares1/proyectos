#!/usr/bin/env python3
"""Debug: Buscar OCs de COOPERATIVA AGRICOLA NEWEN AL SUR DE LA ARAUCANIA"""

import xmlrpc.client
from datetime import datetime

URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("Conectando a Odoo...")
common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
print(f"Conectado como UID: {uid}")

# Buscar el partner
print("\n" + "="*80)
print("BUSCANDO PARTNER: COOPERATIVA AGRICOLA NEWEN AL SUR DE LA ARAUCANIA")
print("="*80)

partners = models.execute_kw(DB, uid, PASSWORD,
    'res.partner', 'search_read',
    [[('name', 'ilike', 'NEWEN AL SUR')]],
    {'fields': ['id', 'name'], 'limit': 5}
)

for p in partners:
    print(f"ID: {p['id']} - {p['name']}")

if not partners:
    print("No se encontró el partner")
    exit()

partner_id = partners[0]['id']
partner_name = partners[0]['name']

# Buscar OCs de este proveedor
print("\n" + "="*80)
print(f"BUSCANDO OCs DEL PARTNER ID={partner_id}")
print("="*80)

ocs = models.execute_kw(DB, uid, PASSWORD,
    'purchase.order', 'search_read',
    [[('partner_id', '=', partner_id)]],
    {
        'fields': [
            'id', 'name', 'state', 'amount_total', 'currency_id',
            'date_order', 'date_planned', 'date_approve',
            'x_studio_fecha_de', 'invoice_ids', 'invoice_status'
        ],
        'order': 'amount_total desc',
        'limit': 50
    }
)

print(f"\nTotal OCs encontradas: {len(ocs)}")
print("\nOCs ordenadas por monto (mayor a menor):")
print("-"*120)

total_sin_factura = 0
for oc in ocs:
    invoice_ids = oc.get('invoice_ids') or []
    tiene_factura = "SÍ" if invoice_ids else "NO"
    
    currency = oc.get('currency_id')
    currency_name = currency[1] if isinstance(currency, (list, tuple)) and len(currency) > 1 else 'CLP'
    
    amount = oc.get('amount_total', 0)
    fecha_pago = oc.get('x_studio_fecha_de') or '-'
    date_planned = oc.get('date_planned') or '-'
    state = oc.get('state', '')
    
    print(f"{oc['name']:20} | Estado: {state:10} | Monto: {amount:>20,.0f} {currency_name:5} | "
          f"Fecha Pago: {str(fecha_pago)[:10]:12} | Date Planned: {str(date_planned)[:10]:12} | "
          f"Factura: {tiene_factura} ({len(invoice_ids)})")
    
    if not invoice_ids and state in ('purchase', 'done'):
        total_sin_factura += amount

print("-"*120)
print(f"\nTOTAL OCs sin factura (purchase/done): {total_sin_factura:,.0f}")

# Buscar OCs con montos muy grandes
print("\n" + "="*80)
print("BUSCANDO OCs CON MONTOS > 1.000.000.000 (cualquier proveedor)")
print("="*80)

ocs_grandes = models.execute_kw(DB, uid, PASSWORD,
    'purchase.order', 'search_read',
    [[('amount_total', '>', 1000000000)]],
    {
        'fields': [
            'id', 'name', 'partner_id', 'state', 'amount_total', 'currency_id',
            'date_order', 'date_planned', 'x_studio_fecha_de', 'invoice_ids'
        ],
        'order': 'amount_total desc',
        'limit': 20
    }
)

print(f"\nOCs con monto > 1.000.000.000: {len(ocs_grandes)}")
for oc in ocs_grandes:
    partner = oc.get('partner_id')
    partner_name_oc = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else 'N/A'
    currency = oc.get('currency_id')
    currency_name = currency[1] if isinstance(currency, (list, tuple)) and len(currency) > 1 else 'CLP'
    invoice_ids = oc.get('invoice_ids') or []
    
    print(f"\n{oc['name']} - {partner_name_oc[:50]}")
    print(f"  Estado: {oc.get('state')} | Monto: {oc.get('amount_total'):,.0f} {currency_name}")
    print(f"  Fecha Pago: {oc.get('x_studio_fecha_de')} | Date Planned: {oc.get('date_planned')}")
    print(f"  Facturas: {len(invoice_ids)} - {invoice_ids}")

# Calcular S10 (semana 10 de marzo 2026)
print("\n" + "="*80)
print("CALCULANDO QUÉ OCs CAEN EN S10 (MAR 2-8, 2026) - NEWEN")
print("="*80)

# S10 sería aproximadamente del 2 al 8 de marzo 2026
s10_inicio = datetime(2026, 3, 2).date()
s10_fin = datetime(2026, 3, 8).date()

print(f"Rango S10: {s10_inicio} a {s10_fin}")

ocs_newen = models.execute_kw(DB, uid, PASSWORD,
    'purchase.order', 'search_read',
    [[
        ('partner_id', '=', partner_id),
        ('state', 'in', ['purchase', 'done'])
    ]],
    {
        'fields': [
            'id', 'name', 'amount_total', 'currency_id',
            'x_studio_fecha_de', 'date_planned', 'invoice_ids'
        ]
    }
)

print(f"\nOCs de NEWEN en estado purchase/done: {len(ocs_newen)}")

ocs_en_s10 = []
for oc in ocs_newen:
    invoice_ids = oc.get('invoice_ids') or []
    if invoice_ids:
        continue  # Tiene factura, no se proyecta
    
    # Determinar fecha de proyección
    fecha_pago = oc.get('x_studio_fecha_de')
    date_planned = oc.get('date_planned')
    
    fecha_str = None
    if fecha_pago:
        fecha_str = str(fecha_pago)[:10]
        origen = "x_studio_fecha_de"
    elif date_planned:
        fecha_str = str(date_planned)[:10]
        origen = "date_planned"
    else:
        continue
    
    try:
        fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except:
        continue
    
    if s10_inicio <= fecha_dt <= s10_fin:
        currency = oc.get('currency_id')
        currency_name = currency[1] if isinstance(currency, (list, tuple)) and len(currency) > 1 else 'CLP'
        ocs_en_s10.append({
            'name': oc['name'],
            'amount': oc['amount_total'],
            'currency': currency_name,
            'fecha': fecha_str,
            'origen': origen
        })

print(f"\nOCs que caen en S10 (sin factura):")
total_s10 = 0
for oc in ocs_en_s10:
    print(f"  {oc['name']}: {oc['amount']:,.0f} {oc['currency']} - Fecha: {oc['fecha']} ({oc['origen']})")
    total_s10 += oc['amount']

print(f"\nTotal S10: {total_s10:,.0f}")

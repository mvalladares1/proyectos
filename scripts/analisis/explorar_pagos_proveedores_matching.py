# -*- coding: utf-8 -*-
"""
Script de exploración para entender la estructura de pagos a proveedores
basada en matching_number.

OBJETIVO:
- Explorar campos de account.move (facturas de proveedores)
- Entender la lógica de matching_number (P, AXXXXX, blank)
- Mapear account.move.line relacionadas
"""
import sys
import os
import io

# Configurar salida UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from shared.odoo_client import OdooClient
from collections import defaultdict

# Credenciales
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

odoo = OdooClient(username=USERNAME, password=PASSWORD)

print("\n" + "="*80)
print("EXPLORACION: Pagos a Proveedores - Matching Number")
print("="*80 + "\n")

# Paso 1: Buscar diario de Facturas de Proveedores
print("[1] Paso 1: Buscando diario 'Facturas de Proveedores'...")
diarios = odoo.search_read(
    'account.journal',
    [('name', 'ilike', 'factura'), ('type', '=', 'purchase')],
    ['id', 'name', 'code', 'type']
)
print(f"Encontrados {len(diarios)} diarios de compras:")
for d in diarios:
    print(f"  - ID {d['id']}: {d['name']} ({d.get('code', 'sin código')})")

# Usar el diario correcto
DIARIO_FACTURAS_PROV = diarios[0]['id'] if diarios else None
print(f"\nOK Usando diario ID: {DIARIO_FACTURAS_PROV}\n")

# Paso 2: Buscar cuenta de Proveedores por Pagar
print("[2] Paso 2: Buscando cuenta 'Proveedores por Pagar'...")
cuentas = odoo.search_read(
    'account.account',
    [('code', '=like', '2101%')],  # Usualmente 2101 es CxP
    ['id', 'code', 'name'],
    limit=10
)
print(f"Encontradas {len(cuentas)} cuentas CxP:")
for c in cuentas:
    print(f"  - {c['code']}: {c['name']}")

CUENTA_CXP = cuentas[0]['code'] if cuentas else '21010101'
print(f"\nOK Usando cuenta: {CUENTA_CXP}\n")

# Paso 3: Buscar facturas de proveedor recientes (POSTED, desde Nov 2025)
print("[3] Paso 3: Buscando facturas de proveedor posteadas desde Nov 2025...")
facturas = odoo.search_read(
    'account.move',
    [
        ('move_type', 'in', ['in_invoice', 'in_refund']),
        ('journal_id', '=', DIARIO_FACTURAS_PROV),
        ('state', '=', 'posted'),  # Solo facturas confirmadas
        ('date', '>=', '2025-11-01')  # Desde noviembre 2025
    ],
    ['id', 'name', 'partner_id', 'date', 'invoice_date', 'state', 
     'amount_total', 'amount_residual', 'payment_state'],
    order='date desc',
    limit=100  # Aumentar límite
)

print(f"\nEncontradas {len(facturas)} facturas\n")

# Paso 3b: Para cada factura, buscar sus líneas con matching_number
print("[3b] Paso 3b: Analizando lineas (account.move.line) con matching_number...\n")

facturas_info = []
for f in facturas:
    # Buscar TODAS las líneas de esta factura
    lineas = odoo.search_read(
        'account.move.line',
        [
            ('move_id', '=', f['id']),
        ],
        ['id', 'account_id', 'debit', 'credit', 'matching_number', 'date'],
        limit=50
    )
    
    # Detectar matching_number de alguna línea
    matching_number = ''
    linea_con_matching = None
    for linea in lineas:
        match = linea.get('matching_number', '')
        if match:
            matching_number = match
            linea_con_matching = linea
            break
    
    facturas_info.append({
        'factura': f,
        'matching_number': matching_number,
        'linea_con_matching': linea_con_matching,
        'total_lineas': len(lineas)
    })

# Clasificar por matching_number
clasificacion = defaultdict(list)
for info in facturas_info:
    matching = info['matching_number']
    if not matching or matching == '':
        categoria = 'NO_PAGADO (blank)'
    elif matching == 'P':
        categoria = 'PARCIAL (P)'
    elif matching.startswith('A'):
        categoria = f'PAGADO (A*****)'
    else:
        categoria = f'OTRO ({matching})'
    
    clasificacion[categoria].append(info)

print("[4] Clasificacion por matching_number:\n")
for cat, infos in clasificacion.items():
    print(f"\n{cat}: {len(infos)} facturas")
    print("-" * 60)
    for info in infos[:3]:  # Mostrar máximo 3 ejemplos
        f = info['factura']
        partner = f.get('partner_id', [0, 'Sin nombre'])
        partner_name = partner[1] if isinstance(partner, (list, tuple)) else 'Sin nombre'
        print(f"  {f['name']} | {partner_name}")
        print(f"    Fecha: {f.get('date')} | Estado: {f.get('state')}")
        print(f"    Total: ${f.get('amount_total', 0):,.2f} | Residual: ${f.get('amount_residual', 0):,.2f}")
        print(f"    Payment State: {f.get('payment_state')}")
        print(f"    Matching: '{info['matching_number']}'")
        print(f"    Total Lineas: {info['total_lineas']}")
        if info['linea_con_matching']:
            cuenta = info['linea_con_matching'].get('account_id', [0, ''])
            cuenta_code = cuenta[1] if isinstance(cuenta, (list, tuple)) else ''
            print(f"    Linea con match: Cuenta={cuenta_code}, Debit={info['linea_con_matching'].get('debit', 0)}, Credit={info['linea_con_matching'].get('credit', 0)}")
        print()

# Paso 4: Para facturas PAGADAS (con código AXXXXX), buscar las líneas de pago
print("\n\n[5] Paso 4: Analizando lineas de pago para facturas PAGADAS\n")
facturas_pagadas = [info for cat, infos in clasificacion.items() if 'PAGADO' in cat for info in infos]

if facturas_pagadas:
    info_ejemplo = facturas_pagadas[0]
    factura_ejemplo = info_ejemplo['factura']
    matching_code = info_ejemplo['matching_number']
    
    print(f"Ejemplo: Factura {factura_ejemplo['name']}")
    print(f"Matching Number: {matching_code}\n")
    
    # Buscar account.move.line con ese matching_number  
    print(f"Buscando TODAS las líneas con matching_number = '{matching_code}'...")
    lineas_pago = odoo.search_read(
        'account.move.line',
        [('matching_number', '=', matching_code)],
        ['id', 'move_id', 'account_id', 'partner_id', 'date', 
         'debit', 'credit', 'name', 'ref', 'matching_number'],
        limit=50
    )
    
    print(f"Encontradas {len(lineas_pago)} líneas:\n")
    for linea in lineas_pago[:10]:
        move = linea.get('move_id', [0, ''])
        move_name = move[1] if isinstance(move, (list, tuple)) else ''
        account = linea.get('account_id', [0, ''])
        account_name = account[1] if isinstance(account, (list, tuple)) else ''
        
        print(f"  Línea {linea['id']} - Asiento: {move_name}")
        print(f"    Fecha: {linea.get('date')} | Cuenta: {account_name}")
        print(f"    Débito: ${linea.get('debit', 0):,.2f} | Crédito: ${linea.get('credit', 0):,.2f}")
        print(f"    Ref: {linea.get('ref', 'Sin ref')}")
        print()
else:
   print("No se encontraron facturas PAGADAS en la muestra")

# Paso 5: Para facturas PARCIALES (P), analizar las líneas
print("\n\n[6] Paso 5: Analizando facturas PARCIALMENTE PAGADAS (P)\n")
facturas_parciales = clasificacion.get('PARCIAL (P)', [])

if facturas_parciales:
    info_parcial = facturas_parciales[0]
    factura_parcial = info_parcial['factura']
    
    print(f"Ejemplo: Factura {factura_parcial['name']}")
    print(f"Total: ${factura_parcial.get('amount_total', 0):,.2f}")
    print(f"Residual: ${factura_parcial.get('amount_residual', 0):,.2f}\n")
    
    # Buscar líneas de esta factura
    lineas_factura = odoo.search_read(
        'account.move.line',
        [('move_id', '=', factura_parcial['id'])],
        ['id', 'account_id', 'date', 'debit', 'credit', 'name', 'matching_number'],
        limit=50
    )
    
    print(f"Líneas de la factura ({len(lineas_factura)} encontradas):\n")
    for linea in lineas_factura:
        account = linea.get('account_id', [0, ''])
        account_code = account[1] if isinstance(account, (list, tuple)) else ''
        
        print(f"  Línea {linea['id']}: {linea.get('name', 'Sin nombre')}")
        print(f"    Cuenta: {account_code}")
        print(f"    Débito: ${linea.get('debit', 0):,.2f} | Crédito: ${linea.get('credit', 0):,.2f}")
        print(f"    Matching: '{linea.get('matching_number', '')}'")
        print()
else:
    print("No se encontraron facturas PARCIALES en la muestra")

print("\n" + "="*80)
print("OK Exploracion completada")
print("="*80 + "\n")

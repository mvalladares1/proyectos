"""
Debug: Ver contrapartidas de los asientos de 21010223
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

print("="*80)
print("CONTRAPARTIDAS DE ASIENTOS 21010223")
print("="*80)

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

# IDs de asientos de enero (posted)
asientos_enero = [
    # Buscar los asientos de enero
]

# Primero buscar las líneas de enero posted
lineas_enero = odoo.search_read(
    'account.move.line',
    [
        ('account_id.code', '=', '21010223'),
        ('date', '>=', '2026-01-01'),
        ('date', '<=', '2026-01-31'),
        ('parent_state', '=', 'posted')
    ],
    ['move_id'],
    limit=10
)

if not lineas_enero:
    print("No hay líneas de enero")
else:
    asientos_ids = [l['move_id'][0] for l in lineas_enero]
    print(f"\nAsientos de enero: {asientos_ids}\n")
    
    # Ver TODAS las líneas de estos asientos
    todas_lineas = odoo.search_read(
        'account.move.line',
        [
            ('move_id', 'in', asientos_ids)
        ],
        ['move_id', 'account_id', 'name', 'debit', 'credit', 'balance'],
        limit=100
    )
    
    # Agrupar por asiento
    asientos = {}
    for linea in todas_lineas:
        move_id = linea['move_id'][0]
        move_name = linea['move_id'][1]
        
        if move_id not in asientos:
            asientos[move_id] = {
                'nombre': move_name,
                'lineas': []
            }
        
        asientos[move_id]['lineas'].append(linea)
    
    # Mostrar cada asiento
    for move_id, data in asientos.items():
        print(f"\n{'='*80}")
        print(f"ASIENTO: {data['nombre']}")
        print(f"{'='*80}")
        
        print(f"{'Cuenta':<25} {'Nombre':<40} {'Debit':>15} {'Credit':>15}")
        print("-" * 100)
        
        for l in data['lineas']:
            cuenta = l['account_id'][1] if l.get('account_id') else 'N/A'
            nombre = l.get('name', '')[:40]
            debit = l.get('debit', 0)
            credit = l.get('credit', 0)
            
            print(f"{cuenta[:25]:<25} {nombre:<40} {debit:>15,.0f} {credit:>15,.0f}")

print("\n" + "="*80)

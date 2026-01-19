"""
Debug: Ver TODOS los movimientos de 21010223 sin filtrar por efectivo
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

codigo_cuenta = "21010223"
fecha_inicio = "2026-01-01"
fecha_fin = "2026-03-31"

print("="*80)
print(f"DEBUG TODAS LAS LÍNEAS DE {codigo_cuenta} (SIN FILTRO EFECTIVO)")
print("="*80)

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

# Buscar TODAS las líneas de la cuenta, sin importar si tocan efectivo
lineas = odoo.search_read(
    'account.move.line',
    [
        ('account_id.code', '=', codigo_cuenta),
        ('date', '>=', fecha_inicio),
        ('date', '<=', fecha_fin)
    ],
    ['date', 'name', 'debit', 'credit', 'balance', 'move_id', 'parent_state', 'account_id'],
    limit=100
)

print(f"\nTotal líneas: {len(lineas)}\n")

if len(lineas) == 0:
    print("⚠️ NO HAY LÍNEAS en esta cuenta para el periodo")
else:
    print("Líneas encontradas:")
    print("-" * 120)
    print(f"{'Fecha':<12} {'Estado':<8} {'Debit':>15} {'Credit':>15} {'Balance':>15} {'Asiento':<30} {'Nombre':<30}")
    print("-" * 120)
    
    for l in lineas:
        fecha = l.get('date', '')
        estado = l.get('parent_state', 'N/A')
        debit = l.get('debit', 0)
        credit = l.get('credit', 0)
        balance = l.get('balance', 0)
        move_name = l.get('move_id', ['', ''])[1] if l.get('move_id') else 'N/A'
        nombre = l.get('name', '')[:30]
        
        print(f"{fecha:<12} {estado:<8} {debit:>15,.2f} {credit:>15,.2f} {balance:>15,.2f} {move_name[:30]:<30} {nombre:<30}")

print("\n" + "="*80)

"""
Debug: Analizar cuenta 82010102 (INTERESES POR LEASING) - ¿Toca efectivo?
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

print("="*100)
print("ANÁLISIS CUENTA 82010102 - INTERESES POR LEASING")
print("="*100)

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

# 1. Obtener cuentas de efectivo
cuentas_efectivo = odoo.search_read(
    'account.account',
    [('account_type', '=', 'asset_cash')],
    ['id', 'code', 'name']
)
cuentas_efectivo_ids = [c['id'] for c in cuentas_efectivo]
print(f"\n1. Cuentas de efectivo: {len(cuentas_efectivo_ids)}")

# 2. Buscar TODAS las líneas de 82010102 en enero-marzo 2026
lineas_82010102 = odoo.search_read(
    'account.move.line',
    [
        ('account_id.code', '=', '82010102'),
        ('date', '>=', '2026-01-01'),
        ('date', '<=', '2026-03-31')
    ],
    ['date', 'name', 'debit', 'credit', 'balance', 'move_id', 'parent_state'],
    limit=100
)

print(f"\n2. Total líneas de 82010102: {len(lineas_82010102)}")

if len(lineas_82010102) == 0:
    print("   ⚠️ NO HAY LÍNEAS en esta cuenta")
    sys.exit(0)

# 3. Por cada línea, verificar si el asiento toca efectivo
print("\n3. Analizando cada línea y sus contrapartidas...\n")
print("-" * 100)
print(f"{'Fecha':<12} {'Estado':<8} {'Debit':>15} {'Credit':>15} {'Etiqueta':<40} {'¿Efectivo?'}")
print("-" * 100)

lineas_con_efectivo = 0
lineas_sin_efectivo = 0

for linea in lineas_82010102:
    fecha = linea.get('date', '')
    estado = linea.get('parent_state', '')
    debit = linea.get('debit', 0)
    credit = linea.get('credit', 0)
    nombre = linea.get('name', '')[:40]
    move_id = linea['move_id'][0] if linea.get('move_id') else None
    
    # Buscar todas las líneas del mismo asiento
    if move_id:
        todas_lineas = odoo.search_read(
            'account.move.line',
            [('move_id', '=', move_id)],
            ['account_id'],
            limit=50
        )
        
        # Ver si alguna línea del asiento toca efectivo
        toca_efectivo = any(
            l['account_id'][0] in cuentas_efectivo_ids 
            for l in todas_lineas 
            if l.get('account_id')
        )
        
        efectivo_str = "✓ SÍ" if toca_efectivo else "✗ NO"
        
        if toca_efectivo:
            lineas_con_efectivo += 1
        else:
            lineas_sin_efectivo += 1
        
        print(f"{fecha:<12} {estado:<8} {debit:>15,.0f} {credit:>15,.0f} {nombre:<40} {efectivo_str}")

print("-" * 100)
print(f"\nRESUMEN:")
print(f"  Líneas que SÍ tocan efectivo: {lineas_con_efectivo}")
print(f"  Líneas que NO tocan efectivo: {lineas_sin_efectivo}")

# 4. Mostrar contrapartidas de las líneas que SÍ tocan efectivo
if lineas_con_efectivo > 0:
    print("\n4. CONTRAPARTIDAS de asientos que tocan efectivo:\n")
    
    asientos_mostrados = set()
    
    for linea in lineas_82010102:
        move_id = linea['move_id'][0] if linea.get('move_id') else None
        
        if not move_id or move_id in asientos_mostrados:
            continue
        
        # Verificar si toca efectivo
        todas_lineas = odoo.search_read(
            'account.move.line',
            [('move_id', '=', move_id)],
            ['account_id', 'name', 'debit', 'credit'],
            limit=50
        )
        
        toca_efectivo = any(
            l['account_id'][0] in cuentas_efectivo_ids 
            for l in todas_lineas 
            if l.get('account_id')
        )
        
        if toca_efectivo:
            asientos_mostrados.add(move_id)
            move_name = linea['move_id'][1]
            
            print(f"\n{'='*100}")
            print(f"ASIENTO: {move_name} - Fecha: {linea.get('date')}")
            print(f"{'='*100}")
            print(f"{'Cuenta':<30} {'Nombre':<40} {'Debit':>15} {'Credit':>15}")
            print("-" * 100)
            
            for l in todas_lineas:
                cuenta_str = l['account_id'][1][:30] if l.get('account_id') else 'N/A'
                nombre = l.get('name', '')[:40]
                debit = l.get('debit', 0)
                credit = l.get('credit', 0)
                
                es_efectivo = l['account_id'][0] in cuentas_efectivo_ids if l.get('account_id') else False
                marca = " ← EFECTIVO" if es_efectivo else ""
                
                print(f"{cuenta_str:<30} {nombre:<40} {debit:>15,.0f} {credit:>15,.0f}{marca}")

print("\n" + "="*100)

"""
Debug sistemático de TODAS las cuentas que aparecen en flujo de caja enero-marzo 2026
Verificar: ¿tocan efectivo? ¿signo correcto? ¿clasificación correcta?
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

print("="*100)
print("ANÁLISIS SISTEMÁTICO FLUJO DE CAJA ENERO-MARZO 2026")
print("="*100)

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

# Cuentas que aparecen en el flujo según las imágenes
cuentas_analizar = [
    "21010223",  # PRESTAMOS LP BANCOS US$ - aparece en 3.0.1 con $6.9M en feb/mar
    "21010213",  # PRESTAMOS LP BANCOS $ - aparece en 3.0.1
    "21010102",  # PRESTAMOS CP BANCOS US$ - aparece en 3.0.2 con valores negativos
    "82010101",  # INTERESES FINANCIEROS
    "82010102",  # INTERESES POR LEASING
]

fecha_inicio = "2026-01-01"
fecha_fin = "2026-03-31"

# 1. Obtener cuentas de efectivo
print("\n1. Identificando cuentas de efectivo...")
cuentas_efectivo = odoo.search_read(
    'account.account',
    [('account_type', '=', 'asset_cash')],
    ['id', 'code', 'name']
)
cuentas_efectivo_ids = [c['id'] for c in cuentas_efectivo]
print(f"   OK {len(cuentas_efectivo_ids)} cuentas de efectivo")

# 2. Obtener asientos que tocan efectivo
print("\n2. Obteniendo asientos que tocan efectivo en el periodo...")
movimientos_efectivo = odoo.search_read(
    'account.move.line',
    [
        ('account_id', 'in', cuentas_efectivo_ids),
        ('parent_state', 'in', ['posted', 'draft']),
        ('date', '>=', fecha_inicio),
        ('date', '<=', fecha_fin)
    ],
    ['move_id'],
    limit=5000
)
asientos_efectivo_ids = list(set(m['move_id'][0] for m in movimientos_efectivo if m.get('move_id')))
print(f"   OK {len(asientos_efectivo_ids)} asientos que tocan efectivo")

# 3. Analizar cada cuenta
for codigo in cuentas_analizar:
    print("\n" + "="*100)
    print(f"CUENTA: {codigo}")
    print("="*100)
    
    # 3a. Buscar la cuenta
    cuenta_info = odoo.search_read(
        'account.account',
        [('code', '=', codigo)],
        ['id', 'name']
    )
    
    if not cuenta_info:
        print(f"   NO ENCONTRADA")
        continue
    
    account_id = cuenta_info[0]['id']
    account_name = cuenta_info[0]['name']
    print(f"\nNombre: {account_name}")
    
    # 3b. Buscar TODAS las líneas de esta cuenta en el periodo
    todas_lineas = odoo.search_read(
        'account.move.line',
        [
            ('account_id', '=', account_id),
            ('date', '>=', fecha_inicio),
            ('date', '<=', fecha_fin)
        ],
        ['move_id', 'date', 'name', 'debit', 'credit', 'balance', 'parent_state'],
        limit=100
    )
    
    print(f"\nTotal líneas en periodo: {len(todas_lineas)}")
    
    if len(todas_lineas) == 0:
        print("   ℹ️  Sin movimientos")
        continue
    
    # 3c. Filtrar cuáles tocan efectivo
    lineas_con_efectivo = [l for l in todas_lineas if l['move_id'][0] in asientos_efectivo_ids]
    lineas_sin_efectivo = [l for l in todas_lineas if l['move_id'][0] not in asientos_efectivo_ids]
    
    print(f"   ✓ Tocan efectivo: {len(lineas_con_efectivo)}")
    print(f"   ✗ NO tocan efectivo: {len(lineas_sin_efectivo)}")
    
    # 3d. Sumarizar por mes
    meses = {}
    for linea in todas_lineas:
        fecha = linea.get('date', '')
        mes = fecha[:7] if fecha else 'N/A'
        estado = linea.get('parent_state', 'N/A')
        toca_efectivo = linea['move_id'][0] in asientos_efectivo_ids
        
        key = f"{mes}_{estado}_{'EFECTIVO' if toca_efectivo else 'NO_EFECTIVO'}"
        
        if key not in meses:
            meses[key] = {'debit': 0, 'credit': 0, 'balance': 0, 'count': 0}
        
        meses[key]['debit'] += linea.get('debit', 0)
        meses[key]['credit'] += linea.get('credit', 0)
        meses[key]['balance'] += linea.get('balance', 0)
        meses[key]['count'] += 1
    
    # Mostrar resumen por mes
    print("\nRESUMEN POR MES:")
    print(f"{'Mes':<10} {'Estado':<8} {'Efectivo?':<12} {'Líneas':<8} {'Debit':>15} {'Credit':>15} {'Balance':>15}")
    print("-" * 100)
    
    for key in sorted(meses.keys()):
        parts = key.split('_')
        mes = parts[0]
        estado = parts[1]
        efectivo = parts[2]
        datos = meses[key]
        
        print(f"{mes:<10} {estado:<8} {efectivo:<12} {datos['count']:<8} {datos['debit']:>15,.0f} {datos['credit']:>15,.0f} {datos['balance']:>15,.0f}")
    
    # 3e. Ver contrapartidas de las que SÍ tocan efectivo
    if lineas_con_efectivo:
        print("\nCONTRAPARTIDAS (solo líneas que tocan efectivo):")
        asientos_muestra = list(set([l['move_id'][0] for l in lineas_con_efectivo[:3]]))  # Primeros 3 asientos
        
        for asiento_id in asientos_muestra:
            todas_lineas_asiento = odoo.search_read(
                'account.move.line',
                [('move_id', '=', asiento_id)],
                ['account_id', 'name', 'debit', 'credit', 'move_id'],
                limit=20
            )
            
            asiento_name = todas_lineas_asiento[0]['move_id'][1] if todas_lineas_asiento else 'N/A'
            print(f"\n  Asiento: {asiento_name}")
            print(f"  {'Cuenta':<30} {'Nombre':<40} {'Debit':>12} {'Credit':>12}")
            print("  " + "-" * 100)
            
            for linea in todas_lineas_asiento:
                cuenta = linea['account_id'][1][:30] if linea.get('account_id') else 'N/A'
                nombre = linea.get('name', '')[:40]
                debit = linea.get('debit', 0)
                credit = linea.get('credit', 0)
                
                # Marcar si es efectivo
                es_efectivo = linea['account_id'][0] in cuentas_efectivo_ids if linea.get('account_id') else False
                marca = "💰" if es_efectivo else "  "
                
                print(f"  {marca} {cuenta:<30} {nombre:<40} {debit:>12,.0f} {credit:>12,.0f}")

print("\n" + "="*100)
print("FIN DEL ANÁLISIS")
print("="*100)

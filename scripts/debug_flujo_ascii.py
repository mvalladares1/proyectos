import sys
import os

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.odoo_client import OdooClient

# Initialize connection
odoo = OdooClient()
if not odoo.uid:
    print("ERROR: No se pudo conectar a Odoo")
    sys.exit(1)

print("Conexion a Odoo exitosa")

# Periodo
fecha_inicio = '2026-01-01'
fecha_fin = '2026-03-31'

# Cuentas a analizar (basado en screenshots del usuario)
cuentas_analizar = [
    '21010223',  # PRESTAMOS LP BANCOS US$ - muestra valores pero NO toca efectivo
    '21010213',  # Otra cuenta LP visible en screenshot
    '21010102',  # PRESTAMOS CP BANCOS US$ - muestra valores negativos
    '82010101',  # INTERESES FINANCIEROS
    '82010102',  # INTERESES POR LEASING
]

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
        ['id', 'name', 'account_type']
    )
    
    if not cuenta_info:
        print(f"   NO ENCONTRADA")
        continue
    
    account_id = cuenta_info[0]['id']
    account_name = cuenta_info[0]['name']
    account_type = cuenta_info[0]['account_type']
    print(f"\nNombre: {account_name}")
    print(f"Tipo: {account_type}")
    
    # 3b. Buscar TODAS las lineas de esta cuenta en el periodo
    todas_lineas = odoo.search_read(
        'account.move.line',
        [
            ('account_id', '=', account_id),
            ('date', '>=', fecha_inicio),
            ('date', '<=', fecha_fin),
            ('parent_state', 'in', ['posted', 'draft'])
        ],
        ['move_id', 'date', 'name', 'debit', 'credit', 'balance', 'parent_state'],
        limit=1000
    )
    
    print(f"\nTotal lineas en periodo: {len(todas_lineas)}")
    
    if len(todas_lineas) == 0:
        print("   INFO: Sin movimientos")
        continue
    
    # 3c. Filtrar cuales tocan efectivo
    lineas_con_efectivo = [l for l in todas_lineas if l['move_id'][0] in asientos_efectivo_ids]
    lineas_sin_efectivo = [l for l in todas_lineas if l['move_id'][0] not in asientos_efectivo_ids]
    
    print(f"   [CASH] Tocan efectivo: {len(lineas_con_efectivo)} lineas")
    print(f"   [NO]   NO tocan efectivo: {len(lineas_sin_efectivo)} lineas")
    
    # 3d. Sumarizar por mes
    print(f"\nRESUMEN POR MES Y ESTADO:")
    
    resumen = {}
    for linea in todas_lineas:
        fecha = linea.get('date', '')
        mes = fecha[:7] if fecha else 'N/A'
        estado = linea.get('parent_state', 'N/A')
        toca_efectivo = linea['move_id'][0] in asientos_efectivo_ids
        
        key = (mes, estado, toca_efectivo)
        
        if key not in resumen:
            resumen[key] = {'count': 0, 'debit': 0, 'credit': 0, 'balance': 0}
        
        resumen[key]['count'] += 1
        resumen[key]['debit'] += linea['debit']
        resumen[key]['credit'] += linea['credit']
        resumen[key]['balance'] += linea['balance']
    
    for (mes, estado, toca_efectivo), data in sorted(resumen.items()):
        efectivo_str = '[CASH]' if toca_efectivo else '[NO]  '
        debit_fmt = f"{data['debit']:>15,.0f}"
        credit_fmt = f"{data['credit']:>15,.0f}"
        balance_fmt = f"{data['balance']:>15,.0f}"
        print(f"   {mes} {efectivo_str} [{estado:6s}]: {data['count']:2d} lineas | Debit: ${debit_fmt} | Credit: ${credit_fmt} | Balance: ${balance_fmt}")
    
    # 3e. Mostrar contrapartidas de las primeras 3 lineas CON efectivo
    if lineas_con_efectivo:
        print(f"\nCONTRAPARTIDAS (Primeras 3 lineas CON efectivo):")
        for i, line in enumerate(lineas_con_efectivo[:3]):
            move_id = line['move_id'][0]
            move_name = line['move_id'][1]
            
            debit_line = f"{line['debit']:,.0f}"
            credit_line = f"{line['credit']:,.0f}"
            print(f"\n   Linea {i+1}: {move_name} | Fecha: {line['date']}")
            print(f"      Esta linea: Debit ${debit_line} | Credit ${credit_line}")
            
            # Obtener todas las lineas del asiento
            asiento_lines = odoo.search_read(
                'account.move.line',
                [('move_id', '=', move_id)],
                ['account_id', 'name', 'debit', 'credit']
            )
            
            print(f"      Todas las lineas del asiento:")
            for al in asiento_lines:
                acc_code = al['account_id'][1].split()[0] if al['account_id'] else 'N/A'
                is_current = '*' if al['id'] == line['id'] else ' '
                debit_al = f"{al['debit']:,.0f}"
                credit_al = f"{al['credit']:,.0f}"
                print(f"       {is_current} {acc_code}: Debit ${debit_al} | Credit ${credit_al}")

print("\n" + "="*100)
print("ANALISIS COMPLETADO")
print("="*100)

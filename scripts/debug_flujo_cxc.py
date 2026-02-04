"""
Script de debug para verificar la nueva estructura de Flujo de Caja CxC.
Valida que las facturas se agrupen por payment_state y tengan los datos correctos para modal.
"""
import xmlrpc.client
from collections import defaultdict
from datetime import datetime

# Configuración
url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
print(f"✅ Conectado como UID: {uid}")

# Parámetros de consulta
fecha_inicio = "2024-10-01"
fecha_fin = "2025-01-31"
cuentas_monitoreadas = ["11030101"]  # Deudores por Ventas

# 1. Obtener IDs de cuentas
print(f"\n{'='*60}")
print("1. OBTENIENDO CUENTAS MONITOREADAS")
print('='*60)
cuentas = models.execute_kw(db, uid, password, 'account.account', 'search_read',
    [[['code', 'in', cuentas_monitoreadas]]],
    {'fields': ['id', 'code', 'name']}
)
account_ids = [c['id'] for c in cuentas]
print(f"Cuentas: {cuentas}")
print(f"IDs: {account_ids}")

# 2. Buscar facturas con estado de pago
print(f"\n{'='*60}")
print("2. BUSCANDO FACTURAS DE CLIENTE (out_invoice, out_refund)")
print('='*60)

# Domain: Facturas de cliente, publicadas
# ESTRATEGIA: Buscar TODO el historial + pendientes
# Opción 1: Fechas en rango (historial)
# Opción 2: No pagadas (proyección)
domain = [
    ['move_type', 'in', ['out_invoice', 'out_refund']],
    ['state', '=', 'posted'],
    '|',
    # Historial: cualquier fecha en rango
    '|',
    '&', '&',
        ['x_studio_fecha_de_pago', '!=', False],
        ['x_studio_fecha_de_pago', '>=', fecha_inicio],
        ['x_studio_fecha_de_pago', '<=', fecha_fin],
    '&', '&',
        ['x_studio_fecha_de_pago', '=', False],
        ['date', '>=', fecha_inicio],
        ['date', '<=', fecha_fin],
    # Proyección: facturas no pagadas (sin importar fecha)
    ['payment_state', 'in', ['not_paid', 'partial', 'in_payment']]
]

moves = models.execute_kw(db, uid, password, 'account.move', 'search_read',
    [domain],
    {'fields': ['id', 'name', 'x_studio_fecha_de_pago', 'date', 'move_type', 
                'payment_state', 'amount_total', 'amount_residual', 'partner_id',
                'invoice_date', 'invoice_date_due']}
)
print(f"Total facturas encontradas: {len(moves)}")

# 3. Agrupar por payment_state
print(f"\n{'='*60}")
print("3. AGRUPANDO POR PAYMENT_STATE")
print('='*60)

ESTADO_LABELS = {
    'paid': 'Facturas Pagadas',
    'partial': 'Facturas Parcialmente Pagadas',
    'in_payment': 'En Proceso de Pago',
    'not_paid': 'Facturas No Pagadas',
    'reversed': 'Facturas Revertidas'
}

por_estado = defaultdict(list)
totales_por_estado = defaultdict(float)

for move in moves:
    estado = move.get('payment_state', 'not_paid')
    fecha_pago = move.get('x_studio_fecha_de_pago') or move.get('date')
    mes = fecha_pago[:7] if fecha_pago else 'SIN_MES'
    
    por_estado[estado].append({
        'nombre': move['name'],
        'partner': move.get('partner_id', [0, ''])[1] if isinstance(move.get('partner_id'), list) else '',
        'amount_total': move.get('amount_total', 0),
        'amount_residual': move.get('amount_residual', 0),
        'fecha_pago': fecha_pago,
        'mes': mes,
        'payment_state': estado
    })
    totales_por_estado[estado] += move.get('amount_total', 0)

for estado, label in ESTADO_LABELS.items():
    facturas = por_estado.get(estado, [])
    total = totales_por_estado.get(estado, 0)
    print(f"\n{label}: {len(facturas)} facturas, Total: ${total:,.0f}")
    
    # Mostrar primeras 5 facturas de cada estado
    for f in facturas[:5]:
        print(f"  - {f['nombre']} | {f['partner'][:30]} | ${f['amount_total']:,.0f} | Mes: {f['mes']}")
    if len(facturas) > 5:
        print(f"  ... y {len(facturas)-5} más")

# 4. Agrupar por mes y estado
print(f"\n{'='*60}")
print("4. TOTALES POR MES Y ESTADO")
print('='*60)

# Crear estructura {estado: {mes: total}} usando los datos ya agrupados
todos_meses = set()
for estado, facturas in por_estado.items():
    for f in facturas:
        todos_meses.add(f['mes'])
meses = sorted(todos_meses)

print(f"\nMeses encontrados: {meses}")
print("\nMatriz de totales:")
print(f"{'Estado':<35} | " + " | ".join(f"{m:>12}" for m in meses))
print("-" * (35 + 15 * len(meses)))

for estado, label in ESTADO_LABELS.items():
    facturas = por_estado.get(estado, [])
    totales_mes = defaultdict(float)
    for f in facturas:
        totales_mes[f['mes']] += f['amount_total']
    
    valores = " | ".join(f"${totales_mes.get(m, 0):>10,.0f}" for m in meses)
    print(f"{label:<35} | {valores}")

# 5. Verificar líneas contables en cuenta CxC
print(f"\n{'='*60}")
print("5. LÍNEAS CONTABLES EN CUENTA CXC (11030101)")
print('='*60)

if account_ids:
    move_ids = [m['id'] for m in moves]
    if move_ids:
        lineas = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
            [[['account_id', 'in', account_ids], ['move_id', 'in', move_ids[:100]]]],  # Limitar para debug
            {'fields': ['account_id', 'name', 'balance', 'date', 'move_id'], 'limit': 500}
        )
        print(f"Líneas encontradas: {len(lineas)}")
        
        # Agrupar líneas por factura
        lineas_por_move = defaultdict(list)
        for l in lineas:
            mid = l['move_id'][0] if isinstance(l.get('move_id'), (list, tuple)) else l.get('move_id')
            lineas_por_move[mid].append(l)
        
        print(f"Facturas con líneas CxC: {len(lineas_por_move)}")
        
        # Mostrar algunas
        for mid, lineas_m in list(lineas_por_move.items())[:5]:
            move_info = next((m for m in moves if m['id'] == mid), {})
            total_lineas = sum(l.get('balance', 0) for l in lineas_m)
            print(f"  - {move_info.get('name', mid)}: {len(lineas_m)} líneas, balance total: ${total_lineas:,.0f}")

print(f"\n{'='*60}")
print("DEBUG COMPLETADO")
print('='*60)

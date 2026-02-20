"""
Debug script para analizar:
1. Diarios disponibles - buscar "Proyecciones Futuras"
2. Payment states en facturas de clientes
3. Comportamiento de facturas revertidas (N/C)
"""
import sys
sys.path.insert(0, r'c:\new\RIO FUTURO\DASHBOARD\proyectos')

from xmlrpc import client as xmlrpc_client

# Credenciales Odoo
url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Conectar
common = xmlrpc_client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
if not uid:
    print("Error de autenticación")
    sys.exit(1)

models = xmlrpc_client.ServerProxy(f'{url}/xmlrpc/2/object')

def search_read(model, domain, fields, limit=500):
    return models.execute_kw(db, uid, password, model, 'search_read', [domain], {'fields': fields, 'limit': limit})

print("=" * 60)
print("1. TODOS LOS DIARIOS CONTABLES (account.journal)")
print("=" * 60)

diarios = search_read('account.journal', [], ['id', 'name', 'type', 'code'], limit=100)
for d in sorted(diarios, key=lambda x: x['id']):
    print(f"  ID {d['id']:3d}: {d['name']:<40} | Tipo: {d['type']:<10} | Código: {d.get('code', '')}")

# Buscar Proyecciones Futuras específicamente
proyecciones = [d for d in diarios if 'proyecc' in d['name'].lower() or 'futur' in d['name'].lower()]
if proyecciones:
    print("\n🔍 DIARIOS RELACIONADOS CON PROYECCIONES:")
    for d in proyecciones:
        print(f"   >>> ID {d['id']}: {d['name']}")

print("\n" + "=" * 60)
print("2. PAYMENT STATES EN FACTURAS DE CLIENTES (2024-01 a 2026-12)")
print("=" * 60)

# Facturas
facturas_cliente = search_read(
    'account.move',
    [
        ['move_type', 'in', ['out_invoice', 'out_refund']],
        ['state', '=', 'posted'],
        ['invoice_date', '>=', '2024-01-01'],
        ['invoice_date', '<=', '2026-12-31']
    ],
    ['id', 'name', 'move_type', 'payment_state', 'amount_total', 'amount_residual'],
    limit=10000
)

print(f"\nTotal facturas/N/C de clientes encontradas: {len(facturas_cliente)}")

# Agrupar por payment_state y move_type
from collections import defaultdict, Counter

stats = defaultdict(lambda: {'count': 0, 'total': 0, 'out_invoice': 0, 'out_refund': 0})

for f in facturas_cliente:
    ps = f.get('payment_state', 'unknown')
    mt = f.get('move_type', 'unknown')
    stats[ps]['count'] += 1
    stats[ps]['total'] += f.get('amount_total', 0) or 0
    stats[ps][mt] += 1

print("\nEstadísticas por payment_state:")
print("-" * 80)
print(f"{'Payment State':<20} | {'Count':>8} | {'Facturas':>10} | {'N/C':>10} | {'Monto Total':>18}")
print("-" * 80)

for ps in sorted(stats.keys()):
    data = stats[ps]
    print(f"{ps:<20} | {data['count']:>8} | {data['out_invoice']:>10} | {data['out_refund']:>10} | ${data['total']:>15,.0f}")

print("-" * 80)

print("\n" + "=" * 60)
print("3. EJEMPLOS DE FACTURAS 'REVERSED'")
print("=" * 60)

reversed_samples = [f for f in facturas_cliente if f.get('payment_state') == 'reversed'][:5]
if reversed_samples:
    for f in reversed_samples:
        print(f"  {f['name']:<20} | Tipo: {f['move_type']:<12} | Total: ${f['amount_total']:>12,.0f} | Residual: ${f['amount_residual']:>12,.0f}")
else:
    print("  No hay facturas con payment_state='reversed'")

print("\n" + "=" * 60)
print("4. FACTURAS EN DIARIO 'PROYECCIONES FUTURAS' (si existe)")
print("=" * 60)

# Buscar diario por nombre
diario_proyecciones = None
for d in diarios:
    if 'proyecc' in d['name'].lower():
        diario_proyecciones = d
        break

if diario_proyecciones:
    print(f"Usando diario ID={diario_proyecciones['id']}: {diario_proyecciones['name']}")
    
    facturas_proyecciones = search_read(
        'account.move',
        [
            ['journal_id', '=', diario_proyecciones['id']],
            ['move_type', 'in', ['in_invoice', 'in_refund']],
        ],
        ['id', 'name', 'state', 'move_type', 'partner_id', 'amount_total', 'date', 'invoice_date'],
        limit=100
    )
    
    print(f"\nFacturas encontradas: {len(facturas_proyecciones)}")
    
    if facturas_proyecciones:
        # Agrupar por estado
        por_estado = defaultdict(list)
        for f in facturas_proyecciones:
            por_estado[f.get('state', 'unknown')].append(f)
        
        print("\nPor estado de factura (state):")
        for estado, lista in sorted(por_estado.items()):
            total = sum(f.get('amount_total', 0) or 0 for f in lista)
            print(f"  {estado}: {len(lista)} facturas - Total: ${total:,.0f}")
        
        print("\nEjemplos:")
        for f in facturas_proyecciones[:10]:
            partner = f.get('partner_id', [0, 'N/A'])
            partner_name = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else 'N/A'
            print(f"  {f['name']:<25} | {f['state']:<10} | {partner_name:<30} | ${f.get('amount_total', 0):>12,.0f} | {f.get('date', '')}")
else:
    print("No se encontró diario de Proyecciones")

print("\n✅ Debug completado")

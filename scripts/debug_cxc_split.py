"""Debug script para diagnosticar CxC split y categorías para FCXE 000284 TRONADOR."""
import xmlrpc.client
import os

url = os.getenv('ODOO_URL', 'https://riofuturo.server98c6e.oerpondemand.net')
db = os.getenv('ODOO_DB', 'riofuturo-master')
username = os.getenv('ODOO_USER', 'mvalladares@riofuturo.cl')
password = os.getenv('ODOO_PASSWORD', '')

# Try multiple credentials
creds_to_try = [
    (username, password),
    ('mvalladares@riofuturo.cl', 'Rv25*Rf'),
    ('mvalladares@riofuturo.cl', 'Rf3490*'),
]

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = None
used_pass = None

for u, p in creds_to_try:
    if not p:
        continue
    try:
        uid = common.authenticate(db, u, p, {})
        if uid:
            used_pass = p
            print(f"Authenticated as {u} (uid={uid})")
            break
    except Exception as e:
        print(f"Auth failed for {u}: {e}")

if not uid:
    print("FAILED to authenticate with any credentials")
    exit(1)

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

def search_read(model, domain, fields, limit=None):
    kwargs = {'fields': fields}
    if limit:
        kwargs['limit'] = limit
    return models.execute_kw(db, uid, used_pass, model, 'search_read', [domain], kwargs)

print("=" * 80)
print("1. BUSCAR FCXE 000284 EN account.move")
print("=" * 80)

# Buscar la factura específica
moves = search_read(
    'account.move',
    [['name', 'like', 'FCXE 000284']],
    ['id', 'name', 'move_type', 'state', 'payment_state', 'partner_id', 
     'amount_total', 'amount_residual', 'amount_total_signed', 'amount_residual_signed',
     'date', 'x_studio_fecha_de_pago', 'currency_id', 'company_currency_id']
)

for m in moves:
    print(f"\n  Move ID: {m['id']}")
    print(f"  Name: {m['name']}")
    print(f"  move_type: {m['move_type']}")
    print(f"  state: {m['state']}")
    print(f"  payment_state: {m['payment_state']}")
    print(f"  partner_id: {m['partner_id']}")
    print(f"  amount_total: {m['amount_total']} (type: {type(m['amount_total']).__name__})")
    print(f"  amount_residual: {m['amount_residual']} (type: {type(m['amount_residual']).__name__})")
    print(f"  amount_total_signed: {m.get('amount_total_signed')}")
    print(f"  amount_residual_signed: {m.get('amount_residual_signed')}")
    print(f"  date: {m['date']}")
    print(f"  x_studio_fecha_de_pago: {m['x_studio_fecha_de_pago']}")
    print(f"  currency_id: {m['currency_id']}")
    print(f"  company_currency_id: {m.get('company_currency_id')}")
    
    move_id = m['id']
    
    # Buscar líneas de esta factura en cuentas CxC
    lines = search_read(
        'account.move.line',
        [['move_id', '=', move_id], ['account_id.code', 'in', ['11030101', '11030103']]],
        ['id', 'name', 'balance', 'amount_currency', 'currency_id', 'account_id', 'move_id']
    )
    
    print(f"\n  LÍNEAS CxC de esta factura ({len(lines)}):")
    for l in lines:
        print(f"    Line ID: {l['id']}")
        print(f"    account: {l['account_id']}")
        print(f"    balance (CLP): {l['balance']}")
        print(f"    amount_currency: {l['amount_currency']}")
        print(f"    currency_id: {l['currency_id']}")
        print(f"    ---")

print("\n" + "=" * 80)
print("2. VERIFICAR CATEGORÍA DE TRONADOR")
print("=" * 80)

# Buscar partner TRONADOR
partners = search_read(
    'res.partner',
    [['name', 'like', 'TRONADOR']],
    ['id', 'name', 'x_studio_categora_de_contacto', 'parent_id', 'type']
)

for p in partners:
    print(f"\n  Partner ID: {p['id']}")
    print(f"  Name: {p['name']}")
    print(f"  Type: {p.get('type')}")
    print(f"  Parent: {p.get('parent_id')}")
    print(f"  Categoría: {p['x_studio_categora_de_contacto']}")


print("\n" + "=" * 80)
print("3. TODAS LAS FACTURAS PARCIALES CxC (cliente)")
print("=" * 80)

partial_moves = search_read(
    'account.move',
    [
        ['move_type', 'in', ['out_invoice', 'out_refund']],
        ['state', '=', 'posted'],
        ['payment_state', '=', 'partial'],
        ['date', '>=', '2026-01-01'],
        ['date', '<=', '2026-05-31'],
    ],
    ['id', 'name', 'partner_id', 'amount_total', 'amount_residual', 'payment_state',
     'x_studio_fecha_de_pago', 'date']
)

print(f"\nTotal facturas parciales: {len(partial_moves)}")
for m in partial_moves:
    print(f"  {m['name']}: partner={m['partner_id']}, total={m['amount_total']}, residual={m['amount_residual']}, fecha_pago={m['x_studio_fecha_de_pago']}, date={m['date']}")


print("\n" + "=" * 80)
print("4. VERIFICAR QUERY CON FECHA_PAGO")
print("=" * 80)

# Replicar exactamente el query del código
domain_moves = [
    ['move_type', 'in', ['out_invoice', 'out_refund']],
    ['state', '=', 'posted'],
    '|',
    '&', '&',
        ['x_studio_fecha_de_pago', '!=', False],
        ['x_studio_fecha_de_pago', '>=', '2026-01-01'],
        ['x_studio_fecha_de_pago', '<=', '2026-05-31'],
    '&', '&',
        ['x_studio_fecha_de_pago', '=', False],
        ['date', '>=', '2026-01-01'],
        ['date', '<=', '2026-05-31'],
]

all_moves = search_read(
    'account.move',
    domain_moves,
    ['id', 'name', 'payment_state', 'x_studio_fecha_de_pago', 'date']
)

# Check if FCXE 000284 is in the result
fcxe_284 = [m for m in all_moves if '000284' in str(m.get('name', ''))]
print(f"\nTotal moves en query: {len(all_moves)}")
print(f"FCXE 000284 encontrado en query: {len(fcxe_284) > 0}")
if fcxe_284:
    for m in fcxe_284:
        print(f"  {m['name']}: payment_state={m['payment_state']}, fecha_pago={m['x_studio_fecha_de_pago']}, date={m['date']}")
else:
    print("  !! FCXE 000284 NO está en el resultado del query !!")
    # Check why
    print("\n  Buscando FCXE 000284 sin filtros de fecha:")
    fcxe = search_read(
        'account.move',
        [['name', 'like', 'FCXE 000284']],
        ['id', 'name', 'payment_state', 'x_studio_fecha_de_pago', 'date', 'state', 'move_type']
    )
    for m in fcxe:
        print(f"    {m['name']}: state={m['state']}, payment_state={m['payment_state']}, fecha_pago={m['x_studio_fecha_de_pago']}, date={m['date']}, move_type={m['move_type']}")

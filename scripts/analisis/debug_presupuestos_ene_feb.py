"""
Debug: Verificar presupuestos en ENE-FEB 2026
"""
import xmlrpc.client

# Odoo credentials
url = "http://167.114.114.51:8069"
db = "riofuturo"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Autenticar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

if not uid:
    print("❌ Error de autenticación")
    exit(1)

print(f"✅ Autenticado como UID: {uid}")

# Conectar a modelos
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Consultar presupuestos en ENE-FEB 2026
print("\n" + "="*80)
print("PRESUPUESTOS EN ENERO-FEBRERO 2026")
print("="*80)

presupuestos = models.execute_kw(
    db, uid, password,
    'sale.order', 'search_read',
    [[
        ('state', 'in', ['draft', 'sent']),
        ('commitment_date', '>=', '2026-01-01'),
        ('commitment_date', '<=', '2026-02-28')
    ]],
    {'fields': ['name', 'partner_id', 'amount_total', 'currency_id', 'commitment_date', 'state']}
)

print(f"\n📊 Total: {len(presupuestos)} presupuestos\n")

if len(presupuestos) == 0:
    print("⚠️ NO HAY PRESUPUESTOS en ENE-FEB 2026")
    print("\nVerificando presupuestos en TODO 2026:")
    
    todos_2026 = models.execute_kw(
        db, uid, password,
        'sale.order', 'search_read',
        [[
            ('state', 'in', ['draft', 'sent']),
            ('commitment_date', '>=', '2026-01-01'),
            ('commitment_date', '<=', '2026-12-31')
        ]],
        {'fields': ['name', 'commitment_date', 'amount_total', 'currency_id']}
    )
    
    print(f"Total 2026: {len(todos_2026)} presupuestos")
    
    # Agrupar por mes
    from collections import defaultdict
    por_mes = defaultdict(lambda: {'count': 0, 'total': 0})
    
    for p in todos_2026:
        fecha = p.get('commitment_date', '')
        if fecha:
            mes = fecha[:7]  # YYYY-MM
            por_mes[mes]['count'] += 1
            por_mes[mes]['total'] += p.get('amount_total', 0)
    
    print("\nDistribución por mes:")
    for mes in sorted(por_mes.keys()):
        data = por_mes[mes]
        print(f"  {mes}: {data['count']:3d} presupuestos | ${data['total']:>15,.0f}")
else:
    total_usd = 0
    total_clp = 0
    
    for p in presupuestos:
        nombre = p.get('name', 'N/A')
        partner = p.get('partner_id', [0, 'N/A'])[1] if p.get('partner_id') else 'N/A'
        amount = p.get('amount_total', 0)
        currency = p.get('currency_id', [0, 'N/A'])[1] if p.get('currency_id') else 'N/A'
        fecha = p.get('commitment_date', 'N/A')
        state = p.get('state', 'N/A')
        
        if 'USD' in currency:
            total_usd += amount
        else:
            total_clp += amount
        
        print(f"{nombre:20s} | {partner:30s} | {currency:5s} ${amount:>12,.0f} | {fecha} | {state}")
    
    print("\n" + "-"*80)
    print(f"Total USD: ${total_usd:,.2f}")
    print(f"Total CLP: ${total_clp:,.0f}")
    
    # Convertir USD a CLP estimado
    total_clp_estimado = total_clp + (total_usd * 950)
    print(f"\nTotal estimado en CLP (USD @ 950): ${total_clp_estimado:,.0f}")

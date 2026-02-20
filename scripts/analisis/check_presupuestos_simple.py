"""
Check simple: ¿Hay presupuestos en ENE-FEB 2026?
"""
import xmlrpc.client

url = "http://167.114.114.51:8069"
db = "riofuturo"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Query ENE-FEB 2026
ene_feb = models.execute_kw(
    db, uid, password,
    'sale.order', 'search_count',
    [[
        ('state', 'in', ['draft', 'sent']),
        ('commitment_date', '>=', '2026-01-01'),
        ('commitment_date', '<=', '2026-02-28')
    ]]
)

print(f"Presupuestos EN ENE-FEB 2026: {ene_feb}")

# Query TODO 2026
todo_2026 = models.execute_kw(
    db, uid, password,
    'sale.order', 'search_count',
    [[
        ('state', 'in', ['draft', 'sent']),
        ('commitment_date', '>=', '2026-01-01'),
        ('commitment_date', '<=', '2026-12-31')
    ]]
)

print(f"Presupuestos en TODO 2026: {todo_2026}")

if ene_feb == 0:
    print("\n⚠️ NO HAY PRESUPUESTOS en ENE-FEB 2026")
    print("Por eso no aparece nada cuando activas el checkbox.")
    print("\n💡 SOLUCIÓN: Amplía el rango de fechas a todo 2026 para ver los presupuestos.")

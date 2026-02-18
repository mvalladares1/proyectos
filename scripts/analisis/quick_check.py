import xmlrpc.client
url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
print(f"UID: {uid}")

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
count = models.execute_kw(db, uid, password, 'sale.order', 'search_count', [[('state', 'in', ['draft', 'sent']), ('commitment_date', '>=', '2026-01-01'), ('commitment_date', '<=', '2026-09-30')]])
print(f"Presupuestos ENE-SEP 2026: {count}")

if count == 0:
    print("\nVerificando sin filtro de fecha...")
    count_all = models.execute_kw(db, uid, password, 'sale.order', 'search_count', [[('state', 'in', ['draft', 'sent'])]])
    print(f"Total draft/sent sin filtro fecha: {count_all}")
    
    if count_all > 0:
        sample = models.execute_kw(db, uid, password, 'sale.order', 'search_read', [[('state', 'in', ['draft', 'sent'])]], {'fields': ['name', 'commitment_date'], 'limit': 5})
        print("\nPrimeros 5:")
        for s in sample:
            print(f"  {s['name']}: commitment_date={s.get('commitment_date', 'NULL')}")

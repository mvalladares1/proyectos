import xmlrpc.client
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=None)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=None)

def sr(model, domain, fields, limit=0):
    return models.execute_kw(db, uid, password, model, 'search_read', [domain], {'fields': fields, 'limit': limit})

CONTINUO_ID = 15987
MP_TAG = 18
MPC_TAG = 60

mp_prods = sr('product.product', [('product_tag_ids', 'in', [MP_TAG])], ['id', 'name'])
mp_ids = set(p['id'] for p in mp_prods)

mpc_prods = sr('product.product', [('product_tag_ids', 'in', [MPC_TAG])], ['id', 'name'])
mpc_ids = set(p['id'] for p in mpc_prods)

both_ids = mp_ids | mpc_ids

prods = sr('mrp.production', [('product_id', '=', CONTINUO_ID), ('state', '=', 'done')], 
           ['id', 'name', 'move_raw_ids', 'date_finished'])

total_mp = 0
total_mpc = 0
total_both = 0

print(f"{'Produccion':<25} {'KG MP':>12} {'KG MPC':>12} {'KG Total':>12}")
print("-" * 65)

for prod in sorted(prods, key=lambda x: x.get('date_finished', '')):
    moves = sr('stock.move', [('id', 'in', prod['move_raw_ids'])], ['id', 'product_id', 'quantity_done'])
    kg_mp = 0
    kg_mpc = 0
    for m in moves:
        pid = m['product_id'][0] if m['product_id'] else 0
        qty = m['quantity_done'] or 0
        if qty <= 0:
            continue
        if pid in mp_ids:
            kg_mp += qty
        if pid in mpc_ids:
            kg_mpc += qty
    if kg_mpc > 0 or kg_mp > 0:
        print(f"{prod['name']:<25} {kg_mp:>12,.2f} {kg_mpc:>12,.2f} {kg_mp+kg_mpc:>12,.2f}")
    total_mp += kg_mp
    total_mpc += kg_mpc

print(f"\n{'='*65}")
print(f"{'TOTAL':<25} {total_mp:>12,.2f} {total_mpc:>12,.2f} {total_mp+total_mpc:>12,.2f}")
print(f"\nSolo MP:      {total_mp:>12,.2f} kg")
print(f"Solo MPC:     {total_mpc:>12,.2f} kg")
print(f"MP + MPC:     {total_mp+total_mpc:>12,.2f} kg")

# Tambien para estaticos
print(f"\n\n=== ESTATICOS + VLK: MP vs MPC ===")
for tid, tname in [(15984, "Estatico 1"), (15985, "Estatico 2"), (15986, "Estatico 3"), (16446, "VLK")]:
    tprods = sr('mrp.production', [('product_id', '=', tid), ('state', '=', 'done')], ['id', 'move_raw_ids'])
    t_mp = 0
    t_mpc = 0
    for p in tprods:
        moves = sr('stock.move', [('id', 'in', p['move_raw_ids'])], ['id', 'product_id', 'quantity_done'])
        for m in moves:
            pid = m['product_id'][0] if m['product_id'] else 0
            qty = m['quantity_done'] or 0
            if qty <= 0:
                continue
            if pid in mp_ids:
                t_mp += qty
            if pid in mpc_ids:
                t_mpc += qty
    print(f"  {tname:<20} MP={t_mp:>12,.2f}   MPC={t_mpc:>12,.2f}   Total={t_mp+t_mpc:>12,.2f}")

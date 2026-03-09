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
MP_TAG_ID = 18

# Obtener productos MP
mp_prods = sr('product.product', [('product_tag_ids', 'in', [MP_TAG_ID])], ['id', 'name'])
mp_ids = set(p['id'] for p in mp_prods)

# Todas las producciones del Continuo
prods = sr('mrp.production', [('product_id', '=', CONTINUO_ID), ('state', '=', 'done')], 
           ['id', 'name', 'move_raw_ids', 'date_finished', 'qty_produced'])

print(f"Total producciones Continuo: {len(prods)}")
print(f"\n{'Producción':<30} {'Fecha':<12} {'KG MP':<15} {'# Moves'}")
print("-" * 75)

total_kg = 0
big_ones = []
for prod in sorted(prods, key=lambda x: x.get('date_finished', '')):
    raw_ids = prod['move_raw_ids']
    moves = sr('stock.move', [('id', 'in', raw_ids)], ['id', 'product_id', 'quantity_done'])
    kg_mp = 0
    for m in moves:
        pid = m['product_id'][0] if m['product_id'] else 0
        if pid in mp_ids:
            kg_mp += m['quantity_done'] or 0
    date = str(prod.get('date_finished', ''))[:10]
    print(f"{prod['name']:<30} {date:<12} {kg_mp:>12,.2f}   {len(raw_ids)} moves")
    total_kg += kg_mp
    if kg_mp > 50000:
        big_ones.append((prod['name'], date, kg_mp))

print(f"\n{'TOTAL':>30} {'':>12} {total_kg:>12,.2f}")

if big_ones:
    print(f"\n=== PRODUCCIONES > 50,000 KG ===")
    for name, date, kg in big_ones:
        print(f"  {name} ({date}): {kg:,.2f} kg")

# Verificar UoM - quizás hay confusión de unidades
print(f"\n=== VERIFICAR UoM EN MOVES ===")
# Tomar una producción grande como ejemplo
if big_ones:
    big_name = big_ones[0][0]
    big_prod = [p for p in prods if p['name'] == big_name][0]
    moves = sr('stock.move', [('id', 'in', big_prod['move_raw_ids'])], 
               ['id', 'product_id', 'quantity_done', 'product_uom_qty', 'product_uom'])
    print(f"\nDetalle de {big_name}:")
    for m in moves:
        pname = m['product_id'][1] if m['product_id'] else '?'
        uom = m['product_uom'][1] if m['product_uom'] else '?'
        print(f"  {pname}: qty_done={m['quantity_done']:.2f}, uom_qty={m['product_uom_qty']:.2f}, UoM={uom}")

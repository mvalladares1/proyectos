import xmlrpc.client
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', context=None)
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', context=None)

def search_read(model, domain, fields, limit=0):
    return models.execute_kw(db, uid, password, model, 'search_read', [domain], {'fields': fields, 'limit': limit})

# 1) Buscar todos los product tags
print("=== TODOS LOS PRODUCT TAGS ===")
tags = search_read('product.tag', [], ['id', 'name'])
for t in tags:
    print(f"  Tag ID {t['id']}: {t['name']}")

# 2) Verificar WH/Transf/00667
print("\n=== VERIFICAR WH/Transf/00667 ===")
# Buscar la producción
prods = search_read('mrp.production', [('name', 'ilike', 'WH/Transf/00667')], ['id', 'name', 'product_id', 'move_raw_ids', 'date_finished'])
if not prods:
    # Quizás es un picking
    picks = search_read('stock.picking', [('name', '=', 'WH/Transf/00667')], ['id', 'name', 'move_ids_without_package', 'move_line_ids_without_package', 'date_done'])
    if picks:
        print(f"Es un picking: {picks[0]}")
    # Buscar en stock.move
    print("\nBuscando en stock.move por reference...")
    moves = search_read('stock.move', [('reference', '=', 'WH/Transf/00667')], ['id', 'product_id', 'product_uom_qty', 'quantity_done', 'reference'])
    print(f"Moves encontrados: {len(moves)}")
    for m in moves:
        prod_id = m['product_id'][0]
        prod_name = m['product_id'][1]
        # Obtener tags del producto
        prod_data = search_read('product.product', [('id', '=', prod_id)], ['id', 'name', 'product_tag_ids', 'categ_id'])
        tag_ids = prod_data[0]['product_tag_ids'] if prod_data else []
        tag_names = []
        if tag_ids:
            tag_data = search_read('product.tag', [('id', 'in', tag_ids)], ['id', 'name'])
            tag_names = [t['name'] for t in tag_data]
        categ = prod_data[0]['categ_id'] if prod_data else 'N/A'
        qty = m.get('quantity_done', 0) or m.get('product_uom_qty', 0)
        print(f"  {prod_name} | qty={qty:.2f} | tags={tag_names} | categ={categ}")
else:
    print(f"Es una producción: {prods[0]['name']}")
    for mid in prods[0]['move_raw_ids']:
        moves = search_read('stock.move', [('id', '=', mid)], ['id', 'product_id', 'quantity_done'])
        if moves:
            m = moves[0]
            prod_id = m['product_id'][0]
            prod_name = m['product_id'][1]
            prod_data = search_read('product.product', [('id', '=', prod_id)], ['id', 'name', 'product_tag_ids', 'categ_id'])
            tag_ids = prod_data[0]['product_tag_ids'] if prod_data else []
            tag_names = []
            if tag_ids:
                tag_data = search_read('product.tag', [('id', 'in', tag_ids)], ['id', 'name'])
                tag_names = [t['name'] for t in tag_data]
            categ = prod_data[0]['categ_id'] if prod_data else 'N/A'
            print(f"  {prod_name} | qty={m['quantity_done']:.2f} | tags={tag_names} | categ={categ}")

# 3) Verificar si product_tag_ids está en product.product o product.template
print("\n=== VERIFICAR CAMPO product_tag_ids ===")
# Probar en product.template
try:
    test = search_read('product.template', [('product_tag_ids', '!=', False)], ['id', 'name', 'product_tag_ids'], limit=3)
    print(f"product.template con tags: {len(test)} (muestra)")
    for t in test:
        print(f"  {t['name']}: tags={t['product_tag_ids']}")
except Exception as e:
    print(f"Error en product.template: {e}")

try:
    test2 = search_read('product.product', [('product_tag_ids', '!=', False)], ['id', 'name', 'product_tag_ids'], limit=3)
    print(f"product.product con tags: {len(test2)} (muestra)")
    for t in test2:
        print(f"  {t['name']}: tags={t['product_tag_ids']}")
except Exception as e:
    print(f"Error en product.product: {e}")

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

# Tunnel product IDs
ESTATICO_1 = 15984
ESTATICO_2 = 15985
ESTATICO_3 = 15986
CONTINUO = 15987
VLK = 16446

# Find a few productions for each tunnel type and check their raw materials
for tunnel_id, tunnel_name in [(ESTATICO_1, "Estático 1"), (ESTATICO_2, "Estático 2"), (ESTATICO_3, "Estático 3"), (VLK, "VLK"), (CONTINUO, "Continuo")]:
    print(f"\n=== {tunnel_name} (ID: {tunnel_id}) ===")
    prods = sr('mrp.production', [('product_id', '=', tunnel_id), ('state', '=', 'done')], ['id', 'name', 'move_raw_ids'], limit=3)
    print(f"  Muestreo: {len(prods)} producciones")
    for prod in prods[:2]:  # solo 2
        print(f"\n  Producción: {prod['name']}")
        for mid in prod['move_raw_ids']:
            moves = sr('stock.move', [('id', '=', mid)], ['id', 'product_id', 'quantity_done'])
            if moves:
                m = moves[0]
                pid = m['product_id'][0]
                pname = m['product_id'][1]
                pdata = sr('product.product', [('id', '=', pid)], ['id', 'name', 'product_tag_ids', 'categ_id'])
                tags = []
                if pdata and pdata[0]['product_tag_ids']:
                    tag_data = sr('product.tag', [('id', 'in', pdata[0]['product_tag_ids'])], ['id', 'name'])
                    tags = [t['name'] for t in tag_data]
                categ = pdata[0]['categ_id'] if pdata else 'N/A'
                print(f"    {pname} | qty={m['quantity_done']:.2f} | tags={tags} | categ={categ}")

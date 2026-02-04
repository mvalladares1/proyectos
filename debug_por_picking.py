from shared.odoo_client import OdooClient
odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

# Ver todos los picking_types que tienen procesos
print('=== PROCESOS AGRUPADOS POR PICKING TYPE ===')
procesos = odoo.search_read('mrp.production', [['state', '!=', 'cancel']], ['name', 'picking_type_id', 'state'], limit=500)

# Agrupar por picking_type
por_pt = {}
for p in procesos:
    pt = p.get('picking_type_id')
    pt_key = str(pt) if pt else 'None'
    if pt_key not in por_pt:
        por_pt[pt_key] = {'count': 0, 'examples': [], 'done': 0}
    por_pt[pt_key]['count'] += 1
    if p['state'] == 'done':
        por_pt[pt_key]['done'] += 1
    if len(por_pt[pt_key]['examples']) < 5:
        por_pt[pt_key]['examples'].append(p['name'])

for pt, data in sorted(por_pt.items(), key=lambda x: -x[1]['count']):
    print(f"{pt}: {data['count']} total ({data['done']} cerrados)")
    print(f"   Ejemplos: {data['examples']}")

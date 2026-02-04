from shared.odoo_client import OdooClient
odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

# Ver patrones de nombres de OF
procesos = odoo.search_read('mrp.production', [['state', '!=', 'cancel']], ['name', 'picking_type_id', 'state'], limit=500)

# Agrupar por prefijos
prefijos = {}
for p in procesos:
    name = p['name']
    # Extraer prefijo (antes del ultimo /)
    parts = name.rsplit('/', 1)
    prefix = parts[0] if len(parts) > 1 else name[:10]
    if prefix not in prefijos:
        prefijos[prefix] = {'count': 0, 'examples': [], 'picking_types': set()}
    prefijos[prefix]['count'] += 1
    prefijos[prefix]['examples'].append(name)
    pt = p.get('picking_type_id')
    if pt:
        prefijos[prefix]['picking_types'].add((pt[0], pt[1]))

print('Patrones de nombres de OF:')
for prefix, data in sorted(prefijos.items(), key=lambda x: -x[1]['count']):
    if data['count'] > 0:
        print(f"\n{prefix}/*: {data['count']} procesos")
        print(f"  Picking types: {data['picking_types']}")
        print(f"  Ejemplos: {data['examples'][:3]}")

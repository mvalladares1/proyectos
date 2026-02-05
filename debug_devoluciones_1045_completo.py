"""
Investigar TODAS las devoluciones asociadas a RF/RFP/IN/01045
"""
import xmlrpc.client

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 100)
print("BÚSQUEDA COMPLETA: TODAS LAS DEVOLUCIONES DE RF/RFP/IN/01045")
print("=" * 100)

# Buscar TODAS las devoluciones que mencionen RF/RFP/IN/01045 en origin
print("\n🔍 Buscando devoluciones con origin que contenga 'RF/RFP/IN/01045'...")

devoluciones = models.execute_kw(db, uid, password,
    'stock.picking', 'search_read',
    [[['picking_type_id', 'in', [2, 3, 5]],
      ['origin', 'ilike', 'RF/RFP/IN/01045']]],
    {'fields': ['id', 'name', 'state', 'scheduled_date', 'origin', 'picking_type_id']}
)

print(f"\n✅ Encontradas {len(devoluciones)} devoluciones")

total_devuelto_global = 0

for idx, dev in enumerate(devoluciones, 1):
    print(f"\n" + "=" * 100)
    print(f"DEVOLUCIÓN #{idx}: {dev['name']}")
    print("=" * 100)
    print(f"   ID: {dev['id']}")
    print(f"   Estado: {dev['state']}")
    print(f"   Fecha: {dev.get('scheduled_date', 'N/A')}")
    print(f"   Origin: {dev.get('origin', 'N/A')}")
    print(f"   Picking Type: {dev.get('picking_type_id', 'N/A')}")
    
    # Obtener movimientos de esta devolución
    moves_dev = models.execute_kw(db, uid, password,
        'stock.move', 'search_read',
        [[['picking_id', '=', dev['id']]]],
        {'fields': ['id', 'product_id', 'quantity_done', 'product_uom', 'state']}
    )
    
    total_devuelto_esta = 0
    print(f"\n   📦 Movimientos ({len(moves_dev)}):")
    for m in moves_dev:
        qty = m.get('quantity_done', 0)
        uom = m.get('product_uom', ['N/A', 'kg'])
        uom_name = uom[1] if isinstance(uom, list) else 'kg'
        estado = m.get('state', 'N/A')
        
        # Solo sumar si es en kg y está done
        if uom_name.lower() == 'kg' and estado == 'done':
            total_devuelto_esta += qty
            total_devuelto_global += qty
        
        print(f"      - {m.get('product_id', 'N/A')}")
        print(f"        Cantidad: {qty} {uom_name}")
        print(f"        Estado: {estado}")
    
    print(f"\n   📊 TOTAL DEVUELTO (esta devolución): {total_devuelto_esta:.2f} kg")

print("\n" + "=" * 100)
print("RESUMEN FINAL")
print("=" * 100)
print(f"Total devoluciones encontradas: {len(devoluciones)}")
print(f"TOTAL KG DEVUELTOS (todas las devoluciones): {total_devuelto_global:.2f} kg")

print("\n📊 CÁLCULO:")
print(f"   Kg Recibidos (IN/01045):     2745.55 kg")
print(f"   Kg Devueltos (TODAS):        {total_devuelto_global:.2f} kg")
print(f"   KG NETOS:                    {2745.55 - total_devuelto_global:.2f} kg")

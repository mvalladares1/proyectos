import xmlrpc.client

# Conexión a Odoo
url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 80)
print("LIMPIAR TIER.REVIEW DE OC12393")
print("=" * 80)

# IDs de usuarios correctos
FRANCISCO_ID = 258
MAXIMO_ID = 241
FELIPE_ID = 17

# Buscar OC12393
print("\n1. BUSCANDO OC12393:")
print("-" * 80)
oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC12393']]],
    {'fields': ['name', 'state', 'id']})

if not oc:
    print("  ❌ OC12393 no encontrada")
    exit(1)

oc = oc[0]
print(f"  ✅ {oc['name']} (ID: {oc['id']}) - Estado: {oc['state']}")

# Buscar tier.review
print("\n2. BUSCANDO TIER.REVIEW:")
print("-" * 80)
try:
    reviews = models.execute_kw(db, uid, password, 'tier.review', 'search_read',
        [[['res_id', '=', oc['id']], ['model', '=', 'purchase.order']]],
        {'fields': ['id', 'name', 'status', 'reviewer_id', 'reviewed_by']})
    
    if reviews:
        print(f"  ✅ Encontrados {len(reviews)} tier.review:")
        for review in reviews:
            reviewer = review.get('reviewer_id', ['Sin revisor'])[1] if review.get('reviewer_id') else 'Sin revisor'
            reviewed_by = review.get('reviewed_by', ['No revisado'])[1] if review.get('reviewed_by') else 'No revisado'
            print(f"    ID: {review['id']} | Revisor: {reviewer} | Estado: {review.get('status')} | Revisado por: {reviewed_by}")
        
        # Determinar usuarios correctos según estado
        if oc['state'] in ['draft', 'sent', 'to approve']:
            usuarios_correctos = [FRANCISCO_ID, MAXIMO_ID]
            print(f"\n  Estado '{oc['state']}' → Correctos: Francisco ({FRANCISCO_ID}) + Maximo ({MAXIMO_ID})")
        elif oc['state'] == 'purchase':
            usuarios_correctos = [FELIPE_ID]
            print(f"\n  Estado 'purchase' → Correcto: Felipe ({FELIPE_ID})")
        else:
            usuarios_correctos = []
        
        # Eliminar tier.review incorrectos
        print("\n3. ELIMINANDO TIER.REVIEW INCORRECTOS:")
        print("-" * 80)
        eliminados = 0
        
        for review in reviews:
            reviewer_id = review['reviewer_id'][0] if review.get('reviewer_id') else None
            reviewer_name = review['reviewer_id'][1] if review.get('reviewer_id') else 'Sin revisor'
            
            if reviewer_id not in usuarios_correctos:
                try:
                    models.execute_kw(db, uid, password, 'tier.review', 'unlink', [[review['id']]])
                    print(f"  ❌ ELIMINADO: {reviewer_name} (ID: {reviewer_id})")
                    eliminados += 1
                except Exception as e:
                    print(f"  ⚠️  Error eliminando review {review['id']}: {e}")
            else:
                print(f"  ✅ MANTENER: {reviewer_name} (ID: {reviewer_id})")
        
        print(f"\n  Total eliminados: {eliminados}")
    else:
        print("  ℹ️  No hay tier.review para esta OC")
        
except Exception as e:
    print(f"  ❌ Error buscando tier.review: {e}")

print("\n" + "=" * 80)
print("✅ Recarga OC12393 y verifica el botón CONFIRMAR PEDIDO")
print("=" * 80)

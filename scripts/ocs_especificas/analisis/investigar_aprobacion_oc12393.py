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
print("INVESTIGAR TODOS LOS CAMPOS DE APROBACIÓN - OC12393")
print("=" * 80)

# Buscar OC12393 con campos específicos tier
print("\n1. CAMPOS TIER DE OC12393:")
print("-" * 80)
oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC12393']]],
    {'fields': ['name', 'state', 'review_ids', 'reviewer_ids', 
                'validated', 'rejected', 'need_validation', 'can_review'], 
     'limit': 1})

if oc:
    oc = oc[0]
    # Buscar campos relacionados con aprobación
    campos_aprobacion = {}
    for key, value in oc.items():
        key_lower = str(key).lower()
        if any(word in key_lower for word in ['approv', 'tier', 'review', 'valid', 'confirm']):
            campos_aprobacion[key] = value
    
    print("  Campos relacionados con aprobación:")
    for key, value in sorted(campos_aprobacion.items()):
        print(f"    {key}: {value}")

# Buscar tier.review si existe
print("\n2. BUSCANDO TIER.REVIEW:")
print("-" * 80)
try:
    tier_reviews = models.execute_kw(db, uid, password, 'tier.review', 'search_read',
        [[['res_id', '=', oc['id']], ['model', '=', 'purchase.order']]],
        {'fields': []})
    
    if tier_reviews:
        print(f"  ✅ Encontrados {len(tier_reviews)} tier.review:")
        for review in tier_reviews:
            print(f"\n  Review ID: {review['id']}")
            for key, value in sorted(review.items()):
                print(f"    {key}: {value}")
    else:
        print("  ℹ️  No hay tier.review para esta OC")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Buscar tier.validation
print("\n3. BUSCANDO TIER.VALIDATION:")
print("-" * 80)
try:
    tier_validations = models.execute_kw(db, uid, password, 'tier.validation', 'search_read',
        [[['res_id', '=', oc['id']], ['model', '=', 'purchase.order']]],
        {'fields': []})
    
    if tier_validations:
        print(f"  ✅ Encontrados {len(tier_validations)} tier.validation:")
        for validation in tier_validations:
            print(f"\n  Validation ID: {validation['id']}")
            for key, value in sorted(validation.items()):
                print(f"    {key}: {value}")
    else:
        print("  ℹ️  No hay tier.validation para esta OC")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "=" * 80)

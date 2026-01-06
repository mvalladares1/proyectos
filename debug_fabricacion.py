"""
Debug de fabricación específica para entender el flujo de datos
Analiza una MO (Orden de Fabricación) específica
"""
import json
import xmlrpc.client
import getpass

ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"

def debug_fabricacion():
    print("=" * 80)
    print("🔍 DEBUG: Análisis de Fabricación Odoo")
    print("=" * 80)
    
    email = input("Email Odoo: ")
    api_key = getpass.getpass("API Key: ")
    
    print("\n🔄 Conectando a Odoo...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, email, api_key, {})
    
    if not uid:
        print("❌ Error de autenticación")
        return
    
    print(f"✅ Conectado como UID: {uid}")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    
    def search_read(model, domain, fields, limit=100):
        return models.execute_kw(ODOO_DB, uid, api_key, model, 'search_read', [domain], {'fields': fields, 'limit': limit})
    
    # Fabricación a analizar
    mo_name = "RF/MO/CongTE1/00104"
    
    print("\n" + "="*80)
    print(f"🔍 ANALIZANDO FABRICACIÓN: {mo_name}")
    print("="*80)
    
    # 1. Buscar la MO
    print("\n1️⃣ BÚSQUEDA DE LA ORDEN DE FABRICACIÓN:")
    print("-"*80)
    mo_search = search_read("mrp.production", [("name", "=", mo_name)], [], limit=1)
    
    if not mo_search:
        print(f"❌ No se encontró la fabricación {mo_name}")
        return
    
    mo = mo_search[0]
    print(f"✅ Fabricación encontrada - ID: {mo.get('id')}")
    print(f"📋 Estado: {mo.get('state')}")
    print(f"📦 Producto: {mo.get('product_id')}")
    print(f"🏭 Workcenter: {mo.get('workcenter_id')}")
    
    print("\n2️⃣ CAMPOS COMPLETOS DE LA MO:")
    print("-"*80)
    print(json.dumps(mo, indent=2, default=str))
    
    # 2. Analizar el producto
    if mo.get('product_id'):
        product_id = mo['product_id'][0] if isinstance(mo['product_id'], list) else mo['product_id']
        print(f"\n3️⃣ PRODUCTO DE LA MO (ID: {product_id}):")
        print("-"*80)
        product = search_read(
            "product.product",
            [("id", "=", product_id)],
            ["name", "default_code", "categ_id", "type"],
            limit=1
        )
        if product:
            print(json.dumps(product[0], indent=2, default=str))
            
            product_name = product[0].get('name', '')
            print(f"\n🔍 ANÁLISIS DEL NOMBRE DEL PRODUCTO:")
            print(f"   Nombre: '{product_name}'")
            print(f"   Contiene 'PROCESO': {'PROCESO' in product_name.upper()}")
            print(f"   Contiene 'TUNEL': {'TUNEL' in product_name.upper() or 'TÚNEL' in product_name.upper()}")
    
    # 3. Analizar movimientos de stock (consumos y producción)
    print(f"\n4️⃣ MOVIMIENTOS DE STOCK RELACIONADOS:")
    print("-"*80)
    moves = search_read(
        "stock.move",
        [("raw_material_production_id", "=", mo['id'])],
        ["name", "product_id", "product_uom_qty", "quantity_done", "state", "location_id", "location_dest_id"],
        limit=50
    )
    print(f"📦 Movimientos de materia prima (consumos): {len(moves)}")
    for move in moves[:5]:  # Primeros 5
        print(f"   - {move.get('product_id', ['?'])[1] if isinstance(move.get('product_id'), list) else move.get('product_id')}")
        print(f"     Planificado: {move.get('product_uom_qty')} | Realizado: {move.get('quantity_done')} | Estado: {move.get('state')}")
    
    # Movimientos de producción (salidas)
    moves_out = search_read(
        "stock.move",
        [("production_id", "=", mo['id'])],
        ["name", "product_id", "product_uom_qty", "quantity_done", "state"],
        limit=50
    )
    print(f"\n📤 Movimientos de producción (salidas): {len(moves_out)}")
    for move in moves_out:
        print(f"   - {move.get('product_id', ['?'])[1] if isinstance(move.get('product_id'), list) else move.get('product_id')}")
        print(f"     Planificado: {move.get('product_uom_qty')} | Realizado: {move.get('quantity_done')} | Estado: {move.get('state')}")
    
    # 4. Calcular totales
    print(f"\n5️⃣ CÁLCULOS:")
    print("-"*80)
    total_mp = sum(move.get('quantity_done', 0) or 0 for move in moves)
    total_pt = sum(move.get('quantity_done', 0) or 0 for move in moves_out)
    rendimiento = (total_pt / total_mp * 100) if total_mp > 0 else 0
    merma = total_pt - total_mp
    
    print(f"📥 Total MP consumida: {total_mp:,.2f} kg")
    print(f"📤 Total PT producido: {total_pt:,.2f} kg")
    print(f"📊 Rendimiento: {rendimiento:.2f}%")
    print(f"⚖️ Merma/Diferencia: {merma:+,.2f} kg")
    
    # 5. Verificar si es un subproducto intermedio
    print(f"\n6️⃣ CLASIFICACIÓN:")
    print("-"*80)
    if product:
        product_name = product[0].get('name', '')
        es_subproducto = 'PROCESO' in product_name.upper() or 'TUNEL' in product_name.upper() or 'TÚNEL' in product_name.upper()
        print(f"❓ ¿Es subproducto intermedio?: {es_subproducto}")
        if es_subproducto:
            print(f"   ⚠️ Este producto NO debería contabilizarse en Kg PT totales")
            print(f"   ✅ Pero SÍ debe aparecer en gráficos de actividad del túnel/sala")
        else:
            print(f"   ✅ Este es un producto final, contabilizar en Kg PT totales")
    
    print("\n" + "="*80)
    print("✅ ANÁLISIS COMPLETADO")
    print("="*80)

if __name__ == "__main__":
    debug_fabricacion()

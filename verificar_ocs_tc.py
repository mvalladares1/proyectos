"""
Verificar TCs directamente desde las Órdenes de Compra en Odoo
"""
import sys
sys.path.insert(0, r"c:\new\RIO FUTURO\DASHBOARD\proyectos")

from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

client = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 120)
print("🔍 ANÁLISIS DE ÓRDENES DE COMPRA Y SUS TIPOS DE CAMBIO")
print("=" * 120)

# OCs de la factura TRES ROBLES
ocs_nombres = ["P06771", "P06648", "P06642", "P06481", "P06476", "P05826"]

print(f"\n📋 Buscando OCs de AGRÍCOLA TRES ROBLES...\n")

for oc_nombre in ocs_nombres:
    # Buscar la OC
    ocs = client.search_read(
        "purchase.order",
        [("name", "=", oc_nombre)],
        ["id", "name", "partner_id", "date_order", "currency_id", "amount_total", "amount_untaxed"],
        limit=1
    )
    
    if not ocs:
        print(f"❌ OC {oc_nombre} no encontrada")
        continue
    
    oc = ocs[0]
    oc_id = oc['id']
    
    # Obtener líneas de la OC
    oc_lines = client.search_read(
        "purchase.order.line",
        [("order_id", "=", oc_id)],
        ["id", "name", "product_id", "product_qty", "price_unit", "price_subtotal"],
        limit=10
    )
    
    # Buscar el move asociado (factura de proveedor generada desde esta OC)
    moves = client.search_read(
        "account.move",
        [
            ("invoice_origin", "like", oc_nombre),
            ("move_type", "=", "in_invoice")
        ],
        ["id", "name", "invoice_origin", "amount_total", "amount_total_signed", "currency_id"],
        limit=1
    )
    
    if moves:
        move = moves[0]
        
        # Obtener líneas del move para ver el debit (CLP)
        move_lines = client.search_read(
            "account.move.line",
            [
                ("move_id", "=", move['id']),
                ("display_type", "=", False),
                ("debit", ">", 0)
            ],
            ["id", "name", "quantity", "price_unit", "debit", "price_subtotal"],
            limit=10
        )
        
        print(f"📦 OC: {oc_nombre}")
        print(f"   📅 Fecha OC: {oc.get('date_order', 'N/A')}")
        print(f"   💵 Total OC USD: ${oc.get('amount_untaxed', 0):,.2f}")
        print(f"   📄 Factura: {move.get('name', 'N/A')}")
        
        if move_lines:
            print(f"   📊 Líneas de factura:")
            for ml in move_lines:
                usd = ml.get('price_subtotal', 0) or 0
                clp = ml.get('debit', 0) or 0
                tc = clp / usd if usd > 0 else 0
                
                print(f"      • {ml.get('name', 'Sin nombre')[:60]}")
                print(f"        USD: ${usd:,.2f} | CLP: ${clp:,.0f} | TC: {tc:,.4f}")
        
        print()
    else:
        print(f"⚠️  OC {oc_nombre} - No se encontró factura asociada")
        print(f"   Fecha OC: {oc.get('date_order', 'N/A')}")
        print(f"   Total USD: ${oc.get('amount_untaxed', 0):,.2f}")
        print()

print("=" * 120)
print("\n🔍 VERIFICACIÓN DE FAC 000001 (AGRICOLA COX)")
print("=" * 120)

# Ahora verificar las OCs de COX
ocs_cox = ["OC12641", "OC12631", "OC12567", "OC12561", "OC12527", "OC12518", "OC12285"]

for oc_nombre in ocs_cox[:3]:  # Solo las primeras 3 para no saturar
    ocs = client.search_read(
        "purchase.order",
        [("name", "=", oc_nombre)],
        ["id", "name", "date_order", "amount_untaxed"],
        limit=1
    )
    
    if ocs:
        oc = ocs[0]
        print(f"\n📦 OC: {oc_nombre}")
        print(f"   📅 Fecha: {oc.get('date_order', 'N/A')}")
        print(f"   💵 Total USD: ${oc.get('amount_untaxed', 0):,.2f}")

print("\n" + "=" * 120)

"""
Investigación profunda: Analizar direcciones de movimientos
Para entender cuál campo corresponde a consumo vs producción
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("INVESTIGACIÓN: DIRECCIONES DE MOVIMIENTOS EN ÓRDENES DE PRODUCCIÓN")
print("="*140)

# Obtener una orden con movimientos
ordenes = odoo.search_read(
    'mrp.production',
    [
        ['date_planned_start', '>=', '2025-11-01'],
        ['state', '=', 'done']
    ],
    ['id', 'name'],
    limit=5
)

for orden in ordenes:
    orden_id = orden['id']
    print(f"\n{'='*140}")
    print(f"ORDEN: {orden['name']} (ID: {orden_id})")
    print(f"{'='*140}")
    
    # Movimientos con raw_material_production_id
    print(f"\n📦 MOVIMIENTOS CON 'raw_material_production_id' = {orden_id}")
    print(f"{'-'*140}")
    
    moves_raw = odoo.search_read(
        'stock.move',
        [
            ['raw_material_production_id', '=', orden_id],
            ['state', '=', 'done']
        ],
        ['product_id', 'quantity_done', 'location_id', 'location_dest_id', 'picking_type_id'],
        limit=20
    )
    
    for mov in moves_raw[:5]:  # Solo primeros 5
        prod = mov.get('product_id', [None, 'N/A'])[1] if mov.get('product_id') else 'N/A'
        qty = mov.get('quantity_done', 0)
        loc_from = mov.get('location_id', [None, 'N/A'])[1] if mov.get('location_id') else 'N/A'
        loc_to = mov.get('location_dest_id', [None, 'N/A'])[1] if mov.get('location_dest_id') else 'N/A'
        picking_type = mov.get('picking_type_id', [None, 'N/A'])[1] if mov.get('picking_type_id') else 'N/A'
        
        print(f"   • {prod[:60]}: {qty:.2f} kg")
        print(f"     Desde: {loc_from}")
        print(f"     Hacia: {loc_to}")
        print(f"     Tipo: {picking_type}")
        
        # Analizar dirección
        if 'Production' in loc_to or 'production' in loc_to.lower():
            print(f"     ➡️  ENTRA A PRODUCCIÓN (consumo MP)")
        elif 'Production' in loc_from or 'production' in loc_from.lower():
            print(f"     ⬅️  SALE DE PRODUCCIÓN (producción PT)")
        print()
    
    print(f"   Total: {len(moves_raw)} movimientos")
    
    # Movimientos con production_id
    print(f"\n🏭 MOVIMIENTOS CON 'production_id' = {orden_id}")
    print(f"{'-'*140}")
    
    moves_prod = odoo.search_read(
        'stock.move',
        [
            ['production_id', '=', orden_id],
            ['state', '=', 'done']
        ],
        ['product_id', 'quantity_done', 'location_id', 'location_dest_id', 'picking_type_id'],
        limit=20
    )
    
    for mov in moves_prod[:5]:  # Solo primeros 5
        prod = mov.get('product_id', [None, 'N/A'])[1] if mov.get('product_id') else 'N/A'
        qty = mov.get('quantity_done', 0)
        loc_from = mov.get('location_id', [None, 'N/A'])[1] if mov.get('location_id') else 'N/A'
        loc_to = mov.get('location_dest_id', [None, 'N/A'])[1] if mov.get('location_dest_id') else 'N/A'
        picking_type = mov.get('picking_type_id', [None, 'N/A'])[1] if mov.get('picking_type_id') else 'N/A'
        
        print(f"   • {prod[:60]}: {qty:.2f} kg")
        print(f"     Desde: {loc_from}")
        print(f"     Hacia: {loc_to}")
        print(f"     Tipo: {picking_type}")
        
        # Analizar dirección
        if 'Production' in loc_to or 'production' in loc_to.lower():
            print(f"     ➡️  ENTRA A PRODUCCIÓN (consumo MP)")
        elif 'Production' in loc_from or 'production' in loc_from.lower():
            print(f"     ⬅️  SALE DE PRODUCCIÓN (producción PT)")
        print()
    
    print(f"   Total: {len(moves_prod)} movimientos")
    
    # Totales
    total_raw = sum([m.get('quantity_done', 0) for m in moves_raw])
    total_prod = sum([m.get('quantity_done', 0) for m in moves_prod])
    
    print(f"\n📊 TOTALES DE ESTA ORDEN:")
    print(f"   raw_material_production_id: {total_raw:,.2f} kg")
    print(f"   production_id: {total_prod:,.2f} kg")
    
    if total_raw > 0 and total_prod > 0:
        rend_actual = (total_prod / total_raw) * 100
        rend_invertido = (total_raw / total_prod) * 100
        
        print(f"\n   Si usamos como está:")
        print(f"      Consumo = raw_material → Producción = production")
        print(f"      Rendimiento = {rend_actual:.1f}%")
        
        print(f"\n   Si invertimos:")
        print(f"      Consumo = production → Producción = raw_material")
        print(f"      Rendimiento = {rend_invertido:.1f}%")
        
        if 70 <= rend_invertido <= 100:
            print(f"      ✅ ESTE ES CORRECTO (rendimiento lógico 70-100%)")
        elif 70 <= rend_actual <= 100:
            print(f"      ✅ ESTE ES CORRECTO (rendimiento lógico 70-100%)")

print(f"\n{'='*140}")
print("FIN DE INVESTIGACIÓN")
print("="*140)

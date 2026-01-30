"""
Script para revertir asignación incorrecta y buscar el quant correcto de 689.50 kg

Uso:
    python scripts/fix_pack0003794_correcto.py
"""

import sys
import os

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# Credenciales
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

def main():
    """Revierte asignación incorrecta y asigna el quant correcto."""
    
    print("=" * 80)
    print("CORRECCIÓN PACK0003794 - BUSCAR 689.50 KG")
    print("=" * 80)
    
    # Conectar a Odoo
    print("\n1. Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("   ✓ Conectado exitosamente")
    
    # Buscar el paquete
    print("\n2. Buscando paquete PACK0003794...")
    packages = odoo.search_read(
        "stock.quant.package",
        [("name", "=", "PACK0003794")],
        ["id", "name"]
    )
    
    if not packages:
        print("   ✗ ERROR: Paquete no encontrado")
        return
    
    package_id = packages[0]["id"]
    print(f"   ✓ Paquete encontrado (ID: {package_id})")
    
    # Paso 1: Revertir la asignación incorrecta
    print("\n3. Revirtiendo asignación incorrecta del quant 176014...")
    try:
        odoo.execute("stock.quant", "write", [176014], {"package_id": False})
        print("   ✓ Quant 176014 desasignado del paquete")
    except Exception as e:
        print(f"   ⚠ Error al desasignar: {e}")
    
    # Buscar el producto
    print("\n4. Buscando producto 101122000...")
    products = odoo.search_read(
        "product.product",
        [("default_code", "=", "101122000")],
        ["id", "name"]
    )
    
    if not products:
        print("   ✗ ERROR: Producto no encontrado")
        return
    
    product_id = products[0]["id"]
    product_name = products[0]["name"]
    print(f"   ✓ Producto encontrado: {product_name}")
    
    # Buscar el lote
    print("\n5. Buscando lote 0001533...")
    lots = odoo.search_read(
        "stock.lot",
        [("name", "=", "0001533"), ("product_id", "=", product_id)],
        ["id", "name"]
    )
    
    if not lots:
        print("   ✗ ERROR: Lote no encontrado")
        return
    
    lot_id = lots[0]["id"]
    print(f"   ✓ Lote encontrado (ID: {lot_id})")
    
    # Buscar TODOS los quants con ese producto/lote en CUALQUIER ubicación
    print("\n6. Buscando TODOS los quants del producto/lote...")
    all_quants = odoo.search_read(
        "stock.quant",
        [
            ("product_id", "=", product_id),
            ("lot_id", "=", lot_id),
            ("quantity", ">", 0)
        ],
        ["id", "quantity", "location_id", "package_id", "reserved_quantity"],
        order="quantity asc"
    )
    
    print(f"   ✓ Encontrados {len(all_quants)} quants totales")
    print("\n   Lista completa de quants:")
    for q in all_quants:
        loc_name = q["location_id"][1] if q.get("location_id") else "N/A"
        pkg = q["package_id"][1] if q.get("package_id") else "SIN PAQUETE"
        print(f"      - ID {q['id']}: {q['quantity']} kg | {loc_name} | Paquete: {pkg}")
    
    # Buscar específicamente el de 689.50 kg
    print("\n7. Buscando quant de exactamente 689.50 kg...")
    quant_correcto = None
    for q in all_quants:
        if abs(q['quantity'] - 689.50) < 0.01:  # Tolerancia por decimales
            quant_correcto = q
            break
    
    if not quant_correcto:
        print("   ✗ No se encontró quant de 689.50 kg exactos")
        print("\n   ¿Alguno de estos es el correcto? Revisa manualmente.")
        return
    
    print(f"   ✓ Quant correcto encontrado:")
    print(f"      - ID: {quant_correcto['id']}")
    print(f"      - Cantidad: {quant_correcto['quantity']} kg")
    print(f"      - Ubicación: {quant_correcto['location_id'][1]}")
    print(f"      - Paquete actual: {quant_correcto['package_id'][1] if quant_correcto.get('package_id') else 'SIN PAQUETE'}")
    
    # Asignar el quant correcto
    print("\n8. Asignando quant correcto al paquete...")
    try:
        # Si tiene reserva, liberarla
        if quant_correcto.get("reserved_quantity", 0) > 0:
            print(f"   Liberando {quant_correcto['reserved_quantity']} kg reservados...")
            odoo.execute("stock.quant", "write", [quant_correcto["id"]], {"reserved_quantity": 0})
        
        # Asignar al paquete
        odoo.execute("stock.quant", "write", [quant_correcto["id"]], {"package_id": package_id})
        print(f"   ✓ Quant {quant_correcto['id']} asignado al paquete PACK0003794")
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        return
    
    # Verificar resultado final
    print("\n9. Verificando resultado final...")
    quants_finales = odoo.search_read(
        "stock.quant",
        [
            ("package_id", "=", package_id),
            ("quantity", ">", 0)
        ],
        ["product_id", "lot_id", "location_id", "quantity"]
    )
    
    total_final = sum(q["quantity"] for q in quants_finales)
    
    print("\n" + "=" * 80)
    print("CORRECCIÓN COMPLETADA")
    print("=" * 80)
    print(f"\nRESUMEN:")
    print(f"  - Paquete: PACK0003794")
    print(f"  - Total en paquete: {total_final} kg")
    
    if quants_finales:
        print(f"\n  Contenido del paquete:")
        for q in quants_finales:
            prod_name = q["product_id"][1] if q.get("product_id") else "N/A"
            lot_name = q["lot_id"][1] if q.get("lot_id") else "N/A"
            loc_name = q["location_id"][1] if q.get("location_id") else "N/A"
            print(f"    - {q['quantity']} kg | {prod_name} | Lote: {lot_name} | {loc_name}")
    
    print("\n✓ Paquete corregido exitosamente")


if __name__ == "__main__":
    main()

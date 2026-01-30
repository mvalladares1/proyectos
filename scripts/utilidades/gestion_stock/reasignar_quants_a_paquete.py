"""
Script para reasignar quants huérfanos al paquete correcto
Busca quants del mismo producto/lote/ubicación y los asocia al paquete.

Uso:
    python scripts/reasignar_quants_a_paquete.py
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
    """Reasigna quants huérfanos al paquete correcto."""
    
    print("=" * 80)
    print("REASIGNACIÓN DE QUANTS A PAQUETE - PACK0003794")
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
        print("   ✗ ERROR: Paquete PACK0003794 no encontrado")
        return
    
    package_id = packages[0]["id"]
    print(f"   ✓ Paquete encontrado (ID: {package_id})")
    
    # Buscar el producto
    print("\n3. Buscando producto 101122000...")
    products = odoo.search_read(
        "product.product",
        [("default_code", "=", "101122000")],
        ["id", "name"]
    )
    
    if not products:
        print("   ✗ ERROR: Producto 101122000 no encontrado")
        return
    
    product_id = products[0]["id"]
    product_name = products[0]["name"]
    print(f"   ✓ Producto encontrado: {product_name} (ID: {product_id})")
    
    # Buscar el lote 0001533 (el correcto)
    print("\n4. Buscando lote 0001533...")
    lots = odoo.search_read(
        "stock.lot",
        [("name", "=", "0001533"), ("product_id", "=", product_id)],
        ["id", "name"]
    )
    
    if not lots:
        print("   ✗ ERROR: Lote 0001533 no encontrado")
        return
    
    lot_id = lots[0]["id"]
    print(f"   ✓ Lote encontrado (ID: {lot_id})")
    
    # Verificar estado actual del paquete
    print("\n5. Verificando contenido actual del paquete...")
    quants_en_paquete = odoo.search_read(
        "stock.quant",
        [
            ("package_id", "=", package_id),
            ("quantity", ">", 0)
        ],
        ["product_id", "lot_id", "location_id", "quantity"]
    )
    
    total_en_paquete = sum(q["quantity"] for q in quants_en_paquete)
    print(f"   Quants actuales en paquete: {len(quants_en_paquete)}")
    print(f"   Total kg en paquete: {total_en_paquete}")
    
    # Buscar quants huérfanos (mismo producto/lote pero sin paquete o con otro paquete)
    print("\n6. Buscando quants huérfanos del mismo producto/lote...")
    
    # Buscar específicamente en la ubicación original: RF/Stock/Camara 0°C REAL
    location_original = odoo.search_read(
        "stock.location",
        [("complete_name", "=", "RF/Stock/Camara 0°C REAL")],
        ["id"]
    )
    
    if not location_original:
        print("   ✗ ERROR: No se encontró la ubicación original")
        return
    
    location_id_original = location_original[0]["id"]
    
    # Buscar solo en la ubicación original, cantidad aproximada a 689.50 kg
    quants_huerfanos = odoo.search_read(
        "stock.quant",
        [
            ("product_id", "=", product_id),
            ("lot_id", "=", lot_id),
            ("location_id", "=", location_id_original),
            ("quantity", ">", 0),
            "|",
            ("package_id", "=", False),
            ("package_id", "!=", package_id)
        ],
        ["id", "location_id", "quantity", "package_id", "reserved_quantity"]
    )
    
    print(f"   ✓ Encontrados {len(quants_huerfanos)} quants huérfanos")
    
    if not quants_huerfanos:
        print("\n   No hay quants para reasignar. El paquete puede estar correcto.")
        return
    
    # Mostrar detalles de quants huérfanos
    print("\n   Detalles de quants huérfanos:")
    for q in quants_huerfanos:
        loc_name = q["location_id"][1] if q.get("location_id") else "N/A"
        pkg = q["package_id"][1] if q.get("package_id") else "SIN PAQUETE"
        print(f"      - ID {q['id']}: {q['quantity']} kg en {loc_name} (Paquete: {pkg})")
    
    # Información de lo que se hará
    print("\n" + "=" * 80)
    print("⚠️  ACCIÓN A REALIZAR:")
    print("=" * 80)
    total_reasignar = sum(q["quantity"] for q in quants_huerfanos)
    print(f"Se reasignarán {len(quants_huerfanos)} quants ({total_reasignar} kg) al paquete PACK0003794")
    
    # Reasignar quants
    print("\n7. Reasignando quants al paquete...")
    reasignados = 0
    errores = 0
    
    for q in quants_huerfanos:
        try:
            # Si tiene cantidad reservada, liberarla primero
            if q.get("reserved_quantity", 0) > 0:
                print(f"   Liberando {q['reserved_quantity']} kg reservados del quant {q['id']}...")
                odoo.execute("stock.quant", "write", [q["id"]], {"reserved_quantity": 0})
            
            # Reasignar al paquete
            odoo.execute("stock.quant", "write", [q["id"]], {"package_id": package_id})
            reasignados += 1
            print(f"   ✓ Quant {q['id']} reasignado ({q['quantity']} kg)")
        except Exception as e:
            errores += 1
            print(f"   ✗ Error reasignando quant {q['id']}: {e}")
    
    # Verificar resultado final
    print("\n8. Verificando resultado final...")
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
    print("REASIGNACIÓN COMPLETADA")
    print("=" * 80)
    print(f"\nRESUMEN:")
    print(f"  - Paquete: PACK0003794 (ID: {package_id})")
    print(f"  - Producto: {product_name}")
    print(f"  - Lote: 0001533")
    print(f"  - Quants reasignados: {reasignados}")
    print(f"  - Errores: {errores}")
    print(f"  - Total en paquete antes: {total_en_paquete} kg")
    print(f"  - Total en paquete ahora: {total_final} kg")
    
    if quants_finales:
        print(f"\n  Contenido del paquete:")
        for q in quants_finales:
            prod_name = q["product_id"][1] if q.get("product_id") else "N/A"
            lot_name = q["lot_id"][1] if q.get("lot_id") else "N/A"
            loc_name = q["location_id"][1] if q.get("location_id") else "N/A"
            print(f"    - {q['quantity']} kg | {prod_name} | Lote: {lot_name} | Ubicación: {loc_name}")
    
    print("\n✓ Paquete restaurado exitosamente")


if __name__ == "__main__":
    main()

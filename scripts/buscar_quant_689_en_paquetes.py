"""
Script para buscar el quant de 689.50 kg en TODOS los paquetes

Uso:
    python scripts/buscar_quant_689_en_paquetes.py
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
    """Busca el quant de 689.50 kg en todos los paquetes."""
    
    print("=" * 80)
    print("BÚSQUEDA DE QUANT 689.50 KG - PRODUCTO 101122000 LOTE 0001533")
    print("=" * 80)
    
    # Conectar a Odoo
    print("\n1. Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("   ✓ Conectado exitosamente")
    
    # Buscar el producto
    print("\n2. Buscando producto 101122000...")
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
    print(f"   ✓ Producto: {product_name}")
    
    # Buscar el lote
    print("\n3. Buscando lote 0001533...")
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
    
    # Buscar TODOS los quants con ese producto/lote (incluyendo los que tienen paquete)
    print("\n4. Buscando TODOS los quants (con y sin paquete)...")
    all_quants = odoo.search_read(
        "stock.quant",
        [
            ("product_id", "=", product_id),
            ("lot_id", "=", lot_id),
            ("quantity", ">", 0),
            ("location_id.usage", "=", "internal")  # Solo ubicaciones internas
        ],
        ["id", "quantity", "location_id", "package_id", "reserved_quantity"],
        order="quantity asc"
    )
    
    print(f"\n   ✓ Encontrados {len(all_quants)} quants totales")
    print("\n   " + "=" * 76)
    print("   LISTA COMPLETA DE QUANTS:")
    print("   " + "=" * 76)
    
    quant_689 = None
    
    for q in all_quants:
        loc_name = q["location_id"][1] if q.get("location_id") else "N/A"
        pkg_name = q["package_id"][1] if q.get("package_id") else "❌ SIN PAQUETE"
        reservado = q.get("reserved_quantity", 0)
        
        # Marcar si es el de 689.50 kg
        es_689 = ""
        if abs(q['quantity'] - 689.50) < 0.01:
            es_689 = " ⭐ ESTE ES!"
            quant_689 = q
        
        print(f"   ID {q['id']:>6} | {q['quantity']:>8.2f} kg | {loc_name[:35]:<35} | {pkg_name[:20]:<20}{es_689}")
        if reservado > 0:
            print(f"          └─ ⚠️  {reservado} kg reservados")
    
    print("   " + "=" * 76)
    
    # Si se encontró el de 689.50
    if quant_689:
        print("\n5. ⭐ QUANT DE 689.50 KG ENCONTRADO!")
        print(f"\n   Detalles:")
        print(f"   - ID: {quant_689['id']}")
        print(f"   - Cantidad: {quant_689['quantity']} kg")
        print(f"   - Ubicación: {quant_689['location_id'][1]}")
        
        if quant_689.get('package_id'):
            pkg_id = quant_689['package_id'][0]
            pkg_name = quant_689['package_id'][1]
            print(f"   - Paquete ACTUAL: {pkg_name} (ID: {pkg_id})")
            print(f"\n   ¿Quieres moverlo a PACK0003794?")
            print(f"\n6. Reasignando a PACK0003794...")
            
            # Buscar el paquete destino
            packages = odoo.search_read(
                "stock.quant.package",
                [("name", "=", "PACK0003794")],
                ["id"]
            )
            
            if packages:
                package_id = packages[0]["id"]
                
                try:
                    # Liberar reservas si las hay
                    if quant_689.get("reserved_quantity", 0) > 0:
                        print(f"   Liberando {quant_689['reserved_quantity']} kg reservados...")
                        odoo.execute("stock.quant", "write", [quant_689["id"]], {"reserved_quantity": 0})
                    
                    # Reasignar
                    odoo.execute("stock.quant", "write", [quant_689["id"]], {"package_id": package_id})
                    print(f"   ✓ Quant {quant_689['id']} reasignado de {pkg_name} a PACK0003794")
                    
                    # Verificar
                    print("\n7. Verificando PACK0003794...")
                    quants_finales = odoo.search_read(
                        "stock.quant",
                        [("package_id", "=", package_id), ("quantity", ">", 0)],
                        ["quantity", "product_id", "lot_id", "location_id"]
                    )
                    
                    total = sum(q["quantity"] for q in quants_finales)
                    print(f"   ✓ Total en PACK0003794: {total} kg")
                    for q in quants_finales:
                        print(f"      - {q['quantity']} kg | {q['lot_id'][1]} | {q['location_id'][1]}")
                    
                    print("\n✅ CORRECCIÓN COMPLETADA")
                    
                except Exception as e:
                    print(f"   ✗ ERROR: {e}")
            else:
                print("   ✗ No se encontró PACK0003794")
        else:
            print(f"   - Paquete ACTUAL: ❌ SIN PAQUETE")
            print(f"\n   Asignando a PACK0003794...")
            
            # Buscar el paquete destino
            packages = odoo.search_read(
                "stock.quant.package",
                [("name", "=", "PACK0003794")],
                ["id"]
            )
            
            if packages:
                package_id = packages[0]["id"]
                
                try:
                    odoo.execute("stock.quant", "write", [quant_689["id"]], {"package_id": package_id})
                    print(f"   ✓ Quant {quant_689['id']} asignado a PACK0003794")
                    print("\n✅ CORRECCIÓN COMPLETADA")
                except Exception as e:
                    print(f"   ✗ ERROR: {e}")
    else:
        print("\n   ❌ No se encontró quant de exactamente 689.50 kg")
        print("\n   Posibles causas:")
        print("   - El quant fue dividido en operaciones posteriores")
        print("   - Fue consumido o movido con otra cantidad")
        print("   - Los decimales no coinciden exactamente")


if __name__ == "__main__":
    main()

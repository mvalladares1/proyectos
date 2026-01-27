"""
Script para corregir quant negativo en PACK0003794
Elimina la línea negativa del lote 0001535.

Uso:
    python scripts/fix_quant_negativo_pack0003794.py
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
    """Corrige el quant negativo de manera directa."""
    
    print("=" * 80)
    print("CORRECCIÓN DE QUANT NEGATIVO - PACK0003794")
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
    
    # Buscar el lote 0001535 (el que está negativo)
    print("\n4. Buscando lote 0001535...")
    lots = odoo.search_read(
        "stock.lot",
        [("name", "=", "0001535"), ("product_id", "=", product_id)],
        ["id", "name"]
    )
    
    if not lots:
        print("   ✗ ERROR: Lote 0001535 no encontrado")
        return
    
    lot_id = lots[0]["id"]
    print(f"   ✓ Lote encontrado (ID: {lot_id})")
    
    # Buscar la ubicación
    print("\n5. Buscando ubicación RF/Stock/Camara 0°C REAL...")
    locations = odoo.search_read(
        "stock.location",
        [("complete_name", "=", "RF/Stock/Camara 0°C REAL")],
        ["id", "name", "complete_name"]
    )
    
    if not locations:
        print("   ✗ ERROR: Ubicación no encontrada")
        return
    
    location_id = locations[0]["id"]
    print(f"   ✓ Ubicación encontrada (ID: {location_id})")
    
    # Buscar el quant problemático
    print("\n6. Buscando quant negativo...")
    quants = odoo.search_read(
        "stock.quant",
        [
            ("package_id", "=", package_id),
            ("product_id", "=", product_id),
            ("lot_id", "=", lot_id),
            ("location_id", "=", location_id),
            ("quantity", "<", 0)
        ],
        ["id", "quantity", "reserved_quantity"]
    )
    
    if not quants:
        print("   ✓ No se encontró quant negativo (puede que ya esté corregido)")
        return
    
    quant = quants[0]
    quant_id = quant["id"]
    qty_anterior = quant["quantity"]
    qty_reservada = quant.get("reserved_quantity", 0)
    
    print(f"   ✓ Quant encontrado:")
    print(f"      - ID: {quant_id}")
    print(f"      - Cantidad actual: {qty_anterior}")
    print(f"      - Cantidad reservada: {qty_reservada}")
    
    # Verificar si hay cantidad reservada
    if qty_reservada != 0:
        print(f"\n   ⚠ ADVERTENCIA: Hay {qty_reservada} unidades reservadas")
        print("   Liberando reservas primero...")
        odoo.execute("stock.quant", "write", [quant_id], {"reserved_quantity": 0})
        print("   ✓ Reservas liberadas")
    
    # Corregir el quant directamente
    print("\n7. Corrigiendo quant (poniendo quantity = 0)...")
    try:
        odoo.execute("stock.quant", "write", [quant_id], {"quantity": 0.0})
        print("   ✓ Quant corregido exitosamente")
    except Exception as e:
        print(f"   ✗ ERROR al corregir: {e}")
        return
    
    # Verificar el resultado
    print("\n8. Verificando corrección...")
    quant_verificado = odoo.search_read(
        "stock.quant",
        [("id", "=", quant_id)],
        ["quantity"]
    )
    
    if quant_verificado:
        qty_final = quant_verificado[0]["quantity"]
        print(f"   ✓ Verificación exitosa:")
        print(f"      - Cantidad anterior: {qty_anterior}")
        print(f"      - Cantidad final: {qty_final}")
    
    print("\n" + "=" * 80)
    print("CORRECCIÓN COMPLETADA")
    print("=" * 80)
    print(f"\nRESUMEN:")
    print(f"  - Quant ID: {quant_id}")
    print(f"  - Paquete: PACK0003794")
    print(f"  - Producto: {product_name}")
    print(f"  - Lote: 0001535")
    print(f"  - Ubicación: RF/Stock/Camara 0°C REAL")
    print(f"  - Cantidad corregida: {qty_anterior} → 0.0")
    print("\n✓ El error ha sido revertido exitosamente")


if __name__ == "__main__":
    main()

"""
Script para buscar la ubicación correcta de Camara 8
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

username = input("Usuario: ").strip()
password = input("API Key: ").strip()

odoo = OdooClient(username=username, password=password)

# Buscar Camara 8
print("\n🔍 Buscando 'Camara 8'...")
locations = odoo.search_read(
    "stock.location",
    [("name", "ilike", "Camara 8")],
    ["id", "name", "complete_name", "usage", "active", "barcode"]
)

print(f"\n✅ Encontradas {len(locations)} ubicaciones:\n")
for loc in locations:
    print(f"ID: {loc['id']}")
    print(f"Nombre: {loc['name']}")
    print(f"Ruta completa: {loc.get('complete_name', 'N/A')}")
    print(f"Tipo: {loc['usage']}")
    print(f"Activo: {loc['active']}")
    print(f"Barcode: {loc.get('barcode', 'N/A')}")
    print("-" * 60)

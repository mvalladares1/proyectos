"""
Script para actualizar los barcodes de pasillos VILKUN
De: CAM01A1, CAM01B1, etc.
A: CAMVLKA1, CAMVLKB1, etc.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

def main():
    print("Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    
    ubicaciones = odoo.search_read(
        "stock.location",
        [("location_id", "=", 8529)],
        ["id", "name", "barcode"],
        order="name"
    )
    
    print(f"\nActualizando {len(ubicaciones)} códigos de barras...")
    for loc in ubicaciones:
        nuevo_barcode = "CAMVLK" + loc["name"]
        odoo.write("stock.location", [loc["id"]], {"barcode": nuevo_barcode})
        print(f"  {loc['name']}: {loc['barcode']} -> {nuevo_barcode}")
    
    print("\n✓ Códigos actualizados!")
    
    print("\nVerificación final:")
    ubicaciones = odoo.search_read(
        "stock.location",
        [("location_id", "=", 8529)],
        ["name", "barcode"],
        order="name"
    )
    for loc in ubicaciones:
        print(f"  {loc['name']}: {loc['barcode']}")

if __name__ == "__main__":
    main()

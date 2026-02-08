"""
Script para crear los pasillos de la Cámara 1 -25°C en VILKUN

Crea 16 ubicaciones:
- A1 a A8 (lado A)
- B1 a B8 (lado B)

Códigos de barras: CAM01A1, CAM01A2... CAM01B1, CAM01B2...

Uso:
    python scripts/utilidades/gestion_stock/crear_pasillos_vilkun.py
"""

import sys
import os

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from shared.odoo_client import OdooClient

# Credenciales
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Configuración
UBICACION_PADRE_NOMBRE = "VLK/Camara 1 -25°C"
PASILLOS = [
    # Lado A
    {"name": "A1", "barcode": "CAM01A1"},
    {"name": "A2", "barcode": "CAM01A2"},
    {"name": "A3", "barcode": "CAM01A3"},
    {"name": "A4", "barcode": "CAM01A4"},
    {"name": "A5", "barcode": "CAM01A5"},
    {"name": "A6", "barcode": "CAM01A6"},
    {"name": "A7", "barcode": "CAM01A7"},
    {"name": "A8", "barcode": "CAM01A8"},
    # Lado B
    {"name": "B1", "barcode": "CAM01B1"},
    {"name": "B2", "barcode": "CAM01B2"},
    {"name": "B3", "barcode": "CAM01B3"},
    {"name": "B4", "barcode": "CAM01B4"},
    {"name": "B5", "barcode": "CAM01B5"},
    {"name": "B6", "barcode": "CAM01B6"},
    {"name": "B7", "barcode": "CAM01B7"},
    {"name": "B8", "barcode": "CAM01B8"},
]


def main():
    """Crea los pasillos de la Cámara 1 -25°C en VILKUN."""
    
    print("=" * 80)
    print("CREAR PASILLOS - VLK/Camara 1 -25°C")
    print("=" * 80)
    
    # Conectar a Odoo
    print("\n1. Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("   ✓ Conectado exitosamente")
    
    # Buscar ubicación padre
    print(f"\n2. Buscando ubicación padre: {UBICACION_PADRE_NOMBRE}...")
    ubicacion_padre = odoo.search_read(
        "stock.location",
        [("complete_name", "=", UBICACION_PADRE_NOMBRE)],
        ["id", "name", "company_id"]
    )
    
    if not ubicacion_padre:
        print(f"   ✗ ERROR: Ubicación '{UBICACION_PADRE_NOMBRE}' no encontrada")
        return
    
    padre_id = ubicacion_padre[0]["id"]
    company_id = ubicacion_padre[0]["company_id"][0] if ubicacion_padre[0]["company_id"] else False
    print(f"   ✓ Ubicación padre encontrada (ID: {padre_id})")
    print(f"   ✓ Compañía: {ubicacion_padre[0]['company_id']}")
    
    # Verificar ubicaciones existentes
    print("\n3. Verificando ubicaciones existentes...")
    existentes = odoo.search_read(
        "stock.location",
        [("location_id", "=", padre_id)],
        ["name", "barcode"]
    )
    
    nombres_existentes = {loc["name"] for loc in existentes}
    barcodes_existentes = {loc["barcode"] for loc in existentes if loc["barcode"]}
    
    if existentes:
        print(f"   ⚠ Ya existen {len(existentes)} ubicaciones hijas:")
        for loc in existentes:
            print(f"      - {loc['name']} (barcode: {loc['barcode']})")
    else:
        print("   ✓ No hay ubicaciones hijas existentes")
    
    # Crear pasillos
    print("\n4. Creando pasillos...")
    creados = 0
    errores = 0
    
    for pasillo in PASILLOS:
        nombre = pasillo["name"]
        barcode = pasillo["barcode"]
        
        # Verificar si ya existe
        if nombre in nombres_existentes:
            print(f"   ⚠ {nombre} ya existe - saltando")
            continue
            
        if barcode in barcodes_existentes:
            print(f"   ⚠ Barcode {barcode} ya existe - saltando")
            continue
        
        try:
            # Crear ubicación
            valores = {
                "name": nombre,
                "location_id": padre_id,
                "usage": "internal",
                "company_id": company_id,
                "barcode": barcode,
                # Coordenadas vacías (ubicación general)
                "posx": 0,
                "posy": 0,
                "posz": 0,
            }
            
            nuevo_id = odoo.execute("stock.location", "create", valores)
            print(f"   ✓ Creado: {nombre} (ID: {nuevo_id}, barcode: {barcode})")
            creados += 1
            
        except Exception as e:
            print(f"   ✗ Error creando {nombre}: {e}")
            errores += 1
    
    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"   Ubicaciones creadas: {creados}")
    print(f"   Errores: {errores}")
    print(f"   Saltadas (ya existían): {len(PASILLOS) - creados - errores}")
    
    # Verificar resultado final
    if creados > 0:
        print("\n5. Verificando ubicaciones creadas...")
        todas = odoo.search_read(
            "stock.location",
            [("location_id", "=", padre_id)],
            ["name", "barcode", "complete_name"],
            order="name"
        )
        print(f"\n   Ubicaciones en {UBICACION_PADRE_NOMBRE}:")
        for loc in todas:
            print(f"      - {loc['complete_name']} | Barcode: {loc['barcode']}")


if __name__ == "__main__":
    main()

"""
DEBUG: Investigar nombres exactos de diarios
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

# Configuración
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 140)
print("DEBUG: NOMBRES DE DIARIOS DISPONIBLES")
print("=" * 140)

odoo = OdooClient(username=USERNAME, password=PASSWORD)

# Obtener todos los diarios
diarios = odoo.search_read(
    'account.journal',
    [],
    ['id', 'name', 'code', 'type'],
    limit=10000
)

print(f"\n✓ Total de diarios encontrados: {len(diarios)}")

# Filtrar solo los que tienen "Factura" en el nombre
diarios_factura = [d for d in diarios if 'factura' in d.get('name', '').lower()]

print(f"\n📋 DIARIOS CON 'FACTURA' EN EL NOMBRE:")
print("=" * 140)
for d in sorted(diarios_factura, key=lambda x: x.get('name', '')):
    print(f"   ID: {d['id']:5} | Nombre: {d.get('name', 'Sin nombre'):50} | Código: {d.get('code', 'N/A'):10} | Tipo: {d.get('type', 'N/A')}")

print(f"\n📋 TODOS LOS DIARIOS:")
print("=" * 140)
for d in sorted(diarios, key=lambda x: x.get('name', '')):
    print(f"   ID: {d['id']:5} | Nombre: {d.get('name', 'Sin nombre'):50} | Código: {d.get('code', 'N/A'):10} | Tipo: {d.get('type', 'N/A')}")

print("\n" + "=" * 140)
print("DEBUG COMPLETADO")
print("=" * 140)

"""
DEBUG: Verificar que el clasificador detecta cuenta 41010101 -> 1.1.1
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.services.flujo_caja.clasificador import ClasificadorCuentas
import json

print("=" * 70)
print("DEBUG: Verificar clasificador para cuenta 41010101")
print("=" * 70)

# Cargar mapeo
mapeo_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backend", "data", "mapeo_cuentas.json"
)
with open(mapeo_path, 'r', encoding='utf-8') as f:
    mapeo = json.load(f)

# Ver si cuenta 41010101 está en mapeo
print("\n[MAPEO_CUENTAS]")
if '41010101' in mapeo.get('mapeo_cuentas', {}):
    print(f"   41010101 -> {mapeo['mapeo_cuentas']['41010101']}")
else:
    print("   41010101 NO está en mapeo_cuentas!")

# Probar clasificador
clasificador = ClasificadorCuentas(mapeo)

# Test clasificacion
resultado = clasificador.clasificar_cuenta('41010101')
print(f"\n[CLASIFICADOR]")
print(f"   clasificar_cuenta('41010101') = {resultado}")

# Ver otras cuentas de prueba
for cuenta in ['21020101', '21010101', '82010102', '51010102']:
    res = clasificador.clasificar_cuenta(cuenta)
    print(f"   clasificar_cuenta('{cuenta}') = {res}")

print("\n" + "=" * 70)

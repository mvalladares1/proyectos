"""
DEBUG: Test clasificador para 11030101
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DEBUG: Test clasificador 11030101")
print("=" * 70)

svc = FlujoCajaService(USERNAME, PASSWORD)

# Test clasificacion
for cuenta in ['11030101', '11030103', '41010101']:
    resultado = svc._clasificar_cuenta(cuenta)
    print(f"   _clasificar_cuenta('{cuenta}') = {resultado}")

print("\n" + "=" * 70)

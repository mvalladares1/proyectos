"""
DEBUG: Bulk check for FAC 000256 duplicates in etiquetas
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DEBUG: BULK ETIQUETAS CHECK")
print("=" * 70)

svc = FlujoCajaService(USERNAME, PASSWORD)
mgr = svc.odoo_manager

# 1. Get Movimientos Efectivo (Bulk)
print("1. Getting Bulk Movimientos (2025-10 to 2026-04)...")
cuentas_config = svc._get_cuentas_efectivo_config()
movs, asientos_ids = mgr.get_movimientos_efectivo_periodo(
    '2025-10-01', '2026-04-30', 
    mgr.get_cuentas_efectivo(cuentas_config)
)
print(f"Total Movs: {len(movs)}")
print(f"Total Asientos IDs: {len(asientos_ids)}")

# Check if our payment is there
if 270971 in asientos_ids:
    print("✅ Pago FAC 256 (270971) ESTÁ en asientos_ids")
else:
    print("❌ Pago FAC 256 (270971) NO ESTÁ en asientos_ids")

# Check if Invoice is there (should not be)
if 268883 in asientos_ids:
    print("❌ Factura FAC 256 (268883) ESTÁ en asientos_ids (ERROR CRITICO)")
else:
    print("✅ Factura FAC 256 (268883) NO ESTÁ en asientos_ids")

# 2. Get Etiquetas for 11030101
print("\n2. Getting Etiquetas for 11030101...")
# 11030101 ID is 5 (from previous debug)
etiquetas = mgr.get_etiquetas_por_mes(asientos_ids, [5], 'mensual')
print(f"Total Etiquetas Groups: {len(etiquetas)}")

# 3. Find FAC 000256
found_count = 0
total_balance = 0
for g in etiquetas:
    name = g.get('name', '')
    if name == 'FAC 000256':
        print(f"FOUND: {g}")
        found_count += 1
        total_balance += g.get('balance', 0)

print(f"\nResumen FAC 000256:")
print(f"Found {found_count} times.")
print(f"Total Balance: ${total_balance:,.0f}")
print(f"Inverted (Expected 1.1.1): ${-total_balance:,.0f}")

print("\n" + "=" * 70)

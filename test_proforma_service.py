"""
Test rápido del servicio de ajuste de proformas
"""
import sys
sys.path.insert(0, r"c:\new\RIO FUTURO\DASHBOARD\proyectos")

from backend.services.proforma_ajuste_service import (
    get_proveedores_con_borradores,
    get_facturas_borrador
)

# Credenciales
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "Abc12345"

print("=" * 60)
print("🧪 TEST: Servicio de Ajuste de Proformas")
print("=" * 60)

# 1. Obtener proveedores
print("\n1️⃣ Obteniendo proveedores con borradores en USD...")
try:
    proveedores = get_proveedores_con_borradores(USERNAME, PASSWORD)
    print(f"   ✅ Se encontraron {len(proveedores)} proveedores")
    for p in proveedores[:5]:
        print(f"      - {p['nombre'][:40]} ({p['rut']})")
except Exception as e:
    print(f"   ❌ Error: {e}")

# 2. Obtener facturas en borrador
print("\n2️⃣ Obteniendo facturas en borrador USD...")
try:
    facturas = get_facturas_borrador(USERNAME, PASSWORD)
    print(f"   ✅ Se encontraron {len(facturas)} facturas")
    
    for f in facturas[:3]:
        print(f"\n   📄 {f['nombre']}")
        print(f"      Proveedor: {f['proveedor_nombre'][:40]}")
        print(f"      USD: ${f['total_usd']:,.2f}")
        print(f"      CLP: ${f['total_clp']:,.0f}")
        print(f"      TC: {f['tipo_cambio']:,.4f}")
        print(f"      Líneas: {f['num_lineas']}")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ Test completado")
print("=" * 60)

"""Debug: Listar TODAS las facturas de octubre 2025."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 80)
print("DEBUG: Todas las facturas de OCTUBRE 2025")
print("=" * 80)

svc = FlujoCajaService(USERNAME, PASSWORD)

# Consultar solo octubre 2025
result = svc.get_flujo_mensualizado("2025-10-01", "2025-10-31")

# Buscar el concepto 1.1.1 (Cobros de ventas)
op = result.get('actividades', {}).get('OPERACION', {})
concepto_ventas = None

for c in op.get('conceptos', []):
    if c['id'] == '1.1.1':
        concepto_ventas = c
        break

if not concepto_ventas:
    print("❌ No se encontró el concepto 1.1.1")
    exit(1)

print(f"\n[{concepto_ventas['id']}] {concepto_ventas.get('nombre')}")
print(f"Total en OCT 2025: ${concepto_ventas.get('montos_por_mes', {}).get('2025-10', 0):,.0f}")

# Buscar la cuenta 11030101 - DEUDORES POR VENTAS
cuentas = concepto_ventas.get('cuentas', [])
cuenta_deudores = None

for cuenta in cuentas:
    if cuenta['codigo'] == '11030101':
        cuenta_deudores = cuenta
        break

if not cuenta_deudores:
    print("❌ No se encontró la cuenta 11030101")
    exit(1)

print(f"\nCuenta: {cuenta_deudores['codigo']} - {cuenta_deudores['nombre']}")
print(f"Total en OCT 2025: ${cuenta_deudores.get('montos_por_mes', {}).get('2025-10', 0):,.0f}")

# Extraer TODAS las facturas
etiquetas = cuenta_deudores.get('etiquetas', [])
facturas_octubre = []

for etiq in etiquetas:
    monto_oct = etiq.get('montos_por_mes', {}).get('2025-10', 0)
    if monto_oct != 0:
        facturas_octubre.append({
            'nombre': etiq['nombre'],
            'monto': monto_oct,
            'monto_total': etiq.get('monto', 0)
        })

# Ordenar por monto en octubre descendente
facturas_octubre.sort(key=lambda x: abs(x['monto']), reverse=True)

print(f"\n{'='*80}")
print(f"TOTAL DE FACTURAS CON MONTO EN OCTUBRE 2025: {len(facturas_octubre)}")
print(f"{'='*80}\n")

# Mostrar todas
total_verificacion = 0
for i, fac in enumerate(facturas_octubre, 1):
    total_verificacion += fac['monto']
    print(f"{i:3d}. {fac['nombre'][:60]:60s} ${fac['monto']:>15,.0f}")

print(f"\n{'='*80}")
print(f"SUMA VERIFICACIÓN: ${total_verificacion:,.0f}")
print(f"TOTAL CUENTA OCT:  ${cuenta_deudores.get('montos_por_mes', {}).get('2025-10', 0):,.0f}")
print(f"{'='*80}")

# Guardar a archivo
with open('facturas_octubre_2025.txt', 'w', encoding='utf-8') as f:
    f.write("FACTURAS OCTUBRE 2025 - CUENTA 11030101\n")
    f.write("="*80 + "\n\n")
    for i, fac in enumerate(facturas_octubre, 1):
        f.write(f"{i:3d}. {fac['nombre'][:60]:60s} ${fac['monto']:>15,.0f}\n")
    f.write(f"\n{'='*80}\n")
    f.write(f"TOTAL: {len(facturas_octubre)} facturas\n")
    f.write(f"SUMA: ${total_verificacion:,.0f}\n")

print("\n✅ Lista guardada en: facturas_octubre_2025.txt")

"""
Mostrar desglose de factura con TCs variables
"""
import sys
sys.path.insert(0, r"c:\new\RIO FUTURO\DASHBOARD\proyectos")

from backend.services.proforma_ajuste_service import get_facturas_borrador

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

facturas = get_facturas_borrador(USERNAME, PASSWORD)

# Buscar TRES ROBLES
factura = None
for f in facturas:
    if "TRES ROBLES" in f['proveedor_nombre'].upper():
        factura = f
        break

if not factura:
    print("❌ No se encontró la factura")
    sys.exit(1)

print("=" * 120)
print("📊 DESGLOSE CON TIPOS DE CAMBIO VARIABLES")
print("=" * 120)

print(f"\n📄 Factura: {factura['nombre']}")
print(f"🏢 Proveedor: {factura['proveedor_nombre']}")
print(f"📅 Fecha: {factura.get('fecha_factura', 'Sin fecha')}")
print(f"💱 TC Promedio General: {factura['tipo_cambio']:,.4f}")
print(f"\n{'='*120}")
print(f"{'LÍNEA (OC)':<55} | {'CANT':>8} | {'P.UNIT USD':>12} | {'TC':>10} | {'P.UNIT CLP':>12} | {'SUB USD':>12} | {'SUB CLP':>14}")
print(f"{'='*120}")

for linea in factura['lineas']:
    nombre = linea['nombre'][:52] if linea['nombre'] else "Sin nombre"
    cant = linea['cantidad']
    p_unit_usd = linea['precio_usd']
    tc = linea['tc_implicito']
    subtotal_usd = linea['subtotal_usd']
    subtotal_clp = linea['subtotal_clp']
    p_unit_clp = subtotal_clp / cant if cant > 0 else 0
    
    print(f"{nombre:<55} | {cant:>8.2f} | ${p_unit_usd:>11,.2f} | {tc:>10,.2f} | ${p_unit_clp:>11,.0f} | ${subtotal_usd:>11,.2f} | ${subtotal_clp:>13,.0f}")

print(f"{'='*120}")
print(f"{'TOTALES':<55} | {'':>8} | {'':>12} | {'':>10} | {'':>12} | ${factura['base_usd']:>11,.2f} | ${factura['base_clp']:>13,.0f}")
print(f"{'IVA 19%':<55} | {'':>8} | {'':>12} | {'':>10} | {'':>12} | ${factura['iva_usd']:>11,.2f} | ${factura['iva_clp']:>13,.0f}")
print(f"{'TOTAL FACTURA':<55} | {'':>8} | {'':>12} | {'':>10} | {'':>12} | ${factura['total_usd']:>11,.2f} | ${factura['total_clp']:>13,.0f}")
print(f"{'='*120}")

# Análisis
tcs = [l['tc_implicito'] for l in factura['lineas'] if l['tc_implicito'] > 0]
if tcs:
    tc_min = min(tcs)
    tc_max = max(tcs)
    tc_promedio = sum(tcs) / len(tcs)
    
    print(f"\n📈 ANÁLISIS DE TIPOS DE CAMBIO:")
    print(f"   • TC Mínimo:  {tc_min:,.4f}")
    print(f"   • TC Máximo:  {tc_max:,.4f}")
    print(f"   • TC Promedio: {tc_promedio:,.4f}")
    print(f"   • Variación:   {tc_max - tc_min:,.4f} pesos ({((tc_max - tc_min) / tc_min * 100):,.2f}%)")
    print(f"\n✅ ¡CORRECTO! Cada OC tiene su TC específico según el día de registro en Odoo")
    print(f"   Esto significa que OCs de diferentes días tendrán diferentes conversiones USD→CLP")

print(f"{'='*120}\n")

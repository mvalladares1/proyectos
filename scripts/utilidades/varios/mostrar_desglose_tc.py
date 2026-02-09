"""
Mostrar desglose de TCs por línea de la factura FAC 000001
"""
import sys
sys.path.insert(0, r"c:\new\RIO FUTURO\DASHBOARD\proyectos")

from backend.services.proforma_ajuste_service import get_facturas_borrador

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 100)
print("📊 DESGLOSE DE TIPO DE CAMBIO POR LÍNEA - FAC 000001")
print("=" * 100)

# Obtener factura
facturas = get_facturas_borrador(USERNAME, PASSWORD)
factura = None

for f in facturas:
    if f['nombre'] == 'FAC 000001':
        factura = f
        break

if not factura:
    print("❌ No se encontró la factura FAC 000001")
    sys.exit(1)

print(f"\n📄 Factura: {factura['nombre']}")
print(f"🏢 Proveedor: {factura['proveedor_nombre']}")
print(f"📅 Fecha: {factura.get('fecha_factura', 'Sin fecha')}")
print(f"💱 TC Promedio General: {factura['tipo_cambio']:,.4f}")
print(f"\n{'='*100}")
print(f"{'LÍNEA':<50} | {'CANT':>8} | {'P.UNIT USD':>12} | {'TC':>10} | {'P.UNIT CLP':>12} | {'SUB USD':>12} | {'SUB CLP':>14}")
print(f"{'='*100}")

for i, linea in enumerate(factura['lineas'], 1):
    nombre = linea['nombre'][:47] if linea['nombre'] else "Sin nombre"
    cant = linea['cantidad']
    p_unit_usd = linea['precio_usd']
    tc = linea['tc_implicito']
    subtotal_usd = linea['subtotal_usd']
    subtotal_clp = linea['subtotal_clp']
    p_unit_clp = subtotal_clp / cant if cant > 0 else 0
    
    print(f"{nombre:<50} | {cant:>8.2f} | ${p_unit_usd:>11,.2f} | {tc:>10,.2f} | ${p_unit_clp:>11,.0f} | ${subtotal_usd:>11,.2f} | ${subtotal_clp:>13,.0f}")

print(f"{'='*100}")
print(f"{'TOTALES':<50} | {'':>8} | {'':>12} | {'':>10} | {'':>12} | ${factura['base_usd']:>11,.2f} | ${factura['base_clp']:>13,.0f}")
print(f"{'IVA 19%':<50} | {'':>8} | {'':>12} | {'':>10} | {'':>12} | ${factura['iva_usd']:>11,.2f} | ${factura['iva_clp']:>13,.0f}")
print(f"{'TOTAL FACTURA':<50} | {'':>8} | {'':>12} | {'':>10} | {'':>12} | ${factura['total_usd']:>11,.2f} | ${factura['total_clp']:>13,.0f}")
print(f"{'='*100}")

# Análisis de variación de TCs
tcs = [l['tc_implicito'] for l in factura['lineas']]
tc_min = min(tcs)
tc_max = max(tcs)
tc_promedio = sum(tcs) / len(tcs)

print(f"\n📈 ANÁLISIS DE TIPOS DE CAMBIO:")
print(f"   • TC Mínimo:  {tc_min:,.4f}")
print(f"   • TC Máximo:  {tc_max:,.4f}")
print(f"   • TC Promedio: {tc_promedio:,.4f}")
print(f"   • Variación:   {tc_max - tc_min:,.4f} ({((tc_max - tc_min) / tc_min * 100):,.2f}%)")

print("\n✅ Cada línea (OC) tiene su propio TC según el día que fue registrada en Odoo")
print(f"{'='*100}\n")

"""
Buscar facturas con múltiples TCs diferentes
"""
import sys
sys.path.insert(0, r"c:\new\RIO FUTURO\DASHBOARD\proyectos")

from backend.services.proforma_ajuste_service import get_facturas_borrador

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("🔍 Buscando facturas con TCs variables...\n")

facturas = get_facturas_borrador(USERNAME, PASSWORD)

facturas_con_tc_variable = []

for f in facturas[:20]:  # Revisar primeras 20
    tcs = [l['tc_implicito'] for l in f['lineas']]
    tc_min = min(tcs) if tcs else 0
    tc_max = max(tcs) if tcs else 0
    variacion = tc_max - tc_min
    
    if variacion > 1:  # Más de 1 peso de diferencia
        facturas_con_tc_variable.append({
            'nombre': f['nombre'],
            'proveedor': f['proveedor_nombre'],
            'lineas': len(f['lineas']),
            'tc_min': tc_min,
            'tc_max': tc_max,
            'variacion': variacion,
            'variacion_pct': (variacion / tc_min * 100) if tc_min > 0 else 0
        })

if facturas_con_tc_variable:
    print(f"✅ Encontradas {len(facturas_con_tc_variable)} facturas con TCs variables:\n")
    print(f"{'FACTURA':<15} | {'PROVEEDOR':<30} | {'LÍNEAS':>6} | {'TC MIN':>10} | {'TC MAX':>10} | {'VARIACIÓN':>12}")
    print("="*100)
    
    for f in facturas_con_tc_variable:
        print(f"{f['nombre']:<15} | {f['proveedor'][:30]:<30} | {f['lineas']:>6} | {f['tc_min']:>10.2f} | {f['tc_max']:>10.2f} | {f['variacion']:>10.2f} ({f['variacion_pct']:.2f}%)")
else:
    print("⚠️ No se encontraron facturas con TCs variables en las primeras 20")
    print("\nMostrando todas las facturas disponibles:")
    print(f"{'FACTURA':<15} | {'PROVEEDOR':<30} | {'LÍNEAS':>6} | {'TC':>10}")
    print("="*80)
    for f in facturas[:10]:
        print(f"{f['nombre']:<15} | {f['proveedor_nombre'][:30]:<30} | {f['num_lineas']:>6} | {f['tipo_cambio']:>10.2f}")

"""
Test COMPLETO del servicio actualizado con filtros
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar el servicio directamente
from backend.services.analisis_produccion_service import AnalisisProduccionService
from shared.odoo_client import OdooClient

print("="*140)
print("TEST: SERVICIO COMPLETO DE PRODUCCIÓN CON FILTROS")
print("="*140)

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")
servicio = AnalisisProduccionService(odoo)

# Analizar últimos 3 meses
resultado = servicio.get_analisis_produccion(
    fecha_desde="2025-11-01",
    fecha_hasta="2026-01-31"
)

resumen = resultado['resumen']
print(f"\n📊 RESUMEN GENERAL:")
print(f"{'='*140}")
print(f"   Órdenes analizadas: {resumen['ordenes_total']}")
print(f"   Consumo total MP (sin insumos): {resumen['kg_consumido']:,.2f} kg")
print(f"   Producción total PT (sin mermas): {resumen['kg_producido']:,.2f} kg")
print(f"   Merma total: {resumen['merma_kg']:,.2f} kg")
print(f"   Rendimiento general: {resumen['rendimiento_pct']:.1f}%")

if 70 <= resumen['rendimiento_pct'] <= 100:
    print(f"   ✅ RENDIMIENTO LÓGICO (70-100%)")
else:
    print(f"   ⚠️ RENDIMIENTO FUERA DE RANGO ESPERADO")

# Mostrar por tipo de fruta
print(f"\n📦 POR TIPO DE FRUTA:")
print(f"{'='*140}")
print(f"{'TIPO FRUTA':<30} {'CONSUMO (kg)':>15} {'PRODUCCIÓN (kg)':>18} {'RENDIMIENTO %':>15} {'STATUS':>10}")
print(f"{'-'*140}")

por_tipo = resultado['rendimientos_por_tipo']
for tipo_data in por_tipo:
    tipo = tipo_data['tipo_fruta']
    rend = tipo_data['rendimiento_pct']
    status = '✅' if 70 <= rend <= 100 else '⚠️'
    print(f"{tipo:<30} {tipo_data['kg_consumido']:>15,.2f} {tipo_data['kg_producido']:>18,.2f} {rend:>14.1f}% {status:>10}")

# Mostrar detalle de órdenes (primeras 10)
print(f"\n📋 DETALLE DE ÓRDENES (primeras 10):")
print(f"{'='*140}")
print(f"{'FECHA':<12} {'ORDEN':<25} {'TIPO':<15} {'CONSUMO':>12} {'PRODUCCIÓN':>12} {'RENDIMIENTO':>12}")
print(f"{'-'*140}")

detalle = resultado['detalle_ordenes'][:10]
for orden in detalle:
    fecha = orden['fecha'][:10] if orden['fecha'] else 'N/A'
    nombre = orden['orden'][:25]
    tipo = orden['tipo_fruta'][:15]
    
    print(f"{fecha:<12} {nombre:<25} {tipo:<15} {orden['kg_consumido']:>11.2f} {orden['kg_producido']:>12.2f} {orden['rendimiento_pct']:>11.1f}%")

print(f"\n{'='*140}")
print(f"FIN DEL TEST")
print(f"{'='*140}")

"""
Script de debug rápido para validar los cambios en 1.1.1 y 1.2.1
"""
import requests
import json
import sys

API_URL = "http://167.114.114.51:8002"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("VERIFICACIÓN DE FLUJO DE CAJA - CAMBIOS EN 1.1.1 Y 1.2.1")
print("=" * 70)

try:
    resp = requests.get(
        f"{API_URL}/api/v1/flujo-caja/mensual",
        params={
            "fecha_inicio": "2024-01-01",
            "fecha_fin": "2026-12-31",
            "username": USERNAME,
            "password": PASSWORD
        },
        timeout=120
    )
    resp.raise_for_status()
    data = resp.json()
except Exception as e:
    print(f"Error en API: {e}")
    sys.exit(1)

# Buscar conceptos
conceptos = data.get('actividades', {}).get('OPERACION', {}).get('conceptos', [])

print("\n" + "=" * 70)
print("1.1.1 - COBROS PROCEDENTES DE VENTAS")
print("=" * 70)

concepto_111 = next((c for c in conceptos if c.get('id') == '1.1.1'), None)
if concepto_111:
    print(f"Total: ${concepto_111.get('total', 0):,.0f}")
    print(f"Cuentas (estados de pago):")
    for cuenta in concepto_111.get('cuentas', []):
        nombre = cuenta.get('nombre', '')[:60]
        monto = cuenta.get('monto', 0)
        print(f"  - {nombre}: ${monto:,.0f}")
    
    # Verificar que NO hay "Facturas Revertidas"
    tiene_revertidas = any('revertidas' in c.get('nombre', '').lower() for c in concepto_111.get('cuentas', []))
    print(f"\n✅ No tiene categoría 'Facturas Revertidas' separada: {not tiene_revertidas}")
else:
    print("❌ Concepto 1.1.1 no encontrado")

print("\n" + "=" * 70)
print("1.2.1 - PAGOS A PROVEEDORES")
print("=" * 70)

concepto_121 = next((c for c in conceptos if c.get('id') == '1.2.1'), None)
if concepto_121:
    print(f"Total: ${concepto_121.get('total', 0):,.0f}")
    print(f"Cuentas (estados/categorías):")
    for cuenta in concepto_121.get('cuentas', []):
        nombre = cuenta.get('nombre', '')[:60]
        monto = cuenta.get('monto', 0)
        print(f"  - {nombre}: ${monto:,.0f}")
    
    # Verificar que tiene ambas categorías proyectadas
    codigos = [c.get('codigo', '') for c in concepto_121.get('cuentas', [])]
    tiene_compras = 'proyectadas_compras' in codigos
    tiene_contabilidad = 'proyectadas_contabilidad' in codigos
    
    print(f"\n✅ Tiene 'Facturas Proyectadas (Modulo Compras)': {tiene_compras}")
    print(f"✅ Tiene 'Facturas Proyectadas (Modulo Contabilidad)': {tiene_contabilidad}")
    
    # Mostrar detalles de proyectadas contabilidad
    cuenta_contab = next((c for c in concepto_121.get('cuentas', []) if c.get('codigo') == 'proyectadas_contabilidad'), None)
    if cuenta_contab:
        print(f"\n   Proyectadas Contabilidad - Total: ${cuenta_contab.get('monto', 0):,.0f}")
        for etiq in cuenta_contab.get('etiquetas', [])[:5]:
            print(f"      - {etiq.get('nombre', '')[:50]}: ${etiq.get('monto', 0):,.0f}")
else:
    print("❌ Concepto 1.2.1 no encontrado")

print("\n✅ Verificación completada")

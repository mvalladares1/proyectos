# -*- coding: utf-8 -*-
"""
Script de prueba para la nueva lógica de calcular_pagos_proveedores
"""
import sys
import os
import io

# Configurar salida UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from shared.odoo_client import OdooClient
from backend.services.flujo_caja.real_proyectado import RealProyectadoCalculator
import json

# Credenciales
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

odoo = OdooClient(username=USERNAME, password=PASSWORD)
calculator = RealProyectadoCalculator(odoo)

print("\n" + "="*100)
print("PRUEBA: Nueva Lógica de 1.2.1 - Pagos a Proveedores (basada en matching_number)")
print("="*100 + "\n")

# Probar con período de prueba
fecha_inicio = '2026-01-01'
fecha_fin = '2026-02-15'

# Probar vista MENSUAL
print("[TEST 1] Vista MENSUAL")
print("-" * 100)
meses_lista = ['2026-01', '2026-02', '2026-03']

resultado = calculator.calcular_pagos_proveedores(fecha_inicio, fecha_fin, meses_lista)

print(f"\nRESULTADO GENERAL:")
print(f"  Total REAL: ${resultado['real']:,.2f}")
print(f"  Total PROYECTADO: ${resultado['proyectado']:,.2f}")
print(f"  Total General: ${resultado['total']:,.2f}")
print(f"  Facturas procesadas: {resultado['facturas_count']}")

print(f"\nDISTRIBUCIÓN POR MES:")
for mes in meses_lista:
    real = resultado['real_por_mes'].get(mes, 0)
    proy = resultado['proyectado_por_mes'].get(mes, 0)
    total = resultado['montos_por_mes'].get(mes, 0)
    print(f"  {mes}: REAL ${real:,.2f} | PROY ${proy:,.2f} | TOTAL ${total:,.2f}")

print(f"\nESTRUCTURA JERÁRQUICA:")
for i, cuenta in enumerate(resultado['cuentas'], 1):
    print(f"\n  [{i}] {cuenta['nombre']}")
    print(f"      Total: ${cuenta['monto']:,.2f} | REAL: ${cuenta['real']:,.2f} | PROY: ${cuenta['proyectado']:,.2f}")
    print(f"      Proveedores: {len(cuenta['etiquetas'])}")
    
    # Mostrar top 3 proveedores
    for j, prov in enumerate(sorted(cuenta['etiquetas'], key=lambda x: abs(x['monto']), reverse=True)[:3], 1):
        print(f"        {j}. {prov['nombre']}: ${prov['monto']:,.2f} (R:${prov['real']:,.2f} P:${prov['proyectado']:,.2f})")

print("\n" + "="*100)

# Probar vista SEMANAL
print("\n[TEST 2] Vista SEMANAL")
print("-" * 100)
semanas_lista = ['2026-W01', '2026-W02', '2026-W03', '2026-W04', '2026-W05', '2026-W06', '2026-W07']

resultado_semanal = calculator.calcular_pagos_proveedores(fecha_inicio, fecha_fin, semanas_lista)

print(f"\nRESULTADO GENERAL:")
print(f"  Total REAL: ${resultado_semanal['real']:,.2f}")
print(f"  Total PROYECTADO: ${resultado_semanal['proyectado']:,.2f}")
print(f"  Facturas procesadas: {resultado_semanal['facturas_count']}")

print(f"\nDISTRIBUCIÓN POR SEMANA:")
for semana in semanas_lista:
    real = resultado_semanal['real_por_mes'].get(semana, 0)
    proy = resultado_semanal['proyectado_por_mes'].get(semana, 0)
    total = resultado_semanal['montos_por_mes'].get(semana, 0)
    if total != 0:
        print(f"  {semana}: REAL ${real:,.2f} | PROY ${proy:,.2f} | TOTAL ${total:,.2f}")

print(f"\nESTRUCTURA POR ESTADO:")
for cuenta in resultado_semanal['cuentas']:
    print(f"  {cuenta['nombre']}: ${cuenta['monto']:,.2f} ({len(cuenta['etiquetas'])} proveedores)")

print("\n" + "="*100)
print("PRUEBA COMPLETADA")
print("="*100 + "\n")

# Guardar resultado JSON para inspección
with open('test_resultado_121.json', 'w', encoding='utf-8') as f:
    json.dump(resultado, f, indent=2, ensure_ascii=False)

print("[OK] Resultado guardado en: test_resultado_121.json\n")

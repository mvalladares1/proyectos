#!/usr/bin/env python3
"""Debug: OCs en Módulo Compras para S10 - NEWEN"""
import json

with open('/tmp/flujo_semanal.json') as f:
    data = json.load(f)

# Buscar en cuenta[3] = Proyectadas Compras
concepto = data['actividades']['OPERACION']['conceptos'][1]
cuenta_compras = concepto['cuentas'][3]

print("CUENTA:", cuenta_compras.get('nombre'))
print("="*80)

# Listar TODOS los proveedores en esta cuenta con sus montos
print("\nTODOS LOS PROVEEDORES EN PROYECTADAS COMPRAS:")

for etiqueta in cuenta_compras.get('etiquetas', []):
    print(f"\n  {etiqueta.get('nombre')}:")
    for sub in etiqueta.get('sub_etiquetas', []):
        montos = sub.get('montos_por_mes', {})
        total = sum(montos.values())
        if total != 0:
            print(f"    {sub.get('nombre')[:50]:50} | Total: {total:>15,.0f}")
            # Mostrar desglose por semana
            for sem in sorted(montos.keys()):
                if montos[sem] != 0:
                    print(f"      {sem}: {montos[sem]:>15,.0f}")

# Totales de S10
print("\n" + "="*80)
print("PROVEEDORES CON VALORES EN W10:")
for etiqueta in cuenta_compras.get('etiquetas', []):
    for sub in etiqueta.get('sub_etiquetas', []):
        montos = sub.get('montos_por_mes', {})
        w10 = montos.get('2026-W10', 0) 
        if w10 != 0:
            print(f"  {sub.get('nombre')}: {w10:,.0f}")

# Total de la cuenta en W10
print("\n" + "="*80)
montos_cuenta = cuenta_compras.get('montos_por_mes', {})
print(f"TOTAL CUENTA COMPRAS EN W10: {montos_cuenta.get('2026-W10', 0):,.0f}")

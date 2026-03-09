#!/usr/bin/env python3
import json

with open('/tmp/flujo_semanal.json') as f:
    data = json.load(f)

# Mostrar estructura del concepto[1] (pagos a proveedores)
concepto = data['actividades']['OPERACION']['conceptos'][1]
print('CONCEPTO:', concepto.get('nombre'))
print()
print('CUENTAS:')
for i, cuenta in enumerate(concepto.get('cuentas', [])):
    print(f"  [{i}] {cuenta.get('codigo')} - {cuenta.get('nombre')}")
    
    # Buscar NEWEN en esta cuenta
    for j, etiqueta in enumerate(cuenta.get('etiquetas', [])):
        for k, sub in enumerate(etiqueta.get('sub_etiquetas', [])):
            if 'NEWEN' in str(sub.get('nombre', '')).upper() and 'ARAUCANIA' in str(sub.get('nombre', '')).upper():
                montos = sub.get('montos_por_mes', {})
                total = sum(montos.values())
                print(f"       -> NEWEN: etiqueta[{j}] ({etiqueta.get('nombre')}).sub[{k}]")
                print(f"          Montos: {montos}")
                print(f"          Total: {total:,.0f}")

#!/usr/bin/env python3
"""
Debug: Verificar mismatch entre categoría "Proveedor" y sus proveedores individuales
en Facturas No Pagadas, S1 Enero 2026
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.odoo_client import OdooClient
from backend.services.flujo_caja.real_proyectado import RealProyectadoCalculator
from collections import defaultdict

def fmt(v):
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.0f}".replace(",", ".")

def main():
    odoo = OdooClient()
    calc = RealProyectadoCalculator(odoo)
    
    # Vista SEMANAL como el usuario la está usando
    semanas = ["2026-W01", "2026-W02", "2026-W03", "2026-W04", "2026-W05", "2026-W06", "2026-W07", "2026-W08"]
    
    resultado = calc.calcular_pagos_proveedores("2026-01-01", "2026-02-28", semanas)
    
    cuentas = resultado.get('cuentas', [])
    
    for cuenta in cuentas:
        nombre = cuenta.get('nombre', '')
        etiquetas = cuenta.get('etiquetas', [])
        
        for etiqueta in etiquetas:
            et_nombre = etiqueta.get('nombre', '')
            if 'Proveedor' in et_nombre and 'Insumos' not in et_nombre:
                # Encontramos la categoría "Proveedor" 
                et_monto = etiqueta.get('monto', 0)
                et_montos_mes = etiqueta.get('montos_por_mes', {})
                sub_etiquetas = etiqueta.get('sub_etiquetas', [])
                
                print(f"\n{'='*80}")
                print(f"Estado: {nombre}")
                print(f"Categoría: {et_nombre}")
                print(f"Monto total categoría: {fmt(et_monto)}")
                print(f"Sub_etiquetas (proveedores) mostrados: {len(sub_etiquetas)}")
                print(f"{'='*80}")
                
                # Montos por semana de la categoría
                print("\nMontos por semana de la CATEGORÍA:")
                for semana in semanas:
                    m = et_montos_mes.get(semana, 0)
                    if m != 0:
                        print(f"  {semana}: {fmt(m)}")
                
                # Suma de sub_etiquetas
                suma_sub = defaultdict(float)
                suma_total_sub = 0
                print(f"\nProveedores ({len(sub_etiquetas)}):")
                for sub in sub_etiquetas:
                    sub_nombre = sub.get('nombre', '')
                    sub_monto = sub.get('monto', 0)
                    sub_montos = sub.get('montos_por_mes', {})
                    suma_total_sub += sub_monto
                    
                    tiene_monto = any(sub_montos.get(s, 0) != 0 for s in semanas)
                    if tiene_monto or sub_monto != 0:
                        print(f"  {sub_nombre}: total={fmt(sub_monto)}")
                        for semana in semanas:
                            m = sub_montos.get(semana, 0)
                            if m != 0:
                                print(f"    {semana}: {fmt(m)}")
                                suma_sub[semana] += m
                
                print(f"\n--- COMPARACIÓN ---")
                print(f"Total categoría: {fmt(et_monto)}")
                print(f"Suma sub_etiquetas: {fmt(suma_total_sub)}")
                print(f"Diferencia: {fmt(et_monto - suma_total_sub)}")
                
                for semana in semanas:
                    cat_sem = et_montos_mes.get(semana, 0)
                    sub_sem = suma_sub.get(semana, 0)
                    if cat_sem != 0 or sub_sem != 0:
                        diff = cat_sem - sub_sem
                        flag = " ⚠️ MISMATCH!" if abs(diff) > 1 else " ✅"
                        print(f"  {semana}: cat={fmt(cat_sem)} subs={fmt(sub_sem)} diff={fmt(diff)}{flag}")

if __name__ == "__main__":
    main()

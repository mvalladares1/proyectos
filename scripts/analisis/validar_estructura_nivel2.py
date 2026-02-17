"""
Script para validar la nueva estructura sin REAL/PROYECTADO en nivel 2.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.flujo_caja.real_proyectado import RealProyectadoCalculator
from shared.odoo_client import OdooClient
import json

def format_money(value):
    """Formatea un número como moneda chilena."""
    if value < 0:
        return f"-${abs(value):,.0f}".replace(',', '.')
    return f"${value:,.0f}".replace(',', '.')

def main():
    print("\n" + "="*80)
    print("VALIDACIÓN: ESTRUCTURA SIN REAL/PROYECTADO EN NIVEL 2")
    print("="*80 + "\n")
    
    odoo = OdooClient()
    service = RealProyectadoCalculator(odoo)
    resultado = service.calcular_pagos_proveedores('2026-01-01', '2026-02-28')
    
    print("TOTALES GENERALES:")
    print(f"  Facturas procesadas: {resultado.get('facturas_count', 0)}")
    print(f"  Categorías: {len(resultado.get('cuentas', []))}")
    print()
    
    print("ESTRUCTURA DE CATEGORÍAS (NIVEL 2):")
    print("="*80)
    
    for i, cuenta in enumerate(resultado.get('cuentas', []), 1):
        print(f"\n{i}. {cuenta.get('nombre', '')}")
        print(f"   Código: {cuenta.get('codigo', '')}")
        print(f"   Monto: {format_money(cuenta.get('monto', 0))}")
        print(f"   Proveedores: {len(cuenta.get('etiquetas', []))}")
        
        # Verificar qué campos tiene
        print(f"   Campos disponibles: {', '.join(cuenta.keys())}")
        
        # Verificar si tiene real_por_mes o proyectado_por_mes
        if 'real_por_mes' in cuenta:
            print("   ❌ ERROR: Tiene 'real_por_mes' (debería estar eliminado)")
        else:
            print("   ✅ OK: No tiene 'real_por_mes'")
        
        if 'proyectado_por_mes' in cuenta:
            print("   ❌ ERROR: Tiene 'proyectado_por_mes' (debería estar eliminado)")
        else:
            print("   ✅ OK: No tiene 'proyectado_por_mes'")
        
        if 'real' in cuenta:
            print(f"   ⚠️  ADVERTENCIA: Tiene 'real' = {format_money(cuenta.get('real', 0))}")
        
        if 'proyectado' in cuenta:
            print(f"   ⚠️  ADVERTENCIA: Tiene 'proyectado' = {format_money(cuenta.get('proyectado', 0))}")
        
        # Mostrar ejemplo de proveedor
        if cuenta.get('etiquetas'):
            prov = cuenta['etiquetas'][0]
            print(f"\n   Ejemplo proveedor nivel 3:")
            print(f"     Nombre: {prov.get('nombre', '')}")
            print(f"     Monto: {format_money(prov.get('monto', 0))}")
            print(f"     Campos: {', '.join(prov.keys())}")
            
            if 'real_por_mes' in prov:
                print("     ❌ ERROR: Proveedor tiene 'real_por_mes'")
            else:
                print("     ✅ OK: Proveedor no tiene 'real_por_mes'")
    
    # Validar totales
    print("\n" + "="*80)
    print("VALIDACIÓN DE TOTALES:")
    print("="*80)
    
    suma_montos = sum(c.get('monto', 0) for c in resultado.get('cuentas', []))
    print(f"Suma de montos categorías: {format_money(suma_montos)}")
    print(f"Total reportado:          {format_money(resultado.get('total', 0))}")
    
    if abs(suma_montos - resultado.get('total', 0)) < 1:
        print("✅ Los montos cuadran")
    else:
        print("❌ Hay discrepancia en los montos")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()

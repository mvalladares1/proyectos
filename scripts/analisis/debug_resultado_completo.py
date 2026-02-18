"""
Script para ver exactamente qué está devolviendo calcular_pagos_proveedores.
Imprime la estructura completa.
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
    print("DEBUG: ESTRUCTURA COMPLETA DEL RESULTADO")
    print("="*80 + "\n")
    
    odoo = OdooClient()
    service = RealProyectadoCalculator(odoo)
    
    fecha_inicio = '2026-01-01'
    fecha_fin = '2026-02-28'
    
    resultado = service.calcular_pagos_proveedores(fecha_inicio, fecha_fin)
    
    print("TOTALES GENERALES:")
    print(f"  real: {format_money(resultado['real'])}")
    print(f"  proyectado: {format_money(resultado['proyectado'])}")
    print(f"  total: {format_money(resultado.get('total', 0))}")
    print(f"  facturas_count: {resultado.get('facturas_count', 0)}")
    print(f"  cuentas: {len(resultado.get('cuentas', []))}")
    print()
    
    print("CUENTAS (CATEGORÍAS):")
    print("="*80)
    
    for i, cuenta in enumerate(resultado.get('cuentas', []), 1):
        print(f"\n{i}. {cuenta.get('codigo', 'sin_codigo')}")
        print(f"   nombre: {cuenta.get('nombre', '')}")
        print(f"   real: {format_money(cuenta.get('real', 0))}")
        print(f"   proyectado: {format_money(cuenta.get('proyectado', 0))}")
        print(f"   monto: {format_money(cuenta.get('monto', 0))}")
        print(f"   etiquetas (proveedores): {len(cuenta.get('etiquetas', []))}")
        print(f"   orden: {cuenta.get('orden', 'N/A')}")
        
        # Mostrar top 3 proveedores
        etiquetas = cuenta.get('etiquetas', [])
        if etiquetas:
            print(f"\n   Top 3 proveedores por monto:")
            for j, prov in enumerate(etiquetas[:3], 1):
                print(f"     {j}. {prov.get('nombre', '')[:40]:40} | REAL: {format_money(prov.get('real', 0)):>20} | PROY: {format_money(prov.get('proyectado', 0)):>20}")
    
    print("\n" + "="*80 + "\n")
    
    # Guardar JSON completo para inspección
    with open('debug_resultado_121.json', 'w', encoding='utf-8') as f:
        # Convertir defaultdicts a dicts regulares para JSON
        resultado_limpio = {
            'real': resultado['real'],
            'proyectado': resultado['proyectado'],
            'total': resultado.get('total', 0),
            'facturas_count': resultado.get('facturas_count', 0),
            'cuentas': resultado.get('cuentas', [])
        }
        json.dump(resultado_limpio, f, indent=2, ensure_ascii=False)
    
    print("✅ JSON completo guardado en: debug_resultado_121.json\n")

if __name__ == "__main__":
    main()

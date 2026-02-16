"""
Script para probar la nueva estructura con categorías de contacto en nivel 3.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.flujo_caja.real_proyectado import RealProyectadoCalculator
from shared.odoo_client import OdooClient

def format_money(value):
    """Formatea un número como moneda chilena."""
    if value < 0:
        return f"-${abs(value):,.0f}".replace(',', '.')
    return f"${value:,.0f}".replace(',', '.')

def main():
    print("\n" + "="*100)
    print("PRUEBA: ESTRUCTURA CON CATEGORÍAS DE CONTACTO EN NIVEL 3")
    print("="*100 + "\n")
    
    odoo = OdooClient()
    service = RealProyectadoCalculator(odoo)
    
    try:
        resultado = service.calcular_pagos_proveedores('2026-01-01', '2026-02-28')
        
        print("TOTALES GENERALES:")
        print(f"  Total: {format_money(resultado.get('total', 0))}")
        print(f"  Categorías estado: {len(resultado.get('cuentas', []))}")
        print()
        
        # Verificar estructura
        print("ESTRUCTURA JERÁRQUICA:")
        print("="*100)
        
        for i, estado in enumerate(resultado.get('cuentas', []), 1):
            print(f"\nNivel 2 - {i}. {estado.get('nombre', '')}")
            print(f"   Monto: {format_money(estado.get('monto', 0))}")
            print(f"   Categorías de contacto (Nivel 3): {len(estado.get('etiquetas', []))}")
            
            # Verificar que no tenga campos obsoletos
            if 'real' in estado:
                print("   ❌ ERROR: Tiene campo 'real'")
            if 'proyectado' in estado:
                print("   ❌ ERROR: Tiene campo 'proyectado'")
            
            # Mostrar algunas categorías
            categorias = estado.get('etiquetas', [])
            if categorias:
                print(f"\n   Top 5 categorías de contacto:")
                for j, categoria in enumerate(categorias[:5], 1):
                    cat_nombre = categoria.get('nombre', '')
                    cat_monto = categoria.get('monto', 0)
                    proveedores_count = len(categoria.get('etiquetas', []))
                    
                    print(f"   Nivel 3 - {j}. {cat_nombre[:40]:40} | Monto: {format_money(cat_monto):>20} | Proveedores: {proveedores_count}")
                    
                    # Mostrar algunos proveedores de esta categoría
                    proveedores = categoria.get('etiquetas', [])
                    if proveedores and j <= 2:  # Solo para las primeras 2 categorías
                        print(f"      Top 3 proveedores:")
                        for k, proveedor in enumerate(proveedores[:3], 1):
                            prov_nombre = proveedor.get('nombre', '')
                            prov_monto = proveedor.get('monto', 0)
                            print(f"      Nivel 4 - {k}. {prov_nombre[:35]:35} | Monto: {format_money(prov_monto):>20}")
        
        print("\n" + "="*100)
        print("VALIDACIÓN:")
        print("="*100)
        
        # Validar que la suma de estados = total
        suma_estados = sum(e.get('monto', 0) for e in resultado.get('cuentas', []))
        print(f"Suma estados:  {format_money(suma_estados)}")
        print(f"Total:         {format_money(resultado.get('total', 0))}")
        
        if abs(suma_estados - resultado.get('total', 0)) < 1:
            print("✅ Las sumas cuadran correctamente")
        else:
            print("❌ HAY DISCREPANCIA")
        
        print("\n" + "="*100 + "\n")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

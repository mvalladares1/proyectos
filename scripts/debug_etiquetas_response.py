"""
Script para debuggear las etiquetas que se están enviando al frontend
para la cuenta 82010102 en enero 2026
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
from backend.services.flujo_caja_service import FlujoCajaService
from datetime import datetime
import json

def main():
    print("="*80)
    print("DEBUG ETIQUETAS EN RESPUESTA DEL ENDPOINT")
    print("="*80)
    
    # Conectar a Odoo
    client = OdooClient(
        url="https://rio-futuro-master-11821236.dev.odoo.com",
        db="rio-futuro-master-11821236",
        username="mvalladares@riofuturo.cl",
        password="c0766224bec30cac071ffe43a858c9ccbd521ddd"
    )
    
    # Crear servicio de flujo de caja
    flujo_service = FlujoCajaService(client)
    
    # Parámetros de consulta (enero 2026)
    fecha_inicio = "2026-01-01"
    fecha_fin = "2026-01-31"
    tipo_periodo = "mensual"
    
    print(f"\n1. Obteniendo flujo de caja para período {fecha_inicio} a {fecha_fin}")
    print(f"   Tipo período: {tipo_periodo}")
    
    # Obtener el flujo completo
    resultado = flujo_service.get_flujo_mensualizado(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        tipo_periodo=tipo_periodo
    )
    
    print(f"\n2. Buscando cuenta 82010102 en la respuesta...")
    
    # Buscar en conceptos_por_actividad
    cuenta_encontrada = False
    for actividad_nombre, conceptos in resultado.get("conceptos_por_actividad", {}).items():
        for concepto in conceptos:
            if concepto.get("tipo") != "LINEA":
                continue
            
            # Buscar en cuentas
            for cuenta in concepto.get("cuentas", []):
                if cuenta.get("codigo") == "82010102":
                    cuenta_encontrada = True
                    print(f"\n   ✓ Cuenta encontrada en actividad: {actividad_nombre}")
                    print(f"   Concepto: {concepto.get('nombre')}")
                    print(f"   Código: {cuenta.get('codigo')}")
                    print(f"   Nombre: {cuenta.get('nombre')}")
                    print(f"   Monto: {cuenta.get('monto'):,.0f}")
                    print(f"   Cantidad movimientos: {cuenta.get('cantidad')}")
                    
                    etiquetas = cuenta.get("etiquetas", [])
                    print(f"\n   Total etiquetas: {len(etiquetas)}")
                    
                    if etiquetas:
                        print("\n   DETALLE DE ETIQUETAS:")
                        for i, etiq in enumerate(etiquetas, 1):
                            nombre = etiq.get("nombre", "")
                            monto = etiq.get("monto", 0)
                            montos_por_mes = etiq.get("montos_por_mes", {})
                            
                            print(f"\n   Etiqueta #{i}:")
                            print(f"     Nombre: '{nombre}'")
                            print(f"     Longitud nombre: {len(nombre)} caracteres")
                            print(f"     Nombre repr: {repr(nombre)}")
                            print(f"     Monto total: {monto:,.0f}")
                            print(f"     Montos por mes: {montos_por_mes}")
                            
                            # Verificar espacios
                            if nombre != nombre.strip():
                                print(f"     ⚠️ TIENE ESPACIOS AL INICIO/FIN (stripped: '{nombre.strip()}')")
                            
                            # Verificar caracteres invisibles
                            if any(ord(c) < 32 or ord(c) == 160 for c in nombre):
                                print(f"     ⚠️ TIENE CARACTERES INVISIBLES")
                                chars = [f"{c}({ord(c)})" for c in nombre]
                                print(f"     Caracteres: {chars}")
                    else:
                        print("   ⚠️ No hay etiquetas en la respuesta")
                    
                    # Mostrar JSON completo de la cuenta
                    print(f"\n3. JSON completo de la cuenta:")
                    print(json.dumps(cuenta, indent=2, ensure_ascii=False))
                    
                    break
            
            if cuenta_encontrada:
                break
        
        if cuenta_encontrada:
            break
    
    if not cuenta_encontrada:
        print("\n   ✗ Cuenta 82010102 NO encontrada en la respuesta")
        print("\n   Verificando todas las cuentas disponibles...")
        for actividad_nombre, conceptos in resultado.get("conceptos_por_actividad", {}).items():
            for concepto in conceptos:
                if concepto.get("tipo") != "LINEA":
                    continue
                for cuenta in concepto.get("cuentas", []):
                    codigo = cuenta.get("codigo")
                    if codigo and codigo.startswith("82"):
                        print(f"     - {codigo}: {cuenta.get('nombre')}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

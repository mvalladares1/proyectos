"""
Debug: Verificar qué devuelve el flujo de caja con estados de pago.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json

# Test via API (como lo hace el frontend)
print("=" * 100)
print("TEST VIA API (como lo ve el frontend)")
print("=" * 100)

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Probar el endpoint local
url = "http://localhost:8000/flujo-caja/mensual"
params = {
    "fecha_inicio": "2025-10-01",
    "fecha_fin": "2025-10-31",
    "username": USERNAME,
    "password": PASSWORD
}

try:
    resp = requests.get(url, params=params, timeout=120)
    if resp.status_code == 200:
        data = resp.json()
        
        # Buscar concepto 1.1.1
        actividades = data.get('actividades', {})
        op = actividades.get('OPERACION', {})
        
        for concepto in op.get('conceptos', []):
            if concepto.get('id') == '1.1.1':
                print(f"\n✅ Concepto 1.1.1: {concepto.get('nombre')}")
                print(f"   Total: ${concepto.get('total', 0):,.0f}")
                
                for cuenta in concepto.get('cuentas', []):
                    if cuenta.get('codigo') == '11030101':
                        print(f"\n📌 Cuenta: {cuenta.get('codigo')} - {cuenta.get('nombre')}")
                        print(f"   es_cuenta_cxc: {cuenta.get('es_cuenta_cxc', 'NO DEFINIDO')}")
                        
                        etiquetas = cuenta.get('etiquetas', [])
                        print(f"\n   📋 Etiquetas ({len(etiquetas)}):")
                        for et in etiquetas[:15]:
                            nombre = et.get('nombre', '?')
                            monto = et.get('monto', 0)
                            tiene_facturas = 'facturas' in et
                            num_facturas = len(et.get('facturas', [])) if tiene_facturas else 0
                            print(f"      - {nombre}: ${monto:,.0f} | Facturas: {num_facturas if tiene_facturas else 'N/A'}")
                        break
                break
    else:
        print(f"❌ Error API: {resp.status_code}")
        print(resp.text[:500])
except requests.exceptions.ConnectionError:
    print("❌ No se pudo conectar a localhost:8000")
    print("\nIntentando con servicio directo...")

# Test directo con el servicio
print("\n" + "=" * 100)
print("TEST DIRECTO CON FlujoCajaService")
print("=" * 100)

from backend.services.flujo_caja_service import FlujoCajaService

svc = FlujoCajaService(USERNAME, PASSWORD)
result = svc.get_flujo_mensualizado("2025-10-01", "2025-10-31")

# Buscar concepto 1.1.1
actividades = result.get('actividades', {})
op = actividades.get('OPERACION', {})

for concepto in op.get('conceptos', []):
    if concepto.get('id') == '1.1.1':
        print(f"\n✅ Concepto 1.1.1: {concepto.get('nombre')}")
        
        for cuenta in concepto.get('cuentas', []):
            if cuenta.get('codigo') == '11030101':
                print(f"\n📌 Cuenta: {cuenta.get('codigo')} - {cuenta.get('nombre')}")
                print(f"   es_cuenta_cxc: {cuenta.get('es_cuenta_cxc', 'NO DEFINIDO')}")
                
                etiquetas = cuenta.get('etiquetas', [])
                print(f"\n   📋 Etiquetas ({len(etiquetas)}):")
                
                estados_esperados = ['Facturas Pagadas', 'Facturas Parcialmente Pagadas', 
                                    'En Proceso de Pago', 'Facturas No Pagadas', 'Facturas Revertidas']
                
                for et in etiquetas:
                    nombre = et.get('nombre', '?')
                    monto = et.get('monto', 0)
                    tiene_facturas = 'facturas' in et
                    num_facturas = len(et.get('facturas', [])) if tiene_facturas else 0
                    
                    es_estado = nombre in estados_esperados
                    emoji = "✅" if es_estado else "❌"
                    
                    print(f"      {emoji} {nombre}: ${monto:,.0f} | Facturas: {num_facturas if tiene_facturas else 'N/A'}")
                
                # Verificar si tiene etiquetas de estado
                nombres_etiquetas = [e.get('nombre') for e in etiquetas]
                tiene_estados = any(e in estados_esperados for e in nombres_etiquetas)
                
                print(f"\n   🔍 ¿Tiene agrupación por estado de pago?: {'✅ SÍ' if tiene_estados else '❌ NO'}")
                
                if not tiene_estados:
                    print(f"\n   ⚠️ PROBLEMA: Las etiquetas son facturas individuales, no estados de pago!")
                    print(f"      Etiquetas encontradas: {nombres_etiquetas[:10]}")
                
                break
        break

print("\n" + "=" * 100)

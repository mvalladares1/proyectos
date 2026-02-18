"""
Test directo del endpoint con incluir_proyecciones=True
"""
import requests
import json

url = "http://167.114.114.51:8002/api/v1/flujo-caja/mensual"

params = {
    'fecha_inicio': '2026-01-01',
    'fecha_fin': '2026-09-30',
    'username': 'mvalladares@riofuturo.cl',
    'password': 'c0766224bec30cac071ffe43a858c9ccbd521ddd',
    'incluir_proyecciones': True
}

print("="*80)
print("TEST ENDPOINT: incluir_proyecciones=True")
print("="*80)
print(f"URL: {url}")
print(f"Params: {json.dumps({k: v if k != 'password' else '***' for k, v in params.items()}, indent=2)}")
print()

try:
    resp = requests.get(url, params=params, timeout=60)
    
    print(f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        
        # Buscar presupuestos proyectados en 1.1.1
        actividades = data.get('actividades', {})
        operacion = actividades.get('OPERACION', {})
        conceptos = operacion.get('conceptos', [])
        
        print("\n" + "="*80)
        print("RESULTADO: Buscando 1.1.1 - Cobros procedentes de ventas")
        print("="*80)
        
        concepto_111 = None
        for c in conceptos:
            if c.get('id') == '1.1.1':
                concepto_111 = c
                break
        
        if concepto_111:
            print(f"\n✅ Concepto 1.1.1 encontrado")
            print(f"Total: ${concepto_111.get('total', 0):,.0f}")
            
            cuentas = concepto_111.get('cuentas', [])
            print(f"Cuentas: {len(cuentas)}")
            
            for cuenta in cuentas:
                codigo = cuenta.get('codigo', '')
                nombre = cuenta.get('nombre', '')
                monto = cuenta.get('monto', 0)
                es_cxc = cuenta.get('es_cuenta_cxc', False)
                
                print(f"\n  Cuenta: {codigo} - {nombre}")
                print(f"  Monto: ${monto:,.0f}")
                print(f"  Es CxC: {es_cxc}")
                
                if es_cxc:
                    etiquetas = cuenta.get('etiquetas', [])
                    print(f"  Etiquetas: {len(etiquetas)}")
                    
                    for etiq in etiquetas:
                        etiq_nombre = etiq.get('nombre', '')
                        etiq_monto = etiq.get('monto', 0)
                        
                        if '🔮' in etiq_nombre or 'Proyect' in etiq_nombre:
                            print(f"    ✅✅✅ ENCONTRADO: {etiq_nombre} = ${etiq_monto:,.0f}")
                        else:
                            print(f"    - {etiq_nombre}: ${etiq_monto:,.0f}")
        else:
            print("❌ Concepto 1.1.1 NO encontrado")
            print(f"\nConceptos disponibles:")
            for c in conceptos[:10]:
                print(f"  - {c.get('id')}: {c.get('nombre')}")
    else:
        print(f"❌ Error: {resp.status_code}")
        print(resp.text[:500])
        
except Exception as e:
    print(f"❌ Exception: {e}")
    import traceback
    traceback.print_exc()

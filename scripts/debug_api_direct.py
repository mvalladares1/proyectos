"""Debug: Verificar respuesta directa del API semanal"""
import requests
import json

# Llamada directa al API semanal
url = 'http://localhost:8002/api/v1/flujo-caja/semanal'
params = {
    'fecha_inicio': '2025-01-01',
    'fecha_fin': '2025-03-31',
    'username': 'api_user',
    'password': 'rf2025api',
    'incluir_proyecciones': 'true'
}

try:
    resp = requests.get(url, params=params, timeout=120)
    if resp.status_code == 200:
        data = resp.json()
        print('MESES DISPONIBLES:', data.get('meses', [])[:10])
        
        # Buscar TRONADOR en CxC
        actividades = data.get('actividades', {})
        operacion = actividades.get('OPERACION', {})
        for concepto in operacion.get('conceptos', []):
            for cuenta in concepto.get('cuentas', []):
                if cuenta.get('es_cuenta_cxc'):
                    for estado in cuenta.get('etiquetas', []):
                        estado_nombre = estado.get('nombre', '')
                        for cliente in estado.get('sub_etiquetas', []):
                            cliente_nombre = cliente.get('nombre', '')
                            if 'TRONADOR' in cliente_nombre:
                                print()
                                print(f'ESTADO: {estado_nombre}')
                                print(f'  CLIENTE: {cliente_nombre}')
                                print(f'  MONTO TOTAL: ${cliente.get("monto"):,.0f}')
                                print(f'  MONTOS POR MES:')
                                for periodo, monto in sorted(cliente.get('montos_por_mes', {}).items()):
                                    if monto != 0:
                                        print(f'    {periodo}: ${monto:,.0f}')
    else:
        print(f'ERROR {resp.status_code}: {resp.text[:500]}')
except Exception as e:
    print(f'ERROR: {e}')

import requests

data = {
    "oc_id": 9999,
    "oc_name": "TEST001",
    "proveedor": "Proveedor Test",
    "monto_total": 100000000,
    "distribuciones": [
        {"fecha": "2026-03-15", "monto": 50000000},
        {"fecha": "2026-04-15", "monto": 50000000}
    ]
}

r = requests.post('http://localhost:8000/api/v1/flujo-caja/distribuciones-oc', json=data)
print(f'Status: {r.status_code}')
print(f'Response: {r.json()}')

# Listar distribuciones
r2 = requests.get('http://localhost:8000/api/v1/flujo-caja/distribuciones-oc')
print(f'\nDistribuciones guardadas: {r2.json()}')

# Eliminar la de prueba
r3 = requests.delete('http://localhost:8000/api/v1/flujo-caja/distribuciones-oc/9999')
print(f'\nEliminada: {r3.json()}')

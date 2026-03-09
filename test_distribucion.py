import requests

# Test 1: Crear distribución
print("=== Test 1: Crear distribución ===")
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

# Test 2: Listar distribuciones
print("\n=== Test 2: Listar distribuciones ===")
r2 = requests.get('http://localhost:8000/api/v1/flujo-caja/distribuciones-oc')
print(f'Distribuciones guardadas: {len(r2.json())} registros')

# Test 3: Generar plantilla
print("\n=== Test 3: Generar plantilla ===")
plantilla_data = {
    "monto_total": 10000000,
    "tipo": "cuotas_iguales",
    "num_cuotas": 3,
    "fecha_inicio": "2026-03-15",
    "oc_id": 12345,
    "oc_name": "PO12345",
    "proveedor": "Test Proveedor"
}
r3 = requests.post('http://localhost:8000/api/v1/flujo-caja/distribuciones-oc/generar-plantilla', json=plantilla_data)
print(f'Plantilla generada: {r3.json()}')

# Test 4: Eliminar la de prueba
print("\n=== Test 4: Eliminar distribución ===")
r4 = requests.delete('http://localhost:8000/api/v1/flujo-caja/distribuciones-oc/9999')
print(f'Eliminada: {r4.json()}')

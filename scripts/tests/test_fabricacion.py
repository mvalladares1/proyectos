"""Test para verificar el servicio del monitor"""
from backend.services.monitor_produccion_service import MonitorProduccionService

service = MonitorProduccionService(
    username='mvalladares@riofuturo.cl', 
    password='c0766224bec30cac071ffe43a858c9ccbd521ddd'
)

# Probar get_procesos_activos
print("=== PROCESOS ACTIVOS ===")
result = service.get_procesos_activos('2026-02-03', None, None, None)
procesos = result.get('procesos', [])
stats = result.get('estadisticas', {})

print(f"Total procesos: {len(procesos)}")
print(f"KG Programados: {stats.get('kg_programados', 0):,.2f}")
print(f"KG Producidos: {stats.get('kg_producidos', 0):,.2f}")
print(f"KG Pendientes: {stats.get('kg_pendientes', 0):,.2f}")
print(f"Por estado: {stats.get('por_estado', {})}")

# Probar get_procesos_cerrados_dia
print("\n=== PROCESOS CERRADOS HOY ===")
cerrados = service.get_procesos_cerrados_dia('2026-02-03', None, None, '2026-02-03')
proc_cerrados = cerrados.get('procesos', [])
stats_cerr = cerrados.get('estadisticas', {})

print(f"Total cerrados hoy: {len(proc_cerrados)}")
print(f"KG Producidos: {stats_cerr.get('kg_producidos', 0):,.2f}")

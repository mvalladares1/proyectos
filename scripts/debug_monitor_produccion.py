"""
Debug del Monitor de Producción Diario
Prueba los endpoints y la lógica del servicio
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from backend.services.monitor_produccion_service import MonitorProduccionService

# Credenciales estáticas
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

def test_procesos_activos():
    """Prueba obtener procesos activos (no done ni cancel)"""
    print("=" * 60)
    print("TEST: Procesos Activos")
    print("=" * 60)
    
    service = MonitorProduccionService(username=USERNAME, password=PASSWORD)
    
    fecha_hoy = date.today().isoformat()
    print(f"\nFecha: {fecha_hoy}")
    
    try:
        resultado = service.get_procesos_activos(fecha_hoy)
        
        stats = resultado.get("estadisticas", {})
        procesos = resultado.get("procesos", [])
        
        print(f"\n📊 Estadísticas:")
        print(f"   Total procesos activos: {stats.get('total_procesos', 0)}")
        print(f"   KG programados: {stats.get('kg_programados', 0):,.0f}")
        print(f"   KG producidos: {stats.get('kg_producidos', 0):,.0f}")
        print(f"   KG pendientes: {stats.get('kg_pendientes', 0):,.0f}")
        print(f"   % Avance: {stats.get('avance_porcentaje', 0):.1f}%")
        
        print(f"\n📋 Por estado:")
        for estado, cantidad in stats.get("por_estado", {}).items():
            print(f"   {estado}: {cantidad}")
        
        print(f"\n🏭 Por sala:")
        for sala, data in stats.get("por_sala", {}).items():
            print(f"   {sala}: {data['cantidad']} procesos, {data['kg']:,.0f} kg")
        
        print(f"\n📝 Primeros 5 procesos:")
        for p in procesos[:5]:
            producto = p.get('product_id', {})
            if isinstance(producto, dict):
                prod_name = producto.get('name', 'N/A')
            else:
                prod_name = str(producto)
            print(f"   {p.get('name', '')} - {prod_name[:40]} - Estado: {p.get('state', '')}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_procesos_cerrados():
    """Prueba obtener procesos cerrados hoy"""
    print("\n" + "=" * 60)
    print("TEST: Procesos Cerrados Hoy")
    print("=" * 60)
    
    service = MonitorProduccionService(username=USERNAME, password=PASSWORD)
    
    fecha_hoy = date.today().isoformat()
    print(f"\nFecha: {fecha_hoy}")
    
    try:
        resultado = service.get_procesos_cerrados_dia(fecha_hoy)
        
        stats = resultado.get("estadisticas", {})
        procesos = resultado.get("procesos", [])
        
        print(f"\n📊 Estadísticas de cerrados:")
        print(f"   Total cerrados hoy: {stats.get('total_procesos', 0)}")
        print(f"   KG producidos: {stats.get('kg_producidos', 0):,.0f}")
        
        print(f"\n📝 Procesos cerrados hoy:")
        for p in procesos[:10]:
            producto = p.get('product_id', {})
            if isinstance(producto, dict):
                prod_name = producto.get('name', 'N/A')
            else:
                prod_name = str(producto)
            print(f"   {p.get('name', '')} - {prod_name[:40]} - Cerrado: {p.get('date_finished', '')[:16]}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_evolucion():
    """Prueba obtener evolución de procesos en un rango"""
    print("\n" + "=" * 60)
    print("TEST: Evolución de Procesos")
    print("=" * 60)
    
    service = MonitorProduccionService(username=USERNAME, password=PASSWORD)
    
    fecha_fin = date.today()
    fecha_inicio = fecha_fin - timedelta(days=7)
    
    print(f"\nRango: {fecha_inicio.isoformat()} a {fecha_fin.isoformat()}")
    
    try:
        resultado = service.get_evolucion_rango(
            fecha_inicio.isoformat(), 
            fecha_fin.isoformat()
        )
        
        evolucion = resultado.get("evolucion", [])
        totales = resultado.get("totales", {})
        
        print(f"\n📈 Evolución diaria:")
        print(f"   {'Fecha':<12} {'Creados':>8} {'Cerrados':>8} {'KG Prog':>12} {'KG Prod':>12}")
        print(f"   {'-'*52}")
        
        for e in evolucion:
            print(f"   {e['fecha_display']:<12} {e['procesos_creados']:>8} {e['procesos_cerrados']:>8} {e['kg_programados']:>12,.0f} {e['kg_producidos']:>12,.0f}")
        
        print(f"   {'-'*52}")
        print(f"\n📊 Totales del período:")
        print(f"   Total creados: {totales.get('total_creados', 0)}")
        print(f"   Total cerrados: {totales.get('total_cerrados', 0)}")
        print(f"   KG programados: {totales.get('total_kg_programados', 0):,.0f}")
        print(f"   KG producidos: {totales.get('total_kg_producidos', 0):,.0f}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_salas_disponibles():
    """Prueba obtener salas disponibles"""
    print("\n" + "=" * 60)
    print("TEST: Salas Disponibles")
    print("=" * 60)
    
    service = MonitorProduccionService(username=USERNAME, password=PASSWORD)
    
    try:
        salas = service.get_salas_disponibles()
        
        print(f"\n🏭 Salas encontradas ({len(salas)}):")
        for sala in salas:
            print(f"   - {sala}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_snapshot():
    """Prueba guardar un snapshot"""
    print("\n" + "=" * 60)
    print("TEST: Guardar Snapshot")
    print("=" * 60)
    
    service = MonitorProduccionService(username=USERNAME, password=PASSWORD)
    
    fecha_hoy = date.today().isoformat()
    
    try:
        resultado = service.guardar_snapshot(fecha_hoy, "Todas")
        
        print(f"\n✅ Snapshot guardado:")
        print(f"   Archivo: {resultado.get('filename', '')}")
        print(f"   Ruta: {resultado.get('filepath', '')}")
        
        snapshot = resultado.get("snapshot", {})
        print(f"\n📊 Contenido del snapshot:")
        print(f"   Fecha: {snapshot.get('fecha', '')}")
        print(f"   Timestamp: {snapshot.get('timestamp', '')}")
        print(f"   Activos: {snapshot.get('procesos_activos', {}).get('total_procesos', 0)}")
        print(f"   Cerrados: {snapshot.get('procesos_cerrados', {}).get('total_procesos', 0)}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "🔧" * 30)
    print("   DEBUG MONITOR DE PRODUCCIÓN DIARIO")
    print("🔧" * 30)
    
    tests = [
        ("Procesos Activos", test_procesos_activos),
        ("Procesos Cerrados", test_procesos_cerrados),
        ("Evolución", test_evolucion),
        ("Salas Disponibles", test_salas_disponibles),
        ("Snapshot", test_snapshot),
    ]
    
    resultados = []
    for nombre, test_func in tests:
        try:
            resultado = test_func()
            resultados.append((nombre, resultado))
        except Exception as e:
            resultados.append((nombre, False))
            print(f"❌ Error en {nombre}: {e}")
    
    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS")
    print("=" * 60)
    
    for nombre, resultado in resultados:
        emoji = "✅" if resultado else "❌"
        print(f"   {emoji} {nombre}")
    
    total_ok = sum(1 for _, r in resultados if r)
    print(f"\n   Total: {total_ok}/{len(resultados)} tests pasaron")

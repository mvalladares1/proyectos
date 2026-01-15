"""
Debug rápido: verificar servicio con MO específica
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.rendimiento_service import RendimientoService

USERNAME = "mvalladares@riofuturo.cl"
API_KEY = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

def main():
    service = RendimientoService(username=USERNAME, password=API_KEY)
    
    # Obtener datos del dashboard
    data = service.get_dashboard_completo("2025-11-25", "2025-11-25", solo_terminadas=True)
    
    if data:
        mos = data.get('mos', [])
        print(f"Total MOs del 25-nov-2025: {len(mos)}")
        
        # Buscar la MO específica
        for mo in mos:
            if '00759' in str(mo.get('mo_name', '')):
                print(f"\n=== MO ENCONTRADA: {mo.get('mo_name')} ===")
                print(f"Especie: {mo.get('especie')}")
                print(f"Manejo: {mo.get('manejo')}")
                print(f"Kg MP: {mo.get('kg_mp'):,.0f}")
                print(f"Kg PT: {mo.get('kg_pt'):,.0f}")
                print(f"Rendimiento: {mo.get('rendimiento'):.1f}%")
                print(f"Sala: {mo.get('sala')}")
        
        # Buscar todas las MOs de Mora
        print("\n=== MOs DE MORA ===")
        for mo in mos:
            if mo.get('especie') == 'Mora':
                print(f"{mo.get('mo_name')}: {mo.get('kg_mp'):,.0f} kg MP -> {mo.get('kg_pt'):,.0f} kg PT")

if __name__ == "__main__":
    main()

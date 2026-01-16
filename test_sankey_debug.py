#!/usr/bin/env python3
"""Debug script para probar Sankey"""

from backend.services.containers.service import ContainersService

def main():
    svc = ContainersService()
    print("Ejecutando get_sankey_data...")
    result = svc.get_sankey_data('2025-01-01', '2026-01-31')
    
    print(f"\n=== RESULTADOS ===")
    print(f"Nodos: {len(result['nodes'])}")
    print(f"Links: {len(result['links'])}")
    
    if result['nodes']:
        print(f"\nPrimeros 10 nodos:")
        for n in result['nodes'][:10]:
            print(f"  {n['label'][:50]} - color: {n['color']}")
    else:
        print("\n⚠️ NO HAY NODOS!")

if __name__ == "__main__":
    main()

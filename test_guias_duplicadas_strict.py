"""
Script de prueba para verificar la detección de guías duplicadas
con criterio estricto: misma guía Y mismo productor
"""

def test_duplicate_detection_strict():
    """Simula el proceso de detección con el criterio estricto"""
    
    # Datos de ejemplo (simulando lo que vendría de Odoo)
    resultado = [
        {
            "id": 1234,
            "albaran": "ALB-001",
            "fecha": "2026-01-15",
            "productor": "Productor A",
            "guia_despacho": "GD-2024-001",
            "cantidad_pallets": 10,
            "total_kg": 500.0,
        },
        {
            "id": 1235,
            "albaran": "ALB-002",
            "fecha": "2026-01-16",
            "productor": "Productor A",  # MISMO productor
            "guia_despacho": "GD-2024-001",  # MISMA guía -> ES DUPLICADO
            "cantidad_pallets": 15,
            "total_kg": 750.0,
        },
        {
            "id": 1236,
            "albaran": "ALB-003",
            "fecha": "2026-01-17",
            "productor": "Productor B",  # DIFERENTE productor
            "guia_despacho": "GD-2024-001",  # Misma guía -> NO ES DUPLICADO
            "cantidad_pallets": 20,
            "total_kg": 1000.0,
        },
        {
            "id": 1237,
            "albaran": "ALB-004",
            "fecha": "2026-01-18",
            "productor": "Productor C",
            "guia_despacho": "GD-2024-015",
            "cantidad_pallets": 12,
            "total_kg": 600.0,
        },
        {
            "id": 1238,
            "albaran": "ALB-005",
            "fecha": "2026-01-19",
            "productor": "Productor C",  # MISMO productor
            "guia_despacho": "GD-2024-015",  # MISMA guía -> ES DUPLICADO
            "cantidad_pallets": 25,
            "total_kg": 1250.0,
        }
    ]
    
    # Identificar guías duplicadas (mismo número de guía Y mismo productor)
    guias_productor_count = {}
    for item in resultado:
        guia = item["guia_despacho"]
        productor = item["productor"]
        if guia and productor:  # Solo contar si ambos campos tienen valor
            # Crear clave compuesta (guía, productor)
            clave = (guia, productor)
            guias_productor_count[clave] = guias_productor_count.get(clave, 0) + 1
    
    # Marcar duplicados
    for item in resultado:
        guia = item["guia_despacho"]
        productor = item["productor"]
        # Marcar si la combinación (guía, productor) está duplicada
        if guia and productor:
            clave = (guia, productor)
            item["es_duplicada"] = guias_productor_count.get(clave, 0) > 1
        else:
            item["es_duplicada"] = False
    
    # Imprimir resultados
    print("=" * 80)
    print("PRUEBA DE DETECCION DE GUIAS DUPLICADAS")
    print("Criterio: MISMA GUIA + MISMO PRODUCTOR")
    print("=" * 80)
    print()
    
    # Mostrar resumen de combinaciones
    print("Resumen de combinaciones guia-productor:")
    for (guia, productor), count in guias_productor_count.items():
        status = "[!] DUPLICADA" if count > 1 else "[OK] UNICA"
        print(f"  Guia: {guia} | Productor: {productor} -> {count} ocurrencia(s) - {status}")
    
    print()
    print("=" * 80)
    print("DETALLE DE REGISTROS")
    print("=" * 80)
    print()
    
    # Mostrar detalles de cada registro
    for item in resultado:
        dup_marker = "[!] " if item["es_duplicada"] else "    "
        print(f"{dup_marker}ID: {item['id']}")
        print(f"    Albaran: {item['albaran']}")
        print(f"    Fecha: {item['fecha']}")
        print(f"    Productor: {item['productor']}")
        print(f"    Guia: {item['guia_despacho']} {'[DUPLICADA]' if item['es_duplicada'] else ''}")
        print(f"    Pallets: {item['cantidad_pallets']}")
        print(f"    Kg: {item['total_kg']}")
        print()
    
    # Mostrar combinaciones duplicadas encontradas
    combinaciones_duplicadas = [(g, p) for (g, p), count in guias_productor_count.items() if count > 1]
    if combinaciones_duplicadas:
        print("=" * 80)
        print(f"[!] ADVERTENCIA: {len(combinaciones_duplicadas)} combinacion(es) duplicada(s):")
        for guia, productor in combinaciones_duplicadas:
            print(f"    - Guia: {guia} | Productor: {productor}")
        print("=" * 80)
        print()
        print("CASOS DE EJEMPLO:")
        print()
        print("[OK] NO ES DUPLICADO:")
        print("     - Guia 'GD-2024-001' de Productor A (ID 1234)")
        print("     - Guia 'GD-2024-001' de Productor B (ID 1236)")
        print("     -> Misma guia, pero DIFERENTES productores")
        print()
        print("[!] SI ES DUPLICADO:")
        print("     - Guia 'GD-2024-001' de Productor A (ID 1234)")
        print("     - Guia 'GD-2024-001' de Productor A (ID 1235)")
        print("     -> MISMA guia + MISMO productor")
        print("=" * 80)
    else:
        print("=" * 80)
        print("[OK] No se encontraron combinaciones duplicadas")
        print("=" * 80)

if __name__ == "__main__":
    test_duplicate_detection_strict()

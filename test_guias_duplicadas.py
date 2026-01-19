"""
Script de prueba para verificar la funcionalidad de detección de guías duplicadas
"""
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Simular datos de prueba
def test_duplicate_detection():
    """Simula el proceso de detección de guías duplicadas"""
    
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
            "manejo": "Orgánico",
            "tipo_fruta": "Arándano",
            "origen": "RFP"
        },
        {
            "id": 1235,
            "albaran": "ALB-002",
            "fecha": "2026-01-16",
            "productor": "Productor B",
            "guia_despacho": "GD-2024-001",  # DUPLICADA
            "cantidad_pallets": 15,
            "total_kg": 750.0,
            "manejo": "Convencional",
            "tipo_fruta": "Frambuesa",
            "origen": "VILKUN"
        },
        {
            "id": 1236,
            "albaran": "ALB-003",
            "fecha": "2026-01-17",
            "productor": "Productor C",
            "guia_despacho": "GD-2024-015",
            "cantidad_pallets": 20,
            "total_kg": 1000.0,
            "manejo": "Orgánico",
            "tipo_fruta": "Arándano",
            "origen": "RFP"
        },
        {
            "id": 1237,
            "albaran": "ALB-004",
            "fecha": "2026-01-18",
            "productor": "Productor D",
            "guia_despacho": "GD-2024-015",  # DUPLICADA
            "cantidad_pallets": 12,
            "total_kg": 600.0,
            "manejo": "Convencional",
            "tipo_fruta": "Frambuesa",
            "origen": "VILKUN"
        },
        {
            "id": 1238,
            "albaran": "ALB-005",
            "fecha": "2026-01-19",
            "productor": "Productor E",
            "guia_despacho": "GD-2024-030",  # ÚNICA
            "cantidad_pallets": 25,
            "total_kg": 1250.0,
            "manejo": "Orgánico",
            "tipo_fruta": "Arándano",
            "origen": "RFP"
        }
    ]
    
    # Identificar guías duplicadas (lógica igual a la implementada)
    guias_count = {}
    for item in resultado:
        guia = item["guia_despacho"]
        if guia:  # Solo contar guías no vacías
            guias_count[guia] = guias_count.get(guia, 0) + 1
    
    # Marcar duplicados y agregar URL de Odoo
    odoo_url = "https://riofuturo.server98c6e.oerpondemand.net"
    for item in resultado:
        guia = item["guia_despacho"]
        # Marcar si la guía está duplicada (aparece más de 1 vez)
        item["es_duplicada"] = guias_count.get(guia, 0) > 1 if guia else False
        # Agregar URL para ir directamente al registro en Odoo
        item["odoo_url"] = f"{odoo_url}/web#id={item['id']}&model=stock.picking&view_type=form"
    
    # Imprimir resultados
    print("=" * 80)
    print("PRUEBA DE DETECCION DE GUIAS DUPLICADAS")
    print("=" * 80)
    print()
    
    # Mostrar resumen de guías
    print("Resumen de guias:")
    for guia, count in guias_count.items():
        status = "[!] DUPLICADA" if count > 1 else "[OK] UNICA"
        print(f"  {guia}: {count} ocurrencia(s) - {status}")
    
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
        print(f"    URL Odoo: {item['odoo_url']}")
        print(f"    Pallets: {item['cantidad_pallets']}")
        print(f"    Kg: {item['total_kg']}")
        print()
    
    # Mostrar guías duplicadas encontradas
    guias_duplicadas = [guia for guia, count in guias_count.items() if count > 1]
    if guias_duplicadas:
        print("=" * 80)
        print(f"[!] ADVERTENCIA: {len(guias_duplicadas)} guia(s) duplicada(s):")
        print(f"    {', '.join(guias_duplicadas)}")
        print("=" * 80)
    else:
        print("=" * 80)
        print("[OK] No se encontraron guias duplicadas")
        print("=" * 80)

if __name__ == "__main__":
    test_duplicate_detection()

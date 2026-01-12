#!/usr/bin/env python3
"""Test directo del import de FlujoCajaService"""
import sys
sys.path.insert(0, "/app")

try:
    from backend.services.flujo_caja_service import FlujoCajaService
    print("✓ Import exitoso")
    
    # Intentar inicializar
    service = FlujoCajaService(username="test", password="test")
    print("✓ Inicialización exitosa")
    
except Exception as e:
    import traceback
    print(f"✗ Error: {e}")
    print(traceback.format_exc())

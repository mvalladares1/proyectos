#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')

try:
    print("1. Importando FlujoCajaService...")
    from backend.services.flujo_caja_service import FlujoCajaService
    print("✅ Import OK")
    
    print("\n2. Creando instancia...")
    service = FlujoCajaService(username="test", password="test")
    print("✅ Instancia creada")
    
    print("\n3. Test completado exitosamente")
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

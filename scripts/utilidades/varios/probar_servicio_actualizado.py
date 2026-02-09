#!/usr/bin/env python3
"""
Prueba del servicio actualizado para leer defectos desde one2many lines.
Debe mostrar defectos reales en lugar de 0.
"""
import sys
import os
sys.path.insert(0, '.')

from backend.services.recepcion_defectos_service import generar_reporte_defectos_excel

# Credenciales desde variables de entorno
username = os.getenv('ODOO_USER', 'admin@riofuturo.com')
password = os.getenv('ODOO_PASSWORD', '')

if not password:
    print("❌ Error: Se requiere ODOO_PASSWORD en las variables de entorno")
    sys.exit(1)

# Generar Excel para el período de prueba (misma fecha que vemos en las capturas)
print("🔄 Generando Excel de defectos para período 2026-01-26 a 2026-02-02...")
print("   Este período debe incluir el QC con 11.1% defectos que viste en pantalla\n")

try:
    excel_bytes = generar_reporte_defectos_excel(
        username=username,
        password=password,
        fecha_inicio='2026-01-26',
        fecha_fin='2026-02-02',
        origenes=None,  # Todos los orígenes
        solo_hechas=True
    )
    
    # Guardar el archivo
    output_path = "test_defectos_actualizado.xlsx"
    with open(output_path, 'wb') as f:
        f.write(excel_bytes)
    
    print(f"✅ Excel generado: {output_path}")
    print(f"   Tamaño: {len(excel_bytes):,} bytes")
    print("\n📊 Abre el archivo Excel y verifica:")
    print("   1. ¿Hay valores diferentes de 0 en las columnas de defectos?")
    print("   2. ¿Aparece algún registro con ~11% en la columna '% Defectos'?")
    print("   3. ¿Los valores de defectos en gramos suman correctamente?")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

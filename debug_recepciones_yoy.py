"""
Script de Debug: Comparativa de Recepciones Año Actual vs Año Anterior
Ejecutar con: python debug_recepciones_yoy.py
"""
import sys
import os

# Añadir path del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.services.recepcion_service import get_recepciones_mp

# Configuración - CAMBIAR CREDENCIALES SI ES NECESARIO
USERNAME = os.getenv("ODOO_USER", "mvalladares@riofuturo.cl")
PASSWORD = os.getenv("ODOO_PASSWORD", "6afb207106b646465ffdc4c3df4d34cb99208eef")  # Llenar con API key

# Fechas fijas según solicitud del usuario
FECHA_ACTUAL_INICIO = "2025-11-24"
FECHA_ACTUAL_FIN = "2025-12-30"

FECHA_ANTERIOR_INICIO = "2023-11-24"
FECHA_ANTERIOR_FIN = "2024-04-30"


def analizar_recepciones(recepciones, titulo):
    """Analiza y muestra estadísticas de un lote de recepciones."""
    print(f"\n{'='*60}")
    print(f"   {titulo}")
    print(f"{'='*60}")
    
    if not recepciones:
        print("❌ No se encontraron recepciones en este período.")
        return
    
    print(f"✅ Total recepciones encontradas: {len(recepciones)}")
    
    # Contadores
    total_kg = 0
    kg_por_semana = {}
    productos_excluidos = {'bandejas': 0, 'pallets': 0}
    productos_contados = 0
    sin_tipo_fruta = 0
    
    for rec in recepciones:
        tipo_fruta = rec.get('tipo_fruta', '')
        if not tipo_fruta:
            sin_tipo_fruta += 1
        
        fecha = rec.get('fecha', '')
        try:
            from datetime import datetime
            import pandas as pd
            fecha_dt = pd.to_datetime(fecha)
            semana = fecha_dt.isocalendar().week
        except:
            continue
        
        productos = rec.get('productos', []) or []
        for p in productos:
            categoria = (p.get('Categoria') or '').strip().upper()
            producto_nombre = (p.get('Producto') or '').strip().upper()
            kg = p.get('Kg Hechos', 0) or 0
            
            if kg <= 0:
                continue
            
            # Verificar exclusiones
            if 'BANDEJ' in categoria:
                productos_excluidos['bandejas'] += 1
                continue
            if 'PALLET' in producto_nombre:
                productos_excluidos['pallets'] += 1
                continue
            
            productos_contados += 1
            total_kg += kg
            
            if semana not in kg_por_semana:
                kg_por_semana[semana] = 0
            kg_por_semana[semana] += kg
    
    print(f"\n📊 Estadísticas:")
    print(f"   - Recepciones sin tipo_fruta: {sin_tipo_fruta}")
    print(f"   - Productos excluidos (bandejas): {productos_excluidos['bandejas']}")
    print(f"   - Productos excluidos (pallets): {productos_excluidos['pallets']}")
    print(f"   - Productos contados: {productos_contados}")
    print(f"   - Total Kg: {total_kg:,.0f}")
    
    print(f"\n📅 Kg por Semana:")
    for semana in sorted(kg_por_semana.keys()):
        print(f"   S{semana}: {kg_por_semana[semana]:,.0f} kg")
    
    return total_kg, kg_por_semana


def main():
    if not PASSWORD:
        print("❌ ERROR: Debes configurar la contraseña/API key en la variable PASSWORD o ODOO_PASSWORD")
        print("   Ejemplo: export ODOO_PASSWORD='tu_api_key'")
        sys.exit(1)
    
    print("\n🔍 DEBUG: Comparativa de Recepciones Año Actual vs Año Anterior")
    print(f"   Usuario: {USERNAME}")
    
    # Año Actual
    print(f"\n📆 Consultando AÑO ACTUAL: {FECHA_ACTUAL_INICIO} a {FECHA_ACTUAL_FIN}")
    try:
        recepciones_actual = get_recepciones_mp(
            username=USERNAME,
            password=PASSWORD,
            fecha_inicio=FECHA_ACTUAL_INICIO,
            fecha_fin=FECHA_ACTUAL_FIN,
            solo_hechas=True
        )
        analizar_recepciones(recepciones_actual, "AÑO ACTUAL (2025)")
    except Exception as e:
        print(f"❌ Error al consultar año actual: {e}")
    
    # Año Anterior
    print(f"\n📆 Consultando AÑO ANTERIOR: {FECHA_ANTERIOR_INICIO} a {FECHA_ANTERIOR_FIN}")
    try:
        recepciones_anterior = get_recepciones_mp(
            username=USERNAME,
            password=PASSWORD,
            fecha_inicio=FECHA_ANTERIOR_INICIO,
            fecha_fin=FECHA_ANTERIOR_FIN,
            solo_hechas=True
        )
        analizar_recepciones(recepciones_anterior, "AÑO ANTERIOR (2023-2024)")
    except Exception as e:
        print(f"❌ Error al consultar año anterior: {e}")
    
    print("\n" + "="*60)
    print("   FIN DEL DEBUG")
    print("="*60)


if __name__ == "__main__":
    main()

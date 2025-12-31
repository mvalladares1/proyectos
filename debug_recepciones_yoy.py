"""
Script de Debug: Comparativa de Recepciones Año Actual vs Año Anterior
Ejecutar con: python debug_recepciones_yoy.py
"""
import sys
import os
import requests
import pandas as pd
from datetime import datetime

# Añadir path del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# API URL - nginx proxies /api/v1/ to backend:8000
API_URL = os.getenv("API_URL", "http://167.114.114.51")

# Configuración
USERNAME = os.getenv("ODOO_USER", "mvalladares@riofuturo.cl")
PASSWORD = os.getenv("ODOO_PASSWORD", "6afb207106b646465ffdc4c3df4d34cb99208eef")

# Fechas fijas según temporada
FECHA_ACTUAL_INICIO = "2024-11-20"
FECHA_ACTUAL_FIN = "2025-04-30"

FECHA_ANTERIOR_INICIO = "2023-11-20"
FECHA_ANTERIOR_FIN = "2024-04-30"


def analizar_recepciones(recepciones, titulo, show_samples=True):
    """Analiza y muestra estadísticas de un lote de recepciones."""
    print(f"\n{'='*60}")
    print(f"   {titulo}")
    print(f"{'='*60}")
    
    if not recepciones:
        print("❌ No se encontraron recepciones en este período.")
        return 0, {}
    
    print(f"✅ Total recepciones encontradas: {len(recepciones)}")
    
    # Contadores
    total_kg = 0
    kg_por_semana = {}
    productos_excluidos = {'bandejas': 0, 'pallets': 0, 'kg_cero': 0}
    productos_contados = 0
    sin_tipo_fruta = 0
    
    # DEBUG: Mostrar estructura de la primera recepción
    if show_samples and recepciones:
        print("\n🔍 DEBUG - Estructura de primera recepción:")
        first_rec = recepciones[0]
        print(f"   Keys en recepción: {list(first_rec.keys())}")
        productos_sample = first_rec.get('productos', []) or []
        if productos_sample:
            print(f"   Cantidad de productos en primera rec: {len(productos_sample)}")
            print(f"   Keys en primer producto: {list(productos_sample[0].keys())}")
            print(f"   Primer producto completo: {productos_sample[0]}")
        else:
            print(f"   ⚠️ No hay productos en primera recepción")
            # Buscar otros campos que puedan tener los kg
            for k, v in first_rec.items():
                if 'kg' in k.lower() or 'peso' in k.lower() or 'cantidad' in k.lower():
                    print(f"   Campo alternativo: {k} = {v}")
    
    for rec in recepciones:
        tipo_fruta = rec.get('tipo_fruta', '')
        if not tipo_fruta:
            sin_tipo_fruta += 1
        
        fecha = rec.get('fecha', '')
        try:
            fecha_dt = pd.to_datetime(fecha)
            semana = fecha_dt.isocalendar().week
        except:
            continue
        
        productos = rec.get('productos', []) or []
        for p in productos:
            categoria = (p.get('Categoria') or '').strip().upper()
            producto_nombre = (p.get('Producto') or '').strip().upper()
            
            # Intentar diferentes campos para kg
            kg = p.get('Kg Hechos', 0) or p.get('kg_hechos', 0) or p.get('Kg', 0) or p.get('kg', 0) or 0
            
            if kg <= 0:
                productos_excluidos['kg_cero'] += 1
                continue
            
            # Verificar exclusiones - SOLO por categoría, no por nombre de producto
            # Productos como 'IQF en Bandeja' son válidos y tienen kg
            if 'BANDEJ' in categoria:
                productos_excluidos['bandejas'] += 1
                continue
            if 'PALLET' in categoria:
                productos_excluidos['pallets'] += 1
                continue
            
            productos_contados += 1
            total_kg += kg
            
            if semana not in kg_por_semana:
                kg_por_semana[semana] = 0
            kg_por_semana[semana] += kg
    
    print(f"\n📊 Estadísticas:")
    print(f"   - Recepciones sin tipo_fruta: {sin_tipo_fruta}")
    print(f"   - Productos con kg=0: {productos_excluidos['kg_cero']}")
    print(f"   - Productos excluidos (bandejas): {productos_excluidos['bandejas']}")
    print(f"   - Productos excluidos (pallets): {productos_excluidos['pallets']}")
    print(f"   - Productos contados: {productos_contados}")
    print(f"   - Total Kg: {total_kg:,.0f}")
    
    print(f"\n📅 Kg por Semana:")
    for semana in sorted(kg_por_semana.keys()):
        print(f"   S{semana}: {kg_por_semana[semana]:,.0f} kg")
    
    return total_kg, kg_por_semana


def consultar_api(fecha_inicio, fecha_fin):
    """Consulta la API de recepciones."""
    params = {
        "username": USERNAME,
        "password": PASSWORD,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "solo_hechas": True
    }
    
    print(f"   URL: {API_URL}/api/v1/recepciones-mp/")
    print(f"   Params: fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}")
    
    try:
        resp = requests.get(
            f"{API_URL}/api/v1/recepciones-mp/",
            params=params,
            timeout=120
        )
        
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"❌ Error HTTP: {resp.status_code}")
            print(f"   Response: {resp.text[:500]}")
            return None
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None


def main():
    if not PASSWORD:
        print("❌ ERROR: Debes configurar la contraseña/API key")
        sys.exit(1)
    
    print("\n🔍 DEBUG: Comparativa de Recepciones Año Actual vs Año Anterior")
    print(f"   API URL: {API_URL}")
    print(f"   Usuario: {USERNAME}")
    
    # Año Anterior (Temporada 2023-2024)
    print(f"\n📆 Consultando AÑO ANTERIOR: {FECHA_ANTERIOR_INICIO} a {FECHA_ANTERIOR_FIN}")
    recepciones_anterior = consultar_api(FECHA_ANTERIOR_INICIO, FECHA_ANTERIOR_FIN)
    kg_anterior, semanas_anterior = analizar_recepciones(recepciones_anterior, "AÑO ANTERIOR (Temporada 2023-2024)")
    
    # Año Actual (Temporada 2024-2025)
    print(f"\n📆 Consultando AÑO ACTUAL: {FECHA_ACTUAL_INICIO} a {FECHA_ACTUAL_FIN}")
    recepciones_actual = consultar_api(FECHA_ACTUAL_INICIO, FECHA_ACTUAL_FIN)
    kg_actual, semanas_actual = analizar_recepciones(recepciones_actual, "AÑO ACTUAL (Temporada 2024-2025)")
    
    # Resumen Final
    print("\n" + "="*60)
    print("   RESUMEN FINAL")
    print("="*60)
    print(f"   Año Anterior Total: {kg_anterior:,.0f} kg")
    print(f"   Año Actual Total:   {kg_actual:,.0f} kg")
    if kg_anterior > 0:
        diff_pct = ((kg_actual - kg_anterior) / kg_anterior) * 100
        print(f"   Diferencia: {diff_pct:+.1f}%")
    
    # Mostrar muestra de datos si hay recepciones
    if recepciones_anterior and len(recepciones_anterior) > 0:
        print("\n📋 Muestra de primeras 3 recepciones año anterior:")
        for i, rec in enumerate(recepciones_anterior[:3]):
            print(f"   [{i+1}] Fecha: {rec.get('fecha')}, Tipo: {rec.get('tipo_fruta')}, Prods: {len(rec.get('productos', []))}")
    
    print("\n" + "="*60)
    print("   FIN DEL DEBUG")
    print("="*60)


if __name__ == "__main__":
    main()

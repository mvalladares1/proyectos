#!/usr/bin/env python3
"""
Debug Forense: Flujo de Caja Mensualizado

Script para diagnosticar problemas con el endpoint /api/v1/flujo-caja/mensual.
Llama al backend y muestra toda la información para análisis.

Uso:
    python scripts/debug_flujo_mensual.py --fecha_inicio 2026-01-01 --fecha_fin 2026-12-31

Requiere:
    - Variables de entorno ODOO_USERNAME y ODOO_PASSWORD
    - O pasar --username y --password
"""
import os
import sys
import json
import requests
from datetime import datetime
from pprint import pprint

# Agregar el path del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuración
API_URL_DEV = "http://127.0.0.1:8002"
API_URL_PROD = "http://127.0.0.1:8000"
API_URL_REMOTE_DEV = "http://167.114.114.51:8002"   # DEV remoto
API_URL_REMOTE_PROD = "http://167.114.114.51:8000"  # PROD remoto

def log(msg, level="INFO"):
    """Logger simple con timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = {
        "INFO": "ℹ️ ",
        "OK": "✅",
        "WARN": "⚠️ ",
        "ERROR": "❌",
        "DEBUG": "🔍"
    }.get(level, "")
    print(f"[{timestamp}] {prefix} {msg}")

def fetch_flujo_mensual(base_url: str, fecha_inicio: str, fecha_fin: str, 
                        username: str, password: str) -> dict:
    """Llama al endpoint /mensual y retorna el JSON."""
    url = f"{base_url}/api/v1/flujo-caja/mensual"
    params = {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "username": username,
        "password": password
    }
    
    log(f"Llamando a {url}")
    log(f"Parámetros: {fecha_inicio} a {fecha_fin}")
    
    try:
        resp = requests.get(url, params=params, timeout=120)
        log(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            return resp.json()
        else:
            log(f"Error: {resp.text[:500]}", "ERROR")
            return {"error": resp.text}
    except Exception as e:
        log(f"Excepción: {e}", "ERROR")
        return {"error": str(e)}

def analizar_respuesta(data: dict):
    """Analiza y muestra la respuesta del backend."""
    
    print("\n" + "="*80)
    print("🔬 ANÁLISIS FORENSE DEL FLUJO DE CAJA MENSUALIZADO")
    print("="*80)
    
    # 1. Metadata
    print("\n📋 METADATA")
    print("-"*40)
    meta = data.get("meta", {})
    periodo = data.get("periodo", {})
    print(f"  Versión: {meta.get('version', 'N/A')}")
    print(f"  Modo: {meta.get('mode', 'N/A')}")
    print(f"  Período: {periodo.get('inicio', 'N/A')} a {periodo.get('fin', 'N/A')}")
    print(f"  Generado: {data.get('generado', 'N/A')}")
    
    # 2. Meses
    meses = data.get("meses", [])
    print(f"\n📅 MESES ({len(meses)})")
    print("-"*40)
    print(f"  Lista: {', '.join(meses)}")
    
    # 3. Conciliación
    conc = data.get("conciliacion", {})
    print(f"\n💰 CONCILIACIÓN")
    print("-"*40)
    print(f"  Efectivo Inicial: ${conc.get('efectivo_inicial', 0):,.0f}")
    print(f"  Efectivo Final:   ${conc.get('efectivo_final', 0):,.0f}")
    print(f"  Variación Neta:   ${conc.get('variacion_neta', 0):,.0f}")
    
    # 4. Efectivo por Mes
    ef_por_mes = data.get("efectivo_por_mes", {})
    print(f"\n📊 EFECTIVO POR MES ({len(ef_por_mes)} entries)")
    print("-"*40)
    for mes in meses:
        ef = ef_por_mes.get(mes, {})
        ini = ef.get("inicial", 0)
        var = ef.get("variacion", 0)
        fin = ef.get("final", 0)
        indicator = "🟢" if var > 0 else ("🔴" if var < 0 else "⚪")
        print(f"  {mes}: Ini=${ini:>15,.0f} | Var=${var:>12,.0f} {indicator} | Fin=${fin:>15,.0f}")
    
    # 5. Actividades
    actividades = data.get("actividades", {})
    print(f"\n🏢 ACTIVIDADES ({len(actividades)})")
    print("-"*40)
    
    for act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
        act = actividades.get(act_key, {})
        if not act:
            continue
            
        subtotal = act.get("subtotal", 0)
        subtotal_mes = act.get("subtotal_por_mes", {})
        conceptos = act.get("conceptos", [])
        
        indicator = "🟢" if subtotal > 0 else ("🔴" if subtotal < 0 else "⚪")
        print(f"\n  {indicator} {act_key}: ${subtotal:,.0f}")
        print(f"     Subtotal por mes: {json.dumps(subtotal_mes)}")
        print(f"     Conceptos: {len(conceptos)}")
        
        # Mostrar conceptos con valores
        conceptos_con_valor = [c for c in conceptos if c.get("total", 0) != 0]
        if conceptos_con_valor:
            print(f"     Conceptos con valor ({len(conceptos_con_valor)}):")
            for c in conceptos_con_valor:
                c_id = c.get("id", "")
                c_nombre = c.get("nombre", "")[:40]
                c_total = c.get("total", 0)
                montos_mes = c.get("montos_por_mes", {})
                
                # Verificar si tiene datos en más de un mes
                meses_con_datos = sum(1 for m, v in montos_mes.items() if v != 0)
                
                ind = "🟢" if c_total > 0 else "🔴"
                print(f"       {ind} {c_id}: ${c_total:>12,.0f} ({meses_con_datos} meses con datos)")
                
                # Mostrar distribución por mes
                print(f"          Distribución: {json.dumps({k: v for k, v in montos_mes.items() if v != 0})}")
    
    # 6. Diagnóstico
    print(f"\n🔍 DIAGNÓSTICO")
    print("-"*40)
    
    # Verificar si solo un mes tiene datos
    meses_con_variacion = [m for m in meses if ef_por_mes.get(m, {}).get("variacion", 0) != 0]
    if len(meses_con_variacion) == 0:
        log("No hay variaciones en ningún mes", "ERROR")
    elif len(meses_con_variacion) == 1:
        log(f"⚠️  Solo {meses_con_variacion[0]} tiene variación - posible problema de parseo de fechas", "WARN")
    else:
        log(f"Meses con variación: {meses_con_variacion}", "OK")
    
    # Verificar subtotales por mes vs total
    for act_key in ["OPERACION", "INVERSION", "FINANCIAMIENTO"]:
        act = actividades.get(act_key, {})
        subtotal = act.get("subtotal", 0)
        subtotal_mes = act.get("subtotal_por_mes", {})
        suma_meses = sum(subtotal_mes.values())
        
        if abs(subtotal - suma_meses) > 1:
            log(f"{act_key}: Suma meses ({suma_meses:,.0f}) != Subtotal ({subtotal:,.0f})", "WARN")
        elif subtotal != 0:
            log(f"{act_key}: Suma meses OK", "OK")

def main():
    print("="*60)
    print("🔬 DEBUG FORENSE - FLUJO DE CAJA MENSUALIZADO")
    print("="*60)
    
    # Login en consola como otros scripts
    username = input("\n👤 Usuario Odoo: ").strip()
    password = input("🔑 API Key: ").strip()
    
    if not username or not password:
        log("Falta username/password", "ERROR")
        sys.exit(1)
    
    # Seleccionar entorno
    print("\n📍 Entorno:")
    print("  1. Local DEV (127.0.0.1:8002)")
    print("  2. Remote DEV (167.114.114.51:8002)")
    print("  3. Remote PROD (167.114.114.51:8000)")
    env_choice = input("Selecciona (1/2/3) [2]: ").strip() or "2"
    
    if env_choice == "1":
        base_url = API_URL_DEV
    elif env_choice == "3":
        base_url = API_URL_REMOTE_PROD
    else:
        base_url = API_URL_REMOTE_DEV
    
    # Fechas
    print("\n📅 Período:")
    fecha_inicio = input("Fecha inicio (YYYY-MM-DD) [2026-01-01]: ").strip() or "2026-01-01"
    fecha_fin = input("Fecha fin (YYYY-MM-DD) [2026-12-31]: ").strip() or "2026-12-31"
    
    log(f"Entorno: {base_url}")
    log(f"Período: {fecha_inicio} a {fecha_fin}")
    
    # Llamar API
    data = fetch_flujo_mensual(
        base_url=base_url,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        username=username,
        password=password
    )
    
    if "error" in data:
        log(f"Error en respuesta: {data['error']}", "ERROR")
        sys.exit(1)
    
    # Analizar
    analizar_respuesta(data)
    
    # Preguntar si guardar
    guardar = input("\n💾 ¿Guardar JSON a archivo? (s/N): ").strip().lower()
    if guardar == "s":
        filename = f"flujo_debug_{fecha_inicio}_{fecha_fin}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log(f"JSON guardado en {filename}", "OK")
    
    print("\n" + "="*60)
    log("Análisis completado", "OK")

if __name__ == "__main__":
    main()

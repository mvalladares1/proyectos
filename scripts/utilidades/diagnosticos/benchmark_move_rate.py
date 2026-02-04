#!/usr/bin/env python3
"""
Analiza el ritmo de creación de stock.move.line
"""
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from shared.odoo_client import OdooClient


def analyze():
    odoo = OdooClient(
        username = "frios@riofuturo.cl",
        password = "413c17f8c0a0ebe211cda26c094c2bbb47fce5c6"
    )
    
    print("=" * 60)
    print("ANÁLISIS: Ritmo de creación de stock.move.line")
    print("=" * 60)
    
    # Traer últimos 30 días de movimientos con fecha de creación
    fecha_inicio = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    print(f"\n📊 Analizando movimientos desde {fecha_inicio}...")
    
    records = odoo.search_read(
        "stock.move.line",
        [
            ("create_date", ">=", fecha_inicio),
            ("state", "=", "done"),
        ],
        ["id", "create_date"],
        limit=50000,
        order="create_date desc"
    )
    
    print(f"   Registros analizados: {len(records):,}")
    
    if not records:
        print("   No hay registros recientes")
        return
    
    # Agrupar por día
    por_dia = defaultdict(int)
    por_hora = defaultdict(int)
    
    for r in records:
        if r.get("create_date"):
            dt = datetime.fromisoformat(r["create_date"].replace("Z", "+00:00"))
            dia = dt.strftime("%Y-%m-%d")
            hora = dt.hour
            por_dia[dia] += 1
            por_hora[hora] += 1
    
    # Estadísticas por día
    dias = sorted(por_dia.keys(), reverse=True)[:14]  # últimos 14 días
    
    print("\n📅 Movimientos por día (últimos 14 días):")
    print("-" * 40)
    total = 0
    for dia in dias:
        count = por_dia[dia]
        total += count
        bar = "█" * (count // 50)
        print(f"   {dia}: {count:>5} {bar}")
    
    promedio_dia = total / len(dias) if dias else 0
    
    print("-" * 40)
    print(f"   Promedio: {promedio_dia:.0f} movimientos/día")
    print(f"   Por hora: {promedio_dia/24:.0f} movimientos/hora")
    print(f"   Por 5 min: {promedio_dia/24/12:.1f} movimientos/5min")
    
    # Distribución por hora del día
    print("\n🕐 Distribución por hora del día:")
    print("-" * 40)
    max_hora = max(por_hora.values()) if por_hora else 1
    for h in range(24):
        count = por_hora.get(h, 0)
        bar = "█" * int(count / max_hora * 20) if max_hora > 0 else ""
        print(f"   {h:02d}:00 - {count:>5} {bar}")
    
    print("\n" + "=" * 60)
    print("CONCLUSIÓN PARA CACHÉ")
    print("=" * 60)
    print(f"  - Promedio: ~{promedio_dia:.0f} movimientos/día")
    print(f"  - Refresh cada 5 min: ~{promedio_dia/24/12:.0f} registros nuevos")
    print(f"  - Tiempo refresh: <1 segundo")
    print("=" * 60)


if __name__ == "__main__":
    analyze()

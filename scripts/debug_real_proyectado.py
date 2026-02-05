"""
Debug: Verificar módulo RealProyectadoCalculator
================================================

Prueba el nuevo módulo de cálculo de REAL/PROYECTADO/PPTO
antes de integrarlo al servicio principal.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
from backend.services.flujo_caja.real_proyectado import RealProyectadoCalculator

# Credenciales estáticas para debug
USERNAME = 'mvalladares@riofuturo.cl'
PASSWORD = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'


def main():
    print("=" * 80)
    print("DEBUG: RealProyectadoCalculator")
    print("=" * 80)
    
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    calculator = RealProyectadoCalculator(odoo)
    
    # Período de análisis
    fecha_inicio = '2026-01-01'
    fecha_fin = '2026-01-31'
    
    print(f"\nPeríodo: {fecha_inicio} a {fecha_fin}")
    
    # ==========================================
    # 1. TEST: calcular_todos()
    # ==========================================
    print("\n[1] TEST: calcular_todos()")
    print("-" * 50)
    
    resultados = calculator.calcular_todos(fecha_inicio, fecha_fin)
    
    for concepto_id, data in resultados.items():
        print(f"\n  {concepto_id}:")
        print(f"    REAL:       ${data.get('real', 0):>18,.0f}")
        print(f"    PROYECTADO: ${data.get('proyectado', 0):>18,.0f}")
        print(f"    PPTO:       ${data.get('ppto', 0):>18,.0f}")
        
        if data.get('error'):
            print(f"    ⚠️ ERROR: {data['error']}")
        
        if data.get('facturas_count'):
            print(f"    Facturas procesadas: {data['facturas_count']}")
        if data.get('movimientos_count'):
            print(f"    Movimientos procesados: {data['movimientos_count']}")
        
        # Mostrar por mes
        real_por_mes = data.get('real_por_mes', {})
        proy_por_mes = data.get('proyectado_por_mes', {})
        if real_por_mes:
            print(f"    Por mes:")
            for mes in sorted(real_por_mes.keys()):
                r = real_por_mes.get(mes, 0)
                p = proy_por_mes.get(mes, 0)
                print(f"      {mes}: REAL=${r:>15,.0f} | PROY=${p:>15,.0f}")
    
    # ==========================================
    # 2. TEST: Enriquecer concepto
    # ==========================================
    print("\n[2] TEST: enriquecer_concepto()")
    print("-" * 50)
    
    # Simular un concepto existente
    concepto_mock = {
        'id': '1.2.1',
        'nombre': 'Pagos a proveedores por el suministro de bienes y servicios',
        'tipo': 'LINEA',
        'total': -2500000000,  # Valor existente del flujo
        'montos_por_mes': {'2026-01': -2500000000}
    }
    
    print(f"\n  Concepto ANTES:")
    print(f"    ID: {concepto_mock['id']}")
    print(f"    Total existente: ${concepto_mock['total']:,.0f}")
    print(f"    Campos: {list(concepto_mock.keys())}")
    
    concepto_enriquecido = calculator.enriquecer_concepto(
        concepto_mock.copy(), 
        resultados, 
        '1.2.1'
    )
    
    print(f"\n  Concepto DESPUÉS:")
    print(f"    REAL:       ${concepto_enriquecido.get('real', 0):>18,.0f}")
    print(f"    PROYECTADO: ${concepto_enriquecido.get('proyectado', 0):>18,.0f}")
    print(f"    PPTO:       ${concepto_enriquecido.get('ppto', 0):>18,.0f}")
    print(f"    Campos: {list(concepto_enriquecido.keys())}")
    
    # ==========================================
    # RESUMEN
    # ==========================================
    print("\n" + "=" * 80)
    print("RESUMEN - ESTRUCTURA PARA EL FRONTEND")
    print("=" * 80)
    
    print("""
    Cada concepto tendrá ahora:
    {
        "id": "1.2.1",
        "nombre": "Pagos a proveedores...",
        "tipo": "LINEA",
        "total": -2500000000,           // Existente
        "montos_por_mes": {...},        // Existente
        
        // NUEVOS CAMPOS:
        "real": -2572079721,            // REAL calculado
        "proyectado": -1432697589,      // PROYECTADO calculado  
        "ppto": 0,                      // PPTO (vacío)
        "real_por_mes": {...},          // Desglose mensual REAL
        "proyectado_por_mes": {...}     // Desglose mensual PROYECTADO
    }
    
    El frontend mostrará:
    | CONCEPTO | REAL | PROYECTADO | PPTO | Ene | Feb | Mar | ... | TOTAL |
    
    PRÓXIMOS PASOS:
    1. Integrar calculator en flujo_caja_service.py
    2. Modificar frontend para mostrar columnas
    """)


if __name__ == "__main__":
    main()

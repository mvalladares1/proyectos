"""
Script de verificación completa para 1.1.1 - Cobros de Clientes

Este script verifica que:
1. El API responde correctamente
2. Los períodos se calculan correctamente (periodo_real vs periodo_proyectado)
3. Los montos se distribuyen por semana correctamente
4. TRONADOR muestra la factura parcial con diferentes períodos para cobrado vs pendiente

Ejecutar en el servidor donde está el API:
    python scripts/verify_cxc_periods.py
"""
import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.services.flujo_caja.real_proyectado import RealProyectadoService
from shared.odoo_client import OdooClient

def main():
    print("=" * 80)
    print("VERIFICACIÓN DE 1.1.1 - COBROS DE CLIENTES")
    print("=" * 80)
    
    # Conectar a Odoo
    odoo = OdooClient(
        url=os.environ.get('ODOO_URL', 'https://erp.riofuturo.cl'),
        db=os.environ.get('ODOO_DB', 'riofuturodocker'),
        username='api_user',
        password='rf2025api'
    )
    
    print("\n1. Conectando a Odoo...")
    try:
        odoo.connect()
        print("   ✅ Conexión exitosa")
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return
    
    # Crear servicio
    service = RealProyectadoService(odoo)
    
    # Generar lista de semanas para enero 2025
    meses_lista = ['W01', 'W02', 'W03', 'W04', 'W05', 'W06', 'W07', 'W08', 'W09', 'W10', 'W11', 'W12']
    
    print("\n2. Calculando cobros de clientes (enero-marzo 2025)...")
    try:
        result = service.calcular_cobros_clientes(
            fecha_inicio='2025-01-01',
            fecha_fin='2025-03-31',
            meses_lista=meses_lista
        )
        print("   ✅ Cálculo completado")
    except Exception as e:
        print(f"   ❌ Error en cálculo: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n3. Resumen global:")
    print(f"   - Total REAL (cobrado): ${result['real']:,.0f} CLP")
    print(f"   - Total PROYECTADO (pendiente): ${result['proyectado']:,.0f} CLP")
    print(f"   - Total facturas procesadas: {result.get('facturas_count', 0)}")
    
    print(f"\n4. Distribución por período:")
    for periodo in sorted(result.get('real_por_mes', {}).keys()):
        real = result['real_por_mes'].get(periodo, 0)
        proy = result['proyectado_por_mes'].get(periodo, 0)
        if real > 0 or proy > 0:
            print(f"   {periodo}: REAL=${real:,.0f}  PROY=${proy:,.0f}")
    
    print(f"\n5. Buscando TRONADOR...")
    tronador_found = False
    for cuenta in result.get('cuentas', []):
        estado_nombre = cuenta.get('nombre', '')
        for cliente in cuenta.get('etiquetas', []):
            cliente_nombre = cliente.get('nombre', '')
            if 'TRONADOR' in cliente_nombre.upper():
                tronador_found = True
                print(f"\n   ENCONTRADO EN: {estado_nombre}")
                print(f"   Cliente: {cliente_nombre}")
                print(f"   Monto Total: ${cliente.get('monto', 0):,.0f}")
                print(f"   Real (cobrado): ${cliente.get('real', 0):,.0f}")
                print(f"   Proyectado (pendiente): ${cliente.get('proyectado', 0):,.0f}")
                
                print(f"\n   MONTOS POR MES (real + proyectado):")
                for periodo, monto in sorted(cliente.get('montos_por_mes', {}).items()):
                    if monto != 0:
                        print(f"     {periodo}: ${monto:,.0f}")
                
                print(f"\n   REAL POR MES (solo cobrado):")
                for periodo, monto in sorted(cliente.get('real_por_mes', {}).items()):
                    if monto != 0:
                        print(f"     {periodo}: ${monto:,.0f}")
                
                print(f"\n   PROYECTADO POR MES (solo pendiente):")
                for periodo, monto in sorted(cliente.get('proyectado_por_mes', {}).items()):
                    if monto != 0:
                        print(f"     {periodo}: ${monto:,.0f}")
                
                # Mostrar primeras facturas
                facturas = cliente.get('facturas', [])
                if facturas:
                    print(f"\n   FACTURAS ({len(facturas)} total):")
                    for f in facturas[:5]:  # Mostrar primeras 5
                        print(f"     - {f['name']}: total=${f['total']:,.0f}, cobrado=${f['cobrado']:,.0f}, pendiente=${f['pendiente']:,.0f}")
    
    if not tronador_found:
        print("   ⚠️ TRONADOR no encontrado en el período")
    
    print("\n" + "=" * 80)
    print("VERIFICACIÓN COMPLETADA")
    print("=" * 80)
    
    # Verificar que hay múltiples períodos
    periodos_con_datos = [p for p, m in result.get('montos_por_mes', {}).items() if m != 0]
    if len(periodos_con_datos) > 1:
        print(f"✅ Se encontraron {len(periodos_con_datos)} períodos con datos")
    else:
        print(f"⚠️ Solo se encontró {len(periodos_con_datos)} período con datos - verificar lógica")

if __name__ == '__main__':
    main()

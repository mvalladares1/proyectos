"""
Script para debuggear las etiquetas de CxC en el flujo de caja
y verificar la lógica de filtrado "Solo pendiente"
"""
import sys
from pathlib import Path
import requests
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Credenciales para conectarse al backend DEV
API_URL = "http://167.114.114.51:8002"
ODOO_USER = "mvalladares@riofuturo.cl"
ODOO_PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

def debug_cxc_filtro():
    """Analizar estructura de CxC y probar lógica de filtrado"""
    
    print("=" * 80)
    print("🔍 DEBUG: Analizando estructura de CxC para filtro 'Solo pendiente'")
    print("=" * 80)
    
    # Obtener datos de flujo de caja
    print("\n📡 Consultando API de flujo de caja...")
    response = requests.get(
        f"{API_URL}/api/v1/flujo-caja/mensual",
        params={
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-02-28",
            "username": ODOO_USER,
            "password": ODOO_PASSWORD
        },
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    print("✅ Datos obtenidos correctamente")
    
    # Buscar actividad OPERACION
    actividades = data.get("actividades", {})
    operacion = actividades.get("OPERACION", {})
    
    if not operacion:
        print("❌ No se encontró actividad OPERACION")
        return
    
    print(f"\n📊 OPERACION subtotal: ${operacion.get('subtotal', 0):,.0f}")
    
    # Buscar conceptos con CxC
    conceptos = operacion.get("conceptos", [])
    print(f"\n🔍 Analizando {len(conceptos)} conceptos...\n")
    
    for concepto in conceptos:
        concepto_nombre = concepto.get("nombre", "")
        cuentas = concepto.get("cuentas", [])
        
        # Buscar cuentas CxC
        for cuenta in cuentas:
            es_cxc = cuenta.get("es_cuenta_cxc", False)
            if not es_cxc:
                continue
            
            cuenta_nombre = cuenta.get("nombre", "")
            cuenta_codigo = cuenta.get("codigo", "")
            cuenta_monto = cuenta.get("monto", 0)
            
            print("=" * 80)
            print(f"📁 CONCEPTO: {concepto_nombre}")
            print(f"💰 CUENTA CxC: [{cuenta_codigo}] {cuenta_nombre}")
            print(f"   Total cuenta: ${cuenta_monto:,.0f}")
            print("-" * 80)
            
            # Analizar etiquetas (estados de pago)
            etiquetas = cuenta.get("etiquetas", [])
            print(f"   📋 {len(etiquetas)} etiquetas encontradas:")
            print()
            
            for etiqueta in etiquetas:
                et_nombre = etiqueta.get("nombre", "")
                et_monto = etiqueta.get("monto", 0)
                et_montos_mes = etiqueta.get("montos_por_mes", {})
                
                print(f"   🏷️  Etiqueta: '{et_nombre}'")
                print(f"      Monto total: ${et_monto:,.0f}")
                print(f"      Montos por mes: {et_montos_mes}")
                
                # Probar lógica de filtrado
                print(f"      Análisis de filtro:")
                print(f"        - 'Pagadas' in nombre: {'Pagadas' in et_nombre}")
                print(f"        - 'Parcialmente' NOT in nombre: {'Parcialmente' not in et_nombre}")
                print(f"        - 'No Pagadas' NOT in nombre: {'No Pagadas' not in et_nombre}")
                
                cumple_condicion = (
                    "Pagadas" in et_nombre and 
                    "Parcialmente" not in et_nombre and 
                    "No Pagadas" not in et_nombre
                )
                
                if cumple_condicion:
                    print(f"      ✅ DEBE FILTRARSE (poner en $0)")
                else:
                    print(f"      ❌ NO debe filtrarse")
                
                print()
            
            print("=" * 80)
            print()
    
    # Ahora simular aplicación del filtro
    print("\n" + "=" * 80)
    print("🧪 SIMULACIÓN: Aplicando filtro 'Solo pendiente'")
    print("=" * 80)
    
    import copy
    actividades_filtradas = copy.deepcopy(actividades)
    operacion_filtrada = actividades_filtradas.get("OPERACION", {})
    
    total_filtrado = 0
    
    for concepto in operacion_filtrada.get("conceptos", []):
        cuentas = concepto.get("cuentas", [])
        for cuenta in cuentas:
            if not cuenta.get("es_cuenta_cxc"):
                continue
            
            cuenta_codigo = cuenta.get("codigo", "")
            cuenta_nombre = cuenta.get("nombre", "")
            
            # Si la cuenta tiene codigo "estado_paid" → Facturas Pagadas → excluir
            if cuenta_codigo == "estado_paid":
                cuenta_monto = cuenta.get("monto", 0)
                total_filtrado += cuenta_monto
                
                # Restar de concepto
                concepto["total"] = concepto.get("total", 0) - cuenta_monto
                for mes, val in cuenta.get("montos_por_mes", {}).items():
                    concepto["montos_por_mes"][mes] = concepto.get("montos_por_mes", {}).get(mes, 0) - val
                
                # Restar de operacion
                operacion_filtrada["subtotal"] = operacion_filtrada.get("subtotal", 0) - cuenta_monto
                if "subtotales_por_mes" in operacion_filtrada:
                    for mes, val in cuenta.get("montos_por_mes", {}).items():
                        operacion_filtrada["subtotales_por_mes"][mes] = operacion_filtrada["subtotales_por_mes"].get(mes, 0) - val
                
                # Poner cuenta en 0
                cuenta["monto"] = 0
                cuenta["montos_por_mes"] = {}
                
                # Poner todas las etiquetas (clientes) en 0
                for etiqueta in cuenta.get("etiquetas", []):
                    etiqueta["monto"] = 0
                    etiqueta["montos_por_mes"] = {}
                
                print(f"✅ Filtrado: cuenta '{cuenta_nombre}' (codigo: {cuenta_codigo}) -> ${cuenta_monto:,.0f}")
    
    print(f"\n📊 RESUMEN:")
    print(f"   Subtotal OPERACION original: ${operacion.get('subtotal', 0):,.0f}")
    print(f"   Total filtrado (Facturas Pagadas): ${total_filtrado:,.0f}")
    print(f"   Subtotal OPERACION después filtro: ${operacion_filtrada.get('subtotal', 0):,.0f}")
    print()


if __name__ == "__main__":
    try:
        debug_cxc_filtro()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

"""
DEBUG: Full Service Trace - Septiembre 2025
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Clear any cached imports
for mod in list(sys.modules.keys()):
    if 'flujo_caja' in mod or 'odoo_queries' in mod or 'agregador' in mod:
        del sys.modules[mod]

from backend.services.flujo_caja_service import FlujoCajaService

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DEBUG: Service Trace Sep 2025")
print("=" * 70)

# Monkey-patch agregador methods to trace calls
original_init = None
call_log = []

from backend.services.flujo_caja.agregador import AgregadorFlujo

orig_procesar_grupos = AgregadorFlujo.procesar_grupos_contrapartida
orig_procesar_etiquetas = AgregadorFlujo.procesar_etiquetas
orig_agregar_cuenta = AgregadorFlujo._agregar_cuenta
orig_procesar_lineas = AgregadorFlujo.procesar_lineas_parametrizadas

def trace_procesar_grupos(self, *args, **kwargs):
    result = orig_procesar_grupos(self, *args, **kwargs)
    if '1.1.1' in self.cuentas_por_concepto and '11030101' in self.cuentas_por_concepto['1.1.1']:
        val = self.cuentas_por_concepto['1.1.1']['11030101']['monto']
        print(f"[TRACE] POST procesar_grupos_contrapartida: 11030101={val:,.0f}")
    return result

def trace_procesar_etiquetas(self, *args, **kwargs):
    print(f"[TRACE] PRE procesar_etiquetas: grupos count={len(args[0]) if args else 0}")
    result = orig_procesar_etiquetas(self, *args, **kwargs)
    if '1.1.1' in self.cuentas_por_concepto and '11030101' in self.cuentas_por_concepto['1.1.1']:
        val = self.cuentas_por_concepto['1.1.1']['11030101']['monto']
        print(f"[TRACE] POST procesar_etiquetas: 11030101={val:,.0f}")
    return result

def trace_agregar_cuenta(self, concepto_id, codigo, display, monto, mes, account_id):
    if codigo == '11030101':
        print(f"[TRACE] _agregar_cuenta: 11030101 += {monto:,.0f} ({mes})")
    return orig_agregar_cuenta(self, concepto_id, codigo, display, monto, mes, account_id)

def trace_procesar_lineas(self, *args, **kwargs):
    print(f"[TRACE] PRE procesar_lineas_parametrizadas: lineas count={len(args[0]) if args else 0}")
    result = orig_procesar_lineas(self, *args, **kwargs)
    if '1.1.1' in self.cuentas_por_concepto and '11030101' in self.cuentas_por_concepto['1.1.1']:
        val = self.cuentas_por_concepto['1.1.1']['11030101']['monto']
        print(f"[TRACE] POST procesar_lineas_parametrizadas: 11030101={val:,.0f}")
    return result

AgregadorFlujo.procesar_grupos_contrapartida = trace_procesar_grupos
AgregadorFlujo.procesar_etiquetas = trace_procesar_etiquetas
AgregadorFlujo._agregar_cuenta = trace_agregar_cuenta
AgregadorFlujo.procesar_lineas_parametrizadas = trace_procesar_lineas

svc = FlujoCajaService(USERNAME, PASSWORD)
result = svc.get_flujo_mensualizado("2025-09-01", "2025-09-30")

print("\n" + "=" * 70)
print("FINAL RESULT:")
op = result.get('actividades', {}).get('OPERACION', {})
for c in op.get('conceptos', []):
    if c['id'] == '1.1.1':
        print(f"1.1.1 Total: ${c.get('total', 0):,.0f}")
        for cuenta in c.get('cuentas', []):
            if '11030101' in cuenta.get('codigo'):
                print(f"  11030101: ${cuenta.get('monto', 0):,.0f}")

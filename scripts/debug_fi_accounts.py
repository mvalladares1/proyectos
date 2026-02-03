"""
Debug: Ver si las cuentas de FINANCIAMIENTO tienen account_id en cuentas_por_concepto
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.flujo_caja_service import FlujoCajaService
from backend.services.flujo_caja.agregador import AgregadorFlujo
from datetime import datetime, timedelta

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

svc = FlujoCajaService(USERNAME, PASSWORD)

# Simular el proceso
fecha_inicio = '2026-01-01'
fecha_fin = '2026-02-03'
meses_lista = svc._generar_periodos(fecha_inicio, fecha_fin, 'mensual')

# Obtener cuentas de efectivo
cuentas_config = svc._get_cuentas_efectivo_config()
cuentas_efectivo_ids = svc.odoo_manager.get_cuentas_efectivo(cuentas_config)

# Obtener movimientos
movimientos, asientos_ids = svc.odoo_manager.get_movimientos_efectivo_periodo(
    fecha_inicio, fecha_fin, cuentas_efectivo_ids, None, incluir_draft=False
)

print(f"Asientos encontrados: {len(asientos_ids)}")

# Crear agregador
agregador = AgregadorFlujo(
    clasificador=svc._clasificar_cuenta,
    catalogo=svc.catalogo,
    meses_lista=meses_lista
)

# Solo CxC monitoreadas
cuentas_cxc_monitoreadas = ['11030101', '11030103']
accs = svc.odoo_manager.odoo.search_read('account.account', [['code', 'in', cuentas_cxc_monitoreadas]], ['id', 'code'])
cxc_ids = [a['id'] for a in accs]

# Query A - sin CxC
ids_excluir = list(set(cuentas_efectivo_ids + cxc_ids))
grupos = svc.odoo_manager.get_contrapartidas_agrupadas_mensual(asientos_ids, ids_excluir, 'mensual')
agregador.procesar_grupos_contrapartida(grupos, None, svc._parse_odoo_month)

# Ver cuentas por concepto para FINANCIAMIENTO
print("\n" + "=" * 80)
print("CUENTAS POR CONCEPTO (después de Query A)")
print("=" * 80)

_, cuentas_por_concepto = agregador.obtener_resultados()

# Buscar cuentas de financiamiento
cuentas_fi = ['21010102', '21010101', '21030201', '21010223', '21010201']
for concepto_id, cuentas in cuentas_por_concepto.items():
    if concepto_id and concepto_id.startswith('3'):
        for codigo, cuenta_data in cuentas.items():
            acc_id = cuenta_data.get('account_id')
            print(f"  Concepto {concepto_id}: Cuenta {codigo} -> account_id={acc_id}")

# Ver qué account_ids se van a consultar para etiquetas
account_ids_to_query = set()
for concepto_id, cuentas in cuentas_por_concepto.items():
    for codigo, cuenta_data in cuentas.items():
        acc_id = cuenta_data.get('account_id')
        if acc_id and acc_id not in cxc_ids:
            account_ids_to_query.add(acc_id)

print(f"\nAccount IDs para buscar etiquetas: {len(account_ids_to_query)}")
print(f"IDs: {sorted(list(account_ids_to_query))[:20]}...")

# Buscar las cuentas 21010102, 21010101, 21030201
cuentas_buscar = ['21010102', '21010101', '21030201']
accs_buscar = svc.odoo_manager.odoo.search_read('account.account', [['code', 'in', cuentas_buscar]], ['id', 'code'])
ids_buscar = {a['id']: a['code'] for a in accs_buscar}
print(f"\nCuentas problema: {ids_buscar}")

# Verificar si están en account_ids_to_query
for acc_id, code in ids_buscar.items():
    if acc_id in account_ids_to_query:
        print(f"  ✅ {code} (ID {acc_id}) ESTÁ en la lista de etiquetas")
    else:
        print(f"  ❌ {code} (ID {acc_id}) NO ESTÁ en la lista de etiquetas")

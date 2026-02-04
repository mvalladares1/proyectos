"""
Debug: Ver etiquetas ANTES y DESPUÉS de formatear
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.flujo_caja_service import FlujoCajaService
from backend.services.flujo_caja.agregador import AgregadorFlujo

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

svc = FlujoCajaService(USERNAME, PASSWORD)

fecha_inicio = '2026-01-01'
fecha_fin = '2026-02-03'
meses_lista = svc._generar_periodos(fecha_inicio, fecha_fin, 'mensual')

print(f"Meses lista: {meses_lista}")

# Obtener asientos
cuentas_config = svc._get_cuentas_efectivo_config()
cuentas_efectivo_ids = svc.odoo_manager.get_cuentas_efectivo(cuentas_config)
_, asientos_ids = svc.odoo_manager.get_movimientos_efectivo_periodo(
    fecha_inicio, fecha_fin, cuentas_efectivo_ids, None, incluir_draft=False
)

# Crear agregador
agregador = AgregadorFlujo(
    clasificador=svc._clasificar_cuenta,
    catalogo=svc.catalogo,
    meses_lista=meses_lista
)

# Solo CxC monitoreadas
cuentas_cxc_monitoreadas = ['11030101', '11030103']
accs_cxc = svc.odoo_manager.odoo.search_read('account.account', [['code', 'in', cuentas_cxc_monitoreadas]], ['id', 'code'])
cxc_ids = [a['id'] for a in accs_cxc]

# Query A - sin CxC
ids_excluir = list(set(cuentas_efectivo_ids + cxc_ids))
grupos = svc.odoo_manager.get_contrapartidas_agrupadas_mensual(asientos_ids, ids_excluir, 'mensual')
agregador.procesar_grupos_contrapartida(grupos, None, svc._parse_odoo_month)

# Ver estado ANTES de etiquetas
print("\n" + "=" * 80)
print("ANTES DE PROCESAR ETIQUETAS")
print("=" * 80)

_, cuentas_antes = agregador.obtener_resultados()
for concepto_id, cuentas in cuentas_antes.items():
    if concepto_id and concepto_id.startswith('3.'):
        for codigo, cuenta_data in cuentas.items():
            etiq_count = len(cuenta_data.get('etiquetas', {}))
            print(f"  {concepto_id} - {codigo}: {etiq_count} etiquetas")

# Procesar etiquetas
account_ids_to_query = set()
for concepto_id, cuentas in cuentas_antes.items():
    for codigo, cuenta_data in cuentas.items():
        acc_id = cuenta_data.get('account_id')
        if acc_id and acc_id not in cxc_ids:
            account_ids_to_query.add(acc_id)

print(f"\nProcesando etiquetas para {len(account_ids_to_query)} cuentas...")

grupos_etiquetas = svc.odoo_manager.get_etiquetas_por_mes(asientos_ids, list(account_ids_to_query), 'mensual')
print(f"Grupos etiquetas recibidos: {len(grupos_etiquetas)}")

agregador.procesar_etiquetas(grupos_etiquetas, svc._parse_odoo_month)

# Ver estado DESPUÉS de etiquetas
print("\n" + "=" * 80)
print("DESPUÉS DE PROCESAR ETIQUETAS")
print("=" * 80)

_, cuentas_despues = agregador.obtener_resultados()
for concepto_id, cuentas in cuentas_despues.items():
    if concepto_id and concepto_id.startswith('3.'):
        for codigo, cuenta_data in cuentas.items():
            etiquetas_raw = cuenta_data.get('etiquetas', {})
            print(f"\n  {concepto_id} - {codigo}: {len(etiquetas_raw)} etiquetas raw")
            for nombre, datos in list(etiquetas_raw.items())[:5]:
                if isinstance(datos, dict):
                    monto = datos.get('monto', 0)
                    montos_mes = datos.get('montos_por_mes', {})
                    print(f"      - {nombre[:40]}: monto={monto:,.0f}, meses={montos_mes}")
                else:
                    print(f"      - {nombre[:40]}: {datos}")

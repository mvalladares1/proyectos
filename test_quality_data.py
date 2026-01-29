"""
Script de prueba para verificar que los datos de calidad se capturen correctamente por tipo de fruta
"""
import sys
sys.path.append(r'c:\new\RIO FUTURO\DASHBOARD')
from shared.odoo_client import OdooClient
from dotenv import load_dotenv
import os

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 100)
print("VERIFICACIÓN DE DATOS DE CALIDAD POR TIPO DE FRUTA")
print("=" * 100)

# Buscar quality checks con CUALQUIER defecto individual registrado
qcs = odoo.search_read(
    'quality.check',
    ['|', '|', '|', '|', '|', '|', '|', 
     ('x_studio_hongos', '>', 0),
     ('x_studio_inmadura', '>', 0),
     ('x_studio_sobremadura', '>', 0),
     ('x_studio_frutos_deformes', '>', 0),
     ('x_studio_materias_extraas', '>', 0),
     ('x_studio_crumble', '>', 0),
     ('x_studio_deshidratado', '>', 0),
     ('x_studio_fruta_verde', '>', 0)],
    ['id', 'create_date', 'picking_id', 'x_studio_tipo_de_fruta', 'x_studio_calific_final', 
     'x_studio_total_def_calidad', 'x_studio_n_de_palet_o_paquete',
     'x_studio_hongos', 'x_studio_inmadura', 'x_studio_sobremadura',
     'x_studio_deshidratado', 'x_studio_crumble', 'x_studio_dao_mecanico',
     'x_studio_frutos_deformes', 'x_studio_fruta_verde', 
     'x_studio_materias_extraas', 'x_studio_temperatura'],
    order='create_date desc',
    limit=5
)

print(f"\n✅ Total de quality checks encontrados: {len(qcs)}\n")

# Agrupar por tipo de fruta
por_tipo = {}
for qc in qcs:
    tipo = qc.get('x_studio_tipo_de_fruta', 'Sin Tipo')
    if tipo not in por_tipo:
        por_tipo[tipo] = []
    por_tipo[tipo].append(qc)

print("📊 RESUMEN POR TIPO DE FRUTA:")
print("-" * 100)
for tipo, checks in por_tipo.items():
    print(f"\n🍓 {tipo}: {len(checks)} registros")
    
    # Mostrar un ejemplo
    if checks:
        ejemplo = checks[0]
        print(f"   ID: {ejemplo.get('id')}")
        print(f"   Pallet: {ejemplo.get('x_studio_n_de_palet_o_paquete', 'N/A')}")
        print(f"   Calificación: {ejemplo.get('x_studio_calific_final', 'N/A')}")
        print(f"   Total Defectos (g): {ejemplo.get('x_studio_total_def_calidad', 0)}")
        print(f"   Temperatura: {ejemplo.get('x_studio_temperatura', 'N/A')}")
        print(f"   Defectos registrados:")
        print(f"      - Hongos: {ejemplo.get('x_studio_hongos', 0)} g")
        print(f"      - Inmadura: {ejemplo.get('x_studio_inmadura', 0)} g")
        print(f"      - Sobremadura: {ejemplo.get('x_studio_sobremadura', 0)} g")
        print(f"      - Deshidratado: {ejemplo.get('x_studio_deshidratado', 0)} g")
        print(f"      - Crumble: {ejemplo.get('x_studio_crumble', 0)} g")
        print(f"      - Daño Mecánico: {ejemplo.get('x_studio_dao_mecanico', 0)} g")
        print(f"      - Deformes: {ejemplo.get('x_studio_frutos_deformes', 0)} g")
        print(f"      - Fruta Verde: {ejemplo.get('x_studio_fruta_verde', 0)} g")
        print(f"      - Materias Extrañas: {ejemplo.get('x_studio_materias_extraas', 0)} g")

print("\n" + "=" * 100)
print("✅ VERIFICACIÓN COMPLETADA")
print("=" * 100)

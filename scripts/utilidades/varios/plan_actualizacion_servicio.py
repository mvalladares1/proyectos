"""
Script para agregar la lógica de lectura de líneas one2many al servicio de defectos
"""

# Los defectos reales están en las líneas one2many, no en el quality check principal
# Modelos one2many encontrados:
# - x_quality_check_line_0d011 (Mora - tiene campos: inmadura, sobremadura, dao_por_insecto, pudricin_hongos)
# - x_quality_check_line_46726 (Frambuesa - tiene campos: frutos_inmaduros, frutos_sobre_maduros, dao_mecanico, daos_por_insectos, golpe_de_sol)

# Campos en las líneas (basado en los ejemplos):
# MORA (x_quality_check_line_0d011):
# - x_studio_inmadura
# - x_studio_sobremadura
# - x_studio_dao_por_insecto
# - x_studio_pudricin_hongos (hongos)
# - x_studio_total_defectos
# - x_studio_total_defectos_ (porcentaje)
# - x_studio_n_palet (número de pallet)
# - x_studio_fecha_y_hora
# - x_studio_temperatura
# - x_studio_muestra (gramos de muestra - 1000.0)

# FRAMBUESA (x_quality_check_line_46726):
# - x_studio_frutos_inmaduros
# - x_studio_frutos_sobre_maduros
# - x_studio_dao_mecanico
# - x_studio_daos_por_insectos
# - x_studio_golpe_de_sol
# - x_studio_total_defectos
# - x_studio_total_defectos_ (porcentaje)
# - x_studio_n_palet
# - x_studio_fecha_y_hora
# - x_studio_temperatura
# - x_studio_muestra

# Para identificar qué modelo usar, debemos ver qué campos one2many tiene el QC:
# QC tiene: x_studio_one2many_field_eNeCg (para Mora)
# QC tiene: x_studio_one2many_field_mZmK2 (para Frambuesa)

print("""
SOLUCIÓN:

1. Después de leer los quality checks, verificar si tienen campos one2many con registros
2. Para cada campo one2many con registros, buscar el modelo relacionado
3. Leer las líneas del modelo usando los IDs del campo one2many
4. Usar los defectos de las líneas en lugar de los del QC principal

Campos que deben agregarse al servicio:
- one2many_fields: Lista de todos los campos x_studio_one2many_field_*
- Función para leer líneas de calidad
- Mapeo de campos de defectos en líneas vs campos en QC principal
""")

# Mapeo de campos en líneas vs QC principal
MAPEO_CAMPOS_LINEAS = {
    # Campos comunes en las líneas
    'total_defectos_linea': ['x_studio_total_defectos'],
    'total_defectos_pct_linea': ['x_studio_total_defectos_'],
    'pallet_linea': ['x_studio_n_palet'],
    'temperatura_linea': ['x_studio_temperatura'],
    'muestra_linea': ['x_studio_muestra'],
    'fecha_hora_linea': ['x_studio_fecha_y_hora'],
    
    # Defectos - variantes según tipo de fruta
    'hongos_linea': ['x_studio_pudricin_hongos', 'x_studio_hongos'],
    'inmadura_linea': ['x_studio_inmadura', 'x_studio_frutos_inmaduros'],
    'sobremadura_linea': ['x_studio_sobremadura', 'x_studio_frutos_sobre_maduros'],
    'dano_insecto_linea': ['x_studio_dao_por_insecto', 'x_studio_daos_por_insectos'],
    'dano_mecanico_linea': ['x_studio_dao_mecanico'],
    'golpe_sol_linea': ['x_studio_golpe_de_sol'],
}

print("\nCampos one2many a buscar:")
ONE2MANY_FIELDS = [
    'x_studio_one2many_field_eNeCg',  # Mora
    'x_studio_one2many_field_mZmK2',  # Frambuesa
    'x_studio_one2many_field_3jSXq',
    'x_studio_one2many_field_0d011',
    'x_studio_one2many_field_35406',
    'x_studio_one2many_field_17bfb',
    'x_studio_one2many_field_2efd1',
    'x_studio_one2many_field_1d183',
    'x_studio_one2many_field_vloaS',
]

for field in ONE2MANY_FIELDS:
    print(f"  - {field}")

print("\nModelos relacionados:")
MODELOS_LINEAS = {
    'x_studio_one2many_field_3jSXq': 'x_quality_check_line_2a594',
    'x_studio_one2many_field_eNeCg': 'x_quality_check_line_0d011',  # Mora
    'x_studio_one2many_field_ipdDS': 'x_quality_check_line_35406',
    'x_studio_one2many_field_mZmK2': 'x_quality_check_line_46726',  # Frambuesa
    'x_studio_one2many_field_nsxt0': 'x_quality_check_line_17bfb',
    'x_studio_one2many_field_RdQtm': 'x_quality_check_line_2efd1',
    'x_studio_one2many_field_rgA7I': 'x_quality_check_line_1d183',
    'x_studio_one2many_field_vloaS': 'x_quality_check_line_f0f7b',
}

for field, model in MODELOS_LINEAS.items():
    print(f"  {field} → {model}")

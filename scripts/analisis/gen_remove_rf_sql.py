"""Genera SQL para remover overrides incorrectos (recepciones RF reales)"""

# Leer los pickings a remover
with open(r'c:\new\RIO FUTURO\DASHBOARD\proyectos\output\pallets_rf_to_remove_override.txt', 'r') as f:
    pickings = [line.strip() for line in f if line.strip()]

print(f'Total pickings a remover: {len(pickings)}')

# Generar SQL DELETE
sql_lines = []
for p in pickings:
    safe = p.replace("'", "''")
    sql_lines.append(f"DELETE FROM override_origen WHERE picking_name = '{safe}';")

sql_path = r'c:\new\RIO FUTURO\DASHBOARD\proyectos\output\remove_rf_overrides.sql'
with open(sql_path, 'w') as f:
    f.write('\n'.join(sql_lines))

print(f'SQL guardado: {sql_path}')
print('Primeras 5 líneas:')
for l in sql_lines[:5]:
    print(f'  {l}')

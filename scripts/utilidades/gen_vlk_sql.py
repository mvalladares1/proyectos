"""Genera SQL para overrides VLK"""
import pandas as pd

EXCEL_PATH = r'c:\new\RIO FUTURO\DASHBOARD\proyectos\output\forense_tunel_vlk_v2_20260226_113419.xlsx'
SQL_PATH = r'c:\new\RIO FUTURO\DASHBOARD\proyectos\output\vlk_overrides.sql'

df = pd.read_excel(EXCEL_PATH, sheet_name='Recepciones Unicas')
pickings = df['Albaran'].dropna().unique().tolist()
pickings_rf = [p for p in pickings if p.startswith('RF/RFP/')]
print(f'Total a cargar: {len(pickings_rf)}')

sql_lines = []
for p in pickings_rf:
    safe = p.replace("'", "''")
    sql_lines.append(f"INSERT OR REPLACE INTO override_origen (picking_name, origen, created_at) VALUES ('{safe}', 'VILKUN', datetime('now'));")

with open(SQL_PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(sql_lines))

print(f'SQL guardado: {SQL_PATH}')
print('Primeras 5 líneas:')
for l in sql_lines[:5]:
    print(f'  {l}')

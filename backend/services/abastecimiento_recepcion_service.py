import pandas as pd
import numpy as np

def get_control_presupuestario_data(po_data, budget_data):
    if po_data.empty and budget_data.empty:
        return pd.DataFrame()
    if not po_data.empty:
        real_df = po_data.copy()
        labeling_map = {'CONV': 'CONVENCIONAL', 'ORG': 'ORGANICO'}
        real_df['MANEJO'] = real_df['labeling'].map(labeling_map).fillna(real_df['labeling']).fillna('OTRO')
        real_df['ESTADO'] = real_df['condition'].fillna('SIN ESTADO')
        fruta_map = {'AR': 'ARANDANO', 'FB': 'FRAMBUESA', 'MO': 'MORA', 'FR': 'FRUTILLA', 'CR': 'CEREZA'}
        real_df['FRUTA'] = real_df['product'].map(fruta_map).fillna('OTRO')
        real_agg = real_df.groupby(['ESTADO', 'FRUTA', 'MANEJO'])['qty_received'].sum().reset_index()
        real_agg = real_agg.rename(columns={'qty_received': 'Recepción'})
    else:
        real_agg = pd.DataFrame(columns=['ESTADO', 'FRUTA', 'MANEJO', 'Recepción'])
    if not budget_data.empty:
        budget_df = budget_data.copy()
        if 'PRODUCTO' in budget_df.columns:
            budget_df = budget_df.rename(columns={'PRODUCTO': 'FRUTA'})
        if 'FRUTA' in budget_df.columns:
            budget_df['FRUTA'] = budget_df['FRUTA'].astype(str).str.upper()
            budget_df['FRUTA'] = budget_df['FRUTA'].str.replace('Á','A').str.replace('É','E').str.replace('Í','I').str.replace('Ó','O').str.replace('Ú','U')
        if 'ESTADO' in budget_df.columns:
            budget_df['ESTADO'] = budget_df['ESTADO'].astype(str).str.upper()
        if 'MANEJO' in budget_df.columns:
            budget_df['MANEJO'] = budget_df['MANEJO'].astype(str).str.upper()
            budget_df['MANEJO'] = budget_df['MANEJO'].replace({'CONV':'CONVENCIONAL','ORG':'ORGANICO'})
        ppto_col = 'PPTO 3' if 'PPTO 3' in budget_df.columns else 'PPTO'
        budget_agg = budget_df.groupby(['ESTADO', 'FRUTA', 'MANEJO'])[ppto_col].sum().reset_index()
        budget_agg = budget_agg.rename(columns={ppto_col: 'PPTO 3'})
    else:
        budget_agg = pd.DataFrame(columns=['ESTADO','FRUTA','MANEJO','PPTO 3'])
    merged = pd.merge(real_agg, budget_agg, on=['ESTADO','FRUTA','MANEJO'], how='outer').fillna(0)
    merged = merged[merged['ESTADO'] != 'SIN ESTADO']
    if merged.empty:
        return pd.DataFrame()
    pivot = merged.pivot(index=['ESTADO','FRUTA'], columns='MANEJO', values=['Recepción','PPTO 3'])
    final_df = pd.DataFrame(index=pivot.index)
    def calc_pct(rec, ppto):
        return (rec / ppto * 100) if ppto > 0 else 0
    final_df[('CONVENCIONAL','Recepción')] = pivot.get(('Recepción','CONVENCIONAL'), pd.Series(0,index=pivot.index))
    final_df[('CONVENCIONAL','PPTO 3')] = pivot.get(('PPTO 3','CONVENCIONAL'), pd.Series(0,index=pivot.index))
    final_df[('CONVENCIONAL','%')] = final_df.apply(lambda r: calc_pct(r[('CONVENCIONAL','Recepción')], r[('CONVENCIONAL','PPTO 3')]), axis=1)
    final_df[('ORGANICO','Recepción')] = pivot.get(('Recepción','ORGANICO'), pd.Series(0,index=pivot.index))
    final_df[('ORGANICO','PPTO 3')] = pivot.get(('PPTO 3','ORGANICO'), pd.Series(0,index=pivot.index))
    final_df[('ORGANICO','%')] = final_df.apply(lambda r: calc_pct(r[('ORGANICO','Recepción')], r[('ORGANICO','PPTO 3')]), axis=1)
    final_df[('Total','Recepción')] = final_df[('CONVENCIONAL','Recepción')] + final_df[('ORGANICO','Recepción')]
    final_df[('Total','PPTO 3')] = final_df[('CONVENCIONAL','PPTO 3')] + final_df[('ORGANICO','PPTO 3')]
    final_df[('Total','%')] = final_df.apply(lambda r: calc_pct(r[('Total','Recepción')], r[('Total','PPTO 3')]), axis=1)
    subtotals = final_df.groupby(level=0).sum()
    for manejo in ['CONVENCIONAL','ORGANICO','Total']:
        rec = subtotals[(manejo,'Recepción')]
        ppto = subtotals[(manejo,'PPTO 3')]
        subtotals[(manejo,'%')] = np.where(ppto>0,(rec/ppto)*100,0)
    total_row = subtotals.sum()
    for manejo in ['CONVENCIONAL','ORGANICO','Total']:
        rec = total_row[(manejo,'Recepción')]
        ppto = total_row[(manejo,'PPTO 3')]
        total_row[(manejo,'%')] = (rec / ppto * 100) if ppto > 0 else 0
    subtotals.index = pd.MultiIndex.from_tuples([(est,'') for est in subtotals.index], names=['ESTADO','FRUTA'])
    final_df = pd.concat([final_df, subtotals])
    final_df = final_df.sort_index(level=[0,1], ascending=[False,True])
    final_df.loc[('Total',''),:] = total_row
    final_df.columns = pd.MultiIndex.from_tuples([(a,b) for a,b in final_df.columns])
    return final_df

def calculate_weighted_average_price(df, price_col='price_unit', qty_col='qty_received', currency_col='currency_name', date_col='date_planned', central_bank_data=None):
    if df.empty:
        return 0.0, 0.0
    temp_df = df.copy()
    if date_col in temp_df.columns:
        temp_df[date_col] = pd.to_datetime(temp_df[date_col])
        temp_df['date_only'] = temp_df[date_col].dt.normalize()
    else:
        temp_df['date_only'] = pd.Timestamp.now().normalize()
    if central_bank_data is not None and not central_bank_data.empty:
        cb_df = central_bank_data.copy()
        cb_df['indexDateString'] = pd.to_datetime(cb_df['indexDateString']).dt.normalize()
        cb_df = cb_df.rename(columns={'indexDateString': 'date_only', 'value': 'usd_rate'})
        cb_df = cb_df[['date_only', 'usd_rate']]
        temp_df = pd.merge(temp_df, cb_df, on='date_only', how='left')
        mean_rate = cb_df['usd_rate'].mean() if not cb_df.empty else 900
        temp_df['usd_rate'] = temp_df['usd_rate'].fillna(mean_rate)
    else:
        temp_df['usd_rate'] = 900
    if currency_col not in temp_df.columns:
        if 'currency_id' in temp_df.columns:
             temp_df[currency_col] = temp_df['currency_id'].apply(lambda x: x[1] if isinstance(x, (list, tuple)) and len(x) > 1 else str(x))
        else:
             temp_df[currency_col] = 'CLP'
    def convert_to_usd(row):
        price = row[price_col]
        curr = str(row[currency_col]).upper()
        if 'CLP' in curr or 'PESO' in curr:
            return price / row['usd_rate'] if row['usd_rate'] > 0 else 0
        return price
    temp_df['price_usd'] = temp_df.apply(convert_to_usd, axis=1)
    total_val_usd = (temp_df['price_usd'] * temp_df[qty_col]).sum()
    total_qty = temp_df[qty_col].sum()
    pmp_usd = total_val_usd / total_qty if total_qty > 0 else 0
    return pmp_usd, total_qty

def calculate_raw_pmp(df, price_col='price_unit', qty_col='qty_received'):
    if df.empty:
        return 0.0, 0.0
    df_nonzero = df[df[price_col] > 0]
    if df_nonzero.empty:
        return 0.0, 0.0
    total_val = (df_nonzero[price_col] * df_nonzero[qty_col]).sum()
    total_qty = df_nonzero[qty_col].sum()
    pmp = total_val / total_qty if total_qty > 0 else 0
    return pmp, total_qty

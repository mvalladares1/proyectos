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


def get_stacked_evolution_data(po_data, budget_data, granularity='Semanal'):
    """
    Prepares data for the Stacked Evolution Chart (Real by Fruit vs PPTO).
    Returns a dictionary with:
    - 'real_stacked': DataFrame [Date, FRUTA, Real]
    - 'ppto_stacked': DataFrame [Date, FRUTA, v.2] (PPTO 3 stacked by fruit)
    - 'ppto_total': DataFrame [Date, PPTO Original] (Total PPTO Original)
    """
    if po_data.empty:
        return {'real_stacked': pd.DataFrame(), 'ppto_stacked': pd.DataFrame(), 'ppto_total': pd.DataFrame()}
        
    # --- Real Data (Stacked by Fruit) ---
    df = po_data.copy()
    df['date_planned'] = pd.to_datetime(df['date_planned'])
    
    # Map Product Code to Fruit Name
    fruta_map = {
        'AR': 'ARANDANO',
        'FB': 'FRAMBUESA',
        'MO': 'MORA',
        'FR': 'FRUTILLA',
        'CR': 'CEREZA'
    }
    # If 'product' column exists (it should)
    if 'product' in df.columns:
        df['FRUTA'] = df['product'].map(fruta_map).fillna('OTRO')
    else:
        df['FRUTA'] = 'OTRO'
    
    if granularity == 'Diario':
        df['Date'] = df['date_planned'].dt.date
    else:
        # Normalize to start of week (Monday)
        df['Date'] = df['date_planned'] - pd.to_timedelta(df['date_planned'].dt.weekday, unit='D')
        df['Date'] = df['Date'].dt.date
    
    # Group by Date AND Fruit
    real_agg = df.groupby(['Date', 'FRUTA'])['qty_received'].sum().reset_index()
    real_agg = real_agg.rename(columns={'qty_received': 'Real'})
    
    # --- Budget Data ---
    if not budget_data.empty and ('FECHAS MOD' in budget_data.columns or 'MES' in budget_data.columns):
        b_df = budget_data.copy()
        date_col = 'FECHAS MOD' if 'FECHAS MOD' in b_df.columns else 'MES'
        b_df[date_col] = pd.to_datetime(b_df[date_col])
        
        if granularity == 'Diario':
            b_df['Date'] = b_df[date_col].dt.date
        else:
            b_df['Date'] = b_df[date_col] - pd.to_timedelta(b_df[date_col].dt.weekday, unit='D')
            b_df['Date'] = b_df['Date'].dt.date
            
        # Normalize FRUTA in Budget
        if 'PRODUCTO' in b_df.columns:
            b_df = b_df.rename(columns={'PRODUCTO': 'FRUTA'})
            
        if 'FRUTA' in b_df.columns:
            b_df['FRUTA'] = b_df['FRUTA'].astype(str).str.upper()
            b_df['FRUTA'] = b_df['FRUTA'].apply(lambda x: 'ARANDANO' if 'AR' in x and 'NDANO' in x else x)
            b_df['FRUTA'] = b_df['FRUTA'].str.replace('Á', 'A').str.replace('É', 'E').str.replace('Í', 'I').str.replace('Ó', 'O').str.replace('Ú', 'U')
        else:
            b_df['FRUTA'] = 'OTRO'

        # Ensure columns exist
        if 'PPTO' not in b_df.columns: b_df['PPTO'] = 0
        if 'PPTO 3' not in b_df.columns: b_df['PPTO 3'] = 0
        
        # 1. PPTO Original (Total)
        ppto_total_agg = b_df.groupby('Date')['PPTO'].sum().reset_index()
        ppto_total_agg = ppto_total_agg.rename(columns={'PPTO': 'PPTO Original'})
        
        # 2. PPTO 3 (Stacked by Fruit) -> v.2
        ppto_stacked_agg = b_df.groupby(['Date', 'FRUTA'])['PPTO 3'].sum().reset_index()
        ppto_stacked_agg = ppto_stacked_agg.rename(columns={'PPTO 3': 'v.2'})
        
    else:
        ppto_total_agg = pd.DataFrame(columns=['Date', 'PPTO Original'])
        ppto_stacked_agg = pd.DataFrame(columns=['Date', 'FRUTA', 'v.2'])
        
    # --- Filter Significant Dates ---
    # Calculate Total Real per date
    real_totals = real_agg.groupby('Date')['Real'].sum()
    valid_real_dates = real_totals[real_totals > 1].index
    
    valid_ppto_dates = pd.Index([])
    if not ppto_total_agg.empty:
        valid_ppto_dates = ppto_total_agg[ppto_total_agg['PPTO Original'] > 1]['Date']
        
    valid_dates = valid_real_dates.union(valid_ppto_dates).unique()
    
    # Filter
    real_agg = real_agg[real_agg['Date'].isin(valid_dates)]
    ppto_total_agg = ppto_total_agg[ppto_total_agg['Date'].isin(valid_dates)]
    ppto_stacked_agg = ppto_stacked_agg[ppto_stacked_agg['Date'].isin(valid_dates)]
    
    # Sort
    real_agg = real_agg.sort_values(['Date', 'FRUTA'])
    ppto_total_agg = ppto_total_agg.sort_values('Date')
    ppto_stacked_agg = ppto_stacked_agg.sort_values(['Date', 'FRUTA'])
    
    return {
        'real_stacked': real_agg,
        'ppto_stacked': ppto_stacked_agg,
        'ppto_total': ppto_total_agg
    }

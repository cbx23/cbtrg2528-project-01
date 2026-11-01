"""Inventory analytics. Demand periods must be calendar months."""
from io import BytesIO
from statistics import NormalDist

import numpy as np
import pandas as pd

REQUIRED = ['sku', 'date', 'demand', 'unit_cost', 'lead_time_days']


def validate_data(frame):
    missing = set(REQUIRED) - set(frame.columns)
    if missing:
        raise ValueError('Coloane lipsă: ' + ', '.join(sorted(missing)))
    df = frame.copy()
    if df.empty:
        raise ValueError('Fișierul nu conține date.')
    if df['sku'].isna().any() or df['sku'].astype(str).str.strip().eq('').any():
        raise ValueError('SKU nu poate fi gol.')
    df['sku'] = df['sku'].astype(str).str.strip()
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    if df['date'].isna().any():
        raise ValueError('Date invalide. Folosește formatul YYYY-MM-DD.')
    for column in REQUIRED[2:] + (['forecast'] if 'forecast' in df else []):
        df[column] = pd.to_numeric(df[column], errors='coerce')
        if df[column].isna().any() or not np.isfinite(df[column]).all() or (df[column] < 0).any():
            raise ValueError(f'{column} trebuie să conțină numere finite, pozitive sau zero.')
    df['month'] = df['date'].dt.to_period('M')
    if df.duplicated(['sku', 'month']).any():
        raise ValueError('Este permis un singur rând per SKU și lună.')
    for sku, group in df.groupby('sku'):
        expected = pd.period_range(group['month'].min(), group['month'].max(), freq='M')
        if len(expected) != len(group):
            raise ValueError(f'{sku}: lipsesc luni. Adaugă explicit cerere zero dacă nu au existat vânzări.')
        if group['unit_cost'].nunique() != 1 or group['lead_time_days'].nunique() != 1:
            raise ValueError(f'{sku}: costul și lead time trebuie să fie constante în interval.')
    return df.sort_values(['sku', 'date']).reset_index(drop=True)


def analyze(frame, service_level=0.95, abc_a=0.80, abc_b=0.95, xyz_x=0.50, xyz_y=1.0):
    if not 0.5 < service_level < 1:
        raise ValueError('Nivelul de serviciu trebuie să fie între 50% și 100%.')
    if not 0 < abc_a < abc_b < 1 or not 0 <= xyz_x < xyz_y:
        raise ValueError('Praguri de clasificare invalide.')
    df = validate_data(frame)
    rows = []
    z = NormalDist().inv_cdf(service_level)
    for sku, g in df.groupby('sku'):
        mean = g.demand.mean()
        std = g.demand.std(ddof=1) if len(g) >= 2 else np.nan
        cv = std / mean if mean > 0 else np.nan
        lead = g.lead_time_days.iloc[0]
        safety = z * std * np.sqrt(lead / 30)
        row = dict(sku=sku, periods=len(g), total_demand=g.demand.sum(),
                   mean_monthly_demand=mean, std_monthly_demand=std, cv=cv,
                   unit_cost=g.unit_cost.iloc[0], lead_time_days=lead,
                   consumption_value=g.demand.sum() * g.unit_cost.iloc[0],
                   xyz=('N/A' if not np.isfinite(cv) else 'X' if cv <= xyz_x else 'Y' if cv <= xyz_y else 'Z'),
                   safety_stock=safety, reorder_point=mean * lead / 30 + safety)
        if 'forecast' in g:
            error = g.forecast - g.demand
            nonzero = g.demand > 0
            row.update(mae=error.abs().mean(), rmse=np.sqrt((error ** 2).mean()),
                       mape_pct=((error[nonzero].abs() / g.demand[nonzero]).mean() * 100 if nonzero.any() else np.nan),
                       wape_pct=(error.abs().sum() / g.demand.sum() * 100 if g.demand.sum() else np.nan),
                       bias_units=error.mean(), mape_periods=int(nonzero.sum()))
        rows.append(row)
    result = pd.DataFrame(rows).sort_values(['consumption_value', 'sku'], ascending=[False, True]).reset_index(drop=True)
    total = result.consumption_value.sum()
    result['value_share'] = result.consumption_value / total if total else 0.0
    result['cumulative_share'] = result.value_share.cumsum()
    # Assign crossing SKU to the class whose interval it starts in.
    before = result.cumulative_share - result.value_share
    result['abc'] = np.where(result.consumption_value.eq(0), 'N/A', np.where(before < abc_a, 'A', np.where(before < abc_b, 'B', 'C')))
    result['segment'] = result.abc + '-' + result.xyz
    return result


def excel_report(frame, result, parameters=None):
    output = BytesIO()
    raw = frame.copy()
    for col in raw.select_dtypes(include=['object', 'string']).columns:
        raw[col] = raw[col].map(lambda v: "'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v)
    safe_result = result.copy()
    safe_result['sku'] = safe_result.sku.map(lambda v: "'" + v if v.startswith(('=', '+', '-', '@')) else v)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        raw.to_excel(writer, sheet_name='Date sursa', index=False)
        safe_result.to_excel(writer, sheet_name='Analiza SKU', index=False)
        result.groupby(['abc', 'xyz']).agg(sku_count=('sku', 'count'), consumption_value=('consumption_value', 'sum')).reset_index().to_excel(writer, sheet_name='Matrice ABC XYZ', index=False)
        pd.DataFrame(list((parameters or {}).items()), columns=['Parametru', 'Valoare']).to_excel(writer, sheet_name='Parametri', index=False)
        for sheet in writer.book.worksheets:
            sheet.freeze_panes = 'A2'
            sheet.auto_filter.ref = sheet.dimensions
            for cells in sheet.columns:
                sheet.column_dimensions[cells[0].column_letter].width = min(36, max(14, max(len(str(c.value or '')) for c in cells) + 2))
    return output.getvalue()

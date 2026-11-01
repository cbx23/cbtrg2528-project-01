from pathlib import Path

import pandas as pd
import streamlit as st

from supply_chain.analytics import analyze, excel_report

st.set_page_config(page_title='Supply Chain Analytics', page_icon='📦', layout='wide')
st.title('📦 Supply Chain Analytics')
st.caption('Decizii de stoc bazate pe valoare, variabilitate și performanța prognozelor.')
with st.sidebar:
    st.header('Configurare')
    upload = st.file_uploader('Încarcă CSV sau Excel', type=['csv', 'xlsx'])
    demo = st.checkbox('Folosește date demonstrative', value=True)
    service = st.slider('Nivel de serviciu (%)', 80.0, 99.9, 95.0, 0.1)
    st.subheader('Praguri ABC (cotă cumulată)')
    a = st.number_input('A (%)', 1, 98, 80)
    b = st.number_input('B (%)', 2, 99, 95)
    st.subheader('Praguri XYZ (coeficient de variație)')
    x = st.number_input('X ≤', min_value=0.0, value=0.5, step=0.1)
    y = st.number_input('Y ≤', min_value=0.1, value=1.0, step=0.1)
    st.download_button('Descarcă model CSV', Path('data/demo.csv').read_bytes(), 'model_stocuri.csv', 'text/csv')

with st.expander('Formatul datelor și metodologia'):
    st.markdown('''Un rând per **SKU și lună**, cu coloanele `sku`, `date` (YYYY-MM-DD), `demand`, `unit_cost`, `lead_time_days` și opțional `forecast`. Cererea și prognoza sunt cantități lunare; costul și lead time sunt constante per SKU. Lunile fără cerere trebuie introduse explicit cu zero. Compară SKU-uri pe aceeași perioadă pentru o clasificare ABC relevantă.

**ABC:** valoarea consumului = cerere totală × cost unitar; SKU-ul care traversează un prag rămâne în clasa începută. Valoarea zero primește N/A. **XYZ:** deviația standard eșantion / media cererii; sub două luni sau medie zero → N/A.

**Safety stock:** z × σ lunar × √(lead time / 30). **Reorder point:** media lunară × lead time / 30 + safety stock. Se presupun luni de 30 zile, cerere independentă cu distribuție aproximativ normală și lead time fix; nivelul de serviciu este probabilitatea de a evita ruptura într-un ciclu. Rezultatele sunt estimări, în unități; un singur punct de date nu permite estimarea variației.

**Forecast:** MAE, RMSE, MAPE (exclude lunile cu cerere zero), WAPE și bias mediu (prognoză − realizat; pozitiv = supraestimare). WAPE/MAPE sunt N/A când numitorul este zero. Erorile procentuale pot depăși 100%.''')
try:
    if upload:
        frame = pd.read_csv(upload, dtype={'sku': str}) if upload.name.endswith('.csv') else pd.read_excel(upload, dtype={'sku': str})
    elif demo:
        frame = pd.read_csv('data/demo.csv', dtype={'sku': str})
    else:
        st.info('Încarcă un fișier sau activează datele demonstrative.')
        st.stop()
    parameters = dict(service_level=service / 100, abc_a=a / 100, abc_b=b / 100, xyz_x=x, xyz_y=y)
    result = analyze(frame, **parameters)
    periods = pd.to_datetime(frame.date).dt.to_period('M').groupby(frame.sku).agg(['min', 'max', 'count'])
    if len(periods.drop_duplicates()) > 1:
        st.warning('SKU-urile au intervale de observație diferite; valorile ABC nu sunt direct comparabile.')
    c1, c2, c3 = st.columns(3)
    c1.metric('SKU analizate', len(result))
    c2.metric('Valoare consum (moneda sursei)', f'{result.consumption_value.sum():,.2f}')
    c3.metric('Stoc de siguranță estimat (unități)', f'{result.safety_stock.sum(min_count=1):,.1f}')
    overview, stock, forecast, source = st.tabs(['ABC–XYZ', 'Safety stock', 'Forecast accuracy', 'Date sursă'])
    with overview:
        st.subheader('Distribuția portofoliului')
        st.dataframe(pd.crosstab(result.abc, result.xyz), width='stretch')
        st.bar_chart(result.groupby('abc').consumption_value.sum())
        st.dataframe(result[['sku', 'consumption_value', 'value_share', 'cumulative_share', 'cv', 'abc', 'xyz', 'segment']], width='stretch', hide_index=True)
    with stock:
        st.dataframe(result[['sku', 'periods', 'mean_monthly_demand', 'std_monthly_demand', 'lead_time_days', 'safety_stock', 'reorder_point']], width='stretch', hide_index=True)
        st.caption('N/A indică istoric insuficient. Rotunjește cantitățile în funcție de ambalaj și politica de comandă.')
    with forecast:
        if 'forecast' in frame:
            st.dataframe(result[['sku', 'mae', 'rmse', 'mape_pct', 'wape_pct', 'bias_units', 'mape_periods']], width='stretch', hide_index=True)
            sku = st.selectbox('Evoluție SKU', result.sku)
            st.line_chart(frame[frame.sku == sku].sort_values('date').set_index('date')[['demand', 'forecast']])
        else:
            st.info('Adaugă coloana forecast pentru evaluarea prognozelor.')
    with source:
        st.dataframe(frame, width='stretch', hide_index=True)
    st.download_button('⬇ Descarcă raport Excel', excel_report(frame, result, parameters), 'supply_chain_report.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
except (ValueError, TypeError, KeyError, OSError) as error:
    st.error(f'Datele nu au putut fi analizate: {error}')

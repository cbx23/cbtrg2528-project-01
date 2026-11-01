import unittest
from io import BytesIO
from statistics import NormalDist

import pandas as pd
from openpyxl import load_workbook

from supply_chain.analytics import analyze, excel_report


def sample(demand=(80, 120), forecast=(100, 100)):
    return pd.DataFrame(dict(sku=['A'] * len(demand), date=pd.date_range('2025-01-01', periods=len(demand), freq='MS'), demand=demand, forecast=forecast, unit_cost=10, lead_time_days=30))


class AnalyticsTests(unittest.TestCase):
    def test_safety_and_forecast(self):
        r = analyze(sample()).iloc[0]
        self.assertAlmostEqual(r.safety_stock, NormalDist().inv_cdf(.95) * (800 ** .5))
        self.assertAlmostEqual(r.reorder_point, 100 + r.safety_stock)
        self.assertEqual(r.mae, 20)
        self.assertEqual(r.rmse, 20)
        self.assertEqual(r.wape_pct, 20)
        self.assertEqual(r.bias_units, 0)
        self.assertAlmostEqual(r.mape_pct, (20 / 80 + 20 / 120) * 50)
        self.assertEqual(r.xyz, 'X')

    def test_zero_and_short_history(self):
        r = analyze(sample((0, 0), (10, 10))).iloc[0]
        self.assertTrue(pd.isna(r.wape_pct))
        self.assertTrue(pd.isna(r.mape_pct))
        self.assertEqual(r.abc, 'N/A')
        self.assertEqual(r.xyz, 'N/A')
        self.assertTrue(pd.isna(analyze(sample((10,), (10,))).iloc[0].safety_stock))

    def test_invalid_inputs(self):
        for column, value in [('demand', -1), ('forecast', float('inf')), ('date', 'bad'), ('sku', '')]:
            df = sample(); df[column] = value
            with self.assertRaises(ValueError): analyze(df)
        df = sample(); df['date'] = ['2025-01-01', '2025-03-01']
        with self.assertRaises(ValueError): analyze(df)
        with self.assertRaises(ValueError): analyze(pd.concat([sample(), sample()]))
        with self.assertRaises(ValueError): analyze(sample(), abc_a=.95, abc_b=.8)

    def test_abc_crossing(self):
        df = pd.concat([sample().assign(sku=s, unit_cost=c) for s,c in [('A',81),('B',15),('C',4)]])
        self.assertEqual(analyze(df).abc.tolist(), ['A', 'B', 'C'])

    def test_excel(self):
        df = sample().assign(sku='=1+1')
        book = load_workbook(BytesIO(excel_report(df, analyze(df), {'service': .95})))
        self.assertEqual(len(book.sheetnames), 4)
        self.assertEqual(book['Date sursa']['A2'].data_type, 's')
        self.assertEqual(book['Analiza SKU'].max_row, 2)


if __name__ == '__main__':
    unittest.main()

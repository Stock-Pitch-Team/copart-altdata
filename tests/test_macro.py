import unittest
import pandas as pd
from src.collect.macro import add_calendar_yoy

class CalendarYoyTests(unittest.TestCase):
    def test_gap_does_not_shift_comparison_month(self):
        dates = pd.date_range('2024-01-01', '2025-03-01', freq='MS')
        frame = pd.DataFrame({'series': 'repair', 'date': dates.strftime('%Y-%m-%d'), 'value': [100 + i for i in range(len(dates))]})
        frame = frame[frame.date != '2024-10-01']
        result = add_calendar_yoy(frame).set_index('date')
        self.assertAlmostEqual(result.loc['2025-03-01', 'value_yoy_pct'], round((114 / 102 - 1) * 100, 2))

    def test_missing_previous_year_is_not_filled(self):
        frame = pd.DataFrame({'series': ['repair'] * 3, 'date': ['2024-02-01', '2024-04-01', '2025-03-01'], 'value': [100, 110, 120]})
        self.assertTrue(pd.isna(add_calendar_yoy(frame).iloc[-1].value_yoy_pct))

    def test_series_are_matched_independently(self):
        frame = pd.DataFrame({'series': ['repair', 'used', 'repair', 'used'], 'date': ['2024-03-01'] * 2 + ['2025-03-01'] * 2, 'value': [100, 200, 110, 180]})
        self.assertEqual(add_calendar_yoy(frame).value_yoy_pct.tail(2).tolist(), [10.0, -10.0])

if __name__ == '__main__':
    unittest.main()

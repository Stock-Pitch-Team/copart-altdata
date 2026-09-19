import unittest
import pandas as pd
import numpy as np
from src.build.tlf_backtest import backtest

class BacktestTests(unittest.TestCase):
    def inputs(self):
        return pd.DataFrame({'quarter_end':pd.date_range('2010-03-31',periods=28,freq='QE'),'scissors':np.sin(np.arange(28)),'total_loss_frequency':20+np.arange(28)*0.1})
    def test_future_actuals_cannot_change_prior_predictions(self):
        a=self.inputs();before=backtest(a);a.loc[25:,'total_loss_frequency']=999;after=backtest(a)
        cutoff=a.quarter_end.iloc[25].strftime('%Y-%m-%d')
        pd.testing.assert_frame_equal(before[before.quarter_end<cutoff],after[after.quarter_end<cutoff])
    def test_target_cpi_not_used_and_same_test_quarters(self):
        a=self.inputs();before=backtest(a);a.loc[27,'scissors']=999;after=backtest(a)
        pd.testing.assert_frame_equal(before,after)
        self.assertTrue((pd.to_datetime(before.last_training_actual)<pd.to_datetime(before.forecast_origin)).all())
        self.assertEqual(before.groupby('model').size().nunique(),1)

if __name__=='__main__':unittest.main()

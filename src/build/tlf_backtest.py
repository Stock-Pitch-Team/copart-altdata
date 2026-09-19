"""Expanding-window, pseudo-out-of-sample validation using current data vintages.

Forecast at the start of each target quarter. Assume actual TLF is available
only through two quarters before target (one-quarter publication delay).
Use CPI from completed prior quarters, never contemporaneous target CPI.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from src.build.tlf_nowcast import load_inputs
from src.common import write_dataset


def backtest(inputs: pd.DataFrame, min_train: int = 12) -> pd.DataFrame:
    d = inputs.copy().sort_values('quarter_end').set_index('quarter_end')
    d = d.reindex(pd.date_range(d.index.min(), d.index.max(), freq='QE'))
    d.index.name = 'quarter_end'
    d['trend'] = (d.index - d.index.min()).days / 365.25
    for lag in (1, 2, 3):
        d[f'lag{lag}'] = d.scissors.shift(lag)
    rows = []
    for i in range(2, len(d)):
        target = d.iloc[i]
        if pd.isna(target.total_loss_frequency) or target[['lag1','lag2','lag3']].isna().any():
            continue
        # Exclude previous-quarter TLF: it may not yet have been released.
        train = d.iloc[:i-1].dropna(subset=['total_loss_frequency','lag1','lag2','lag3'])
        if len(train) < min_train:
            continue
        y = train.total_loss_frequency.to_numpy()
        candidates = []
        for lag in (1, 2, 3):
            X = np.column_stack([np.ones(len(train)), train.trend, train[f'lag{lag}']])
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            # Same observations and parameter count for each candidate.
            mse = np.mean((y-X@beta)**2)
            pred = float(np.array([1,target.trend,target[f'lag{lag}']])@beta)
            candidates.append((mse,lag,pred))
        _, chosen, pred = min(candidates)
        X = np.column_stack([np.ones(len(train)), train.trend])
        beta = np.linalg.lstsq(X,y,rcond=None)[0]
        trend_pred = float(np.array([1,target.trend])@beta)
        available = d.iloc[:i-1].dropna(subset=['total_loss_frequency'])
        predictions = [('Spread + trend',pred,chosen),('Trend only',trend_pred,0),('Last available actual',float(available.total_loss_frequency.iloc[-1]),0)]
        for model, prediction, lag in predictions:
            rows.append(dict(quarter_end=d.index[i].strftime('%Y-%m-%d'),forecast_origin=d.index[i-1].strftime('%Y-%m-%d'),last_training_actual=train.index.max().strftime('%Y-%m-%d'),model=model,n_train=len(train),selected_lag=lag,actual=float(target.total_loss_frequency),prediction=prediction,error=prediction-float(target.total_loss_frequency)))
    return pd.DataFrame(rows)


def main() -> int:
    inputs = load_inputs()
    if inputs is None:
        return 1
    predictions = backtest(inputs)
    if predictions.empty:
        raise ValueError('Not enough observations for validation')
    summary = predictions.groupby('model',sort=False).apply(lambda g: pd.Series({'n_test':len(g),'mae':g.error.abs().mean(),'rmse':np.sqrt((g.error**2).mean()),'bias':g.error.mean()}),include_groups=False).reset_index()
    meta = dict(source='Local CCC manual panel and BLS CPI; current dataset vintages.',method='Expanding window with at least 12 training observations. Assume a one-quarter TLF publication delay: target Q trains through Q-2. CPI lags 1-3 only. Re-select lag using training error on identical training rows at each origin. Compare with trend-only and last available actual on identical target quarters.',gaps='Pseudo-out-of-sample, not a real-time vintage backtest. CPI revisions and historical CCC publication dates are unavailable. Quarterly means can have missing months. Lag zero from the original in-sample search is excluded because target-quarter CPI would be unavailable at this forecast origin. Small test sample, overlapping training windows and mixed CCC definitions limit conclusions.',units='percentage points for errors; percent for TLF',frequency='quarterly')
    write_dataset(predictions,'tlf_backtest',**meta)
    write_dataset(summary,'tlf_backtest_summary',**meta)
    print(summary.to_string(index=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

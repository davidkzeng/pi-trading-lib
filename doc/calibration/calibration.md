# Investigate whether PredictIt markets are well calibrated

## Academic Research Prior Work

Existing work on whether prediction markets are well calibrated.

[DO PREDICTION MARKETS PRODUCE WELL-CALIBRATED PROBABILITY FORECASTS?. Page, Clemen 2013](page_clemen_ej_2013.pdf)

They use the following approach:

- Local Regression Estimator (sampled at 100 discrete price points, 0.10 sized window)
- Sample on transactions
- Sample 10 per market.
- 597 competitions, 1787 markets, 512612 transactions
- InTrade dataset

## Replication

For adapting to available predictit market data. We can:

- Keep N samples per contract (or market).
- Sample on price changes?
    - Or maybe hourly
- Local Regression Estimator
    - Or just use simple windowed average for initial implementation

## Implementation

- Determine contracts where outcome can be determined from final market price.
    - Get final market price + check if > 0.98
    - Get final day from db, check last day price
- Aggregate samples per contract.
    - python?
- Merge + compupte calibration curve

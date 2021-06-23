import argparse
import datetime
import itertools
import os
import typing as t

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from pi_trading_lib.data.resolution_data import NO_CORRECT_CONTRACT_MARKETS
from pi_trading_lib.model import Model
import pi_trading_lib.data.contracts
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.data.resolution as resolution
import pi_trading_lib.date_util as date_util
import pi_trading_lib.decorators
import pi_trading_lib.fs as fs
import pi_trading_lib.model_config as model_config
import pi_trading_lib.timers
import pi_trading_lib.work_dir as work_dir


@pi_trading_lib.decorators.memoize()
@pi_trading_lib.timers.timer
def sample_date(date: datetime.date, binary: bool, config: model_config.Config):
    snapshot = market_data.get_snapshot(date).data
    contracts = snapshot.index.tolist()

    binary_contract_map = pi_trading_lib.data.contracts.is_binary_contract(contracts)
    binary_contracts = [cid for cid, val in binary_contract_map.items() if val]

    if binary:
        snapshot = snapshot[snapshot.index.get_level_values(0).isin(binary_contracts)]
    else:
        snapshot = snapshot[~snapshot.index.get_level_values(0).isin(binary_contracts)]

    snapshot = snapshot[~snapshot.index.get_level_values(0).isin(NO_CORRECT_CONTRACT_MARKETS)]

    contracts = snapshot.index.tolist()

    resolutions = resolution.get_contract_resolution(contracts)
    resolutions = pd.Series(resolutions, name='resolution')
    snapshot = snapshot.join(resolutions)
    snapshot = snapshot.dropna()

    samples = []
    for idx, row in snapshot.iterrows():
        samples.append((row['market_id'], row['trade_price'], row['resolution']))

    return samples


@pi_trading_lib.timers.timer
def sample(begin_date: datetime.date, end_date: datetime.date, binary: bool, config: model_config.Config):
    all_samples = []
    for date in date_util.date_range(begin_date, end_date, skip_dates=market_data.missing_market_data_days()):
        date_samples = sample_date(date, binary, config)
        all_samples.append(date_samples)
    samples = list(itertools.chain(*all_samples))
    sample_df = pd.DataFrame(samples, columns=['market_id', 'trade_price', 'resolution'])

    return sample_df


@pi_trading_lib.timers.timer
def fit_model(date: datetime.date, binary: bool, config: model_config.Config) -> pd.Series:
    series_name = 'bin_model_price' if binary else 'non_bin_model_price'
    if date < date_util.from_str(config['calibration-model-active-date']):
        nan_array = np.empty(99)
        nan_array[:] = np.nan
        ser = pd.Series(nan_array, name=series_name, index=[i for i in range(1, 100)])
        ser.index.name = 'price_cents'
        return ser

    begin_date = date_util.from_str(config['calibration-model-begin-date'])

    sample_df = sample(begin_date, date_util.prev(date), binary, config)

    calibration_model = []

    window_width = config['calibration-model-fit-window-size']
    # samples at edge of window have e^{-alpha}. e^{-1} ~= 0.368
    weight_alpha = config['calibration-model-fit-sample-weight-alpha'] * 1 / window_width

    if config['calibration-model-fit-market-normalize']:
        market_counts = sample_df.groupby('market_id').size()
        market_weights = 1 / market_counts
        market_weights_df = market_weights.to_frame(name='market_weight')
    else:
        market_ids = sample_df['market_id'].unique()
        market_weights_df = pd.DataFrame([], index=market_ids)
        market_weights_df['market_weight'] = 1.0

    sample_df = sample_df.merge(market_weights_df, left_on='market_id', right_index=True, how="left")

    lin_reg = LinearRegression()
    for i in range(1, 100):
        px = i * 0.01
        window_lower = px - window_width
        window_upper = px + window_width

        df_filter = (sample_df['trade_price'] >= window_lower) & (sample_df['trade_price'] <= window_upper)

        # we reuse the same df, but that's ok
        sample_df['dist_weight'] = np.round(np.exp(-1.0 * weight_alpha * (sample_df['trade_price'] - px).abs()), decimals=3)
        sample_df['weight'] = sample_df['dist_weight'] * sample_df['market_weight']
        sample_df_window = sample_df[df_filter]
        lin_model = lin_reg.fit(np.reshape(sample_df_window['trade_price'].to_numpy(), (-1, 1)),
                                sample_df_window['resolution'].to_numpy(),
                                sample_df_window['weight'].to_numpy())
        lin_model_estimate = lin_model.coef_[0] * px + lin_model.intercept_
        lin_model_estimate = max(0.0, min(1.0, lin_model_estimate))
        calibration_model.append(lin_model_estimate)

    calibration_ser = pd.Series(calibration_model, name=series_name, index=[i for i in range(1, 100)])
    calibration_ser.index.name = 'price_cents'
    return calibration_ser


@pi_trading_lib.timers.timer
def generate_parameters(date: datetime.date, config: model_config.Config) -> pd.DataFrame:
    output = os.path.join(work_dir.get_uri('calibration_model', config.component_params('calibration-model'), date_1=date), 'model.csv')

    if os.path.exists(output):
        df = pd.read_csv(output, index_col='price_cents')
        return df

    binary_ser = fit_model(date, True, config)
    nonbinary_ser = fit_model(date, False, config)

    calibration_df = pd.concat([binary_ser, nonbinary_ser], axis=1)

    with fs.safe_open(output, 'w+') as f:
        calibration_df.to_csv(f)
    return calibration_df


class CalibrationModel(Model):
    def __init__(self):
        pass

    def _get_contract_md(self, date: datetime.date) -> pd.DataFrame:
        snapshot = market_data.get_snapshot(date).data
        return snapshot

    def get_price(self, config: model_config.Config, date: datetime.date) -> t.Optional[pd.Series]:
        model = generate_parameters(date, config)
        md = market_data.get_snapshot(date)

        contracts = md.data.index.get_level_values('contract_id').unique().tolist()
        binary_contract_map = pi_trading_lib.data.contracts.is_binary_contract(contracts)

        # combine with trade_price?
        df = pd.DataFrame([], index=md.data.index)
        df['rounded_price'] = (md['mid_price'] * 100).round().astype(np.int64)
        df['is_binary'] = md.data.index.get_level_values('contract_id').map(binary_contract_map)

        merged = df.merge(model, how='left', left_on='rounded_price', right_index=True)
        merged['model_price'] = np.nan

        if config['calibration-model-enable-binary']:
            merged.loc[merged['is_binary'] == False, 'model_price'] = merged.loc[merged['is_binary'] == False, 'bin_model_price']  # noqa
        if config['calibration-model-enable-non-binary']:
            merged.loc[merged['is_binary'] == True, 'model_price'] = merged.loc[merged['is_binary'] == True, 'non_bin_model_price']  # noqa

        return merged['model_price']

    def get_universe(self, config: model_config.Config, date: datetime.date) -> np.ndarray:
        model_snapshot = self._get_contract_md(date)
        return model_snapshot.index.to_numpy()  # type: ignore

    @property
    def name(self) -> str:
        return 'calibration-model'


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--begin-date')
    parser.add_argument('--end-date', required=True)
    parser.add_argument('--override', default='')

    args = parser.parse_args()

    config = model_config.get_config('calibration_model')
    if args.begin_date:
        config = config.override({'calibration-model-begin-date': args.begin_date})
    config = pi_trading_lib.model_config.override_config(config, args.override)

    model_df = generate_parameters(date_util.from_str(args.end_date), config)
    model_df['price'] = model_df.index.get_level_values(0) / 100
    model_df = model_df.reset_index(drop=True)
    model_df = model_df.set_index('price', drop=False)

    print(model_df)
    pi_trading_lib.timers.report_timers()

    model_df.plot()
    plt.show()

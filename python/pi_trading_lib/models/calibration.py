import argparse
import concurrent.futures
import datetime
import logging
import os
import typing as t

from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from pi_trading_lib.data.resolution import NO_CORRECT_CONTRACT_MARKETS, UNRESOLVED_CONTRACTS
from pi_trading_lib.model import Model
import pi_trading_lib.data.contracts
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.datetime_ext as datetime_ext
import pi_trading_lib.decorators
import pi_trading_lib.df_annotators
import pi_trading_lib.fs as fs
import pi_trading_lib.logging_ext as logging_ext
import pi_trading_lib.model_config as model_config
import pi_trading_lib.timers
import pi_trading_lib.work_dir as work_dir


@pi_trading_lib.decorators.memoize()
@pi_trading_lib.timers.timer
def sample_date(date: datetime.date, binary: bool, config: model_config.Config) -> pd.DataFrame:
    if config['calibration-model-fit-sample-method'] == 'sod':
        snapshot = market_data.get_snapshot(date).data
        contracts = snapshot.index.tolist()

        binary_contract_map = pi_trading_lib.data.contracts.is_binary_contract(contracts)
        binary_contracts = [cid for cid, val in binary_contract_map.items() if val]

        if binary:
            snapshot = snapshot[snapshot.index.get_level_values(0).isin(binary_contracts)]
        else:
            snapshot = snapshot[~snapshot.index.get_level_values(0).isin(binary_contracts)]

        if not config['calibration-model-fit-sample-no-correct']:
            snapshot = snapshot[~snapshot['market_id'].isin(NO_CORRECT_CONTRACT_MARKETS)]
            snapshot = snapshot[~snapshot['market_id'].isin(UNRESOLVED_CONTRACTS)]

        # some arbitrary filters to avoid bad samples
        snapshot['wide_market'] = ((snapshot['bid_price'] - snapshot['ask_price']).abs() > 0.1) | ((snapshot['trade_price'] - snapshot['mid_price']).abs() > 0.05)
        snapshot = snapshot[~snapshot['wide_market']]

        snapshot['dead_market'] = (
            ((snapshot['bid_price'] == 0.0) & (snapshot['ask_price'] == 0.01) & (snapshot['trade_price'] == 0.01)) |
            ((snapshot['bid_price'] == 0.99) & (snapshot['ask_price'] == 1.0) & (snapshot['trade_price'] == 0.99))
        )
        snapshot = snapshot[~snapshot['dead_market']]

        return snapshot.reset_index()[['contract_id', 'market_id', 'trade_price']]
    else:
        assert False, 'only sod sample method is supported'


@pi_trading_lib.timers.timer
def sample(begin_date: datetime.date, end_date: datetime.date, binary: bool, config: model_config.Config):
    dfs = []
    for date in datetime_ext.date_range(begin_date, end_date, skip_dates=market_data.missing_market_data_days()):
        date_sample_df = sample_date(date, binary, config.component_params('calibration-model-fit-sample'))
        dfs.append(date_sample_df)
    all_samples_df = pd.concat(dfs)
    all_samples_df = pi_trading_lib.df_annotators.add_resolution(all_samples_df, end_date, cid_col='contract_id')
    all_samples_df = all_samples_df.dropna()

    if binary and config['calibration-model-fit-symmetric-binary']:
        reverse_df = all_samples_df.copy()
        reverse_df['trade_price'] = 1.0 - reverse_df['trade_price']
        reverse_df['resolution'] = 1.0 - reverse_df['resolution']
        all_samples_df = pd.concat([all_samples_df, reverse_df])

    return all_samples_df


def _fit_for_price(px: float, window_df: pd.DataFrame) -> float:
    if len(window_df) == 0:
        logging.debug(f'No data from price {px}')
        return px

    lin_reg = LinearRegression()

    lin_model = lin_reg.fit(np.reshape(window_df['trade_price'].to_numpy(), (-1, 1)),
                            window_df['resolution'].to_numpy(),
                            window_df['weight'].to_numpy())
    lin_model_estimate: float = lin_model.coef_[0] * px + lin_model.intercept_  # typing: ignore
    lin_model_estimate = max(0.0, min(1.0, lin_model_estimate))
    return lin_model_estimate


@pi_trading_lib.timers.timer
def fit_model(date: datetime.date, binary: bool, config: model_config.Config) -> pd.DataFrame:
    series_name = 'bin' if binary else 'non_bin'
    cents_index = np.array([i for i in range(1, 100)])

    begin_date = datetime_ext.from_str(config['calibration-model-fit-begin-date'])

    sample_df = sample(begin_date, datetime_ext.prev(date), binary, config)

    if config['calibration-model-fit-market-resample-seed'] is not None:
        # used for bootstrap estimate of fitted model parameter distribution
        seed = config['calibration-model-fit-market-resample-seed']
        rng = np.random.default_rng(seed)
        mids = sample_df['market_id'].unique()
        sampled_mids = rng.choice(mids, len(mids) // 2)
        sample_df = sample_df[sample_df['market_id'].isin(sampled_mids)]

    window_width = config['calibration-model-fit-window-size']
    # samples at edge of window have e^{-alpha}. e^{-1} ~= 0.368
    weight_alpha = config['calibration-model-fit-sample-weight-alpha'] * 1 / window_width

    if config['calibration-model-fit-market-normalize'] == 'global':
        market_total_weight = sample_df.groupby('contract_id').size()
        market_total_weight = market_total_weight.reindex(sample_df['contract_id'].unique()).fillna(0.001)
        market_weight = 1 / market_total_weight
        market_weight.name = 'market_weight'
        market_weight_df = market_weight.to_frame()
        sample_df = sample_df.merge(market_weight_df, left_on='contract_id', right_index=True, how="left")
    elif config['calibration-model-fit-market-normalize'] is None:
        sample_df['market_weight'] = 1.0

    futures = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        for i in range(1, 100):
            px = i * 0.01
            window_lower = px - window_width
            window_upper = px + window_width
            df_filter = (sample_df['trade_price'] >= window_lower) & (sample_df['trade_price'] <= window_upper)
            window_df = sample_df[df_filter].copy()
            window_df['dist_weight'] = np.round(np.exp(-1.0 * weight_alpha * (window_df['trade_price'] - px).abs()), decimals=3)

            if config['calibration-model-fit-market-normalize'] == 'local':
                market_total_weight = window_df.groupby('contract_id').size()
                market_total_weight = market_total_weight.reindex(window_df['contract_id'].unique()).fillna(0.001)
                market_weight = 1 / market_total_weight
                market_weight = market_weight.pow(0.75)
                market_weight.name = 'market_weight'
                market_weight_df = market_weight.to_frame()
                window_df = window_df.merge(market_weight_df, left_on='contract_id', right_index=True, how="left")

            window_df['weight'] = window_df['dist_weight'] * window_df['market_weight']
            future = executor.submit(_fit_for_price, px, window_df)
            futures.append(future)
    calibration_model = [future.result() for future in futures]

    sample_df['trade_price_cents'] = (sample_df['trade_price'] * 100).astype(int)
    sample_density_ser = sample_df.groupby('trade_price_cents').size().reindex(cents_index).fillna(0.0)

    model_col = f'{series_name}_model_price'
    calibration_df = pd.DataFrame(calibration_model, columns=[model_col], index=cents_index)
    calibration_df[model_col] = calibration_df[model_col].rolling(window=5, min_periods=1, center=True).mean()
    calibration_df[f'{series_name}_sample_density'] = sample_density_ser
    calibration_df.index.name = 'price_cents'
    return calibration_df


@pi_trading_lib.timers.timer
def generate_parameters(date: datetime.date, config: model_config.Config) -> str:
    output_dir = os.path.join(work_dir.get_uri('calibration_model', config.component_params('calibration-model-fit'), date_1=date))

    if os.path.exists(output_dir):
        return output_dir

    binary_df = fit_model(date, True, config)
    nonbinary_df = fit_model(date, False, config)

    calibration_df = binary_df.join(nonbinary_df)

    with fs.atomic_output(output_dir) as tmpdir:
        with open(os.path.join(tmpdir, 'model.csv'), 'w+') as f:
            calibration_df.to_csv(f)

    return output_dir


def get_model_df(model_dir: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(model_dir, 'model.csv'), index_col='price_cents')


class CalibrationModel(Model):
    def __init__(self):
        pass

    def _get_contract_md(self, date: datetime.date) -> pd.DataFrame:
        snapshot = market_data.get_snapshot(date).data
        return snapshot

    def get_price(self, config: model_config.Config, date: datetime.date) -> t.Optional[pd.Series]:
        if date < datetime_ext.from_str(config['calibration-model-active-date']):
            return None

        model = get_model_df(generate_parameters(date, config))
        md = market_data.get_snapshot(date)

        contracts = md.data.index.get_level_values('contract_id').unique().tolist()
        binary_contract_map = pi_trading_lib.data.contracts.is_binary_contract(contracts)

        # combine with trade_price?
        df = pd.DataFrame([], index=md.data.index)
        df['rounded_price'] = (md['mid_price'] * 100).round().astype(np.int64)
        df['is_binary'] = md.data.index.get_level_values('contract_id').map(binary_contract_map)

        merged = df.merge(model, how='left', left_on='rounded_price', right_index=True)
        merged['model_price'] = np.nan

        if config['calibration-model-enable-non-binary']:
            merged.loc[merged['is_binary'] == False, 'model_price'] = merged.loc[merged['is_binary'] == False, 'non_bin_model_price']  # noqa
        if config['calibration-model-enable-binary']:
            merged.loc[merged['is_binary'] == True, 'model_price'] = merged.loc[merged['is_binary'] == True, 'bin_model_price']  # noqa

        return merged['model_price']

    def get_universe(self, config: model_config.Config, date: datetime.date) -> np.ndarray:
        model_snapshot = self._get_contract_md(date)
        return model_snapshot.index.to_numpy()  # type: ignore

    @property
    def name(self) -> str:
        return 'calibration-model'


# ============================= Model debugging, metrics =========================


def generate_confidence_intervals(config: model_config.Config, date: datetime.date, samples: int):
    model_dfs = []
    for i in range(samples):
        print('taking sample ' + str(i))
        config = config.override({'calibration-model-fit-market-resample-seed': i})
        model_df = get_model_df(generate_parameters(date, config))
        model_dfs.append(model_df)
    merged = pd.concat(model_dfs)
    merged['non_bin_model_price'] = merged['non_bin_model_price'] * 100
    merged['bin_model_price'] = merged['bin_model_price'] * 100

    conf_df = merged.groupby('price_cents').agg(
        {'non_bin_model_price': ['min', 'median', 'max'],
         'bin_model_price': ['min', 'median', 'max']}
    )
    conf_df = conf_df.stack(level=0).swaplevel().sort_index()
    print(conf_df)

    price_line = pd.Series(np.arange(1, 100), index=np.arange(1, 100), name='price')
    price_line.index.name = 'price_cents'

    fig, ax = plt.subplots(1, 2)

    sns.lineplot(data=merged, x='price_cents', y='non_bin_model_price', ax=ax[0], label='non-binary contracts')
    sns.lineplot(data=merged, x='price_cents', y='bin_model_price', ax=ax[1], label='binary contracts')
    sns.lineplot(data=price_line, ax=ax[0], label='perfect calibration')
    sns.lineplot(data=price_line, ax=ax[1], label='perfect calibration')

    for idx in [0, 1]:
        ax[idx].set_xlabel('trade price')
        ax[idx].set_ylabel('probability resolved YES')
        ax[idx].set_title(f'Contract price calibration {datetime_ext.from_str(config["calibration-model-fit-begin-date"])} to {date}')
    plt.show()


def main():
    parser = argparse.ArgumentParser()

    # common
    parser.add_argument('--date', required=True)
    parser.add_argument('--override', default='')
    parser.add_argument('--debug', action='store_true')

    # alternate commands, default is to plot fitted curve
    parser.add_argument('--eval', action='store_true')

    parser.add_argument('--conf', action='store_true')
    parser.add_argument('--conf-samples', default=10, type=int)

    # arguments for default command
    parser.add_argument('--save', action='store_true')

    args = parser.parse_args()

    if args.debug:
        logging_ext.init_logging(level=logging.DEBUG)
    else:
        logging_ext.init_logging()

    config = model_config.get_config('calibration_model').component_params('calibration-model-fit')
    config = pi_trading_lib.model_config.override_config(config, args.override)

    model_df = get_model_df(generate_parameters(datetime_ext.from_str(args.date), config))
    model_df['price'] = model_df.index.get_level_values(0) / 100
    model_df = model_df.reset_index(drop=True)
    model_df = model_df.set_index('price', drop=False)

    if args.eval:
        for binary in [False, True]:
            snapshot_df = sample_date(datetime_ext.from_str(args.date), binary, config.component_params('calibration-model-fit-sample'))
            snapshot_df = pi_trading_lib.df_annotators.add_resolution(snapshot_df, cid_col='contract_id')
            snapshot_df = snapshot_df.merge(model_df, left_on='trade_price', right_index=True, how='left')
            snapshot_df = snapshot_df.dropna()

            print('num resolved contracts for date', len(snapshot_df))
            if binary:
                model_price = snapshot_df['bin_model_price']
            else:
                model_price = snapshot_df['non_bin_model_price']

            snapshot_df['prof'] = np.nan

            buy_filter = model_price > snapshot_df['trade_price'] + 0.03
            sell_filter = model_price < snapshot_df['trade_price'] - 0.03
            snapshot_df.loc[buy_filter, 'prof'] = snapshot_df.loc[buy_filter, 'resolution'] - snapshot_df.loc[buy_filter, 'trade_price']
            snapshot_df.loc[sell_filter, 'prof'] = snapshot_df.loc[sell_filter, 'trade_price'] - snapshot_df.loc[sell_filter, 'resolution']
            snapshot_df = snapshot_df.dropna()

            print(snapshot_df)
            ther_prof = snapshot_df['prof'].sum()
            prof_per_share = snapshot_df['prof'].mean()
            print(ther_prof, prof_per_share)
    elif args.conf:
        generate_confidence_intervals(config, datetime_ext.from_str(args.date), args.conf_samples)
    else:
        print(model_df)

        fig, axs = plt.subplots(nrows=2)
        model_df[['bin_model_price', 'non_bin_model_price', 'price']].plot(ax=axs[0])
        model_df[['bin_sample_density', 'non_bin_sample_density']].rolling(5).mean().iloc[20:80].plot(ax=axs[1])

        if args.save:
            save_dir = work_dir.get_uri('cal_image', config, args.date)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            plt.savefig(os.path.join(save_dir, 'image.png'))
        else:
            plt.show()

    pi_trading_lib.timers.report_timers()


if __name__ == "__main__":
    main()

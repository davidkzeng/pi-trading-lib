import argparse
import datetime
import itertools
import json
import os
import typing as t

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# from pi_trading_lib.data.resolution_data import NO_CORRECT_CONTRACT_MARKETS
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
def sample_date(date: datetime.date, config: model_config.Config):
    snapshot = market_data.get_snapshot(date).data
    contracts = snapshot.index.tolist()

    binary_contract_map = pi_trading_lib.data.contracts.is_binary_contract(contracts)
    binary_contracts = [cid for cid, val in binary_contract_map.items() if val]
    snapshot = snapshot[snapshot.index.get_level_values(0).isin(binary_contracts)]
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
def sample(begin_date: datetime.date, end_date: datetime.date, config: model_config.Config):
    all_samples = []
    for date in date_util.date_range(begin_date, end_date, skip_dates=market_data.missing_market_data_days()):
        date_samples = sample_date(date, config)
        all_samples.append(date_samples)
    samples = list(itertools.chain(*all_samples))
    return samples


@pi_trading_lib.timers.timer
def generate_parameters(date: datetime.date, config: model_config.Config) -> t.Dict[int, float]:
    output = os.path.join(work_dir.get_uri('calibration_model', config.component_params('calibration-model'), date_1=date), 'model.json')

    if os.path.exists(output):
        with open(output) as f:
            d_json = json.load(f)
            d = {int(k): float(v) for k, v in d_json.items()}
            return d

    if date < date_util.from_str(config['calibration-model-active-date']):
        return {}

    begin_date = date_util.from_str(config['calibration-model-begin-date'])
    samples = sample(begin_date, date_util.prev(date), config)

    sample_df = pd.DataFrame(samples, columns=['market_id', 'trade_price', 'resolution'])

    calibration_model = []

    for i in range(1, 100, 1):
        px = i * 0.01
        alpha = 25.0
        sample_df['weight'] = np.round(np.exp(-1.0 * alpha * (sample_df['trade_price'] - px).abs()), decimals=3)
        sample_df['weighted_res'] = sample_df['weight'] * sample_df['resolution']
        sample_df['weighted_trade'] = sample_df['weight'] * sample_df['trade_price']
        result = sample_df['weighted_res'].sum() / sample_df['weight'].sum()
        result_trade = sample_df['weighted_trade'].sum() / sample_df['weight'].sum()
        calibration_model.append((result_trade, result))

    # hacky calibration script, we should adopt a smarter fitting method
    calibration_dict = {}
    for i in range(1, 100, 1):
        val = i * 0.01
        if val < calibration_model[0][0]:
            calibration_dict[i] = calibration_model[0][1]
        if val > calibration_model[-1][0]:
            calibration_dict[i] = calibration_model[-1][1]
        for idx in range(0, len(calibration_model) - 1):
            if val >= calibration_model[idx][0] and val < calibration_model[idx + 1][0]:
                calibration_dict[i] = (calibration_model[idx][1] + calibration_model[idx + 1][1]) * 0.5
                break

    with fs.safe_open(output, 'w+') as f:
        json.dump(calibration_dict, f)
    return calibration_dict


class CalibrationModel(Model):
    def __init__(self):
        pass

    def _get_contract_md(self, date: datetime.date) -> pd.DataFrame:
        snapshot = market_data.get_snapshot(date).data
        return snapshot

    def get_price(self, config: model_config.Config, date: datetime.date) -> t.Optional[pd.Series]:
        model = generate_parameters(date, config)
        md = market_data.get_snapshot(date)
        # combine with trade_price?
        calibrated_price = md['mid_price'].map(lambda f: model.get(int(f * 100), None))
        return calibrated_price

    def get_universe(self, date: datetime.date) -> np.ndarray:
        model_snapshot = self._get_contract_md(date)
        return model_snapshot.index.to_numpy()  # type: ignore

    @property
    def name(self) -> str:
        return 'calibration-model'


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--begin-date')
    parser.add_argument('--end-date', required=True)

    args = parser.parse_args()

    default_config = model_config.get_config('calibration_model')
    if args.begin_date:
        default_config = default_config.override({'calibration-model-begin-date': args.begin_date})

    parameters = generate_parameters(date_util.from_str(args.end_date), default_config)

    pser = pd.Series(parameters).to_frame()
    pser.index = pser.index / 100
    pser['price'] = pser.index
    print(pser)
    pser.plot()
    plt.show()

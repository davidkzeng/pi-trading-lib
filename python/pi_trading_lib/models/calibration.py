import argparse
import typing as t
import datetime
import itertools

import pandas as pd
import numpy as np

import pi_trading_lib.data.contracts
import pi_trading_lib.date_util as date_util
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.data.resolution as resolution
import pi_trading_lib.model_config as model_config
import pi_trading_lib.timers
import pi_trading_lib.decorators
# from pi_trading_lib.data.resolution_data import NO_CORRECT_CONTRACT_MARKETS
from pi_trading_lib.model import Model

import pi_trading_lib.data.contract_groups as contract_groups
import pi_trading_lib.states as states


@pi_trading_lib.decorators.memoize()
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


def sample(begin_date: datetime.date, end_date: datetime.date, config: model_config.Config):
    all_samples = []
    for date in date_util.date_range(begin_date, end_date, skip_dates=market_data.missing_market_data_days()):
        date_samples = sample_date(date, config)
        all_samples.append(date_samples)
    samples = list(itertools.chain(*all_samples))
    return samples


@pi_trading_lib.timers.timer
def generate_parameters(date: datetime.date, config: model_config.Config) -> t.Dict[int, float]:
    start_date = date_util.from_str(config['calibration_model_start_date'])
    samples = sample(start_date, date, config)

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

    calibration_dict = {}
    for i in range(1, 100, 1):
        val = i * 0.01
        if val < calibration_model[0][0]:
            calibration_dict[i] = val
        if val > calibration_model[-1][0]:
            calibration_dict[i] = val
        for idx in range(0, len(calibration_model) - 1):
            if val >= calibration_model[idx][0] and val < calibration_model[idx + 1][0]:
                calibration_dict[i] = (calibration_model[idx][1] + calibration_model[idx + 1][1]) * 0.5
                break

    return calibration_dict


STATE_CONTRACTS = 'election_2020/states_pres.json'
EXCLUDE_STATES = states.EC_SPECIAL_DISTRICTS + ['ME', 'NE']


class CalibrationModel(Model):
    def __init__(self):
        all_state_contract_info = contract_groups.get_contract_data(STATE_CONTRACTS)
        self.state_contract_info = {cid: info for cid, info in all_state_contract_info.items()
                                    if (info[0] not in EXCLUDE_STATES) and (info[1] == 'democratic')}
        self.state_contract_ids = sorted(self.state_contract_info.keys(), key=lambda cid: self.state_contract_info[cid][0])
        self.universe: np.ndarray = np.sort(np.array(list(self.state_contract_ids)))

    def _get_contract_md(self, date: datetime.date) -> pd.DataFrame:
        state_md = market_data.get_snapshot(date, tuple(self.universe.tolist())).data
        return state_md

    def get_price(self, config: model_config.Config, date: datetime.date) -> t.Optional[pd.Series]:
        md = self._get_contract_md(date)
        model = generate_parameters(date, config)
        md['fair_price'] = md['trade_price'].map(lambda f: model[int(f * 100)])

        print(md['fair_price'])
        print(md['trade_price'])
        print(pd.Series(model))
        return md['fair_price']

    def get_universe(self, date: datetime.date) -> np.ndarray:
        return self.universe


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('begin_date')
    parser.add_argument('end_date')
    assert parser

import datetime
import typing as t

import numpy as np
import pandas as pd
import scipy.stats as st

from pi_trading_lib.model import StandardModel
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.model_config as model_config
import pi_trading_lib.data.fivethirtyeight as fte
import pi_trading_lib.data.contracts as contracts
import pi_trading_lib.states as states


STATE_CONTRACTS = 'election_2020/states_pres.json'
EXCLUDE_STATES = states.EC_SPECIAL_DISTRICTS + ['ME', 'NE']


class NaiveModel(StandardModel):
    """
    Generates optimal state election portfolio based on FiveThirtyEight state model.

    At a high level, we take FiveThirtyEight state-level simulation results and use them to
    maximize expected return while being neutral to a shift in the expected national margin.

    margin_hi, margin_lo from 538 represent 80% conf. interval outcomes

    We make the following assumptions:
        1. State margin follows a normal distribution.
        2. The expectation for state margin is directly associated with the national margin.
        3. The variance for the stage margin is unaffected by the national margin.
        4. State results are uncorrelated (beyond the described shift based on national margin.)

    Assumes state margin follows a normal distribution.

    """

    def __init__(self):
        all_state_contract_info = contracts.get_contract_data_by_cid(STATE_CONTRACTS)
        self.state_contract_info = {cid: info for cid, info in all_state_contract_info.items()
                                    if (info[0] not in EXCLUDE_STATES) and (info[1] == 'democratic')}
        self.state_contract_ids = sorted(self.state_contract_info.keys(), key=lambda cid: self.state_contract_info[cid][0])
        self.universe: np.ndarray = np.array(list(self.state_contract_ids))

    def _get_state_contract_md(self, date: datetime.date) -> pd.DataFrame:
        state_md = market_data.get_snapshot(date, tuple(self.state_contract_ids))
        state_md['state'] = state_md.index.get_level_values('contract_id').map(self.state_contract_info).map(lambda info: info[0])
        return state_md.reset_index().set_index('state')

    def _get_state_contract_model(self, date: datetime.date) -> pd.DataFrame:
        national_model = fte.get_df('pres_national_2020', date, date).iloc[0]
        national_model['margin_hi'] = national_model['national_voteshare_inc_hi'] - national_model['national_voteshare_chal_lo']
        national_model['margin_lo'] = national_model['national_voteshare_inc_lo'] - national_model['national_voteshare_chal_hi']
        national_model['national_margin_stdev'] = (national_model['margin_hi'] - national_model['margin_lo']) / (2 * 1.28)

        state_model = fte.get_df('pres_state_2020', date, date)
        state_model = state_model[['state', 'modeldate', 'candidate_inc', 'candidate_chal', 'margin', 'margin_hi', 'margin_lo', 'voteshare_inc', 'voteshare_chal']]

        # Standard deviation assuming normal distribution
        state_model['margin_stdev'] = (state_model['margin_hi'] - state_model['margin_lo']) / (2 * 1.28)
        state_model['zscore_margin'] = state_model['margin'] / state_model['margin_stdev']
        # Expected change of winning
        state_model['winstate_chal'] = 1 - st.norm.cdf(state_model['zscore_margin'])

        # d(winstate_chal) / d(margin) * stdev_nat_margin, change in winstat_chal per 1 stdev change in expected national margin
        state_model['margin_factor'] = national_model['national_margin_stdev'] * st.norm.pdf(state_model['zscore_margin']) / state_model['margin_stdev']

        p_win = state_model['winstate_chal']
        state_model['return_stdev'] = np.sqrt(p_win * (1 - p_win) ** 2 + (1 - p_win) * (0 - p_win) ** 2)

        state_model = state_model.set_index('state')
        state_md = self._get_state_contract_md(date)
        state_model = state_model.join(state_md, lsuffix='_model', rsuffix='_md', how='inner')

        return state_model.sort_index()

    def get_universe(self, date: datetime.date) -> np.ndarray:
        return self.universe

    def get_return(self, config: model_config.Config, date: datetime.date) -> t.Optional[np.ndarray]:
        state_model = self._get_state_contract_model(date)
        return state_model['winstate_chal'].to_numpy()  # type: ignore

    def get_factors(self, config: model_config.Config, date: datetime.date) -> t.List[np.ndarray]:
        state_model = self._get_state_contract_model(date)
        return [state_model['margin_factor'].to_numpy()]

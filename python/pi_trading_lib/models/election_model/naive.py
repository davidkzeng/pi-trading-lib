import datetime
import typing as t

import numpy as np
import pandas as pd
import scipy.stats as st
import cvxpy as cp

from pi_trading_lib.model import BaseModel, OptimizeResult, POSITION_LIMIT_VALUE
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.data.fivethirtyeight as fte
import pi_trading_lib.data.contracts as contracts
import pi_trading_lib.logging as logging
import pi_trading_lib.states as states

logging.init_logging()


STATE_CONTRACTS = 'election_2020/states_pres.json'
EXCLUDE_STATES = states.EC_SPECIAL_DISTRICTS + ['ME', 'NE']


class NaiveModel(BaseModel):
    """
    Prices contracts based on FiveThirtyEight state model.

    Assumes state margin follows a normal distribution.

    """
    def __init__(self):
        self.default_params = {
            'variance_weight': 1.0
        }
        self.state_contract_info = contracts.get_contract_data_by_cid(STATE_CONTRACTS)
        self.state_contract_ids = self.state_contract_info.keys()

    def _get_state_contract_md(self, date: datetime.date) -> pd.DataFrame:
        state_md = market_data.get_df(date, date, contracts=tuple(self.state_contract_ids),
                                      snapshot_interval=datetime.timedelta(days=1))
        contract_info = state_md.index.get_level_values('contract_id').map(lambda val: self.state_contract_info[val])
        state_md['state'] = contract_info.map(lambda info: info[0])
        state_md_dem = state_md.loc[contract_info.map(lambda info: info[1] == 'democratic'), :]
        return state_md_dem.set_index('state')

    def get_state_contract_model(self, date: datetime.date) -> pd.DataFrame:
        state_model = fte.get_df('pres_state_2020', date, date)

        # Standard deviation assuming normal distribution
        state_model['margin_stdev'] = (state_model['margin_hi'] - state_model['margin_lo']) / (2 * 1.28)
        state_model['zscore_margin'] = state_model['margin'] / state_model['margin_stdev']

        # Expected winstate_chal assuming normal distribution
        state_model['winstate_chal_margin'] = 1 - st.norm.cdf(state_model['zscore_margin'])

        # d(winstate_chal_margin) / d(margin)
        state_model['margin_factor'] = st.norm.pdf(state_model['zscore_margin']) / state_model['margin_stdev']
        state_model = state_model.set_index('state')
        state_md = self._get_state_contract_md(date)

        state_model = state_model.join(state_md, lsuffix='_model', rsuffix='_md', how='inner')
        state_model = state_model[~state_model.index.isin(EXCLUDE_STATES)]
        state_model['buy_edge'] = state_model['winstate_chal'] - state_model['best_ask_price']
        state_model['sell_edge'] = state_model['best_bid_price'] - state_model['winstate_chal']

        p_win = state_model['winstate_chal']
        state_model['return_stdev'] = np.sqrt(p_win * (1 - p_win) ** 2 + (1 - p_win) * (0 - p_win) ** 2)
        state_model = state_model.sort_index()
        return state_model.sort_index()

    # TODO: Add existing positions
    # TODO: Represent ability to take the same position on either side of contract
    def optimize(self, date: datetime.date, capital: float,
                 cur_position: t.Optional[np.ndarray] = None,
                 params: t.Dict[str, t.Any] = {}) -> OptimizeResult:
        assert set(params.keys()).issubset(set(self.default_params.keys()))

        params = {**self.default_params, **params}

        state_model = self.get_state_contract_model(date)

        edge_b, edge_s = state_model['buy_edge'].to_numpy(), state_model['sell_edge'].to_numpy()
        price_b, price_s = state_model['best_ask_price'].to_numpy(), (1 - state_model['best_bid_price']).to_numpy()
        margin_f = state_model['margin_factor'].to_numpy()
        contract_return_stdev = state_model['return_stdev'].to_numpy()

        num_contracts = len(state_model.index)

        if cur_position is None:
            cur_position = np.empty(num_contracts)

        # Contracts to sell or buy
        delta_b, delta_s = cp.Variable(num_contracts), cp.Variable(num_contracts)
        net_pos = cp.Variable(num_contracts)
        contract_position_stdev = (
            cp.multiply(delta_b, contract_return_stdev) + cp.multiply(delta_s, contract_return_stdev)
        )
        stdev_return = cp.norm(contract_position_stdev)
        delta_cap = price_b @ delta_b + price_s @ delta_s

        constraints = [
            delta_b >= 0, delta_s >= 0,
            net_pos == cur_position + delta_b - delta_s,
            delta_cap <= capital,  # Equality should work here too
            margin_f @ net_pos == 0,  # Zero net exposure to margin move
            cp.multiply(price_b, net_pos) <= POSITION_LIMIT_VALUE,
            cp.multiply(-1 * price_s, net_pos) <= POSITION_LIMIT_VALUE,
        ]
        exp_return = edge_b @ delta_b + edge_s @ delta_s
        objective = exp_return - params['variance_weight'] * stdev_return
        problem = cp.Problem(cp.Maximize(objective), constraints)
        problem.solve()

        state_model['buy_amount'] = np.round(delta_b.value)
        state_model['sell_amount'] = np.round(delta_s.value)
        return state_model, capital - delta_cap.value, (exp_return.value, stdev_return.value)

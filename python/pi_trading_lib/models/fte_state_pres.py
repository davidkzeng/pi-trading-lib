import datetime
import logging
# import typing as t

import numpy as np
import pandas as pd
import scipy.stats as st
import cvxpy as cp

from pi_trading_lib.model import PositionModel, PIPOSITION_LIMIT_VALUE
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.data.fivethirtyeight as fte
import pi_trading_lib.data.contracts as contracts
import pi_trading_lib.states as states


STATE_CONTRACTS = 'election_2020/states_pres.json'
EXCLUDE_STATES = states.EC_SPECIAL_DISTRICTS + ['ME', 'NE']


class NaiveModel(PositionModel):
    """
    Generates optimal state election portfolio based on FiveThirtyEight state model.

    At a high level, we take FiveThirtyEight state-level simulation results and use them to
    maximize expected return while begin neutral to a shift in the expected national margin.

    margin_hi, margin_lo from 538 represent 2 std. dev. outcomes.

    We make the following assumptions:
        1. State margin follows a normal distribution.
        2. The expectation for state margin is directly associated with the national margin.
        3. The variance for the stage margin is unaffected by the national margin.
        4. State results are uncorrelated (beyond the described shift based on national margin.)

    Assumes state margin follows a normal distribution.

    """

    def __init__(self):
        self.default_params = {
            'variance_weight': 1.0
        }
        all_state_contract_info = contracts.get_contract_data_by_cid(STATE_CONTRACTS)
        self.state_contract_info = {cid: info for cid, info in all_state_contract_info.items()
                                    if (info[0] not in EXCLUDE_STATES) and (info[1] == 'democratic')}
        self.state_contract_ids = sorted(self.state_contract_info.keys(), key=lambda cid: self.state_contract_info[cid][0])
        self.universe: np.ndarray = np.array(list(self.state_contract_ids))

    def _get_state_contract_md(self, date: datetime.date) -> pd.DataFrame:
        state_md = market_data.get_snapshot(date, self.state_contract_ids)
        state_md['state'] = state_md.index.get_level_values('contract_id').map(self.state_contract_info).map(lambda info: info[0])
        return state_md.reset_index().set_index('state')

    def _get_state_contract_model(self, date: datetime.date) -> pd.DataFrame:
        state_model = fte.get_df('pres_state_2020', date, date)
        state_model = state_model[['state', 'modeldate', 'candidate_inc', 'candidate_chal', 'margin', 'margin_hi', 'margin_lo', 'voteshare_inc', 'voteshare_chal']]

        # Standard deviation assuming normal distribution
        state_model['margin_stdev'] = (state_model['margin_hi'] - state_model['margin_lo']) / (2 * 1.28)
        state_model['zscore_margin'] = state_model['margin'] / state_model['margin_stdev']
        state_model['winstate_chal'] = 1 - st.norm.cdf(state_model['zscore_margin'])

        # d(winstate_chal) / d(margin)
        state_model['margin_factor'] = st.norm.pdf(state_model['zscore_margin']) / state_model['margin_stdev']
        state_model = state_model.set_index('state')
        state_md = self._get_state_contract_md(date)

        state_model = state_model.join(state_md, lsuffix='_model', rsuffix='_md', how='inner')
        state_model['buy_edge'] = state_model['winstate_chal'] - state_model['ask_price']
        state_model['sell_edge'] = state_model['bid_price'] - state_model['winstate_chal']

        p_win = state_model['winstate_chal']
        state_model['return_stdev'] = np.sqrt(p_win * (1 - p_win) ** 2 + (1 - p_win) * (0 - p_win) ** 2)
        state_model = state_model.sort_index()
        return state_model.sort_index()

    def get_universe(self, date: datetime.date) -> np.ndarray:
        return self.universe

    # OLDTODO: Represent ability to take the same position on either side of contract
    def optimize(self, date: datetime.date, capital: float, cur_position: np.ndarray) -> np.ndarray:
        params = self.default_params

        state_model = self._get_state_contract_model(date)

        fair_price = state_model['winstate_chal'].to_numpy()
        price_b, price_s = state_model['ask_price'].to_numpy(), (1 - state_model['bid_price']).to_numpy()
        price_bb, price_bs, price_sb, price_ss = price_b, 1 - price_s, 1 - price_b, price_s
        margin_f = state_model['margin_factor'].to_numpy()
        contract_return_stdev = state_model['return_stdev'].to_numpy()

        num_contracts = len(state_model.index)

        # Contracts to sell or buy
        cur_position_b = np.maximum(np.zeros(num_contracts), cur_position)
        cur_position_s = np.maximum(np.zeros(num_contracts), cur_position * -1)

        delta_bb, delta_bs, delta_sb, delta_ss = cp.Variable(num_contracts), cp.Variable(num_contracts), cp.Variable(num_contracts), cp.Variable(num_contracts)
        new_pos = cp.Variable(num_contracts)
        new_pos_b, new_pos_s = cp.Variable(num_contracts), cp.Variable(num_contracts)

        delta_cap = price_sb @ delta_sb + price_bs @ delta_bs - price_bb @ delta_bb - price_ss @ delta_ss
        new_cap = capital + delta_cap

        constraints = [
            new_pos_b >= 0, new_pos_s >= 0,
            delta_bb >= 0, delta_bs >= 0, delta_ss >= 0, delta_sb >= 0,
            new_pos_b == cur_position_b + delta_bb - delta_bs,
            new_pos_s == cur_position_s + delta_ss - delta_sb,
            new_pos == new_pos_b - new_pos_s,
            new_cap >= 250,  # Equality should work here too, allow for rounding to work out hopefully
            margin_f @ new_pos == 0,  # Zero new exposure to margin move
            cp.multiply(price_b, new_pos) <= PIPOSITION_LIMIT_VALUE,
            cp.multiply(-1 * price_s, new_pos) <= PIPOSITION_LIMIT_VALUE,
        ]
        exp_return = fair_price @ new_pos_b + (1 - fair_price) @ new_pos_s + new_cap
        contract_position_stdev = (
            cp.multiply(new_pos_b, contract_return_stdev) + cp.multiply(new_pos_s, contract_return_stdev)
        )
        stdev_return = cp.norm(contract_position_stdev)

        objective = exp_return - params['variance_weight'] * stdev_return
        problem = cp.Problem(cp.Maximize(objective), constraints)
        problem.solve()

        state_model['buy_amount'] = np.round(new_pos_b.value)
        state_model['sell_amount'] = np.round(new_pos_s.value)

        logging.info(state_model)

        return new_pos.value  # type: ignore

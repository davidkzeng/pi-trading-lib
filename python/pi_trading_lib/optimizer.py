import logging
import typing as t

import numpy as np
import pandas as pd
import cvxpy as cp

import pi_trading_lib.model_config as model_config
import pi_trading_lib.numpy_ext as np_ext
from pi_trading_lib.data.market_data import MarketDataSnapshot
from pi_trading_lib.model import PIPOSITION_LIMIT_VALUE
from pi_trading_lib.accountant import Book
import pi_trading_lib.timers


@pi_trading_lib.timers.timer
def optimize(book: Book, snapshot: MarketDataSnapshot, price_models: t.List[pd.Series],
             return_models: t.List[pd.Series], factor_models: t.List[pd.Series],
             config: model_config.Config) -> pd.Series:
    assert return_models is not None  # unused

    num_contracts = len(snapshot.data)
    print(num_contracts)
    for pm in price_models:
        assert len(pm) == num_contracts
    for fm in factor_models:
        assert len(fm) == num_contracts

    price_b, price_s = snapshot['ask_price'].to_numpy(), (1 - snapshot['bid_price']).to_numpy()

    # widen to reduce trading (even if we could execute as best bid/ask)
    price_b = price_b + config['trading_cost']
    price_s = price_s + config['trading_cost']

    price_bb, price_bs, price_sb, price_ss = price_b, 1 - price_s, 1 - price_b, price_s

    agg_price_model = np.nanmean(np.array(price_models), axis=0)
    agg_price_model[np.isnan(agg_price_model)] = snapshot['mid_price'][np.isnan(agg_price_model)]

    # Contracts to sell or buy
    cur_position = pd.Series(book.position, index=book.universe.cids).reindex(snapshot.universe).to_numpy()
    cur_position_b = np.maximum(np.zeros(num_contracts), cur_position)
    cur_position_s = np.maximum(np.zeros(num_contracts), cur_position * -1)

    delta_bb, delta_bs, delta_sb, delta_ss = cp.Variable(num_contracts), cp.Variable(num_contracts), cp.Variable(num_contracts), cp.Variable(num_contracts)
    new_pos = cp.Variable(num_contracts)
    new_pos_b, new_pos_s = cp.Variable(num_contracts), cp.Variable(num_contracts)

    delta_cap = price_sb @ delta_sb + price_bs @ delta_bs - price_bb @ delta_bb - price_ss @ delta_ss
    new_cap = book.capital + delta_cap

    margin_factors = []
    for factor_model in factor_models:
        factor_model = np.nan_to_num(factor_model)
        margin_factors.append(cp.abs(factor_model @ new_pos))

    constraints = [
        new_pos_b >= 0, new_pos_s >= 0,
        delta_bb >= 0, delta_bs >= 0, delta_ss >= 1, delta_sb >= 0,
        new_pos_b == cur_position_b + delta_bb - delta_bs,
        new_pos_s == cur_position_s + delta_ss - delta_sb,
        new_pos == new_pos_b - new_pos_s,
        new_cap >= 250,
        cp.multiply(price_b, new_pos) <= PIPOSITION_LIMIT_VALUE, # TODO: this should be base on the value of our current pos + FIFO
        cp.multiply(-1 * price_s, new_pos) <= PIPOSITION_LIMIT_VALUE,
    ]

    p_win = agg_price_model
    contract_return_stdev = np.sqrt(p_win * (1 - p_win) ** 2 + (1 - p_win) * (0 - p_win) ** 2)
    contract_position_stdev = (
        cp.multiply(new_pos_b, contract_return_stdev) + cp.multiply(new_pos_s, contract_return_stdev)
    )
    stdev_return = cp.norm(contract_position_stdev)

    obj_factor = -1 * cp.sum(margin_factors)
    obj_return = agg_price_model @ new_pos_b + (1 - agg_price_model) @ new_pos_s + new_cap
    obj_std = -1 * config['std_penalty'] * stdev_return

    objective = obj_return + obj_std + obj_factor
    problem = cp.Problem(cp.Maximize(objective), constraints)
    problem.solve()

    logging.debug((obj_return.value, obj_std.value, obj_factor.value))

    pos_mult = config['position_size_mult']
    rounded_new_pos = np.around(new_pos.value / pos_mult) * pos_mult
    return pd.Series(rounded_new_pos, index=snapshot.universe)  # type: ignore

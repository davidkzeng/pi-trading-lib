import logging
import typing as t

import numpy as np
import pandas as pd
import cvxpy as cp
import cvxpy.settings

import pi_trading_lib.model_config as model_config
from pi_trading_lib.data.market_data import MarketDataSnapshot
from pi_trading_lib.model import PIPOSITION_LIMIT_VALUE
from pi_trading_lib.accountant import Book
import pi_trading_lib.timers


@pi_trading_lib.timers.timer
def optimize(book: Book, snapshot: MarketDataSnapshot, price_models: t.List[pd.Series],
             price_model_weights: t.List[float],
             return_models: t.List[pd.Series], factor_models: t.List[pd.Series],
             config: model_config.Config) -> pd.DataFrame:
    """Returns optimal book given market prices and models

    snapshot: Used for market prices as well as universe to optimize over
    """

    assert return_models is not None  # unused

    num_contracts = len(snapshot.data)
    logging.debug(f'optimizing over {num_contracts} contracts')

    assert len(price_models) == len(price_model_weights)
    for pm in price_models:
        assert len(pm) == num_contracts
    for fm in factor_models:
        assert len(fm) == num_contracts

    if num_contracts == 0:
        return pd.DataFrame([], columns=['new_pos', 'agg_price_model', 'take_edge'])

    price_b, price_s = snapshot['ask_price'].to_numpy(), (1 - snapshot['bid_price']).to_numpy()

    # widen prices as a proxy for requiring a larger edge to trade
    # note that because both prices are for "buying" a long/short contract, we widen by incrementing
    price_b = price_b + config['optimizer-take-edge']
    price_s = price_s + config['optimizer-take-edge']

    # e.x price_b = 0.5, price_s = 0.55
    # price_bs = 0.45, price_sb = 0.5
    # bid ask on going long contracts (0.45, 0.5)
    # bid ask on going short contracts (0.5, 0.55)
    price_bb, price_bs, price_sb, price_ss = price_b, 1 - price_s, 1 - price_b, price_s

    price_models = price_models + [snapshot['mid_price']]
    price_model_weights = price_model_weights + [1.0]

    # TODO: convert this to numpy code
    agg_prices = []
    for cid in snapshot.universe:
        sum_price = 0.0
        sum_weight = 0.0
        for idx, price_model in enumerate(price_models):
            if not np.isnan(price_model[cid]):
                price_model_weight = price_model_weights[idx]
                sum_weight += price_model_weight
                sum_price += price_model[cid] * price_model_weight
        agg_price = sum_price / sum_weight
        agg_prices.append(agg_price)

    agg_price_model = np.array(agg_prices)

    # Contracts to sell or buy
    cur_position = pd.Series(book.position, index=book.universe.cids).reindex(snapshot.universe).to_numpy()
    cur_position_b = np.maximum(np.zeros(num_contracts), cur_position)
    cur_position_s = np.maximum(np.zeros(num_contracts), cur_position * -1)

    delta_bb, delta_bs, delta_sb, delta_ss = cp.Variable(num_contracts), cp.Variable(num_contracts), cp.Variable(num_contracts), cp.Variable(num_contracts)
    new_pos = cp.Variable(num_contracts)
    new_pos_b, new_pos_s = cp.Variable(num_contracts), cp.Variable(num_contracts)

    delta_cap = price_sb @ delta_sb + price_bs @ delta_bs - price_bb @ delta_bb - price_ss @ delta_ss
    new_cap = book.capital + delta_cap

    net_cost = pd.Series(book.pos_cost, index=book.universe.cids).reindex(snapshot.universe).to_numpy()
    net_cost = np.minimum(net_cost, np.full(net_cost.shape, PIPOSITION_LIMIT_VALUE))

    margin_factors = []
    for factor_model in factor_models:
        factor_model = np.nan_to_num(factor_model)
        margin_factors.append(cp.abs(factor_model @ new_pos))

    constraints = [
        new_pos_b >= 0, new_pos_s >= 0,
        delta_bb >= 0, delta_bs >= 0, delta_ss >= 0, delta_sb >= 0,
        new_pos_b == cur_position_b + delta_bb - delta_bs,
        new_pos_s == cur_position_s + delta_ss - delta_sb,
        new_pos == new_pos_b - new_pos_s,
        new_cap >= 250,
        delta_bb <= config['optimizer-max-add-order-size'],
        delta_ss <= config['optimizer-max-add-order-size'],
        # This constraint eliminates the possibility of going wildly from
        # max long to max short, which should be ok
        net_cost + cp.multiply(price_b, delta_bb) <= PIPOSITION_LIMIT_VALUE,
        net_cost + cp.multiply(price_s, delta_ss) <= PIPOSITION_LIMIT_VALUE,
    ]

    # this isn't literally the stdev, just trying to convey the idea that as the position size increases, we
    # want the edge required to increase linearly
    # maybe we want to do something more like kelly-betting instead of creating fake
    # variance as if it's normal distributed?
    stdev_return = cp.sum_squares(new_pos)

    # add constant for when margin_factors is empty to ensure obj_factor has type Expr
    obj_factor = -1 * cp.sum(margin_factors) + cp.expressions.constants.Constant(0)
    obj_return = agg_price_model @ new_pos_b + (1 - agg_price_model) @ new_pos_s + new_cap
    obj_std = -1 * config['optimizer-std-penalty'] * stdev_return

    objective = obj_return + obj_std + obj_factor
    problem = cp.Problem(cp.Maximize(objective), constraints)

    try:
        problem.solve(solver=cp.ECOS, abstol=2.0, reltol=1e-4, feastol=1e-4, verbose=True)
    except cp.error.SolverError as e:
        solver_error = True
        print('Solver error', str(e))
    else:
        solver_error = False

    if problem.status not in cvxpy.settings.SOLUTION_PRESENT:
        print('Solver completed with unexpected status', problem.status)
        print(delta_bb.value, delta_bs.value, delta_sb.value, delta_ss.value)
        solver_error = True

    if solver_error:
        if not config['optimizer-allow-unsolved']:
            assert False

        opt_res = {
            'new_pos': cur_position,
            'agg_price_model': agg_price_model,
        }
        df = pd.DataFrame(opt_res, index=snapshot.universe)
        df['take_edge'] = 0.0
        return df

    logging.info((obj_return.value, obj_std.value, obj_factor.value))

    pos_mult = config['optimizer-position-size-mult']
    rounded_new_pos = np.around(new_pos.value / pos_mult) * pos_mult
    opt_res = {
        'new_pos': rounded_new_pos,
        'agg_price_model': agg_price_model,
    }
    df = pd.DataFrame(opt_res, index=snapshot.universe)
    df['take_edge'] = config['optimizer-take-edge']
    return df

import argparse
import logging
import datetime

import numpy as np
import cvxpy as cp

import pi_trading_lib.data.resolution
import pi_trading_lib.timers
import pi_trading_lib.date_util as date_util
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.model_config as model_config
import pi_trading_lib.tune as tune
import pi_trading_lib.logging_ext as logging_ext
from pi_trading_lib.accountant import PositionChange, Book
from pi_trading_lib.model import StandardModel, PIPOSITION_LIMIT_VALUE
from pi_trading_lib.models.fte_election import NaiveModel


def optimize_date(config: model_config.Config, model: StandardModel, cur_date: datetime.date, book: Book):
    universe = book.universe
    num_contracts = len(universe)

    eod = datetime.datetime.combine(cur_date, datetime.time.max)
    md = market_data.get_snapshot(eod, tuple(universe.tolist()))
    md_sod = market_data.get_snapshot(cur_date, tuple(universe.tolist()))

    return_model = model.get_return(config, cur_date)
    assert return_model is not None
    factor_models = model.get_factors(config, cur_date)

    price_b, price_s = md_sod['ask_price'].to_numpy(), (1 - md_sod['bid_price']).to_numpy()

    # widen to reduce trading (even if we could execute as best bid/ask)
    price_b = price_b + config['election_trading_cost']
    price_s = price_s + config['election_trading_cost']

    price_bb, price_bs, price_sb, price_ss = price_b, 1 - price_s, 1 - price_b, price_s
    margin_f = factor_models[0]

    p_win = return_model
    contract_return_stdev = np.sqrt(p_win * (1 - p_win) ** 2 + (1 - p_win) * (0 - p_win) ** 2)

    # Contracts to sell or buy
    cur_position = book.position
    cur_position_b = np.maximum(np.zeros(num_contracts), cur_position)
    cur_position_s = np.maximum(np.zeros(num_contracts), cur_position * -1)

    delta_bb, delta_bs, delta_sb, delta_ss = cp.Variable(num_contracts), cp.Variable(num_contracts), cp.Variable(num_contracts), cp.Variable(num_contracts)
    new_pos = cp.Variable(num_contracts)
    new_pos_b, new_pos_s = cp.Variable(num_contracts), cp.Variable(num_contracts)

    delta_cap = price_sb @ delta_sb + price_bs @ delta_bs - price_bb @ delta_bb - price_ss @ delta_ss
    new_cap = book.capital + delta_cap

    margin_exp = margin_f @ new_pos

    constraints = [
        new_pos_b >= 0, new_pos_s >= 0,
        delta_bb >= 0, delta_bs >= 0, delta_ss >= 0, delta_sb >= 0,
        new_pos_b == cur_position_b + delta_bb - delta_bs,
        new_pos_s == cur_position_s + delta_ss - delta_sb,
        new_pos == new_pos_b - new_pos_s,
        new_cap >= 250,  # Equality should work here too, allow for rounding to work out hopefully
        cp.multiply(price_b, new_pos) <= PIPOSITION_LIMIT_VALUE, # TODO: this should be base on the value of our current pos + FIFO
        cp.multiply(-1 * price_s, new_pos) <= PIPOSITION_LIMIT_VALUE,
    ]
    exp_return = return_model @ new_pos_b + (1 - return_model) @ new_pos_s + new_cap
    contract_position_stdev = (
        cp.multiply(new_pos_b, contract_return_stdev) + cp.multiply(new_pos_s, contract_return_stdev)
    )
    stdev_return = cp.norm(contract_position_stdev)

    objective = exp_return - config['election_variance_weight'] * stdev_return - config['election_margin_f_weight'] * cp.abs(margin_exp)
    problem = cp.Problem(cp.Maximize(objective), constraints)
    problem.solve()

    logging.debug((exp_return.value, stdev_return.value, margin_exp.value))

    pos_mult = config['position_size_mult']
    rounded_new_pos = np.around(new_pos.value / pos_mult) * pos_mult
    position_change = PositionChange(book.position, rounded_new_pos)
    book.apply_position_change(position_change, md['bid_price'], md['ask_price'])
    book.set_mark_price(md['trade_price'])
    logging.debug(f'\n{book.get_summary()}\n')


@pi_trading_lib.timers.timer
def daily_sim(config: model_config.Config, model: StandardModel, begin_date: datetime.date, end_date: datetime.date):
    universe = model.get_universe(begin_date)
    book = Book(universe, config['capital'])

    for cur_date in date_util.date_range(begin_date, end_date):
        if market_data.bad_market_data(cur_date):
            continue

        optimize_date(config, model, cur_date, book)

    contract_res = pi_trading_lib.data.resolution.get_contract_resolution(universe.tolist())
    final_pos_res = np.array([contract_res[cid] for cid in universe.tolist()])
    book.set_mark_price(final_pos_res)
    print(book)

    return book.value, book.get_summary()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config')
    parser.add_argument('--search')
    parser.add_argument('--debug', action='store_true')

    args = parser.parse_args()

    if args.debug:
        logging_ext.init_logging(level=logging.DEBUG)

    config = model_config.get_config(args.config)
    naive_model = NaiveModel()

    def run_sim(sim_config: model_config.Config):
        return daily_sim(sim_config, naive_model, date_util.from_str(config['begin_date']),
                         date_util.from_str(config['end_date']))

    if args.search:
        overrides = tune.parse_search(args.search)
        tune.grid_search(config, overrides, run_sim)
    else:
        run_sim(config)

    pi_trading_lib.timers.report_timers()


if __name__ == "__main__":
    main()

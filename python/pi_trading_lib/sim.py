import argparse
import logging
import datetime
import sys

import numpy as np
import pandas as pd

import pi_trading_lib.data.resolution
import pi_trading_lib.timers
import pi_trading_lib.date_util as date_util
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.model_config as model_config
import pi_trading_lib.tune as tune
import pi_trading_lib.optimizer as optimizer
import pi_trading_lib.logging_ext as logging_ext
from pi_trading_lib.accountant import Book
from pi_trading_lib.models.fte_election import NaiveModel
from pi_trading_lib.model import Model


@pi_trading_lib.timers.timer
def optimize_date(model: Model, cur_date: datetime.date, book: Book, config: model_config.Config):
    # TODO: add resolved contracts as 0/1
    model_universe = model.get_universe(cur_date)
    daily_universe = np.sort(model_universe)
    md_sod = market_data.get_snapshot(cur_date, tuple(set(book.universe.tolist() + daily_universe.tolist())))
    book.update_universe(daily_universe, md_sod)

    price_model = model.get_price(config, cur_date)
    assert price_model is not None
    factor_model = model.get_factor(config, cur_date)
    assert factor_model is not None

    price_model = price_model.reindex(daily_universe)
    factor_model = factor_model.reindex(daily_universe)
    md_sod = md_sod.reindex(daily_universe)

    new_pos = optimizer.optimize(book, md_sod, [price_model], [], [factor_model], config)

    book.apply_position_change(new_pos.to_numpy(), md_sod)
    book.set_mark_price(md_sod['trade_price'])
    logging.debug(f'\n{book.get_summary()}\n')


@pi_trading_lib.timers.timer
def daily_sim(model: Model, begin_date: datetime.date, end_date: datetime.date, config: model_config.Config):
    book = Book(np.array([], dtype=int), config['capital'])

    for cur_date in date_util.date_range(begin_date, end_date):
        if market_data.bad_market_data(cur_date):
            continue

        optimize_date(model, cur_date, book, config)

    contract_res = pi_trading_lib.data.resolution.get_contract_resolution(book.universe.tolist())
    final_pos_res = np.array([contract_res[cid] for cid in book.universe.tolist()])
    res_series = pd.Series(final_pos_res, index=book.universe.cids)
    book.set_mark_price(res_series)
    print(book)

    return book.value, book.get_summary()


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('config')
    parser.add_argument('--search')
    parser.add_argument('--debug', action='store_true')

    args = parser.parse_args(argv)

    if args.debug:
        logging_ext.init_logging(level=logging.DEBUG)

    config = model_config.get_config(args.config)
    naive_model = NaiveModel()

    def run_sim(sim_config: model_config.Config):
        return daily_sim(naive_model, date_util.from_str(config['begin_date']),
                         date_util.from_str(config['end_date']), sim_config)

    if args.search:
        overrides = tune.parse_search(args.search)
        tune.grid_search(overrides, run_sim, config)
    else:
        run_sim(config)

    pi_trading_lib.timers.report_timers()


if __name__ == "__main__":
    main(sys.argv[1:])

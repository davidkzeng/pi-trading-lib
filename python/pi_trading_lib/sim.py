import argparse
import logging
import datetime

import numpy as np

import pi_trading_lib.data.resolution
import pi_trading_lib.timers
import pi_trading_lib.date_util as date_util
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.model_config as model_config
import pi_trading_lib.tune as tune
import pi_trading_lib.logging_ext as logging_ext
from pi_trading_lib.accountant import PositionChange, Book
from pi_trading_lib.model import PositionModel
from pi_trading_lib.models.fte_election import NaiveModel


@pi_trading_lib.timers.timer
def daily_sim(config: model_config.Config, model: PositionModel, begin_date: datetime.date, end_date: datetime.date):
    universe = model.get_universe(begin_date)
    book = Book(universe, config['capital'])

    for cur_date in date_util.date_range(begin_date, end_date):
        if market_data.bad_market_data(cur_date):
            continue

        eod = datetime.datetime.combine(cur_date, datetime.time.max)
        md = market_data.get_snapshot(eod, tuple(universe.tolist()))

        new_pos = model.optimize(config, cur_date, book.capital, book.position)
        pos_mult = config['position_size_mult']
        rounded_new_pos = np.around(new_pos / pos_mult) * pos_mult
        position_change = PositionChange(book.position, rounded_new_pos)
        book.apply_position_change(position_change, md['bid_price'], md['ask_price'])
        book.set_mark_price(md['trade_price'])
        logging.debug(f'\n{book.get_summary()}\n')

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

import argparse
import datetime
import logging
import os
import sys
import typing as t

import numpy as np
import pandas as pd

from pi_trading_lib.accountant import Book
from pi_trading_lib.model import Model
from pi_trading_lib.models.calibration import CalibrationModel
from pi_trading_lib.models.fte_election import NaiveModel
from pi_trading_lib.score import SimResult
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.data.resolution
import pi_trading_lib.date_util as date_util
import pi_trading_lib.logging_ext as logging_ext
import pi_trading_lib.model_config as model_config
import pi_trading_lib.optimizer as optimizer
import pi_trading_lib.timers
import pi_trading_lib.tune as tune
import pi_trading_lib.work_dir as work_dir


@pi_trading_lib.timers.timer
def optimize_date(models: t.List[Model], cur_date: datetime.date, book: Book, config: model_config.Config):
    model_universes = [model.get_universe(cur_date) for model in models]
    model_universe = np.concatenate(model_universes)
    daily_universe = np.sort(np.unique(model_universe))

    combined_universe = tuple(set(book.universe.tolist() + daily_universe.tolist()))
    md_sod = market_data.get_snapshot(cur_date, combined_universe)
    resolutions = pi_trading_lib.data.resolution.get_contract_resolution(combined_universe, date=cur_date)
    resolutions = {cid: res for cid, res in resolutions.items() if res is not None}
    dead_contracts = set(daily_universe) & set(resolutions.keys())
    assert len(dead_contracts) == 0, f'Model universe has dead contracts{dead_contracts}'

    book.apply_resolutions(resolutions)
    book.update_universe(daily_universe, md_sod)

    price_models = []
    factor_models = []
    for model in models:
        price_model = model.get_price(config, cur_date)
        factor_model = model.get_factor(config, cur_date)
        if price_model is not None:
            price_model = price_model.reindex(daily_universe)
            price_models.append(price_model)
        if factor_model is not None:
            factor_model = factor_model.reindex(daily_universe)
            factor_models.append(factor_model)

    md_sod = md_sod.reindex(daily_universe)
    new_pos = optimizer.optimize(book, md_sod, price_models, [], factor_models, config)

    book.apply_position_change(new_pos, md_sod)
    book.set_mark_price(md_sod['trade_price'])
    logging.debug(f'\n{book.get_summary()}')


@pi_trading_lib.timers.timer
def daily_sim(models: t.List[Model], begin_date: datetime.date, end_date: datetime.date,
              config: model_config.Config) -> SimResult:
    result_uri = work_dir.get_uri('sim', config, date_1=end_date)
    if os.path.exists(result_uri):
        return SimResult.load(result_uri)

    book = Book(np.array([], dtype=int), config['capital'])

    book_summaries = []

    for cur_date in date_util.date_range(begin_date, end_date):
        if market_data.bad_market_data(cur_date):
            continue

        optimize_date(models, cur_date, book, config)
        book_summary = book.get_summary()
        book_summary['date'] = cur_date
        book_summary = book_summary.reset_index(drop=True).set_index('date')
        book_summaries.append(book_summary)

    daily_summary = pd.concat(book_summaries)

    if config['use-final-res']:
        contract_res = pi_trading_lib.data.resolution.get_contract_resolution(book.universe.tolist())
        final_pos_res = np.array([contract_res[cid] for cid in book.universe.tolist()])
        res_series = pd.Series(final_pos_res, index=book.universe.cids, dtype='float64')
        book.set_mark_price(res_series)
    logging.debug(f'\n{book}')

    result = SimResult(book.get_summary(), book.get_contract_summary(), daily_summary)
    result.dump(result_uri)
    return result


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('config')
    parser.add_argument('--search')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--override')
    parser.add_argument('--force', action='store_true')

    args = parser.parse_args(argv)

    if args.debug:
        logging_ext.init_logging(level=logging.DEBUG)

    if args.force:
        work_dir.cleanup()

    config = model_config.get_config(args.config)

    models = []
    if config['election-model-enabled']:
        models.append(NaiveModel())
    if config['calibration-model-enabled']:
        models.append(CalibrationModel())

    def run_sim(sim_config: model_config.Config) -> SimResult:
        return daily_sim(models, date_util.from_str(config['sim-begin-date']),
                         date_util.from_str(config['sim-end-date']), sim_config)

    if args.search:
        overrides = tune.parse_search(args.search)
    else:
        overrides = []

    tune.grid_search(config, overrides, run_sim)

    pi_trading_lib.timers.report_timers()


if __name__ == "__main__":
    main(sys.argv[1:])

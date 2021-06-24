import argparse
import datetime
import logging
import os
import sys
import typing as t

import numpy as np
import pandas as pd

from pi_trading_lib.accountant import Book
from pi_trading_lib.fillstats import Fillstats
from pi_trading_lib.model import Model
from pi_trading_lib.models.calibration import CalibrationModel
from pi_trading_lib.models.fte_election import NaiveModel
from pi_trading_lib.score import SimResult
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.data.resolution
import pi_trading_lib.date_util as date_util
import pi_trading_lib.decorators
import pi_trading_lib.logging_ext as logging_ext
import pi_trading_lib.model_config as model_config
import pi_trading_lib.optimizer as optimizer
import pi_trading_lib.timers
import pi_trading_lib.tune as tune
import pi_trading_lib.work_dir as work_dir


class SimState:
    def __init__(self, models: t.List[Model], book: Book, fillstats: Fillstats):
        self.models = models
        self.book = book
        self.fillstats = fillstats


@pi_trading_lib.timers.timer
@pi_trading_lib.decorators.impure
def optimize_date(cur_date: datetime.date, config: model_config.Config, sim_state: SimState):
    models, book = sim_state.models, sim_state.book

    model_universes = [model.get_universe(config, cur_date) for model in models]
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
    price_model_names = []
    price_model_weights = []
    factor_models = []
    for model in models:
        price_model = model.get_price(config, cur_date)
        factor_model = model.get_factor(config, cur_date)
        if price_model is not None:
            price_model = price_model.reindex(daily_universe)
            price_models.append(price_model)
            price_model_names.append(model.name)
            price_model_weights.append(config[f'return-weight-{model.name}'])
        if factor_model is not None:
            factor_model = factor_model.reindex(daily_universe)
            factor_models.append(factor_model)

    md_sod = md_sod.reindex(daily_universe)
    opt_result = optimizer.optimize(book, md_sod, price_models, price_model_weights, [], factor_models, config)
    new_pos = opt_result['new_pos']

    fills = book.apply_position_change(new_pos, md_sod)
    for fill in fills:
        fill.add_sim_info(cur_date)
        cid = fill.info['cid']
        for idx, price_model in enumerate(price_models):
            fill.add_model_info({f'model_price_{price_model_names[idx]}': price_model.loc[cid]})
        fill.add_opt_info({'agg_price_model': opt_result['agg_price_model'].loc[cid]})
        fill.add_computed_info()

    sim_state.fillstats.add_fills(fills)
    book.set_mark_price(md_sod['trade_price'])
    logging.debug(f'\n{book.get_summary()}')


@pi_trading_lib.timers.timer
def daily_sim(begin_date: datetime.date, end_date: datetime.date,
              config: model_config.Config) -> SimResult:
    result_uri = work_dir.get_uri('sim', config, date_1=end_date)
    if os.path.exists(result_uri):
        return SimResult.load(result_uri)

    # Init stateful sim portion
    book = Book(np.array([], dtype=int), config['capital'])
    models: t.List[Model] = []
    if config['election-model-enabled']:
        models.append(NaiveModel())
    if config['calibration-model-enabled']:
        models.append(CalibrationModel())
    fillstats = Fillstats()

    sim_state = SimState(models, book, fillstats)

    book_summaries = []
    cid_summaries = []

    for cur_date in date_util.date_range(begin_date, end_date):
        logging.info('sim for: ' + str(cur_date))

        if market_data.bad_market_data(cur_date):
            continue

        optimize_date(cur_date, config, sim_state)
        cid_summary = book.get_contract_summary()
        cid_summary['date'] = cur_date
        cid_summary = cid_summary.reset_index().set_index(['date', 'cid'])

        book_summary = book.get_summary()
        book_summary['date'] = cur_date
        book_summary = book_summary.reset_index(drop=True).set_index('date')
        book_summaries.append(book_summary)
        cid_summaries.append(cid_summary)

    daily_summary = pd.concat(book_summaries)
    daily_cid_summary = pd.concat(cid_summaries)

    if config['use-final-res']:
        contract_res = pi_trading_lib.data.resolution.get_contract_resolution(book.universe.tolist())
        final_pos_res = np.array([contract_res[cid] for cid in book.universe.tolist()])
        res_series = pd.Series(final_pos_res, index=book.universe.cids, dtype='float64')
        book.set_mark_price(res_series)
    logging.debug(f'\n{book}')

    result = SimResult(book.get_summary(), book.get_contract_summary(), daily_summary,
                       daily_cid_summary, fillstats.to_frame(), path=result_uri)
    result.dump()
    return result


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='current')
    parser.add_argument('--search')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--override', default='')
    parser.add_argument('--force', nargs='*')
    parser.add_argument('--force-all', action='store_true')

    args = parser.parse_args(argv)

    if args.debug:
        logging_ext.init_logging(level=logging.DEBUG)
    else:
        logging_ext.init_logging()

    if args.force_all:
        work_dir.cleanup()
    elif args.force:
        work_dir.cleanup(stages=args.force)

    config = model_config.get_config(args.config)

    def run_sim(sim_config: model_config.Config) -> SimResult:
        return daily_sim(date_util.from_str(sim_config['sim-begin-date']),
                         date_util.from_str(sim_config['sim-end-date']), sim_config)

    if args.search:
        search = tune.parse_search(args.search)
    else:
        search = []

    tune.grid_search(config, search, args.override, run_sim)

    pi_trading_lib.timers.report_timers()


if __name__ == "__main__":
    main(sys.argv[1:])

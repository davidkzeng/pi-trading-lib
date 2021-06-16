import argparse
import datetime

import numpy as np

import pi_trading_lib.data.resolution
import pi_trading_lib.date_util as date_util
import pi_trading_lib.data.market_data as market_data
from pi_trading_lib.accountant import PositionChange, Book
from pi_trading_lib.model import PositionModel
from pi_trading_lib.models.fte_state_pres import NaiveModel


def daily_sim(model: PositionModel, begin_date: datetime.date, end_date: datetime.date):
    universe = model.get_universe(begin_date)
    book = Book(universe, 10000.0)

    for cur_date in date_util.date_range(begin_date, end_date):
        if market_data.bad_market_data(cur_date):
            continue

        eod = datetime.datetime.combine(cur_date, datetime.time.max)
        md = market_data.get_snapshot(eod, tuple(universe.tolist()))

        print(md)
        bid_price = md['bid_price'].to_numpy()
        ask_price = md['ask_price'].to_numpy()
        mark_price = md['trade_price'].to_numpy()

        new_pos = model.optimize(cur_date, book.capital, book.position)
        rounded_new_pos = np.round(new_pos)
        position_change = PositionChange(book.position, rounded_new_pos)
        book.apply_position_change(position_change, bid_price, ask_price)
        book.set_mark_price(mark_price)
        print(book)

    contract_res = pi_trading_lib.data.resolution.get_contract_resolution(universe.tolist())
    final_pos_res = np.array([contract_res[cid] for cid in universe.tolist()])
    book.set_mark_price(final_pos_res)
    print(book)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config')

    args = parser.parse_args()
    assert args.config # TEMP

    naive_model = NaiveModel()
    daily_sim(naive_model, date_util.from_str('20201015'), date_util.from_str('20201030'))


if __name__ == "__main__":
    main()

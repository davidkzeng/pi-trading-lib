import argparse
import datetime

import numpy as np
import pandas as pd

import pi_trading_lib.data.resolution
import pi_trading_lib.date_util as date_util
import pi_trading_lib.numpy_ext as np_ext
import pi_trading_lib.data.market_data as market_data
from pi_trading_lib.model import PositionModel
from pi_trading_lib.models.fte_state_pres import NaiveModel

bad_days = [
    '20200917',
    '20200922',
    '20200923',
    '20201008',
    '20201012',
]


class PositionChange:
    def __init__(self, cur_pos: np.ndarray, new_pos: np.ndarray):
        self.cur_pos = cur_pos
        self.new_pos = new_pos
        self.diff = self.new_pos - self.cur_pos
        self.b_qty = np_ext.pos(self.diff)
        self.s_qty = -np_ext.neg(self.diff)

        self.bb_qty = np.minimum(self.b_qty, np_ext.pos(new_pos))
        self.sb_qty = np.minimum(self.b_qty, -np_ext.neg(cur_pos))

        self.bs_qty = np.minimum(self.s_qty, np_ext.pos(cur_pos))
        self.ss_qty = np.minimum(self.s_qty, -np_ext.neg(new_pos))

        assert (self.b_qty - self.s_qty == self.diff).all()
        assert (self.bb_qty + self.sb_qty == self.b_qty).all()
        assert (self.bs_qty + self.ss_qty == self.s_qty).all()

    def delta_cap(self, best_bid: np.ndarray, best_ask: np.ndarray) -> float:
        return np.sum(self.sb_qty * (1 - best_ask) - self.bb_qty * best_ask + self.bs_qty * best_bid - self.ss_qty * (1 - best_bid))  # type: ignore


def daily_sim(model: PositionModel, begin_date: datetime.date, end_date: datetime.date):
    universe = model.get_universe(begin_date)
    num_contracts = len(universe)
    current_pos = np.zeros(num_contracts)
    current_cap = 10000.0

    for cur_date in date_util.date_range(begin_date, end_date):
        if date_util.to_str(cur_date) in bad_days:
            continue

        state_md = market_data.get_df(cur_date, cur_date, contracts=tuple(universe.tolist()),
                                      snapshot_interval=datetime.timedelta(days=1))
        state_md = state_md.reset_index().set_index('contract_id').reindex(universe)
        bid_price = state_md['best_bid_price'].to_numpy()
        ask_price = state_md['best_ask_price'].to_numpy()

        new_pos = model.optimize(cur_date, current_cap, current_pos)
        rounded_new_pos = np.round(new_pos)
        position_change = PositionChange(current_pos, new_pos)
        delta_cap = position_change.delta_cap(bid_price, ask_price)

        current_pos = rounded_new_pos
        current_cap = current_cap + delta_cap
        current_mark = np.dot(bid_price, np_ext.pos(current_pos)) + np.dot(1 - ask_price, -np_ext.neg(current_pos)) + current_cap
        print(current_pos)
        print(current_cap)
        print(current_mark)

    contract_res = pi_trading_lib.data.resolution.get_contract_resolution(universe.tolist())
    final_pos_res = np.array([contract_res[cid] for cid in universe.tolist()])

    debug = pd.DataFrame([], index=universe)
    debug['res'] = final_pos_res
    debug['val'] = np.round(np_ext.pos(current_pos) * final_pos_res) + np.round(-np_ext.neg(current_pos) * (1 - final_pos_res))
    final_pos_val = np.sum(debug['val'])
    print(final_pos_val + current_cap, current_cap)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config')

    args = parser.parse_args()
    assert args.config # TEMP

    naive_model = NaiveModel()
    daily_sim(naive_model, date_util.from_str('20201015'), date_util.from_str('20201030'))


if __name__ == "__main__":
    main()

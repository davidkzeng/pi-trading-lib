import typing as t

import numpy as np
import pandas as pd

import pi_trading_lib.numpy_ext as np_ext
import pi_trading_lib.data.contracts


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


class Book:
    universe: np.ndarray
    universe_names: t.List[str]
    num_contracts: int
    capital: float
    position: np.ndarray
    mark_price: np.ndarray
    value: float

    def __init__(self, universe: np.ndarray, capital: float, initial_pos: t.Optional[np.ndarray] = None, mark_price: t.Optional[np.ndarray] = None):
        self.universe = universe
        contract_names = pi_trading_lib.data.contracts.get_contract_names(self.universe.tolist())
        self.universe_names = [contract_names[cid] for cid in self.universe]
        self.num_contracts = len(self.universe)
        self.capital = capital

        if initial_pos is None:
            initial_pos = np.zeros(self.num_contracts)
        self.position = initial_pos

        if mark_price is None:
            mark_price = np.zeros(self.num_contracts)
        self.set_mark_price(mark_price)

    def apply_position_change(self, change: PositionChange, bid_price: np.ndarray, ask_price: np.ndarray):
        delta_cap = np.sum(change.sb_qty * (1 - ask_price) - change.bb_qty * ask_price + change.bs_qty * bid_price - change.ss_qty * (1 - bid_price))
        self.capital += delta_cap
        self.position = change.new_pos
        self.recompute()

    def set_mark_price(self, mark_price: np.ndarray):
        assert len(mark_price) == self.num_contracts
        self.mark_price = mark_price
        self.recompute()

    def recompute(self):
        self.mark_value = self.mark_price * np_ext.pos(self.position) + (1 - self.mark_price) * -np_ext.neg(self.position)
        self.value = np.sum(self.mark_value) + self.capital

    def get_summary(self) -> t.Tuple[pd.DataFrame, pd.Series]:
        summary_contracts = pd.DataFrame({
            'position': self.position,
            'val': self.mark_price,
            'name': self.universe_names
        }, index=self.universe)
        summary = pd.Series({
            'capital': self.capital,
            'value': self.value
        })
        return summary_contracts, summary

    def __str__(self):
        summary_contracts, summary = self.get_summary()
        res = str(summary_contracts)
        res += "\n"
        res += str(summary)
        return res

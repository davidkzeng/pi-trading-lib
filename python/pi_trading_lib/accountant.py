import typing as t

import numpy as np
import pandas as pd

import pi_trading_lib.numpy_ext as np_ext
import pi_trading_lib.data.contracts
from pi_trading_lib.data.market_data import MarketDataSnapshot


class PositionChange:
    def __init__(self, cur_pos: np.ndarray, new_pos: np.ndarray):
        self.size = len(cur_pos)

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

    def exe_qty(self) -> np.ndarray:
        return np.abs(self.diff)  # type: ignore


class Universe:
    cids: np.ndarray
    names: t.List[str]
    mapping: t.Dict[int, int]
    size: int

    def __init__(self, cids: np.ndarray):
        assert cids.ndim == 1
        self.cids = cids
        self.size = len(cids)
        name_map = pi_trading_lib.data.contracts.get_contract_names(self.cids.tolist())
        self.names = [name_map[cid] for cid in self.cids]
        self.mapping = Universe.get_map(self.cids)

    @staticmethod
    def get_map(cids: np.ndarray) -> t.Dict[int, int]:
        return {x: index[0] for index, x in np.ndenumerate(cids)}

    @pi_trading_lib.timers.timer
    def rebroadcast(self, arr: np.ndarray, src_universe: np.ndarray) -> np.ndarray:
        assert arr.ndim == 1
        assert arr.shape == src_universe.shape

        vget = np.vectorize(self.mapping.__getitem__)
        new_idxs = vget(src_universe)
        target_arr = np.empty(self.size)
        target_arr[new_idxs] = arr
        return target_arr  # type: ignore


class Book:
    universe: Universe
    capital: float
    position: np.ndarray
    mark_price: np.ndarray
    value: float
    exe_qty: np.ndarray
    exe_value: np.ndarray

    def __init__(self, cids: np.ndarray, capital: float, initial_pos: t.Optional[np.ndarray] = None, mark_price: t.Optional[np.ndarray] = None):
        self.universe = Universe(cids)
        self.capital = capital

        if initial_pos is None:
            initial_pos = np.zeros(self.universe.size)
        self.position = initial_pos

        if mark_price is None:
            mark_price = np.zeros(self.universe.size)

        self.exe_qty = np.zeros(self.universe.size)
        self.exe_value = np.zeros(self.universe.size)
        self.set_mark_price(mark_price)
        self.recompute()

    def apply_position_change(self, change: PositionChange, snapshot: MarketDataSnapshot):
        assert len(snapshot.universe) == len(self.universe.cids)

        bid_price = snapshot['bid_price']
        ask_price = snapshot['ask_price']

        # We assume here that liquidity at TOB is enough to implement the position change
        change_cost = change.sb_qty * (1 - ask_price) - change.bb_qty * ask_price + change.bs_qty * bid_price - change.ss_qty * (1 - bid_price)
        self.capital += np.sum(change_cost)
        self.position = change.new_pos
        self.exe_qty += change.exe_qty()
        self.exe_value += np.abs(change_cost)
        self.recompute()

    def set_mark_price(self, mark_price: np.ndarray):
        assert len(mark_price) == self.universe.size
        self.mark_price = mark_price
        self.recompute()

    def recompute(self):
        self.mark_value = self.mark_price * np_ext.pos(self.position) + (1 - self.mark_price) * -np_ext.neg(self.position)
        self.value = np.sum(self.mark_value) + self.capital

    def get_contract_summary(self) -> pd.DataFrame:
        summary_contracts = pd.DataFrame({
            'position': self.position,
            'val': self.mark_value,
            'exe_qty': self.exe_qty,
            'exe_val': self.exe_value,
            'name': self.universe.names,
        }, index=self.universe.cids)
        return summary_contracts

    def get_summary(self) -> pd.Series:
        summary = pd.Series({
            'capital': self.capital,
            'pos_value': np.sum(self.mark_value),
            'value': self.value,
            'exe_qty': np.sum(self.exe_qty),
            'exe_val': np.sum(self.exe_value),
        })
        return summary

    def __str__(self):
        summary_contracts, summary = self.get_contract_summary(), self.get_summary()
        res = str(summary_contracts)
        res += "\n"
        res += str(summary)
        return res

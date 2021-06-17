import typing as t
import logging

import numpy as np
import pandas as pd

import pi_trading_lib.numpy_ext as np_ext
import pi_trading_lib.data.contracts
from pi_trading_lib.data.market_data import MarketDataSnapshot


class PositionChange:
    def __init__(self, cur_pos: np.ndarray, new_pos: np.ndarray):
        assert len(cur_pos) == len(new_pos)

        self.size = len(cur_pos)

        self.cur_pos = cur_pos
        self.new_pos = new_pos
        self.new_pos[np.isnan(self.new_pos)] = self.cur_pos[np.isnan(self.new_pos)]
        self.diff = self.new_pos - self.cur_pos
        self.b_qty = np_ext.pos(self.diff)
        self.s_qty = -np_ext.neg(self.diff)

        self.bb_qty = np.minimum(self.b_qty, np_ext.pos(self.new_pos))
        self.sb_qty = np.minimum(self.b_qty, -np_ext.neg(self.cur_pos))

        self.bs_qty = np.minimum(self.s_qty, np_ext.pos(self.cur_pos))
        self.ss_qty = np.minimum(self.s_qty, -np_ext.neg(self.new_pos))

        assert (self.b_qty - self.s_qty == self.diff).all()
        assert (self.bb_qty + self.sb_qty == self.b_qty).all()
        assert (self.bs_qty + self.ss_qty == self.s_qty).all()

    def exe_qty(self) -> np.ndarray:
        return np.abs(self.diff)  # type: ignore


class Universe:
    cids: np.ndarray
    active: np.ndarray
    names: t.List[str]
    mapping: t.Dict[int, int]
    size: int

    def __init__(self, cids: np.ndarray):
        assert cids.ndim == 1
        self.cids = np.array([], dtype=int)
        self.active = np.array([], dtype=bool)
        self.names = []
        self.mapping = {}
        self.size = 0

        if len(cids) > 0:
            self.update_cids(cids)

    @staticmethod
    def get_map(cids: np.ndarray) -> t.Dict[int, int]:
        return {x: index[0] for index, x in np.ndenumerate(cids)}

    @pi_trading_lib.timers.timer
    def reindex(self, arr: np.ndarray, src_universe: np.ndarray) -> np.ndarray:
        if np.all(src_universe == self.cids):
            return arr
        return np_ext.reindex(arr, src_universe, self.cids)

    def get_idxs(self, universe: np.ndarray) -> np.ndarray:
        vget = np.vectorize(self.mapping.__getitem__)
        idxs = vget(universe)
        return idxs  # type: ignore

    def tolist(self) -> t.List[int]:
        return self.cids.tolist()  # type: ignore

    def update_cids(self, cids: np.ndarray):
        new_cids = np.array(list(set(cids) - set(self.cids)))
        if len(new_cids) > 0:
            new_cids = np.sort(new_cids)
            self.cids = np.concatenate((self.cids, new_cids))

            name_map = pi_trading_lib.data.contracts.get_contract_names(new_cids.tolist())
            new_names = [name_map[cid] for cid in new_cids]
            self.names = self.names + new_names

            new_mapping = Universe.get_map(new_cids)
            self.mapping.update(new_mapping)

        self.size = len(self.cids)
        self.active = np.zeros(self.size, dtype=bool)
        active_cid_idxs = self.get_idxs(cids)
        self.active[active_cid_idxs] = True

    def __str__(self):
        return str(self.cids)


class Book:
    universe: Universe
    capital: float
    value: float
    position: np.ndarray
    mark_price: np.ndarray
    exe_qty: np.ndarray
    exe_value: np.ndarray

    def __init__(self, cids: np.ndarray, capital: float):
        self.universe = Universe(cids)
        self.capital = capital

        self.position = np.zeros(self.universe.size, dtype=int)
        self.exe_qty = np.zeros(self.universe.size)
        self.exe_value = np.zeros(self.universe.size)
        self.mark_price = np.zeros(self.universe.size)
        self.recompute()

    def apply_position_change(self, new_pos: pd.Series, snapshot: MarketDataSnapshot):
        assert np.all(new_pos.index == snapshot.universe)

        new_pos = new_pos.reindex(self.universe.cids).to_numpy()
        change = PositionChange(self.position, new_pos)

        bid_price = snapshot['bid_price'].reindex(self.universe.cids).to_numpy()
        ask_price = snapshot['ask_price'].reindex(self.universe.cids).to_numpy()
        missing_price = np.isnan(bid_price)
        assert not np.any(missing_price & (change.diff != 0)), "position change with missing price snapshot"

        # We assume here that liquidity at TOB is enough to implement the position change
        change_cost = np.nan_to_num(change.sb_qty * (1 - ask_price) - change.bb_qty * ask_price + change.bs_qty * bid_price - change.ss_qty * (1 - bid_price), 0.0)
        self.capital += np.sum(change_cost)
        self.position = change.new_pos
        self.exe_qty += change.exe_qty()
        self.exe_value += np.abs(change_cost)
        self.recompute()

    def set_mark_price(self, mark_price: pd.Series):
        mark_price = mark_price.reindex(self.universe.cids).to_numpy()
        self.mark_price[~np.isnan(mark_price)] = mark_price[~np.isnan(mark_price)]
        self.recompute()

    def recompute(self):
        self.mark_value = self.mark_price * np_ext.pos(self.position) + (1 - self.mark_price) * -np_ext.neg(self.position)
        self.value = np.sum(self.mark_value) + self.capital

    def update_universe(self, new_cids: np.ndarray, snapshot: MarketDataSnapshot):
        diff = set(self.universe.cids) ^ set(new_cids)
        if len(diff) == 0:
            return

        removed = set(self.universe.cids[self.position != 0]) - set(new_cids)

        old_size = self.universe.size
        self.universe.update_cids(new_cids)
        new_contracts = self.universe.size - old_size

        if new_contracts > 0:
            self.position = np.pad(self.position, (0, new_contracts), 'constant')
            self.exe_qty = np.pad(self.exe_qty, (0, new_contracts), 'constant')
            self.exe_value = np.pad(self.exe_value, (0, new_contracts), 'constant')
            self.mark_price = np.pad(self.mark_price, (0, new_contracts), 'constant')

        if len(removed) > 0:
            logging.info(f'Liquiditating positions for {removed}')
            new_pos = pd.Series(self.position.copy(), index=self.universe.cids)
            new_pos.loc[list(removed)] = 0
            new_pos = new_pos.reindex(snapshot.universe)
            self.apply_position_change(new_pos, snapshot)

        self.recompute()

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

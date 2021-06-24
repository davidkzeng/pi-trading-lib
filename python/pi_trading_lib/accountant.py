import typing as t
import logging

import numpy as np
import pandas as pd

from pi_trading_lib.data.market_data import MarketDataSnapshot
from pi_trading_lib.fifo import Fifo
from pi_trading_lib.fillstats import Fill
import pi_trading_lib.data.contracts
import pi_trading_lib.numpy_ext as np_ext


class PositionChange:
    def __init__(self, cur_pos: np.ndarray, new_pos: np.ndarray):
        assert len(cur_pos) == len(new_pos)

        self.size = len(cur_pos)

        self.cur_pos = cur_pos.copy()
        self.new_pos = new_pos.copy()
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

    def tolist(self) -> t.List[int]:
        return self.cids.tolist()  # type: ignore

    def update_cids(self, cids: np.ndarray):
        new_cids = np.array(list(set(cids) - set(self.cids)), dtype=int)
        if len(new_cids) > 0:
            new_cids = np.sort(new_cids)
            self.cids = np.concatenate((self.cids, new_cids))

            name_map = pi_trading_lib.data.contracts.get_contract_names(new_cids.tolist())
            new_names = [name_map[cid] for cid in new_cids]
            self.names = self.names + new_names

            new_mapping = Universe.get_map(new_cids)
            self.mapping.update(new_mapping)

        self.size = len(self.cids)
        active = pd.Series(np.zeros(self.size, dtype=bool), index=self.cids)
        active.loc[cids] = True
        self.active = active

    def __str__(self):
        return str(self.cids)


class Book:
    universe: Universe
    initial_capital: float
    capital: float
    value: float
    position: np.ndarray
    mark_price: np.ndarray
    exe_qty: np.ndarray
    exe_value: np.ndarray
    net_cost: np.ndarray
    pos_cost: np.ndarray
    mark_pnl: np.ndarray
    unrealized_pnl: np.ndarray
    fifo: Fifo

    def __init__(self, cids: np.ndarray, capital: float):
        self.universe = Universe(cids)
        self.initial_capital = capital
        self.capital = capital

        self.fifo = Fifo()

        self.position = np.zeros(self.universe.size, dtype=int)
        self.exe_qty = np.zeros(self.universe.size)
        self.exe_value = np.zeros(self.universe.size)
        self.mark_price = np.zeros(self.universe.size)
        self.net_cost = np.zeros(self.universe.size)
        self.pos_cost = np.zeros(self.universe.size)
        self.mark_pnl = np.zeros(self.universe.size)
        self.unrealized_pnl = np.zeros(self.universe.size)

        self._recompute()

    def _recompute(self):
        self.mark_value = self.mark_price * np_ext.pos(self.position) + (1 - self.mark_price) * -np_ext.neg(self.position)
        self.value = np.sum(self.mark_value) + self.capital

        self.pos_cost = self.fifo.pos_cost().reindex(self.universe.cids).fillna(0.0).to_numpy()
        self.pos_cost = np.around(self.pos_cost, decimals=2)
        self.unrealized_pnl = self.mark_value - self.pos_cost

        self.mark_pnl = self.mark_value - self.net_cost

    def set_mark_price(self, mark_price: pd.Series):
        mark_price = mark_price.reindex(self.universe.cids).to_numpy()
        self.mark_price[~np.isnan(mark_price)] = mark_price[~np.isnan(mark_price)]
        self._recompute()

    @pi_trading_lib.timers.timer
    def apply_position_change(self, new_pos: pd.Series, snapshot: MarketDataSnapshot) -> t.List[Fill]:
        assert np.all(new_pos.index == snapshot.universe)

        if len(new_pos) == 0:
            return []

        new_pos = new_pos.reindex(self.universe.cids).to_numpy()
        change = PositionChange(self.position, new_pos)

        bid_price = snapshot['bid_price'].reindex(self.universe.cids).to_numpy()
        ask_price = snapshot['ask_price'].reindex(self.universe.cids).to_numpy()
        missing_price = np.isnan(bid_price)
        assert not np.any(missing_price & (change.diff != 0)), "position change with missing price snapshot"

        # We assume here that liquidity at TOB is enough to implement the position change
        change_cost = -1 * np.nan_to_num(change.sb_qty * (1 - ask_price) - change.bb_qty * ask_price + change.bs_qty * bid_price - change.ss_qty * (1 - bid_price), 0.0)
        exe_value = np.abs(
            np.nan_to_num(change.sb_qty * (1 - ask_price), 0.0) +
            np.nan_to_num(-1 * change.bb_qty * ask_price, 0.0) +
            np.nan_to_num(change.bs_qty * bid_price, 0.0) +
            np.nan_to_num(-1 * change.ss_qty * (1 - bid_price), 0.0)
        )
        self.capital -= np.sum(change_cost)
        self.position = change.new_pos
        self.exe_qty += change.exe_qty()
        self.exe_value += np.abs(exe_value)
        self.net_cost += change_cost

        fifo_df = pd.DataFrame([], index=self.universe.cids)
        fifo_df['qty'] = change.diff
        fifo_df['price'] = np.nan
        fifo_df['price'] = fifo_df['price'].mask(fifo_df['qty'] > 0, ask_price)
        fifo_df['price'] = fifo_df['price'].mask(fifo_df['qty'] < 0, (1 - bid_price))
        fifo_df = fifo_df.dropna()
        self.fifo.process_pos_change(fifo_df)

        self._recompute()

        fills: t.List[Fill] = []
        fill_info = pd.DataFrame(
            np.array([change.cur_pos, change.diff, bid_price, ask_price,
                      change_cost, exe_value]).T,
            index=self.universe.cids,
            columns=Fill.BOOK_COLUMNS
        )
        fill_info.index.name = 'cids'
        fill_info = fill_info[fill_info['qty'] != 0]
        for _, fill in fill_info.iterrows():
            new_fill = Fill()
            new_fill.add_book_info(fill)
            fills.append(new_fill)
        return fills

    def apply_resolutions(self, resolutions: t.Dict[int, float]):
        resolution_ser = pd.Series(resolutions, name='resolution')
        resolution_ser = resolution_ser.reindex(self.universe.cids).to_numpy()

        resolution_value = (
            np.nan_to_num((self.position * resolution_ser) * (self.position > 0)) +
            np.nan_to_num((-1 * self.position * (1 - resolution_ser)) * (self.position < 0))
        )
        self.capital += np.sum(resolution_value)
        self.position[~np.isnan(resolution_ser)] = 0
        self.net_cost -= resolution_value
        self.fifo.resolve(resolutions)
        self._recompute()

    @pi_trading_lib.timers.timer
    def update_universe(self, new_cids: np.ndarray, snapshot: MarketDataSnapshot):
        """Expand book with new_cids and conform active book to new_cids"""
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
            self.unrealized_pnl = np.pad(self.unrealized_pnl, (0, new_contracts), 'constant')
            self.net_cost = np.pad(self.net_cost, (0, new_contracts), 'constant')

        if len(removed) > 0:
            logging.info(f'Liquiditating positions for {removed}')
            new_pos = pd.Series(self.position.copy(), index=self.universe.cids)
            new_pos.loc[list(removed)] = 0
            new_pos = new_pos.reindex(snapshot.universe)
            self.apply_position_change(new_pos, snapshot)

        self._recompute()

    def get_contract_summary(self) -> pd.DataFrame:
        summary_contracts = pd.DataFrame({
            'position': self.position,
            'val': self.mark_value,
            'exe_qty': self.exe_qty,
            'exe_val': self.exe_value,
            'mark_pnl': self.mark_pnl,
            'realized_pnl': self.mark_pnl - self.unrealized_pnl,
            'name': self.universe.names,
        }, index=self.universe.cids)
        summary_contracts.index.name = 'cid'
        return summary_contracts

    def get_summary(self) -> pd.DataFrame:
        summary = {
            'capital': self.capital,
            'pos_value': np.sum(self.mark_value),
            'value': self.value,
            'exe_qty': np.sum(self.exe_qty),
            'exe_val': np.sum(self.exe_value),
            'pos_cost': np.sum(self.pos_cost),
            'mark_pnl': np.sum(self.mark_pnl),
            'unrealized_pnl': np.sum(self.unrealized_pnl),
        }
        summary_df = pd.DataFrame([list(summary.values())], columns=list(summary))
        return summary_df

    def __str__(self):
        summary_contracts, summary = self.get_contract_summary(), self.get_summary()
        res = str(summary_contracts)
        res += "\n"
        res += str(summary)
        return res

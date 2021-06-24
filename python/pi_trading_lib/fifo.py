from collections import deque
from dataclasses import dataclass
import typing as t

import pandas as pd


@dataclass
class FifoEntry:
    cid: int
    price: int
    qty: float

    def __post_init__(self):
        assert self.price > 0
        assert self.qty != 0


# Currently not using the queue aspect but may be useful in the future
# if we want to annotate fill's Fifo PNL
class Fifo:
    def __init__(self):
        self.cid_fifo = {}  # cid -> [fifo queue]
        self.cid_realized_pnl = {} # cid -> float

    def process_pos_change(self, changes: pd.DataFrame):
        for cid, change in changes.iterrows():
            qty, price = change['qty'], change['price']
            entry = FifoEntry(cid, price, qty)
            self.apply_fifo(entry)

    def resolve(self, cids: t.Dict[int, float]):
        for cid in cids:
            if cid in self.cid_fifo:
                del self.cid_fifo[cid]

    def apply_fifo(self, entry: FifoEntry):
        cid = entry.cid

        if cid not in self.cid_fifo:
            self.cid_fifo[cid] = deque()

        cid_queue = self.cid_fifo[cid]

        while len(cid_queue) > 0:
            if entry.qty == 0:
                break

            front = cid_queue[0]
            if (front.qty > 0) == (entry.qty > 0):
                break

            self._match(front, entry)
            if front.qty == 0:
                cid_queue.popleft()

        if entry.qty != 0:
            cid_queue.append(entry)

        self._check_invariant(cid)

    def _match(self, old: FifoEntry, new: FifoEntry):
        assert old.cid == new.cid
        assert (old.qty > 0) != (new.qty > 0)

        cid = old.cid

        if cid not in self.cid_realized_pnl:
            self.cid_realized_pnl[cid] = 0.0

        if abs(old.qty) >= abs(new.qty):
            self.cid_realized_pnl[cid] += abs(new.qty) * (1 - new.price - old.price)
            old.qty += new.qty
            new.qty = 0
        else:
            self.cid_realized_pnl[cid] += abs(old.qty) * (1 - new.price - old.price)
            new.qty += old.qty
            old.qty = 0

    def _check_invariant(self, cid: int):
        if cid in self.cid_fifo:
            cid_queue = self.cid_fifo[cid]
            assert all(entry.qty > 0 for entry in cid_queue) or all(entry.qty < 0 for entry in cid_queue)

    def pos_cost(self) -> pd.Series:
        pos_costs = {}
        for cid, cid_queue in self.cid_fifo.items():
            cost = 0
            for entry in cid_queue:
                cost += abs(entry.qty) * entry.price
            pos_costs[cid] = cost
        pos_cost = pd.Series(pos_costs, name='net_cost')
        return pos_cost

    def realized_pnl(self) -> pd.Series:
        return pd.Series(self.cid_realized_pnl, name='realized_pnl')

from collections import deque
from dataclasses import dataclass
import typing as t

import pandas as pd


@dataclass
class FifoEntry:
    cid: int
    # price should be the the cost assuming we are increasing the long/short position (determined by qty)
    price: float
    qty: float

    def __post_init__(self):
        assert self.price >= 0
        assert self.qty != 0


# Currently not using the queue aspect but may be useful in the future
# if we want to annotate fill's Fifo PNL
class Fifo:
    def __init__(self):
        self.cid_fifo = {}  # cid -> [fifo queue]
        self.cid_realized_pnl = {} # cid -> float
        self.cid_fees = {} # cid -> float

    def process_pos_change(self, changes: pd.DataFrame) -> pd.Series:
        change_costs = {}
        for cid, change in changes.iterrows():
            qty, price = change['qty'], change['price']
            entry = FifoEntry(cid, price, qty)
            cost = self.apply_fifo(entry)
            change_costs[cid] = cost
        cost_ser = pd.Series(change_costs, name='cost')
        return cost_ser

    def resolve(self, cids: t.Dict[int, float]):
        for cid, res in cids.items():
            if cid in self.cid_fifo:
                queue = self.cid_fifo[cid]

                if len(queue) > 0:
                    qty_sum = 0
                    for entry in queue:
                        qty_sum += entry.qty
                    res_qty = -1 * qty_sum
                    if res_qty > 0:
                        self.apply_fifo(FifoEntry(cid, res, res_qty))
                    else:
                        self.apply_fifo(FifoEntry(cid, 1 - res, res_qty))

                assert len(self.cid_fifo[cid]) == 0
                del self.cid_fifo[cid]

    def apply_fifo(self, entry: FifoEntry) -> float:
        cost = 0.0
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

            cost += self._match(front, entry)
            if front.qty == 0:
                cid_queue.popleft()

        if entry.qty != 0:
            cid_queue.append(entry)
            cost += abs(entry.price * entry.qty)

        self._check_invariant(cid)
        return cost

    def _match(self, old: FifoEntry, new: FifoEntry) -> float:
        assert old.cid == new.cid
        assert (old.qty > 0) != (new.qty > 0)

        cid = old.cid

        if cid not in self.cid_realized_pnl:
            self.cid_realized_pnl[cid] = 0.0
        if cid not in self.cid_fees:
            self.cid_fees[cid] = 0.0

        # one way to think of this is that we pay the cost to go both long and short, and then get rewarded with a guaranteed payoff of 1
        if abs(old.qty) >= abs(new.qty):
            match_qty = new.qty
            fee = max(0, 0.1 * abs(match_qty) * (1 - new.price - old.price))
            cost = fee + (abs(match_qty) * (new.price - 1))
            self.cid_realized_pnl[cid] += abs(match_qty) * (1 - new.price - old.price)
            self.cid_fees[cid] += fee
            old.qty += match_qty
            new.qty = 0
        else:
            match_qty = old.qty
            fee = max(0, 0.1 * abs(match_qty) * (1 - new.price - old.price))
            cost = fee + (abs(match_qty) * (new.price - 1))
            self.cid_realized_pnl[cid] += abs(match_qty) * (1 - new.price - old.price)
            self.cid_fees[cid] += fee
            new.qty += match_qty
            old.qty = 0
        return cost

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

    def fees(self) -> pd.Series:
        return pd.Series(self.cid_fees, name='fees')

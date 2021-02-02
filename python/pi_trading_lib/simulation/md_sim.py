import typing as t

from pi_trading_lib.data.market_data import MarketDataProvider
from pi_trading_lib.simulation.components import SimNode


class MarketDataSim(SimNode[t.Optional[float]]):
    def __init__(self, universe: t.List[int], md_provider: MarketDataProvider) -> None:
        SimNode.__init__(self, universe)

        self.md_provider = md_provider
        self.cur_val: t.List[t.Optional[float]] = [None for _ in range(self.size)]

        # Used for sanity checking
        self.window_max_time = [0 for _ in range(self.size)]
        self.sampler_max_time = 0

        self.cur_time = 0

    def _process(self, timestamp: int, cid: int, price: float, valid: bool):
        if cid not in self.cid_idx:
            return
        idx: int = self.cid_idx[cid]

        assert timestamp >= self.sampler_max_time
        assert timestamp >= self.window_max_time[idx]

        if timestamp == self.window_max_time[idx]:
            return
        self.window_max_time[idx] = timestamp
        self.sampler_max_time = max(timestamp, self.sampler_max_time)

        self.cur_val[idx] = price

    def poll(self, timestamp: int):
        assert timestamp >= self.cur_time
        if timestamp == self.cur_time:
            return

        while True:
            next_timestamp = self.md_provider.peek_timestamp()
            if next_timestamp is None or next_timestamp > timestamp:
                break

            md_entry = self.md_provider.next()
            assert md_entry is not None

            self._process(md_entry.timestamp, md_entry.cid, md_entry.price, True)

        self.cur_time = timestamp

    def sample(self, universe: t.Optional[t.List[int]] = None) -> t.List[t.Optional[float]]:
        if universe is None:
            universe = self.universe

        return [self.cur_val[self.cid_idx[cid]] for cid in universe]

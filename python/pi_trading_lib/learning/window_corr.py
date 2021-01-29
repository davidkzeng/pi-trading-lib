import typing as t
import datetime
import itertools

import pandas as pd

from pi_trading_lib.constants import NANOS_IN_SECOND
from pi_trading_lib.data.market_data import DataFrameProvider
from pi_trading_lib.simulation.md_sim import MarketDataSim
from pi_trading_lib.simulation.components import EMA, EMA_ALPHA


# TODO: Extract this out into two window samplers
class WindowSampler:
    def __init__(self, md_sim: MarketDataSim, window_length: int, universe: t.List[int]) -> None:
        assert window_length >= 2

        self.ema_window_length = window_length
        self.universe = universe
        self.universe_size = len(self.universe)
        self.cid_idx = {}
        for idx, cid in enumerate(self.universe):
            self.cid_idx[cid] = idx

        self.ema = EMA(md_sim, EMA_ALPHA)
        self.md_sim = md_sim

        # TODO: See if we can optimize this a bit
        self.ema_window: t.List[t.List[float]] = [[] for _ in range(self.universe_size)]
        self.raw_window: t.List[t.List[float]] = [[] for _ in range(self.universe_size)]

        self.cur_time = 0

    def poll(self, timestamp: int):
        assert timestamp >= self.cur_time
        if timestamp == self.cur_time:
            return
        self.ema.poll(timestamp)
        self.md_sim.poll(timestamp)

        sample = self.ema.sample(universe=self.universe)
        raw_sample = self.md_sim.sample(universe=self.universe)
        for idx, (ema_val, raw_val) in enumerate(zip(sample, raw_sample)):
            if ema_val is None:
                self.ema_window[idx].clear()
                self.raw_window[idx].clear()
            else:
                assert raw_val is not None
                self.ema_window[idx].append(ema_val)
                self.raw_window[idx].append(raw_val)

            # TODO: Should this be 2n - 1 instead of 2n?
            if len(self.ema_window[idx]) > 2 * self.ema_window_length:
                self.ema_window[idx].pop(0)
                self.raw_window[idx].pop(0)

        self.cur_time = timestamp

    def _compute_window(self, cid: int) -> t.Optional[t.Tuple[float, float]]:
        idx = self.cid_idx[cid]
        window = self.ema_window[idx]
        raw_window = self.raw_window[idx]
        if len(window) == 2 * self.ema_window_length:
            return (window[self.ema_window_length - 1] - window[0], window[-1] - raw_window[self.ema_window_length])
        else:
            return None

    def sample(self, universe: t.Optional[t.List[int]] = None) -> t.List[t.Optional[t.Tuple[float, float]]]:
        if universe is None:
            universe = self.universe

        return [self._compute_window(cid) for cid in universe]


def sample_md(market_data: pd.DataFrame, window_length: int, sample_interval: int, universe: t.List[int]):
    md_provider = DataFrameProvider(market_data)
    md_sim = MarketDataSim(universe, md_provider)

    window_sampler = WindowSampler(md_sim, window_length, universe)

    start_time = market_data.index[0][0].value
    end_time = market_data.index[-1][0].value

    counter = 0
    samples: t.List[t.List[t.Optional[t.Tuple[float, float]]]] = []

    for cur_time in range(start_time, end_time, 1 * 60 * NANOS_IN_SECOND):
        window_sampler.poll(cur_time)
        if counter % sample_interval == 0:
            samples.append(window_sampler.sample())
        counter += 1

    flat_samples = list(itertools.chain(*samples))
    return [sample for sample in flat_samples if sample is not None]


if __name__ == "__main__":
    # For unit testing
    import pi_trading_lib.data.market_data as market_data

    data = market_data.get_df(datetime.datetime(2021, 1, 20).date(), datetime.datetime(2021, 1, 20).date())
    corrs = sample_md(data, 60, 10, [24804])
    print(corrs)

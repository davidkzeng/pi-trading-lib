import typing as t
import datetime
import itertools

import pandas as pd

from pi_trading_lib.constants import NANOS_IN_SECOND
from pi_trading_lib.data.market_data import DataFrameProvider
from pi_trading_lib.simulation.md_sim import MarketDataSim
from pi_trading_lib.simulation.components import SimNode, EMA, EMA_ALPHA, Return

R = t.TypeVar('R')
S = t.TypeVar('S')


class WindowSampler(SimNode[t.Optional[t.Tuple[R, S]]]):
    def __init__(self, back: SimNode[t.Optional[R]], front: SimNode[t.Optional[S]],
                 window_length: int, universe: t.List[int]) -> None:
        assert window_length >= 1

        self.window_length = window_length
        self.universe = universe
        self.size = len(self.universe)
        self.cid_idx = {}
        for idx, cid in enumerate(self.universe):
            self.cid_idx[cid] = idx

        self.back_input = back
        self.front_input = front

        self.back_window: t.List[t.List[t.Optional[R]]] = [[] for _ in range(self.size)]

        self.cur_time = 0

    def poll(self, timestamp: int):
        assert timestamp >= self.cur_time
        if timestamp == self.cur_time:
            return
        self.back_input.poll(timestamp)
        self.front_input.poll(timestamp)

        sample = self.back_input.sample(universe=self.universe)
        for idx, raw_val in enumerate(sample):
            self.back_window[idx].append(raw_val)

            if len(self.back_window[idx]) > self.window_length:
                self.back_window[idx].pop(0)

        self.cur_time = timestamp

    def sample(self, universe: t.Optional[t.List[int]] = None) -> t.List[t.Optional[t.Tuple[R, S]]]:
        if universe is None:
            universe = self.universe

        front_values = self.front_input.sample(universe=universe)

        def compute_window(cid):
            idx = self.cid_idx[cid]
            if len(self.back_window[idx]) < self.window_length:
                return None

            back_val, front_val = self.back_window[idx][0], front_values[idx]
            if back_val is not None and front_val is not None:
                return (back_val, front_val)
            else:
                return None
        return [compute_window(cid) for cid in universe]


def sample_md(market_data: pd.DataFrame, window_length: int, sample_interval: int, universe: t.List[int],
              ema_alpha=EMA_ALPHA):
    md_provider = DataFrameProvider(market_data)
    md_sim = MarketDataSim(universe, md_provider)
    md_ema = EMA(md_sim, EMA_ALPHA)

    back_window = WindowSampler(md_ema, md_ema, window_length, universe)
    front_window = WindowSampler(md_sim, md_ema, window_length, universe)

    back_return = Return(back_window, universe)
    front_return = Return(front_window, universe)

    window_sampler = WindowSampler(back_return, front_return, window_length, universe)

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
    # Write some testcases

    data = market_data.get_df(datetime.datetime(2021, 1, 20).date(), datetime.datetime(2021, 1, 20).date())
    corrs = sample_md(data, 60, 10, [24804])
    print(corrs)

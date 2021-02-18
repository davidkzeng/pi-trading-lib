import typing as t
import itertools

import pandas as pd

from pi_trading_lib.constants import NANOS_IN_MIN
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
        SimNode.__init__(self, universe, inputs=[back, front])

        self.front_input = front
        self.back_input = back

        self.back_window: t.List[t.List[t.Optional[R]]] = [[] for _ in range(self.size)]

        self.cur_time = 0

    def poll(self, timestamp: int):
        SimNode.poll(self, timestamp)

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


# sample self correlation
def sample_md(market_data: pd.DataFrame, window_length: int, sample_interval: int, universe: t.List[int],
              ema_alpha=EMA_ALPHA):
    md_provider = DataFrameProvider(market_data)
    md_sim = MarketDataSim(universe, md_provider)
    md_ema = EMA(md_sim, ema_alpha)

    back_window = WindowSampler(md_ema, md_ema, window_length, universe)
    front_window = WindowSampler(md_sim, md_sim, window_length, universe)

    back_return = Return(back_window, universe)
    front_return = Return(front_window, universe)

    window_sampler = WindowSampler(back_return, front_return, window_length + 1, universe)

    start_time = market_data.index[0][0].value
    end_time = market_data.index[-1][0].value

    counter = 0
    samples: t.List[t.List[t.Optional[t.Tuple[float, float]]]] = []

    for cur_time in range(start_time, end_time + 1, 1 * NANOS_IN_MIN):
        window_sampler.poll(cur_time)
        if counter % sample_interval == 0:
            """
            # debug
            print('md_sim', md_sim.sample())
            print('md_ema', md_ema.sample())
            print('back_window', back_window.sample())
            print('front_window', front_window.sample())
            print('back_return', back_return.sample())
            print('front_return', front_return.sample())
            print('return_window', window_sampler.sample())
            print('')
            """
            samples.append(window_sampler.sample())
        counter += 1

    flat_samples = list(itertools.chain(*samples))
    return [sample for sample in flat_samples if sample is not None]

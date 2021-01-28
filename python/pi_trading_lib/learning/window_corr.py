import typing as t
import datetime

import pandas as pd

from pi_trading_lib.constants import NANOS_IN_SECOND


# TODO: Determine if we need to move this to rust for performance improvement
class WindowSampler:
    def __init__(self, window_length: int, universe: t.List[int]) -> None:
        self.window_length = window_length
        self.universe = universe
        self.universe_size = len(self.universe)
        self.cid_idx = {}
        for idx, cid in enumerate(self.universe):
            self.cid_idx[cid] = idx

        self.sample_results: t.List[t.List[t.Tuple[float, float]]] = [[] for _ in range(self.universe_size)]

        # TODO: Replace with circular buffer queue?
        self.cur_val = [None for _ in range(self.universe_size)]
        self.ema_val = [None for _ in range(self.universe_size)]
        self.window: t.List[t.List[t.Tuple[int, float, bool]]] = [[] for _ in range(self.universe_size)]

        # Used for sanity checking
        self.window_max_time = [0 for _ in range(self.universe_size)]
        self.sampler_max_time = 0

    def sample(self, timestamp: int):
        # TODO: Try sampling by return vs absolute difference
        back_window_cutoff = timestamp - 2 * self.window_length
        front_window_cutoff = timestamp - self.window_length

        for idx in range(self.universe_size):
            if len(self.window[idx]) == 0 or self.window[idx][0][0] > back_window_cutoff:
                continue
            # TODO: implement less brute force version
            back, mid, front = None, None, None
            back_window_idx = -1
            cur_window_idx = 0

            while cur_window_idx < len(self.window[idx]) and self.window[idx][cur_window_idx][0] <= back_window_cutoff:
                cur_window_idx += 1
            _, price, _ = self.window[idx][cur_window_idx - 1]
            back = price
            back_window_idx = cur_window_idx

            while cur_window_idx < len(self.window[idx]) and self.window[idx][cur_window_idx][0] <= front_window_cutoff:
                cur_window_idx += 1
            _, price, _ = self.window[idx][cur_window_idx - 1]  # guaranteed valid if we reach this point
            mid = price

            _, price, _ = self.window[idx][-1]
            front = price

            for _ in range(back_window_idx):
                self.window[idx].pop(0)
            print(back, mid, front)
            self.sample_results[idx].append((mid - back, front - mid))

    def ema_process(self, cur_time):
        for idx in range(self.universe_size):
            if self.cur_val[idx] is None:
                continue

            if self.ema_val[idx] is None:
                self.ema_val[idx] = self.cur_val[idx]
            else:
                self.ema_val[idx] = 0.8 * self.ema_val[idx] + 0.2 * self.cur_val[idx]
            self.window[idx].append((cur_time, self.ema_val[idx], True))

    def process(self, timestamp: int, cid: int, price: float, valid: bool):
        if cid not in self.cid_idx:
            return
        idx = self.cid_idx[cid]

        assert timestamp >= self.sampler_max_time
        assert timestamp >= self.window_max_time[idx]

        if timestamp == self.window_max_time[idx]:
            return
        self.window_max_time[idx] = timestamp
        self.sampler_max_time = max(timestamp, self.sampler_max_time)

        self.cur_val[idx] = price

    def output(self):
        return self.sample_results


def sample_md(market_data: pd.DataFrame, window_length: int, sample_interval: int, universe: t.List[int]):
    assert sample_interval >= 1 * 60 * NANOS_IN_SECOND

    sampler = WindowSampler(window_length, universe)
    start_time = market_data.index[0][0].value
    end_time = market_data.index[-1][0].value

    cur_data_idx = 0
    sample_time = start_time + 4 * sample_interval  # warmup time
    for cur_time in range(start_time, end_time, 1 * 60 * NANOS_IN_SECOND):
        while market_data.index[cur_data_idx][0].value < cur_time:
            row = market_data.iloc[cur_data_idx]
            sampler.process(row.name[0].value, row.name[1], row['mid_price'], True)
            cur_data_idx += 1
        sampler.ema_process(cur_time)

        if cur_time > sample_time:
            sampler.sample(sample_time)
            sample_time += sample_interval
    return sampler.output()


if __name__ == "__main__":
    # For unit testing
    import pi_trading_lib.data.market_data as market_data

    data = market_data.get_df(datetime.datetime(2021, 1, 20).date(), datetime.datetime(2021, 1, 20).date())
    corrs = sample_md(data, 60 * 60 * NANOS_IN_SECOND, 10 * 60 * NANOS_IN_SECOND, [24804])

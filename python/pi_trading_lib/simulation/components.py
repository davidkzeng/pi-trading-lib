import typing as t

from pi_trading_lib.simulation.md_sim import MarketDataSim

EMA_ALPHA = 0.75  # Minimal ema


class EMA:
    def __init__(self, md_sim: MarketDataSim, alpha: float, sample_interval: int = 1) -> None:
        assert alpha >= 0 and alpha < 1
        assert sample_interval >= 1

        self.universe = md_sim.universe
        self.size = len(self.universe)
        self.cid_idx = md_sim.cid_idx.copy()

        self.ema_val: t.List[t.Optional[float]] = [None for _ in range(self.size)]
        self.sample_interval = sample_interval
        self.alpha = alpha

        self.cur_time = 0
        self.counter = 0

        self.md_sim = md_sim

    def poll(self, timestamp: int):
        assert timestamp >= self.cur_time
        if timestamp == self.cur_time:
            return
        self.md_sim.poll(timestamp)

        if self.counter % self.sample_interval == 0:
            md_sample = self.md_sim.sample()
            for idx, price in enumerate(md_sample):
                if price is None:
                    self.ema_val[idx] = None
                    continue

                cur_ema_val = self.ema_val[idx]
                if cur_ema_val is None:
                    self.ema_val[idx] = price
                else:
                    self.ema_val[idx] = self.alpha * cur_ema_val + (1 - self.alpha) * price

        self.cur_time = timestamp
        self.counter += 1

    def sample(self, universe: t.Optional[t.List[int]] = None) -> t.List[t.Optional[float]]:
        if universe is None:
            universe = self.universe

        return [self.ema_val[self.cid_idx[cid]] for cid in universe]

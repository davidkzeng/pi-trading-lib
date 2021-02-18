import typing as t
from abc import abstractmethod

EMA_ALPHA = 0.75  # Minimal ema


T = t.TypeVar('T')


class SimNode(t.Generic[T]):
    universe: t.List[int]
    size: int
    cid_idx: t.Dict[int, int]

    cur_time: int
    inputs: t.List['SimNode']

    def __init__(self, universe: t.List[int], inputs=[]):
        self.universe = universe
        self.size = len(self.universe)
        self.cid_idx = {}
        for idx, cid in enumerate(self.universe):
            self.cid_idx[cid] = idx

        self.cur_time = 0
        self.inputs = inputs

    def poll(self, timestamp: int):
        assert timestamp >= self.cur_time
        if timestamp == self.cur_time:
            return

        for inp in self.inputs:
            inp.poll(timestamp)

    @abstractmethod
    def sample(self, universe: t.Optional[t.List[int]] = None) -> t.List[T]:
        pass


class EMA(SimNode[t.Optional[float]]):
    def __init__(self, inp: SimNode[t.Optional[float]], alpha: float, sample_interval: int = 1) -> None:
        assert alpha >= 0 and alpha < 1
        assert sample_interval >= 1

        SimNode.__init__(self, inp.universe.copy(), inputs=[inp])

        self.ema_val: t.List[t.Optional[float]] = [None for _ in range(self.size)]
        self.sample_interval = sample_interval
        self.alpha = alpha

        self.cur_time = 0
        self.counter = 0

        self.inp = inp

    def poll(self, timestamp: int):
        SimNode.poll(self, timestamp)

        if self.counter % self.sample_interval == 0:
            md_sample = self.inp.sample()
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


# TODO: Figure out how to reuse functionality better with generics
class Return(SimNode[t.Optional[float]]):
    def __init__(self, inp: SimNode[t.Optional[t.Tuple[float, float]]], universe: t.List[int]) -> None:
        SimNode.__init__(self, universe, inputs=[inp])
        self.inp = inp

    def sample(self, universe: t.Optional[t.List[int]] = None) -> t.List[t.Optional[float]]:
        if universe is None:
            universe = self.universe

        inp_values = self.inp.sample(universe=universe)

        def compute_return(cid):
            idx = self.cid_idx[cid]
            if inp_values[idx] is None:
                return None
            else:
                a, b = inp_values[idx]
                return b - a
        return [compute_return(cid) for cid in universe]

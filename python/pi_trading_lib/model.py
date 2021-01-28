import typing as t
import datetime
from abc import abstractmethod

import pandas as pd

# Can we type alias pd.DataFrame?
Capital = float
Return = t.Tuple[float, float]
OptimizeResult = t.Tuple[pd.DataFrame, Capital, Return]

POSITION_LIMIT_VALUE = 800


class BaseModel:
    @abstractmethod
    def optimize(self, date: datetime.date, capital: float, cur_position: pd.DataFrame,
                 params: t.Dict[str, t.Any] = {}) -> OptimizeResult:
        pass

    @staticmethod
    def get_base_contraints(x_b, x_s, price_b, price_s, capital, current_position) -> t.List:
        pass

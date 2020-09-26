import typing as t
import datetime
from abc import abstractmethod

import pandas as pd

from pi_trading_lib.data.data_archive import DataArchive
from pi_trading_lib.data.market_data import MarketData

OptimizeResult = t.Tuple[pd.DataFrame, t.Tuple[float, float]]

POSITION_LIMIT_VALUE = 800


class BaseModel:
    def __init__(self, archive_location):
        self.data_archive = DataArchive(archive_location)
        self.market_data = MarketData(self.data_archive)

    @abstractmethod
    def optimize(self, date: datetime.date, capital: float, params: t.Dict[str, t.Any] = {}) -> OptimizeResult:
        pass

    @staticmethod
    def get_base_contraints(x_b, x_s, price_b, price_s, capital, current_position) -> t.List:
        pass

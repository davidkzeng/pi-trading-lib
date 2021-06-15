import typing as t
import datetime
from abc import abstractmethod, ABC

import numpy as np


PIPOSITION_LIMIT_VALUE = 800 # PI position limit of 850 - some buffer room


class PositionModel(ABC):
    @abstractmethod
    def optimize(self, date: datetime.date, capital: float, cur_position: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def get_universe(self, date: datetime.date) -> np.ndarray:
        pass


class ReturnModel:
    @abstractmethod
    def get_return(self, contracts: t.List[int]) -> t.List[float]:
        pass

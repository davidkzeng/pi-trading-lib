import typing as t
import datetime
from abc import abstractmethod, ABC

import numpy as np

import pi_trading_lib.model_config as model_config


PIPOSITION_LIMIT_VALUE = 825 # PI position limit of 850 - some buffer room


class PositionModel(ABC):
    @abstractmethod
    def optimize(self, config: model_config.Config, date: datetime.date, capital: float, cur_position: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def get_universe(self, date: datetime.date) -> np.ndarray:
        pass


class StandardModel:
    @abstractmethod
    def optimize(self, config: model_config.Config, date: datetime.date) -> np.ndarray:
        pass

    @abstractmethod
    def get_universe(self, date: datetime.date) -> np.ndarray:
        pass


class ReturnModel:
    @abstractmethod
    def get_return(self, contracts: t.List[int]) -> t.List[float]:
        pass

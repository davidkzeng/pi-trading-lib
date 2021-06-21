import typing as t
import datetime
from abc import abstractmethod, ABC

import numpy as np
import pandas as pd

import pi_trading_lib.model_config as model_config


PIPOSITION_LIMIT_VALUE = 825 # PI position limit of 850 - some buffer room


class Model(ABC):
    def get_price(self, config: model_config.Config, date: datetime.date) -> t.Optional[pd.Series]:
        return None

    def get_return(self, config: model_config.Config, date: datetime.date) -> t.Optional[pd.Series]:
        return None

    def get_factor(self, config: model_config.Config, date: datetime.date) -> t.Optional[pd.Series]:
        return None

    @abstractmethod
    def get_universe(self, config: model_config.Config, date: datetime.date) -> np.ndarray:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class ReturnModel:
    @abstractmethod
    def get_return(self, contracts: t.List[int]) -> t.List[float]:
        pass

import datetime
import typing as t

import pandas as pd

import pi_trading_lib.data.resolution as resolution


def add_name(df: pd.DataFrame) -> pd.DataFrame:
    pass


def add_resolution(df: pd.DataFrame, date: t.Optional[datetime.date] = None, cid_col: str = 'cid') -> pd.DataFrame:
    contracts = df[cid_col].unique().tolist()
    resolutions = resolution.get_contract_resolution(contracts, date)
    df['resolution'] = df[cid_col].map(resolutions)
    return df

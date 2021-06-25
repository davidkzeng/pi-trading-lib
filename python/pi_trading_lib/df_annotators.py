import datetime
import typing as t

import pandas as pd

import pi_trading_lib.data.resolution as resolution
import pi_trading_lib.data.contracts


def add_name(df: pd.DataFrame) -> pd.DataFrame:
    pass


def add_resolution(df: pd.DataFrame, date: t.Optional[datetime.date] = None, cid_col: str = 'cid') -> pd.DataFrame:
    contracts = df[cid_col].unique().tolist()
    resolutions = resolution.get_contract_resolution(contracts, date)
    df['resolution'] = df[cid_col].map(resolutions)
    return df


def add_begin_date(df: pd.DataFrame, cid_col: str = 'cid') -> pd.DataFrame:
    cids = df[cid_col].unique().tolist()
    contract_info_map = pi_trading_lib.data.contracts.get_contracts(cids)
    contract_begin_dates = {cid: info['begin_date'] for cid, info in contract_info_map.items()}
    df['begin_date'] = df[cid_col].map(contract_begin_dates)
    return df

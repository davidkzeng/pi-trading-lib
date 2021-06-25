import datetime
import typing as t

import pandas as pd

import pi_trading_lib.data.resolution as resolution
import pi_trading_lib.data.contracts


def add_name(df: pd.DataFrame, cid_col: str = 'cid') -> pd.DataFrame:
    full_names = pi_trading_lib.data.contracts.get_contract_names(df[cid_col].unique().tolist())
    df['full_name'] = df[cid_col].map(full_names)
    return df


def add_resolution(df: pd.DataFrame, date: t.Optional[datetime.date] = None, cid_col: str = 'cid') -> pd.DataFrame:
    contracts = df[cid_col].unique().tolist()
    resolutions = resolution.get_contract_resolution(contracts, date)
    df['resolution'] = df[cid_col].map(resolutions)
    return df


def add_contract_dates(df: pd.DataFrame, cid_col: str = 'cid') -> pd.DataFrame:
    cids = df[cid_col].unique().tolist()
    contract_info_map = pi_trading_lib.data.contracts.get_contracts(cids)
    contract_begin_dates = {cid: info['begin_date'] for cid, info in contract_info_map.items()}
    contract_end_dates = {cid: info['end_date'] for cid, info in contract_info_map.items()}
    df['begin_date'] = df[cid_col].map(contract_begin_dates)
    df['end_date'] = df[cid_col].map(contract_end_dates)
    return df


def add_is_binary(df: pd.DataFrame, cid_col: str = 'cid') -> pd.DataFrame:
    return add_from_cid_mapping(pi_trading_lib.data.contracts.is_binary_contract, 'binary', df, cid_col=cid_col)


def add_from_cid_mapping(cid_mapping: t.Callable[[t.List[int]], t.Dict[int, t.Any]], mapped_col: str, df: pd.DataFrame, cid_col: str = 'cid') -> pd.DataFrame:
    assert mapped_col not in df.columns
    assert cid_col in df.columns

    cids = df[cid_col].unique().tolist()
    map_result = cid_mapping(cids)
    df[mapped_col] = df[cid_col].map(map_result)
    return df

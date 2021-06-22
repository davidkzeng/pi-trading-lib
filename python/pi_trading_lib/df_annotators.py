import pandas as pd

import pi_trading_lib.data.resolution as resolution


def add_name(df: pd.DataFrame) -> pd.DataFrame:
    pass


def add_resolution(df: pd.DataFrame) -> pd.DataFrame:
    contracts = df['cid'].unique().tolist()
    resolutions = resolution.get_contract_resolution(contracts)
    df['resolution'] = df['cid'].map(resolutions)
    return df

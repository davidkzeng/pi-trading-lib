import typing as t
import os.path
import logging
import datetime
import functools

import pandas as pd
import numpy as np

import pi_trading_lib.data.data_archive as data_archive
import pi_trading_lib.date_util as date_util
import pi_trading_lib.decorators
import pi_trading_lib.data.contracts
import pi_trading_lib.timers

# TODO: Store market data in contract based format to optimize for common use cases

COLUMNS = ['timestamp', 'market_id', 'contract_id', 'bid_price', 'ask_price', 'trade_price', 'name']


@functools.lru_cache()
def missing_market_data_days() -> t.List[datetime.date]:
    with open(data_archive.get_data_file('bad_md_days')) as f:
        bad_days = [date_util.from_str(line.rstrip()) for line in f]
    return bad_days


def bad_market_data(date: datetime.date) -> bool:
    return date in missing_market_data_days()


@functools.lru_cache()
def get_market_data_start() -> datetime.date:
    begin_date = data_archive.get_begin_date('market_data_csv')
    assert begin_date is not None
    return begin_date


@functools.lru_cache()
@pi_trading_lib.timers.timer
def get_raw_data(date: datetime.date) -> pd.DataFrame:
    """Get raw data for date as dataframe"""
    market_data_file = data_archive.get_data_file('market_data_csv', {'date': date_util.to_str(date)})
    if not os.path.exists(market_data_file):
        logging.warn('No raw market data for {date}'.format(date=str(date)))
        md_df = pd.DataFrame([], columns=COLUMNS)
    else:
        logging.debug('Loading market data file %s' % market_data_file)
        md_df = pd.read_csv(market_data_file)
        md_df['contract_id'] = md_df['id']
        md_df['timestamp'] = pd.to_datetime(md_df['timestamp'], unit='ms')
        contract_name_map = pi_trading_lib.data.contracts.get_contract_names(md_df['contract_id'].unique().tolist())
        md_df['name'] = md_df['contract_id'].map(contract_name_map)
        md_df = md_df[COLUMNS]

    md_df = md_df.set_index(['timestamp', 'contract_id'])
    md_df = md_df.sort_index(level='timestamp')  # Is this needed? maybe presorted
    return md_df


@pi_trading_lib.decorators.copy
@functools.lru_cache()
@pi_trading_lib.timers.timer
def get_filtered_data(date: datetime.date, contracts: t.Optional[t.Tuple[int, ...]] = None,
                      snapshot_interval: t.Optional[datetime.timedelta] = None) -> pd.DataFrame:
    """
    Get data for date as dataframe, applying filters

    param snapshot_interval: Transform dataframe into a market data snapshot every snapshot_interval time
    """
    df = get_raw_data(date)

    if contracts is not None:
        df = df.iloc[df.index.get_level_values('contract_id').isin(contracts)]

    if snapshot_interval is not None:
        assert snapshot_interval <= datetime.timedelta(days=1)
        assert snapshot_interval >= datetime.timedelta(minutes=1)

        df = df.groupby([
            pd.Grouper(level='contract_id'),
            pd.Grouper(level='timestamp', freq=snapshot_interval)
        ]).last()

        # Adjust timestamps so that rows respresent the last seen market data at the timestamp
        def adjust_ts(index):
            contract_id, ts = index
            return (contract_id, ts + snapshot_interval - datetime.timedelta(seconds=1))
        df.index = df.index.map(adjust_ts)

        # Forward fill values when possible possible
        timestamps = df.index.unique(level='timestamp')
        timestamp_range = pd.date_range(start=timestamps.min(), end=timestamps.max(), freq=snapshot_interval)
        snapshot_index = pd.MultiIndex.from_product(
            [df.index.unique(level='contract_id'), timestamp_range],
            names=['contract_id', 'timestamp']
        )
        df = df.reindex(snapshot_index)
        df = df.groupby(level=['contract_id']).ffill()
        df = df.dropna()
        df['market_id'] = df['market_id'].astype('int64')
        df = df.reorder_levels(['timestamp', 'contract_id']).sort_index()

    return df


def add_mid_price(df: pd.DataFrame) -> pd.DataFrame:
    df['mid_price'] = (df['bid_price'] + df['ask_price']) / 2
    return df


def _annotate(df: pd.DataFrame) -> pd.DataFrame:
    add_mid_price(df)
    return df


def get_df(begin_date: datetime.date, end_date: datetime.date, **filter_kwargs) -> pd.DataFrame:
    """Get market data between [begin_date, end_date], inclusive"""
    # TODO: Support intraday snapshots
    df = pd.concat(
        [get_filtered_data(date, **filter_kwargs) for date in date_util.date_range(begin_date, end_date)],
        axis=0
    )
    df = _annotate(df)
    return df


class MarketDataSnapshot:
    data: pd.DataFrame
    universe: np.ndarray

    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.universe = self.data.index.to_numpy()

    def __getitem__(self, key):
        return self.data[key]

    def reindex(self, target_universe: np.ndarray) -> 'MarketDataSnapshot':
        new_data = self.data.reindex(target_universe)
        return MarketDataSnapshot(new_data)


@functools.lru_cache()
@pi_trading_lib.timers.timer
def get_snapshot(timestamp: t.Union[datetime.datetime, datetime.date], contracts: t.Optional[t.Tuple[int, ...]] = None) -> MarketDataSnapshot:
    if isinstance(timestamp, datetime.datetime):
        timestamp_date = timestamp.date()
        df = get_raw_data(timestamp_date).reset_index('contract_id')
        df = df[df.index.get_level_values('timestamp') < timestamp]
        df = df.groupby('contract_id').tail(1).reset_index().set_index('contract_id')
    else:
        df = get_raw_data(timestamp).reset_index('contract_id')
        # TODO: maybe don't do this to exclude contracts added intraday
        df = df.groupby('contract_id').head(1).reset_index().set_index('contract_id')
    if contracts is not None:
        df = df.reindex(list(set(contracts)))
    df = _annotate(df)
    return MarketDataSnapshot(df)

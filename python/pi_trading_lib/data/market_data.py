import typing as t
import os.path
import logging
import datetime
import functools

import pandas as pd

import pi_trading_lib.data.data_archive as data_archive
import pi_trading_lib.date_util as date_util
import pi_trading_lib.decorators
import pi_trading_lib.data.contracts

# TODO: Store market data in contract based format to optimize for common use cases

COLUMNS = ['timestamp', 'market_id', 'contract_id', 'bid_price', 'ask_price', 'trade_price', 'name']


@functools.lru_cache()
def _get_missing_market_data_days() -> t.List[str]:
    with open(data_archive.get_data_file('bad_md_days')) as f:
        bad_days = [line.rstrip() for line in f]
    return bad_days


def bad_market_data(date: datetime.date) -> bool:
    return date_util.to_date_str(date) in _get_missing_market_data_days()


def get_raw_data(date: datetime.date) -> pd.DataFrame:
    """Get raw data for date as dataframe"""
    market_data_file = data_archive.get_data_file('market_data_csv', {'date': date_util.to_date_str(date)})
    if not os.path.exists(market_data_file):
        logging.warn('No raw market data for {date}'.format(date=str(date)))
        md_df = pd.DataFrame([], columns=COLUMNS)
    else:
        logging.info('Loading market data file %s' % market_data_file)
        md_df = pd.read_csv(market_data_file)
        md_df['contract_id'] = md_df['id']
        md_df['timestamp'] = pd.to_datetime(md_df['timestamp'], unit='ms')
        contract_name_map = pi_trading_lib.data.contracts.get_contract_names(md_df['contract_id'].unique().tolist())
        md_df['name'] = md_df['contract_id'].map(contract_name_map)
        md_df = md_df[COLUMNS]

    md_df = md_df.set_index(['timestamp', 'contract_id'])
    md_df = md_df.sort_index(level='timestamp')
    return md_df


@pi_trading_lib.decorators.copy
@functools.lru_cache()
def get_filtered_data(date: datetime.date, contracts: t.Optional[t.Tuple[int, ...]] = None,
                      markets: t.Optional[t.Tuple[int, ...]] = None,
                      snapshot_interval: t.Optional[datetime.timedelta] = None) -> pd.DataFrame:
    """
    Get data for date as dataframe, applying filters

    param snapshot_interval: Transform dataframe into a market data snapshot every snapshot_interval time
    """
    assert contracts is None or markets is None, "Cannot specify both contracts and markets"

    # Add support for both cids and mids
    df = get_raw_data(date)
    if contracts is not None:
        df = df.iloc[df.index.get_level_values('contract_id').isin(contracts)]
    if markets is not None:
        df = df[df['market_id'].isin(markets)]

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


def add_market_best_price(df: pd.DataFrame):
    if True:
        # Try to support this again, maybe prepopulate in rust?
        # The current problem is that we decoupled market and contract updates
        df['best_bid_price'] = df['bid_price']
        df['best_ask_price'] = df['ask_price']
        return df

    bid_ask_by_market = df.groupby('market_id')[['bid_price', 'ask_price']].sum()
    contracts_in_market = df.reset_index(drop=False).groupby('market_id')['contract_id'].nunique()

    def get_best_bid(row):
        """
        An order to buy contract A at bid_price is the equivalent to an order to sell
        the complementary contract B as ask_price = 1 - bid_price
        From our POV: selling contract A at bid_price (buying NO's) is the same as
        buying contract B at ask_price (buying YES's)

        Currently only supporting binary contracts

        """
        if contracts_in_market[row['market_id']] == 2:
            opp_side_bid = 1 - (bid_ask_by_market.at[row['market_id'], 'ask_price'] - row['ask_price'])
            return max(row['bid_price'], opp_side_bid)
        else:
            return row['bid_price']

    def get_best_ask(row):
        if contracts_in_market[row['market_id']] == 2:
            opp_side_ask = 1 - (bid_ask_by_market.at[row['market_id'], 'bid_price'] - row['bid_price'])
            return min(row['ask_price'], opp_side_ask)
        else:
            return row['ask_price']

    df['best_bid_price'] = df.apply(lambda row: get_best_bid(row), axis=1, result_type='reduce')
    df['best_ask_price'] = df.apply(lambda row: get_best_ask(row), axis=1, result_type='reduce')
    return df


def add_mid_price(df: pd.DataFrame):
    df['mid_price'] = (df['best_bid_price'] + df['best_ask_price']) / 2
    df['mid_price_strict'] = (df['bid_price'] + df['ask_price']) / 2

    return df


def get_df(start_date: datetime.date, end_date: datetime.date, **filter_kwargs) -> pd.DataFrame:
    """Get market data between [start_date, end_date], inclusive"""
    # TODO: Support intraday snapshots
    df = pd.concat(
        [get_filtered_data(date, **filter_kwargs) for date in date_util.date_range(start_date, end_date)],
        axis=0
    )
    df = add_market_best_price(df)
    df = add_mid_price(df)
    return df

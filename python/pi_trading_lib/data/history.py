"""Module for writing and querying generic history items"""
import typing as t
import datetime

import pi_trading_lib.data.market_data
import pi_trading_lib.data.contract_db as contract_db
import pi_trading_lib.timers

BBO_CHANGE_COUNT = 1  # Number of BBO updates per day
PI_DATA_CHANGE_COUNT = 2  # Number of BBO or last trade price updates per day


def get_bbo_change_count(contract_ids: t.List[int], date: datetime.date) -> t.Dict[int, int]:
    pass


@pi_trading_lib.timers.timer
def update_history(date_values: t.List[t.Tuple[int, int]], date: datetime.date, value_type: int, replace=False):
    query_args = [(contract_id, date, value, value_type) for contract_id, value in date_values]
    conflict_res = 'REPLACE' if replace else 'IGNORE'
    query = f'''INSERT OR {conflict_res} INTO daily_history (contract_id, date, value, value_type)
                VALUES (?, ?, ?, ?)
                '''
    with contract_db.get_contract_db() as db:
        db.executemany(query, query_args)


@pi_trading_lib.timers.timer
def update_bbo_change_count_history(date: datetime.date, replace=False):
    df = pi_trading_lib.data.market_data.get_raw_data(date)
    if len(df) == 0:
        return
    else:
        df['previous_bid'] = df.groupby(level=1)['bid_price'].shift(periods=1)
        df['previous_ask'] = df.groupby(level=1)['ask_price'].shift(periods=1)
        df['bbo_updated'] = ((~df['previous_bid'].isnull() & (df['previous_bid'] != df['bid_price'])) |
                             (~df['previous_ask'].isnull() & (df['previous_ask'] != df['ask_price'])))
        bbo_change_counts = df.groupby(level=1)['bbo_updated'].sum()
        bbo_change_counts = list(zip(bbo_change_counts.index.tolist(), bbo_change_counts.tolist()))
        update_history(bbo_change_counts, date, BBO_CHANGE_COUNT, replace=replace)

        # subtract one to ignore initial data refresh
        data_change_counts = df.index.get_level_values('contract_id').value_counts() - 1
        data_change_counts = list(zip(data_change_counts.index.tolist(), data_change_counts.tolist()))
        update_history(data_change_counts, date, PI_DATA_CHANGE_COUNT, replace=replace)

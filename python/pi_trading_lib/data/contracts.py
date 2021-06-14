"""Refactor this"""
import typing as t
import functools
import json
import os
import logging
import datetime

import pi_trading_lib
import pi_trading_lib.fs as fs
import pi_trading_lib.data.contract_db as contract_db
import pi_trading_lib.timers
import pi_trading_lib.decorators

# ========================= Legacy =========================


def save_contract_data(name: str, data: t.Dict[int, t.Dict[int, t.List]]):
    contract_file = os.path.join(pi_trading_lib.get_package_dir(), 'config/contracts', name)
    if os.path.exists(contract_file):
        logging.warn('Overriding existing contract file: %s' % contract_file)

    with fs.safe_open(contract_file, 'w+') as contract_file_f:
        json.dump(data, contract_file_f, indent=2, sort_keys=True)


@functools.lru_cache()
def get_contract_data(name: str) -> t.Dict[int, t.Dict[int, t.List]]:
    contract_file = os.path.join(pi_trading_lib.get_package_dir(), 'config/contracts', name)
    assert os.path.exists(contract_file)

    with open(contract_file, 'r') as contract_f:
        contract_json = json.load(contract_f)
        contract_info = {int(mid): {int(cid): info for cid, info in mid_info.items()}
                         for mid, mid_info in contract_json.items()}
    return contract_info


def get_contract_data_by_cid(name: str) -> t.Dict[int, t.List]:
    """
    returns: contract id -> [contract info]
    """
    contract_data = get_contract_data(name)
    flattened_data = [(cid, contract_data[mid][cid]) for mid in contract_data for cid in contract_data[mid]]
    contract_data_by_cid = {cid: info for cid, info in flattened_data}

    assert len(flattened_data) == len(contract_data_by_cid)
    return contract_data_by_cid


def get_contract_ids(name: str) -> t.List[int]:
    return list(get_contract_data_by_cid(name).keys())

# ========================= Current =========================


@pi_trading_lib.timers.timer
def get_contracts(ids: t.Optional[t.List[int]] = None) -> t.Dict[int, t.Dict]:
    # TODO: Make this return dict
    if ids is not None and len(ids) == 0:
        return {}

    columns = ['id', 'name', 'market_id', 'begin_date', 'end_date', 'last_update_date']
    column_str = ', '.join(columns)
    if ids is None:
        query = f'SELECT {column_str} FROM contract'
    else:
        query = f'SELECT {column_str} FROM contract WHERE id IN {contract_db.to_sql_list(ids)}'

    res = contract_db.get_contract_db().cursor().execute(query).fetchall()

    return {
        row[0]: {
            'id': row[0],
            'name': row[1],
            'market_id': row[2],
            'begin_date': datetime.date.fromisoformat(row[3]),
            'end_date': datetime.date.fromisoformat(row[4]) if row[4] is not None else None,
            'last_update_date': datetime.date.fromisoformat(row[5]),
        }
        for row in res
    }


@pi_trading_lib.timers.timer
def get_markets(ids: t.List[int] = []) -> t.Dict[int, t.Dict]:
    columns = ['id', 'name']
    column_str = ', '.join(columns)

    if len(ids) == 0:
        query = f'SELECT {column_str} FROM market'
    else:
        query = f'SELECT {column_str} FROM market WHERE id IN {contract_db.to_sql_list(ids)}'

    markets = contract_db.get_contract_db().cursor().execute(query).fetchall()
    return {
        row[0]: {
            'id': row[0],
            'name': row[1],
        }
        for row in markets
    }


def get_contract_names(ids: t.List[int]) -> t.Dict[int, str]:
    """Returns {contract id: full contract name}"""

    contracts = get_contracts(ids)
    contract_market_ids = list(set(contract['market_id'] for contract in contracts.values()))
    markets = get_markets(contract_market_ids)
    market_names = {market_id: market['name'] for market_id, market in markets.items()}
    contract_name_map = {}
    for contract_id, contract in contracts.items():
        if markets[contract['market_id']] != contract['name']:
            contract_name_map[contract_id] = market_names[contract['market_id']] + ' ' + contract['name']
        else:
            contract_name_map[contract_id] = contract['name']
    return contract_name_map


def get_market_contracts(market_ids: t.List[int]) -> t.Dict[int, t.List[int]]:
    query = f"""
        SELECT id, market_id FROM contract
        WHERE market_id IN {contract_db.to_sql_list(market_ids)}
    """
    contracts = contract_db.get_contract_db().cursor().execute(query).fetchall()
    res: t.Dict[int, t.List[int]] = {}
    for contract in contracts:
        res.setdefault(contract[1], []).append(contract[0])
    return res


@pi_trading_lib.decorators.memoize_mapping()
def is_binary_contract(ids: t.List[int]) -> t.Dict[int, bool]:
    contracts = get_contracts(ids)
    unique_market_ids = list(set(contract['market_id'] for contract in contracts.values()))
    market_contracts = get_market_contracts(unique_market_ids)
    market_size = {market_id: len(cons) for market_id, cons in market_contracts.items()}
    # heuristic
    return {contract_id: market_size[contract['market_id']] <= 2 for contract_id, contract in contracts.items()}


# ========================= Updates =========================

@pi_trading_lib.timers.timer
def add_contracts(contracts):
    contract_rows = [
        (contract['id'], contract['name'], contract['market_id'],
         contract['begin_date'].isoformat(), contract['begin_date'].isoformat(), None)
        for contract in contracts
    ]
    db = contract_db.get_contract_db()
    with db:
        db.executemany('INSERT INTO contract VALUES (?, ?, ?, ?, ?, ?)', contract_rows)


@pi_trading_lib.timers.timer
def update_contract_dates(contract_ids: t.List[int], alive_date: datetime.date):
    """Update contract begin, last_update, end dates.

    TODO: Define the invariant here
    TODO: Redo this to be cleaner, set end date based on whether there is data on the last
          data date in the overall DB
    f(contracts + their alive date ranges) = contract_state
    """

    alive_date_str = alive_date.isoformat()

    # Step 1: Extend begin date
    query = f"""
        SELECT id FROM contract
        WHERE id IN {contract_db.to_sql_list(contract_ids)}
        AND begin_date > '{alive_date_str}'
    """
    results = contract_db.get_contract_db().cursor().execute(query).fetchall()
    begin_date_update_ids = [result[0] for result in results]
    print(f'Setting or extending begin date for {len(results)} contracts')
    with contract_db.get_contract_db() as db:
        db.execute(
            f"""UPDATE contract SET begin_date = '{alive_date_str}'
                WHERE id IN {contract_db.to_sql_list(begin_date_update_ids)}
            """)

    # Step 2: Extend last_update_date
    query = f"""
        SELECT id FROM contract
        WHERE id IN {contract_db.to_sql_list(contract_ids)}
        AND last_update_date < '{alive_date_str}'
    """
    results = contract_db.get_contract_db().cursor().execute(query).fetchall()
    last_update_date_update_ids = [result[0] for result in results]
    print(f'Extending last update date for {len(results)} contracts')
    with contract_db.get_contract_db() as db:
        db.execute(
            f"""UPDATE contract SET last_update_date = '{alive_date_str}'
                WHERE id IN {contract_db.to_sql_list(last_update_date_update_ids)}
            """)

    # Step 3: Reset end date if actually alive
    query = """
        SELECT id FROM contract
        WHERE end_date IS NOT NULL AND end_date < last_update_date
    """
    results = contract_db.get_contract_db().cursor().execute(query).fetchall()
    end_date_update_ids = [result[0] for result in results]
    print(f'Resetting end date for {len(results)} contracts')
    with contract_db.get_contract_db() as db:
        db.execute(
            f"""UPDATE contract SET end_date = NULL
                WHERE id IN {contract_db.to_sql_list(end_date_update_ids)}
            """)

    # Step 4: Set end date for contracts missing data.
    query = f"""
        SELECT id FROM contract
        WHERE id NOT IN {contract_db.to_sql_list(contract_ids)}
        AND (end_date IS NULL OR end_date != last_update_date)
        AND (last_update_date < '{alive_date_str}')
    """
    results = contract_db.get_contract_db().cursor().execute(query).fetchall()
    end_date_update_ids = [result[0] for result in results]
    print(f'Setting end date for {len(results)} contracts')
    with contract_db.get_contract_db() as db:
        db.execute(
            f"""UPDATE contract SET end_date = last_update_date
                WHERE id IN {contract_db.to_sql_list(end_date_update_ids)}
            """)


@pi_trading_lib.timers.timer
def add_markets(markets):
    market_rows = [(market['id'], market['name']) for market in markets]
    db = contract_db.get_contract_db()
    with db:
        db.executemany('INSERT INTO market VALUES (?, ?)', (market_rows))


@pi_trading_lib.timers.timer
def update_contract_info(date):
    daily_contracts: t.Dict[int, t.Dict] = {}
    daily_markets: t.Dict[int, t.Dict] = {}
    market_data_file = pi_trading_lib.data.data_archive.get_data_file(
        'market_data_raw', {'date': date})
    with open(market_data_file, 'r') as f:
        for update in f:
            update = update.rstrip()
            market_updates = json.loads(update)['market_updates']
            for market_id, market in market_updates.items():
                market_id = int(market_id)
                for contract in market['contracts']:
                    contract_id = int(contract['id'])
                    if contract_id not in daily_contracts:
                        daily_contracts[contract_id] = {
                            'id': contract_id,
                            'name': contract['name'],
                            'market_id': int(market['id']),
                            'begin_date': date,
                        }
                if market_id not in daily_markets:
                    daily_markets[market_id] = {
                        'id': market_id,
                        'name': market['name']
                    }

    db_contracts = get_contracts(list(daily_contracts.keys()))
    db_markets = get_markets(list(daily_markets.keys()))
    missing_markets = set(daily_markets.keys()) - set(db_markets.keys())
    missing_contracts = set(daily_contracts.keys()) - set(db_contracts.keys())

    if len(missing_markets) > 0:
        print(f'Adding {len(missing_markets)} new markets')
        add_markets([daily_markets[market_id] for market_id in sorted(list(missing_markets))])
    if len(missing_contracts) > 0:
        print(f'Adding {len(missing_contracts)} new contracts')
        add_contracts([daily_contracts[contract_id] for contract_id in sorted(list(missing_contracts))])

    print('Updating alive date range for contracts')
    update_contract_dates(list(daily_contracts.keys()), date)

"""Refactor this"""
import typing as t
import functools
import json
import os
import logging
import datetime

import pi_trading_lib
import pi_trading_lib.fs as fs
import pi_trading_lib.date_util as date_util
import pi_trading_lib.data.contract_db as contract_db
import pi_trading_lib.timers


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
        contract_info = json.load(contract_f)
        contract_info = {int(mid): {int(cid): info for cid, info in mid_info.items()}
                         for mid, mid_info in contract_info.items()}
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


@pi_trading_lib.timers.timer
def get_contracts(ids: t.List[int] = []):
    # TODO: Make this return dict
    if len(ids) == 0:
        query = 'SELECT * FROM contract'
    else:
        query = f'SELECT * FROM contract WHERE id IN {contract_db.to_sql_list(ids)}'

    contracts = contract_db.get_contract_db().cursor().execute(query).fetchall()
    return [{'id': contract[0], 'name': contract[1], 'market_id': contract[2]} for contract in contracts]


@pi_trading_lib.timers.timer
def get_markets(ids: t.List[int] = []):
    if len(ids) == 0:
        query = 'SELECT * FROM market'
    else:
        query = f'SELECT * FROM market WHERE id IN {contract_db.to_sql_list(ids)}'

    markets = contract_db.get_contract_db().cursor().execute(query).fetchall()
    return [{'id': market[0], 'name': market[1]} for market in markets]


def get_contract_names(ids: t.List[int]):
    contracts = get_contracts(ids)
    contract_market_ids = list(set(contract['market_id'] for contract in contracts))
    markets = get_markets(contract_market_ids)
    markets = {market['id']: market['name'] for market in markets}
    contract_name_map = {}
    for contract in contracts:
        contract_name_map[contract['id']] = markets[contract['market_id']] + ' ' + contract['name']
    return contract_name_map


# ========================= Updates =========================

@pi_trading_lib.timers.timer
def add_contracts(contracts):
    contract_rows = [
        (contract['id'], contract['name'], contract['market_id'], contract['begin_date'].isoformat(), None)
        for contract in contracts
    ]
    db = contract_db.get_contract_db()
    with db:
        db.executemany('INSERT INTO contract VALUES (?, ?, ?, ?, ?)', contract_rows)


@pi_trading_lib.timers.timer
def update_contract_dates(contract_ids: t.List[int], alive_date: datetime.date):
    alive_date_str = alive_date.isoformat()
    query = f"""
        SELECT id FROM contract
        WHERE id IN {contract_db.to_sql_list(contract_ids)}
        AND (begin_date IS NULL OR begin_date > '{alive_date_str}')
    """
    results = contract_db.get_contract_db().cursor().execute(query).fetchall()
    begin_date_update_ids = [result[0] for result in results]
    print(f'Setting or extending begin date for {len(results)} contracts')
    with contract_db.get_contract_db() as db:
        db.execute(
            f"""UPDATE contract SET begin_date = '{alive_date_str}'
                WHERE id IN {contract_db.to_sql_list(begin_date_update_ids)}
            """)

    query = f"""
        SELECT id FROM contract
        WHERE id IN {contract_db.to_sql_list(contract_ids)} AND end_date < '{alive_date_str}'
    """
    results = contract_db.get_contract_db().cursor().execute(query).fetchall()
    end_date_update_ids = [result[0] for result in results]
    print(f'Extending end date for {len(results)} contracts')
    with contract_db.get_contract_db() as db:
        db.execute(
            f"""UPDATE contract SET end_date = '{alive_date_str}'
                WHERE id IN {contract_db.to_sql_list(end_date_update_ids)}
            """)

    query = f"""
        SELECT id FROM contract
        WHERE id NOT IN {contract_db.to_sql_list(contract_ids)}
        AND end_date IS NULL AND begin_date < '{alive_date_str}'
    """
    results = contract_db.get_contract_db().cursor().execute(query).fetchall()
    end_date_update_ids = [result[0] for result in results]
    print(f'Setting end date for {len(results)} contracts')
    with contract_db.get_contract_db() as db:
        db.execute(
            f"""UPDATE contract SET end_date = '{alive_date_str}'
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
        'market_data_raw', {'date': date_util.to_date_str(date)})
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
    missing_markets = set(daily_markets.keys()) - set(market['id'] for market in db_markets)
    missing_contracts = set(daily_contracts.keys()) - set(contract['id'] for contract in db_contracts)

    if len(missing_markets) > 0:
        print(f'Adding {len(missing_markets)} new markets')
        add_markets([daily_markets[market_id] for market_id in sorted(list(missing_markets))])
    if len(missing_contracts) > 0:
        print(f'Adding {len(missing_contracts)} new contracts')
        add_contracts([daily_contracts[contract_id] for contract_id in sorted(list(missing_contracts))])

    print('Updating alive date range for contracts')
    update_contract_dates(list(daily_contracts.keys()), date)

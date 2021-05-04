"""Refactor this"""
import typing as t
import functools
import json
import os
import logging

import pi_trading_lib
import pi_trading_lib.fs as fs
import pi_trading_lib.date_util as date_util
import pi_trading_lib.data.contract_db as contract_db


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


def get_contracts(ids: t.List[int] = []):
    if len(ids) == 0:
        query = 'SELECT * FROM contract'
    else:
        query = f'SELECT * FROM contract WHERE id IN {contract_db.to_sql_list(ids)}'

    contracts = contract_db.get_contract_db().cursor().execute(query).fetchall()
    return [{'id': contract[0], 'name': contract[1], 'market_id': contract[2]} for contract in contracts]


def get_markets(ids: t.List[int] = []):
    if len(ids) == 0:
        query = 'SELECT * FROM market'
    else:
        query = f'SELECT * FROM market WHERE id IN {contract_db.to_sql_list(ids)}'

    markets = contract_db.get_contract_db().cursor().execute(query).fetchall()
    return [{'id': market[0], 'name': market[1]} for market in markets]


def add_contract(contract):
    db = contract_db.get_contract_db()
    with db:
        db.execute('INSERT INTO contract VALUES (?, ?, ?, ?, ?)',
                   (contract['id'], contract['name'], contract['market_id'], None, None))


def add_market(market):
    db = contract_db.get_contract_db()
    with db:
        db.execute('INSERT INTO market VALUES (?, ?)', (market['id'], market['name']))


def create_contracts_from_market_data(date):
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
                            'market_id': int(market['id'])
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

    print(f'Adding {len(missing_markets)} new markets')
    print(f'Adding {len(missing_contracts)} new contracts')

    for market_id in sorted(list(missing_markets)):
        market = daily_markets[market_id]
        print('Adding market', market['id'], market['name'])
        add_market(market)
    for contract_id in sorted(list(missing_contracts)):
        contract = daily_contracts[contract_id]
        print('Adding contract', contract['id'], contract['name'], contract['market_id'])
        add_contract(contract)

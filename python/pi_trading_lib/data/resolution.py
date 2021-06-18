import argparse
import typing as t
import datetime

import pi_trading_lib.decorators
import pi_trading_lib.data.contracts
import pi_trading_lib.data.contract_db as contract_db
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.date_util as date_util
from pi_trading_lib.data.resolution_data import CONTRACT_RESOLUTIONS, UNRESOLVED_CONTRACTS, NO_CORRECT_CONTRACT_MARKETS


@pi_trading_lib.timers.timer
def get_contract_resolution(ids: t.List[int], date: t.Optional[datetime.date] = None) -> t.Dict[int, t.Optional[float]]:
    resolution = _get_contract_resolution_db(ids, date)
    return resolution


def _get_contract_resolution_db(ids: t.List[int], date: t.Optional[datetime.date]) -> t.Dict[int, t.Optional[float]]:
    columns = ['contract_id', 'value', 'end_date']
    column_str = ', '.join(columns)
    query = f'''
    SELECT {column_str} FROM resolution
    INNER JOIN contract ON resolution.contract_id = contract.id
    WHERE contract_id IN {contract_db.to_sql_list(ids)}
    '''
    res = contract_db.get_contract_db().cursor().execute(query).fetchall()

    resolution = {row[0]: row[1] for row in res}
    resolution_dates = {row[0]: datetime.date.fromisoformat(row[2]) for row in res}
    missing_resolution = set(ids) - set(resolution.keys())
    resolution.update({cid: None for cid in missing_resolution})
    if date is not None:
        resolution.update({cid: None for cid, end_date in resolution_dates.items() if end_date > date})
    return resolution


def _get_contract_resolution_raw(ids: t.List[int]) -> t.Dict[int, t.Optional[float]]:
    resolution: t.Dict[int, t.Optional[float]] = {}

    contracts = pi_trading_lib.data.contracts.get_contracts(ids)
    for contract_id, contract in contracts.items():
        if contract['end_date'] is not None:
            date_data = market_data.get_raw_data(contract['end_date'])
            final_data = date_data.xs(contract_id, axis=0, level='contract_id').iloc[-1]
            if contract_id in CONTRACT_RESOLUTIONS:
                resolution[contract_id] = CONTRACT_RESOLUTIONS[contract_id]
                if resolution[contract_id] is not None:
                    continue

            if (final_data['trade_price'] <= 0.03 and final_data['ask_price'] <= 0.03) or final_data['ask_price'] <= 0.01:
                resolution[contract_id] = 0.0
            elif (final_data['trade_price'] >= 0.97 and final_data['bid_price'] >= 0.97) or final_data['bid_price'] >= 0.99:
                resolution[contract_id] = 1.0
            else:
                resolution[contract_id] = None
        else:
            resolution[contract_id] = None

    return resolution


def audit_resolutions():
    audit_passed = True

    contracts = pi_trading_lib.data.contracts.get_contracts()
    ended_contracts = [contract['id'] for contract in contracts.values() if contract['end_date'] is not None]
    resolutions = get_contract_resolution(ended_contracts)
    missing_resolutions = sorted(
        [cid for cid, res in resolutions.items() if res is None and cid not in UNRESOLVED_CONTRACTS],
        key=lambda cid: contracts[cid]['end_date']
    )

    if len(missing_resolutions) > 0:
        audit_passed = False
        print(f'{len(missing_resolutions)} contract missing resolutions')
        print(missing_resolutions)
        full_names = pi_trading_lib.data.contracts.get_contract_names(missing_resolutions)
        for cid in missing_resolutions:
            contract_info = contracts[cid]
            full_names[cid]
            date_data = market_data.get_raw_data(contract_info['end_date'])
            final_data = date_data.xs(cid, axis=0, level='contract_id').iloc[-1]
            if final_data['trade_price'] < 0.1:
                recommendation = 0.0
            elif final_data['trade_price'] > 0.8:
                recommendation = 1.0
            else:
                recommendation = None
            print(f"{cid}: {recommendation},  # {contract_info['market_id']} {contract_info['end_date']} {full_names[cid]} {final_data['trade_price']} {final_data['bid_price']} {final_data['ask_price']}")

    markets = pi_trading_lib.data.contracts.get_markets()
    markets_ids = list(markets.keys())
    all_market_contracts = pi_trading_lib.data.contracts.get_market_contracts(markets_ids)
    for market_id, market_contract_ids in all_market_contracts.items():
        market_contracts = pi_trading_lib.data.contracts.get_contracts(market_contract_ids)
        if any(market_contract['end_date'] is None for market_contract in market_contracts.values()):
            continue

        contract_resolutions = get_contract_resolution(market_contract_ids)
        num_correct = len([res for _cid, res in contract_resolutions.items() if res == 1.0])
        if num_correct > 1:
            audit_passed = False
            print(f'Non-unique market resolution {market_id}')
        if num_correct == 0 and len(market_contracts) >= 2:
            if market_id not in NO_CORRECT_CONTRACT_MARKETS:
                audit_passed = False
                print(f"{market_id},  # {markets[market_id]['name']}, 0 correct contracts")

    if audit_passed:
        print('Audit Passed')
    else:
        print('Audit Failed')

    pi_trading_lib.timers.report_timers()


# ========================= Updates =========================

@pi_trading_lib.timers.timer
def update_contract_resolutions():
    all_contracts = pi_trading_lib.data.contracts.get_contracts()
    db_resolutions = _get_contract_resolution_db(list(all_contracts.keys()))
    missing_resolutions = [cid for cid, res in db_resolutions.items() if res is None]
    print(f'{len(missing_resolutions)} contracts missing resolution')

    raw_data_resolution = _get_contract_resolution_raw(missing_resolutions)
    raw_data_resolution = [(cid, res) for cid, res in raw_data_resolution.items() if res is not None]
    print(f'Inserting {len(raw_data_resolution)} new entries into resolution db')
    with contract_db.get_contract_db() as db:
        db.executemany('INSERT INTO resolution VALUES (?, ?)', (raw_data_resolution))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparser', required=True)

    audit_parser = subparsers.add_parser('audit', aliases=['a'])
    update_parser = subparsers.add_parser('update', aliases=['u'])

    args = parser.parse_args()
    if args.subparser in ['audit', 'a']:
        audit_resolutions()
    if args.subparser in ['update', 'u']:
        update_contract_resolutions()

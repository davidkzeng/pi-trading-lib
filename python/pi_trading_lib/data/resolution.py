import typing as t
import argparse

import pi_trading_lib.decorators
import pi_trading_lib.data.contracts
import pi_trading_lib.data.market_data as market_data
from pi_trading_lib.data.resolution_data import CONTRACT_RESOLUTIONS, UNRESOLVED_CONTRACTS, NO_CORRECT_CONTRACT_MARKETS


@pi_trading_lib.decorators.memoize_mapping()
@pi_trading_lib.timers.timer
def get_contract_resolution(ids: t.List[int]) -> t.Dict[int, t.Optional[float]]:
    # TODO: Convert this to DB entry
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

            if final_data['trade_price'] <= 0.03 and final_data['ask_price'] <= 0.03:
                resolution[contract_id] = 0.0
            elif final_data['trade_price'] >= 0.97 and final_data['bid_price'] >= 0.97:
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
    markets_ids = [market['id'] for market in markets]
    all_market_contracts = pi_trading_lib.data.contracts.get_market_contracts(markets_ids)
    for market_id, market_contract_ids in all_market_contracts.items():
        # TODO: no need once switch to dict
        market = pi_trading_lib.data.contracts.get_markets([market_id])[0]
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
                print(f"{market_id},  # {market['name']}, 0 correct contracts")
    
    if audit_passed:
        print('Audit Passed')
    else:
        print('Audit Failed')

    pi_trading_lib.timers.report_timers()


if __name__ == "__main__":
    audit_resolutions()

import argparse
import pprint

import pi_trading_lib.data.contracts


def contract(args):
    contract = pi_trading_lib.data.contracts.get_contracts([args.cid])[args.cid]
    contract['full_name'] = pi_trading_lib.data.contracts.get_contract_names([args.cid])[args.cid]
    contract['market_link'] = 'https://www.predictit.org/markets/detail/' + str(contract['market_id'])
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(contract)


def market(args):
    pp = pprint.PrettyPrinter(indent=2)
    market = pi_trading_lib.data.contracts.get_markets([args.mid])[0]
    pp.pprint(market)

    if args.verbose:
        market_contracts = pi_trading_lib.data.contracts.get_market_contracts([args.mid])[args.mid]
        for cid in market_contracts:
            contract = pi_trading_lib.data.contracts.get_contracts([cid])[cid]
            contract['full_name'] = pi_trading_lib.data.contracts.get_contract_names([cid])[cid]
            contract['market_link'] = 'https://www.predictit.org/markets/detail/' + str(contract['market_id'])
            pp = pprint.PrettyPrinter(indent=2)
            pp.pprint(contract)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparser', required=True)

    contract_parser = subparsers.add_parser('contract', aliases=['c'])
    contract_parser.add_argument('cid', type=int)

    market_parser = subparsers.add_parser('market', aliases=['m'])
    market_parser.add_argument('mid', type=int)
    market_parser.add_argument('--verbose', '-v', action='store_true')

    args = parser.parse_args()
    if args.subparser in ['contract', 'c']:
        contract(args)
    if args.subparser in ['market', 'm']:
        market(args)


if __name__ == "__main__":
    main()

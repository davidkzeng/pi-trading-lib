import argparse
import pprint

import pi_trading_lib.data.contracts


def contract(args):
    pp = pprint.PrettyPrinter(indent=2)
    contract = pi_trading_lib.data.contracts.get_contracts([args.cid])[0]
    contract['full_name'] = pi_trading_lib.data.contracts.get_contract_names([args.cid])[args.cid]
    contract['market_link'] = 'https://www.predictit.org/markets/detail/' + str(contract['market_id'])
    pp.pprint(contract)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparser', required=True)

    contract_parser = subparsers.add_parser('contract', aliases=['c'])
    contract_parser.add_argument('cid', type=int)

    args = parser.parse_args()
    if args.subparser in ['contract', 'c']:
        contract(args)


if __name__ == "__main__":
    main()

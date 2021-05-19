import argparse

import pi_trading_lib.data.contracts


def contract(args):
    contract_name = pi_trading_lib.data.contracts.get_contract_names([args.cid])[args.cid]
    print(contract_name)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparser')

    contract_parser = subparsers.add_parser('contract')
    contract_parser.add_argument('cid', type=int)

    args = parser.parse_args()
    if args.subparser == 'contract':
        contract(args)


if __name__ == "__main__":
    main()

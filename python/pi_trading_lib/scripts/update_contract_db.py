import argparse

import pi_trading_lib.date_util as date_util
import pi_trading_lib.utils
import pi_trading_lib.data.data_archive
import pi_trading_lib.data.contracts as contracts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('start_date')
    parser.add_argument('end_date')
    parser.add_argument('data_archive')

    args = parser.parse_args()

    start_date = date_util.from_date_str(args.start_date)
    end_date = date_util.from_date_str(args.end_date)

    pi_trading_lib.data.data_archive.set_archive_dir(args.data_archive)

    for date in date_util.date_range(start_date, end_date):
        print('Running for', date)
        contracts.create_contracts_from_market_data(date)


if __name__ == "__main__":
    main()

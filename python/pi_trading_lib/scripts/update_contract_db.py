import argparse

import pi_trading_lib.date_util as date_util
import pi_trading_lib.utils
import pi_trading_lib.data.data_archive
import pi_trading_lib.data.contracts as contracts
import pi_trading_lib.data.history as history
import pi_trading_lib.timers as timers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('start_date')
    parser.add_argument('end_date')
    parser.add_argument('--data_archive')

    parser.add_argument('--force-history', action='store_true')

    args = parser.parse_args()

    start_date = date_util.from_date_str(args.start_date)
    end_date = date_util.from_date_str(args.end_date)

    if args.data_archive:
        pi_trading_lib.data.data_archive.set_archive_dir(args.data_archive)

    for date in date_util.date_range(start_date, end_date):
        print('Running for', date)
        contracts.update_contract_info(date)
        history.update_bbo_change_count_history(date, replace=args.force_history)

    timers.report_timers()


if __name__ == "__main__":
    main()

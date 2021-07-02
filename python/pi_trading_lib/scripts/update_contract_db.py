import argparse

import pi_trading_lib.datetime_ext as datetime_ext
import pi_trading_lib.utils
import pi_trading_lib.data.data_archive
import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.data.contracts as contracts
import pi_trading_lib.data.history as history
import pi_trading_lib.timers as timers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--begin-date', default=market_data.get_market_data_start())
    parser.add_argument('--end-date')
    parser.add_argument('--data-archive')

    parser.add_argument('--force-history', action='store_true')

    args = parser.parse_args()

    begin_date = datetime_ext.from_str(args.begin_date)
    end_date = datetime_ext.from_str(args.end_date)

    if args.data_archive:
        pi_trading_lib.data.data_archive.set_archive_dir(args.data_archive)

    for date in datetime_ext.date_range(begin_date, end_date):
        print('Running for', date)
        contracts.update_contract_info(date)
        history.update_bbo_change_count_history(date, replace=args.force_history)

    timers.report_timers()


if __name__ == "__main__":
    main()

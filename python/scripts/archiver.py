import argparse

import pi_trading_lib.data.data_archive as data_archive
import pi_trading_lib.data.fivethirtyeight as fte
import pi_trading_lib.dates
import pi_trading_lib.logging

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive_location')
    parser.add_argument('date')
    args = parser.parse_args()

    pi_trading_lib.logging.init_logging()
    date = pi_trading_lib.dates.from_date_str(args.date)
    data_archive.set_archive_dir(args.archive_location)

    fte.archive_data(date)

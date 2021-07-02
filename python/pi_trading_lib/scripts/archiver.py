import argparse

import pi_trading_lib.data.data_archive as data_archive
import pi_trading_lib.data.fivethirtyeight as fte
import pi_trading_lib.datetime_ext
import pi_trading_lib.logging_ext


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive_location')
    parser.add_argument('date')
    args = parser.parse_args()
    print(args)

    pi_trading_lib.logging_ext.init_logging()
    date = pi_trading_lib.datetime_ext.from_str(args.date)
    data_archive.set_archive_dir(args.archive_location)

    fte.archive_data(date)

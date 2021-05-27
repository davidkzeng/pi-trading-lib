import os
import argparse
import subprocess
import logging

import pi_trading_lib.date_util as date_util
import pi_trading_lib.utils
import pi_trading_lib.data.data_archive
import pi_trading_lib.logging


def _run_converter(date, force=False):
    date_str = date_util.to_str(date)
    input_uri = pi_trading_lib.data.data_archive.get_data_file('market_data_raw', {'date': date_str})
    output_uri = pi_trading_lib.data.data_archive.get_data_file('market_data_csv', {'date': date_str})

    if not os.path.exists(input_uri):
        logging.info(f'Could not find input for date {date} at uri {input_uri}')
        return

    if os.path.exists(output_uri) and not force:
        logging.info(f'Skipping existing output file for date {date} at uri {output_uri}')
        return

    os.makedirs(os.path.dirname(output_uri), exist_ok=True)

    logging.info(f'Running convert for date {date}')
    cmd = [
        os.path.join(pi_trading_lib.utils.get_rust_bin_dir(), 'md_csv_generator'),
        input_uri,
        output_uri,
    ]
    logging.debug(' '.join(cmd))
    subprocess.check_call(cmd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('begin_date')
    parser.add_argument('end_date')
    parser.add_argument('--data_archive')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--verbose', action='store_true')

    args = parser.parse_args()

    if args.verbose:
        pi_trading_lib.logging.init_logging(logging.DEBUG)

    begin_date = date_util.from_str(args.begin_date)
    end_date = date_util.from_str(args.end_date)

    if args.data_archive:
        pi_trading_lib.data.data_archive.set_archive_dir(args.data_archive)

    for date in date_util.date_range(begin_date, end_date):
        _run_converter(date, force=args.force)


if __name__ == "__main__":
    main()

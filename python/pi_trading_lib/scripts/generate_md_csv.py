import os
import argparse
import subprocess

import pi_trading_lib.dates as dates
import pi_trading_lib.utils
import pi_trading_lib.data.data_archive


def _run_converter(date, force=False):
    date_str = dates.to_date_str(date)
    input_uri = pi_trading_lib.data.data_archive.get_data_file('market_data_raw', {'date': date_str})
    output_uri = pi_trading_lib.data.data_archive.get_data_file('market_data_csv', {'date': date_str})

    if not os.path.exists(input_uri):
        raise Exception(f'Could not find input for date {date} at uri {input_uri}')

    if os.path.exists(output_uri) and not force:
        print(f'Skipping existing output file for date {date} at uri {output_uri}')
        return

    os.makedirs(os.path.dirname(output_uri), exist_ok=True)

    print(f'Running convert for date {date}')
    subprocess.check_call([
        os.path.join(pi_trading_lib.utils.get_rust_bin_dir(), 'md_csv_generator'),
        input_uri,
        output_uri,
    ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('start_date')
    parser.add_argument('end_date')
    parser.add_argument('data_archive')
    parser.add_argument('--force', action='store_true')

    args = parser.parse_args()

    start_date = dates.from_date_str(args.start_date)
    end_date = dates.from_date_str(args.end_date)

    pi_trading_lib.data.data_archive.set_archive_dir(args.data_archive)

    for date in dates.date_range(start_date, end_date):
        _run_converter(date, force=args.force)


if __name__ == "__main__":
    main()

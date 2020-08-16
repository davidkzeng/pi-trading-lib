import argparse

from pi_trading_lib.data.data_archive import DataArchive
from pi_trading_lib.data.fivethirtyeight import FiveThirtyEightArchiver
import pi_trading_lib.dates
import pi_trading_lib.logging

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive_location')
    parser.add_argument('date')
    args = parser.parse_args()

    pi_trading_lib.logging.init_logging()
    date = pi_trading_lib.dates.from_date_str(args.date)
    archive = DataArchive(args.archive_location)
    fivethirtyeight_archiver = FiveThirtyEightArchiver(archive)

    fivethirtyeight_archiver.archive_data(date)

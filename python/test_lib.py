# Testing various components
import sys
import datetime
import argparse

import pi_trading_lib.data.market_data
import pi_trading_lib.work_dir
import pi_trading_lib.logging


def main(args):
    pi_trading_lib.logging.init_logging()
    with pi_trading_lib.work_dir.WorkDir(args.work_dir) as work_dir:
        market_data = pi_trading_lib.data.market_data.MarketData(work_dir)
        df = market_data.get_df(datetime.date(2020, 8, 13), datetime.date(2020, 8, 15))
        print(df)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work-dir')
    args = parser.parse_args(sys.argv[1:])
    main(args)

# Testing various components
import logging
import sys
import datetime

import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.work_dir


def main():
    work_dir = pi_trading_lib.work_dir.WorkDir(sys.argv[1])
    logging.basicConfig(level=logging.INFO)
    df = market_data.get_df(datetime.date(2020, 8, 15), datetime.date(2020, 8, 15), work_dir)
    print(df)


if __name__ == '__main__':
    assert len(sys.argv) == 2
    main()

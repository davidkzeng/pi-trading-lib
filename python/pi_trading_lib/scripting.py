# flake8: noqa

from datetime import date, datetime, timedelta

from pi_trading_lib.work_dir import WorkDir
from pi_trading_lib.data.data_archive import DataArchive
from pi_trading_lib.data.market_data import MarketData
from pi_trading_lib.data.fivethirtyeight import FiveThirtyEight, FiveThirtyEightArchiver

import pi_trading_lib.data.contracts as contracts
import pi_trading_lib.states as states
import pi_trading_lib.logging as logging

logging.init_logging()

work_dir = WorkDir()
data_archive = DataArchive()
market_data = MarketData(work_dir, data_archive)
fte = FiveThirtyEight(data_archive)

yesterday = (datetime.now() - timedelta(days=1)).date()

# Testing various components
import logging

import pi_trading_lib.data.market_data as md

logging.basicConfig(level=logging.INFO)
md.get_raw_market_data("20200813")

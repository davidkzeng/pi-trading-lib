import os.path
import json
import logging

import pi_trading_lib.data.data_sources as data_sources


def get_raw_market_data(date: str):
    # Temp we should just do this in rust
    market_data_file = data_sources.get_data_file('market_data_raw', date)
    assert os.path.exists(market_data_file)

    logging.info("Loading %s" % market_data_file)
    with open(market_data_file, 'r') as market_data_f:
        for line in market_data_f:
            line = line.rstrip()
            update = json.loads(line)
            print(update)

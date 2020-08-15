import typing as t
import os.path
import json
import logging
import datetime
import csv

import pandas as pd  # type: ignore
import dateutil.parser

import pi_trading_lib.data.data_sources as data_sources
import pi_trading_lib.work_dir as work_dir
import pi_trading_lib.fs as fs


class MarketData:
    def __init__(self, work_dir: work_dir.WorkDir):
        self.work_dir = work_dir

    def get_raw(self, date: datetime.date) -> t.Optional[t.List[t.Dict]]:
        # Temp we should just do this in rust
        market_data_file = data_sources.get_data_file('market_data_raw', date)
        if not os.path.exists(market_data_file):
            logging.warn('No raw market data for {date}'.format(date=str(date)))
            return None

        market_updates = []
        logging.info('Loading raw market data file %s' % market_data_file)
        with open(market_data_file, 'r') as market_data_f:
            for line in market_data_f:
                line = line.rstrip()
                updates = json.loads(line)['market_updates']  # Map from market_id -> market_info
                market_updates.extend(updates.values())
        return market_updates

    def get_csv(self, date: datetime.date) -> t.Optional[str]:
        md_csv = self.work_dir.md_csv(date)
        if os.path.exists(md_csv):
            return md_csv

        raw_market_data = self.get_raw(date)
        if raw_market_data is None:
            return None

        for update in raw_market_data:
            update['timestamp'] = dateutil.parser.isoparse(update['timestamp'])

        # We present market data "pessmistically" by taking the last update for each day and give a
        # pessimistic timestamp
        sorted_market_data = sorted(raw_market_data, key=lambda update: update['timestamp'], reverse=True)
        daily_market_data = {}
        for market_update in sorted_market_data:
            if market_update['id'] not in daily_market_data:
                daily_market_data[market_update['id']] = market_update
        timestamp = datetime.datetime(date.year, date.month, date.day,
                                      hour=23, minute=59, second=59, tzinfo=datetime.timezone.utc)

        columns = ['timestamp', 'market_id', 'contract_id', 'bid_price', 'ask_price', 'trade_price', 'name']
        with fs.safe_open(md_csv, 'w+', newline='') as md_csv_f:
            writer = csv.DictWriter(md_csv_f, fieldnames=columns)
            writer.writeheader()
            for market in daily_market_data.values():
                for contract in market['contracts']:
                    row = {
                        'timestamp': timestamp,
                        'market_id': market['id'],
                        'contract_id': contract['id'],
                        'bid_price': contract['bid_price'],
                        'ask_price': contract['ask_price'],
                        'trade_price': contract['trade_price'],
                        'name': market['name'] + ':' + contract['name']
                    }
                    writer.writerow(row)

        return md_csv

    def get_df(self, start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
        """Get market data dataframe, including start_date and end_date"""
        assert end_date >= start_date

        date_dfs = []

        num_dates = (end_date - start_date).days + 1
        for i in range(num_dates):
            cur_date = start_date + datetime.timedelta(days=i)
            market_data_csv = self.get_csv(cur_date)
            if market_data_csv is None:
                continue

            with open(market_data_csv, 'r') as market_data_csv_f:
                date_dfs.append(pd.read_csv(market_data_csv_f))

        return pd.concat(date_dfs, axis=0, ignore_index=True)

import typing as t
import datetime
import os
import os.path
import csv
import logging
import urllib.request
import io
import functools
import pandas as pd  # type: ignore

import pi_trading_lib
import pi_trading_lib.dates as dates
import pi_trading_lib.fs as fs
import pi_trading_lib.utils as utils
import pi_trading_lib.states as states
import pi_trading_lib.data.data_archive as data_archive

CONFIG_FILE = os.path.join(pi_trading_lib.get_package_dir(), 'config/fivethirtyeight.csv')


# Archiving
def archive_data(date: datetime.date) -> None:
    with open(CONFIG_FILE, 'r') as data_config_f:
        reader = csv.DictReader(data_config_f)
        for row in reader:
            name = row['name']
            start_date, end_date = row['start_date'], row['end_date']
            location = row['location']

            if (
                    (start_date and date < dates.from_date_str(start_date)) or
                    (end_date and date > dates.from_date_str(end_date))
               ):
                logging.info("Out of date range, ignoring data source {name}".format(name=name))
                break

            save_location = data_archive.get_data_file(name, {'date': dates.to_date_str(date)})
            if os.path.exists(save_location):
                break

            with urllib.request.urlopen(location) as f:
                reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))

                assert reader.fieldnames is not None
                assert 'modeldate' in reader.fieldnames

                rows_written = 0
                with fs.safe_open(save_location, 'w+', newline='') as save_f:
                    writer = csv.DictWriter(save_f, fieldnames=reader.fieldnames)
                    writer.writeheader()
                    # Currently true for all 538 data
                    for row in reader:
                        # 538 file may contain rows for previous dates
                        model_date = datetime.datetime.strptime(row['modeldate'], '%m/%d/%Y').date()
                        if model_date == date:
                            writer.writerow(row)
                            rows_written += 1
                if rows_written == 0:
                    logging.warn("No rows found for {name} for {date}".format(name=name, date=date))


# Reading
@functools.lru_cache()
def _get_data_sources():
    with open(CONFIG_FILE, 'r') as data_config_f:
        reader = csv.DictReader(data_config_f)
        return [row['name'] for row in reader]


def get_csv(name: str, date: datetime.date) -> t.Optional[str]:
    assert name in _get_data_sources()
    data_file = data_archive.get_data_file(name, {'date': dates.to_date_str(date)})
    return data_file


def _process_pres_state_2020(df: pd.DataFrame) -> pd.DataFrame:
    df['state'] = df.apply(lambda row: states.get_state_abbrv_pres(row['state']), axis=1)
    return df


@utils.copy
@functools.lru_cache()
def get_df(name: str, start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
    """Get market data dataframe, including start_date and end_date"""
    base_df = pd.concat([get_csv(name, date) for date in dates.date_range(start_date, end_date)], axis=0)

    if name == 'pres_state_2020':
        base_df = _process_pres_state_2020(base_df)

    return base_df

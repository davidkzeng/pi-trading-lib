import typing as t
import datetime
import os
import os.path
import csv
import logging
import urllib.request
import io
import functools
import json
import pandas as pd  # type: ignore

import pi_trading_lib
import pi_trading_lib.datetime_ext as datetime_ext
import pi_trading_lib.fs as fs
import pi_trading_lib.decorators
import pi_trading_lib.states as states
import pi_trading_lib.data.data_archive as data_archive

CONFIG_FILE = os.path.join(pi_trading_lib.get_package_dir(), 'config/fivethirtyeight.csv')
START_DATE = '20200816'


def archive_csv(location, save_location, date_col, date_format, date, name) -> None:
    with urllib.request.urlopen(location) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))

        assert reader.fieldnames is not None
        assert date_col in reader.fieldnames

        rows_written = 0
        with fs.safe_open(save_location, 'w+', newline='') as save_f:
            writer = csv.DictWriter(save_f, fieldnames=reader.fieldnames)
            writer.writeheader()
            for row in reader:
                # 538 file may contain rows for previous dates
                model_date = datetime.datetime.strptime(row[date_col], date_format).date()
                if model_date == date:
                    writer.writerow(row)
                    rows_written += 1
        if rows_written == 0:
            logging.warn("No rows found for {name} for {date}".format(name=name, date=date))


def archive_sim_2020_json(location, save_location) -> None:
    with urllib.request.urlopen(location) as f:
        sim_data = json.load(io.TextIOWrapper(f, encoding='utf-8'))
        states = sim_data['states']
        maps = sim_data['maps']
        columns = ['winner', 'trump_ev', 'biden_ev'] + states

        with fs.safe_open(save_location, 'w+', newline='') as save_f:
            writer = csv.writer(save_f)
            writer.writerow(columns)
            for map_data in maps:
                writer.writerow(map_data)


# Archiving
def archive_data(date: datetime.date) -> None:
    with open(CONFIG_FILE, 'r') as data_config_f:
        reader = csv.DictReader(data_config_f)
        for row in reader:
            name = row['name']
            begin_date, end_date = row['begin_date'], row['end_date']
            location = row['location']

            if (
                    (begin_date and date < datetime_ext.from_str(begin_date)) or
                    (end_date and date > datetime_ext.from_str(end_date))
               ):
                logging.info("Out of date range, ignoring data source {name}".format(name=name))
                continue

            save_location = data_archive.get_data_file(name, {'date': datetime_ext.to_str(date)})
            if os.path.exists(save_location):
                logging.info(f"Data already exists: {save_location}")
                continue

            if location.endswith('.csv'):
                date_col, date_format = row['date_col'], row['date_format']
                archive_csv(location, save_location, date_col, date_format, date, name)
            elif name == 'pres_sim_2020':
                archive_sim_2020_json(location, save_location)
            else:
                assert False, f"Archiving logic not implemented for {name}"


# Reading
@functools.lru_cache()
def _get_data_sources():
    with open(CONFIG_FILE, 'r') as data_config_f:
        reader = csv.DictReader(data_config_f)
        return [row['name'] for row in reader]


def get_csv(name: str, date: datetime.date) -> t.Optional[str]:
    assert name in _get_data_sources()
    data_file = data_archive.get_data_file(name, {'date': datetime_ext.to_str(date)})
    return data_file


def _process_pres_state_2020(df: pd.DataFrame) -> pd.DataFrame:
    df['state'] = df.apply(lambda row: states.get_state_abbrv_pres(row['state']), axis=1)
    return df


@pi_trading_lib.decorators.copy
@functools.lru_cache()
def get_df(name: str, begin_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
    """Get market data dataframe, including begin_date and end_date"""
    base_df = pd.concat(
        [pd.read_csv(get_csv(name, date)) for date in datetime_ext.date_range(begin_date, end_date)], axis=0
    )

    if name == 'pres_state_2020':
        base_df = _process_pres_state_2020(base_df)

    return base_df

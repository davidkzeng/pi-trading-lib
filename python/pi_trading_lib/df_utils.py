import typing as t
import datetime

import pandas as pd  # type: ignore


def df_from_csvs(get_csv_fn: t.Callable[[datetime.date], pd.DataFrame], start_date: datetime.date,
                 end_date: datetime.date) -> pd.DataFrame:
    assert end_date >= start_date

    date_dfs = []

    num_dates = (end_date - start_date).days + 1
    for i in range(num_dates):
        cur_date = start_date + datetime.timedelta(days=i)
        data_csv = get_csv_fn(cur_date)
        if data_csv is None:
            continue

        with open(data_csv, 'r') as data_csv_f:
            date_dfs.append(pd.read_csv(data_csv_f))

    return pd.concat(date_dfs, axis=0, ignore_index=True)

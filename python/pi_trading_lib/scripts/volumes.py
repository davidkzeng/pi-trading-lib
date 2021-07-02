"""Get approximation for market volumes by going off of quote updates"""
import argparse

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import pi_trading_lib.data.data_archive
import pi_trading_lib.data.market_data
import pi_trading_lib.datetime_ext as datetime_ext


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('begin_date')
    parser.add_argument('end_date')
    parser.add_argument('--data-archive')
    parser.add_argument('--hist', choices=['contract', 'market'])

    args = parser.parse_args()
    if args.data_archive:
        pi_trading_lib.data.data_archive.set_archive_dir(args.data_archive)

    begin_date = datetime_ext.from_str(args.begin_date)
    end_date = datetime_ext.from_str(args.end_date)

    if args.hist:
        date_range = list(datetime_ext.date_range(begin_date, end_date))
        dfs = []
        for date in date_range:
            df = pi_trading_lib.data.market_data.get_raw_data(date)
            if len(df) == 0:
                continue
            else:
                first_ts = df.index.get_level_values('timestamp')[0]
                quote_updates = df.loc[df.index.get_level_values('timestamp') != first_ts]
                dfs.append(quote_updates)
        merged_df = pd.concat(dfs, axis=0)

        if args.hist == 'contract':
            counts = merged_df.index.get_level_values('contract_id').value_counts()
        else:
            counts = merged_df['market_id'].value_counts()
        fig = go.Figure([go.Bar(x=counts.index.to_numpy().astype(str), y=counts.to_numpy())])
        fig.show()
    else:
        date_range = list(datetime_ext.date_range(begin_date, end_date))
        df_lengths = []
        df_date_range = []
        for date in date_range:
            if pi_trading_lib.data.market_data.incomplete_market_data(date):
                continue

            df = pi_trading_lib.data.market_data.get_raw_data(date)
            if len(df) == 0:
                continue
            else:
                first_ts = df.index.get_level_values('timestamp')[0]
                quote_updates = np.count_nonzero(df.index.get_level_values('timestamp') != first_ts)
                df_lengths.append(quote_updates)
                df_date_range.append(date)

        fig = go.Figure(data=go.Scatter(x=df_date_range, y=df_lengths))
        fig.show()


if __name__ == "__main__":
    main()

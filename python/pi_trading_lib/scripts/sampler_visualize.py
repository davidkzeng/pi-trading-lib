import argparse
import subprocess
import random
import datetime
import os

# import matplotlib.pyplot as plt
import plotly.graph_objects as go
from scipy import stats
import pandas as pd

import pi_trading_lib.datetime_ext as datetime_ext
import pi_trading_lib.data.market_data
import pi_trading_lib.utils


def rand_small():
    return (random.random() * 0.01) - 0.005


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('begin_date')
    parser.add_argument('end_date')
    parser.add_argument('--cids', nargs='*', default=[])

    args = parser.parse_args()

    begin_date = datetime.datetime.strptime(args.begin_date, '%Y%m%d').date()
    end_date = datetime.datetime.strptime(args.end_date, '%Y%m%d').date()

    rg = datetime_ext.date_range(begin_date, end_date)

    dfs = []
    for d in rg:
        if not pi_trading_lib.data.market_data.bad_market_data(d):
            date_str = datetime_ext.to_str(d)
            input_uri = pi_trading_lib.data.data_archive.get_data_file('market_data_csv', {'date': date_str})
            output_uri = pi_trading_lib.data.data_archive.get_data_file('sampler', {'date': date_str})
            cmd = [
                os.path.join(pi_trading_lib.utils.get_rust_bin_dir(), 'sampler'),
                input_uri,
                output_uri,
            ]
            subprocess.run(cmd)
            df = pd.read_csv(output_uri)
            dfs.append(df)
    df = pd.concat(dfs)
    if args.cids:
        df = df[df['id'].isin(args.cids)]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['rand'] = df.apply(lambda row: rand_small(), axis=1)
    df['rand2'] = df.apply(lambda row: rand_small(), axis=1)

    df = df[(df['tick'] - df['back'] > 0.05) & (df['tick'] - df['back'] < 0.5)]
    print((df['forward'] - df['tick']).mean())
    x, y = (df['tick'] - df['back'] + df['rand']).to_numpy(), (df['forward'] - df['tick'] + df['rand2']).to_numpy()
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    print(slope, intercept, r_value)

    text = df['id'].astype(str) + ' : ' + df['tick'].astype(str) + ' : ' + df['timestamp'].astype(str)
    line = slope * x + intercept
    fig = go.Figure(data=[
        go.Scattergl(x=x, y=y, text=text, mode='markers'),
        go.Scattergl(x=x, y=line, mode='lines')
    ])
    fig.show()


if __name__ == "__main__":
    main()

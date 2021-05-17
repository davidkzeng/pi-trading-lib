import argparse
import subprocess
import random
import datetime
import os

# import matplotlib.pyplot as plt
import plotly.graph_objects as go
from scipy import stats
import pandas as pd

import pi_trading_lib.date_util as date_util
import pi_trading_lib.data.market_data
import pi_trading_lib.utils


def rand_small():
    return (random.random() * 0.01) - 0.005


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('start_date')
    parser.add_argument('end_date')

    args = parser.parse_args()

    start_date = datetime.datetime.strptime(args.start_date, '%Y%m%d').date()
    end_date = datetime.datetime.strptime(args.end_date, '%Y%m%d').date()

    rg = date_util.date_range(start_date, end_date)

    dfs = []
    for d in rg:
        if not pi_trading_lib.data.market_data.bad_market_data(d):
            date_str = date_util.to_date_str(d)
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
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    print(df[df['id'] == 25662])
    df['rand'] = df.apply(lambda row: rand_small(), axis=1)
    df['rand2'] = df.apply(lambda row: rand_small(), axis=1)

    df = df[(df['tick'] - df['back']) > 0.06]
    x, y = (df['tick'] - df['back'] + df['rand']).to_numpy(), (df['forward'] - df['tick'] + df['rand2']).to_numpy()
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    print(slope, intercept, r_value)

    line = slope * x + intercept
    fig = go.Figure(data=[
        go.Scattergl(x=x, y=y, text=(df['id'].astype(str) + ' : ' + df['timestamp'].astype(str)), mode='markers'),
        go.Scattergl(x=x, y=line, mode='lines')
    ])
    fig.show()


if __name__ == "__main__":
    main()

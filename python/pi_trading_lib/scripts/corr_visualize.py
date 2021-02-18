import argparse
import datetime
# import matplotlib.pyplot as plt
import plotly.graph_objects as go
from scipy import stats

import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.data.data_archive as data_archive
import pi_trading_lib.learning.window_corr as window_corr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('start_date')
    parser.add_argument('end_date')
    parser.add_argument('window')  # minutes
    parser.add_argument('rate')  # minutes
    parser.add_argument('cids', nargs='+') # TODO allow cids to be *
    parser.add_argument('--data-archive')
    parser.add_argument('--cutoff', default=0.01)

    args = parser.parse_args()

    if args.data_archive:
        data_archive.set_archive_dir(args.data_archive)

    cids = tuple(int(cid) for cid in args.cids)
    start_date = datetime.datetime.strptime(args.start_date, '%Y%m%d').date()
    end_date = datetime.datetime.strptime(args.end_date, '%Y%m%d').date()
    data = market_data.get_df(start_date, end_date, contracts=cids)

    corrs_df = window_corr.sample_md(data, int(args.window), int(args.rate), cids)
    corrs_df = corrs_df.reset_index()
    corrs_df = corrs_df[corrs_df['back'].abs() >= float(args.cutoff)]
    corrs_df['text'] = corrs_df['contract_id'].astype(str) + '_' + corrs_df['timestamp'].astype(str)

    x, y = corrs_df['back'].to_numpy(), corrs_df['front'].to_numpy()
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    print(slope, intercept, r_value)

    line = slope * x + intercept
    fig = go.Figure(data=[
        go.Scattergl(x=x, y=y, text=corrs_df['text'], mode='markers'),
        go.Scattergl(x=x, y=line, mode='lines')
    ])
    fig.show()


if __name__ == "__main__":
    main()

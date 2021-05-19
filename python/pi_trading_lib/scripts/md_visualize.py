import argparse
import datetime
import matplotlib.pyplot as plt
import plotly.graph_objects as go

import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.data.data_archive as data_archive


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('start_date')
    parser.add_argument('end_date')
    parser.add_argument('--mids', nargs='*')
    parser.add_argument('--cids', nargs='*')
    parser.add_argument('--backend', choices=['matplotlib', 'plotly'], default='plotly')
    parser.add_argument('--bid-ask', action='store_true')
    parser.add_argument('--data-archive')

    args = parser.parse_args()

    if args.data_archive:
        data_archive.set_archive_dir(args.data_archive)

    mids = tuple(int(mid) for mid in args.mids) if args.mids is not None else None
    cids = tuple(int(cid) for cid in args.cids) if args.cids is not None else None

    start_date = datetime.datetime.strptime(args.start_date, '%Y%m%d').date()
    end_date = datetime.datetime.strptime(args.end_date, '%Y%m%d').date()
    data = market_data.get_df(start_date, end_date, markets=mids, contracts=cids)

    if args.bid_ask:
        plot_df = data[['bid_price', 'ask_price']]
    else:
        plot_df = data['mid_price']

    plot_df = plot_df.unstack(level=1)  # unstack the contract_id index

    if args.backend == 'plotly':
        fig = go.Figure()
        for series in plot_df:
            fig.add_trace(go.Scatter(
                x=plot_df.index,
                y=plot_df[series].to_numpy(),
                mode='lines',
                name=str(series),
                connectgaps=True,
            ))
        fig.show()
    elif args.backend == 'matplotlib':
        plot_df.plot(figsize=(20, 10))
        plt.show()


if __name__ == "__main__":
    main()

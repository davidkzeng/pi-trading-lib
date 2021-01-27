import argparse
import datetime
import matplotlib.pyplot as plt
import plotly.graph_objects as go

import pi_trading_lib.data.market_data as market_data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('start_date')
    parser.add_argument('end_date')
    parser.add_argument('mids', nargs='+')
    parser.add_argument('--interactive', action='store_true')
    parser.add_argument('--bid-ask', action='store_true')
    args = parser.parse_args()

    mids = tuple(int(mid) for mid in args.mids)
    start_date = datetime.datetime.strptime(args.start_date, '%Y%m%d').date()
    end_date = datetime.datetime.strptime(args.end_date, '%Y%m%d').date()
    data = market_data.get_df(start_date, end_date, markets=mids)

    if args.bid_ask:
        plot_df = data[['bid_price', 'ask_price']]
    else:
        plot_df = data['mid_price']

    plot_df = plot_df.unstack(level=1)  # unstack the contract_id index

    if args.interactive:
        fig = go.Figure()
        for series in plot_df:
            fig.add_trace(go.Scatter(
                x=plot_df.index.to_numpy(),
                y=plot_df[series].to_numpy(),
                mode='lines',
                name=str(series)
            ))
        fig.show()
    else:
        plot_df.plot(figsize=(20, 10))
        plt.show()


if __name__ == "__main__":
    main()

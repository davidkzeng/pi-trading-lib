import argparse
import datetime
import itertools
import matplotlib.pyplot as plt
import plotly.graph_objects as go

import pi_trading_lib.data.market_data as market_data
import pi_trading_lib.data.data_archive as data_archive
import pi_trading_lib.data.contracts
import pi_trading_lib.date_util


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--begin_date')
    parser.add_argument('--end_date')
    parser.add_argument('--mids', nargs='*', default=[])
    parser.add_argument('--cids', nargs='*', default=[])
    parser.add_argument('--backend', choices=['matplotlib', 'plotly'], default='plotly')
    parser.add_argument('--bid-ask', action='store_true')
    parser.add_argument('--data-archive')

    args = parser.parse_args()

    if args.data_archive:
        data_archive.set_archive_dir(args.data_archive)

    mids = tuple(int(mid) for mid in args.mids)
    cids = tuple(int(cid) for cid in args.cids)

    assert mids or cids

    if mids is not None:
        if cids is None:
            cids = []
        cids = cids + tuple(itertools.chain(*(pi_trading_lib.data.contracts.get_market_contracts(mids).values())))

    if not args.begin_date and not args.end_date:
        # Inferring start and end date based on contract ranges
        contracts = pi_trading_lib.data.contracts.get_contracts(cids).values()
        begin_date = min(contract['begin_date'] for contract in contracts)
        end_date = max([contract['end_date'] for contract in contracts if contract['end_date'] is not None],
                       default=datetime.date.today())
    else:
        begin_date = datetime.datetime.strptime(args.begin_date, '%Y%m%d').date()
        end_date = datetime.datetime.strptime(args.end_date, '%Y%m%d').date()
    data = market_data.get_df(begin_date, end_date, contracts=cids)

    if args.bid_ask or len(cids) == 1:
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

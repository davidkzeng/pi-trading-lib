import argparse
import sys

import matplotlib.pyplot as plt

from pi_trading_lib.score import SimResult
import pi_trading_lib.data.market_data as market_data


def print_df(df, csv=False):
    if csv:
        try:
            df.to_csv(sys.stdout)
        except BrokenPipeError:
            pass
    else:
        print(df)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    subparsers = parser.add_subparsers(dest='subparser', required=True)

    subparsers.add_parser('plot')
    subparsers.add_parser('pnl')

    cids_parser = subparsers.add_parser('cids')
    cids_parser.add_argument('--csv', action='store_true')

    cid_parser = subparsers.add_parser('cid')
    cid_parser.add_argument('cid')
    cid_parser.add_argument('--csv', action='store_true')

    fill_parser = subparsers.add_parser('fill')
    fill_parser.add_argument('--cid')

    args = parser.parse_args()

    sim_result = SimResult.load(args.path)

    if args.subparser == 'plot':
        sim_result.daily_summary[['capital', 'pos_value', 'value', 'net_cost', 'mark_pnl']].plot()
        plt.show()
    elif args.subparser == 'pnl':
        sim_result.daily_pnl.cumsum().plot()
        plt.show()
    elif args.subparser == 'cids':
        cid_summary = sim_result.cid_summary
        cid_summary['abs_mark'] = cid_summary['mark_pnl'].abs()
        cid_summary = cid_summary.sort_values('abs_mark', ascending=False)
        print_df(cid_summary, args.csv)
    elif args.subparser == 'cid':
        cid = int(args.cid)
        daily_cid_summary = sim_result.daily_cid_summary
        cid_summary = daily_cid_summary.xs(cid, level='cid')
        begin_date = cid_summary.index[0]
        end_date = cid_summary.index[-1]
        data = market_data.get_df(begin_date, end_date, contracts=tuple([cid])).reset_index('contract_id', drop=True)
        data = data[['bid_price', 'ask_price', 'mid_price', 'trade_price']]

        combined = data.join(cid_summary, how='outer')
        combined = combined.ffill()

        fig, axs = plt.subplots(nrows=2)
        combined[['bid_price', 'ask_price', 'mid_price', 'trade_price']].plot(ax=axs[0])
        combined[['position', 'val', 'mark_pnl']].plot(ax=axs[1])
        plt.show()


if __name__ == "__main__":
    main()

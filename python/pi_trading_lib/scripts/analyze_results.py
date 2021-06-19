import argparse
import sys

import matplotlib.pyplot as plt

from pi_trading_lib.score import SimResult


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    subparsers = parser.add_subparsers(dest='subparser', required=True)

    _plot_parser = subparsers.add_parser('plot')
    cid_parser = subparsers.add_parser('cid')
    cid_parser.add_argument('--csv', action='store_true')
    assert _plot_parser

    args = parser.parse_args()

    sim_result = SimResult.load(args.path)

    if args.subparser == 'plot':
        sim_result.daily_summary[['capital', 'pos_value', 'value', 'net_cost', 'mark_pnl']].plot()
        plt.show()
    elif args.subparser == 'cid':
        cid_summary = sim_result.cid_summary
        cid_summary['abs_mark'] = cid_summary['mark_pnl'].abs()
        cid_summary = cid_summary.sort_values('abs_mark', ascending=False)
        if args.csv:
            try:
                cid_summary.to_csv(sys.stdout)
            except BrokenPipeError:
                pass
        else:
            print(cid_summary)


if __name__ == "__main__":
    main()

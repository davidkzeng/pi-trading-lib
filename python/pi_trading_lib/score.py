import os
import typing as t

import pandas as pd

import pi_trading_lib.fs as fs


class SimResult:
    def __init__(self, book_summary: pd.DataFrame, cid_summary: pd.DataFrame,
                 daily_summary: pd.DataFrame, daily_cid_summary: pd.DataFrame,
                 fillstats: pd.DataFrame, path: t.Optional[str] = None):
        self.book_summary = book_summary
        self.cid_summary = cid_summary
        self.daily_summary = daily_summary
        self.daily_cid_summary = daily_cid_summary
        self.fillstats = fillstats
        self.path = path

    @staticmethod
    def load(path) -> 'SimResult':
        daily_summary = pd.read_csv(os.path.join(path, 'daily_summary.csv'), index_col='date',
                                    parse_dates=['date'])
        daily_sim_summary = pd.read_csv(os.path.join(path, 'daily_cid_summary.csv'), index_col=['date', 'cid'],
                                        parse_dates=['date'])

        result = SimResult(
            pd.read_csv(os.path.join(path, 'book_summary.csv'), index_col=0),
            pd.read_csv(os.path.join(path, 'cid_summary.csv'), index_col=0),
            daily_summary,
            daily_sim_summary,
            pd.read_csv(os.path.join(path, 'fillstats.csv'), index_col=['fill_id']),
            path=path,
        )
        return result

    def dump(self):
        assert self.path is not None

        with fs.atomic_output(self.path) as tmpdir:
            self.book_summary.to_csv(os.path.join(tmpdir, 'book_summary.csv'), float_format='%.3f')
            self.cid_summary.to_csv(os.path.join(tmpdir, 'cid_summary.csv'), float_format='%.3f')
            self.daily_summary.to_csv(os.path.join(tmpdir, 'daily_summary.csv'), float_format='%.3f')
            self.daily_cid_summary.to_csv(os.path.join(tmpdir, 'daily_cid_summary.csv'), float_format='%.3f')
            self.fillstats.to_csv(os.path.join(tmpdir, 'fillstats.csv'), float_format='%.3f')

    @property
    def score(self):
        return self.book_summary.iloc[0]['value']

    @property
    def ndays(self):
        return len(self.daily_summary)

    @property
    def daily_pnl(self) -> pd.Series:
        return (self.daily_summary['value'] - self.daily_summary['value'].shift()).dropna()

    @property
    def sharpe(self):
        mu = self.daily_pnl.mean()
        sigma = self.daily_pnl.std()
        return mu / sigma

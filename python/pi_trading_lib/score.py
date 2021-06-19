import os

import pandas as pd

import pi_trading_lib.fs as fs


class SimResult:
    def __init__(self, book_summary: pd.Series, cid_summary: pd.DataFrame, daily_summary: pd.DataFrame):
        self.book_summary = book_summary
        self.cid_summary = cid_summary
        self.daily_summary = daily_summary

    @staticmethod
    def load(path) -> 'SimResult':
        return SimResult(
            pd.read_csv(os.path.join(path, 'book_summary.csv'), index_col=0),
            pd.read_csv(os.path.join(path, 'cid_summary.csv'), index_col=0),
            pd.read_csv(os.path.join(path, 'daily_summary.csv'), index_col=0),
        )

    def dump(self, path):
        with fs.atomic_output(path) as tmpdir:
            self.book_summary.to_csv(os.path.join(tmpdir, 'book_summary.csv'))
            self.cid_summary.to_csv(os.path.join(tmpdir, 'cid_summary.csv'))
            self.daily_summary.to_csv(os.path.join(tmpdir, 'daily_summary.csv'))

    @property
    def score(self):
        return self.book_summary.iloc[0]['value']

import pandas as pd


class SimScore:
    def __init__(self, book_summary: pd.Series, cid_summary: pd.DataFrame, daily_summary: pd.DataFrame):
        self.book_summary = book_summary
        self.cid_summary = cid_summary
        self.daily_summary = daily_summary

    @property
    def value(self):
        return self.book_summary['value']

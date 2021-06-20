import pandas as pd

from pi_trading_lib.accountant import Book


class Fillstats:
    def __init__(self):
        self.fills = []
        pass

    def add_fill(self, book: Book, md: pd.DataFrame):
        pass

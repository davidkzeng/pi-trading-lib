import datetime
import typing as t

import pandas as pd

import pi_trading_lib.date_util as date_util


class Fill:
    BASE_COLUMNS = [
        'cid',
        'date',
    ]
    BOOK_COLUMNS = [
        'pos',
        'qty',
        'bid_price',
        'ask_price',
        'cost',
        'exe_value',
    ]

    def __init__(self):
        # turn this into a 1 row dataframe?
        self.info: t.Dict[str, t.Any] = {}
        self.price_models = 0

    def add_book_info(self, book_info: pd.Series):
        self.info.update(
            book_info.loc[Fill.BOOK_COLUMNS].to_dict(),
        )
        self.info.update({'cid': book_info.name})

    def add_sim_info(self, date: datetime.date):
        self.info.update({'date': date_util.to_str(date)})

    def add_model_info(self, model_info: t.Dict[str, t.Any]):
        # TODO: do some safety check in columns
        self.info.update(
            model_info
        )

    def add_opt_info(self, optimizer_info: t.Dict[str, t.Any]):
        self.info.update(
            optimizer_info
        )


class Fillstats:
    def __init__(self):
        self.fills: t.List[Fill] = []

    def add_fills(self, fills: t.List[Fill]):
        self.fills.extend(fills)

    def to_frame(self) -> pd.DataFrame:
        fill_infos = [fill.info for fill in self.fills]
        if len(fill_infos) > 0:
            df = pd.DataFrame(fill_infos)
        else:
            df = pd.DataFrame([], columns=Fill.BASE_COLUMNS + Fill.BOOK_COLUMNS)
        df['cid'] = df['cid'].astype(int)
        return df

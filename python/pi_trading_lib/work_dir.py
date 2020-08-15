import os
import datetime


class WorkDir:
    def __init__(self, root):
        self.root = root

    def md_csv(self, date: datetime.date) -> str:
        return os.path.join(self.root, 'market_data', date.strftime("%Y%m%d") + '.csv')

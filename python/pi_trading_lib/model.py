from pi_trading_lib.work_dir import WorkDir
from pi_trading_lib.data.data_archive import DataArchive
from pi_trading_lib.data.market_data import MarketData


class BaseModel:
    def __init__(self, archive_location):
        self.data_archive = DataArchive(archive_location)
        self.work_dir = WorkDir()
        self.market_data = MarketData(self.work_dir, self.data_archive)

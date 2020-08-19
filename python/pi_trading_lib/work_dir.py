import typing as t
import os
import datetime
import tempfile
import shutil
import logging
import atexit


class WorkDir:
    def __init__(self, root: t.Optional[str] = None):
        if root is None:
            root = tempfile.mkdtemp()
            atexit.register(self.cleanup)

        self.root = root
        logging.info("Using work directory %s" % self.root)

    def cleanup(self):
        if os.path.exists(self.root):
            logging.info("Cleaning up work directory %s" % self.root)
            shutil.rmtree(self.root)

    def md_csv(self, date: datetime.date) -> str:
        return os.path.join(self.root, 'market_data', date.strftime("%Y%m%d") + '.csv')

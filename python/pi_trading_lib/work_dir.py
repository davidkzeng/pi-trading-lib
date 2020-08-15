import typing as t
import os
import datetime
import tempfile
import shutil
import logging


class WorkDir:
    def __init__(self, root: t.Optional[str] = None):
        if root is None:
            root = tempfile.mkdtemp()
            self.cleanup = True
        else:
            self.cleanup = False

        self.root = root
        logging.info("Using work directory %s" % self.root)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.cleanup:
            logging.info("Cleaning up work directory %s" % self.root)
            shutil.rmtree(self.root)
        return True

    def md_csv(self, date: datetime.date) -> str:
        return os.path.join(self.root, 'market_data', date.strftime("%Y%m%d") + '.csv')

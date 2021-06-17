import os
import tempfile
import shutil
import logging
import atexit


_work_dir = os.environ.get('PI_WORK_DIR')


def set_work_dir(loc: str):
    global _work_dir
    _work_dir = loc


def get_work_dir():
    global _work_dir

    if _work_dir is None:
        _work_dir = tempfile.mkdtemp()
        atexit.register(cleanup)

    return _work_dir


def cleanup():
    if os.path.exists(_work_dir):
        logging.info("Cleaning up work directory %s" % _work_dir)
        shutil.rmtree(_work_dir)

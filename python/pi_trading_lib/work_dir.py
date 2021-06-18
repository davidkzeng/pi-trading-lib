import os
import tempfile
import shutil
import logging
import atexit

import mmh3

import pi_trading_lib.model_config as model_config


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


def strhash(s) -> str:
    params = sorted(s.items())
    param_str = ':'.join([key + ':' + str(value) for key, value in params])
    return mmh3.hash_bytes(param_str.encode(), 42).hex()


def get_uri(component: str, date, config: model_config.Config) -> str:
    return os.path.join(get_work_dir(), component, date, strhash(config.params))


def cleanup():
    if os.path.exists(_work_dir):
        logging.info("Cleaning up work directory %s" % _work_dir)
        shutil.rmtree(_work_dir)

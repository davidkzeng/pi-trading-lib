import os
import datetime
import tempfile
import shutil
import logging
import atexit
import typing as t

import mmh3

import pi_trading_lib.model_config as model_config
import pi_trading_lib.datetime_ext as datetime_ext


_work_dir = os.environ.get('PI_WORK_DIR')


def set_work_dir(loc: str):
    global _work_dir
    _work_dir = loc


def get_work_dir():
    global _work_dir

    if _work_dir is None:
        _work_dir = tempfile.mkdtemp()
        logging.warn(f'Using temporary work dir {_work_dir}, considering calling pi_trarding_lib.work_dir.set_work_dir()')
        atexit.register(cleanup)

    return _work_dir


def strhash(s) -> str:
    params = sorted(s.items())
    param_str = ':'.join([key + ':' + str(value) for key, value in params])
    return mmh3.hash_bytes(param_str.encode(), 42).hex()  # type: ignore


def get_uri(stage: str, config: model_config.Config,
            date_1: t.Optional[datetime.date] = None, date_2: t.Optional[datetime.date] = None) -> str:
    stage_suffix = ''
    if date_1 is not None:
        stage_suffix = os.path.join(stage_suffix, datetime_ext.to_str(date_1))
    if date_2 is not None:
        stage_suffix = os.path.join(stage_suffix, datetime_ext.to_str(date_2))

    return os.path.join(get_work_dir(), stage, stage_suffix, strhash(config.params))


def cleanup(stages='all'):
    if os.path.exists(_work_dir):
        logging.info("Cleaning up work directory %s" % _work_dir)
        if stages == 'all':
            shutil.rmtree(_work_dir)
        else:
            assert isinstance(stages, list)
            for stage in stages:
                if os.path.exists(os.path.join(_work_dir, stage)):
                    shutil.rmtree(os.path.join(_work_dir, stage))

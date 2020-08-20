"""Refactor this"""
import typing as t
import functools
import json
import os
import logging

import pi_trading_lib
import pi_trading_lib.fs as fs


def save_contract_data(name: str, data: t.Dict[int, t.Dict[int, t.List]]):
    contract_file = os.path.join(pi_trading_lib.get_package_dir(), 'config/contracts', name)
    if os.path.exists(contract_file):
        logging.warn('Overriding existing contract file: %s' % contract_file)

    with fs.safe_open(contract_file, 'w+') as contract_file_f:
        json.dump(data, contract_file_f, indent=2, sort_keys=True)


@functools.lru_cache()
def get_contract_data(name: str) -> t.Dict[int, t.Dict[int, t.List]]:
    contract_file = os.path.join(pi_trading_lib.get_package_dir(), 'config/contracts', name)
    assert os.path.exists(contract_file)

    with fs.safe_open(contract_file, 'r') as contract_f:
        return json.load(contract_f)


@functools.lru_cache()
def get_contract_ids(name: str) -> t.List[int]:
    contract_data = get_contract_data(name)
    return [cid for mid in contract_data for cid in contract_data[mid]]

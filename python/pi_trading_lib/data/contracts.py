"""Refactor this"""
import typing as t
import functools
import json
import os

import pi_trading_lib


@functools.lru_cache()
def get_pres_state_contracts() -> t.List[int]:
    config_file = os.path.join(
        pi_trading_lib.get_package_dir(), 'config/contracts/election_2020/states_pres.json'
    )
    state_contracts = []
    with open(config_file, 'r') as config_f:
        contract_dict = json.load(config_f)
        for key in contract_dict:
            _, contract_id = key.split(':')
            state_contracts.append(contract_id)
    return state_contracts

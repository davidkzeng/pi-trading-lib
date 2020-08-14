from typing import Dict, Optional
import csv
import functools
import os.path

import pi_trading_lib


@functools.lru_cache()
def _get_data_sources() -> Dict[str, str]:
    config_file = os.path.join(pi_trading_lib.get_package_dir(), 'config/data_sources.csv')

    data_sources = {}
    with open(config_file, 'r') as data_config_f:
        reader = csv.DictReader(data_config_f)
        for row in reader:
            source_name, source_location = row['name'], row['location']
            assert source_name not in data_sources
            data_sources[source_name] = os.path.join(pi_trading_lib.get_package_dir(), source_location)
    return data_sources


def get_data_file(name: str, date: Optional[str] = None) -> str:
    data_sources = _get_data_sources()
    location = data_sources[name]

    if "{date}" in location:
        assert date is not None
        location = location.format(date=date)

    return location

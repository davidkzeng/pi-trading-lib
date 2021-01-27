import typing as t
import csv
import functools
import os

import pi_trading_lib

# reads from environment for easier interactive workflows
_archive_dir = os.environ.get('PI_DATA_ARCHIVE')


def set_archive_dir(loc: str):
    global _archive_dir
    _archive_dir = loc


def get_archive_dir():
    assert _archive_dir is not None, "data archive not initialized"

    return _archive_dir


@functools.lru_cache()
def _get_data_archives() -> t.Dict[str, str]:
    config_file = os.path.join(pi_trading_lib.get_package_dir(), 'config/data_archive.csv')

    data_archives = {}
    with open(config_file, 'r') as data_config_f:
        reader = csv.DictReader(data_config_f)
        for row in reader:
            archive_name = row['name']
            archive_location = os.path.join(get_archive_dir(), row['location'])
            data_archives[archive_name] = archive_location
    return data_archives


def get_data_file(name: str, template_vals: t.Dict[str, t.Any]) -> str:
    data_archives = _get_data_archives()
    location_template = data_archives[name]
    location = location_template.format(**template_vals)

    return location

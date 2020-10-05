import typing as t
import csv
import functools
import os.path

import pi_trading_lib


archive_dir = None


def set_archive_dir(loc: str):
    global archive_dir
    archive_dir = loc


@functools.lru_cache()
def _get_data_archives() -> t.Dict[str, str]:
    assert archive_dir is not None, "data archive not initialized"

    config_file = os.path.join(pi_trading_lib.get_package_dir(), 'config/data_archive.csv')

    data_archives = {}
    with open(config_file, 'r') as data_config_f:
        reader = csv.DictReader(data_config_f)
        for row in reader:
            archive_name = row['name']
            archive_location = os.path.join(archive_dir, row['location'])
            data_archives[archive_name] = archive_location
    return data_archives


def get_data_file(name: str, template_vals: t.Dict[str, t.Any]) -> str:
    data_archives = _get_data_archives()
    location_template = data_archives[name]
    location = location_template.format(**template_vals)

    return location

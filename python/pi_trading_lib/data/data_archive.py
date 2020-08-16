import typing as t
import csv
import functools
import os.path

import pi_trading_lib


class DataArchive:
    DEFAULT_ARCHIVE_DIR = os.path.join(pi_trading_lib.get_package_dir(), 'data')

    def __init__(self, archive_dir: t.Optional[str] = None):
        if archive_dir is None:
            archive_dir = DataArchive.DEFAULT_ARCHIVE_DIR
        self.archive_dir = archive_dir

    @functools.lru_cache()
    def _get_data_archives(self) -> t.Dict[str, str]:
        config_file = os.path.join(pi_trading_lib.get_package_dir(), 'config/data_archive.csv')

        data_archives = {}
        with open(config_file, 'r') as data_config_f:
            reader = csv.DictReader(data_config_f)
            for row in reader:
                archive_name = row['name']
                archive_location = os.path.join(self.archive_dir, row['location'])
                data_archives[archive_name] = archive_location
        return data_archives

    def get_data_file(self, name: str, template_vals: t.Dict[str, t.Any]) -> str:
        data_archives = self._get_data_archives()
        location_template = data_archives[name]
        location = location_template.format(**template_vals)

        return location

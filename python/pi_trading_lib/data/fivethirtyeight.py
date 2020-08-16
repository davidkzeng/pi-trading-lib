import datetime
import os
import os.path
import csv
import logging
import urllib.request
import io

import pi_trading_lib
import pi_trading_lib.dates as dates
import pi_trading_lib.fs as fs
from pi_trading_lib.data.data_archive import DataArchive


class FiveThirtyEightArchiver:
    CONFIG_FILE = os.path.join(pi_trading_lib.get_package_dir(), 'config/fivethirtyeight.csv')

    def __init__(self, data_archive: DataArchive):
        self.data_archive = data_archive

    def archive_data(self, date: datetime.date) -> None:
        with open(FiveThirtyEightArchiver.CONFIG_FILE, 'r') as data_config_f:
            reader = csv.DictReader(data_config_f)
            for row in reader:
                name = row['name']
                start_date, end_date = row['start_date'], row['end_date']
                location = row['location']

                if (
                        (start_date and date < dates.from_date_str(start_date)) or
                        (end_date and date > dates.from_date_str(end_date))
                   ):
                    logging.info("Out of date range, ignoring data source {name}".format(name=name))
                    break

                save_location = self.data_archive.get_data_file(name, {'date': dates.to_date_str(date)})
                if os.path.exists(save_location):
                    break

                with urllib.request.urlopen(location) as f:
                    reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))

                    assert reader.fieldnames is not None
                    assert 'modeldate' in reader.fieldnames

                    rows_written = 0
                    with fs.safe_open(save_location, 'w+', newline='') as save_f:
                        writer = csv.DictWriter(save_f, fieldnames=reader.fieldnames)
                        writer.writeheader()
                        # Currently true for all 538 data
                        for row in reader:
                            # 538 file may contain rows for previous dates
                            model_date = datetime.datetime.strptime(row['modeldate'], '%m/%d/%Y').date()
                            if model_date == date:
                                writer.writerow(row)
                                rows_written += 1
                    if rows_written == 0:
                        logging.warn("No rows found for {name} for {date}".format(name=name, date=date))


class FiveThirtyEight:
    def __init__(self):
        pass

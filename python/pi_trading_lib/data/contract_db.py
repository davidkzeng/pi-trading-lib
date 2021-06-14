import os
import sys
import functools
import sqlite3
import typing as t

import pi_trading_lib.data.data_archive


MIGRATIONS = [
    '1_initialize.sql',
    '2_resolution.sql',
]
MIGRATION_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'db')


def to_sql_list(il: t.List[t.Any]):
    return '(' + ', '.join([str(item) for item in il]) + ')'


@functools.lru_cache
def get_contract_db():
    db_uri = pi_trading_lib.data.data_archive.get_data_file('contract_db')
    connection = sqlite3.connect(db_uri)
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def initialize_db():
    db = get_contract_db()

    starting_version = db.cursor().execute('pragma user_version').fetchone()[0]
    assert starting_version <= len(MIGRATIONS)

    for idx, migration in enumerate(MIGRATIONS[starting_version:]):
        print(f'Applying migration {os.path.basename(migration)}')
        current_version = starting_version + idx
        with open(os.path.join(MIGRATION_DIR, migration)) as sql_file:
            sql_cmd = sql_file.read()

        db.cursor().executescript(sql_cmd)
        db.cursor().execute(f'pragma user_version = {current_version + 1};')
        db.commit()
        print('Finished applying')


if __name__ == "__main__":
    assert len(sys.argv) <= 2
    if len(sys.argv) == 2:
        pi_trading_lib.data.data_archive.set_archive_dir(sys.argv[1])
    initialize_db()

CREATE TABLE contract (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    market_id INTEGER NOT NULL,
    begin_date TEXT NOT NULL,
    last_update_date TEXT NOT NULL,
    end_date TEXT,
    FOREIGN KEY(market_id) REFERENCES market(id)
);

CREATE TABLE market (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE daily_history (
    contract_id INTEGER,
    date TEXT NOT NULL,
    value REAL NOT NULL,
    value_type INTEGER NOT NULL,
    FOREIGN KEY(contract_id) REFERENCES contract(id),
    PRIMARY KEY(contract_id, date, value_type)
);

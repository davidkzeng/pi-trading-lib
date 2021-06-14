CREATE TABLE resolution (
    contract_id INTEGER,
    value REAL NOT NULL,
    FOREIGN KEY(contract_id) REFERENCES contract(id),
    PRIMARY KEY(contract_id, value)
);

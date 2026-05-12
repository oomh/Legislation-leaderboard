CREATE TABLE IF NOT EXISTS assembly_bills (
    id             SERIAL PRIMARY KEY,
    serial_number  INTEGER,
    bill_name      TEXT,
    sponsor        TEXT,
    bill_house     TEXT,
    bill_number    INTEGER,
    bill_year      INTEGER,
    gazette_number INTEGER,
    dated          DATE,
    maturity_date  DATE,
    first_reading  DATE,
    assent_date    DATE,
    gazette_period_days BIGINT,
    assent_period_days  BIGINT
);

CREATE TABLE IF NOT EXISTS members (
    id             SERIAL PRIMARY KEY,
    chamber        TEXT,
    name           TEXT,
    county         TEXT,
    constituency   TEXT,
    party          TEXT,
    status         TEXT,
    profile_url    TEXT
);

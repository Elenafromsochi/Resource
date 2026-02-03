CREATE TABLE IF NOT EXISTS participants (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    display_name VARCHAR,
    about TEXT,
    photo_bytes BYTEA,
    photo_mime VARCHAR
);

CREATE INDEX IF NOT EXISTS participants_username_idx
    ON participants (username);

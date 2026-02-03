CREATE TABLE IF NOT EXISTS participants (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    display_name VARCHAR,
    about TEXT,
    is_bot BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_scam BOOLEAN DEFAULT FALSE,
    is_fake BOOLEAN DEFAULT FALSE,
    is_restricted BOOLEAN DEFAULT FALSE,
    photo_id BIGINT,
    photo_bytes BYTEA,
    photo_mime VARCHAR,
    last_seen_at TIMESTAMPTZ,
    profile_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS participants_last_seen_idx
    ON participants (last_seen_at DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS participants_username_idx
    ON participants (username);

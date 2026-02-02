CREATE TABLE IF NOT EXISTS hashtags (
    id BIGSERIAL PRIMARY KEY,
    tag VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT hashtags_tag_format CHECK (
        tag = LOWER(tag)
        AND tag LIKE '#%'
        AND POSITION(' ' IN tag) = 0
    )
);

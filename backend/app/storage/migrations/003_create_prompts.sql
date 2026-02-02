CREATE TABLE IF NOT EXISTS analysis_prompts (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

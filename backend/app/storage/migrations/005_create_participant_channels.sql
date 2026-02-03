CREATE TABLE IF NOT EXISTS participant_channels (
    participant_id BIGINT NOT NULL REFERENCES participants(user_id) ON DELETE CASCADE,
    channel_id BIGINT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    PRIMARY KEY (participant_id, channel_id)
);

CREATE INDEX IF NOT EXISTS participant_channels_channel_idx
    ON participant_channels (channel_id);

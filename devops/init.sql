CREATE TABLE IF NOT EXISTS prediction_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    client_id INTEGER,
    features JSONB,
    probabilite_defaut FLOAT,
    risque INTEGER,
    execution_time_ms FLOAT,
    status_code INTEGER,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON prediction_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_client_id ON prediction_logs(client_id);
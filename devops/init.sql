CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prediction_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    username VARCHAR(50),
    client_id INTEGER,
    features JSONB,
    probabilite_defaut DOUBLE PRECISION,
    risque INTEGER,
    execution_time_ms DOUBLE PRECISION,
    status_code INTEGER,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON prediction_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_client_id ON prediction_logs(client_id);
CREATE INDEX IF NOT EXISTS idx_logs_username ON prediction_logs(username);
CREATE DATABASE IF NOT EXISTS mobility_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'mobility_user'@'localhost' IDENTIFIED BY '%DB_PASSWORD%';
GRANT ALL PRIVILEGES ON mobility_bot.* TO 'mobility_user'@'localhost';
FLUSH PRIVILEGES;
CREATE TABLE trend_queries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    use_case VARCHAR(255),
    sector VARCHAR(255),
    demand TEXT,
    selected_trend VARCHAR(255),
    trend_solutions TEXT,
    trend_assessment TEXT,
    radar_positioning TEXT,
    pestel_tag TEXT,
    market_solution TEXT,
    partners TEXT,
    confidence_score FLOAT,
    session_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS autonomous_learning (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trend_data TEXT,
    validation_results TEXT,
    success_metrics TEXT,
    timestamp DATETIME,
    confidence_score FLOAT
);

CREATE TABLE IF NOT EXISTS llm_assessment_trials (
        id INT AUTO_INCREMENT PRIMARY KEY,
        trial_id VARCHAR(64) UNIQUE,
        use_case VARCHAR(255),
        sector VARCHAR(255),
        demand TEXT,
        timestamp DATETIME,
        raw_output LONGTEXT,
        latency_ms FLOAT,
        token_count INT,
        api_calls INT,
        metadata JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_input (use_case, sector, demand(255))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS llm_assessment_metrics (
        id INT AUTO_INCREMENT PRIMARY KEY,
        assessment_id VARCHAR(64),
        metric_type VARCHAR(50),
        metric_name VARCHAR(100),
        metric_value FLOAT,
        details JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_assessment (assessment_id),
        INDEX idx_metric (metric_type, metric_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
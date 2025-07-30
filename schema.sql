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
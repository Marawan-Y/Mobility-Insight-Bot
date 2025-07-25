CREATE TABLE trend_queries (
  id                INT          NOT NULL AUTO_INCREMENT,
  use_case          VARCHAR(255) NULL,
  sector            VARCHAR(255) NULL,
  demand            VARCHAR(255) NULL,
  selected_trend    VARCHAR(255) NULL,
  trend_solutions   TEXT         NULL,
  trend_assessment  TEXT         NULL,
  radar_positioning TEXT         NULL,
  pestel_tag        TEXT         NULL,
  market_solution   TEXT         NULL,
  partners          TEXT         NULL,
  confidence_score  FLOAT        NULL,
  created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS autonomous_learning (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trend_data TEXT,
    validation_results TEXT,
    success_metrics TEXT,
    timestamp DATETIME,
    confidence_score FLOAT
);
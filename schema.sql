CREATE TABLE `trend_queries` (
  `id`                INT          NOT NULL AUTO_INCREMENT,
  `use_case`          VARCHAR(255) NULL,
  `sector`            VARCHAR(255) NULL,
  `demand`            VARCHAR(255) NULL,
  `selected_trend`    VARCHAR(255) NULL,
  `trend_solutions`   TEXT         NULL,
  `trend_assessment`  TEXT         NULL,
  `radar_positioning` TEXT         NULL,
  `pestel_tag`        TEXT         NULL,
  `created_at`        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

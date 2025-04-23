CREATE TABLE `trend_queries` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `use_case` VARCHAR(255),
  `sector` VARCHAR(255),
  `demand` VARCHAR(255),
  `trend_solutions` MEDIUMTEXT,
  `trend_assessment` TEXT,
  `radar_positioning` TEXT,
  `pestel_tag` TEXT,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

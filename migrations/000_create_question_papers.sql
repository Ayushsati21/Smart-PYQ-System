CREATE TABLE IF NOT EXISTS question_papers (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    pdf_filename VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL,
    pdf_relative_path VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL,
    text_file_path VARCHAR(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
    subject VARCHAR(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
    academic_year VARCHAR(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
    semester VARCHAR(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
    exam_year SMALLINT UNSIGNED DEFAULT NULL,
    term VARCHAR(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
    total_pages INT UNSIGNED NOT NULL DEFAULT 0,
    ocr_characters INT UNSIGNED NOT NULL DEFAULT 0,
    extracted_text LONGTEXT COLLATE utf8mb4_unicode_ci NOT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY pdf_relative_path (pdf_relative_path)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

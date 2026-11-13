ALTER TABLE question_papers
    ADD COLUMN paper_code VARCHAR(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL
    AFTER semester;

-- Non-destructive addition for persistent question analysis.
-- Existing question_papers rows are retained; the FK prevents paper deletion
-- while question rows refer to it.
CREATE TABLE IF NOT EXISTS questions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    paper_id BIGINT UNSIGNED NOT NULL,
    question_text LONGTEXT NOT NULL,
    normalized_question LONGTEXT NOT NULL,
    normalized_hash BINARY(32) NOT NULL,
    question_number VARCHAR(32) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_questions_paper_normalized (paper_id, normalized_hash),
    KEY ix_questions_hash (normalized_hash),
    CONSTRAINT fk_questions_paper
        FOREIGN KEY (paper_id) REFERENCES question_papers (id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

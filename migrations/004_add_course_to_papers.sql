ALTER TABLE question_papers
ADD COLUMN course VARCHAR(120) NOT NULL DEFAULT 'Unassigned' AFTER text_file_path;

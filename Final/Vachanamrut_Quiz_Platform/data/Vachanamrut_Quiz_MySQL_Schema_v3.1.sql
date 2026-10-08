-- Vachanamrut Quiz Platform v3.1 - MySQL 8 / MariaDB compatible schema
-- All application timestamps are stored as UTC ISO-8601 strings to preserve existing behaviour.

CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(180) NOT NULL,
    email VARCHAR(255) NOT NULL,
    login_id VARCHAR(100) NULL,
    password_hash VARCHAR(255) NOT NULL,
    age INT NULL,
    dob VARCHAR(40) NULL,
    city VARCHAR(180) NULL,
    gurukul_name VARCHAR(180) NULL,
    mobile VARCHAR(50) NULL,
    o_number VARCHAR(100) NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'student',
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    approval_status VARCHAR(30) NOT NULL DEFAULT 'approved',
    approval_message VARCHAR(500) NULL,
    approved_at VARCHAR(40) NULL,
    approved_by BIGINT UNSIGNED NULL,
    created_at VARCHAR(40) NOT NULL,
    last_login VARCHAR(40) NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email),
    UNIQUE KEY uq_users_login_id (login_id),
    KEY idx_users_role_status (role, status),
    KEY idx_users_approval (role, approval_status),
    CONSTRAINT fk_users_approved_by FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS subjects (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    title VARCHAR(180) NOT NULL,
    description VARCHAR(500) NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at VARCHAR(40) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_subjects_title (title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chapters (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    subject_id BIGINT UNSIGNED NULL,
    title VARCHAR(180) NOT NULL,
    chapter_number INT NULL,
    remark TEXT NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at VARCHAR(40) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_chapters_subject_title (subject_id, title),
    KEY idx_chapters_subject (subject_id),
    CONSTRAINT fk_chapters_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS course_materials (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    subject_id BIGINT UNSIGNED NULL,
    chapter_id BIGINT UNSIGNED NULL,
    title VARCHAR(255) NOT NULL,
    content LONGTEXT NOT NULL,
    source_file VARCHAR(255) NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at VARCHAR(40) NOT NULL,
    PRIMARY KEY (id),
    KEY idx_materials_subject (subject_id),
    KEY idx_materials_chapter (chapter_id),
    CONSTRAINT fk_materials_subject FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    CONSTRAINT fk_materials_chapter FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS questions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    chapter_id BIGINT UNSIGNED NOT NULL,
    question_text LONGTEXT NOT NULL,
    question_type VARCHAR(30) NOT NULL,
    question_format VARCHAR(60) NOT NULL DEFAULT 'general',
    options_json LONGTEXT NOT NULL,
    correct_answer LONGTEXT NOT NULL,
    answer_source LONGTEXT NULL,
    source_file VARCHAR(255) NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at VARCHAR(40) NOT NULL,
    PRIMARY KEY (id),
    KEY idx_questions_chapter (chapter_id),
    KEY idx_questions_type (question_type, question_format, active),
    CONSTRAINT fk_questions_chapter FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS question_bank_uploads (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    chapter_id BIGINT UNSIGNED NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    source_hash VARCHAR(128) NOT NULL,
    uploaded_by BIGINT UNSIGNED NULL,
    created_at VARCHAR(40) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_question_upload_hash (source_hash),
    KEY idx_question_upload_chapter (chapter_id),
    KEY idx_question_upload_admin (uploaded_by),
    CONSTRAINT fk_upload_chapter FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
    CONSTRAINT fk_upload_admin FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attempts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    chapter_ids_json LONGTEXT NOT NULL,
    question_ids_json LONGTEXT NOT NULL,
    mode VARCHAR(30) NOT NULL DEFAULT 'quiz',
    status VARCHAR(30) NOT NULL DEFAULT 'in_progress',
    started_at VARCHAR(40) NOT NULL,
    completed_at VARCHAR(40) NULL,
    finish_requested TINYINT(1) NOT NULL DEFAULT 0,
    question_formats_json LONGTEXT NOT NULL,
    PRIMARY KEY (id),
    KEY idx_attempts_user (user_id),
    KEY idx_attempts_user_status (user_id, status, id),
    CONSTRAINT fk_attempts_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS responses (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    attempt_id BIGINT UNSIGNED NOT NULL,
    question_id BIGINT UNSIGNED NOT NULL,
    user_answer LONGTEXT NULL,
    is_correct TINYINT(1) NULL,
    answer_viewed TINYINT(1) NOT NULL DEFAULT 0,
    completed TINYINT(1) NOT NULL DEFAULT 0,
    updated_at VARCHAR(40) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_responses_attempt_question (attempt_id, question_id),
    KEY idx_responses_attempt (attempt_id),
    KEY idx_responses_question (question_id),
    CONSTRAINT fk_responses_attempt FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE CASCADE,
    CONSTRAINT fk_responses_question FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS revision_items (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    question_id BIGINT UNSIGNED NOT NULL,
    source_attempt_id BIGINT UNSIGNED NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    wrong_count INT NOT NULL DEFAULT 1,
    last_wrong_at VARCHAR(40) NULL,
    last_reviewed_at VARCHAR(40) NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_revision_user_question (user_id, question_id),
    KEY idx_revision_user (user_id, status),
    KEY idx_revision_attempt (source_attempt_id),
    CONSTRAINT fk_revision_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_revision_question FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    CONSTRAINT fk_revision_attempt FOREIGN KEY (source_attempt_id) REFERENCES attempts(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS notifications (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    kind VARCHAR(50) NOT NULL DEFAULT 'info',
    is_read TINYINT(1) NOT NULL DEFAULT 0,
    created_at VARCHAR(40) NOT NULL,
    PRIMARY KEY (id),
    KEY idx_notifications_user (user_id, is_read, id),
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key VARCHAR(190) NOT NULL,
    setting_value LONGTEXT NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    updated_by BIGINT UNSIGNED NULL,
    PRIMARY KEY (setting_key),
    KEY idx_settings_admin (updated_by),
    CONSTRAINT fk_settings_admin FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS password_reset_otps (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    email VARCHAR(255) NOT NULL,
    otp_hash VARCHAR(128) NOT NULL,
    expires_at VARCHAR(40) NOT NULL,
    attempts INT NOT NULL DEFAULT 0,
    verified_at VARCHAR(40) NULL,
    consumed_at VARCHAR(40) NULL,
    created_at VARCHAR(40) NOT NULL,
    PRIMARY KEY (id),
    KEY idx_password_reset_otps_user (user_id, created_at),
    KEY idx_password_reset_otps_email (email),
    CONSTRAINT fk_reset_otp_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    token_hash VARCHAR(128) NOT NULL,
    expires_at VARCHAR(40) NOT NULL,
    used_at VARCHAR(40) NULL,
    created_at VARCHAR(40) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_password_reset_token_hash (token_hash),
    KEY idx_password_reset_tokens_user (user_id, created_at),
    CONSTRAINT fk_reset_token_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

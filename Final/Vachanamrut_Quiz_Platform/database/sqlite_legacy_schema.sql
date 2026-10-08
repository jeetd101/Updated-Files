-- Vachanamrut Quiz Platform v3.0
-- SQLite schema reference. The application also performs safe migrations on startup.

PRAGMA foreign_keys = ON;

CREATE TABLE attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                chapter_ids_json TEXT NOT NULL,
                question_ids_json TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'quiz' CHECK(mode IN ('quiz','revision')),
                status TEXT NOT NULL DEFAULT 'in_progress' CHECK(status IN ('in_progress','completed')),
                started_at TEXT NOT NULL,
                completed_at TEXT,
                finish_requested INTEGER NOT NULL DEFAULT 0
            , question_formats_json TEXT NOT NULL DEFAULT '[]');

CREATE TABLE chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                chapter_number INTEGER,
                remark TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                UNIQUE(subject_id, title)
            );

CREATE TABLE course_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
                chapter_id INTEGER REFERENCES chapters(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_file TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'info',
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

CREATE TABLE app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
            );

CREATE TABLE password_reset_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                email TEXT NOT NULL,
                otp_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                verified_at TEXT,
                consumed_at TEXT,
                created_at TEXT NOT NULL
            );

CREATE TABLE password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL
            );

CREATE TABLE question_bank_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
                source_file TEXT NOT NULL,
                source_hash TEXT NOT NULL UNIQUE,
                uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                created_at TEXT NOT NULL
            );

CREATE TABLE questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL CHECK(question_type IN ('objective','written')),
                question_format TEXT NOT NULL DEFAULT 'general',
                options_json TEXT NOT NULL DEFAULT '[]',
                correct_answer TEXT NOT NULL,
                answer_source TEXT,
                source_file TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

CREATE TABLE responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
                question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                user_answer TEXT,
                is_correct INTEGER,
                answer_viewed INTEGER NOT NULL DEFAULT 0,
                completed INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                UNIQUE(attempt_id, question_id)
            );

CREATE TABLE revision_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                source_attempt_id INTEGER REFERENCES attempts(id) ON DELETE SET NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','mastered')),
                wrong_count INTEGER NOT NULL DEFAULT 1,
                last_wrong_at TEXT,
                last_reviewed_at TEXT,
                UNIQUE(user_id, question_id)
            );

CREATE TABLE subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                description TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                login_id TEXT UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                age INTEGER,
                dob TEXT,
                city TEXT,
                gurukul_name TEXT,
                mobile TEXT,
                o_number TEXT,
                role TEXT NOT NULL DEFAULT 'student' CHECK(role IN ('student','admin','super_admin')),
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','inactive')),
                created_at TEXT NOT NULL,
                last_login TEXT
            , approval_status TEXT NOT NULL DEFAULT 'approved', approval_message TEXT, approved_at TEXT, approved_by INTEGER);

CREATE INDEX idx_attempts_user ON attempts(user_id);

CREATE INDEX idx_chapters_subject ON chapters(subject_id);

CREATE INDEX idx_notifications_user ON notifications(user_id,is_read);

CREATE INDEX idx_password_reset_otps_user ON password_reset_otps(user_id,created_at);

CREATE INDEX idx_password_reset_tokens_user ON password_reset_tokens(user_id,created_at);

CREATE INDEX idx_questions_chapter ON questions(chapter_id);

CREATE INDEX idx_responses_attempt ON responses(attempt_id);

CREATE INDEX idx_revision_user ON revision_items(user_id,status);

CREATE UNIQUE INDEX idx_users_login_id ON users(login_id COLLATE NOCASE);


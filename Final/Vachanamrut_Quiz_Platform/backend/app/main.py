from __future__ import annotations

import hashlib
import hmac
import json
import os
import random
import re
import secrets
import smtplib
import sqlite3
import ssl
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Literal

import jwt
from dotenv import load_dotenv
from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from fastapi import Cookie, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .database import DB_DIALECT, DBIntegrityError, add_column_if_missing, database_info, db, execute_schema_file, table_columns

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"
LOCAL_USER_DIR = FRONTEND_DIR / "local_user"
ADMIN_DIR = FRONTEND_DIR / "admin"
SUPER_ADMIN_DIR = FRONTEND_DIR / "super_admin"
DATA_DIR.mkdir(parents=True, exist_ok=True)

APP_SECRET = os.getenv("APP_SECRET", "change-this-secret-before-production")
JWT_ALGORITHM = "HS256"
TOKEN_COOKIE = "quiz_session"
TOKEN_DAYS = int(os.getenv("TOKEN_DAYS", "14") or "14")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").strip().casefold() in {"1", "true", "yes", "on"}
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").strip().casefold()
if COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    COOKIE_SAMESITE = "lax"

# Fixed single-owner identity. Only this email can authenticate through the
# Super Admin portal. The bootstrap password is applied once by v3.2 and can
# later be changed through the existing verified password-reset flow.
SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "sadhusevakdas215@sgrs.org").strip().casefold()
SUPER_ADMIN_BOOTSTRAP_PASSWORD = os.getenv("SUPER_ADMIN_BOOTSTRAP_PASSWORD", "@gurukulquiz2184")
SUPER_ADMIN_IDENTITY_MARKER = "system.super_admin_identity_v3_2"

app = FastAPI(title="Vachanamrut Quiz Platform", version="3.2.0")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

LOCAL_LOGIN_TEXT_DEFAULTS = {
    "brand_title": "Vachanamrut Quiz",
    "brand_subtitle": "Learning & Revision Platform",
    "kicker": "APPROVED QUESTION BANK ONLY",
    "hero_title": "Learn chapter by chapter. Review every mistake.",
    "hero_description": "Practice without a timer, study uploaded course material, repeat wrong answers, and track progress by chapter, subject and complete course.",
    "feature1_title": "Source controlled",
    "feature1_description": "Questions and answers only from uploaded files.",
    "feature2_title": "Personal dashboard",
    "feature2_description": "Private results, analytics and revision history.",
    "feature3_title": "Flexible learning",
    "feature3_description": "No time limit. Resume an incomplete quiz.",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_mysql_db() -> None:
    schema_path = BASE_DIR / "database" / "mysql_schema.sql"
    with db() as conn:
        execute_schema_file(conn, schema_path)

        # Keep startup idempotent and preserve all existing live data.
        conn.execute("UPDATE users SET approval_status='approved' WHERE role IN ('student','super_admin') AND (approval_status IS NULL OR approval_status='')")
        conn.execute("UPDATE users SET approval_status='approved' WHERE role='admin' AND status='active' AND (approval_status IS NULL OR approval_status='')")
        conn.execute("UPDATE users SET login_id=email WHERE login_id IS NULL OR TRIM(login_id)='' ")

        default_subject = conn.execute("SELECT id FROM subjects WHERE title=?", ("Vachanamrut",)).fetchone()
        if not default_subject:
            cursor = conn.execute(
                "INSERT INTO subjects(title,description,active,created_at) VALUES(?,?,1,?)",
                ("Vachanamrut", "Default Vachanamrut course", now_iso()),
            )
            default_subject_id = cursor.lastrowid
        else:
            default_subject_id = default_subject["id"]
        conn.execute("UPDATE chapters SET subject_id=? WHERE subject_id IS NULL", (default_subject_id,))
        for setting_key, setting_value in LOCAL_LOGIN_TEXT_DEFAULTS.items():
            conn.execute(
                "INSERT IGNORE INTO app_settings(setting_key,setting_value,updated_at,updated_by) VALUES(?,?,?,NULL)",
                (f"local_login.{setting_key}", setting_value, now_iso()),
            )

    seed_admin()


def init_db() -> None:
    if DB_DIALECT == "mysql":
        init_mysql_db()
        return
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
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
            );

            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                description TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                chapter_number INTEGER,
                remark TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                UNIQUE(subject_id, title)
            );

            CREATE TABLE IF NOT EXISTS course_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
                chapter_id INTEGER REFERENCES chapters(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_file TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS questions (
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

            CREATE TABLE IF NOT EXISTS question_bank_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
                source_file TEXT NOT NULL,
                source_hash TEXT NOT NULL UNIQUE,
                uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                chapter_ids_json TEXT NOT NULL,
                question_ids_json TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'quiz' CHECK(mode IN ('quiz','revision')),
                status TEXT NOT NULL DEFAULT 'in_progress' CHECK(status IN ('in_progress','completed')),
                started_at TEXT NOT NULL,
                completed_at TEXT,
                finish_requested INTEGER NOT NULL DEFAULT 0,
                question_formats_json TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS responses (
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

            CREATE TABLE IF NOT EXISTS revision_items (
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

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'info',
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS password_reset_otps (
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

            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id,is_read);
            CREATE INDEX IF NOT EXISTS idx_password_reset_otps_user ON password_reset_otps(user_id,created_at);
            CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user ON password_reset_tokens(user_id,created_at);
            CREATE INDEX IF NOT EXISTS idx_chapters_subject ON chapters(subject_id);
            CREATE INDEX IF NOT EXISTS idx_questions_chapter ON questions(chapter_id);
            CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts(user_id);
            CREATE INDEX IF NOT EXISTS idx_responses_attempt ON responses(attempt_id);
            CREATE INDEX IF NOT EXISTS idx_revision_user ON revision_items(user_id,status);
            """
        )

        # Safe migrations for installations created by earlier versions.
        add_column_if_missing(conn, "users", "o_number TEXT")
        add_column_if_missing(conn, "users", "approval_status TEXT NOT NULL DEFAULT 'approved'")
        add_column_if_missing(conn, "users", "approval_message TEXT")
        add_column_if_missing(conn, "users", "approved_at TEXT")
        add_column_if_missing(conn, "users", "approved_by INTEGER")
        conn.execute("UPDATE users SET approval_status='approved' WHERE role IN ('student','super_admin') AND (approval_status IS NULL OR approval_status='')")
        conn.execute("UPDATE users SET approval_status='approved' WHERE role='admin' AND status='active' AND (approval_status IS NULL OR approval_status='')")
        add_column_if_missing(conn, "users", "login_id TEXT")
        conn.execute("UPDATE users SET login_id=email WHERE login_id IS NULL OR TRIM(login_id)='' ")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_login_id ON users(login_id COLLATE NOCASE)")
        add_column_if_missing(conn, "chapters", "subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL")
        add_column_if_missing(conn, "chapters", "remark TEXT")
        add_column_if_missing(conn, "questions", "question_format TEXT NOT NULL DEFAULT 'general'")
        add_column_if_missing(conn, "questions", "active INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(conn, "attempts", "mode TEXT NOT NULL DEFAULT 'quiz'")
        add_column_if_missing(conn, "attempts", "finish_requested INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "attempts", "question_formats_json TEXT NOT NULL DEFAULT '[]'")

        default_subject = conn.execute("SELECT id FROM subjects WHERE title=?", ("Vachanamrut",)).fetchone()
        if not default_subject:
            cursor = conn.execute(
                "INSERT INTO subjects(title,description,active,created_at) VALUES(?,?,1,?)",
                ("Vachanamrut", "Default Vachanamrut course", now_iso()),
            )
            default_subject_id = cursor.lastrowid
        else:
            default_subject_id = default_subject["id"]
        conn.execute("UPDATE chapters SET subject_id=? WHERE subject_id IS NULL", (default_subject_id,))
        for setting_key, setting_value in LOCAL_LOGIN_TEXT_DEFAULTS.items():
            conn.execute(
                "INSERT OR IGNORE INTO app_settings(setting_key,setting_value,updated_at,updated_by) VALUES(?,?,?,NULL)",
                (f"local_login.{setting_key}", setting_value, now_iso()),
            )

    seed_admin()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        method, salt_hex, digest_hex = stored.split("$", 2)
        if method != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=64
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _otp_hash(user_id: int, email: str, code: str) -> str:
    payload = f"{user_id}:{email.casefold()}:{code}".encode("utf-8")
    return hmac.new(APP_SECRET.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _reset_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _send_super_admin_reset_email(email: str, code: str) -> str:
    """Send the 4-digit reset code using SMTP.

    For a local installation where SMTP has not yet been configured, the same
    email is written to data/mail_outbox so the password-reset workflow can be
    tested without changing application logic. Production deployments should
    configure SMTP_* variables and MAIL_DELIVERY_MODE=smtp.
    """
    mode = os.getenv("MAIL_DELIVERY_MODE", "auto").strip().casefold()
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587") or "587")
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    from_email = os.getenv("SMTP_FROM_EMAIL", username or "no-reply@localhost").strip()
    from_name = os.getenv("SMTP_FROM_NAME", "Vachanamrut Quiz").strip() or "Vachanamrut Quiz"
    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().casefold() in {"1", "true", "yes", "on"}
    use_ssl = os.getenv("SMTP_USE_SSL", "false").strip().casefold() in {"1", "true", "yes", "on"}

    message = EmailMessage()
    message["Subject"] = "Super Admin password reset code"
    message["From"] = f"{from_name} <{from_email}>"
    message["To"] = email
    message.set_content(
        "Your Vachanamrut Quiz Super Admin password reset code is " + code +
        ".\n\nThis 4-digit code expires in 10 minutes. If you did not request a password reset, ignore this email."
    )

    if mode == "file" or (mode == "auto" and not host):
        outbox = DATA_DIR / "mail_outbox"
        outbox.mkdir(parents=True, exist_ok=True)
        stamp = _utc_now().strftime("%Y%m%d_%H%M%S_%f")
        safe_email = re.sub(r"[^a-zA-Z0-9_.-]+", "_", email)
        (outbox / f"{stamp}_{safe_email}.eml").write_bytes(message.as_bytes())
        return "local_outbox"

    if not host:
        raise RuntimeError("SMTP_HOST is not configured.")

    if use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as server:
            if username:
                server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            if use_tls:
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
            if username:
                server.login(username, password)
            server.send_message(message)
    return "smtp"


def seed_admin() -> None:
    """Ensure exactly one fixed Super Admin identity.

    v3.2 locks Super Admin authentication to SUPER_ADMIN_EMAIL. On the first
    v3.2 startup, that account is created/promoted and given the configured
    bootstrap password. A marker then prevents later restarts from overwriting
    a password changed through the existing OTP reset flow.
    """
    with db() as conn:
        marker = conn.execute(
            "SELECT setting_value FROM app_settings WHERE setting_key=?",
            (SUPER_ADMIN_IDENTITY_MARKER,),
        ).fetchone()
        apply_bootstrap = not marker or str(marker["setting_value"] or "").casefold() != SUPER_ADMIN_EMAIL

        target = conn.execute(
            "SELECT * FROM users WHERE email=? COLLATE NOCASE ORDER BY id LIMIT 1",
            (SUPER_ADMIN_EMAIL,),
        ).fetchone()

        if target:
            if apply_bootstrap:
                conn.execute(
                    """UPDATE users SET role='super_admin', status='active', approval_status='approved',
                       approval_message=NULL, password_hash=? WHERE id=?""",
                    (hash_password(SUPER_ADMIN_BOOTSTRAP_PASSWORD), target["id"]),
                )
            else:
                conn.execute(
                    """UPDATE users SET role='super_admin', status='active', approval_status='approved',
                       approval_message=NULL WHERE id=?""",
                    (target["id"],),
                )
            owner_id = target["id"]
        else:
            login_id = SUPER_ADMIN_EMAIL.split("@", 1)[0]
            base_login_id = login_id
            suffix = 1
            while conn.execute("SELECT id FROM users WHERE login_id=? COLLATE NOCASE", (login_id,)).fetchone():
                suffix += 1
                login_id = f"{base_login_id}{suffix}"
            cursor = conn.execute(
                """INSERT INTO users(name,email,login_id,password_hash,role,status,approval_status,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (
                    "Super Administrator",
                    SUPER_ADMIN_EMAIL,
                    login_id,
                    hash_password(SUPER_ADMIN_BOOTSTRAP_PASSWORD),
                    "super_admin",
                    "active",
                    "approved",
                    now_iso(),
                ),
            )
            owner_id = cursor.lastrowid

        # No other account is allowed to retain the Super Admin role.
        conn.execute(
            "UPDATE users SET role='admin', approval_status='approved' WHERE role='super_admin' AND id<>?",
            (owner_id,),
        )

        if marker:
            conn.execute(
                "UPDATE app_settings SET setting_value=?,updated_at=?,updated_by=? WHERE setting_key=?",
                (SUPER_ADMIN_EMAIL, now_iso(), owner_id, SUPER_ADMIN_IDENTITY_MARKER),
            )
        else:
            conn.execute(
                "INSERT INTO app_settings(setting_key,setting_value,updated_at,updated_by) VALUES(?,?,?,?)",
                (SUPER_ADMIN_IDENTITY_MARKER, SUPER_ADMIN_EMAIL, now_iso(), owner_id),
            )


def issue_token(user: sqlite3.Row) -> str:
    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS),
    }
    return jwt.encode(payload, APP_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str | None) -> dict[str, Any]:
    if not token:
        raise HTTPException(status_code=401, detail="Please sign in.")
    try:
        return jwt.decode(token, APP_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.") from exc


def get_current_user(quiz_session: str | None = Cookie(default=None, alias=TOKEN_COOKIE)) -> sqlite3.Row:
    payload = decode_token(quiz_session)
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (int(payload["sub"]),)).fetchone()
    if not user or user["status"] != "active":
        raise HTTPException(status_code=401, detail="Account is inactive or unavailable.")
    return user


def require_admin(user: sqlite3.Row = Depends(get_current_user)) -> sqlite3.Row:
    if user["role"] not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


def require_super_admin(user: sqlite3.Row = Depends(get_current_user)) -> sqlite3.Row:
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required.")
    return user


def public_user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "login_id": row["login_id"] if "login_id" in row.keys() else row["email"],
        "age": row["age"],
        "dob": row["dob"],
        "city": row["city"],
        "gurukul_name": row["gurukul_name"],
        "mobile": row["mobile"],
        "o_number": row["o_number"] if "o_number" in row.keys() else None,
        "role": row["role"],
        "status": row["status"],
        "approval_status": row["approval_status"] if "approval_status" in row.keys() else "approved",
        "approval_message": row["approval_message"] if "approval_message" in row.keys() else None,
        "approved_at": row["approved_at"] if "approved_at" in row.keys() else None,
        "created_at": row["created_at"],
        "last_login": row["last_login"],
    }


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("।", ".")
    value = re.sub(r"\s+", " ", value).strip().casefold()
    return value


def parse_options(raw_options: list[Any]) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    for index, item in enumerate(raw_options):
        if isinstance(item, dict):
            key = str(item.get("key") or chr(65 + index)).strip().upper()
            text = str(item.get("text") or "").strip()
        else:
            key = chr(65 + index)
            text = str(item).strip()
        if text:
            options.append({"key": key, "text": text})
    return options


def answer_tokens(answer: str) -> list[str]:
    return [token.strip() for token in re.split(r"[,;/|+]+", answer) if token.strip()]


def resolve_answer_display(question: sqlite3.Row) -> tuple[list[str], str]:
    answer = question["correct_answer"].strip()
    options = parse_options(json.loads(question["options_json"] or "[]"))
    if question["question_format"] == "multiple_select":
        keys: list[str] = []
        texts: list[str] = []
        for token in answer_tokens(answer):
            normalized = normalize_text(token)
            matched = next(
                (
                    option
                    for option in options
                    if normalized in {normalize_text(option["key"]), normalize_text(option["text"]), normalize_text(f"{option['key']}. {option['text']}")}
                ),
                None,
            )
            if matched:
                keys.append(matched["key"])
                texts.append(matched["text"])
            else:
                keys.append(token)
                texts.append(token)
        return keys, ", ".join(texts)

    normalized_answer = normalize_text(answer)
    for option in options:
        if normalized_answer in {
            normalize_text(option["key"]),
            normalize_text(option["text"]),
            normalize_text(f"{option['key']}. {option['text']}"),
        }:
            return [option["key"]], option["text"]
    return [answer], answer


def objective_is_correct(question: sqlite3.Row, user_answer: str) -> bool:
    correct_keys, correct_text = resolve_answer_display(question)
    if question["question_format"] == "multiple_select":
        user_tokens = {normalize_text(token) for token in answer_tokens(user_answer)}
        correct_key_tokens = {normalize_text(token) for token in correct_keys}
        # Also allow exact option text combinations.
        if user_tokens == correct_key_tokens:
            return True
        correct_text_tokens = {normalize_text(token) for token in answer_tokens(correct_text)}
        return user_tokens == correct_text_tokens
    user = normalize_text(user_answer)
    return user in {normalize_text(correct_keys[0]), normalize_text(correct_text)}


def compact_answer(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = value.casefold().strip()
    value = re.sub(r"[\s\u200b\u200c\u200d]+", " ", value)
    value = re.sub(r"[.,;:!?।\-–—()\[\]{}\"'`]+", "", value)
    return re.sub(r"\s+", " ", value).strip()


def bilingual_word_tokens(value: str | None) -> list[str]:
    """Tokenize Gujarati or English safely, preserving Unicode combining marks."""
    normalized = unicodedata.normalize("NFKC", value or "").casefold()
    chars: list[str] = []
    for char in normalized:
        category = unicodedata.category(char)
        if category and category[0] in {"L", "M", "N"}:
            chars.append(char)
        else:
            chars.append(" ")
    return [token for token in "".join(chars).split() if token]


def written_match_percentage(question: sqlite3.Row, user_answer: str) -> float:
    user_compact = compact_answer(user_answer)
    correct_compact = compact_answer(question["correct_answer"] or "")
    if not user_compact or not correct_compact:
        return 0.0
    if user_compact == correct_compact:
        return 100.0

    # Identify-chapter remains tolerant of a small label/prefix around the chapter name.
    if question["question_format"] == "identify_chapter" and (user_compact in correct_compact or correct_compact in user_compact):
        return 100.0

    user_words = bilingual_word_tokens(user_answer)
    correct_words = bilingual_word_tokens(question["correct_answer"] or "")
    if not user_words or not correct_words:
        return 0.0

    # For very short answers, avoid false positives from one common word.
    if len(correct_words) <= 2:
        return 100.0 if user_words == correct_words else 0.0

    user_counts = Counter(user_words)
    correct_counts = Counter(correct_words)
    matched = sum(min(user_counts[word], count) for word, count in correct_counts.items())
    return round((matched / len(correct_words)) * 100, 1)


def written_is_correct(question: sqlite3.Row, user_answer: str) -> bool:
    # Gujarati and English Unicode text are both supported. A written answer is accepted
    # when at least 70% of the words from the approved question-bank answer are present.
    return written_match_percentage(question, user_answer) >= 70.0


def _strip_item_prefix(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^\s*(?:[0-9૦-૯]+|[A-Za-z])\s*[.)\-:–—]\s*", "", value)
    return value.strip()


def _sequence_source_entries(question_text: str) -> list[tuple[str, str]]:
    lines = [line.strip() for line in (question_text or "").splitlines() if line.strip()]
    entries: list[tuple[str, str]] = []
    for line in lines:
        pipe_parts = [part.strip() for part in line.split("|")]
        if len(pipe_parts) >= 2 and re.fullmatch(r"[0-9૦-૯A-Za-z]+", pipe_parts[0]):
            entries.append((pipe_parts[0].strip().lower(), pipe_parts[1].strip()))
            continue
        match = re.match(r"^\s*[•·▪◦-]?\s*\(?([0-9૦-૯]+|[A-Za-z])\)?\s*[.)\-:–—]\s*(.+)$", line)
        if match:
            entries.append((match.group(1).strip().lower(), match.group(2).strip()))
    if len(entries) >= 2:
        return entries
    generic = [line for line in lines if "arrange" not in line.casefold() and "sequence" not in line.casefold() and "ક્રમ" not in line]
    return [(str(i + 1), value) for i, value in enumerate(generic)] if len(generic) >= 2 else [(str(i + 1), value) for i, value in enumerate(lines)]


def _sequence_source_items(question_text: str) -> list[str]:
    return [text for _, text in _sequence_source_entries(question_text)]


def _expected_sequence(question: sqlite3.Row) -> list[str]:
    answer = (question["correct_answer"] or "").strip()
    entries = _sequence_source_entries(question["question_text"] or "")
    source = [text for _, text in entries]
    if not source:
        return [answer] if answer else []

    # Support answer keys such as a → b → c → d or 1 → 3 → 2.
    tokens = [token.strip().lower() for token in re.split(r"\s*(?:→|->|=>|,|;|\n)\s*", answer) if token.strip()]
    key_map = {key.lower(): text for key, text in entries}
    if len(tokens) >= 2 and all(token in key_map for token in tokens):
        mapped = [key_map[token] for token in tokens]
        if len(mapped) == len(source):
            return mapped

    numeric_tokens = re.findall(r"(?<!\w)([0-9]+)(?!\w)", answer)
    if len(numeric_tokens) >= len(source):
        order = []
        for token in numeric_tokens[: len(source)]:
            idx = int(token) - 1
            if 0 <= idx < len(source):
                order.append(source[idx])
        if len(order) == len(source):
            return order

    parts = [part.strip() for part in re.split(r"\n|→|->|=>|\s*,\s*|\s*;\s*", answer) if part.strip()]
    cleaned = [_strip_item_prefix(part) for part in parts]
    return cleaned if len(cleaned) >= 2 else [answer]


def _match_rows(question_text: str) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for line in [line.strip() for line in (question_text or "").splitlines() if line.strip()]:
        # DOCX tables are stored as pipe-separated rows. Pasted tables may use tabs.
        if "|" in line:
            parts = [part.strip() for part in line.split("|") if part.strip()]
        elif "\t" in line:
            parts = [part.strip() for part in line.split("\t") if part.strip()]
        else:
            parts = []
        if len(parts) < 2:
            continue
        header_text = normalize_text(" ".join(parts[:2])).casefold()
        if any(token in header_text for token in ("ભાગ a", "ભાગ b", "part a", "part b", "column a", "column b")):
            continue
        left, right = parts[0], parts[1]
        lmatch = re.match(r"^\s*([0-9૦-૯]+)\s*[.)\-:–—]?\s*(.*)$", left)
        rmatch = re.match(r"^\s*([A-Za-z])\s*[.)\-:–—]?\s*(.*)$", right)
        index = len(rows)
        left_key = lmatch.group(1) if lmatch else str(index + 1)
        left_text = (lmatch.group(2) if lmatch else left).strip()
        right_key = rmatch.group(1).upper() if rmatch else chr(65 + index)
        right_text = (rmatch.group(2) if rmatch else right).strip()
        if left_text and right_text:
            rows.append((left_key, left_text, right_key, right_text))
    return rows

def structured_is_correct(question: sqlite3.Row, user_answer: str) -> bool:
    try:
        selected = json.loads(user_answer)
    except Exception:
        selected = None
    if question["question_format"] == "sequence":
        if not isinstance(selected, list):
            return False
        expected = _expected_sequence(question)
        return [compact_answer(str(v)) for v in selected] == [compact_answer(v) for v in expected]
    if question["question_format"] == "match":
        if not isinstance(selected, list):
            return False
        # Submitted values are right-column letter keys aligned to left-column rows.
        answer = question["correct_answer"] or ""
        pairs = re.findall(r"(?:^|[,;\n\s])([0-9૦-૯]+)\s*[-:=→]\s*([A-Za-z])", answer)
        if pairs:
            expected_map = {left: right.upper() for left, right in pairs}
            rows = _match_rows(question["question_text"] or "")
            if rows:
                expected = [expected_map.get(left, "") for left, _, _, _ in rows]
                return [str(v).strip().upper() for v in selected] == expected
        # If the uploaded Word table itself contains the correct Part A / Part B pairing,
        # the original right-column row order is the answer key. No external answer is invented.
        rows = _match_rows(question["question_text"] or "")
        if rows:
            expected = [right_key for _, _, right_key, _ in rows]
            return [str(v).strip().upper() for v in selected] == expected
        return compact_answer(" ".join(str(v) for v in selected)) == compact_answer(answer)
    return False


QUIZ_SECTION_TITLES: dict[str, str] = {
    "multiple choice questions": "mcq",
    "mcq": "mcq",
    "multiple select questions": "multiple_select",
    "multiple answer questions": "multiple_select",
    "fill in the blanks": "fill_blank",
    "true or false": "true_false",
    "one-word answer questions": "one_word",
    "one word answer questions": "one_word",
    "very short answer questions": "very_short",
    "short answer questions": "short_answer",
    "who said that? — કોણે કહ્યું?": "who_said",
    "who said that?": "who_said",
    "કોણે કહ્યું?": "who_said",
    "match the following": "match",
    "arrange in correct sequence": "sequence",
    "નીચેના સંકેતો પરથી પ્રકરણ ઓળખો.": "identify_chapter",
    "નીચેના સંકેતો પરથી પ્રકરણ ઓળખો": "identify_chapter",
    "rapid fire questions": "rapid_fire",
}

NON_QUIZ_SECTION_TITLES = {
    "chapter master information",
    "chapter memory formula",
    "paragraph-wise breakdown",
    "ખૂબ મહત્ત્વના યાદ રાખવાના મુદ્દા",
    "key points to remember",
}

SECTION_HEADING_RE = re.compile(r"^\s*(\d+|[૦-૯]+)\s*[\).:\-–—]\s*(.+?)\s*$", re.IGNORECASE)
NUMBERED_QUESTION_RE = re.compile(r"^\s*(\d+|[૦-૯]+)\s*[\).:\-–—]\s*(.+?)\s*$")
MCQ_MARKER_RE = re.compile(r"^\s*MCQ\s*(\d+|[૦-૯]+)\s*[\).:\-–—]?\s*(.*)$", re.IGNORECASE)
NAMED_QUESTION_RE = re.compile(r"^\s*(?:question|q|પ્રશ્ન)\s*(\d+|[૦-૯]+)?\s*[\).:\-–—]?\s*(.*)$", re.IGNORECASE)
CLUE_MARKER_RE = re.compile(r"^\s*સંકેત\s*(\d+|[૦-૯]+)\s*[\).:\-–—]?\s*(.*)$")
SEQUENCE_MARKER_RE = re.compile(r"^\s*Sequence\s*(\d+|[૦-૯]+)\s*[\).:\-–—]?\s*(.*)$", re.IGNORECASE)
STANDALONE_NUMBER_RE = re.compile(r"^\s*(\d+|[૦-૯]+)\s*[\).:\-–—]?\s*$")
SEQUENCE_ITEM_RE = re.compile(r"^\s*[•·▪◦-]?\s*\(?([A-Za-z])\)?\s*[\).:\-–—]\s*(.+)$")
STRUCTURED_ANSWER_RE = re.compile(r"^\s*(?:જવાબ|answer)\s*\([^)]*(?:સાચો\s*ક્રમ|ક્રમ|correct\s*sequence|matching|જોડણી)[^)]*\)\s*[.:：\-–—]*\s*(.*)$", re.IGNORECASE)
ANSWER_RE = re.compile(
    r"^\s*(?:ans(?:wer)?|correct\s*answer|correct\s*option|model\s*answer|મોડેલ\s*જવાબ|જવાબ|ઉત્તર|સાચો\s*જવાબ)\s*[.:：\-–—]*\s*(.*)$",
    re.IGNORECASE,
)
OPTION_RE = re.compile(r"^\s*\(?([A-Ha-h])\)?\s*[\).:\-–—]\s*(.+)$")
INLINE_ANSWER_RE = re.compile(
    r"\s+(?:ans(?:wer)?|correct\s*answer|correct\s*option|model\s*answer|મોડેલ\s*જવાબ|જવાબ|ઉત્તર|સાચો\s*જવાબ)\s*[.:：\-–—]+\s*",
    re.IGNORECASE,
)
SEPARATOR_RE = re.compile(r"^[\s\-—–_=]+$")


def canonical_heading(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[*#]+", "", value)
    return re.sub(r"\s+", " ", value).strip().casefold()


def detect_section(line: str) -> str | None:
    match = SECTION_HEADING_RE.match(line)
    title = match.group(2) if match else line
    normalized = canonical_heading(title)
    if normalized in QUIZ_SECTION_TITLES:
        return QUIZ_SECTION_TITLES[normalized]
    if normalized in NON_QUIZ_SECTION_TITLES:
        return "ignore"
    return None


def clean_answer_for_objective(answer: str, options: list[dict[str, str]], question_format: str) -> str:
    answer = answer.strip()
    if not answer:
        return ""
    if question_format == "multiple_select":
        cleaned: list[str] = []
        for token in answer_tokens(answer):
            match = re.match(r"^\(?([A-Ha-h])\)?(?:\s*[\).:\-–—]\s*.*)?$", token)
            cleaned.append(match.group(1).upper() if match else token)
        return ",".join(cleaned)
    match = re.match(r"^\(?([A-Ha-h])\)?(?:\s*[\).:\-–—]\s*.*)?$", answer)
    if match and options:
        return match.group(1).upper()
    return answer


def _iter_docx_blocks(parent: DocxDocument):
    """Yield paragraphs and tables in their real document order."""
    parent_elm = parent.element.body
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def document_lines(file_path: Path) -> list[dict[str, Any]]:
    doc = Document(file_path)
    lines: list[dict[str, Any]] = []
    for block in _iter_docx_blocks(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
            bold_text = " ".join(run.text.strip() for run in block.runs if run.bold and run.text.strip())
            lines.append({"text": text, "bold_text": bold_text})
            continue
        if isinstance(block, Table):
            for row in block.rows:
                cell_values: list[str] = []
                for cell in row.cells:
                    value = " ".join(p.text.strip() for p in cell.paragraphs if p.text.strip()).strip()
                    cell_values.append(value)
                if any(cell_values):
                    # Preserve blank cells so column positions are not shifted.
                    lines.append({"text": " | ".join(cell_values), "bold_text": ""})
    return lines

def text_lines(text: str) -> list[dict[str, Any]]:
    return [{"text": line.strip(), "bold_text": ""} for line in text.splitlines() if line.strip()]


def extract_document_text(file_path: Path) -> str:
    return "\n\n".join(entry["text"] for entry in document_lines(file_path))


def parse_question_bank(lines: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    questions: list[dict[str, Any]] = []
    warnings: list[str] = []
    current_section: str | None = None
    current: dict[str, Any] | None = None
    collecting_answer = False
    rapid_stage: str | None = None

    def new_question(initial_text: str = "", *, section: str | None = None) -> dict[str, Any]:
        return {
            "question_parts": [initial_text.strip()] if initial_text.strip() else [],
            "options": [],
            "answer_parts": [],
            "answer_source_parts": [],
            "section": section or current_section or "general",
        }

    def finish_current() -> None:
        nonlocal current, collecting_answer, rapid_stage
        if not current:
            return
        question_text = "\n".join(part.strip() for part in current["question_parts"] if part.strip()).strip()
        answer_text = "\n".join(part.strip() for part in current["answer_parts"] if part.strip()).strip()
        options = parse_options(current["options"])
        section = current.get("section") or current_section or "general"
        if section == "true_false" and not options:
            options = [{"key": "A", "text": "સાચું"}, {"key": "B", "text": "ખોટું"}]
        question_type = "objective" if options else "written"
        if question_type == "objective":
            answer_text = clean_answer_for_objective(answer_text, options, section)
        if section == "match" and not answer_text and question_text:
            table_rows = _match_rows(question_text)
            if len(table_rows) >= 2:
                answer_text = ", ".join(f"{left}-{right}" for left, _, right, _ in table_rows)
                current["answer_source_parts"].append("Correct pairing detected from uploaded Part A / Part B table row alignment.")
        if question_text:
            status = "detected" if answer_text else "needs_review"
            if not answer_text:
                warnings.append(f"Answer not detected for: {question_text[:100]}")
            questions.append(
                {
                    "question_text": question_text,
                    "question_type": question_type,
                    "question_format": section,
                    "options": options,
                    "correct_answer": answer_text,
                    "answer_source": "\n".join(current.get("answer_source_parts", [])).strip(),
                    "status": status,
                    "section": section,
                }
            )
        current = None
        collecting_answer = False
        rapid_stage = None

    for entry in lines:
        line = str(entry.get("text") or "").strip()
        bold_text = str(entry.get("bold_text") or "").strip()
        if not line or SEPARATOR_RE.match(line):
            continue

        section = detect_section(line)
        if section is not None:
            finish_current()
            current_section = section
            if section == "match":
                current = new_question("Match the following items.", section=section)
            continue
        if current_section == "ignore":
            continue

        inline_parts = INLINE_ANSWER_RE.split(line, maxsplit=1)
        if len(inline_parts) == 2 and current is None:
            left, answer = inline_parts
            q_match = NUMBERED_QUESTION_RE.match(left) or NAMED_QUESTION_RE.match(left)
            if q_match:
                question_text = q_match.group(q_match.lastindex or 1).strip()
                if q_match.re is NAMED_QUESTION_RE and q_match.lastindex == 2:
                    question_text = q_match.group(2).strip()
                current = new_question(question_text)
                current["answer_parts"].append(answer.strip())
                current["answer_source_parts"].append(line)
                finish_current()
                continue

        structured_answer_match = STRUCTURED_ANSWER_RE.match(line)
        if structured_answer_match and current:
            collecting_answer = True
            answer = structured_answer_match.group(1).strip()
            current["answer_source_parts"].append(line)
            if answer:
                current["answer_parts"].append(answer)
            continue

        answer_match = ANSWER_RE.match(line)
        if answer_match and current:
            collecting_answer = True
            answer = answer_match.group(1).strip()
            current["answer_source_parts"].append(line)
            if answer:
                current["answer_parts"].append(answer)
            continue

        if current and collecting_answer and re.match(r"^\s*(?:સુધારો|correction)\s*[:：\-–—]", line, re.IGNORECASE):
            current["answer_source_parts"].append(line)
            continue
        if current and collecting_answer and re.match(r"^\s*કોને\s*કહ્યું\s*[:：\-–—]", line):
            current["answer_source_parts"].append(line)
            current["answer_parts"].append(line)
            continue

        if current_section == "match" and canonical_heading(line) in {"સાચી જોડણી", "correct matching", "answers"}:
            collecting_answer = True
            current["answer_source_parts"].append(line)
            continue
        if current_section == "sequence" and canonical_heading(line) in {"સાચો ક્રમ", "correct sequence"}:
            collecting_answer = True
            if current:
                current["answer_source_parts"].append(line)
            continue

        # Sequence sections commonly use a bare question number followed by (a), (b), (c) items.
        if current_section == "sequence":
            bare_number = STANDALONE_NUMBER_RE.match(line)
            if bare_number:
                finish_current()
                current = new_question("", section="sequence")
                continue
            seq_item = SEQUENCE_ITEM_RE.match(line)
            if seq_item and current is not None and not collecting_answer:
                current["question_parts"].append(f"{seq_item.group(1).lower()}. {seq_item.group(2).strip()}")
                continue

        marker_match = MCQ_MARKER_RE.match(line)
        if marker_match:
            finish_current()
            current_section = current_section or "mcq"
            current = new_question(marker_match.group(2), section=current_section if current_section == "multiple_select" else "mcq")
            continue
        marker_match = SEQUENCE_MARKER_RE.match(line)
        if marker_match:
            finish_current()
            current_section = "sequence"
            initial = marker_match.group(2).strip()
            current = new_question(initial or "Arrange the following items in the correct sequence.", section="sequence")
            continue
        marker_match = CLUE_MARKER_RE.match(line)
        if marker_match:
            finish_current()
            current_section = current_section or "identify_chapter"
            current = new_question(marker_match.group(2), section="identify_chapter")
            continue
        marker_match = NAMED_QUESTION_RE.match(line)
        if marker_match and (marker_match.group(1) or marker_match.group(2)):
            if marker_match.group(1) or current_section in {"very_short", "short_answer", "who_said"}:
                finish_current()
                current = new_question(marker_match.group(2), section=current_section)
                continue

        numbered_match = NUMBERED_QUESTION_RE.match(line)
        if numbered_match:
            if current and collecting_answer and current_section in {"sequence", "match"}:
                current["answer_parts"].append(line)
                current["answer_source_parts"].append(line)
                continue
            if current_section == "match" and current:
                current["question_parts"].append(line)
                continue
            finish_current()
            current = new_question(numbered_match.group(2), section=current_section)
            if current_section == "rapid_fire":
                rapid_stage = "awaiting_answer"
            continue

        if not current:
            if current_section in {
                "mcq", "multiple_select", "fill_blank", "true_false", "one_word", "very_short",
                "short_answer", "who_said", "identify_chapter", "rapid_fire",
            }:
                current = new_question(line, section=current_section)
                if current_section == "rapid_fire":
                    rapid_stage = "awaiting_answer"
            continue

        option_match = OPTION_RE.match(line)
        if option_match and not collecting_answer:
            option = {"key": option_match.group(1).upper(), "text": option_match.group(2).strip()}
            current["options"].append(option)
            if "✓" in line or (bold_text and normalize_text(bold_text) == normalize_text(line)):
                if current.get("section") == "multiple_select" and current["answer_parts"]:
                    current["answer_parts"].append(option["key"])
                else:
                    current["answer_parts"] = [option["key"]]
                current["answer_source_parts"].append(f"Marked option: {line}")
            continue

        if current_section == "rapid_fire" and rapid_stage == "awaiting_answer" and current["question_parts"]:
            current["answer_parts"].append(line)
            current["answer_source_parts"].append(line)
            finish_current()
            continue
        if collecting_answer:
            current["answer_parts"].append(line)
            current["answer_source_parts"].append(line)
        else:
            current["question_parts"].append(line)

    finish_current()
    if not questions:
        warnings.append("No questions were detected. Use a numbered question and an answer label such as જવાબ: or ANS:.")
    return questions, warnings


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    login_id: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=5, max_length=200)
    account_type: Literal["local_user", "admin"] = "local_user"
    age: int | None = Field(default=None, ge=5, le=100)
    dob: str | None = None
    city: str | None = Field(default=None, max_length=100)
    gurukul_name: str | None = Field(default=None, max_length=150)
    mobile: str | None = Field(default=None, max_length=30)
    o_number: str | None = Field(default=None, max_length=50)


class LoginInput(BaseModel):
    identifier: str | None = None
    email: str | None = None
    password: str


class ForgotPasswordInput(BaseModel):
    identifier: str = Field(min_length=3, max_length=200)
    email: str = Field(min_length=5, max_length=200)
    verification: str | None = Field(default=None, max_length=100)
    new_password: str = Field(min_length=5, max_length=200)


class SuperAdminOtpRequestInput(BaseModel):
    email: str = Field(min_length=5, max_length=200)


class SuperAdminOtpVerifyInput(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    code: str = Field(min_length=4, max_length=4)


class SuperAdminPasswordCompleteInput(BaseModel):
    reset_token: str = Field(min_length=20, max_length=500)
    new_password: str = Field(min_length=5, max_length=200)


def normalize_login_id(value: str) -> str:
    value = value.strip().casefold()
    if not re.fullmatch(r"[a-z0-9._-]{3,50}", value):
        raise HTTPException(
            status_code=422,
            detail="User Name must be 3-50 characters.",
        )
    return value


def login_identifier(payload: LoginInput) -> str:
    value = (payload.identifier or payload.email or "").strip().casefold()
    if not value:
        raise HTTPException(status_code=422, detail="Enter your Login ID or email address.")
    return value


def normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    raw = value.strip()
    prefix = "+" if raw.startswith("+") else ""
    digits = re.sub(r"\D", "", raw)
    return prefix + digits if digits else ""


def find_user_by_identifier(conn: sqlite3.Connection, identifier: str) -> sqlite3.Row | None:
    row = conn.execute(
        "SELECT * FROM users WHERE login_id = ? COLLATE NOCASE OR email = ? COLLATE NOCASE",
        (identifier, identifier),
    ).fetchone()
    if row:
        return row
    wanted_phone = normalize_phone(identifier)
    if wanted_phone and len(re.sub(r"\D", "", wanted_phone)) >= 7:
        wanted_digits = re.sub(r"\D", "", wanted_phone)
        for candidate in conn.execute("SELECT * FROM users WHERE mobile IS NOT NULL AND TRIM(mobile)<>''").fetchall():
            candidate_phone = normalize_phone(candidate["mobile"])
            candidate_digits = re.sub(r"\D", "", candidate_phone)
            if candidate_phone == wanted_phone or (len(wanted_digits) >= 10 and len(candidate_digits) >= 10 and candidate_digits[-10:] == wanted_digits[-10:]):
                return candidate
    return None


def complete_login(user: sqlite3.Row, response: Response) -> dict[str, Any]:
    token = issue_token(user)
    response.set_cookie(
        TOKEN_COOKIE, token, httponly=True, samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE,
        max_age=TOKEN_DAYS * 86400, expires=TOKEN_DAYS * 86400, path="/"
    )
    return {
        "user": public_user(user),
        "redirect": "/dashboard" if user["role"] == "student" else ("/super-admin" if user["role"] == "super_admin" else "/admin"),
    }


class SubjectInput(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=500)


class ChapterInput(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    chapter_number: int | None = Field(default=None, ge=1)
    subject_id: int


class SubjectUpdateInput(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=500)


class ChapterUpdateInput(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    chapter_number: int | None = Field(default=None, ge=1)
    subject_id: int
    remark: str | None = Field(default=None, max_length=2000)


class RemarkInput(BaseModel):
    remark: str = Field(default="", max_length=2000)


class LocalLoginTextInput(BaseModel):
    brand_title: str = Field(min_length=1, max_length=120)
    brand_subtitle: str = Field(min_length=1, max_length=180)
    kicker: str = Field(min_length=1, max_length=120)
    hero_title: str = Field(min_length=1, max_length=240)
    hero_description: str = Field(min_length=1, max_length=800)
    feature1_title: str = Field(min_length=1, max_length=120)
    feature1_description: str = Field(min_length=1, max_length=300)
    feature2_title: str = Field(min_length=1, max_length=120)
    feature2_description: str = Field(min_length=1, max_length=300)
    feature3_title: str = Field(min_length=1, max_length=120)
    feature3_description: str = Field(min_length=1, max_length=300)


class QuestionUpdateInput(BaseModel):
    question_text: str = Field(min_length=1)
    correct_answer: str = Field(min_length=1)
    options: list[dict[str, Any]] = []


class StudentUpdateInput(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    email: str = Field(min_length=3, max_length=255)
    login_id: str = Field(min_length=3, max_length=50)
    age: int | None = Field(default=None, ge=1, le=120)
    dob: str | None = None
    city: str | None = Field(default=None, max_length=180)
    gurukul_name: str | None = Field(default=None, max_length=180)
    mobile: str | None = Field(default=None, max_length=50)
    o_number: str | None = Field(default=None, max_length=100)
    status: Literal["active", "inactive"] = "active"
    new_password: str | None = Field(default=None, min_length=5, max_length=128)


class AdminUpdateInput(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    email: str = Field(min_length=3, max_length=255)
    login_id: str = Field(min_length=3, max_length=50)
    status: Literal["active", "inactive"] = "active"
    new_password: str | None = Field(default=None, min_length=5, max_length=128)


class AdminApprovalInput(BaseModel):
    message: str | None = Field(default=None, max_length=500)


class ApprovalStatusInput(BaseModel):
    identifier: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=5, max_length=200)


class ImportQuestionsInput(BaseModel):
    chapter_id: int
    source_file: str = "Uploaded question bank"
    source_hash: str | None = None
    questions: list[dict[str, Any]]


class StartAttemptInput(BaseModel):
    chapter_ids: list[int]
    question_count: int | None = Field(default=None, ge=1, le=500)
    question_formats: list[str] = []


class StartRevisionInput(BaseModel):
    chapter_ids: list[int] = []
    question_count: int | None = Field(default=None, ge=1, le=500)


class AnswerInput(BaseModel):
    question_id: int
    answer: str = ""
    finalize: bool = False


class RevisionMarkInput(BaseModel):
    question_id: int
    needs_revision: bool = True


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def login_page() -> FileResponse:
    return FileResponse(LOCAL_USER_DIR / "login.html")


def read_local_login_text() -> dict[str, str]:
    values = dict(LOCAL_LOGIN_TEXT_DEFAULTS)
    with db() as conn:
        rows = conn.execute(
            "SELECT setting_key,setting_value FROM app_settings WHERE setting_key LIKE 'local_login.%'"
        ).fetchall()
    for row in rows:
        key = row["setting_key"].removeprefix("local_login.")
        if key in values and str(row["setting_value"]).strip():
            values[key] = str(row["setting_value"])
    return values


@app.get("/api/public/local-login-text")
def public_local_login_text() -> dict[str, Any]:
    return {"content": read_local_login_text()}


@app.get("/admin-access")
def admin_access_page() -> FileResponse:
    return FileResponse(ADMIN_DIR / "login.html")


@app.get("/super-admin-access")
def super_admin_access_page() -> FileResponse:
    return FileResponse(SUPER_ADMIN_DIR / "login.html")


@app.get("/dashboard")
def dashboard_page() -> FileResponse:
    return FileResponse(LOCAL_USER_DIR / "dashboard.html")


@app.get("/admin")
def admin_page(user: sqlite3.Row = Depends(require_admin)) -> FileResponse:
    return FileResponse(ADMIN_DIR / "dashboard.html")


@app.get("/super-admin")
def super_admin_page(user: sqlite3.Row = Depends(require_super_admin)) -> FileResponse:
    return FileResponse(SUPER_ADMIN_DIR / "dashboard.html")


@app.get("/health")
def health() -> dict[str, Any]:
    info = database_info()
    with db() as conn:
        conn.execute("SELECT 1").fetchone()
    return {"status": "ok", "version": "3.1.0", "database": info}


@app.post("/api/register")
def register(payload: RegisterInput) -> dict[str, Any]:
    return create_account(payload, role="student")


@app.post("/api/admin-register")
def admin_register(payload: RegisterInput) -> dict[str, Any]:
    return create_account(payload, role="admin")


def create_account(payload: RegisterInput, role: Literal["student", "admin"]) -> dict[str, Any]:
    email = payload.email.strip().casefold()
    login_id = normalize_login_id(payload.login_id)
    with db() as conn:
        if conn.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE", (email,)).fetchone():
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        if conn.execute("SELECT id FROM users WHERE login_id = ? COLLATE NOCASE", (login_id,)).fetchone():
            raise HTTPException(status_code=409, detail="This User Name is already in use. Choose another one.")
        approval_status = "pending" if role == "admin" else "approved"
        account_status = "inactive" if role == "admin" else "active"
        approval_message = "Your Administrator account request is waiting for Super Admin approval." if role == "admin" else None
        cursor = conn.execute(
            """INSERT INTO users(name,email,login_id,password_hash,age,dob,city,gurukul_name,mobile,o_number,role,status,approval_status,approval_message,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                payload.name.strip(), email, login_id, hash_password(payload.password), payload.age, payload.dob,
                (payload.city or "").strip(), (payload.gurukul_name or "").strip(),
                (payload.mobile or "").strip(), (payload.o_number or "").strip(),
                role, account_status, approval_status, approval_message, now_iso(),
            ),
        )
        user = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        if role == "admin":
            super_admin = conn.execute("SELECT id FROM users WHERE role='super_admin' LIMIT 1").fetchone()
            if super_admin:
                push_notification(conn, super_admin["id"], "New Administrator approval request", f"{payload.name.strip()} (@{login_id}) requested Administrator access.", "info")
    if role == "admin":
        message = "Administrator request submitted. You can sign in only after the Super Admin approves it."
    else:
        message = "Account created successfully. Sign in with your User Name and password."
    return {
        "user": public_user(user),
        "message": message,
        "login_identifier": login_id,
        "redirect": "/admin-access" if role == "admin" else "/",
    }


def authenticate_user(
    payload: LoginInput,
    response: Response,
    allowed_role: str,
) -> dict[str, Any]:
    identifier = login_identifier(payload)
    with db() as conn:
        user = find_user_by_identifier(conn, identifier)
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid User Name/email or password.")
        if user["role"] != allowed_role:
            target = "Local User" if user["role"] == "student" else ("Super Admin" if user["role"] == "super_admin" else "Administrator")
            raise HTTPException(status_code=403, detail=f"This account belongs to the {target} portal.")
        if allowed_role == "admin":
            approval = user["approval_status"] if "approval_status" in user.keys() else "approved"
            if approval == "pending":
                raise HTTPException(status_code=403, detail="Your Administrator request is pending Super Admin approval.")
            if approval == "rejected":
                message = user["approval_message"] or "Your Administrator request was not approved."
                raise HTTPException(status_code=403, detail=message)
        if user["status"] != "active":
            raise HTTPException(status_code=403, detail="This account is inactive.")
        conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (now_iso(), user["id"]))
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    return complete_login(user, response)


@app.post("/api/login")
def login(payload: LoginInput, response: Response) -> dict[str, Any]:
    return authenticate_user(payload, response, allowed_role="student")


@app.post("/api/admin-login")
def admin_login(payload: LoginInput, response: Response) -> dict[str, Any]:
    return authenticate_user(payload, response, allowed_role="admin")


def _unique_super_login_id(conn: sqlite3.Connection) -> str:
    base = "superadmin"
    candidate = base
    suffix = 1
    while conn.execute("SELECT id FROM users WHERE login_id=? COLLATE NOCASE", (candidate,)).fetchone():
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


def _looks_like_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value.strip()))


def _looks_like_phone(value: str) -> bool:
    digits = re.sub(r"\D", "", value or "")
    return 7 <= len(digits) <= 15


@app.post("/api/super-admin-login")
def super_admin_login(payload: LoginInput, response: Response) -> dict[str, Any]:
    identifier = login_identifier(payload)
    # The owner portal is intentionally bound to one configured email only.
    # Do not accept phone numbers, user names, aliases, or another account.
    if identifier.casefold() != SUPER_ADMIN_EMAIL:
        raise HTTPException(status_code=401, detail="Invalid Super Admin email or password.")

    with db() as conn:
        owner = conn.execute(
            "SELECT * FROM users WHERE role='super_admin' AND email=? COLLATE NOCASE LIMIT 1",
            (SUPER_ADMIN_EMAIL,),
        ).fetchone()
        if not owner or not verify_password(payload.password, owner["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid Super Admin email or password.")
        if owner["status"] != "active":
            raise HTTPException(status_code=403, detail="This Super Admin account is inactive.")
        conn.execute("UPDATE users SET last_login=? WHERE id=?", (now_iso(), owner["id"]))
        owner = conn.execute("SELECT * FROM users WHERE id=?", (owner["id"],)).fetchone()
    return complete_login(owner, response)


@app.get("/api/super-admin-availability")
def super_admin_availability() -> dict[str, Any]:
    with db() as conn:
        exists = conn.execute("SELECT id FROM users WHERE role='super_admin' LIMIT 1").fetchone()
    return {"setup_required": not bool(exists)}


@app.post("/api/super-admin-register")
def super_admin_register_disabled() -> dict[str, Any]:
    raise HTTPException(status_code=410, detail="Super Admin Sign Up is disabled. Use the Super Admin Sign In page.")


@app.post("/api/super-admin-password-reset/request")
def super_admin_password_reset_request(payload: SuperAdminOtpRequestInput) -> dict[str, Any]:
    email = payload.email.strip().casefold()
    if not _looks_like_email(email):
        raise HTTPException(status_code=422, detail="Enter a valid registered email address.")

    with db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE role='super_admin' AND email=? COLLATE NOCASE LIMIT 1",
            (email,),
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="No Super Admin account is registered with this email address.")
        if email.endswith("@local.invalid"):
            raise HTTPException(status_code=422, detail="This Super Admin account was created with a phone number and does not have a recoverable email address.")

        recent = conn.execute(
            "SELECT created_at FROM password_reset_otps WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (user["id"],),
        ).fetchone()
        if recent and (_utc_now() - _parse_iso_datetime(recent["created_at"])) < timedelta(seconds=60):
            raise HTTPException(status_code=429, detail="Please wait 60 seconds before requesting another code.")

        code = f"{secrets.randbelow(10000):04d}"
        created_at = now_iso()
        expires_at = (_utc_now() + timedelta(minutes=10)).isoformat()
        conn.execute(
            "UPDATE password_reset_otps SET consumed_at=? WHERE user_id=? AND consumed_at IS NULL",
            (created_at, user["id"]),
        )
        cursor = conn.execute(
            """INSERT INTO password_reset_otps(user_id,email,otp_hash,expires_at,attempts,created_at)
               VALUES(?,?,?,?,0,?)""",
            (user["id"], email, _otp_hash(user["id"], email, code), expires_at, created_at),
        )
        otp_id = cursor.lastrowid

    try:
        delivery = _send_super_admin_reset_email(email, code)
    except Exception as exc:
        with db() as conn:
            conn.execute("DELETE FROM password_reset_otps WHERE id=?", (otp_id,))
        raise HTTPException(status_code=503, detail=f"The password reset email could not be sent. Check the email service configuration. ({type(exc).__name__})") from exc

    message = "A 4-digit verification code has been sent to the registered email address."
    if delivery == "local_outbox":
        message = "SMTP email is not configured on this local installation. A test email containing the 4-digit code was written to data/mail_outbox. Configure SMTP before deployment."
    return {"message": message, "delivery": delivery, "expires_in_seconds": 600}


@app.post("/api/super-admin-password-reset/verify")
def super_admin_password_reset_verify(payload: SuperAdminOtpVerifyInput) -> dict[str, Any]:
    email = payload.email.strip().casefold()
    code = payload.code.strip()
    if not re.fullmatch(r"\d{4}", code):
        raise HTTPException(status_code=422, detail="Enter the complete 4-digit verification code.")

    with db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE role='super_admin' AND email=? COLLATE NOCASE LIMIT 1",
            (email,),
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Super Admin account could not be verified.")
        otp = conn.execute(
            """SELECT * FROM password_reset_otps
               WHERE user_id=? AND email=? COLLATE NOCASE AND consumed_at IS NULL
               ORDER BY id DESC LIMIT 1""",
            (user["id"], email),
        ).fetchone()
        if not otp:
            raise HTTPException(status_code=400, detail="Request a new verification code.")
        if _parse_iso_datetime(otp["expires_at"]) < _utc_now():
            conn.execute("UPDATE password_reset_otps SET consumed_at=? WHERE id=?", (now_iso(), otp["id"]))
            raise HTTPException(status_code=410, detail="The verification code has expired. Request a new code.")
        if int(otp["attempts"] or 0) >= 5:
            conn.execute("UPDATE password_reset_otps SET consumed_at=? WHERE id=?", (now_iso(), otp["id"]))
            raise HTTPException(status_code=429, detail="Too many incorrect attempts. Request a new code.")

        expected = _otp_hash(user["id"], email, code)
        if not hmac.compare_digest(expected, otp["otp_hash"]):
            attempts = int(otp["attempts"] or 0) + 1
            conn.execute("UPDATE password_reset_otps SET attempts=? WHERE id=?", (attempts, otp["id"]))
            remaining = max(0, 5 - attempts)
            raise HTTPException(status_code=400, detail=f"Incorrect verification code. {remaining} attempt(s) remaining.")

        verified_at = now_iso()
        conn.execute(
            "UPDATE password_reset_otps SET verified_at=?, consumed_at=? WHERE id=?",
            (verified_at, verified_at, otp["id"]),
        )
        token = secrets.token_urlsafe(32)
        token_hash = _reset_token_hash(token)
        expires_at = (_utc_now() + timedelta(minutes=10)).isoformat()
        conn.execute(
            "INSERT INTO password_reset_tokens(user_id,token_hash,expires_at,created_at) VALUES(?,?,?,?)",
            (user["id"], token_hash, expires_at, verified_at),
        )
    return {"message": "Email verified. Create your new password.", "reset_token": token, "expires_in_seconds": 600}


@app.post("/api/super-admin-password-reset/complete")
def super_admin_password_reset_complete(payload: SuperAdminPasswordCompleteInput) -> dict[str, str]:
    token_hash = _reset_token_hash(payload.reset_token.strip())
    with db() as conn:
        reset = conn.execute(
            "SELECT * FROM password_reset_tokens WHERE token_hash=? AND used_at IS NULL LIMIT 1",
            (token_hash,),
        ).fetchone()
        if not reset:
            raise HTTPException(status_code=400, detail="Password reset session is invalid or already used.")
        if _parse_iso_datetime(reset["expires_at"]) < _utc_now():
            conn.execute("UPDATE password_reset_tokens SET used_at=? WHERE id=?", (now_iso(), reset["id"]))
            raise HTTPException(status_code=410, detail="Password reset session has expired. Start again.")
        user = conn.execute("SELECT * FROM users WHERE id=?", (reset["user_id"],)).fetchone()
        if not user or user["role"] != "super_admin":
            raise HTTPException(status_code=403, detail="Super Admin account could not be verified.")
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(payload.new_password), user["id"]))
        used_at = now_iso()
        conn.execute("UPDATE password_reset_tokens SET used_at=? WHERE id=?", (used_at, reset["id"]))
        conn.execute("UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL", (used_at, user["id"]))
        conn.execute("UPDATE password_reset_otps SET consumed_at=? WHERE user_id=? AND consumed_at IS NULL", (used_at, user["id"]))
    return {"message": "Password changed successfully. Sign in with your new password."}


@app.post("/api/admin-approval-status")
def admin_approval_status(payload: ApprovalStatusInput) -> dict[str, Any]:
    identifier = payload.identifier.strip().casefold()
    with db() as conn:
        user = find_user_by_identifier(conn, identifier)
        if not user or user["role"] != "admin" or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Administrator account details could not be verified.")
        return {
            "approval_status": user["approval_status"] or "approved",
            "message": user["approval_message"] or ("Your Administrator account is approved. You can sign in now." if user["status"] == "active" else "Administrator account is inactive."),
        }


@app.post("/api/forgot-password")
def forgot_password(payload: ForgotPasswordInput) -> dict[str, str]:
    return reset_account_password(payload, allowed_roles={"student"})


@app.post("/api/admin-forgot-password")
def admin_forgot_password(payload: ForgotPasswordInput) -> dict[str, str]:
    return reset_account_password(payload, allowed_roles={"admin"})


@app.post("/api/super-admin-forgot-password")
def super_admin_forgot_password(payload: ForgotPasswordInput) -> dict[str, str]:
    return reset_account_password(payload, allowed_roles={"super_admin"})


def reset_account_password(payload: ForgotPasswordInput, allowed_roles: set[str]) -> dict[str, str]:
    identifier = payload.identifier.strip().casefold()
    email = payload.email.strip().casefold()
    verification = normalize_text(payload.verification or "")
    with db() as conn:
        user = find_user_by_identifier(conn, identifier)
        if not user or user["email"].strip().casefold() != email or user["role"] not in allowed_roles:
            raise HTTPException(status_code=404, detail="Account details could not be verified.")

        saved_checks = [user["mobile"], user["dob"], user["o_number"]]
        available_checks = [normalize_text(value) for value in saved_checks if value and str(value).strip()]
        if available_checks and verification not in available_checks:
            raise HTTPException(
                status_code=403,
                detail="Verification detail does not match the registered mobile number or date of birth.",
            )

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(payload.new_password), user["id"]),
        )
    return {"message": "Password reset successfully. You can sign in with the new password."}


@app.post("/api/logout")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(TOKEN_COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    return {"user": public_user(user)}


@app.get("/api/subjects")
def subjects(user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute(
            """SELECT s.*, COUNT(DISTINCT c.id) AS chapter_count, COUNT(DISTINCT q.id) AS question_count
               FROM subjects s LEFT JOIN chapters c ON c.subject_id=s.id AND c.active=1
               LEFT JOIN questions q ON q.chapter_id=c.id AND q.active=1
               WHERE s.active=1 GROUP BY s.id ORDER BY s.title"""
        ).fetchall()
    return {"subjects": [dict(row) for row in rows]}


@app.get("/api/chapters")
def chapters(user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute(
            """SELECT c.id,c.subject_id,c.title,c.chapter_number,c.active,c.created_at, s.title AS subject_title, COUNT(DISTINCT q.id) AS question_count,
                      COUNT(DISTINCT m.id) AS material_count
               FROM chapters c JOIN subjects s ON s.id=c.subject_id
               LEFT JOIN questions q ON q.chapter_id=c.id AND q.active=1
               LEFT JOIN course_materials m ON m.chapter_id=c.id AND m.active=1
               WHERE c.active=1 AND s.active=1
               GROUP BY c.id ORDER BY s.title, COALESCE(c.chapter_number,99999), c.title"""
        ).fetchall()
    return {"chapters": [dict(row) for row in rows]}


@app.get("/api/materials")
def materials(chapter_ids: str = "", user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    ids = [int(value) for value in chapter_ids.split(",") if value.strip().isdigit()]
    with db() as conn:
        query = """SELECT m.*, c.title AS chapter_title, s.title AS subject_title
                   FROM course_materials m JOIN chapters c ON c.id=m.chapter_id
                   JOIN subjects s ON s.id=c.subject_id WHERE m.active=1"""
        params: list[Any] = []
        if ids:
            query += f" AND m.chapter_id IN ({','.join('?' for _ in ids)})"
            params.extend(ids)
        query += " ORDER BY s.title, COALESCE(c.chapter_number,99999), m.id"
        rows = conn.execute(query, params).fetchall()
    return {"materials": [dict(row) for row in rows]}


def attempt_owned(attempt_id: int, user_id: int) -> sqlite3.Row:
    with db() as conn:
        attempt = conn.execute("SELECT * FROM attempts WHERE id = ? AND user_id = ?", (attempt_id, user_id)).fetchone()
    if not attempt:
        raise HTTPException(status_code=404, detail="Quiz attempt not found.")
    return attempt


def question_in_attempt(attempt: sqlite3.Row, question_id: int) -> None:
    if question_id not in json.loads(attempt["question_ids_json"]):
        raise HTTPException(status_code=400, detail="Question does not belong to this quiz.")


def serialize_attempt(attempt_id: int, user_id: int) -> dict[str, Any]:
    attempt = attempt_owned(attempt_id, user_id)
    qids = json.loads(attempt["question_ids_json"])
    if not qids:
        raise HTTPException(status_code=400, detail="This quiz has no questions.")
    placeholders = ",".join("?" for _ in qids)
    with db() as conn:
        qrows = conn.execute(
            f"""SELECT q.*, c.title AS chapter_title, s.title AS subject_title FROM questions q
                JOIN chapters c ON c.id=q.chapter_id JOIN subjects s ON s.id=c.subject_id
                WHERE q.id IN ({placeholders})""", qids,
        ).fetchall()
        responses = conn.execute("SELECT * FROM responses WHERE attempt_id = ?", (attempt_id,)).fetchall()
        selected_chapter_ids = json.loads(attempt["chapter_ids_json"] or "[]")
        chapter_options: list[dict[str, str]] = []
        if selected_chapter_ids:
            cph = ",".join("?" for _ in selected_chapter_ids)
            crows = conn.execute(
                f"SELECT id,title,chapter_number FROM chapters WHERE id IN ({cph}) ORDER BY COALESCE(chapter_number,99999),title",
                selected_chapter_ids,
            ).fetchall()
            chapter_options = [
                {"key": chr(65 + idx) if idx < 26 else str(idx + 1), "text": row["title"], "value": row["title"]}
                for idx, row in enumerate(crows)
            ]
    qmap = {row["id"]: row for row in qrows}
    rmap = {row["question_id"]: row for row in responses}
    items: list[dict[str, Any]] = []
    for qid in qids:
        row = qmap.get(qid)
        if not row:
            continue
        r = rmap.get(qid)
        item: dict[str, Any] = {
            "id": row["id"],
            "chapter_id": row["chapter_id"],
            "chapter_title": row["chapter_title"],
            "subject_title": row["subject_title"],
            "question_text": row["question_text"],
            "question_type": "objective" if row["question_format"] == "identify_chapter" else row["question_type"],
            "question_format": row["question_format"],
            "options": chapter_options if row["question_format"] == "identify_chapter" else parse_options(json.loads(row["options_json"] or "[]")),
            "response": {
                "user_answer": r["user_answer"] if r else "",
                "is_correct": None if not r or r["is_correct"] is None else bool(r["is_correct"]),
                "answer_viewed": bool(r["answer_viewed"]) if r else False,
                "completed": bool(r["completed"]) if r else False,
            },
        }
        if r and (r["is_correct"] is not None or r["answer_viewed"]):
            _, display = resolve_answer_display(row)
            item["correct_answer"] = display
        items.append(item)
    return {
        "attempt": {
            "id": attempt["id"],
            "mode": attempt["mode"],
            "status": "pending" if attempt["status"] == "in_progress" and bool(attempt["finish_requested"]) else attempt["status"],
            "started_at": attempt["started_at"],
            "completed_at": attempt["completed_at"],
            "questions": items,
        }
    }


def create_attempt(conn: sqlite3.Connection, user_id: int, chapter_ids: list[int], question_ids: list[int], mode: str, question_formats: list[str] | None = None) -> int:
    cursor = conn.execute(
        "INSERT INTO attempts(user_id,chapter_ids_json,question_ids_json,mode,status,started_at,question_formats_json) VALUES(?,?,?,?,?,?,?)",
        (user_id, json.dumps(chapter_ids), json.dumps(question_ids), mode, "in_progress", now_iso(), json.dumps(question_formats or [])),
    )
    return int(cursor.lastrowid)


@app.post("/api/attempts/start")
def start_attempt(payload: StartAttemptInput, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    chapter_ids = sorted(set(payload.chapter_ids))
    if not chapter_ids:
        raise HTTPException(status_code=400, detail="Select at least one chapter.")
    placeholders = ",".join("?" for _ in chapter_ids)
    scope_json = json.dumps(chapter_ids)
    allowed_formats = {"mcq", "multiple_select", "true_false", "fill_blank", "one_word", "very_short", "short_answer", "who_said", "match", "sequence", "identify_chapter", "rapid_fire", "general"}
    question_formats = sorted({fmt.strip() for fmt in payload.question_formats if fmt.strip() in allowed_formats})
    formats_json = json.dumps(question_formats)
    with db() as conn:
        valid_count = conn.execute(
            f"SELECT COUNT(*) FROM chapters WHERE active=1 AND id IN ({placeholders})", chapter_ids
        ).fetchone()[0]
        if valid_count != len(chapter_ids):
            raise HTTPException(status_code=400, detail="One or more selected chapters are unavailable.")

        # Keep one live history row for the same chapter selection. Starting the same
        # unfinished quiz resumes and updates that row instead of creating duplicates.
        existing = conn.execute(
            """SELECT id FROM attempts
               WHERE user_id=? AND mode='quiz' AND status='in_progress' AND chapter_ids_json=?
                 AND COALESCE(question_formats_json,'[]')=?
               ORDER BY id DESC LIMIT 1""",
            (user["id"], scope_json, formats_json),
        ).fetchone()
        if existing:
            data = serialize_attempt(existing["id"], user["id"])
            data["resumed_existing"] = True
            return data

        question_query = f"SELECT id FROM questions WHERE active=1 AND chapter_id IN ({placeholders})"
        question_params: list[Any] = list(chapter_ids)
        if question_formats:
            question_query += f" AND question_format IN ({','.join('?' for _ in question_formats)})"
            question_params.extend(question_formats)
        qrows = conn.execute(question_query, question_params).fetchall()
        question_ids = [row["id"] for row in qrows]
        if not question_ids:
            raise HTTPException(status_code=400, detail="No approved questions are available for the selected chapters and question types.")
        random.shuffle(question_ids)
        if payload.question_count:
            question_ids = question_ids[: payload.question_count]
        attempt_id = create_attempt(conn, user["id"], chapter_ids, question_ids, "quiz", question_formats)
    data = serialize_attempt(attempt_id, user["id"])
    data["resumed_existing"] = False
    return data


@app.post("/api/revision/start")
def start_revision(payload: StartRevisionInput, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        query = """SELECT r.question_id, q.chapter_id FROM revision_items r
                   JOIN questions q ON q.id=r.question_id
                   WHERE r.user_id=? AND r.status='pending' AND q.active=1"""
        params: list[Any] = [user["id"]]
        chapter_ids = sorted(set(payload.chapter_ids))
        if chapter_ids:
            query += f" AND q.chapter_id IN ({','.join('?' for _ in chapter_ids)})"
            params.extend(chapter_ids)
        rows = conn.execute(query, params).fetchall()
        if not rows:
            raise HTTPException(status_code=400, detail="No pending revision questions are available.")
        question_ids = [row["question_id"] for row in rows]
        random.shuffle(question_ids)
        if payload.question_count:
            question_ids = question_ids[: payload.question_count]
        actual_chapters = sorted({row["chapter_id"] for row in rows if row["question_id"] in question_ids})
        attempt_id = create_attempt(conn, user["id"], actual_chapters, question_ids, "revision")
    return serialize_attempt(attempt_id, user["id"])


@app.get("/api/attempts/{attempt_id}")
def get_attempt(attempt_id: int, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    return serialize_attempt(attempt_id, user["id"])


def add_revision_item(conn: sqlite3.Connection, user_id: int, question_id: int, attempt_id: int) -> None:
    conn.execute(
        """INSERT INTO revision_items(user_id,question_id,source_attempt_id,status,wrong_count,last_wrong_at)
           VALUES(?,?,?,?,1,?)
           ON CONFLICT(user_id,question_id) DO UPDATE SET source_attempt_id=excluded.source_attempt_id,
           status='pending',wrong_count=revision_items.wrong_count+1,last_wrong_at=excluded.last_wrong_at""",
        (user_id, question_id, attempt_id, "pending", now_iso()),
    )


@app.post("/api/attempts/{attempt_id}/check")
def check_answer(attempt_id: int, payload: AnswerInput, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    attempt = attempt_owned(attempt_id, user["id"])
    if attempt["status"] == "completed":
        raise HTTPException(status_code=400, detail="This quiz is already completed.")
    question_in_attempt(attempt, payload.question_id)
    with db() as conn:
        q = conn.execute("SELECT * FROM questions WHERE id = ?", (payload.question_id,)).fetchone()
        if not q or (q["question_type"] != "objective" and q["question_format"] != "identify_chapter"):
            raise HTTPException(status_code=400, detail="This action is only for objective questions.")
        if not payload.answer.strip():
            raise HTTPException(status_code=400, detail="Please select an answer.")
        correct = objective_is_correct(q, payload.answer)
        conn.execute(
            """INSERT INTO responses(attempt_id,question_id,user_answer,is_correct,answer_viewed,completed,updated_at)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(attempt_id,question_id) DO UPDATE SET user_answer=excluded.user_answer,
               is_correct=excluded.is_correct,completed=1,updated_at=excluded.updated_at""",
            (attempt_id, payload.question_id, payload.answer.strip(), int(correct), 0, 1, now_iso()),
        )
        if not correct:
            add_revision_item(conn, user["id"], payload.question_id, attempt_id)
        elif attempt["mode"] == "revision":
            conn.execute(
                "UPDATE revision_items SET status='mastered',last_reviewed_at=? WHERE user_id=? AND question_id=?",
                (now_iso(), user["id"], payload.question_id),
            )
    correct_keys, correct_text = resolve_answer_display(q)
    return {
        "is_correct": correct,
        "correct_key": ",".join(correct_keys),
        "correct_answer": correct_text,
        "added_to_revision": not correct,
    }


@app.post("/api/attempts/{attempt_id}/save-written")
def save_written(attempt_id: int, payload: AnswerInput, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    attempt = attempt_owned(attempt_id, user["id"])
    if attempt["status"] == "completed":
        raise HTTPException(status_code=400, detail="This quiz is already completed.")
    question_in_attempt(attempt, payload.question_id)
    with db() as conn:
        q = conn.execute("SELECT * FROM questions WHERE id = ?", (payload.question_id,)).fetchone()
        if not q or q["question_type"] != "written" or q["question_format"] in {"match", "sequence"}:
            raise HTTPException(status_code=400, detail="This action is only for written questions.")
        answer = payload.answer.strip()
        previous = conn.execute(
            "SELECT is_correct FROM responses WHERE attempt_id=? AND question_id=?",
            (attempt_id, payload.question_id),
        ).fetchone()
        is_correct: int | None = None
        match_percentage: float | None = None
        if payload.finalize and answer:
            match_percentage = written_match_percentage(q, answer)
            is_correct = int(match_percentage >= 70.0)
        conn.execute(
            """INSERT INTO responses(attempt_id,question_id,user_answer,is_correct,answer_viewed,completed,updated_at)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(attempt_id,question_id) DO UPDATE SET user_answer=excluded.user_answer,
               is_correct=excluded.is_correct,completed=excluded.completed,updated_at=excluded.updated_at""",
            (attempt_id, payload.question_id, answer, is_correct, 0, int(bool(answer)), now_iso()),
        )
        if payload.finalize and answer and is_correct == 0:
            if not previous or previous["is_correct"] is None or bool(previous["is_correct"]):
                add_revision_item(conn, user["id"], payload.question_id, attempt_id)
        elif payload.finalize and answer and is_correct == 1 and attempt["mode"] == "revision":
            conn.execute(
                "UPDATE revision_items SET status='mastered',last_reviewed_at=? WHERE user_id=? AND question_id=?",
                (now_iso(), user["id"], payload.question_id),
            )
    return {
        "saved": True,
        "completed": bool(answer),
        "is_correct": None if is_correct is None else bool(is_correct),
        "match_percentage": match_percentage,
        "added_to_revision": bool(payload.finalize and answer and is_correct == 0),
    }


@app.post("/api/attempts/{attempt_id}/view-answer")
def view_answer(attempt_id: int, payload: AnswerInput, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    attempt = attempt_owned(attempt_id, user["id"])
    question_in_attempt(attempt, payload.question_id)
    with db() as conn:
        q = conn.execute("SELECT * FROM questions WHERE id = ?", (payload.question_id,)).fetchone()
        if not q or q["question_type"] != "written" or q["question_format"] in {"match", "sequence"}:
            raise HTTPException(status_code=400, detail="This action is only for written questions.")
        existing = conn.execute(
            "SELECT user_answer,is_correct FROM responses WHERE attempt_id=? AND question_id=?", (attempt_id, payload.question_id)
        ).fetchone()
        user_answer = (existing["user_answer"] if existing else payload.answer).strip()
        match_percentage = written_match_percentage(q, user_answer) if user_answer else 0.0
        correct = match_percentage >= 70.0 if user_answer else False
        conn.execute(
            """INSERT INTO responses(attempt_id,question_id,user_answer,is_correct,answer_viewed,completed,updated_at)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(attempt_id,question_id) DO UPDATE SET user_answer=excluded.user_answer,
               is_correct=excluded.is_correct,answer_viewed=1,completed=1,updated_at=excluded.updated_at""",
            (attempt_id, payload.question_id, user_answer, int(correct), 1, 1, now_iso()),
        )
        if not correct:
            if not existing or existing["is_correct"] is None or bool(existing["is_correct"]):
                add_revision_item(conn, user["id"], payload.question_id, attempt_id)
        elif attempt["mode"] == "revision":
            conn.execute(
                "UPDATE revision_items SET status='mastered',last_reviewed_at=? WHERE user_id=? AND question_id=?",
                (now_iso(), user["id"], payload.question_id),
            )
    return {
        "correct_answer": q["correct_answer"], "answer_viewed": True,
        "is_correct": correct, "match_percentage": match_percentage, "added_to_revision": not correct,
    }


@app.post("/api/attempts/{attempt_id}/check-structured")
def check_structured(attempt_id: int, payload: AnswerInput, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    attempt = attempt_owned(attempt_id, user["id"])
    if attempt["status"] == "completed":
        raise HTTPException(status_code=400, detail="This quiz is already completed.")
    question_in_attempt(attempt, payload.question_id)
    with db() as conn:
        q = conn.execute("SELECT * FROM questions WHERE id=?", (payload.question_id,)).fetchone()
        if not q or q["question_format"] not in {"match", "sequence"}:
            raise HTTPException(status_code=400, detail="This action is only for matching or sequence questions.")
        correct = structured_is_correct(q, payload.answer)
        previous = conn.execute(
            "SELECT is_correct FROM responses WHERE attempt_id=? AND question_id=?",
            (attempt_id, payload.question_id),
        ).fetchone()
        conn.execute(
            """INSERT INTO responses(attempt_id,question_id,user_answer,is_correct,answer_viewed,completed,updated_at)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(attempt_id,question_id) DO UPDATE SET user_answer=excluded.user_answer,
               is_correct=excluded.is_correct,completed=1,updated_at=excluded.updated_at""",
            (attempt_id, payload.question_id, payload.answer, int(correct), 0, 1, now_iso()),
        )
        if not correct:
            if not previous or previous["is_correct"] is None or bool(previous["is_correct"]):
                add_revision_item(conn, user["id"], payload.question_id, attempt_id)
        elif attempt["mode"] == "revision":
            conn.execute(
                "UPDATE revision_items SET status='mastered',last_reviewed_at=? WHERE user_id=? AND question_id=?",
                (now_iso(), user["id"], payload.question_id),
            )
    return {
        "is_correct": correct, "correct_answer": q["correct_answer"],
        "added_to_revision": not correct,
    }


@app.post("/api/revision/mark")
def mark_revision(payload: RevisionMarkInput, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        question = conn.execute("SELECT id FROM questions WHERE id=?", (payload.question_id,)).fetchone()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found.")
        if payload.needs_revision:
            conn.execute(
                """INSERT INTO revision_items(user_id,question_id,status,wrong_count,last_wrong_at)
                   VALUES(?,?,?,1,?)
                   ON CONFLICT(user_id,question_id) DO UPDATE SET status='pending',last_wrong_at=excluded.last_wrong_at""",
                (user["id"], payload.question_id, "pending", now_iso()),
            )
        else:
            conn.execute(
                "UPDATE revision_items SET status='mastered',last_reviewed_at=? WHERE user_id=? AND question_id=?",
                (now_iso(), user["id"], payload.question_id),
            )
    return {"saved": True, "status": "pending" if payload.needs_revision else "mastered"}


def result_for_attempt(attempt_id: int, user_id: int, include_questions: bool = False) -> dict[str, Any]:
    attempt = attempt_owned(attempt_id, user_id)
    qids = json.loads(attempt["question_ids_json"])
    if not qids:
        return {"attempt_id": attempt_id, "total": 0, "completed": 0, "remaining": 0}
    placeholders = ",".join("?" for _ in qids)
    with db() as conn:
        qrows = conn.execute(
            f"""SELECT q.*, c.title AS chapter_title, c.chapter_number, s.title AS subject_title
                FROM questions q JOIN chapters c ON c.id=q.chapter_id JOIN subjects s ON s.id=c.subject_id
                WHERE q.id IN ({placeholders})""", qids,
        ).fetchall()
        responses = conn.execute("SELECT * FROM responses WHERE attempt_id=?", (attempt_id,)).fetchall()
    scope_rows = sorted(
        {row["chapter_id"]: (row["subject_title"], row["chapter_number"], row["chapter_title"]) for row in qrows}.values(),
        key=lambda item: (str(item[0]).casefold(), item[1] if item[1] is not None else 99999, str(item[2]).casefold()),
    )
    scope_label = " + ".join(str(item[2]) for item in scope_rows) if scope_rows else "Quiz"
    qmap = {row["id"]: row for row in qrows}
    rmap = {row["question_id"]: row for row in responses}
    correct = wrong = written = viewed = completed = 0
    chapter_stats: dict[int, dict[str, Any]] = {}
    question_review: list[dict[str, Any]] = []
    for qid in qids:
        q = qmap.get(qid)
        if not q:
            continue
        r = rmap.get(qid)
        chapter = chapter_stats.setdefault(
            q["chapter_id"],
            {
                "chapter_id": q["chapter_id"], "chapter_title": q["chapter_title"],
                "subject_title": q["subject_title"], "total": 0, "completed": 0,
                "correct": 0, "wrong": 0, "written": 0,
            },
        )
        chapter["total"] += 1
        if r and r["completed"]:
            completed += 1
            chapter["completed"] += 1
        if r and r["is_correct"] is not None:
            if r["is_correct"]:
                correct += 1
                chapter["correct"] += 1
            else:
                wrong += 1
                chapter["wrong"] += 1
        if r and q["question_type"] == "written" and r["user_answer"]:
            written += 1
            chapter["written"] += 1
        if r and q["question_type"] == "written" and r["answer_viewed"]:
            viewed += 1
        if include_questions and r and r["completed"]:
            _, answer_display = resolve_answer_display(q)
            question_review.append(
                {
                    "question_id": qid,
                    "subject_title": q["subject_title"],
                    "chapter_title": q["chapter_title"],
                    "question_text": q["question_text"],
                    "question_type": q["question_type"],
                    "question_format": q["question_format"],
                    "user_answer": r["user_answer"] if r else "",
                    "is_correct": None if not r or r["is_correct"] is None else bool(r["is_correct"]),
                    "answer_viewed": bool(r["answer_viewed"]) if r else False,
                    "correct_answer": answer_display,
                }
            )
    total = len(qids)
    remaining = max(total - completed, 0)
    completion = round((completed / total) * 100, 1) if total else 0
    evaluated_attempted = correct + wrong
    for stats in chapter_stats.values():
        evaluated = stats["correct"] + stats["wrong"]
        stats["attempted"] = stats["completed"]
        stats["remaining"] = max(stats["total"] - stats["completed"], 0)
        stats["completion_percentage"] = round(stats["completed"] / stats["total"] * 100, 1) if stats["total"] else 0
        stats["accuracy"] = round(stats["correct"] / evaluated * 100, 1) if evaluated else 0
        stats["performance_percentage"] = stats["accuracy"]
    result: dict[str, Any] = {
        "attempt_id": attempt_id,
        "mode": attempt["mode"],
        "scope_label": scope_label,
        "total": total,
        "completed": completed,
        "remaining": remaining,
        "correct": correct,
        "wrong": wrong,
        "written_answers": written,
        "written_answers_viewed": viewed,
        "completion_percentage": completion,
        "remaining_percentage": round(100 - completion, 1),
        "objective_accuracy": round((correct / evaluated_attempted) * 100, 1) if evaluated_attempted else 0,
        "performance_percentage": round((correct / evaluated_attempted) * 100, 1) if evaluated_attempted else 0,
        "evaluated_attempted": evaluated_attempted,
        "status": "pending" if attempt["status"] == "in_progress" and bool(attempt["finish_requested"]) else attempt["status"],
        "started_at": attempt["started_at"],
        "completed_at": attempt["completed_at"],
        "chapter_results": [stats for stats in chapter_stats.values() if stats.get("attempted", 0) > 0],
    }
    if include_questions:
        result["questions"] = question_review
    return result


@app.post("/api/attempts/{attempt_id}/finish")
def finish_attempt(attempt_id: int, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    # A quiz becomes completed only at 100% question completion.
    # If Finish is pressed early, keep the DB attempt resumable and expose it as "pending".
    attempt_owned(attempt_id, user["id"])
    current_result = result_for_attempt(attempt_id, user["id"], include_questions=False)
    is_complete = current_result["total"] > 0 and current_result["completed"] == current_result["total"]
    with db() as conn:
        if is_complete:
            conn.execute(
                "UPDATE attempts SET status='completed',completed_at=?,finish_requested=1 WHERE id=?",
                (now_iso(), attempt_id),
            )
        else:
            conn.execute(
                "UPDATE attempts SET status='in_progress',completed_at=NULL,finish_requested=1 WHERE id=?",
                (attempt_id,),
            )
    return {"result": result_for_attempt(attempt_id, user["id"], include_questions=True)}


@app.get("/api/attempts/{attempt_id}/result")
def attempt_result(attempt_id: int, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    return {"result": result_for_attempt(attempt_id, user["id"], include_questions=True)}


def analytics_for_user(user_id: int) -> dict[str, Any]:
    with db() as conn:
        chapter_rows = conn.execute(
            """SELECT c.id,c.title,c.chapter_number,s.id AS subject_id,s.title AS subject_title,
                      COUNT(q.id) AS total_questions
               FROM chapters c JOIN subjects s ON s.id=c.subject_id
               LEFT JOIN questions q ON q.chapter_id=c.id AND q.active=1
               WHERE c.active=1 AND s.active=1 GROUP BY c.id
               ORDER BY s.title,COALESCE(c.chapter_number,99999),c.title"""
        ).fetchall()
        response_rows = conn.execute(
            """SELECT r.question_id,r.is_correct,r.completed,q.chapter_id
               FROM responses r JOIN attempts a ON a.id=r.attempt_id
               JOIN questions q ON q.id=r.question_id WHERE a.user_id=?""",
            (user_id,),
        ).fetchall()
        revision_count = conn.execute(
            "SELECT COUNT(*) FROM revision_items WHERE user_id=? AND status='pending'", (user_id,)
        ).fetchone()[0]

    attempted_by_chapter: dict[int, set[int]] = defaultdict(set)
    correct_by_chapter: dict[int, int] = defaultdict(int)
    wrong_by_chapter: dict[int, int] = defaultdict(int)
    for row in response_rows:
        if row["completed"]:
            attempted_by_chapter[row["chapter_id"]].add(row["question_id"])
        if row["is_correct"] is not None:
            if row["is_correct"]:
                correct_by_chapter[row["chapter_id"]] += 1
            else:
                wrong_by_chapter[row["chapter_id"]] += 1

    per_chapter: list[dict[str, Any]] = []
    subject_agg: dict[int, dict[str, Any]] = {}
    for row in chapter_rows:
        chapter_id = row["id"]
        total = row["total_questions"]
        attempted = len(attempted_by_chapter[chapter_id])
        correct = correct_by_chapter[chapter_id]
        wrong = wrong_by_chapter[chapter_id]
        objective_attempted = correct + wrong
        chapter = {
            "chapter_id": chapter_id,
            "chapter_title": row["title"],
            "chapter_number": row["chapter_number"],
            "subject_id": row["subject_id"],
            "subject_title": row["subject_title"],
            "total_questions": total,
            "attempted_questions": attempted,
            "remaining_questions": max(total - attempted, 0),
            "completion_percentage": round(attempted / total * 100, 1) if total else 0,
            "correct": correct,
            "wrong": wrong,
            "accuracy": round(correct / objective_attempted * 100, 1) if objective_attempted else 0,
        }
        per_chapter.append(chapter)
        agg = subject_agg.setdefault(
            row["subject_id"],
            {
                "subject_id": row["subject_id"], "subject_title": row["subject_title"],
                "total_questions": 0, "attempted_questions": 0, "correct": 0, "wrong": 0,
            },
        )
        agg["total_questions"] += total
        agg["attempted_questions"] += attempted
        agg["correct"] += correct
        agg["wrong"] += wrong

    per_subject: list[dict[str, Any]] = []
    for agg in subject_agg.values():
        total = agg["total_questions"]
        objective_attempted = agg["correct"] + agg["wrong"]
        agg["remaining_questions"] = max(total - agg["attempted_questions"], 0)
        agg["completion_percentage"] = round(agg["attempted_questions"] / total * 100, 1) if total else 0
        agg["accuracy"] = round(agg["correct"] / objective_attempted * 100, 1) if objective_attempted else 0
        per_subject.append(agg)

    total_questions = sum(item["total_questions"] for item in per_chapter)
    attempted_questions = sum(item["attempted_questions"] for item in per_chapter)
    total_correct = sum(item["correct"] for item in per_chapter)
    total_wrong = sum(item["wrong"] for item in per_chapter)
    objective_attempted = total_correct + total_wrong
    return {
        "overall": {
            "total_questions": total_questions,
            "attempted_questions": attempted_questions,
            "remaining_questions": max(total_questions - attempted_questions, 0),
            "completion_percentage": round(attempted_questions / total_questions * 100, 1) if total_questions else 0,
            "correct": total_correct,
            "wrong": total_wrong,
            "accuracy": round(total_correct / objective_attempted * 100, 1) if objective_attempted else 0,
            "revision_pending": revision_count,
        },
        "subjects": per_subject,
        "chapters": per_chapter,
    }


@app.get("/api/dashboard")
def dashboard_data(user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        attempts = conn.execute("SELECT * FROM attempts WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
        chapters = conn.execute(
            """SELECT c.id,c.title,c.chapter_number,c.subject_id,s.title AS subject_title,
                      COUNT(DISTINCT q.id) AS total_questions,COUNT(DISTINCT m.id) AS material_count
               FROM chapters c JOIN subjects s ON s.id=c.subject_id
               LEFT JOIN questions q ON q.chapter_id=c.id AND q.active=1
               LEFT JOIN course_materials m ON m.chapter_id=c.id AND m.active=1
               WHERE c.active=1 AND s.active=1 GROUP BY c.id
               ORDER BY s.title,COALESCE(c.chapter_number,99999),c.title"""
        ).fetchall()
    results = [result_for_attempt(a["id"], user["id"]) for a in attempts]
    analytics = analytics_for_user(user["id"])
    return {
        "summary": {
            "total_attempts": len(results),
            "completed_attempts": sum(1 for r in results if r["status"] == "completed"),
            "in_progress_attempts": sum(1 for r in results if r["status"] in {"in_progress", "pending"}),
            "correct": analytics["overall"]["correct"],
            "wrong": analytics["overall"]["wrong"],
            "accuracy": analytics["overall"]["accuracy"],
            "revision_pending": analytics["overall"]["revision_pending"],
        },
        "attempts": results[:50],
        "chapters": [dict(c) for c in chapters],
        "analytics": analytics,
    }


@app.get("/api/analytics")
def analytics(user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    return analytics_for_user(user["id"])


@app.get("/api/revision")
def revision_list(user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute(
            """SELECT r.*,q.question_text,q.question_type,q.question_format,c.id AS chapter_id,
                      c.title AS chapter_title,s.title AS subject_title
               FROM revision_items r JOIN questions q ON q.id=r.question_id
               JOIN chapters c ON c.id=q.chapter_id JOIN subjects s ON s.id=c.subject_id
               WHERE r.user_id=? AND r.status='pending' AND q.active=1
               ORDER BY r.last_wrong_at DESC""",
            (user["id"],),
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


def overall_student_analytics(conn: sqlite3.Connection) -> dict[str, Any]:
    students = conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
    active_students = conn.execute("SELECT COUNT(*) FROM users WHERE role='student' AND status='active'").fetchone()[0]
    attempts = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
    completed_attempts = conn.execute("SELECT COUNT(*) FROM attempts WHERE status='completed'").fetchone()[0]
    response_row = conn.execute("""SELECT COUNT(*) AS attempted,
        COALESCE(SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END),0) AS correct,
        COALESCE(SUM(CASE WHEN is_correct=0 THEN 1 ELSE 0 END),0) AS wrong
        FROM responses WHERE completed=1 AND user_answer IS NOT NULL AND TRIM(user_answer)<>''""").fetchone()
    attempted = int(response_row["attempted"] or 0)
    correct = int(response_row["correct"] or 0)
    wrong = int(response_row["wrong"] or 0)
    accuracy = round(correct * 100 / (correct + wrong), 1) if (correct + wrong) else 0.0
    return {"students": students, "active_students": active_students, "attempts": attempts,
            "completed_attempts": completed_attempts, "attempted_questions": attempted,
            "correct": correct, "wrong": wrong, "accuracy": accuracy}


@app.get("/api/super-admin/dashboard")
def super_admin_dashboard(user: sqlite3.Row = Depends(require_super_admin)) -> dict[str, Any]:
    with db() as conn:
        analytics = overall_student_analytics(conn)
        admin_stats = {
            "admins": conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0],
            "pending": conn.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND approval_status='pending'").fetchone()[0],
            "approved": conn.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND approval_status='approved'").fetchone()[0],
            "rejected": conn.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND approval_status='rejected'").fetchone()[0],
            "active": conn.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND status='active'").fetchone()[0],
            "inactive": conn.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND status='inactive'").fetchone()[0],
            "uploads": conn.execute("""SELECT COUNT(*) FROM question_bank_uploads qbu
                JOIN users u ON u.id=qbu.uploaded_by WHERE u.role='admin'""").fetchone()[0],
        }
        admins = conn.execute("""SELECT u.*, COUNT(qbu.id) AS uploads
            FROM users u LEFT JOIN question_bank_uploads qbu ON qbu.uploaded_by=u.id
            WHERE u.role='admin' GROUP BY u.id ORDER BY u.id DESC""").fetchall()
        students = conn.execute("""SELECT u.*, COUNT(DISTINCT a.id) AS attempts,
            COUNT(DISTINCT CASE WHEN a.status='completed' THEN a.id END) AS completed_attempts,
            COUNT(DISTINCT CASE WHEN a.status='in_progress' THEN a.id END) AS pending_attempts,
            COALESCE(SUM(CASE WHEN r.completed=1 AND r.user_answer IS NOT NULL AND TRIM(r.user_answer)<>'' THEN 1 ELSE 0 END),0) AS attempted_questions,
            COALESCE(SUM(CASE WHEN r.completed=1 AND r.is_correct=1 THEN 1 ELSE 0 END),0) AS correct,
            COALESCE(SUM(CASE WHEN r.completed=1 AND r.is_correct=0 THEN 1 ELSE 0 END),0) AS wrong,
            (SELECT COUNT(*) FROM revision_items ri WHERE ri.user_id=u.id AND ri.status='pending') AS revision_pending
            FROM users u LEFT JOIN attempts a ON a.user_id=u.id LEFT JOIN responses r ON r.attempt_id=a.id
            WHERE u.role='student' GROUP BY u.id ORDER BY u.id DESC""").fetchall()
        analytics["inactive_students"] = conn.execute("SELECT COUNT(*) FROM users WHERE role='student' AND status='inactive'").fetchone()[0]
        analytics["pending_attempts"] = conn.execute("""SELECT COUNT(*) FROM attempts a JOIN users u ON u.id=a.user_id
            WHERE u.role='student' AND a.status='in_progress'""").fetchone()[0]
        analytics["revision_pending"] = conn.execute("""SELECT COUNT(*) FROM revision_items ri JOIN users u ON u.id=ri.user_id
            WHERE u.role='student' AND ri.status='pending'""").fetchone()[0]
    admin_rows=[]
    for row in admins:
        item=public_user(row); item["uploads"]=int(row["uploads"] or 0); admin_rows.append(item)
    student_rows=[]
    for row in students:
        item=public_user(row)
        item["attempts"]=int(row["attempts"] or 0)
        item["completed_attempts"]=int(row["completed_attempts"] or 0)
        item["pending_attempts"]=int(row["pending_attempts"] or 0)
        item["attempted_questions"]=int(row["attempted_questions"] or 0)
        item["correct"]=int(row["correct"] or 0)
        item["wrong"]=int(row["wrong"] or 0)
        item["revision_pending"]=int(row["revision_pending"] or 0)
        denom=item["correct"]+item["wrong"]
        item["accuracy"]=round(item["correct"]*100/denom,1) if denom else 0.0
        student_rows.append(item)
    return {"analytics": analytics, "admin_stats": admin_stats, "admins": admin_rows, "students": student_rows}


@app.get("/api/super-admin/admins")
def super_admin_admins(user: sqlite3.Row = Depends(require_super_admin)) -> dict[str, Any]:
    with db() as conn:
        rows=conn.execute("SELECT * FROM users WHERE role='admin' ORDER BY CASE approval_status WHEN 'pending' THEN 0 WHEN 'rejected' THEN 1 ELSE 2 END, id DESC").fetchall()
    return {"admins":[public_user(r) for r in rows]}


def push_notification(conn: sqlite3.Connection, user_id: int, title: str, message: str, kind: str = "info") -> None:
    conn.execute("INSERT INTO notifications(user_id,title,message,kind,is_read,created_at) VALUES(?,?,?,?,0,?)",
                 (user_id,title,message,kind,now_iso()))


@app.post("/api/super-admin/admins/{admin_id}/approve")
def approve_admin(admin_id: int, payload: AdminApprovalInput, user: sqlite3.Row = Depends(require_super_admin)) -> dict[str, Any]:
    message=(payload.message or "Your Administrator account has been approved by the Super Admin. You can sign in now.").strip()
    with db() as conn:
        row=conn.execute("SELECT * FROM users WHERE id=? AND role='admin'",(admin_id,)).fetchone()
        if not row: raise HTTPException(status_code=404, detail="Administrator request not found.")
        conn.execute("UPDATE users SET approval_status='approved',approval_message=?,approved_at=?,approved_by=?,status='active' WHERE id=?",
                     (message,now_iso(),user["id"],admin_id))
        push_notification(conn, admin_id, "Administrator access approved", message, "success")
        updated=conn.execute("SELECT * FROM users WHERE id=?",(admin_id,)).fetchone()
    return {"admin":public_user(updated),"message":message}


@app.post("/api/super-admin/admins/{admin_id}/reject")
def reject_admin(admin_id: int, payload: AdminApprovalInput, user: sqlite3.Row = Depends(require_super_admin)) -> dict[str, Any]:
    message=(payload.message or "Your Administrator account request was not approved. Contact the Super Admin for details.").strip()
    with db() as conn:
        row=conn.execute("SELECT * FROM users WHERE id=? AND role='admin'",(admin_id,)).fetchone()
        if not row: raise HTTPException(status_code=404, detail="Administrator request not found.")
        conn.execute("UPDATE users SET approval_status='rejected',approval_message=?,approved_at=NULL,approved_by=?,status='inactive' WHERE id=?",
                     (message,user["id"],admin_id))
        push_notification(conn, admin_id, "Administrator request update", message, "error")
        updated=conn.execute("SELECT * FROM users WHERE id=?",(admin_id,)).fetchone()
    return {"admin":public_user(updated),"message":message}


@app.put("/api/super-admin/admins/{admin_id}")
def update_admin_account(admin_id: int, payload: AdminUpdateInput, user: sqlite3.Row = Depends(require_super_admin)) -> dict[str, Any]:
    email=payload.email.strip().casefold(); login_id=normalize_login_id(payload.login_id)
    with db() as conn:
        row=conn.execute("SELECT * FROM users WHERE id=? AND role='admin'",(admin_id,)).fetchone()
        if not row: raise HTTPException(status_code=404, detail="Administrator not found.")
        dup=conn.execute("SELECT id FROM users WHERE id<>? AND (email=? COLLATE NOCASE OR login_id=? COLLATE NOCASE)",(admin_id,email,login_id)).fetchone()
        if dup: raise HTTPException(status_code=409, detail="Email or User Name is already in use.")
        conn.execute("UPDATE users SET name=?,email=?,login_id=?,status=? WHERE id=?",(payload.name.strip(),email,login_id,payload.status,admin_id))
        if payload.new_password: conn.execute("UPDATE users SET password_hash=? WHERE id=?",(hash_password(payload.new_password),admin_id))
        updated=conn.execute("SELECT * FROM users WHERE id=?",(admin_id,)).fetchone()
    return {"admin":public_user(updated)}


@app.delete("/api/super-admin/admins/{admin_id}")
def delete_admin_account(admin_id: int, user: sqlite3.Row = Depends(require_super_admin)) -> dict[str, Any]:
    with db() as conn:
        row=conn.execute("SELECT id FROM users WHERE id=? AND role='admin'",(admin_id,)).fetchone()
        if not row: raise HTTPException(status_code=404, detail="Administrator not found.")
        conn.execute("DELETE FROM users WHERE id=?",(admin_id,))
    return {"deleted":True}


@app.get("/api/admin/local-login-text")
def admin_local_login_text(user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    return {"content": read_local_login_text()}


@app.put("/api/admin/local-login-text")
def update_admin_local_login_text(payload: LocalLoginTextInput, user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    values = payload.model_dump()
    with db() as conn:
        for key, value in values.items():
            conn.execute(
                """INSERT INTO app_settings(setting_key,setting_value,updated_at,updated_by) VALUES(?,?,?,?)
                   ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value,updated_at=excluded.updated_at,updated_by=excluded.updated_by""",
                (f"local_login.{key}", value.strip(), now_iso(), user["id"]),
            )
    return {"content": read_local_login_text(), "saved": True}


@app.get("/api/admin/notifications")
def admin_notifications(user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        rows=conn.execute("SELECT * FROM notifications WHERE user_id=? AND is_read=0 ORDER BY id DESC",(user["id"],)).fetchall()
        if rows: conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=? AND is_read=0",(user["id"],))
    return {"notifications":[dict(r) for r in rows]}


@app.get("/api/admin/dashboard")
def admin_dashboard(user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        stats = {
            "students": conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
            "active_students": conn.execute("SELECT COUNT(*) FROM users WHERE role='student' AND status='active'").fetchone()[0],
            "subjects": conn.execute("SELECT COUNT(*) FROM subjects WHERE active=1").fetchone()[0],
            "chapters": conn.execute("SELECT COUNT(*) FROM chapters WHERE active=1").fetchone()[0],
            "questions": conn.execute("SELECT COUNT(*) FROM questions WHERE active=1").fetchone()[0],
            "materials": conn.execute("SELECT COUNT(*) FROM course_materials WHERE active=1").fetchone()[0],
            "attempts": conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0],
        }
        recent_students = conn.execute("SELECT * FROM users WHERE role='student' ORDER BY id DESC LIMIT 8").fetchall()
        subject_rows = conn.execute(
            """SELECT s.*,COUNT(DISTINCT c.id) AS chapter_count,COUNT(DISTINCT q.id) AS question_count
               FROM subjects s LEFT JOIN chapters c ON c.subject_id=s.id
               LEFT JOIN questions q ON q.chapter_id=c.id AND q.active=1 GROUP BY s.id ORDER BY s.title"""
        ).fetchall()
        chapter_rows = conn.execute(
            """SELECT c.id,c.title,c.chapter_number,c.subject_id,c.remark,s.title AS subject_title,
                      COUNT(DISTINCT q.id) AS question_count,COUNT(DISTINCT m.id) AS material_count
               FROM chapters c JOIN subjects s ON s.id=c.subject_id
               LEFT JOIN questions q ON q.chapter_id=c.id
               LEFT JOIN course_materials m ON m.chapter_id=c.id AND m.active=1
               GROUP BY c.id ORDER BY s.title,COALESCE(c.chapter_number,99999),c.title"""
        ).fetchall()
    return {
        "stats": stats,
        "recent_students": [public_user(r) for r in recent_students],
        "subjects": [dict(r) for r in subject_rows],
        "chapters": [dict(r) for r in chapter_rows],
    }


@app.get("/api/admin/students")
def admin_students(user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute(
            """SELECT u.*,COUNT(DISTINCT a.id) AS attempts
               FROM users u LEFT JOIN attempts a ON a.user_id=u.id
               WHERE u.role='student' GROUP BY u.id ORDER BY u.id DESC"""
        ).fetchall()
    students: list[dict[str, Any]] = []
    for row in rows:
        item = public_user(row)
        item["attempts"] = row["attempts"]
        students.append(item)
    return {"students": students}


@app.put("/api/admin/students/{student_id}")
def update_student(student_id: int, payload: StudentUpdateInput, user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    email = payload.email.strip().lower()
    login_id = normalize_login_id(payload.login_id)
    with db() as conn:
        current = conn.execute("SELECT * FROM users WHERE id=? AND role='student'", (student_id,)).fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="Student not found.")
        duplicate = conn.execute("SELECT id FROM users WHERE id<>? AND (email=? COLLATE NOCASE OR login_id=? COLLATE NOCASE)",
                                 (student_id, email, login_id)).fetchone()
        if duplicate:
            raise HTTPException(status_code=409, detail="Email or Login ID is already in use.")
        values = [payload.name.strip(), email, login_id, payload.age, (payload.dob or "").strip() or None,
                  (payload.city or "").strip(), (payload.gurukul_name or "").strip(), (payload.mobile or "").strip(),
                  (payload.o_number or "").strip(), payload.status, student_id]
        conn.execute("""UPDATE users SET name=?,email=?,login_id=?,age=?,dob=?,city=?,gurukul_name=?,mobile=?,o_number=?,status=? WHERE id=?""", values)
        if payload.new_password:
            conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(payload.new_password), student_id))
        row = conn.execute("SELECT * FROM users WHERE id=?", (student_id,)).fetchone()
    return {"student": public_user(row)}


@app.delete("/api/admin/students/{student_id}")
def delete_student(student_id: int, user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT id,name FROM users WHERE id=? AND role='student'", (student_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Student not found.")
        conn.execute("DELETE FROM users WHERE id=?", (student_id,))
    return {"deleted": True}


@app.get("/api/admin/questions")
def admin_questions(chapter_id: int, user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute("""SELECT q.*,c.title AS chapter_title FROM questions q JOIN chapters c ON c.id=q.chapter_id
                               WHERE q.chapter_id=? AND q.active=1 ORDER BY q.id""", (chapter_id,)).fetchall()
    out=[]
    for row in rows:
        item=dict(row)
        item["options"] = parse_options(json.loads(row["options_json"] or "[]"))
        item.pop("options_json", None)
        out.append(item)
    return {"questions": out}


@app.put("/api/admin/questions/{question_id}")
def update_question(question_id: int, payload: QuestionUpdateInput, user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    options = parse_options(payload.options or [])
    with db() as conn:
        cursor = conn.execute("""UPDATE questions SET question_text=?,correct_answer=?,options_json=? WHERE id=? AND active=1""",
                              (payload.question_text.strip(), payload.correct_answer.strip(), json.dumps(options, ensure_ascii=False), question_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Question not found.")
    return {"saved": True}


@app.delete("/api/admin/questions/{question_id}")
def delete_question(question_id: int, user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        cursor = conn.execute("UPDATE questions SET active=0 WHERE id=? AND active=1", (question_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Question not found.")
        conn.execute("UPDATE revision_items SET status='mastered' WHERE question_id=? AND status='pending'", (question_id,))
    return {"deleted": True}


@app.post("/api/admin/subjects")
def create_subject(payload: SubjectInput, user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO subjects(title,description,active,created_at) VALUES(?,?,1,?)",
                (payload.title.strip(), (payload.description or "").strip(), now_iso()),
            )
        except DBIntegrityError as exc:
            raise HTTPException(status_code=409, detail="A subject with this title already exists.") from exc
        row = conn.execute("SELECT * FROM subjects WHERE id=?", (cursor.lastrowid,)).fetchone()
    return {"subject": dict(row)}


@app.put("/api/admin/subjects/{subject_id}")
def update_subject(subject_id: int, payload: SubjectUpdateInput, user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        current = conn.execute("SELECT id FROM subjects WHERE id=?", (subject_id,)).fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="Subject not found.")
        try:
            conn.execute("UPDATE subjects SET title=?, description=? WHERE id=?",
                         (payload.title.strip(), (payload.description or "").strip(), subject_id))
        except DBIntegrityError as exc:
            raise HTTPException(status_code=409, detail="A subject with this title already exists.") from exc
        row = conn.execute("SELECT * FROM subjects WHERE id=?", (subject_id,)).fetchone()
    return {"subject": dict(row)}


@app.post("/api/admin/chapters")
def create_chapter(payload: ChapterInput, user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        subject = conn.execute("SELECT id FROM subjects WHERE id=? AND active=1", (payload.subject_id,)).fetchone()
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found.")
        try:
            cursor = conn.execute(
                "INSERT INTO chapters(subject_id,title,chapter_number,active,created_at) VALUES(?,?,?,1,?)",
                (payload.subject_id, payload.title.strip(), payload.chapter_number, now_iso()),
            )
        except DBIntegrityError as exc:
            raise HTTPException(status_code=409, detail="This chapter already exists in the selected subject.") from exc
        row = conn.execute("SELECT * FROM chapters WHERE id=?", (cursor.lastrowid,)).fetchone()
    return {"chapter": dict(row)}


@app.put("/api/admin/chapters/{chapter_id}")
def update_chapter(chapter_id: int, payload: ChapterUpdateInput, user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        if not conn.execute("SELECT id FROM chapters WHERE id=?", (chapter_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Chapter not found.")
        if not conn.execute("SELECT id FROM subjects WHERE id=? AND active=1", (payload.subject_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Subject not found.")
        try:
            conn.execute("UPDATE chapters SET subject_id=?, title=?, chapter_number=?, remark=? WHERE id=?",
                         (payload.subject_id, payload.title.strip(), payload.chapter_number, (payload.remark or "").strip(), chapter_id))
        except DBIntegrityError as exc:
            raise HTTPException(status_code=409, detail="This chapter already exists in the selected subject.") from exc
        row = conn.execute("SELECT * FROM chapters WHERE id=?", (chapter_id,)).fetchone()
    return {"chapter": dict(row)}


@app.put("/api/admin/chapters/{chapter_id}/remark")
def update_chapter_remark(chapter_id: int, payload: RemarkInput, user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        cursor = conn.execute("UPDATE chapters SET remark=? WHERE id=?", (payload.remark.strip(), chapter_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Chapter not found.")
    return {"saved": True, "remark": payload.remark.strip()}


@app.post("/api/admin/materials")
async def create_material(
    chapter_id: int = Form(...),
    title: str = Form(...),
    file: UploadFile | None = File(default=None),
    pasted_text: str = Form(default=""),
    user: sqlite3.Row = Depends(require_admin),
) -> dict[str, Any]:
    has_file = bool(file and file.filename)
    has_text = bool(pasted_text.strip())
    if not has_file and not has_text:
        raise HTTPException(status_code=400, detail="Choose a material file or paste course material text.")
    with db() as conn:
        chapter = conn.execute("SELECT subject_id FROM chapters WHERE id=?", (chapter_id,)).fetchone()
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found.")
    source_file = "Pasted material"
    content = pasted_text.strip()
    if has_file and not has_text:
        assert file is not None and file.filename is not None
        source_file = file.filename
        suffix = Path(file.filename).suffix.lower()
        if suffix not in {".docx", ".txt", ".md"}:
            raise HTTPException(status_code=400, detail="Upload a DOCX, TXT or MD course material file.")
        raw = await file.read()
        if len(raw) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size must be below 10 MB.")
        if suffix == ".docx":
            temp_path = DATA_DIR / f"material_{secrets.token_hex(8)}.docx"
            temp_path.write_bytes(raw)
            try:
                content = extract_document_text(temp_path)
            finally:
                temp_path.unlink(missing_ok=True)
        else:
            content = raw.decode("utf-8", errors="replace").strip()
    if not content:
        raise HTTPException(status_code=400, detail="No readable course material was found.")
    with db() as conn:
        cursor = conn.execute(
            """INSERT INTO course_materials(subject_id,chapter_id,title,content,source_file,active,created_at)
               VALUES(?,?,?,?,?,1,?)""",
            (chapter["subject_id"], chapter_id, title.strip(), content, source_file, now_iso()),
        )
    return {"material_id": cursor.lastrowid, "saved": True}


@app.get("/api/admin/materials")
def admin_materials(user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute(
            """SELECT m.id,m.title,m.source_file,m.created_at,c.title AS chapter_title,s.title AS subject_title
               FROM course_materials m JOIN chapters c ON c.id=m.chapter_id
               JOIN subjects s ON s.id=c.subject_id WHERE m.active=1 ORDER BY m.id DESC"""
        ).fetchall()
    return {"materials": [dict(row) for row in rows]}


@app.post("/api/admin/question-banks/preview")
async def preview_question_bank(
    file: UploadFile | None = File(default=None),
    pasted_text: str = Form(default=""),
    chapter_id: int | None = Form(default=None),
    user: sqlite3.Row = Depends(require_admin),
) -> dict[str, Any]:
    input_warnings: list[str] = []
    has_file = bool(file and file.filename)
    has_text = bool(pasted_text.strip())
    if not has_file and not has_text:
        raise HTTPException(status_code=400, detail="Choose a question-bank file or paste its text.")
    source_hash: str | None = None
    if has_text:
        filename = "Pasted text"
        lines = text_lines(pasted_text)
        if has_file:
            input_warnings.append("Both a file and pasted text were supplied. Pasted text was analyzed.")
    else:
        assert file is not None and file.filename is not None
        filename = file.filename
        suffix = Path(file.filename).suffix.lower()
        if suffix not in {".docx", ".txt", ".md"}:
            raise HTTPException(status_code=400, detail="Upload a DOCX, TXT or MD question bank.")
        content = await file.read()
        source_hash = hashlib.sha256(content).hexdigest()
        if chapter_id:
            with db() as conn:
                prior_hash = conn.execute("SELECT id FROM question_bank_uploads WHERE source_hash=?", (source_hash,)).fetchone()
                prior_name = conn.execute("SELECT id FROM questions WHERE chapter_id=? AND source_file=? AND active=1 LIMIT 1", (chapter_id, filename)).fetchone()
            if prior_hash or prior_name:
                raise HTTPException(status_code=409, detail="This question-bank file has already been uploaded. Duplicate upload is not allowed.")
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size must be below 10 MB.")
        if suffix == ".docx":
            temp_path = DATA_DIR / f"preview_{secrets.token_hex(8)}.docx"
            temp_path.write_bytes(content)
            try:
                lines = document_lines(temp_path)
            except Exception as exc:
                raise HTTPException(status_code=400, detail="The Word file could not be read. Save it again as a standard .docx file.") from exc
            finally:
                temp_path.unlink(missing_ok=True)
        else:
            lines = text_lines(content.decode("utf-8", errors="replace"))
    questions, parser_warnings = parse_question_bank(lines)
    return {
        "source_file": filename,
        "source_hash": source_hash,
        "questions": questions,
        "summary": {
            "total": len(questions),
            "detected": sum(1 for q in questions if q["status"] == "detected"),
            "needs_review": sum(1 for q in questions if q["status"] != "detected"),
        },
        "warnings": input_warnings + parser_warnings,
    }


@app.post("/api/admin/question-banks/import")
def import_question_bank(payload: ImportQuestionsInput, user: sqlite3.Row = Depends(require_admin)) -> dict[str, Any]:
    with db() as conn:
        chapter = conn.execute("SELECT id FROM chapters WHERE id=?", (payload.chapter_id,)).fetchone()
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found.")
        if payload.source_hash and conn.execute("SELECT id FROM question_bank_uploads WHERE source_hash=?", (payload.source_hash,)).fetchone():
            raise HTTPException(status_code=409, detail="This question-bank file has already been uploaded. Duplicate upload is not allowed.")
        if payload.source_file != "Pasted text" and conn.execute("SELECT id FROM questions WHERE chapter_id=? AND source_file=? AND active=1 LIMIT 1", (payload.chapter_id, payload.source_file)).fetchone():
            raise HTTPException(status_code=409, detail="A question bank with this file name is already imported in this chapter.")
        imported = skipped = 0
        for item in payload.questions:
            question_text = str(item.get("question_text") or "").strip()
            correct_answer = str(item.get("correct_answer") or "").strip()
            status = item.get("status")
            if not question_text or not correct_answer or status != "detected":
                skipped += 1
                continue
            qtype = "objective" if item.get("question_type") == "objective" else "written"
            question_format = str(item.get("question_format") or item.get("section") or "general")
            options = parse_options(item.get("options") or [])
            conn.execute(
                """INSERT INTO questions(chapter_id,question_text,question_type,question_format,options_json,
                   correct_answer,answer_source,source_file,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    payload.chapter_id, question_text, qtype, question_format,
                    json.dumps(options, ensure_ascii=False), correct_answer,
                    str(item.get("answer_source") or ""), payload.source_file, now_iso(),
                ),
            )
            imported += 1
        if imported and payload.source_hash:
            conn.execute("INSERT INTO question_bank_uploads(chapter_id,source_file,source_hash,uploaded_by,created_at) VALUES(?,?,?,?,?)",
                         (payload.chapter_id, payload.source_file, payload.source_hash, user["id"], now_iso()))
    return {"imported": imported, "skipped": skipped}


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# MySQL Database

The application now uses MySQL as its production database. The browser never writes directly to MySQL. All Local User, Admin and Super Admin data flows through the FastAPI backend and is committed to MySQL.

## Primary schema

- `database/schema.sql` / `database/mysql_schema.sql` - MySQL schema
- `database/sqlite_legacy_schema.sql` - reference only for old installations

## Persistent data coverage

| Table | Stored data |
|---|---|
| `users` | Local User, Admin, Super Admin profile, login ID, email, password hash, role, status, admin approval, last login |
| `subjects` | Subject folders |
| `chapters` | Chapters, number, subject link, remarks |
| `course_materials` | Uploaded/pasted study material |
| `questions` | Complete question bank, type, options, correct answer, source file |
| `question_bank_uploads` | Uploaded Word file fingerprints and uploader |
| `attempts` | Every quiz/revision session and status |
| `responses` | Every typed/selected answer, correct/wrong state, view-answer state |
| `revision_items` | Wrong-question revision queue and mastery status |
| `notifications` | Admin/Super Admin notifications |
| `app_settings` | Admin-controlled public login-page text and application settings |
| `password_reset_otps` | Super Admin OTP reset workflow |
| `password_reset_tokens` | Verified password-reset tokens |

All quiz history and analytics are calculated from these persistent tables, so a page refresh or later login loads the same data again.

## Initialize

```bash
python scripts/init_db.py
```

This command is idempotent. It creates missing tables without deleting existing rows.

## Migrate old SQLite data

Put the current old database at `data/quiz_platform.db` or pass another path:

```bash
python scripts/migrate_sqlite_to_mysql.py --source /path/to/quiz_platform.db
```

The migration copies users, admins, Super Admin, subjects, chapters, materials, questions, attempts, answers, revision data, notifications and settings while preserving IDs.

## Backup

```bash
python scripts/backup_db.py
```

A timestamped portable JSON backup is written to `database/backups/`.

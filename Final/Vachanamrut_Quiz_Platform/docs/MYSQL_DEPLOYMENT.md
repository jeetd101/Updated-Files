# MySQL Deployment Guide

## Recommended: Docker Compose

This is the easiest deployment because MySQL and the web application are created together.

1. Copy `.env.example` to `.env`.
2. Change at least `APP_SECRET`, `MYSQL_ROOT_PASSWORD` and `MYSQL_PASSWORD`.
3. Run:

```bash
docker compose up -d --build
```

The MySQL database is stored in the persistent Docker volume `mysql_data`. Rebuilding or restarting the web container does not delete user data.

Default application URL:

- Local User: `http://SERVER:8030/`
- Admin: `http://SERVER:8030/admin-access`
- Super Admin: `http://SERVER:8030/super-admin-access`

## Existing MySQL server

Configure `.env`:

```env
DB_BACKEND=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=vachanamrut_quiz
MYSQL_USER=quiz_user
MYSQL_PASSWORD=YOUR_PASSWORD
APP_SECRET=YOUR_LONG_STABLE_SECRET
```

If the database/user does not yet exist and you have MySQL root/admin credentials:

```env
MYSQL_ADMIN_USER=root
MYSQL_ADMIN_PASSWORD=YOUR_MYSQL_ROOT_PASSWORD
```

Then run:

```bash
python scripts/create_mysql_database.py
python scripts/init_db.py
python scripts/check_project.py
```

Start the web application:

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8030
```

## Upgrade from the old SQLite version without losing data

Stop the old application first and copy its real `quiz_platform.db` into this project's `data/` directory. Then configure MySQL and run:

```bash
python scripts/init_db.py
python scripts/migrate_sqlite_to_mysql.py --source data/quiz_platform.db
python scripts/check_project.py
```

After migration, sign in with the same existing Local User/Admin/Super Admin credentials. Password hashes are migrated unchanged.

## Persistence rules

- Registration data is written to MySQL before the API returns success.
- Quiz text/MCQ answers are written to MySQL as users interact with the quiz.
- Login sessions use an HTTP-only cookie. `APP_SECRET` must stay the same across server restarts.
- The dashboard fetches fresh data from MySQL after refresh/reopen.
- Admin approval state and notification state are stored in MySQL.
- Super Admin analytics are generated live from MySQL records.

## HTTPS production setting

When the public site is served through HTTPS, set:

```env
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
```

Do not change `APP_SECRET` after users begin using the site unless you intentionally want all active sessions to sign in again.

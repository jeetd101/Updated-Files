# Vachanamrut Quiz Platform v3.0 - Deployment Ready Structure

This release reorganizes the existing application by role without changing the quiz/admin functionality.

## Role-separated frontend

```text
frontend/
├── local_user/
│   ├── login.html
│   ├── dashboard.html
│   └── student.js
├── admin/
│   ├── login.html
│   ├── dashboard.html
│   └── admin.js
├── super_admin/
│   ├── login.html
│   ├── dashboard.html
│   └── super_admin.js
└── shared/
    ├── css/
    │   ├── styles.css
    │   └── login.css
    └── js/
        └── common.js
```

## Backend and database

```text
backend/
└── app/
    └── main.py              # Shared API, authentication, quiz logic

database/
├── schema.sql               # Schema reference
├── README.md
└── backups/                 # Created when backup script runs

data/
└── quiz_platform.db         # Active SQLite database

scripts/
├── init_db.py               # Create / migrate database
├── backup_db.py             # Safe timestamped backup
└── check_project.py         # Quick structure/database test
```

## URLs
- Local User: `/`
- Admin: `/admin-access`
- Super Admin: `/super-admin-access`

## First run on Windows
1. Extract the ZIP completely.
2. Run `run_windows.bat`.
3. The script installs requirements and creates/upgrades the database automatically.
4. Open `http://127.0.0.1:8030/`.

## Database creation
Run:

`python scripts/init_db.py`

It does not delete existing data. If `data/quiz_platform.db` already exists, safe migrations are applied.

## Database backup
Run:

`python scripts/backup_db.py`

## Deployment
Docker files and a deployment guide are included. See `docs/DEPLOYMENT.md`.

## Existing data
To move an older installation, stop both apps and copy its `data/quiz_platform.db` into this project's `data/` folder. Keep a backup first.

## Super Admin password reset by email (v3.0)

The Super Admin access page includes **Forgot password?** with a 4-digit email OTP flow:

1. Enter the registered Super Admin email address.
2. Receive and enter the 4-digit code (valid for 10 minutes, maximum 5 wrong attempts).
3. Create a new password (minimum 5 characters).

For production email delivery, copy `.env.example` to `.env` and configure the `SMTP_*` values, then set `MAIL_DELIVERY_MODE=smtp`.

For local testing, `MAIL_DELIVERY_MODE=auto` writes the email to `data/mail_outbox` when SMTP is not configured. The OTP is never returned by the API response.

## Fixed Super Admin (v3.2)

The Super Admin portal now accepts exactly one owner email. On the first v3.2 startup, the configured account is created or promoted and all other `super_admin` roles are demoted to normal Administrators.

Configure these values in `.env` before deployment:

```env
SUPER_ADMIN_EMAIL=sadhusevakdas215@sgrs.org
SUPER_ADMIN_BOOTSTRAP_PASSWORD=@gurukulquiz2184
```

Only `SUPER_ADMIN_EMAIL` can sign in through `/super-admin-access`. The bootstrap password is applied once during the v3.2 identity migration. The existing OTP password-reset flow remains available for that same email and later restarts do not overwrite a reset password.

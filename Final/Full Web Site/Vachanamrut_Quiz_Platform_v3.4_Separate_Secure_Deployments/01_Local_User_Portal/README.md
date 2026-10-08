# Local User Portal v3.4

Deploy this folder independently for students/local users only. It contains only the Local User frontend plus its backend runtime. Admin/Super Admin pages are not included and their API namespaces are blocked on this deployment.

1. Copy `.env.example` to `.env`.
2. Set `MYSQL_HOST` and `MYSQL_PASSWORD` to the shared MySQL database.
3. Run `docker compose up -d --build` or `run_windows.bat`.

Default port: **8041**.

Secrets are server-side only. `data/.app_secret` is generated automatically and is never available through `/assets`.

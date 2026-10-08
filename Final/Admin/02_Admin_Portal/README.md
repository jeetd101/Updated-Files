# Admin Portal v3.4

Deploy this folder independently for Administrators only. It includes Admin Sign In/Sign Up and all existing Admin functions. Super Admin pages are not included and Super Admin APIs are blocked on this deployment.

1. Copy `.env.example` to `.env`.
2. Set the same shared MySQL credentials used by the Local User and Super Admin deployments.
3. Run `docker compose up -d --build` or `run_windows.bat`.

Default port: **8042**.

Admin approval status remains live because all portals use the same MySQL database. No database/JWT/SMTP secret is sent to the browser.

# Super Admin Portal v3.4

Deploy this folder independently for the single Super Admin. It includes Super Admin analytics/control and the existing full Admin panel for owner access.

1. Copy `.env.example` to `.env`.
2. Set the same shared MySQL credentials used by the other two deployments.
3. Configure SMTP privately in `.env` if email OTP password reset is required.
4. Run `docker compose up -d --build` or `run_windows.bat`.

Default port: **8043**.

The fixed Super Admin email remains `sadhusevakdas215@sgrs.org`. The plaintext password is not present in frontend files, source configuration or `.env.example`; initial verification uses a server-only irreversible scrypt hash. Password reset continues to update the database hash.

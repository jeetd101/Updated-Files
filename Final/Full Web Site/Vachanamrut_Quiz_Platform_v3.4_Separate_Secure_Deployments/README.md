# Vachanamrut Quiz Platform v3.4 - Separate Secure Deployments

The existing application is split into three independently deployable portals. No UI or quiz workflow was intentionally changed.

## Deployments

1. `01_Local_User_Portal` - Local User Sign In/Sign Up, Courses, Quiz, Results and Revision.
2. `02_Admin_Portal` - Admin Sign In/Sign Up, approval status, Subjects, Chapters, Question Bank, Materials and Students.
3. `03_Super_Admin_Portal` - fixed Super Admin Sign In, Admin approvals/control, Local User analytics and full Admin access.
4. `00_Shared_MySQL_Database` - one shared MySQL database used by all three portals.

## Security

- No APP/JWT signing secret is present in frontend HTML/JS or `.env.example`. Each portal generates a private server-only key in `data/.app_secret`.
- MySQL and SMTP passwords are server-side `.env` values only. `.env` is ignored by Git.
- The Super Admin plaintext password is not stored in frontend/source configuration. Fresh deployment uses an irreversible scrypt bootstrap hash in the Super Admin server data directory.
- Local User deployment blocks Admin and Super Admin API namespaces.
- Admin deployment blocks Super Admin API namespaces.
- Backend/data/database files are never mounted as static browser assets.

## Recommended deployment

Use separate host names if available:
- `quiz.example.com` -> Local User Portal
- `admin.example.com` -> Admin Portal
- `owner.example.com` -> Super Admin Portal

All three must connect to the same MySQL database so live users, approvals, quiz results and analytics remain synchronized.

Start the shared MySQL database first, then deploy each portal separately. Copy each `.env.example` to `.env` on its own server and set the same private MySQL credentials.

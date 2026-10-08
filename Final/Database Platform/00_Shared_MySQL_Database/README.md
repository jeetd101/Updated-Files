# Shared MySQL Database v3.4

This database is shared by Local User, Admin and Super Admin deployments.

1. Copy `.env.example` to `.env`.
2. Replace both password placeholders with strong private values.
3. Run `docker compose up -d`.
4. Configure every portal with the same `MYSQL_DATABASE`, `MYSQL_USER` and `MYSQL_PASSWORD`.

MySQL data is persisted in the Docker volume `mysql_vachanamrut_data`. The schema is initialized automatically on a fresh database. Never publish the `.env` file.

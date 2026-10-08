from __future__ import annotations

import os
import re
from collections.abc import Mapping, Iterator
from pathlib import Path
from typing import Any, Sequence

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Connection, CursorResult, Engine, URL
from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Production should set DATABASE_URL to MySQL, for example:
# mysql+pymysql://quiz_user:password@mysql:3306/vachanamrut_quiz?charset=utf8mb4
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_BACKEND = os.getenv("DB_BACKEND", "mysql").strip().casefold()

if DATABASE_URL:
    DB_TARGET: str | URL = DATABASE_URL
elif DB_BACKEND == "sqlite":
    # Explicit development/legacy fallback only. Production package defaults to MySQL.
    DB_TARGET = f"sqlite:///{(DATA_DIR / 'quiz_platform.db').as_posix()}"
else:
    mysql_password = os.getenv("MYSQL_PASSWORD", "")
    if not mysql_password:
        raise RuntimeError("MYSQL_PASSWORD must be configured on the server. It is never sent to the browser.")
    DB_TARGET = URL.create(
        "mysql+pymysql",
        username=os.getenv("MYSQL_USER", "quiz_user"),
        password=mysql_password,
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306") or "3306"),
        database=os.getenv("MYSQL_DATABASE", "vachanamrut_quiz"),
        query={"charset": "utf8mb4"},
    )

ENGINE: Engine = create_engine(
    DB_TARGET,
    pool_pre_ping=True,
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "280") or "280"),
    pool_size=int(os.getenv("DB_POOL_SIZE", "10") or "10") if not str(DB_TARGET).startswith("sqlite") else 5,
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20") or "20") if not str(DB_TARGET).startswith("sqlite") else 10,
    future=True,
    connect_args={"check_same_thread": False} if str(DB_TARGET).startswith("sqlite") else {"connect_timeout": 10},
)

DB_DIALECT = ENGINE.dialect.name
DBIntegrityError = SQLAlchemyIntegrityError


class HybridRow(Mapping[str, Any]):
    """Mapping row that also supports SQLite-style integer indexing."""

    def __init__(self, keys: Sequence[str], values: Sequence[Any]):
        self._keys = list(keys)
        self._values = list(values)
        self._map = dict(zip(self._keys, self._values))

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return self._map[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def keys(self):
        return self._map.keys()

    def get(self, key: str, default: Any = None) -> Any:
        return self._map.get(key, default)

    def __repr__(self) -> str:
        return repr(self._map)


class ResultWrapper:
    def __init__(self, result: CursorResult[Any]):
        self._result = result
        self.lastrowid = getattr(result, "lastrowid", None)
        self.rowcount = result.rowcount
        self._keys = list(result.keys()) if result.returns_rows else []

    def fetchone(self) -> HybridRow | None:
        row = self._result.fetchone()
        if row is None:
            return None
        return HybridRow(self._keys, list(row))

    def fetchall(self) -> list[HybridRow]:
        if not self._result.returns_rows:
            return []
        return [HybridRow(self._keys, list(row)) for row in self._result.fetchall()]


_UPSERT_RE = re.compile(r"\s+ON\s+CONFLICT\s*\(([^)]+)\)\s+DO\s+UPDATE\s+SET\s+(.+)$", re.I | re.S)


def _mysqlize_sql(sql: str) -> str:
    sql = re.sub(r"\s+COLLATE\s+NOCASE", "", sql, flags=re.I)
    sql = re.sub(r"\bINSERT\s+OR\s+IGNORE\b", "INSERT IGNORE", sql, flags=re.I)

    match = _UPSERT_RE.search(sql)
    if match:
        update_clause = match.group(2).strip()
        # SQLite's excluded.col maps to MySQL's VALUES(col) for this app's upserts.
        update_clause = re.sub(r"\bexcluded\.([A-Za-z_][A-Za-z0-9_]*)", r"VALUES(\1)", update_clause)
        sql = sql[: match.start()] + " ON DUPLICATE KEY UPDATE " + update_clause

    # mysqlclient/PyMySQL use %s placeholders. The application SQL has no literal ? tokens.
    sql = sql.replace("?", "%s")
    return sql


class DBConnection:
    def __init__(self):
        self._conn: Connection | None = None
        self._tx = None

    def __enter__(self) -> "DBConnection":
        self._conn = ENGINE.connect()
        self._tx = self._conn.begin()
        if DB_DIALECT == "mysql":
            self._conn.exec_driver_sql("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
            self._conn.exec_driver_sql("SET time_zone = '+00:00'")
        elif DB_DIALECT == "sqlite":
            self._conn.exec_driver_sql("PRAGMA foreign_keys = ON")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self._tx is not None:
                if exc_type is None:
                    self._tx.commit()
                else:
                    self._tx.rollback()
        finally:
            if self._conn is not None:
                self._conn.close()

    @property
    def raw(self) -> Connection:
        if self._conn is None:
            raise RuntimeError("Database connection is not open")
        return self._conn

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> ResultWrapper:
        bound = tuple(params) if params else None
        if DB_DIALECT == "mysql":
            sql = _mysqlize_sql(sql)
        result = self.raw.exec_driver_sql(sql, bound) if bound is not None else self.raw.exec_driver_sql(sql)
        return ResultWrapper(result)

    def executescript(self, script: str) -> None:
        # Execute statements individually so SQLAlchemy keeps transaction state consistent.
        for statement in split_sql_script(script):
            cleaned = re.sub(r"(?m)^\s*--.*$", "", statement).strip()
            if cleaned:
                self.execute(cleaned)


def db() -> DBConnection:
    return DBConnection()


def table_columns(conn: DBConnection, table: str) -> set[str]:
    inspector = inspect(conn.raw)
    try:
        return {str(col["name"]) for col in inspector.get_columns(table)}
    except Exception:
        return set()


def table_exists(conn: DBConnection, table: str) -> bool:
    return inspect(conn.raw).has_table(table)


def add_column_if_missing(conn: DBConnection, table: str, definition: str) -> None:
    name = definition.split()[0].strip("`")
    if name in table_columns(conn, table):
        return
    if DB_DIALECT == "mysql":
        definition = _sqlite_definition_to_mysql(definition)
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def _sqlite_definition_to_mysql(definition: str) -> str:
    # Current migrations only use simple scalar columns.
    text = definition
    text = re.sub(r"\bTEXT\b", "TEXT", text, flags=re.I)
    text = re.sub(r"\bINTEGER\b", "BIGINT", text, flags=re.I)
    # MySQL cannot add a REFERENCES clause inline reliably across versions; FK is optional for legacy migration columns.
    text = re.sub(r"\s+REFERENCES\s+\w+\([^)]*\)(?:\s+ON\s+DELETE\s+\w+)?", "", text, flags=re.I)
    return text


def split_sql_script(script: str) -> list[str]:
    """Split our schema scripts on semicolons outside quoted strings."""
    statements: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escape = False
    for ch in script:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\":
            current.append(ch)
            escape = True
            continue
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in {"'", '"', '`'}:
            quote = ch
            current.append(ch)
            continue
        if ch == ";":
            statements.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def execute_schema_file(conn: DBConnection, path: Path) -> None:
    script = path.read_text(encoding="utf-8")
    for statement in split_sql_script(script):
        # Skip comments-only chunks.
        cleaned = re.sub(r"(?m)^\s*--.*$", "", statement).strip()
        if cleaned:
            conn.execute(cleaned)


def database_info() -> dict[str, str]:
    if DB_DIALECT == "mysql":
        # Hide credentials from API/console output.
        host = ENGINE.url.host or "mysql"
        db_name = ENGINE.url.database or ""
        return {"backend": "mysql", "host": host, "database": db_name}
    return {"backend": "sqlite", "database": str(ENGINE.url.database or "")}

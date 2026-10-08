"""Create or safely upgrade the configured database (MySQL in production)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import database_info  # noqa: E402
from backend.app.main import init_db  # noqa: E402

if __name__ == "__main__":
    init_db()
    info = database_info()
    print(f"Database ready: {info}")

from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "moon.db"
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"

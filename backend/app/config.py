"""Runtime settings. Everything is read lazily from the environment so tests can override it."""
import datetime as dt
import os


def today() -> dt.date:
    v = os.getenv("BP_TODAY")
    return dt.date.fromisoformat(v) if v else dt.date.today()


def database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./data/brandproof.db")


def storage_dir() -> str:
    return os.getenv("BP_STORAGE_DIR", "./data/files")


def secret() -> str:
    return os.getenv("BP_SECRET", "dev-secret-change-me")


def demo_password() -> str:
    return os.getenv("BP_DEMO_PASSWORD", "demo1234")


def seed_enabled() -> bool:
    return os.getenv("BP_SEED", "1") == "1"


def llm_provider_name() -> str:
    """auto | anthropic | gemini | offline"""
    return os.getenv("BP_LLM_PROVIDER", "auto").lower()


def anthropic_key() -> str | None:
    return os.getenv("ANTHROPIC_API_KEY") or None


def gemini_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or None


def anthropic_model() -> str:
    return os.getenv("BP_ANTHROPIC_MODEL", "claude-sonnet-5-5")


def gemini_model() -> str:
    return os.getenv("BP_GEMINI_MODEL", "gemini-3.1-flash-lite")


def cors_origins() -> list[str]:
    return [o.strip() for o in os.getenv("BP_CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]


CONFIDENCE_FLOOR = 0.6  # below this an AI/heuristic finding becomes "Needs human"


def storage_mode() -> str:
    """'db' keeps uploaded files in the database (default with Postgres); 'disk' keeps them in BP_STORAGE_DIR."""
    m = os.getenv("BP_STORAGE", "").lower()
    if m in ("db", "disk"):
        return m
    return "db" if database_url().startswith("postgres") else "disk"

import os


# -------------------------------------------------
# ENV HELPERS
# -------------------------------------------------
def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(f"❌ Missing required env var: {name}")
    return value


# -------------------------------------------------
# TELEGRAM CONFIG
# -------------------------------------------------
TELEGRAM_BOT_TOKEN: str = get_required_env("TELEGRAM_BOT_TOKEN")

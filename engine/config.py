import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")

    CONFIDENCE_LEVEL = float(os.getenv("CONFIDENCE_LEVEL", "0.95"))
    VAR_WINDOW_DAYS = int(os.getenv("VAR_WINDOW_DAYS", "252"))


def get_client():
    import psycopg2

    return psycopg2.connect(
        Config.DATABASE_URL,
        sslmode="require"
    )
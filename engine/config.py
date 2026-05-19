# engine/config.py
# Central configuration — reads from environment variables
# Works locally (.env file) and in cloud (GitHub Secrets)

import os
from dotenv import load_dotenv

# Load .env file if it exists (local development)
# In GitHub Actions, environment variables come from Secrets instead
load_dotenv()

class Config:
    # ClickHouse connection
    CLICKHOUSE_HOST     = os.getenv('CLICKHOUSE_HOST', 'localhost')
    CLICKHOUSE_PORT     = int(os.getenv('CLICKHOUSE_PORT', '9000'))
    CLICKHOUSE_USER     = os.getenv('CLICKHOUSE_USER', 'default')
    CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')
    CLICKHOUSE_SECURE   = os.getenv('CLICKHOUSE_SECURE', 'false').lower() == 'true'

    # Risk parameters
    CONFIDENCE_LEVEL    = float(os.getenv('CONFIDENCE_LEVEL', '0.95'))
    VAR_WINDOW_DAYS     = int(os.getenv('VAR_WINDOW_DAYS', '252'))


def get_client():
    """
    Returns a ClickHouse client using environment configuration.
    Works for both local Docker and ClickHouse Cloud.
    """
    from clickhouse_driver import Client

    return Client(
        host     = Config.CLICKHOUSE_HOST,
        port     = Config.CLICKHOUSE_PORT,
        user     = Config.CLICKHOUSE_USER,
        password = Config.CLICKHOUSE_PASSWORD,
        secure   = Config.CLICKHOUSE_SECURE,
        verify   = False  # for self-signed certs
    )
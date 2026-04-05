import psycopg

from backend.config import settings


def get_conn():
    return psycopg.connect(settings.database_url)

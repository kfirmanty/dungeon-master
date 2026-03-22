"""
Database connection pool setup.

We use psycopg v3 (not the older psycopg2) which has native async support
and a cleaner API. The connection pool maintains a set of reusable connections
to PostgreSQL, avoiding the overhead of connecting/disconnecting per query.
"""

import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector


def get_connection(database_url: str) -> psycopg.Connection:
    """Create a new database connection.

    NOTE: register_vector() is NOT called here. It must be called AFTER
    run_migrations() creates the pgvector extension. If called before the
    extension exists, you get "vector type not found in the database".
    """
    try:
        conn = psycopg.connect(database_url, row_factory=dict_row)
        return conn
    except psycopg.OperationalError:
        raise ConnectionError(
            "Cannot connect to PostgreSQL. Is the database running?\n"
            "  Try: docker compose up -d"
        )


def register_vector_type(conn: psycopg.Connection) -> None:
    """Register the pgvector type with psycopg.

    This teaches psycopg how to serialize Python lists to/from PostgreSQL's
    vector type. Must be called AFTER the vector extension is created
    (i.e., after run_migrations).
    """
    register_vector(conn)

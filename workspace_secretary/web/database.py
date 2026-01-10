"""
Direct PostgreSQL connection for web UI - read-only access.
"""

from typing import Optional
from contextlib import contextmanager
import logging
import psycopg_pool
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        from workspace_secretary.config import load_config

        config = load_config()
        db = config.database.postgres

        conninfo = f"host={db.host} port={db.port} dbname={db.database} user={db.user} password={db.password}"
        _pool = psycopg_pool.ConnectionPool(conninfo, min_size=1, max_size=5)
        logger.info("Web UI database pool initialized")
    return _pool


@contextmanager
def get_conn():
    pool = get_pool()
    with pool.connection() as conn:
        yield conn


def get_inbox_emails(
    folder: str, limit: int, offset: int, unread_only: bool = False
) -> list[dict]:
    sql = """
        SELECT uid, folder, from_addr, subject, 
               LEFT(body_text, 200) as preview, date, is_unread, has_attachments
        FROM emails 
        WHERE folder = %s {unread_filter}
        ORDER BY date DESC 
        LIMIT %s OFFSET %s
    """
    unread_filter = "AND is_unread = true" if unread_only else ""
    sql = sql.format(unread_filter=unread_filter)

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (folder, limit, offset))
            return cur.fetchall()


def get_email(uid: int, folder: str) -> Optional[dict]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM emails WHERE uid = %s AND folder = %s", (uid, folder)
            )
            return cur.fetchone()


def get_thread(uid: int, folder: str) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT message_id, in_reply_to, references_header FROM emails WHERE uid = %s AND folder = %s",
                (uid, folder),
            )
            row = cur.fetchone()
            if not row:
                return []

            message_id = row["message_id"]
            in_reply_to = row["in_reply_to"] or ""
            references = row["references_header"] or ""

            related_ids = set()
            if message_id:
                related_ids.add(message_id)
            for ref in (in_reply_to + " " + references).split():
                if ref:
                    related_ids.add(ref)

            if not related_ids:
                cur.execute(
                    "SELECT * FROM emails WHERE uid = %s AND folder = %s", (uid, folder)
                )
                single = cur.fetchone()
                return [single] if single else []

            cur.execute(
                """
                SELECT * FROM emails 
                WHERE message_id = ANY(%s) OR in_reply_to = ANY(%s)
                ORDER BY date ASC
            """,
                (list(related_ids), list(related_ids)),
            )
            return cur.fetchall()


def search_emails(query: str, folder: str, limit: int) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT uid, folder, from_addr, subject, 
                       LEFT(body_text, 200) as preview, date, is_unread
                FROM emails 
                WHERE folder = %s AND (
                    to_tsvector('english', COALESCE(subject, '') || ' ' || COALESCE(body_text, '')) 
                    @@ plainto_tsquery('english', %s)
                )
                ORDER BY date DESC LIMIT %s
            """,
                (folder, query, limit),
            )
            return cur.fetchall()


def semantic_search(
    query_embedding: list[float], folder: str, limit: int, threshold: float = 0.5
) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT e.uid, e.folder, e.from_addr, e.subject, 
                       LEFT(e.body_text, 200) as preview, e.date, e.is_unread,
                       1 - (emb.embedding <=> %s::vector) as similarity
                FROM email_embeddings emb
                JOIN emails e ON e.uid = emb.uid AND e.folder = emb.folder
                WHERE e.folder = %s AND 1 - (emb.embedding <=> %s::vector) > %s
                ORDER BY similarity DESC LIMIT %s
            """,
                (query_embedding, folder, query_embedding, threshold, limit),
            )
            return cur.fetchall()


def has_embeddings() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM email_embeddings LIMIT 1")
                return cur.fetchone() is not None
    except Exception:
        return False


def find_related_emails(uid: int, folder: str, limit: int = 5) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT embedding FROM email_embeddings WHERE uid = %s AND folder = %s",
                (uid, folder),
            )
            row = cur.fetchone()
            if not row:
                return []

            embedding = row["embedding"]
            cur.execute(
                """
                SELECT e.uid, e.folder, e.from_addr, e.subject, 
                       LEFT(e.body_text, 150) as preview, e.date,
                       1 - (emb.embedding <=> %s::vector) as similarity
                FROM email_embeddings emb
                JOIN emails e ON e.uid = emb.uid AND e.folder = emb.folder
                WHERE NOT (e.uid = %s AND e.folder = %s)
                  AND 1 - (emb.embedding <=> %s::vector) > 0.6
                ORDER BY similarity DESC LIMIT %s
            """,
                (embedding, uid, folder, embedding, limit),
            )
            return cur.fetchall()

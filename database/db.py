import asyncpg
import aiosqlite
import math
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, dsn: Optional[str] = None, sqlite_path: Optional[Path] = None, schema: Optional[str] = None):
        self.dsn = dsn
        self.sqlite_path = sqlite_path or Path("data/kino_bot.db")
        self.schema = schema
        self.pool: Optional[asyncpg.Pool] = None
        self.engine: str = "sqlite"  # "postgres" or "sqlite"

    async def connect(self):
        # 1. Try PostgreSQL first if dsn is provided
        if self.dsn and ("postgres" in self.dsn):
            try:
                async def _init_conn(conn):
                    if self.schema:
                        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema};")
                        await conn.execute(f"SET search_path TO {self.schema}, public;")

                self.pool = await asyncpg.create_pool(
                    dsn=self.dsn,
                    min_size=2,
                    max_size=20,
                    command_timeout=10,
                    init=_init_conn if self.schema else None
                )
                async with self.pool.acquire() as conn:
                    if self.schema:
                        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema};")
                        await conn.execute(f"SET search_path TO {self.schema}, public;")
                    await conn.fetchval("SELECT 1")
                self.engine = "postgres"
                await self._create_tables_postgres()
                logger.info(f"✅ PostgreSQL ma'lumotlar bazasiga muvaffaqiyatli ulandi (schema={self.schema or 'public'}).")
                return
            except Exception as e:
                logger.warning(f"⚠️ PostgreSQL ga ulanib bo'lmadi ({e}). Avtomatik ravishda SQLite rejimiga o'tilmoqda.")
                if self.pool:
                    try:
                        await self.pool.close()
                    except Exception:
                        pass
                self.pool = None

        # 2. Fallback to SQLite
        self.engine = "sqlite"
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        await self._create_tables_sqlite()
        logger.info(f"✅ SQLite ma'lumotlar bazasiga ulandi: {self.sqlite_path}")

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL ulanishi yopildi.")

    async def close(self):
        await self.disconnect()

    async def _create_tables_postgres(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    status VARCHAR(32) DEFAULT 'active',
                    referrer_id BIGINT DEFAULT NULL,
                    referrer_code TEXT DEFAULT NULL,
                    is_premium INTEGER DEFAULT 0,
                    premium_until TIMESTAMPTZ DEFAULT NULL,
                    balance DOUBLE PRECISION DEFAULT 0,
                    joined_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    last_active_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS movies (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(64) UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    file_type VARCHAR(32) DEFAULT 'video',
                    caption TEXT DEFAULT '',
                    quality VARCHAR(64) DEFAULT '720p HD',
                    language VARCHAR(64) DEFAULT 'O‘zbekcha',
                    year VARCHAR(32) DEFAULT '',
                    genre VARCHAR(255) DEFAULT '',
                    views INTEGER DEFAULT 0,
                    downloads INTEGER DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id SERIAL PRIMARY KEY,
                    channel_id VARCHAR(128) DEFAULT '',
                    channel_type VARCHAR(32) DEFAULT 'telegram',
                    name TEXT NOT NULL,
                    username VARCHAR(128) DEFAULT '',
                    invite_link TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    movie_id INTEGER NOT NULL REFERENCES movies (id) ON DELETE CASCADE,
                    downloaded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    action VARCHAR(128) NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    query TEXT NOT NULL,
                    status VARCHAR(32) DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ads (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) DEFAULT '',
                    content_type VARCHAR(32) DEFAULT 'text',
                    file_id TEXT DEFAULT '',
                    text TEXT DEFAULT '',
                    button_text VARCHAR(255) DEFAULT '',
                    button_url TEXT DEFAULT '',
                    views INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    user_id BIGINT PRIMARY KEY,
                    role VARCHAR(32) DEFAULT 'admin',
                    added_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key VARCHAR(128) PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payment_systems (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(128) NOT NULL,
                    details TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    plan_name VARCHAR(128) NOT NULL,
                    amount INTEGER NOT NULL,
                    receipt_file_id TEXT DEFAULT '',
                    status VARCHAR(32) DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS referral_links (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    code VARCHAR(64) UNIQUE NOT NULL,
                    clicks INTEGER DEFAULT 0,
                    joined INTEGER DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_movies_code ON movies(code);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_joined ON users(joined_at);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active_at);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_downloads_time ON downloads(downloaded_at);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_ref_code ON referral_links(code);")

            await conn.execute("""
                INSERT INTO settings (key, value) VALUES ('ad_on_start', '0')
                ON CONFLICT (key) DO NOTHING;
            """)
            await conn.execute("""
                INSERT INTO settings (key, value) VALUES ('ad_on_movie', '0')
                ON CONFLICT (key) DO NOTHING;
            """)

    async def _create_tables_sqlite(self):
        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA foreign_keys=ON;")

            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    status TEXT DEFAULT 'active',
                    referrer_id INTEGER DEFAULT NULL,
                    referrer_code TEXT DEFAULT NULL,
                    is_premium INTEGER DEFAULT 0,
                    premium_until TIMESTAMP DEFAULT NULL,
                    balance REAL DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    file_type TEXT DEFAULT 'video',
                    caption TEXT DEFAULT '',
                    quality TEXT DEFAULT '720p HD',
                    language TEXT DEFAULT 'O‘zbekcha',
                    year TEXT DEFAULT '',
                    genre TEXT DEFAULT '',
                    views INTEGER DEFAULT 0,
                    downloads INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT DEFAULT '',
                    channel_type TEXT DEFAULT 'telegram',
                    name TEXT NOT NULL,
                    username TEXT DEFAULT '',
                    invite_link TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            try:
                await db.execute("ALTER TABLE channels ADD COLUMN channel_type TEXT DEFAULT 'telegram';")
            except Exception:
                pass

            await db.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    movie_id INTEGER NOT NULL,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (movie_id) REFERENCES movies (id) ON DELETE CASCADE
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    query TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS ads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT DEFAULT '',
                    content_type TEXT DEFAULT 'text',
                    file_id TEXT DEFAULT '',
                    text TEXT DEFAULT '',
                    button_text TEXT DEFAULT '',
                    button_url TEXT DEFAULT '',
                    views INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    role TEXT DEFAULT 'admin',
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS payment_systems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    details TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    plan_name TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    receipt_file_id TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS referral_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    code TEXT UNIQUE NOT NULL,
                    clicks INTEGER DEFAULT 0,
                    joined INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            try:
                await db.execute("ALTER TABLE users ADD COLUMN referrer_code TEXT DEFAULT NULL;")
            except Exception:
                pass

            await db.execute("CREATE INDEX IF NOT EXISTS idx_movies_code ON movies(code);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_joined ON users(joined_at);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active_at);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_downloads_time ON downloads(downloaded_at);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ref_code ON referral_links(code);")

            cur = await db.execute("SELECT value FROM settings WHERE key = 'ad_on_start'")
            if not await cur.fetchone():
                await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('ad_on_start', '0')")

            cur = await db.execute("SELECT value FROM settings WHERE key = 'ad_on_movie'")
            if not await cur.fetchone():
                await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('ad_on_movie', '0')")

            await db.commit()

    # ================= USER OPERATIONS =================
    async def add_or_update_user(
        self,
        user_id: int,
        username: Optional[str],
        full_name: str,
        referrer_id: Optional[int] = None,
        referrer_code: Optional[str] = None
    ) -> bool:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT user_id, status FROM users WHERE user_id = $1", user_id)
                if row is None:
                    valid_ref = None
                    if referrer_id and referrer_id != user_id:
                        ref_row = await conn.fetchrow("SELECT user_id FROM users WHERE user_id = $1", referrer_id)
                        if ref_row:
                            valid_ref = referrer_id

                    if referrer_code:
                        ref_link = await conn.fetchrow("SELECT id FROM referral_links WHERE code = $1", referrer_code)
                        if ref_link:
                            await conn.execute("UPDATE referral_links SET joined = joined + 1 WHERE code = $1", referrer_code)

                    await conn.execute("""
                        INSERT INTO users (user_id, username, full_name, referrer_id, referrer_code, status, joined_at, last_active_at)
                        VALUES ($1, $2, $3, $4, $5, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, user_id, username, full_name, valid_ref, referrer_code)

                    await conn.execute("INSERT INTO activity_logs (user_id, action) VALUES ($1, 'join')", user_id)
                    return True
                else:
                    new_status = row["status"]
                    if new_status == 'blocked':
                        new_status = 'active'

                    await conn.execute("""
                        UPDATE users 
                        SET username = $1, full_name = $2, last_active_at = CURRENT_TIMESTAMP, status = $3
                        WHERE user_id = $4
                    """, username, full_name, new_status, user_id)
                    return False
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT user_id, status FROM users WHERE user_id = ?", (user_id,))
                row = await cursor.fetchone()

                if row is None:
                    valid_ref = None
                    if referrer_id and referrer_id != user_id:
                        ref_cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,))
                        if await ref_cursor.fetchone():
                            valid_ref = referrer_id

                    if referrer_code:
                        ref_link_cur = await db.execute("SELECT id FROM referral_links WHERE code = ?", (referrer_code,))
                        if await ref_link_cur.fetchone():
                            await db.execute("UPDATE referral_links SET joined = joined + 1 WHERE code = ?", (referrer_code,))

                    await db.execute("""
                        INSERT INTO users (user_id, username, full_name, referrer_id, referrer_code, status, joined_at, last_active_at)
                        VALUES (?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (user_id, username, full_name, valid_ref, referrer_code))

                    await db.execute("INSERT INTO activity_logs (user_id, action) VALUES (?, 'join')", (user_id,))
                    await db.commit()
                    return True
                else:
                    new_status = row["status"]
                    if new_status == 'blocked':
                        new_status = 'active'

                    await db.execute("""
                        UPDATE users 
                        SET username = ?, full_name = ?, last_active_at = CURRENT_TIMESTAMP, status = ?
                        WHERE user_id = ?
                    """, (username, full_name, new_status, user_id))
                    await db.commit()
                    return False

    async def log_activity(self, user_id: int, action: str):
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE user_id = $1", user_id)
                await conn.execute("INSERT INTO activity_logs (user_id, action) VALUES ($1, $2)", user_id, action)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("UPDATE users SET last_active_at = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
                await db.execute("INSERT INTO activity_logs (user_id, action) VALUES (?, ?)", (user_id, action))
                await db.commit()

    async def set_user_status(self, user_id: int, status: str):
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE users SET status = $1 WHERE user_id = $2", status, user_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
                await db.commit()

    async def toggle_user_ban(self, user_id: int) -> str:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT status FROM users WHERE user_id = $1", user_id)
                if not row:
                    return "not_found"
                new_status = "active" if row["status"] == "banned" else "banned"
                await conn.execute("UPDATE users SET status = $1 WHERE user_id = $2", new_status, user_id)
                return new_status
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("SELECT status FROM users WHERE user_id = ?", (user_id,))
                row = await cur.fetchone()
                if not row:
                    return "not_found"
                new_status = "active" if row[0] == "banned" else "banned"
                await db.execute("UPDATE users SET status = ? WHERE user_id = ?", (new_status, user_id))
                await db.commit()
                return new_status

    async def toggle_user_premium(self, user_id: int) -> int:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT is_premium FROM users WHERE user_id = $1", user_id)
                if not row:
                    return 0
                new_val = 0 if row["is_premium"] == 1 else 1
                await conn.execute("UPDATE users SET is_premium = $1 WHERE user_id = $2", new_val, user_id)
                return new_val
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
                row = await cur.fetchone()
                if not row:
                    return 0
                new_val = 0 if row[0] == 1 else 1
                await db.execute("UPDATE users SET is_premium = ? WHERE user_id = ?", (new_val, user_id))
                await db.commit()
                return new_val

    async def get_premium_users_count(self) -> int:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                val = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_premium = 1")
                return val or 0
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
                row = await cur.fetchone()
                return row[0] if row else 0

    async def get_premium_users_list(self, page: int = 1, limit: int = 10) -> Tuple[List[Dict[str, Any]], int, int]:
        offset = (page - 1) * limit
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                total_count = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_premium = 1") or 0
                rows = await conn.fetch("""
                    SELECT * FROM users 
                    WHERE is_premium = 1
                    ORDER BY joined_at DESC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
                users = [dict(r) for r in rows]
                total_pages = max(1, (total_count + limit - 1) // limit)
                return users, total_count, total_pages
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                count_cur = await db.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
                total_count = (await count_cur.fetchone())[0]

                cur = await db.execute("""
                    SELECT * FROM users 
                    WHERE is_premium = 1
                    ORDER BY joined_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                rows = await cur.fetchall()
                users = [dict(r) for r in rows]
                total_pages = max(1, (total_count + limit - 1) // limit)
                return users, total_count, total_pages

    async def grant_premium(self, user_id: int, days: Optional[int] = None) -> bool:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                user = await self.get_user(user_id)
                if not user:
                    return False
                until = datetime.now() + timedelta(days=days) if days else None
                await conn.execute("UPDATE users SET is_premium = 1, premium_until = $1 WHERE user_id = $2", until, user_id)
                return True
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                user = await self.get_user(user_id)
                if not user:
                    return False
                until = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S') if days else None
                await db.execute("UPDATE users SET is_premium = 1, premium_until = ? WHERE user_id = ?", (until, user_id))
                await db.commit()
                return True

    async def revoke_premium(self, user_id: int) -> bool:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                user = await self.get_user(user_id)
                if not user:
                    return False
                await conn.execute("UPDATE users SET is_premium = 0, premium_until = NULL WHERE user_id = $1", user_id)
                return True
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                user = await self.get_user(user_id)
                if not user:
                    return False
                await db.execute("UPDATE users SET is_premium = 0, premium_until = NULL WHERE user_id = ?", (user_id,))
                await db.commit()
                return True

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_referral_count(self, user_id: int) -> int:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                val = await conn.fetchval("SELECT COUNT(*) FROM users WHERE referrer_id = $1", user_id)
                return val or 0
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_all_user_ids(self, active_only: bool = False) -> List[int]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                if active_only:
                    rows = await conn.fetch("SELECT user_id FROM users WHERE status = 'active'")
                else:
                    rows = await conn.fetch("SELECT user_id FROM users")
                return [r["user_id"] for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                if active_only:
                    cursor = await db.execute("SELECT user_id FROM users WHERE status = 'active'")
                else:
                    cursor = await db.execute("SELECT user_id FROM users")
                rows = await cursor.fetchall()
                return [r[0] for r in rows]

    async def get_users_overview_stats(self) -> Dict[str, int]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                total = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
                active = await conn.fetchval("SELECT COUNT(*) FROM users WHERE status = 'active'") or 0
                left_count = await conn.fetchval("SELECT COUNT(*) FROM users WHERE status = 'blocked'") or 0
                banned = await conn.fetchval("SELECT COUNT(*) FROM users WHERE status = 'banned'") or 0
                premium = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_premium = 1") or 0
                return {
                    "total": total,
                    "active": active,
                    "left": left_count,
                    "banned": banned,
                    "premium": premium
                }
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("SELECT COUNT(*) FROM users")
                total = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM users WHERE status = 'active'")
                active = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM users WHERE status = 'blocked'")
                left_count = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM users WHERE status = 'banned'")
                banned = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
                premium = (await cur.fetchone())[0]

                return {
                    "total": total,
                    "active": active,
                    "left": left_count,
                    "banned": banned,
                    "premium": premium
                }

    async def get_users_list(self, page: int = 1, limit: int = 10, filter_status: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int, int]:
        offset = (page - 1) * limit
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                if filter_status == "blocked":
                    total_count = await conn.fetchval("SELECT COUNT(*) FROM users WHERE status IN ('blocked', 'banned')") or 0
                    rows = await conn.fetch("""
                        SELECT * FROM users 
                        WHERE status IN ('blocked', 'banned')
                        ORDER BY joined_at DESC LIMIT $1 OFFSET $2
                    """, limit, offset)
                else:
                    total_count = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
                    rows = await conn.fetch("""
                        SELECT * FROM users 
                        ORDER BY joined_at DESC LIMIT $1 OFFSET $2
                    """, limit, offset)

                users = [dict(r) for r in rows]
                total_pages = max(1, math.ceil(total_count / limit))
                return users, total_count, total_pages
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                if filter_status == "blocked":
                    count_cur = await db.execute("SELECT COUNT(*) FROM users WHERE status IN ('blocked', 'banned')")
                    total_count = (await count_cur.fetchone())[0]
                    cur = await db.execute("""
                        SELECT * FROM users 
                        WHERE status IN ('blocked', 'banned')
                        ORDER BY joined_at DESC LIMIT ? OFFSET ?
                    """, (limit, offset))
                else:
                    count_cur = await db.execute("SELECT COUNT(*) FROM users")
                    total_count = (await count_cur.fetchone())[0]
                    cur = await db.execute("""
                        SELECT * FROM users 
                        ORDER BY joined_at DESC LIMIT ? OFFSET ?
                    """, (limit, offset))

                rows = await cur.fetchall()
                users = [dict(r) for r in rows]
                total_pages = max(1, math.ceil(total_count / limit))
                return users, total_count, total_pages

    # ================= STATISTICS =================
    async def get_full_statistics(self) -> Dict[str, Any]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                total_users = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
                active_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE status = 'active'") or 0
                blocked_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE status IN ('blocked', 'banned')") or 0

                new_24h = await conn.fetchval("SELECT COUNT(*) FROM users WHERE joined_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'") or 0
                new_7d = await conn.fetchval("SELECT COUNT(*) FROM users WHERE joined_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'") or 0
                new_30d = await conn.fetchval("SELECT COUNT(*) FROM users WHERE joined_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'") or 0

                active_24h = await conn.fetchval("SELECT COUNT(DISTINCT user_id) FROM activity_logs WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'") or 0
                active_7d = await conn.fetchval("SELECT COUNT(DISTINCT user_id) FROM activity_logs WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'") or 0
                active_30d = await conn.fetchval("SELECT COUNT(DISTINCT user_id) FROM activity_logs WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'") or 0

                active_24h = max(active_24h, new_24h)
                active_7d = max(active_7d, new_7d)
                active_30d = max(active_30d, new_30d)

                downloads_24h = await conn.fetchval("SELECT COUNT(*) FROM downloads WHERE downloaded_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'") or 0
                downloads_7d = await conn.fetchval("SELECT COUNT(*) FROM downloads WHERE downloaded_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'") or 0
                downloads_30d = await conn.fetchval("SELECT COUNT(*) FROM downloads WHERE downloaded_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'") or 0

                total_movies = await conn.fetchval("SELECT COUNT(*) FROM movies") or 0

                return {
                    "total_users": total_users,
                    "active_users": active_users,
                    "blocked_users": blocked_users,
                    "new_24h": new_24h,
                    "new_7d": new_7d,
                    "new_30d": new_30d,
                    "active_24h": active_24h,
                    "active_7d": active_7d,
                    "active_30d": active_30d,
                    "downloads_24h": downloads_24h,
                    "downloads_7d": downloads_7d,
                    "downloads_30d": downloads_30d,
                    "total_movies": total_movies,
                }
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("SELECT COUNT(*) FROM users")
                total_users = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM users WHERE status = 'active'")
                active_users = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM users WHERE status IN ('blocked', 'banned')")
                blocked_users = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM users WHERE joined_at >= datetime('now', '-1 day')")
                new_24h = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM users WHERE joined_at >= datetime('now', '-7 days')")
                new_7d = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM users WHERE joined_at >= datetime('now', '-30 days')")
                new_30d = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(DISTINCT user_id) FROM activity_logs WHERE created_at >= datetime('now', '-1 day')")
                active_24h = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(DISTINCT user_id) FROM activity_logs WHERE created_at >= datetime('now', '-7 days')")
                active_7d = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(DISTINCT user_id) FROM activity_logs WHERE created_at >= datetime('now', '-30 days')")
                active_30d = (await cur.fetchone())[0]

                active_24h = max(active_24h, new_24h)
                active_7d = max(active_7d, new_7d)
                active_30d = max(active_30d, new_30d)

                cur = await db.execute("SELECT COUNT(*) FROM downloads WHERE downloaded_at >= datetime('now', '-1 day')")
                downloads_24h = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM downloads WHERE downloaded_at >= datetime('now', '-7 days')")
                downloads_7d = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM downloads WHERE downloaded_at >= datetime('now', '-30 days')")
                downloads_30d = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM movies")
                total_movies = (await cur.fetchone())[0]

                return {
                    "total_users": total_users,
                    "active_users": active_users,
                    "blocked_users": blocked_users,
                    "new_24h": new_24h,
                    "new_7d": new_7d,
                    "new_30d": new_30d,
                    "active_24h": active_24h,
                    "active_7d": active_7d,
                    "active_30d": active_30d,
                    "downloads_24h": downloads_24h,
                    "downloads_7d": downloads_7d,
                    "downloads_30d": downloads_30d,
                    "total_movies": total_movies,
                }

    # ================= REKLAMA (ADS) =================
    async def get_ads_stats(self) -> Dict[str, Any]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                total_ads = await conn.fetchval("SELECT COUNT(*) FROM ads") or 0
                active_ads = await conn.fetchval("SELECT COUNT(*) FROM ads WHERE is_active = 1") or 0
                total_views = await conn.fetchval("SELECT COALESCE(SUM(views), 0) FROM ads") or 0

                start_val = await conn.fetchval("SELECT value FROM settings WHERE key = 'ad_on_start'")
                start_enabled = (start_val == "1") if start_val else False

                movie_val = await conn.fetchval("SELECT value FROM settings WHERE key = 'ad_on_movie'")
                movie_enabled = (movie_val == "1") if movie_val else False

                return {
                    "total_ads": total_ads,
                    "active_ads": active_ads,
                    "total_views": total_views,
                    "start_enabled": start_enabled,
                    "movie_enabled": movie_enabled
                }
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("SELECT COUNT(*) FROM ads")
                total_ads = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM ads WHERE is_active = 1")
                active_ads = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COALESCE(SUM(views), 0) FROM ads")
                total_views = (await cur.fetchone())[0]

                cur = await db.execute("SELECT value FROM settings WHERE key = 'ad_on_start'")
                row = await cur.fetchone()
                start_enabled = (row[0] == "1") if row else False

                cur = await db.execute("SELECT value FROM settings WHERE key = 'ad_on_movie'")
                row = await cur.fetchone()
                movie_enabled = (row[0] == "1") if row else False

                return {
                    "total_ads": total_ads,
                    "active_ads": active_ads,
                    "total_views": total_views,
                    "start_enabled": start_enabled,
                    "movie_enabled": movie_enabled
                }

    async def toggle_ad_setting(self, setting_key: str) -> bool:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                current_val = await conn.fetchval("SELECT value FROM settings WHERE key = $1", setting_key) or "0"
                new_val = "0" if current_val == "1" else "1"
                await conn.execute("""
                    INSERT INTO settings (key, value) VALUES ($1, $2)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """, setting_key, new_val)
                return new_val == "1"
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("SELECT value FROM settings WHERE key = ?", (setting_key,))
                row = await cur.fetchone()
                current_val = row[0] if row else "0"
                new_val = "0" if current_val == "1" else "1"
                await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (setting_key, new_val))
                await db.commit()
                return new_val == "1"

    async def add_ad(self, text: str, content_type: str = "text", file_id: str = "", button_text: str = "", button_url: str = "") -> int:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    INSERT INTO ads (text, content_type, file_id, button_text, button_url, is_active, views)
                    VALUES ($1, $2, $3, $4, $5, 1, 0)
                    RETURNING id
                """, text, content_type, file_id, button_text, button_url)
                return row["id"]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("""
                    INSERT INTO ads (text, content_type, file_id, button_text, button_url, is_active, views)
                    VALUES (?, ?, ?, ?, ?, 1, 0)
                """, (text, content_type, file_id, button_text, button_url))
                await db.commit()
                return cur.lastrowid

    async def get_ads_list(self, page: int = 1, limit: int = 10) -> Tuple[List[Dict[str, Any]], int, int]:
        offset = (page - 1) * limit
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                total_count = await conn.fetchval("SELECT COUNT(*) FROM ads") or 0
                rows = await conn.fetch("SELECT * FROM ads ORDER BY id DESC LIMIT $1 OFFSET $2", limit, offset)
                ads = [dict(r) for r in rows]
                total_pages = max(1, math.ceil(total_count / limit))
                return ads, total_count, total_pages
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                count_cur = await db.execute("SELECT COUNT(*) FROM ads")
                total_count = (await count_cur.fetchone())[0]

                cur = await db.execute("SELECT * FROM ads ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
                rows = await cur.fetchall()
                ads = [dict(r) for r in rows]
                total_pages = max(1, math.ceil(total_count / limit))
                return ads, total_count, total_pages

    async def toggle_ad_active(self, ad_id: int) -> int:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                is_active = await conn.fetchval("SELECT is_active FROM ads WHERE id = $1", ad_id)
                if is_active is None:
                    return 0
                new_val = 0 if is_active == 1 else 1
                await conn.execute("UPDATE ads SET is_active = $1 WHERE id = $2", new_val, ad_id)
                return new_val
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("SELECT is_active FROM ads WHERE id = ?", (ad_id,))
                row = await cur.fetchone()
                if not row:
                    return 0
                new_val = 0 if row[0] == 1 else 1
                await db.execute("UPDATE ads SET is_active = ? WHERE id = ?", (new_val, ad_id))
                await db.commit()
                return new_val

    async def delete_ad(self, ad_id: int) -> bool:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM ads WHERE id = $1", ad_id)
                return res != "DELETE 0"
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
                await db.commit()
                return cur.rowcount > 0

    async def get_active_ad(self) -> Optional[Dict[str, Any]]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM ads WHERE is_active = 1 ORDER BY RANDOM() LIMIT 1")
                if row:
                    ad = dict(row)
                    await conn.execute("UPDATE ads SET views = views + 1 WHERE id = $1", ad["id"])
                    return ad
                return None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cur = await db.execute("SELECT * FROM ads WHERE is_active = 1 ORDER BY RANDOM() LIMIT 1")
                row = await cur.fetchone()
                if row:
                    ad = dict(row)
                    await db.execute("UPDATE ads SET views = views + 1 WHERE id = ?", (ad["id"],))
                    await db.commit()
                    return ad
                return None

    # ================= MOVIES =================
    async def add_movie(self, code: str, title: str, file_id: str, file_type: str = 'video',
                        caption: str = '', quality: str = '720p HD', language: str = 'O‘zbekcha',
                        year: str = '', genre: str = '') -> int:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    INSERT INTO movies (code, title, file_id, file_type, caption, quality, language, year, genre)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                """, str(code).strip(), title.strip(), file_id, file_type, caption, quality, language, year, genre)
                return row["id"]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    INSERT INTO movies (code, title, file_id, file_type, caption, quality, language, year, genre)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (str(code).strip(), title.strip(), file_id, file_type, caption, quality, language, year, genre))
                await db.commit()
                return cursor.lastrowid

    async def update_movie(self, movie_id: int, **fields) -> bool:
        if not fields:
            return False
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                set_clauses = [f"{k} = ${i+1}" for i, k in enumerate(fields.keys())]
                values = list(fields.values()) + [movie_id]
                sql = f"UPDATE movies SET {', '.join(set_clauses)} WHERE id = ${len(values)}"
                res = await conn.execute(sql, *values)
                return res != "UPDATE 0"
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
                values = list(fields.values()) + [movie_id]
                await db.execute(f"UPDATE movies SET {set_clause} WHERE id = ?", values)
                await db.commit()
                return True

    async def get_movie_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM movies WHERE code = $1 OR code = $2",
                    str(code).strip(), f"K{code}".strip()
                )
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM movies WHERE code = ? OR code = ?", (str(code).strip(), f"K{code}".strip()))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_movie_by_id(self, movie_id: int) -> Optional[Dict[str, Any]]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM movies WHERE id = $1", movie_id)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM movies WHERE id = ?", (movie_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def search_movies(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                pattern = f"%{query}%"
                rows = await conn.fetch("""
                    SELECT * FROM movies 
                    WHERE title ILIKE $1 OR code ILIKE $1 OR genre ILIKE $1 
                    ORDER BY downloads DESC LIMIT $2
                """, pattern, limit)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM movies 
                    WHERE title LIKE ? OR code LIKE ? OR genre LIKE ? 
                    ORDER BY downloads DESC LIMIT ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_movies_list(self, page: int = 1, limit: int = 10) -> Tuple[List[Dict[str, Any]], int, int]:
        offset = (page - 1) * limit
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                total_count = await conn.fetchval("SELECT COUNT(*) FROM movies") or 0
                rows = await conn.fetch("SELECT * FROM movies ORDER BY id DESC LIMIT $1 OFFSET $2", limit, offset)
                movies = [dict(r) for r in rows]
                total_pages = max(1, math.ceil(total_count / limit))
                return movies, total_count, total_pages
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                count_cur = await db.execute("SELECT COUNT(*) FROM movies")
                total_count = (await count_cur.fetchone())[0]
                cur = await db.execute("SELECT * FROM movies ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
                rows = await cur.fetchall()
                movies = [dict(r) for r in rows]
                total_pages = max(1, math.ceil(total_count / limit))
                return movies, total_count, total_pages

    async def get_latest_movies(self, limit: int = 10) -> List[Dict[str, Any]]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM movies ORDER BY id DESC LIMIT $1", limit)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM movies ORDER BY id DESC LIMIT ?", (limit,))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_top_movies(self, limit: int = 10) -> List[Dict[str, Any]]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM movies ORDER BY downloads DESC, views DESC LIMIT $1", limit)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM movies ORDER BY downloads DESC, views DESC LIMIT ?", (limit,))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_random_movie(self) -> Optional[Dict[str, Any]]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM movies ORDER BY RANDOM() LIMIT 1")
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM movies ORDER BY RANDOM() LIMIT 1")
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def record_download(self, user_id: int, movie_id: int):
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE movies SET downloads = downloads + 1, views = views + 1 WHERE id = $1", movie_id)
                await conn.execute("INSERT INTO downloads (user_id, movie_id) VALUES ($1, $2)", user_id, movie_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("UPDATE movies SET downloads = downloads + 1, views = views + 1 WHERE id = ?", (movie_id,))
                await db.execute("INSERT INTO downloads (user_id, movie_id) VALUES (?, ?)", (user_id, movie_id))
                await db.commit()

    async def delete_movie(self, code_or_id: str) -> bool:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                if str(code_or_id).isdigit():
                    res = await conn.execute("DELETE FROM movies WHERE id = $1 OR code = $2", int(code_or_id), str(code_or_id))
                else:
                    res = await conn.execute("DELETE FROM movies WHERE code = $1", str(code_or_id))
                return res != "DELETE 0"
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                if str(code_or_id).isdigit():
                    cursor = await db.execute("DELETE FROM movies WHERE id = ? OR code = ?", (int(code_or_id), str(code_or_id)))
                else:
                    cursor = await db.execute("DELETE FROM movies WHERE code = ?", (str(code_or_id),))
                await db.commit()
                return cursor.rowcount > 0

    async def get_next_available_code(self) -> str:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT code FROM movies ORDER BY id DESC LIMIT 100")
                max_num = 0
                for r in rows:
                    c = str(r["code"]).strip()
                    if c.isdigit():
                        max_num = max(max_num, int(c))
                return str(max_num + 1 if max_num > 0 else 1)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT code FROM movies ORDER BY id DESC LIMIT 100")
                rows = await cursor.fetchall()
                max_num = 0
                for r in rows:
                    c = str(r[0]).strip()
                    if c.isdigit():
                        max_num = max(max_num, int(c))
                return str(max_num + 1 if max_num > 0 else 1)

    # ================= CHANNELS (MAJBURIIY OBUNA) =================
    async def add_channel(self, name: str, invite_link: str, channel_id: str = '', username: str = '', channel_type: str = 'telegram') -> bool:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                try:
                    await conn.execute("""
                        INSERT INTO channels (channel_id, channel_type, name, username, invite_link, is_active)
                        VALUES ($1, $2, $3, $4, $5, 1)
                    """, str(channel_id), channel_type, name, username, invite_link)
                    return True
                except Exception:
                    return False
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                try:
                    await db.execute("""
                        INSERT INTO channels (channel_id, channel_type, name, username, invite_link, is_active)
                        VALUES (?, ?, ?, ?, ?, 1)
                    """, (str(channel_id), channel_type, name, username, invite_link))
                    await db.commit()
                    return True
                except Exception:
                    return False

    async def get_channels(self, active_only: bool = True) -> List[Dict[str, Any]]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                if active_only:
                    rows = await conn.fetch("SELECT * FROM channels WHERE is_active = 1")
                else:
                    rows = await conn.fetch("SELECT * FROM channels")
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                if active_only:
                    cursor = await db.execute("SELECT * FROM channels WHERE is_active = 1")
                else:
                    cursor = await db.execute("SELECT * FROM channels")
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def delete_channel(self, channel_db_id: int) -> bool:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM channels WHERE id = $1", channel_db_id)
                return res != "DELETE 0"
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM channels WHERE id = ?", (channel_db_id,))
                await db.commit()
                return cursor.rowcount > 0

    async def toggle_channel_active(self, channel_db_id: int) -> int:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                is_active = await conn.fetchval("SELECT is_active FROM channels WHERE id = $1", channel_db_id)
                if is_active is None:
                    return 0
                new_val = 0 if is_active == 1 else 1
                await conn.execute("UPDATE channels SET is_active = $1 WHERE id = $2", new_val, channel_db_id)
                return new_val
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("SELECT is_active FROM channels WHERE id = ?", (channel_db_id,))
                row = await cur.fetchone()
                if not row:
                    return 0
                new_val = 0 if row[0] == 1 else 1
                await db.execute("UPDATE channels SET is_active = ? WHERE id = ?", (new_val, channel_db_id))
                await db.commit()
                return new_val

    # ================= REQUESTS (SO'ROVLAR) =================
    async def add_request(self, user_id: int, query: str) -> int:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    INSERT INTO requests (user_id, query, status) VALUES ($1, $2, 'pending')
                    RETURNING id
                """, user_id, query)
                return row["id"]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    INSERT INTO requests (user_id, query, status) VALUES (?, ?, 'pending')
                """, (user_id, query))
                await db.commit()
                return cursor.lastrowid

    async def get_requests(self, status: str = 'pending', limit: int = 20) -> List[Dict[str, Any]]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT r.*, u.full_name, u.username 
                    FROM requests r
                    LEFT JOIN users u ON r.user_id = u.user_id
                    WHERE r.status = $1
                    ORDER BY r.id DESC LIMIT $2
                """, status, limit)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT r.*, u.full_name, u.username 
                    FROM requests r
                    LEFT JOIN users u ON r.user_id = u.user_id
                    WHERE r.status = ?
                    ORDER BY r.id DESC LIMIT ?
                """, (status, limit))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def resolve_request(self, request_id: int, status: str = 'resolved') -> bool:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                res = await conn.execute("UPDATE requests SET status = $1 WHERE id = $2", status, request_id)
                return res != "UPDATE 0"
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("UPDATE requests SET status = ? WHERE id = ?", (status, request_id))
                await db.commit()
                return cursor.rowcount > 0

    # ================= ADMINS =================
    async def add_admin(self, user_id: int, role: str = 'admin') -> bool:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                try:
                    await conn.execute("""
                        INSERT INTO admins (user_id, role) VALUES ($1, $2)
                        ON CONFLICT (user_id) DO UPDATE SET role = EXCLUDED.role
                    """, user_id, role)
                    return True
                except Exception:
                    return False
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                try:
                    await db.execute("INSERT OR REPLACE INTO admins (user_id, role) VALUES (?, ?)", (user_id, role))
                    await db.commit()
                    return True
                except Exception:
                    return False

    async def remove_admin(self, user_id: int) -> bool:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM admins WHERE user_id = $1", user_id)
                return res != "DELETE 0"
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
                await db.commit()
                return cursor.rowcount > 0

    async def get_admins(self) -> List[int]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT user_id FROM admins")
                return [r["user_id"] for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT user_id FROM admins")
                rows = await cursor.fetchall()
                return [r[0] for r in rows]

    # ================= SETTINGS / TEXTS =================
    async def get_setting(self, key: str, default: str = '') -> str:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                val = await conn.fetchval("SELECT value FROM settings WHERE key = $1", key)
                return val if val is not None else default
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
                row = await cursor.fetchone()
                return row[0] if row else default

    async def set_setting(self, key: str, value: str):
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO settings (key, value) VALUES ($1, $2)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """, key, str(value))
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
                await db.commit()

    async def get_bot_text(self, key: str, default: str = '') -> str:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                val = await conn.fetchval("SELECT value FROM settings WHERE key = $1", f"text_{key}")
                if val is not None:
                    return val
                from kino_bot.config import DEFAULT_TEXTS
                return DEFAULT_TEXTS.get(key, default)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (f"text_{key}",))
                row = await cursor.fetchone()
                if row:
                    return row[0]
                from kino_bot.config import DEFAULT_TEXTS
                return DEFAULT_TEXTS.get(key, default)

    async def set_bot_text(self, key: str, value: str):
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO settings (key, value) VALUES ($1, $2)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """, f"text_{key}", str(value))
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"text_{key}", str(value)))
                await db.commit()

    async def reset_bot_text(self, key: str):
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM settings WHERE key = $1", f"text_{key}")
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("DELETE FROM settings WHERE key = ?", (f"text_{key}",))
                await db.commit()

    async def reset_all_bot_texts(self):
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM settings WHERE key LIKE 'text_%'")
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("DELETE FROM settings WHERE key LIKE 'text_%'")
                await db.commit()

    # ================= PAYMENT METHODS =================
    async def get_payment_systems(self) -> List[Dict[str, Any]]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM payment_systems WHERE is_active = 1")
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM payment_systems WHERE is_active = 1")
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def add_payment_system(self, name: str, details: str):
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                await conn.execute("INSERT INTO payment_systems (name, details) VALUES ($1, $2)", name, details)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("INSERT INTO payment_systems (name, details) VALUES (?, ?)", (name, details))
                await db.commit()

    async def delete_payment_system(self, sys_id: int):
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM payment_systems WHERE id = $1", sys_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("DELETE FROM payment_systems WHERE id = ?", (sys_id,))
                await db.commit()

    # ================= REFERRAL LINKS =================
    async def create_referral_link(self, name: str, code: str) -> int:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    INSERT INTO referral_links (name, code) VALUES ($1, $2)
                    RETURNING id
                """, name, code)
                return row["id"]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("INSERT INTO referral_links (name, code) VALUES (?, ?)", (name, code))
                await db.commit()
                return cur.lastrowid

    async def get_referral_links(self, page: int = 1, limit: int = 5) -> Tuple[List[Dict[str, Any]], int, int]:
        offset = (page - 1) * limit
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                total_count = await conn.fetchval("SELECT COUNT(*) FROM referral_links") or 0
                rows = await conn.fetch("""
                    SELECT * FROM referral_links
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
                links = [dict(r) for r in rows]
                total_pages = max(1, (total_count + limit - 1) // limit)
                return links, total_count, total_pages
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                count_cur = await db.execute("SELECT COUNT(*) FROM referral_links")
                total_count = (await count_cur.fetchone())[0]

                cur = await db.execute("""
                    SELECT * FROM referral_links
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                rows = await cur.fetchall()
                links = [dict(r) for r in rows]
                total_pages = max(1, (total_count + limit - 1) // limit)
                return links, total_count, total_pages

    async def get_total_referral_stats(self) -> Tuple[int, int]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT COUNT(*) as count, COALESCE(SUM(joined), 0) as joined FROM referral_links")
                links_count = row["count"] if row else 0
                users_count = int(row["joined"]) if row else 0
                return links_count, users_count
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(joined), 0) FROM referral_links")
                row = await cur.fetchone()
                links_count = row[0] if row else 0
                users_count = row[1] if row else 0
                return links_count, users_count

    async def get_referral_link_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM referral_links WHERE code = $1", code)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cur = await db.execute("SELECT * FROM referral_links WHERE code = ?", (code,))
                row = await cur.fetchone()
                return dict(row) if row else None

    async def delete_referral_link(self, link_id: int) -> bool:
        if self.engine == "postgres":
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM referral_links WHERE id = $1", link_id)
                return res != "DELETE 0"
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cur = await db.execute("DELETE FROM referral_links WHERE id = ?", (link_id,))
                await db.commit()
                return cur.rowcount > 0



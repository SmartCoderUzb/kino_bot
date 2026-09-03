import asyncio
import sqlite3
import asyncpg
from pathlib import Path
from kino_bot.config import DATABASE_URL

SQLITE_PATH = Path("data/kino_bot.db")


async def migrate():
    if not SQLITE_PATH.exists():
        print(f"❌ SQLite fayli topilmadi: {SQLITE_PATH}")
        return

    print("🚀 SQLite -> PostgreSQL migratsiyasi boshlandi...")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    s_cur = sqlite_conn.cursor()

    pg_pool = await asyncpg.create_pool(DATABASE_URL)

    from kino_bot.database.db import Database
    db = Database(DATABASE_URL)
    db.pool = pg_pool
    await db.create_tables()

    async with pg_pool.acquire() as pg:
        # 1. Migrate Users
        try:
            s_cur.execute("SELECT * FROM users")
            users = s_cur.fetchall()
            print(f"👥 Foydalanuvchilar: {len(users)} ta topildi.")
            for u in users:
                await pg.execute("""
                    INSERT INTO users (user_id, username, full_name, status, referrer_id, referrer_code, is_premium, balance)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (user_id) DO NOTHING
                """, u["user_id"], u["username"], u["full_name"], u["status"], u["referrer_id"],
                   u["referrer_code"] if "referrer_code" in u.keys() else None,
                   u["is_premium"], u["balance"] if "balance" in u.keys() else 0.0)
        except Exception as e:
            print(f"⚠️ Users ko'chirishda xatolik: {e}")

        # 2. Migrate Movies
        try:
            s_cur.execute("SELECT * FROM movies")
            movies = s_cur.fetchall()
            print(f"🎬 Kinolar: {len(movies)} ta topildi.")
            for m in movies:
                await pg.execute("""
                    INSERT INTO movies (code, title, file_id, file_type, caption, quality, language, year, genre, views, downloads)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (code) DO NOTHING
                """, str(m["code"]), m["title"], m["file_id"], m["file_type"], m["caption"],
                   m["quality"], m["language"], m["year"], m["genre"], m["views"], m["downloads"])
        except Exception as e:
            print(f"⚠️ Movies ko'chirishda xatolik: {e}")

        # 3. Migrate Channels
        try:
            s_cur.execute("SELECT * FROM channels")
            channels = s_cur.fetchall()
            print(f"📢 Kanallar: {len(channels)} ta topildi.")
            for ch in channels:
                ch_type = ch["channel_type"] if "channel_type" in ch.keys() else "telegram"
                await pg.execute("""
                    INSERT INTO channels (channel_id, channel_type, name, username, invite_link, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, str(ch["channel_id"]), ch_type, ch["name"], ch["username"], ch["invite_link"], ch["is_active"])
        except Exception as e:
            print(f"⚠️ Channels ko'chirishda xatolik: {e}")

        # 4. Migrate Settings
        try:
            s_cur.execute("SELECT * FROM settings")
            settings = s_cur.fetchall()
            print(f"⚙️ Sozlamalar: {len(settings)} ta topildi.")
            for st in settings:
                await pg.execute("""
                    INSERT INTO settings (key, value)
                    VALUES ($1, $2)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """, st["key"], st["value"])
        except Exception as e:
            print(f"⚠️ Settings ko'chirishda xatolik: {e}")

    await pg_pool.close()
    sqlite_conn.close()
    print("✅ Barcha ma'lumotlar PostgreSQL ga muvaffaqiyatli ko'chirildi!")


if __name__ == "__main__":
    asyncio.run(migrate())

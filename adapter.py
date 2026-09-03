import os
import sys
import logging
from pathlib import Path
from typing import Optional, Tuple
from aiogram import Dispatcher, Router
from redis.asyncio import Redis

logger = logging.getLogger("KinoBotAdapter")

from kino_bot.database.db import Database
from kino_bot.middlewares.user_tracker import UserTrackerMiddleware
from kino_bot.middlewares.check_sub import CheckSubscriptionMiddleware
from kino_bot.middlewares.throttling import ThrottlingMiddleware
from kino_bot.handlers.admin import (
    main as admin_main,
    movies as admin_movies,
    channels as admin_channels,
    broadcast as admin_broadcast,
    ads as admin_ads,
    users as admin_users,
    posts as admin_posts,
    requests as admin_requests,
    settings as admin_settings
)
from kino_bot.handlers.user import start as user_start, movies as user_movies

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/kino_bot"
)
REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0"
)

_EVENT_OBSERVERS = [
    'message', 'edited_message', 'channel_post', 'edited_channel_post',
    'inline_query', 'chosen_inline_result', 'callback_query', 'shipping_query',
    'pre_checkout_query', 'poll', 'poll_answer', 'my_chat_member',
    'chat_member', 'chat_join_request', 'message_reaction',
    'message_reaction_count', 'chat_boost', 'removed_chat_boost', 'errors'
]


def clone_router(src: Router) -> Router:
    dest = Router(name=src.name)
    for obs_name in _EVENT_OBSERVERS:
        src_obs = getattr(src, obs_name, None)
        if src_obs and hasattr(src_obs, 'handlers'):
            dest_obs = getattr(dest, obs_name)
            for h in src_obs.handlers:
                raw_filters = [f.callback for f in h.filters]
                dest_obs.register(h.callback, *raw_filters, flags=h.flags)
    for sub in src.sub_routers:
        dest.include_router(clone_router(sub))
    return dest


def create_kino_admin_router() -> Router:
    root = Router(name="kino_admin_root")
    for mod in [
        admin_main, admin_movies, admin_channels, admin_broadcast,
        admin_ads, admin_users, admin_posts, admin_requests, admin_settings
    ]:
        root.include_router(clone_router(mod.router))
    return root


def create_kino_user_router() -> Router:
    root = Router(name="kino_user_root")
    for mod in [user_start, user_movies]:
        root.include_router(clone_router(mod.router))
    return root


async def init_kino_subbot(
    dp: Dispatcher,
    bot_id: int,
    owner_id: int = 0
) -> Tuple[Database, Optional[Redis]]:
    """
    Kino botini PostgreSQL (schema=kino_bot_{bot_id}) va Redis bilan ulaydi.
    PostgreSQL va Redis bo'lmaganda avtomatik ravishda SQLite va Memory rejimiga o'tadi.
    """
    db_dir = Path("data/kino_bots")
    db_dir.mkdir(parents=True, exist_ok=True)
    sqlite_fallback_path = db_dir / f"kino_{bot_id}.db"

    # 1. Database (PostgreSQL with Schema per Bot + SQLite fallback)
    schema_name = f"kino_bot_{bot_id}"
    db = Database(
        dsn=DATABASE_URL,
        schema=schema_name,
        sqlite_path=sqlite_fallback_path
    )
    await db.connect()
    logger.info(f"✅ [KinoBot {bot_id}] Ma'lumotlar bazasi ({db.engine.upper()}) muvaffaqiyatli ishga tushdi.")

    # 2. Redis Connection
    redis_client = None
    try:
        redis_client = Redis.from_url(REDIS_URL)
        await redis_client.ping()
        logger.info(f"✅ [KinoBot {bot_id}] Redis kesh va throttling muvaffaqiyatli ulandi.")
    except Exception as e:
        logger.warning(f"⚠️ [KinoBot {bot_id}] Redis ulanishida ogohlantirish ({e}).")
        if redis_client:
            try:
                await redis_client.aclose()
            except Exception:
                pass
        redis_client = None

    # 3. Bot egasini avtomatik admin qilish
    if owner_id:
        try:
            await db.add_or_update_user(
                user_id=owner_id,
                username="",
                full_name="Bot Egasi"
            )
            await db.add_admin(owner_id)
        except Exception as e:
            logger.warning(f"Could not auto-add owner {owner_id} as admin: {e}")

    # 4. Globals for handlers
    dp["db"] = db
    dp["redis"] = redis_client
    dp["bot_id"] = bot_id
    dp["owner_id"] = owner_id

    # 5. Middlewares
    if redis_client:
        throttling = ThrottlingMiddleware(redis=redis_client)
        dp.message.outer_middleware(throttling)
        dp.callback_query.outer_middleware(throttling)

    user_tracker = UserTrackerMiddleware(db, owner_id=owner_id)
    check_sub = CheckSubscriptionMiddleware(db, redis=redis_client)

    dp.message.outer_middleware(user_tracker)
    dp.callback_query.outer_middleware(user_tracker)

    dp.message.middleware(check_sub)
    dp.callback_query.middleware(check_sub)

    # 6. Routers
    dp.include_router(create_kino_admin_router())
    dp.include_router(create_kino_user_router())

    return db, redis_client

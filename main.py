import os
import sys
import types
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if 'kino_bot' not in sys.modules:
    pkg = types.ModuleType('kino_bot')
    pkg.__path__ = [str(BASE_DIR)]
    sys.modules['kino_bot'] = pkg

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from kino_bot.config import BOT_TOKEN, DATABASE_URL, DB_PATH, REDIS_URL
from kino_bot.database.db import Database
from kino_bot.middlewares.user_tracker import UserTrackerMiddleware
from kino_bot.middlewares.check_sub import CheckSubscriptionMiddleware
from kino_bot.middlewares.throttling import ThrottlingMiddleware
from kino_bot.handlers.admin import admin_router
from kino_bot.handlers.user import user_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi! Iltimos, .env faylida BOT_TOKEN ni belgilang.")
        return

    # Initialize Database (PostgreSQL with SQLite fallback)
    schema = os.getenv("DB_SCHEMA")
    db = Database(DATABASE_URL, sqlite_path=DB_PATH, schema=schema)
    try:
        await db.connect()
    except Exception as e:
        logger.error(f"Ma'lumotlar bazasiga ulanishda xatolik: {e}")
        return


    # Initialize Redis & Storage
    redis_client = None
    try:
        redis_client = Redis.from_url(REDIS_URL)
        await redis_client.ping()
        from aiogram.fsm.storage.redis import DefaultKeyBuilder
        key_builder = DefaultKeyBuilder(with_bot_id=True, prefix=schema or "fsm_kino")
        storage = RedisStorage(redis=redis_client, key_builder=key_builder)
        logger.info("Redis xotirasi (RedisStorage) muvaffaqiyatli ishga tushdi.")
    except Exception as e:
        logger.warning(f"Redis ulanishida xatolik: {e}. Xotira rejimiga (MemoryStorage) o'tilmoqda.")
        redis_client = None
        storage = MemoryStorage()

    # Initialize Bot & Dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)

    # Pass db and redis globally to all handlers and middlewares
    dp["db"] = db
    dp["redis"] = redis_client

    # Register Middlewares
    user_tracker = UserTrackerMiddleware(db)
    check_sub = CheckSubscriptionMiddleware(db, redis=redis_client)

    if redis_client:
        throttling = ThrottlingMiddleware(redis=redis_client)
        dp.message.outer_middleware(throttling)
        dp.callback_query.outer_middleware(throttling)

    dp.message.outer_middleware(user_tracker)
    dp.callback_query.outer_middleware(user_tracker)

    dp.message.middleware(check_sub)
    dp.callback_query.middleware(check_sub)

    # Register Routers (Admin first, then User)
    dp.include_router(admin_router)
    dp.include_router(user_router)

    bot_info = await bot.get_me()
    logger.info(f"Bot muvaffaqiyatli ishga tushdi: @{bot_info.username} (ID: {bot_info.id})")
    print(f"🚀 Bot @{bot_info.username} ishga tushdi!")

    bot_id = os.getenv("BOT_ID", "1")
    webhook_url = os.getenv("WEBHOOK_URL")
    webhook_host = os.getenv("WEBHOOK_HOST")
    webhook_path = os.getenv("WEBHOOK_PATH", f"/webhook/bot/{bot_id}")
    if not webhook_url and webhook_host:
        webhook_url = f"{webhook_host.rstrip('/')}{webhook_path}"

    webapp_host = os.getenv("WEBAPP_HOST", "127.0.0.1")
    if bot_id and bot_id.isdigit():
        webapp_port = 10000 + int(bot_id)
    else:
        webapp_port = int(os.getenv("WEBAPP_PORT", "8100"))

    if webhook_url:
        logger.info(f"🌐 Webhook rejimida ishga tushmoqda: {webhook_url} ({webapp_host}:{webapp_port})")
        app = web.Application()
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=webhook_path)
        setup_application(app, dp, bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=webapp_host, port=webapp_port)
        await site.start()

        await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=dp.resolve_used_update_types()
        )
        logger.info(f"✅ Webhook server faol: {webapp_host}:{webapp_port}{webhook_path}")

        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            try:
                await bot.delete_webhook()
            except Exception:
                pass
            await runner.cleanup()
            await bot.session.close()
            await db.disconnect()
            if redis_client:
                await redis_client.aclose()
    else:
        # Fallback polling mode
        logger.info("ℹ️ WEBHOOK_URL sozlanmagan. Polling rejimida ishga tushmoqda...")
        await bot.delete_webhook(drop_pending_updates=True)
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        finally:
            await bot.session.close()
            await db.disconnect()
            if redis_client:
                await redis_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")


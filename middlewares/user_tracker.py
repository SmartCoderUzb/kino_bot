from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, User
from typing import Callable, Dict, Any, Awaitable
from kino_bot.database.db import Database
from kino_bot.config import ADMINS

class UserTrackerMiddleware(BaseMiddleware):
    def __init__(self, db: Database, owner_id: int = 0):
        self.db = db
        self.owner_id = owner_id
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")
        is_admin = False

        if user and not user.is_bot:
            # Check for referral in /start
            referrer_id = None
            referrer_code = None
            if isinstance(event, Message) and event.text and event.text.startswith("/start"):
                parts = event.text.split()
                if len(parts) > 1:
                    arg = parts[1].strip()
                    if arg.startswith("ref_"):
                        referrer_code = arg
                        # If it's a numeric user ID ref
                        raw_sub = arg.replace("ref_", "")
                        if raw_sub.isdigit():
                            referrer_id = int(raw_sub)
                    elif arg.isdigit():
                        referrer_id = int(arg)

            # Add / update user in DB
            await self.db.add_or_update_user(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                referrer_id=referrer_id,
                referrer_code=referrer_code
            )

            # Check if user is admin
            owner_id = data.get("owner_id") or self.owner_id
            if owner_id and user.id == owner_id:
                is_admin = True
            elif user.id in ADMINS:
                is_admin = True
            else:
                db_admins = await self.db.get_admins()
                is_admin = user.id in db_admins

        data["is_admin"] = is_admin
        data["db"] = self.db
        return await handler(event, data)

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from typing import List, Dict, Any

def get_sub_channels_kb(channels: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    keyboard = []
    for idx, ch in enumerate(channels, 1):
        ch_type = ch.get("channel_type", "telegram")
        if ch_type == "external":
            icon = "🌐"
            link = ch.get("invite_link", "").lower()
            if "instagram" in link:
                icon = "📸"
            elif "youtube" in link or "youtu.be" in link:
                icon = "🔴"
            btn_text = f"{icon} {ch.get('name')}"
        else:
            btn_text = f"{idx}️⃣ {ch.get('name')}"

        keyboard.append([
            InlineKeyboardButton(text=btn_text, url=ch.get('invite_link'))
        ])
    keyboard.append([
        InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_movie_action_kb(movie_code: str, bot_username: str) -> InlineKeyboardMarkup:
    share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}?start=m_{movie_code}&text=Ajoyib+kino+topdim!+Kod:+{movie_code}"
    keyboard = [
        [
            InlineKeyboardButton(text="↗️ Do'stlarga ulashish", url=share_url)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from kino_bot.config import WEB_PANEL_URL

def get_admin_reply_kb() -> ReplyKeyboardMarkup:
    """Provides a single control button for admins on reply keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🕹️ Boshqaruv")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )


def get_admin_main_kb() -> InlineKeyboardMarkup:
    """Matches the exact screenshot layout for the Admin Panel."""
    keyboard = [
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin:stats"),
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin:users")
        ],
        [
            InlineKeyboardButton(text="🎬 Kinolar", callback_data="admin:movies"),
            InlineKeyboardButton(text="📬 Postlar", callback_data="admin:posts")
        ],
        [
            InlineKeyboardButton(text="✉️ Xabar yuborish", callback_data="admin:broadcast"),
            InlineKeyboardButton(text="📢 Reklama", callback_data="admin:ads")
        ],
        [
            InlineKeyboardButton(text="🔐 Kanallar", callback_data="admin:channels"),
            InlineKeyboardButton(text="🗳 So'rovlar", callback_data="admin:requests")
        ],
        [
            InlineKeyboardButton(text="💳 To'lov tizimlar", callback_data="admin:payments"),
            InlineKeyboardButton(text="⚙️ Premium", callback_data="admin:premium")
        ],
        [
            InlineKeyboardButton(text="📝 Matnlar", callback_data="admin:texts"),
            InlineKeyboardButton(text="🔗 Referal", callback_data="admin:referral")
        ],
        [
            InlineKeyboardButton(text="👮‍♂️ Adminlar", callback_data="admin:admins"),
            InlineKeyboardButton(text="↗️ Ulashish", callback_data="admin:share")
        ],
        [
            InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:close"),
            InlineKeyboardButton(text="🎨 Dizayn", callback_data="admin:design")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= FOYDALANUVCHILAR MENYUSI =================
def get_users_menu_kb() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="📋 Foydalanuvchilar ro'yxati", callback_data="users:list:1")],
        [InlineKeyboardButton(text="🔎 Foydalanuvchi qidirish", callback_data="users:search")],
        [InlineKeyboardButton(text="🚫 Bloklangan foydalanuvchilar", callback_data="users:blocked:1")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_users_pagination_kb(page: int, total_pages: int, mode: str = "all") -> InlineKeyboardMarkup:
    nav_row = []
    cb_prefix = "users:list" if mode == "all" else "users:blocked"

    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"{cb_prefix}:{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"{cb_prefix}:{page+1}"))

    keyboard = []
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:users")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= KINOLAR MENYUSI =================
def get_movies_mgmt_kb() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="📥 Kino yuklash", callback_data="movies:add:single"),
            InlineKeyboardButton(text="📦 Ko'p kino yuklash", callback_data="movies:add:batch")
        ],
        [
            InlineKeyboardButton(text="📝 Kino tahrirlash", callback_data="movies:edit"),
            InlineKeyboardButton(text="🗑 Kino o‘chirish", callback_data="movies:delete")
        ],
        [
            InlineKeyboardButton(text="📋 Kinolar ro'yxati", callback_data="movies:list:1")
        ],
        [
            InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_movies_pagination_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"movies:list:{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"movies:list:{page+1}"))

    keyboard = []
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:movies")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= XABAR YUBORISH =================
def get_broadcast_kb() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="💬 Oddiy", callback_data="broadcast:start:simple"),
            InlineKeyboardButton(text="📨 Forward", callback_data="broadcast:start:forward")
        ],
        [
            InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= REKLAMA (ADS) MENYUSI =================
def get_ads_menu_kb(start_enabled: bool, movie_enabled: bool) -> InlineKeyboardMarkup:
    start_txt = "🚀 Start: ✅ Yoqiq" if start_enabled else "🚀 Start: ❌ O'chiq"
    movie_txt = "🎬 Kino: ✅ Yoqiq" if movie_enabled else "🎬 Kino: ❌ O'chiq"

    keyboard = [
        [
            InlineKeyboardButton(text=start_txt, callback_data="ads:toggle:start"),
            InlineKeyboardButton(text=movie_txt, callback_data="ads:toggle:movie")
        ],
        [
            InlineKeyboardButton(text="➕ Reklama qo'shish", callback_data="ads:add")
        ],
        [
            InlineKeyboardButton(text="📋 Reklamalar ro'yxati", callback_data="ads:list:1")
        ],
        [
            InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_ads_pagination_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"ads:list:{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"ads:list:{page+1}"))

    keyboard = []
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:ads")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= KANALLAR MENYUSI =================
def get_channels_main_kb() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="channels:type_select")],
        [InlineKeyboardButton(text="📋 Ro'yxatni ko'rish", callback_data="channels:list")],
        [InlineKeyboardButton(text="🗑 Kanalni o'chirish", callback_data="channels:delete_menu")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_channels_type_select_kb() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="📢 Ommaviy / Shaxsiy (Kanal · Guruh)", callback_data="chadd:type:telegram")],
        [InlineKeyboardButton(text="🔐 Shaxsiy / So'rovli havola", callback_data="chadd:type:join_request")],
        [InlineKeyboardButton(text="🌐 Oddiy havola", callback_data="chadd:type:external")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:channels")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= SO'ROVLAR (JOIN REQUESTS) MENYUSI =================
def get_join_requests_menu_kb(auto_approve: bool, has_post: bool) -> InlineKeyboardMarkup:
    auto_txt = "⚡️ Avto tasdiqlash: ✅ Yoqiq" if auto_approve else "⚡️ Avto tasdiqlash: ❌ O'chiq"
    
    keyboard = [
        [
            InlineKeyboardButton(text=auto_txt, callback_data="requests:toggle_auto")
        ],
        [
            InlineKeyboardButton(text="📨 Post belgilash", callback_data="requests:set_post")
        ]
    ]
    if has_post:
        keyboard.append([
            InlineKeyboardButton(text="🗑 Postni o'chirish", callback_data="requests:clear_post")
        ])
    keyboard.append([
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= STATS =================
def get_stats_refresh_kb() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin:stats:refresh")
        ],
        [
            InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= PREMIUM SOZLAMALARI MENYUSI =================
def get_premium_menu_kb() -> InlineKeyboardMarkup:
    """Matches the exact screenshot layout for the Premium settings."""
    keyboard = [
        [InlineKeyboardButton(text="💡 Holat o‘zgartirish", callback_data="prem:toggle_status")],
        [InlineKeyboardButton(text="👥 Premium foydalanuvchilar ro‘yxati", callback_data="prem:users_list:1")],
        [InlineKeyboardButton(text="📋 Premium tariflar", callback_data="prem:tariffs")],
        [InlineKeyboardButton(text="➕ Premium berish / Muddatni boshqarish", callback_data="prem:manage_user")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_premium_tariffs_kb() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="✏️ 1 oylik narxini o'zgartirish", callback_data="prem:edit:1m")],
        [InlineKeyboardButton(text="✏️ 3 oylik narxini o'zgartirish", callback_data="prem:edit:3m")],
        [InlineKeyboardButton(text="✏️ 1 yillik narxini o'zgartirish", callback_data="prem:edit:1y")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:premium")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_premium_users_pagination_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"prem:users_list:{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"prem:users_list:{page+1}"))

    keyboard = []
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:premium")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_premium_user_actions_kb(user_id: int, is_prem: bool) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="➕ 1 oy (30 kun)", callback_data=f"prem:grant:{user_id}:30"),
            InlineKeyboardButton(text="➕ 3 oy (90 kun)", callback_data=f"prem:grant:{user_id}:90")
        ],
        [
            InlineKeyboardButton(text="➕ 1 yil (365 kun)", callback_data=f"prem:grant:{user_id}:365"),
            InlineKeyboardButton(text="♾ Cheksiz (Muddatsiz)", callback_data=f"prem:grant:{user_id}:unlimited")
        ]
    ]
    if is_prem:
        keyboard.append([
            InlineKeyboardButton(text="❌ Premiumdan chiqarish", callback_data=f"prem:revoke:{user_id}")
        ])
    keyboard.append([
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:premium")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= MATNLAR MENYUSI =================
def get_texts_menu_kb() -> InlineKeyboardMarkup:
    """Matches the exact screenshot layout for the Matnlar (Texts) section."""
    keyboard = [
        [InlineKeyboardButton(text="👋 Start xabari", callback_data="text:edit:welcome")],
        [InlineKeyboardButton(text="📢 Kanallar chiqadigan matn", callback_data="text:edit:channels_msg")],
        [InlineKeyboardButton(text="➕ Obuna bo'lish tugmasi", callback_data="text:edit:subscribe_btn")],
        [InlineKeyboardButton(text="✅ Tekshirish tugmasi", callback_data="text:edit:check_btn")],
        [InlineKeyboardButton(text="🎬 Kino caption matni", callback_data="text:edit:movie_caption")],
        [InlineKeyboardButton(text="↗️ Ulashish tugmasi", callback_data="text:edit:share_btn")],
        [InlineKeyboardButton(text="🔒 Premium kino xabari", callback_data="text:edit:prem_movie_msg")],
        [InlineKeyboardButton(text="💎 Premium tugmasi", callback_data="text:edit:prem_btn")],
        [InlineKeyboardButton(text="🎬 Kino qismlari sarlavhasi", callback_data="text:edit:series_title")],
        [InlineKeyboardButton(text="❌ Noto'g'ri kod xabari", callback_data="text:edit:wrong_code_msg")],
        [InlineKeyboardButton(text="🗃 Qism nomi (masalan: 1-qism)", callback_data="text:edit:part_name")],
        [InlineKeyboardButton(text="🎬 Kino nomi matni", callback_data="text:edit:movie_name_format")],
        [InlineKeyboardButton(text="💎 Premium faol — obuna sahifasi", callback_data="text:edit:prem_active_page")],
        [InlineKeyboardButton(text="💎 Premium taklifi sahifasi", callback_data="text:edit:prem_offer_page")],
        [InlineKeyboardButton(text="💳 To'lov tizimini tanlash", callback_data="text:edit:pay_select_msg")],
        [InlineKeyboardButton(text="💳 Qo'lda to'lov ma'lumotlari", callback_data="text:edit:manual_pay_info")],
        [InlineKeyboardButton(text="🧾 Chek qabul qilindi xabari", callback_data="text:edit:receipt_received_msg")],
        [InlineKeyboardButton(text="✅ To'lov tasdiqlandi xabari", callback_data="text:edit:pay_approved_msg")],
        [InlineKeyboardButton(text="❌ To'lov bekor qilindi xabari", callback_data="text:edit:pay_rejected_msg")],
        [InlineKeyboardButton(text="💰 Pullik kino taklifi", callback_data="text:edit:paid_movie_offer")],
        [InlineKeyboardButton(text="💰 Pullik kino — to'lov ma'lumotlari", callback_data="text:edit:paid_movie_pay_info")],
        [InlineKeyboardButton(text="🔄 Hammasini asliga qaytarish", callback_data="text:reset_all")],
        [InlineKeyboardButton(text="🎨 Dizayn menyusi", callback_data="admin:design")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_text_edit_kb(key: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🔄 Asliga qaytarish", callback_data=f"text:reset:{key}")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:texts")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= REFERAL MENYUSI =================
def get_referral_menu_kb() -> InlineKeyboardMarkup:
    """Matches the exact screenshot layout for the Referal section."""
    keyboard = [
        [InlineKeyboardButton(text="➕ Havola yaratish", callback_data="ref:create")],
        [InlineKeyboardButton(text="📋 Havolalar ro'yxati", callback_data="ref:list:1")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_referral_list_pagination_kb(page: int, total_pages: int, links: list) -> InlineKeyboardMarkup:
    keyboard = []
    
    # Delete buttons for each link on page
    for link in links:
        keyboard.append([
            InlineKeyboardButton(text=f"🗑 «{link['name']}»ni o'chirish", callback_data=f"ref:del:{link['id']}")
        ])
    
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"ref:list:{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"ref:list:{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
        
    keyboard.append([
        InlineKeyboardButton(text="➕ Yangi havola yaratish", callback_data="ref:create"),
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:referral")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= KONTENTNI HIMOYALASH / ULASHISH =================
def get_content_protection_kb(protect_regular: bool, protect_premium: bool) -> InlineKeyboardMarkup:
    reg_btn = "👥 Oddiy ( 🔓 Ruxsat berish )" if protect_regular else "👥 Oddiy ( 🔒 Taqiqlash )"
    prem_btn = "🌟 Premium ( 🔓 Ruxsat berish )" if protect_premium else "🌟 Premium ( 🔒 Taqiqlash )"

    keyboard = [
        [InlineKeyboardButton(text=reg_btn, callback_data="protect:toggle:regular")],
        [InlineKeyboardButton(text=prem_btn, callback_data="protect:toggle:premium")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= DIZAYN BOSHQARUVI MENYUSI =================
def get_design_menu_kb(colors: dict = None) -> InlineKeyboardMarkup:
    if colors is None:
        colors = {}
    
    c_sub = colors.get("subscribe", "⚪")
    c_chk = colors.get("check", "⚪")
    c_prem = colors.get("premium", "⚪")
    c_share = colors.get("share", "⚪")
    c_tar = colors.get("tariffs", "⚪")
    c_pay = colors.get("payments", "⚪")

    keyboard = [
        [InlineKeyboardButton(text=f"{c_sub} ➕ Obuna bo'lish", callback_data="design:btn:subscribe")],
        [InlineKeyboardButton(text=f"{c_chk} ✅ Tekshirish", callback_data="design:btn:check")],
        [InlineKeyboardButton(text=f"{c_prem} 💎 Premium", callback_data="design:btn:premium")],
        [InlineKeyboardButton(text=f"{c_share} ↗️ Ulashish", callback_data="design:btn:share")],
        [InlineKeyboardButton(text=f"{c_tar} 📦 Tarif tugmalari", callback_data="design:btn:tariffs")],
        [InlineKeyboardButton(text=f"{c_pay} 💳 To'lov tugmalari", callback_data="design:btn:payments")],
        [InlineKeyboardButton(text="📝 Matnlar", callback_data="admin:texts")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_design_button_detail_kb(key: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🎨 Rangni tanlash", callback_data=f"design:color:{key}")],
        [InlineKeyboardButton(text="✏️ Tugma matnini o'zgartirish", callback_data=f"design:text:{key}")],
        [InlineKeyboardButton(text="✨ Custom Emoji sozlash", callback_data=f"design:emoji:{key}")],
        [InlineKeyboardButton(text="🔄 Standart holatga qaytarish", callback_data=f"design:reset:{key}")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:design")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_color_picker_kb(key: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="⚪ Oq", callback_data=f"design:set_color:{key}:⚪"),
            InlineKeyboardButton(text="🟢 Yashil", callback_data=f"design:set_color:{key}:🟢"),
            InlineKeyboardButton(text="🔵 Ko'k", callback_data=f"design:set_color:{key}:🔵")
        ],
        [
            InlineKeyboardButton(text="🟡 Sariq", callback_data=f"design:set_color:{key}:🟡"),
            InlineKeyboardButton(text="🔴 Qizil", callback_data=f"design:set_color:{key}:🔴"),
            InlineKeyboardButton(text="🟣 Binafsha", callback_data=f"design:set_color:{key}:🟣")
        ],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"design:btn:{key}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")]
    ])


def get_cancel_fsm_kb(target: str = "admin:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data=target)]
    ])

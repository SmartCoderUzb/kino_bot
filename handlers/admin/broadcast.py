import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from kino_bot.database.db import Database
from kino_bot.utils.states import AdminBroadcast
from kino_bot.keyboards.admin_kb import get_broadcast_kb, get_back_to_admin_kb, get_cancel_fsm_kb
import logging

logger = logging.getLogger(__name__)
router = Router(name="admin_broadcast")

# ================= 1. XABAR TURI TANLASH =================
@router.callback_query(F.data == "admin:broadcast")
async def cb_admin_broadcast(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    await state.clear()

    text = "Foydalanuvchilarga yuboradigan xabar turini tanlang."
    await call.message.edit_text(text, reply_markup=get_broadcast_kb(), parse_mode="HTML")
    await call.answer()


# ================= 2. ODDIY XABAR =================
@router.callback_query(F.data == "broadcast:start:simple")
async def cb_broadcast_simple(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminBroadcast.waiting_for_content)
    await state.update_data(mode="simple")
    text = "✉️ <b>Barcha foydalanuvchilarga xabar yuborish:</b>\n\nIltimos, yubormoqchi bo'lgan xabaringizni (matn, rasm, video, audio va h.k.) yuboring:"
    await call.message.edit_text(text, reply_markup=get_cancel_fsm_kb("admin:broadcast"), parse_mode="HTML")
    await call.answer()


# ================= 3. FORWARD XABAR =================
@router.callback_query(F.data == "broadcast:start:forward")
async def cb_broadcast_forward(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminBroadcast.waiting_for_content)
    await state.update_data(mode="forward")
    text = "⏩ <b>Forward xabar yuborish:</b>\n\nIltimos, tarqatmoqchi bo'lgan xabaringizni bu yerga <b>Forward</b> qiling:"
    await call.message.edit_text(text, reply_markup=get_cancel_fsm_kb("admin:broadcast"), parse_mode="HTML")
    await call.answer()


@router.message(AdminBroadcast.waiting_for_content)
async def process_broadcast_content(message: Message, state: FSMContext, db: Database, bot):
    if message.text and message.text in ["Bekor qilish", "❌ Bekor qilish", "/cancel", "Orqaga", "🔙 Orqaga", "Bekor qilish ❌"]:
        await state.clear()
        return await message.answer("✅ Xabar yuborish bekor qilindi.", reply_markup=get_back_to_admin_kb())

    data = await state.get_data()
    mode = data.get("mode", "simple")
    await state.clear()

    user_ids = await db.get_all_user_ids()
    total = len(user_ids)
    if total == 0:
        return await message.answer("❌ Botda foydalanuvchilar mavjud emas.", reply_markup=get_back_to_admin_kb())

    status_msg = await message.answer(f"🚀 Xabar yuborilmoqda...\nJami: {total} ta foydalanuvchi.")
    
    sent = 0
    blocked = 0

    for idx, u_id in enumerate(user_ids, 1):
        try:
            if mode == "forward":
                await bot.forward_message(chat_id=u_id, from_chat_id=message.chat.id, message_id=message.message_id)
            else:
                await bot.copy_message(chat_id=u_id, from_chat_id=message.chat.id, message_id=message.message_id)
            sent += 1
        except Exception:
            blocked += 1
            await db.set_user_status(u_id, "blocked")

        if idx % 30 == 0 or idx == total:
            try:
                await status_msg.edit_text(
                    f"🚀 <b>Xabar yuborilmoqda:</b>\n\n"
                    f"• Jarayon: {idx}/{total}\n"
                    f"• Yetkazildi: {sent} ta\n"
                    f"• Yetkazilmadi (bloklangan): {blocked} ta",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        await asyncio.sleep(0.04)

    await status_msg.edit_text(
        f"✅ <b>Xabar yuborish yakunlandi!</b>\n\n"
        f"• Jami: {total} ta\n"
        f"• Muvaffaqiyatli: {sent} ta\n"
        f"• Bloklaganlar: {blocked} ta",
        reply_markup=get_back_to_admin_kb(),
        parse_mode="HTML"
    )

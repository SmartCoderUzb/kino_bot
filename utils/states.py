from aiogram.fsm.state import State, StatesGroup

class AdminAddMovie(StatesGroup):
    waiting_for_video = State()
    waiting_for_code = State()
    waiting_for_title = State()
    waiting_for_quality = State()
    waiting_for_language = State()

class AdminBatchAddMovies(StatesGroup):
    waiting_for_videos = State()

class AdminEditMovie(StatesGroup):
    waiting_for_target_code = State()
    waiting_for_new_title = State()
    waiting_for_new_code = State()
    waiting_for_new_video = State()

class AdminDeleteMovie(StatesGroup):
    waiting_for_code = State()

class AdminPostMaker(StatesGroup):
    waiting_for_channel = State()
    waiting_for_movie_code = State()

class AdminAddChannelTelegram(StatesGroup):
    waiting_for_forward_or_id = State()
    waiting_for_name = State()
    waiting_for_invite_link = State()

class AdminAddChannelExternal(StatesGroup):
    waiting_for_name = State()
    waiting_for_url = State()

class AdminSetJoinPost(StatesGroup):
    waiting_for_content = State()
    waiting_for_button_text = State()
    waiting_for_button_url = State()

class AdminBroadcast(StatesGroup):
    waiting_for_content = State()
    waiting_for_confirm = State()

class AdminAds(StatesGroup):
    waiting_for_content = State()
    waiting_for_button_text = State()
    waiting_for_button_url = State()

class AdminSetText(StatesGroup):
    waiting_for_key = State()
    waiting_for_value = State()

class AdminAddPayment(StatesGroup):
    waiting_for_name = State()
    waiting_for_details = State()

class AdminManageAdmin(StatesGroup):
    waiting_for_user_id = State()

class AdminPremiumTariffEdit(StatesGroup):
    waiting_for_price = State()

class AdminPremiumUserManage(StatesGroup):
    waiting_for_user_id = State()

class AdminCreateReferralLink(StatesGroup):
    waiting_for_name = State()

class AdminDesignEdit(StatesGroup):
    waiting_for_text = State()
    waiting_for_custom_emoji = State()

class UserSearch(StatesGroup):
    waiting_for_query = State()

class UserRequestMovie(StatesGroup):
    waiting_for_query = State()

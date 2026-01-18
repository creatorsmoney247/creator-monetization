from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def platform_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Instagram", callback_data="platform_instagram"),
            InlineKeyboardButton("TikTok", callback_data="platform_tiktok"),
        ],
        [
            InlineKeyboardButton("YouTube Shorts", callback_data="platform_youtube"),
            InlineKeyboardButton("Twitter", callback_data="platform_twitter"),
        ],
        [
            InlineKeyboardButton("Facebook", callback_data="platform_facebook"),
            InlineKeyboardButton("Other", callback_data="platform_other"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

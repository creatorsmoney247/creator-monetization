from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def niche_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Fashion/Beauty", callback_data="niche_fashion"),
            InlineKeyboardButton("Tech/Gadgets", callback_data="niche_tech"),
        ],
        [
            InlineKeyboardButton("Meme/Comedy", callback_data="niche_comedy"),
            InlineKeyboardButton("Lifestyle/Vlog", callback_data="niche_lifestyle"),
        ],
        [
            InlineKeyboardButton("Food/Hospitality", callback_data="niche_food"),
            InlineKeyboardButton("Music/Entertainment", callback_data="niche_music"),
        ],
        [
            InlineKeyboardButton("Fitness/Wellness", callback_data="niche_fitness"),
            InlineKeyboardButton("Other", callback_data="niche_other"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

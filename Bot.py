import telebot
import time
import os
from telebot import types

TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

BAD_WORDS = ['хуй', 'пизд', 'блять', 'сука', 'пидор', 'мудак', 'ебал']
user_warnings = {}
muted_users = {}

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_1 = types.KeyboardButton('🛡️ Помощь')
    btn_2 = types.KeyboardButton('🔓 Размут')
    btn_3 = types.KeyboardButton('📋 Список мута')
    markup.add(btn_1, btn_2, btn_3)
    return markup

@bot.message_handler(commands=['start', 'help'])
def start_message(message):
    bot.reply_to(message, "Я админ-бот Цербер. Слежу за порядком.\n\nДобавь меня в чат и дай права админа.\n\n🛡️ Помощь - инструкция.\n🔓 Размут - ответь на сообщение замученного, чтобы размутить.\n📋 Список мута - покажу, кто сидит.", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: True, content_types=['text'])
def check_message(message):
    if message.from_user.is_bot:
        return

    user_text = message.text
    chat_id = message.chat.id

    # --- ОБРАБОТКА КНОПОК ---
    if user_text == '🛡️ Помощь':
        bot.reply_to(message, "Я удаляю мат, выдаю предупреждения (3 страйка) и мучу на час. Чтобы размутить кого-то, ответь на его сообщение и нажми '🔓 Размут'.", reply_markup=get_main_menu())
        return
        
    elif user_text == '📋 Список мута':
        if not muted_users:
            bot.reply_to(message, "Сейчас никто не сидит в муте.", reply_markup=get_main_menu())
        else:
            text = "Список замученных:\n"
            for uid, uname in muted_users.items():
                text += f"@{uname}\n"
            bot.reply_to(message, text, reply_markup=get_main_menu())
        return
        
    elif user_text == '🔓 Размут':
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            target_name = message.reply_to_message.from_user.username or message.reply_to_message.from_user.first_name
            try:
                bot.restrict_chat_member(chat_id, target_id, can_send_messages=True)
                if target_id in muted_users:
                    del muted_users[target_id]
                bot.reply_to(message, f"@{target_name} размучен. Гуляй, но смотри не косячь.", reply_markup=get_main_menu())
            except Exception as e:
                bot.reply_to(message, f"Ошибка: {e}. Убедись, что у меня есть права.", reply_markup=get_main_menu())
        else:
            bot.reply_to(message, "Ответь на сообщение того, кого хочешь размутить, и нажми эту кнопку.", reply_markup=get_main_menu())
        return

    # --- ПРОВЕРКА НА АДМИНА ---
    try:
        admins = [admin.user.id for admin in bot.get_chat_administrators(chat_id)]
        if message.from_user.id in admins:
            return
    except:
        pass

    # --- ПРОВЕРКА МАТА ---
    text_lower = user_text.lower()
    is_bad = False
    for word in BAD_WORDS:
        if word in text_lower:
            is_bad = True
            break

    if is_bad:
        user_id = message.from_user.id
        user_name = message.from_user.username or message.from_user.first_name

        try:
            bot.delete_message(chat_id, message.message_id)
            if user_id not in user_warnings:
                user_warnings[user_id] = 0
            user_warnings[user_id] += 1

            if user_warnings[user_id] >= 3:
                until_date = int(time.time()) + 3600
                bot.restrict_chat_member(chat_id, user_id, until_date=until_date, can_send_messages=False)
                bot.send_message(chat_id, f"@{user_name}, ты заебал! Мут на 1 час.")
                muted_users[user_id] = user_name
                user_warnings[user_id] = 0
            else:
                bot.send_message(chat_id, f"@{user_name}, не матерись! Предупреждение {user_warnings[user_id]}/3.")
        except Exception as e:
            print(f"ОШИБКА: {e}")

if name == 'main':
    print("Админ-бот (Цербер) запущен...")
    bot.polling(non_stop=True)

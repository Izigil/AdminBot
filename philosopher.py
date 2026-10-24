import telebot
import requests
import time
from telebot import types

# ВСТАВЬ СВОЙ ТОКЕН ОТ БОТФАЗЕРА В КАВЫЧКИ НИЖЕ
TOKEN = '8963384031:AAFBkJTaDppZ9B_CxqMH7RR9vt9jLOJQElA'
# ВСТАВЬ СВОЙ КЛЮЧ ОТ OPENROUTER В КАВЫЧКИ НИЖЕ
AI_API_KEY = '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'

AI_URL = "https://openrouter.ai/api/v1/chat/completions"

bot = telebot.TeleBot(TOKEN)
user_histories = {}

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_1 = types.KeyboardButton('Порассуждай')
    btn_2 = types.KeyboardButton('Оскорби меня')
    btn_3 = types.KeyboardButton('Очистить память')
    markup.add(btn_1, btn_2, btn_3)
    return markup

@bot.message_handler(commands=['start'])
def start_message(message):
    user_histories[message.chat.id] = []
    bot.reply_to(message, "Здарова, братуха! Я Изигиль. Чё надо?", reply_markup=get_main_menu())

@bot.message_handler(func=lambda message: True)
def chat(message):
    chat_id = message.chat.id
    if chat_id not in user_histories:
        user_histories[chat_id] = []

    user_text = message.text

    if user_text == 'Очистить память':
        user_histories[chat_id] = []
        bot.reply_to(message, "Память мне отшибло, блять. Начинаем с чистого листа.", reply_markup=get_main_menu())
        return

    if user_text == 'Порассуждай':
        user_text = 'Расскажи о смысле жизни.'
    elif user_text == 'Оскорби меня':
        user_text = 'Оскорби меня.'

    system_prompt = (
        "Ты — Изигиль Рахметович, наглый инопланетянин, который выучил русский по пацанским пабликам. "
        "Ты общаешься грубо, с матом, используешь уличный сленг. Твои любимые фразы: 'ЕБАТЬ МОЙ ЛЫСЫЙ ЧЕРЕП', 'ЕБАТЬ ЧЁТКО, НИШТЯК', 'ПИЗДЕЦ Я В АХУЕ'. "
        "Ты любишь собак больше людей и презираешь офисный планктон. "
        "Твоя главная особенность: ты можешь отвечать как угодно. Хочешь — дай короткий, злой и дерзкий ответ в 1-2 предложения. Хочешь — разверни длинную, глубокую и философскую мысль. "
        "Главное правило: отвечай по сути заданного вопроса, но всегда сохраняй свой жесткий, циничный и немного безумный стиль. Не переходи на английский. Ты не ИИ, ты Изигиль."
    )

    user_histories[chat_id].append({"role": "user", "content": user_text})
    messages_for_api = [{"role": "system", "content": system_prompt}] + user_histories[chat_id][-6:]

    payload = {
        "model": "openrouter/free", 
        "messages": messages_for_api,
        "stream": False
    }
    
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(AI_URL, json=payload, headers=headers, timeout=60)
        result = response.json()
        
        if 'error' in result:
            bot.reply_to(message, f"Блять, API выдало ошибку: {result['error']['message']}", reply_markup=get_main_menu())
            return
            
        ai_reply = result['choices'][0]['message']['content']
        user_histories[chat_id].append({"role": "assistant", "content": ai_reply})
        bot.reply_to(message, ai_reply, reply_markup=get_main_menu())
    except Exception as e:
        bot.reply_to(message, f"Блять, у меня мозги зависли. Ошибка: {e}", reply_markup=get_main_menu())

if __name__ == '__main__':
    print("Бот-философ (OpenRouter) запущен...")
    bot.polling(none_stop=True)

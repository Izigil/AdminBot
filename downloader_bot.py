import telebot
import yt_dlp
import os

# ВСТАВЬ СВОЙ ТОКЕН
TOKEN = '9096084181:AAG7izHTvmU80bmkrt5OYO8Alxgu2n7-Swc'
bot = telebot.TeleBot(TOKEN)

# Папка для скачивания (создастся сама)
DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Здарова. Кидай ссылку на видео, я скачаю.")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text
    
    # Проверяем, похоже ли это на ссылку
    if not url.startswith('http'):
        bot.reply_to(message, "Это не похоже на ссылку, брат. Кидай нормальный URL.")
        return

    msg = bot.reply_to(message, "Качаю, подожди...")
    
    try:
        # Настройки yt-dlp
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'noplaylist': True,
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        # Отправляем видео (лимит Телеграма 50 МБ для ботов без Premium)
        with open(filename, 'rb') as video:
            bot.send_video(message.chat.id, video, caption="Держи, братуха.")
        
        # Удаляем файл после отправки, чтобы не забивать диск
        os.remove(filename)
        bot.delete_message(message.chat.id, msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"Ошибка: {e}", message.chat.id, msg.message_id)

print("Бот-качальщик запущен...")
bot.polling(non_stop=True)

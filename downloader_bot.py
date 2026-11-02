import telebot
import yt_dlp
import os

# Берем токен из переменных Bothost
TOKEN = os.environ.get('BOT_TOKEN_DOWNLOADER')
bot = telebot.TeleBot(TOKEN)

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Здарова. Кидай ссылку на видео, я скачаю.")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text
    
    if not url.startswith('http'):
        bot.reply_to(message, "Это не похоже на ссылку, брат. Кидай нормальный URL.")
        return

    msg = bot.reply_to(message, "Качаю, подожди...")
    
    try:
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'noplaylist': True,
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        with open(filename, 'rb') as video:
            bot.send_video(message.chat.id, video, caption="Держи, братуха.")
        
        os.remove(filename)
        bot.delete_message(message.chat.id, msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"Ошибка: {e}", message.chat.id, msg.message_id)

if __name__ == '__main__':
    print("Бот-качальщик запущен...")
    # Вот та самая правильная строка вместо non_stop=True
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
